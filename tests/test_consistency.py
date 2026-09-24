"""Consistency across sentences after a reviewer edit.

Each sentence is fact-checked against the case data on its own, so an edit can
leave the draft disagreeing with itself (a value changed in one place only), with
the case's typology, or with the analyst's SAR / No SAR decision.
"""
from pathlib import Path

import pytest

import audit_trail as at
import generate_narrative as g
import typology as ty

ROOT = Path(__file__).resolve().parent.parent

DRAFT = """### What (Suspicious Activity)

NG-4471 received $68,150.00 in cash deposits between June 3, 2024 and June 21, 2024.

### Quantitative Summary

Cash deposits totalled $68,150.00, and the last deposit was on June 21, 2024.
"""


def _notes(before: str, after: str) -> dict[int, list[str]]:
    base = at.parse_narrative_into_sentences(before)
    cur = at.parse_narrative_into_sentences(after)
    changes, _ = at.diff_provenance(base, cur)
    return at.stale_mentions(cur, changes)


# ── Values changed in one sentence only ──────────────────────────────────────

def test_changed_amount_points_at_other_sentence():
    notes = _notes(DRAFT, DRAFT.replace("$68,150.00", "$88,150.00", 1))
    assert list(notes) == [1]
    assert "Still says $68,150.00" in notes[1][0] and "to $88,150.00 in S0" in notes[1][0]


def test_changed_date_points_at_other_sentence():
    notes = _notes(DRAFT, DRAFT.replace("June 21, 2024", "June 24, 2024", 1))
    assert list(notes) == [1] and "June 21, 2024" in notes[1][0]


def test_no_note_once_every_copy_is_changed():
    assert _notes(DRAFT, DRAFT.replace("$68,150.00", "$88,150.00")) == {}


def test_edits_that_keep_the_values_raise_no_note():
    assert _notes(DRAFT, DRAFT.replace("cash deposits between", "cash deposits from", 1)) == {}


def test_changed_identifier_points_at_other_sentence():
    text = ("### What\n\nAccount 8001BB380 sent ten ACH transfers.\n\n"
            "### Who\n\nThe subject holds account 8001BB380.\n")
    notes = _notes(text, text.replace("8001BB380", "8001BB381", 1))
    assert list(notes) == [1] and "8001BB380" in notes[1][0]


# ── A different typology named ───────────────────────────────────────────────

def test_other_typology_flagged():
    # Case 003 (FAN-IN), stored evaluation draft
    s = ("This pattern is consistent with the mechanism described in the Gather-Scatter "
         "typology, where funds are collected from multiple accounts into one.")
    assert "GATHER-SCATTER" in at.typology_mismatch(s, "FAN-IN")
    assert "no typology was detected" in at.typology_mismatch("Consistent with a fan-out.", "NONE")


@pytest.mark.parametrize("sentence,pattern", [
    ("Pattern: GATHER-SCATTER (10-degree Fan-In/11-degree Fan-Out).", "GATHER-SCATTER"),
    ("The chain shows no return-to-origin at any point, ruling out CYCLE.", "RANDOM"),
    ("This is a fan-out rather than a cycle.", "FAN-OUT"),
    ("A cycle was ruled out.", "STACK"),
    ("Statements follow a monthly billing cycle.", "FAN-OUT"),
    ("Funds moved in a cycle back to the originator.", "CYCLE"),
])
def test_legitimate_typology_mentions(sentence, pattern):
    assert at.typology_mismatch(sentence, pattern) == ""


def test_gold_narratives_raise_no_typology_mismatch():
    for path in sorted((ROOT / "narratives").glob("*.md")):
        pattern = path.stem[4:].upper().replace("_", "-")[:-2]
        for s in at.parse_narrative_into_sentences(path.read_text()):
            assert at.typology_mismatch(s.sentence_text, pattern) == "", (path.name, s.sentence_text)


def test_typology_mismatch_marks_sentence_for_review(northgate_case):
    d, flags = ty.analyse_case(northgate_case)
    text = ("### Why Suspicious\n\nNG-4471 received $68,150.00 in cash, consistent with a "
            "bipartite scheme.")
    rec = at.build_audit_record("NG", None, "FAN-IN", "m", 0, text, None, {},
                                northgate_case.transactions, case_facts=northgate_case.case_facts(),
                                detection=d.to_dict(), red_flags=flags)
    sent = rec.narrative_sentences[0]
    assert "BIPARTITE" in sent.needs_review and at.grounding_status(sent) != "grounded"


# ── Conclusion versus the decision ───────────────────────────────────────────

NO_SAR = "The activity does not warrant a SAR filing."
SUSPICIOUS = "The activity is consistent with structuring."


@pytest.mark.parametrize("text,decision_no_sar,expected", [
    (SUSPICIOUS, False, ""),
    (NO_SAR, True, ""),
    (NO_SAR, False, "decision is File SAR"),
    (SUSPICIOUS, True, "never states"),
])
def test_conclusion_versus_decision(text, decision_no_sar, expected):
    result = g.conclusion_mismatch(text, decision_no_sar)
    assert (expected in result) if expected else result == ""


# ── The card's Typology line ─────────────────────────────────────────────────

@pytest.mark.parametrize("sentence,pattern,expected", [
    # "structuring" used to be labelled FAN-OUT, in a FAN-IN case (stored case 003, S11)
    ("Structural grounding: FinCEN Case Example, July 2014, Case 7 "
     "(structuring/aggregation into a single account).", "FAN-IN", None),
    ("Pattern: GATHER-SCATTER (13-degree Fan-In).", "GATHER-SCATTER", "GATHER-SCATTER"),
    ("The chain shows no return-to-origin at any point, ruling out CYCLE.", "RANDOM", None),
    ("Funds were aggregated in a fan-in.", "FAN-IN", "FAN-IN"),
])
def test_named_typology(sentence, pattern, expected):
    assert at.named_typology(sentence, pattern) == expected


# ── Countries named in the narrative ─────────────────────────────────────────

def _country_case(banks, ccy="US Dollar", countries=("", "")):
    import pandas as pd
    import case_input as ci
    rows = [{"Timestamp": f"2022/09/0{i + 1} 10:00", "From_Account": f"A{i}", "To_Account": "HUB1",
             "From_Bank_Name": b, "To_Bank_Name": banks[0], "From_Entity_Name": "", "To_Entity_Name": "",
             "Amount Paid": 100.0 + i, "Payment Currency": ccy, "Amount Received": 100.0 + i,
             "Receiving Currency": ccy, "Payment Format": "ACH", "Flagged": True, "Txn_ID": f"T{i}",
             "From_Country": countries[0], "To_Country": countries[1]}
            for i, b in enumerate(banks)]
    return ci.normalise_frame(pd.DataFrame(rows))


def _countries(df, sentence):
    refs, unverified = at.check_sentence_facts(sentence, df, None, at.FactIndex(df))
    return ([r.field_value for r in refs if r.match_type == "country"],
            [(u.field_value, u.note) for u in unverified if u.field_name == "Country"])


def test_country_not_in_case_is_unverified():
    # Case 012 edit: China -> India, where the banks are China/Germany/Finland/France + a US bank
    df = _country_case(["Germany Bank #65", "China Bank #6", "Finland Bank #0", "France Bank #51",
                        "National Bank of Laramie"])
    ok, bad = _countries(df, "Activity spans the United States, Germany, India, Finland, and France.")
    assert [b for b, _ in bad] == ["India"] and "China" in bad[0][1]
    assert len(ok) == 4
    ok, bad = _countries(df, "Activity spans the United States, Germany, China, Finland, and France.")
    assert bad == [] and len(ok) == 5


def test_country_sources():
    # ISO codes in the country columns, a single-country currency, a ruled-out mention
    df = _country_case(["Harbor Bank"], ccy="Rupee", countries=("AE", "GB"))
    ok, bad = _countries(df, "Funds moved from the UAE to the United Kingdom and India.")
    assert bad == [] and len(ok) == 3
    assert _countries(df, "No transfers involved Iran.") == ([], [])


def test_unnumbered_bank_is_american_only_in_ibm_style_data():
    real_names = _country_case(["Harbor Community Bank"], ccy="Euro")
    assert _countries(real_names, "Funds came from the United States.")[1]
    ibm = _country_case(["Germany Bank #65", "National Bank of the East"], ccy="Euro")
    assert _countries(ibm, "Funds came from the United States.")[1] == []
