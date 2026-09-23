"""Edge cases found by the 2026-09-23 end-to-end test (docs/EDGE_CASES.md).

Tests marked xfail(strict=True) document a KNOWN defect: they fail today, and
the moment a fix makes one pass, strict mode fails the suite so the marker is
removed and the test becomes a regression guard. The IDs (EC-xx) match the
report. Unmarked tests are behaviours that held up and must keep holding.
"""
import io

import pandas as pd
import pytest

import audit_trail as at
import case_input as ci
import generate_narrative as g
import typology as ty


def known(ec: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{ec}: {why}")


def txns(rows):
    out = []
    for i, r in enumerate(rows):
        ccy = r.get("ccy", "US Dollar")
        out.append({"Timestamp": r["ts"], "From_Account": r["frm"], "To_Account": r["to"],
                    "From_Bank_Name": r.get("fbn", "Harbor Community Bank"),
                    "To_Bank_Name": r.get("tbn", "Harbor Community Bank"),
                    "From_Entity_Name": r.get("fn", ""), "To_Entity_Name": r.get("tn", ""),
                    "Amount Paid": r["amt"], "Payment Currency": ccy,
                    "Amount Received": r["amt"], "Receiving Currency": ccy,
                    "Payment Format": r.get("fmt", "ACH"), "Flagged": True, "Txn_ID": f"E{i}"})
    return ci.normalise_frame(pd.DataFrame(out))


def imp(text: str | bytes):
    data = text.encode() if isinstance(text, str) else text
    raw = ci.read_table(io.BytesIO(data), "x.csv")
    mapping = ci.suggest_mapping(raw.columns)
    return ci.apply_mapping(raw, mapping, dayfirst=ci.guess_dayfirst(raw[mapping["timestamp"]]))


HDR = "Date,From Account,To Account,Amount,Currency\n"


def _facts(case, sentence):
    d, flags = ty.analyse_case(case)
    idx = at.FactIndex(case.transactions, case.case_facts(), [f.to_dict() for f in flags],
                       d.to_dict())
    return at.check_sentence_facts(sentence, case.transactions, case.case_facts(), idx)


@pytest.fixture
def single_depositor():
    rows = [dict(ts=f"2024/06/0{d} 10:00", frm="CASH-JD01", to="ACC-5520", amt=a, fmt="Cash")
            for d, a in [(3, 9800.0), (4, 9750.0), (5, 9900.0), (6, 9650.0)]]
    return ci.CaseInput("EDGE-STRUCT", txns(rows))


# ── EC-01: "no SAR" on a high-risk case without a network pattern ───────────

def test_single_depositor_structuring_is_high_risk(single_depositor):
    d, flags = ty.analyse_case(single_depositor)
    assert d.pattern == "NONE"
    assert any(f.code == "STRUCTURING" and f.severity == "high" for f in flags)
    assert not ty.warrants_no_sar(d.pattern, flags)


@known("EC-01", "system rule 6 tells the model NONE ⇒ 'does not warrant a SAR' even with high flags")
def test_prompt_does_not_invite_no_sar_when_high_flags_exist(single_depositor):
    d, flags = ty.analyse_case(single_depositor)
    rule6_by_pattern = "Only when the case's pattern is RANDOM or NONE" in g.SYSTEM_PROMPT
    assert not rule6_by_pattern or g.case_directive(d.pattern, flags)


@known("EC-01", "the contradiction check is skipped for NONE/RANDOM even when no_sar is False")
def test_validation_rejects_no_sar_conclusion_when_high_flags_exist():
    text = "\n\n".join(f"### {h}\n\nThis activity does not warrant a SAR filing."
                       for h in ["Who", "What", "When", "Where", "Why Suspicious"])
    assert g.validate_narrative(text, "stop", "NONE", no_sar=False)


# ── EC-02: amount formats that import silently wrong ────────────────────────

@known("EC-02", "European decimal comma read as 1.23456")
def test_european_decimal_comma():
    c, issues = imp(HDR + '2024-06-03,A-1,B-2,"1.234,56",EUR\n')
    assert c["Amount Paid"][0] == pytest.approx(1234.56) or any(i["level"] == "error" for i in issues)


@known("EC-02", "semicolon export with 9.800,00 read as 9.8")
def test_semicolon_european_export():
    c, issues = imp("Date;From Account;To Account;Amount;Currency\n03.06.2024;A-1;B-2;9.800,00;EUR\n")
    assert c["Amount Paid"][0] == pytest.approx(9800) or any(i["level"] == "error" for i in issues)


@known("EC-02", "'$9.8k' / '$1.2M' stripped to 9.8 / 1.2")
def test_abbreviated_amounts():
    c, issues = imp(HDR + "2024-06-03,A-1,B-2,$9.8k,USD\n")
    assert c["Amount Paid"][0] == pytest.approx(9800) or any(i["level"] == "error" for i in issues)


# ── EC-03: relationships between verified values are not checked ────────────

@known("EC-03", "every value exists, so a reversed transfer passes the fact-check")
def test_reversed_direction_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "AE-77120 sent $38,000.00 to NG-4471.")
    assert unverified


@known("EC-03", "a negated fact with a real account ID is not flagged")
def test_negated_fact_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "NG-4471 did not receive any cash deposits in June 2024.")
    assert unverified


# ── EC-04: continuing-activity SARs ──────────────────────────────────────────

@known("EC-04", "prior SAR amount + current total is not indexed; the prompt asks for it")
def test_cumulative_total_is_verified(northgate_case):
    northgate_case.prior_sars = [ci.PriorSAR(filed_on="2024-03-01", reference="BSA-31000000123456",
                                             amount=41200.0)]
    _, unverified = _facts(northgate_case, "The cumulative total is $109,350.00.")
    assert not unverified


@known("EC-04", "validation does not require the prior SAR to be cited")
def test_continuing_draft_must_cite_prior_sar():
    text = "\n\n".join(f"### {h}\n\nNew activity only." for h in
                       ["Who", "What", "When", "Where", "Why Suspicious"])
    problems = g.validate_narrative(text, "stop", "GATHER-SCATTER", no_sar=False)
    assert any("prior SAR" in p for p in problems)


# ── EC-05: currencies in the fact-check ──────────────────────────────────────

@known("EC-05", "currency-less legacy aggregates verify a $ figure against a euro value")
def test_dollar_figure_does_not_match_euro_only_value():
    rows = [dict(ts=f"2024/02/0{5 + i} 11:00", frm=f"DE-10{i}", to="FR-900", amt=a, ccy="Euro")
            for i, a in enumerate([18250.40, 22100.00, 15875.25, 19990.10])]
    rows.append(dict(ts="2024/02/10 16:00", frm="FR-900", to="CY-777", amt=74000.00, ccy="Euro"))
    case = ci.CaseInput("EUR", txns(rows))
    _, unverified = _facts(case, "FR-900 sent $74,000.00 to CY-777.")
    assert unverified   # the wire was €74,000.00, not $74,000.00


# ── EC-07: identifiers ───────────────────────────────────────────────────────

@known("EC-07", "identifier regex needs a letter; numeric account numbers are never matched")
def test_numeric_account_numbers_are_matched():
    case = ci.CaseInput("NUM", txns([dict(ts="2024/04/01 10:00", frm="4001234501",
                                          to="5500123456", amt=7300.00)]))
    refs, _ = _facts(case, "Account 5500123456 received $7,300.00 from 4001234501.")
    assert any(r.field_name == "Account" for r in refs)


@known("EC-07", "a truncated ID that is a substring of a real one is skipped")
def test_truncated_account_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "Funds went to NG-447.")
    assert unverified


# ── EC-08: counts and durations ──────────────────────────────────────────────

@known("EC-08", "subset counts ('the first three deposits') are flagged as wrong totals")
def test_subset_count_is_not_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "The first three deposits were made on June 3 and 4, 2024.")
    assert not unverified


@known("EC-08", "durations are not checked (live draft: '16 days' for a 6-day span)")
def test_wrong_duration_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "The activity spanned approximately 16 days.")
    assert unverified


# ── EC-09: prompt budget on large cases ─────────────────────────────────────

@known("EC-09", "ACCOUNTS & ENTITIES is not summarised; ~300 counterparties overflow num_ctx")
def test_large_fan_out_fits_the_context_window():
    rows = [dict(ts=f"2024/05/{1 + i % 28:02d} 10:00", frm="HUB-0001", to=f"MULE-{i:04d}",
                 amt=1000.0 + i) for i in range(300)]
    case = ci.CaseInput("BIG", txns(rows))
    d, flags = ty.analyse_case(case)
    assert g.estimate_prompt_tokens(case, d, flags) + g.NUM_PREDICT <= g.NUM_CTX


# ── EC-11: import hygiene ────────────────────────────────────────────────────

@known("EC-11", "'Euro' and 'EUR' are different currencies to the rules → false CROSS_CURRENCY")
def test_currency_spellings_are_normalised():
    c, _ = imp(HDR + "2024-06-03,A-1,B-2,100.00,Euro\n2024-06-04,B-2,C-3,100.00,EUR\n")
    _, flags = ty.analyse_case(ci.CaseInput("x", c))
    assert not any(f.code == "CROSS_CURRENCY" for f in flags)


@known("EC-11", "Windows-1252 files are decoded as UTF-8 with replacement characters")
def test_cp1252_file_keeps_accents():
    data = (HDR.replace("Amount", "Beneficiary,Amount")
            + "2024-06-03,A-1,B-2,Société Générale,100.00,EUR\n").encode("cp1252")
    c, issues = imp(data)
    assert "Société" in c["To_Entity_Name"][0] or any("encod" in i["message"].lower() for i in issues)


@known("EC-11", "exact duplicate rows are double-counted without a warning")
def test_duplicate_rows_are_warned():
    _, issues = imp(HDR + "2024-06-03,A-1,B-2,100.00,USD\n2024-06-03,A-1,B-2,100.00,USD\n")
    assert any("duplicate" in i["message"].lower() for i in issues)


# ── EC-12: validation ────────────────────────────────────────────────────────

@known("EC-12", r"'\bno SAR\b' rejects 'No SAR has previously been filed' in a positive case")
def test_prior_sar_statement_is_not_a_no_sar_conclusion():
    text = "\n\n".join(f"### {h}\n\nNo SAR has previously been filed on this subject."
                       for h in ["Who", "What", "When", "Where", "Why Suspicious"])
    assert not g.validate_narrative(text, "stop", "GATHER-SCATTER", no_sar=False)


# ── EC-13 … EC-17: parsing details ───────────────────────────────────────────

@known("EC-13", "'31 CFR 1020.320' is read as the amount $1,020.32")
def test_cfr_citation_is_not_an_amount(northgate_case):
    _, unverified = _facts(northgate_case, "The filing is required under 31 CFR 1020.320.")
    assert not unverified


@known("EC-14", "'$68.15 thousand' is read as $68.15")
def test_scaled_amount_words(northgate_case):
    _, unverified = _facts(northgate_case, "Deposits totalled $68.15 thousand.")
    assert not unverified


@known("EC-15", "impossible dates are silently dropped instead of flagged")
def test_impossible_date_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "The wire was sent on June 31, 2024.")
    assert unverified


@known("EC-16", "bank names match as raw substrings ('Chase' inside 'purchased')")
def test_bank_name_matches_whole_words_only():
    case = ci.CaseInput("C", txns([dict(ts="2024/06/03 10:00", frm="A-1", to="B-2", amt=100.0,
                                        tbn="Chase")]))
    refs, _ = _facts(case, "The subject purchased goods online.")
    assert not refs


@known("EC-17", "sentence splitter breaks on 'U.S.' and 'Mr.'")
def test_abbreviations_do_not_split_sentences():
    sents = at.parse_narrative_into_sentences(
        "### What\n\nFunds went to U.S. accounts held by Mr. Kumar. He then wired $9,800.00 abroad.")
    assert len(sents) == 2


@known("EC-17", "'whole' in a heading is normalised to the Who section")
def test_heading_normalisation_uses_word_boundaries():
    sents = at.parse_narrative_into_sentences(
        "### Quantitative Summary (whole period)\n\nSeven deposits totalling $68,150.00.")
    assert sents[0].section == "Quantitative Summary"


# ── Behaviours that held up (regression guards) ─────────────────────────────

@pytest.mark.parametrize("sentence, flagged", [
    ("NG-4471 received $68,150.00 in cash.", False),
    ("NG-4471 received approximately $68,000 in cash.", False),
    ("NG-4471 received $86,150.00 in cash.", True),
    ("The first deposit was USD 9,800 on June 3, 2024.", False),
    ("About 98% of the inflow left within two days.", False),
    ("Deposits ran from June 3–7, 2024.", False),
    ("A further deposit was made on June 20, 2024.", True),
])
def test_fact_check_core_cases(northgate_case, sentence, flagged):
    _, unverified = _facts(northgate_case, sentence)
    assert bool(unverified) == flagged


def test_edit_tracking_merge_reorder_and_figure_change():
    base = at.parse_narrative_into_sentences(
        "### What\n\nNG-4471 received $68,150.00. It wired $38,000.00 to AE-77120.")
    merged = at.parse_narrative_into_sentences(
        "### What\n\nNG-4471 received $68,150.00 and wired $38,000.00 to AE-77120.")
    changes, removed = at.diff_provenance(base, merged)
    assert len(removed) == 1 and list(changes.values())[0]["kind"] == "edited"
    reordered = at.parse_narrative_into_sentences(
        "### What\n\nIt wired $38,000.00 to AE-77120. NG-4471 received $68,150.00.")
    assert at.diff_provenance(base, reordered) == ({}, [])
    figure = at.parse_narrative_into_sentences(
        "### What\n\nNG-4471 received $68,510.00. It wired $38,000.00 to AE-77120.")
    assert at.diff_provenance(base, figure)[0][0]["kind"] == "edited"


def test_import_handles_iso_z_two_digit_years_and_yes_no_flags():
    c, _ = imp(HDR + "2024-06-03T14:40:00Z,A-1,B-2,100.00,USD\n")
    assert c["Timestamp"][0] == "2024/06/03 14:40"
    c, _ = imp(HDR.replace(",Currency", ",Currency,Flagged")
               + "2024-06-03,A-1,B-2,100.00,USD,Y\n2024-06-04,A-1,B-2,90.00,USD,N\n")
    assert c["Flagged"].tolist() == [True, False]
