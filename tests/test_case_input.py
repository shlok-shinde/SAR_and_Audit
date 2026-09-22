import pandas as pd

import case_input as ci
from conftest import FIXTURES


def _load(name, **kw):
    raw = ci.read_table(open(FIXTURES / name, "rb"), name)
    return ci.import_table(raw, **kw)


def test_ibm_trans_format_is_detected_and_enriched():
    canon, issues, fmt, _ = _load("ibm_cycle_249.csv")
    assert fmt == "ibm_trans"
    assert len(canon) == 124
    assert canon["Flagged"].sum() == 6          # "Is Laundering" used as the alert flag
    assert set(ci.CANONICAL_COLUMNS) <= set(canon.columns)
    # Bank / entity names come from HI-Small_accounts.csv
    row = canon[canon["From_Account"] == "8049DD1C0"].iloc[0]
    assert row["From_Bank_Name"] == "China Bank #14"
    assert any("Is Laundering" in i["message"] for i in issues)


def test_generic_export_mapping_dates_and_bank_names():
    canon, issues, fmt, mapping = _load("generic_structuring.csv", dayfirst=True)
    assert fmt == "generic"
    assert not [i for i in issues if i["level"] == "error"]
    assert mapping["from_account"] == "Sender Acct" and mapping["from_name"] == "Sender"
    assert len(canon) == 21 and canon["Flagged"].sum() == 9
    first = canon.iloc[0]
    assert first["Timestamp"] == "2024/05/02 17:05"       # 02/05/2024 read day-first
    assert first["Amount Paid"] == 1840.25                   # "$1,840.25" parsed
    assert first["To_Bank_Name"] == "Harbor Community Bank"  # names routed to the name column
    assert first["To Bank"] == ""


def test_xlsx_matches_csv():
    csv, *_ = _load("generic_structuring.csv", dayfirst=True)
    xlsx, *_ = _load("generic_structuring.xlsx", dayfirst=True)
    pd.testing.assert_frame_equal(csv, xlsx)


def test_statement_debit_credit_becomes_from_to():
    canon, issues, _, _ = _load("statement_structuring.csv", dayfirst=True,
                                statement_account="NG-4471")
    assert not [i for i in issues if i["level"] == "error"]
    deposit = canon[canon["Timestamp"] == "2024/06/03 09:12"].iloc[0]
    assert (deposit["From_Account"], deposit["To_Account"]) == ("DEP-RK01", "NG-4471")
    wire = canon[canon["Timestamp"] == "2024/06/06 13:15"].iloc[0]
    assert (wire["From_Account"], wire["To_Account"]) == ("NG-4471", "AE-77120")


def test_statement_without_account_number_is_an_error():
    _, issues, _, _ = _load("statement_structuring.csv", dayfirst=True)
    assert any(i["level"] == "error" and "statement" in i["message"] for i in issues)


def test_bad_dates_and_amounts_are_reported():
    df = pd.DataFrame({"Date": ["2024-01-02", "not a date"], "From": ["A1", "B2"],
                       "To": ["B2", "C3"], "Amount": ["100", "abc"]})
    _, issues, _, _ = ci.import_table(df, {"timestamp": "Date", "from_account": "From",
                                           "to_account": "To", "amount": "Amount"})
    messages = " ".join(i["message"] for i in issues if i["level"] == "error")
    assert "date" in messages and "amount" in messages


def test_finalize_manual_grid():
    grid = ci.empty_transactions().reindex(range(3))
    grid.loc[0, ["Timestamp", "From_Account", "To_Account", "Amount Paid"]] = [
        "2024-06-03 10:00", "A-1", "B-2", 500.0]
    grid.loc[1, ["Timestamp", "From_Account", "Amount Paid"]] = ["2024-06-04", "B-2", 20.0]
    txns, issues = ci.finalize_transactions(grid)
    assert len(txns) == 2                                   # blank row dropped
    assert txns.loc[0, "Timestamp"] == "2024/06/03 10:00"
    assert txns.loc[0, "Amount Received"] == 500.0          # filled from paid
    assert any("missing a From or To account" in i["message"] for i in issues)


def test_case_round_trip_and_fingerprint(northgate_case):
    data = northgate_case.to_dict()
    again = ci.CaseInput.from_dict(data)
    assert again.fingerprint() == northgate_case.fingerprint()
    assert again.subject.occupation == "Retail auto parts store"
    again.investigation.findings += " More."
    assert again.fingerprint() != northgate_case.fingerprint()


def test_case_facts_and_views(northgate_case):
    facts = northgate_case.case_facts()
    assert facts["Subject name"] == "Northgate Auto Parts LLC"
    assert facts["Expected monthly volume"] == "40,000.00"
    assert len(northgate_case.flagged()) == 9 and len(northgate_case.context()) == 12


def test_from_attempt_sample():
    case = ci.from_attempt(249, "006")
    assert case.dataset_label == "CYCLE" and case.attempt_id == 249
    assert "pattern_type" not in case.transactions.columns
    assert len(case.flagged()) == 5


def test_guess_dayfirst():
    assert ci.guess_dayfirst(["03/06/2024", "13/06/2024"])
    assert not ci.guess_dayfirst(["06/13/2024"])
