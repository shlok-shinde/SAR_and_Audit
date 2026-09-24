"""Edge cases found by the 2026-09-23 end-to-end test (docs/EDGE_CASES.md).

Each test was first written as xfail(strict=True) against the defect it names
(EC-xx), confirmed to fail on its assertion, and had its marker removed when the
fix landed — so every one is now a regression guard for a real, observed failure.
`known()` is kept for pinning the next defect the same way.
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


def test_prompt_does_not_invite_no_sar_when_high_flags_exist(single_depositor):
    d, flags = ty.analyse_case(single_depositor)
    assert "Only when the case's pattern is RANDOM or NONE" not in g.SYSTEM_PROMPT
    directive = g.case_directive(d.pattern, flags)
    assert "high-severity red flags" in directive and "Amounts just below" in directive
    assert "Do not state that the activity does not warrant a SAR" in directive


def test_validation_rejects_no_sar_conclusion_when_high_flags_exist():
    text = "\n\n".join(f"### {h}\n\nThis activity does not warrant a SAR filing."
                       for h in ["Who", "What", "When", "Where", "Why Suspicious"])
    assert g.validate_narrative(text, "stop", "NONE", no_sar=False)


# ── EC-02: amount formats that import silently wrong ────────────────────────

@pytest.mark.parametrize("cell, expected", [
    ('"1.234,56"', 1234.56), ('"1 234,56"', 1234.56), ('"$1,840.25"', 1840.25),
    ("$9.8k", 9800.0), ("$1.2M", 1_200_000.0), ("(250.00)", 250.0), ("USD 9800", 9800.0),
])
def test_amount_formats(cell, expected):
    c, issues = imp(HDR + f"2024-06-03,A-1,B-2,{cell},EUR\n")
    assert c["Amount Paid"][0] == pytest.approx(expected)
    assert not [i for i in issues if i["level"] == "error"]


def test_semicolon_european_export():
    c, issues = imp("Date;From Account;To Account;Amount;Currency\n03.06.2024;A-1;B-2;9.800,00;EUR\n")
    assert c["Amount Paid"][0] == pytest.approx(9800)
    assert c["Timestamp"][0] == "2024/06/03 00:00"          # dotted dates are day-first
    assert any("decimal separator" in i["message"] for i in issues)


def test_unreadable_amount_is_an_error_not_a_guess():
    _, issues = imp(HDR + "2024-06-03,A-1,B-2,about ten grand,USD\n")
    assert any(i["level"] == "error" and "amount" in i["message"] for i in issues)


# ── EC-03: relationships between verified values are not checked ────────────

def test_reversed_direction_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "AE-77120 sent $38,000.00 to NG-4471.")
    assert unverified


def test_negated_fact_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "NG-4471 did not receive any cash deposits in June 2024.")
    assert unverified


# ── EC-04: continuing-activity SARs ──────────────────────────────────────────

def test_cumulative_total_is_verified(northgate_case):
    northgate_case.prior_sars = [ci.PriorSAR(filed_on="2024-03-01", reference="BSA-31000000123456",
                                             amount=41200.0)]
    _, unverified = _facts(northgate_case, "The cumulative total is $109,350.00.")
    assert not unverified


def test_continuing_draft_must_cite_prior_sar():
    prior = [ci.PriorSAR(filed_on="2024-03-01", reference="BSA-31000000123456", amount=41200.0)]
    text = "\n\n".join(f"### {h}\n\nNew activity only." for h in
                       ["Who", "What", "When", "Where", "Why Suspicious"])
    assert any("prior SAR" in w for w in g.draft_warnings(text, prior))
    cited = text + "\n\nThis continues the SAR filed on March 1, 2024."
    assert not any("prior SAR" in w for w in g.draft_warnings(cited, prior))


# ── EC-05: currencies in the fact-check ──────────────────────────────────────

def test_dollar_figure_does_not_match_euro_only_value():
    rows = [dict(ts=f"2024/02/0{5 + i} 11:00", frm=f"DE-10{i}", to="FR-900", amt=a, ccy="Euro")
            for i, a in enumerate([18250.40, 22100.00, 15875.25, 19990.10])]
    rows.append(dict(ts="2024/02/10 16:00", frm="FR-900", to="CY-777", amt=74000.00, ccy="Euro"))
    case = ci.CaseInput("EUR", txns(rows))
    _, unverified = _facts(case, "FR-900 sent $74,000.00 to CY-777.")
    assert unverified   # the wire was €74,000.00, not $74,000.00


# ── EC-07: identifiers ───────────────────────────────────────────────────────

def test_numeric_account_numbers_are_matched():
    case = ci.CaseInput("NUM", txns([dict(ts="2024/04/01 10:00", frm="4001234501",
                                          to="5500123456", amt=7300.00)]))
    refs, _ = _facts(case, "Account 5500123456 received $7,300.00 from 4001234501.")
    assert any(r.field_name == "Account" for r in refs)


def test_truncated_account_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "Funds went to NG-447.")
    assert unverified


# ── EC-08: counts and durations ──────────────────────────────────────────────

def test_subset_count_is_not_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "The first three deposits were made on June 3 and 4, 2024.")
    assert not unverified


def test_wrong_duration_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "The activity spanned approximately 16 days.")
    assert unverified


# ── EC-09: prompt budget on large cases ─────────────────────────────────────

def test_large_fan_out_fits_the_context_window():
    rows = [dict(ts=f"2024/05/{1 + i % 28:02d} 10:00", frm="HUB-0001", to=f"MULE-{i:04d}",
                 amt=1000.0 + i) for i in range(300)]
    case = ci.CaseInput("BIG", txns(rows))
    d, flags = ty.analyse_case(case)
    assert g.estimate_prompt_tokens(case, d, flags) + g.NUM_PREDICT <= g.NUM_CTX


# ── EC-11: import hygiene ────────────────────────────────────────────────────

def test_currency_spellings_are_normalised():
    c, _ = imp(HDR + "2024-06-03,A-1,B-2,100.00,Euro\n2024-06-04,B-2,C-3,100.00,EUR\n")
    _, flags = ty.analyse_case(ci.CaseInput("x", c))
    assert not any(f.code == "CROSS_CURRENCY" for f in flags)


def test_cp1252_file_keeps_accents():
    data = (HDR.replace("Amount", "Beneficiary,Amount")
            + "2024-06-03,A-1,B-2,Société Générale,100.00,EUR\n").encode("cp1252")
    c, issues = imp(data)
    assert "Société" in c["To_Entity_Name"][0] or any("encod" in i["message"].lower() for i in issues)


def test_duplicate_rows_are_warned():
    _, issues = imp(HDR + "2024-06-03,A-1,B-2,100.00,USD\n2024-06-03,A-1,B-2,100.00,USD\n")
    assert any("duplicate" in i["message"].lower() for i in issues)


# ── EC-12: validation ────────────────────────────────────────────────────────

def test_prior_sar_statement_is_not_a_no_sar_conclusion():
    text = "\n\n".join(f"### {h}\n\nNo SAR has previously been filed on this subject."
                       for h in ["Who", "What", "When", "Where", "Why Suspicious"])
    assert not g.validate_narrative(text, "stop", "GATHER-SCATTER", no_sar=False)


# ── EC-13 … EC-17: parsing details ───────────────────────────────────────────

def test_cfr_citation_is_not_an_amount(northgate_case):
    _, unverified = _facts(northgate_case, "The filing is required under 31 CFR 1020.320.")
    assert not unverified


def test_scaled_amount_words(northgate_case):
    _, unverified = _facts(northgate_case, "Deposits totalled $68.15 thousand.")
    assert not unverified


def test_impossible_date_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "The wire was sent on June 31, 2024.")
    assert unverified


def test_bank_name_matches_whole_words_only():
    case = ci.CaseInput("C", txns([dict(ts="2024/06/03 10:00", frm="A-1", to="B-2", amt=100.0,
                                        tbn="Chase")]))
    refs, _ = _facts(case, "The subject purchased goods online.")
    assert not refs


def test_abbreviations_do_not_split_sentences():
    sents = at.parse_narrative_into_sentences(
        "### What\n\nFunds went to U.S. accounts held by Mr. Kumar. He then wired $9,800.00 abroad.")
    assert len(sents) == 2


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


# ── Regression guards added with the fixes ──────────────────────────────────

@pytest.mark.parametrize("sentence", [
    "NG-4471 received seven cash deposits totaling $68,150.00 between June 3 and June 6, 2024.",
    "NG-4471 wired $38,000.00 to AE-77120 on June 6, 2024.",
    "The subject executed two international wire transfers totaling $67,500.00 to AE-77120 "
    "and CY-50831.",
    "Lumen Trade FZE received $38,000.00 from NG-4471.",
    "Each deposit was kept just below the $10,000 threshold.",
])
def test_correct_relationships_are_not_flagged(northgate_case, sentence):
    _, unverified = _facts(northgate_case, sentence)
    assert not unverified


@pytest.mark.parametrize("sentence", [
    "CY-50831 received $38,000.00 from NG-4471.",
    "NG-4471 received $38,000.00 in cash from Lumen Trade FZE.",
])
def test_wrong_relationships_are_flagged(northgate_case, sentence):
    _, unverified = _facts(northgate_case, sentence)
    assert any(u.field_name == "Relationship" for u in unverified)


def test_relative_negation_is_left_for_review(northgate_case):
    sentence = "NG-4471 did not receive any cash deposits before June 2024."
    refs, unverified = _facts(northgate_case, sentence)
    assert not unverified and at.needs_review(sentence, refs)


def test_currency_sign_on_foreign_amount_is_flagged(northgate_case):
    _, unverified = _facts(northgate_case, "NG-4471 wired $38,000.00 EUR to AE-77120.")
    assert unverified and "currency" in unverified[0].note


def test_dollar_family_currency_is_not_a_sign_error():
    case = ci.CaseInput("AUD", txns([dict(ts="2024/06/03 10:00", frm="AU-1", to="AU-2",
                                          amt=4352.31, ccy="Australian Dollar")]))
    _, unverified = _facts(case, "AU-1 sent $4,352.31 AUD to AU-2.")
    assert not unverified


def test_wrong_currency_hint_names_the_real_currency():
    rows = [dict(ts="2024/02/10 16:00", frm="FR-900", to="CY-777", amt=74000.00, ccy="Euro")]
    _, unverified = _facts(ci.CaseInput("E", txns(rows)), "The wire was $74,000.00.")
    assert "wrong currency" in unverified[0].note and "EUR" in unverified[0].note


@pytest.mark.parametrize("sentence, flagged", [
    ("Funds went to ab-12345 at another bank.", True),        # invented lowercase ID
    ("Pattern: FAN-OUT (150-degree).", False),                # a measurement, not an ID
    ("There were thirty-one transfers in total.", True),       # 21 exist, not 31
    ("A dozen deposits were made.", True),
    ("NG-4471 received deposits from 9 unique originating accounts.", True),  # 5 do
    ("The activity occurred over a four-day period.", False),
    ("The activity spanned five calendar days.", False),
    ("Banks must file under 12 CFR 21.11 within 30 days.", False),
    ("Deposits totalled roughly $68.2 thousand.", False),
    ("The funds went through 12 banks.", True),               # bank counts are checked too
])
def test_fact_check_phrasings(northgate_case, sentence, flagged):
    _, unverified = _facts(northgate_case, sentence)
    assert bool(unverified) == flagged


def test_year_less_dates_across_new_year():
    rows = [dict(ts="2023/12/28 10:00", frm="YB-1", to="YB-HUB", amt=4100.0),
            dict(ts="2024/01/02 09:00", frm="YB-3", to="YB-HUB", amt=4400.0)]
    case = ci.CaseInput("YB", txns(rows))
    assert not _facts(case, "Deposits arrived on December 28 and January 2.")[1]
    assert _facts(case, "A deposit arrived on December 29.")[1]


def test_override_reason_reaches_the_prompt(northgate_case):
    northgate_case.pattern_override = "CYCLE"
    northgate_case.override_reason = "funds return via an account outside this export"
    d, flags = ty.analyse_case(northgate_case)
    block = g.format_case_file(northgate_case, d, flags)
    assert "TYPOLOGY: CYCLE, selected by the analyst" in block and "GATHER-SCATTER" in block
    assert "RULE-BASED TYPOLOGY DETECTION" not in block        # no conflicting evidence
    directive = g._directive_for(northgate_case, "CYCLE", d, flags)
    assert "classified this activity as CYCLE" in directive and "outside this export" in directive


def test_cumulative_total_reaches_the_case_file(northgate_case):
    northgate_case.prior_sars = [ci.PriorSAR(filed_on="2024-03-01", reference="BSA-1", amount=41200.0)]
    d, flags = ty.analyse_case(northgate_case)
    assert "Cumulative including prior SARs: $109,350.00" in g.format_case_file(northgate_case, d, flags)


def test_import_hygiene_warnings():
    text = ("Export generated 2024-06-30\nAccount: 5500123456\n\n" + HDR
            + "2024-06-03,ng-4471,B-2,100.00,USD\n2024-06-04,NG-4471,NG-4471,0.00,USD\n")
    c, issues = imp(text)
    messages = " ".join(i["message"] for i in issues)
    assert len(c) == 2 and set(c["From_Account"]) == {"NG-4471"}
    for word in ("Skipped 3 line(s)", "Merged account IDs", "to itself", "zero amount"):
        assert word in messages


def test_ambiguous_dates_are_warned():
    _, issues = imp(HDR + "01/02/2024,A-1,B-2,100.00,USD\n03/04/2024,A-1,B-2,100.00,USD\n")
    assert any("either way" in i["message"] for i in issues)


def test_validation_warnings():
    good = "\n\n".join(f"### {h}\n\nText." for h in
                        ["Who", "What", "When", "Where", "Why Suspicious"])
    warnings = g.draft_warnings(good)
    assert any("How, Supporting Pattern, Quantitative Summary" in w for w in warnings)
    assert any("alternative explanations" in w for w in warnings)
    assert g.validate_narrative("### Whole picture\n\nText.")          # not a Who heading


def test_no_sar_regex_matches_conclusions_only():
    assert g.NO_SAR_PATTERN.search("Therefore, this activity does not warrant a SAR filing.")
    assert g.NO_SAR_PATTERN.search("A SAR is not warranted.")
    assert not g.NO_SAR_PATTERN.search("Further review of the card settlements is not warranted.")


def test_models_are_local_and_reachable(monkeypatch):
    monkeypatch.setattr(g, "PRIMARY_MODEL", "gemma4:31b-cloud")
    with pytest.raises(g.NarrativeGenerationError, match="local-first"):
        g.check_models()
    monkeypatch.setattr(g, "PRIMARY_MODEL", "gemma4:e2b")
    monkeypatch.setattr(g, "OLLAMA_URL", "http://127.0.0.1:9")
    with pytest.raises(g.NarrativeGenerationError, match="not reachable"):
        g.check_models()


def test_empty_case_is_refused_and_prompt_has_no_nan():
    empty = ci.CaseInput("E", ci.empty_transactions())
    with pytest.raises(g.NarrativeGenerationError, match="no transactions"):
        g.prepare_generation(empty)
    assert "nan" not in g.format_transaction_data(empty, "NONE", ty.detect_typology(empty.flagged()))


@pytest.mark.parametrize("ccy, amounts, flagged", [
    ("Euro", [9800.0, 9750.0, 9900.0], True),
    ("Rupee", [950_000.0, 980_000.0], True),
    ("UK Pound", [9800.0, 9750.0, 9900.0], False),          # no single UK threshold
])
def test_structuring_thresholds_by_currency(ccy, amounts, flagged):
    rows = [dict(ts=f"2024/06/0{i + 3} 10:00", frm=f"S{i}", to="R", amt=a, ccy=ccy, fmt="Cash")
            for i, a in enumerate(amounts)]
    _, flags = ty.analyse_case(ci.CaseInput("X", txns(rows)))
    assert any(f.code == "STRUCTURING" for f in flags) == flagged


def test_bold_section_heading_is_a_heading():
    sents = at.parse_narrative_into_sentences(
        "**Who (Subject Identification)**\n\nNorthgate Auto Parts LLC holds NG-4471.")
    assert sents and sents[0].section == "Who"


def test_relationship_is_read_from_the_amounts_clause(northgate_case):
    sentence = ("The funds were introduced via seven cash deposits, which were aggregated into "
                "account NG-4471, followed by the disbursement of $67,500.00 via two international "
                "wire transfers to foreign accounts.")
    assert not _facts(northgate_case, sentence)[1]


def test_continuing_directive_gives_the_exact_citation(northgate_case):
    northgate_case.prior_sars = [ci.PriorSAR(filed_on="2024-03-01", reference="BSA-31000000123456",
                                             amount=41200.0)]
    sentence = g.continuing_sentence(northgate_case)
    assert sentence == ("This is a continuing-activity SAR: SAR BSA-31000000123456, filed on "
                        "March 1, 2024, reported $41,200.00; including this period's $68,150.00, "
                        "the cumulative total is $109,350.00.")
    d, flags = ty.analyse_case(northgate_case)
    assert sentence in g._directive_for(northgate_case, d.pattern, d, flags)
    assert not _facts(northgate_case, sentence)[1]            # every figure in it verifies
    warnings = g.draft_warnings("### Why Suspicious\n\n" + sentence, northgate_case.prior_sars)
    assert not any("prior SAR" in w for w in warnings)        # the sentence counts as a citation
