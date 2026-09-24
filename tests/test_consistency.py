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
