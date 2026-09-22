import pandas as pd
import pytest

import case_input as ci
import typology as ty


def frame(edges, amount=1000.0, ccy="US Dollar", start="2024-01-01"):
    rows = []
    t = pd.Timestamp(start)
    for i, (a, b) in enumerate(edges):
        rows.append({"Timestamp": (t + pd.Timedelta(hours=i)).strftime(ci.TIMESTAMP_FORMAT),
                     "From_Account": a, "To_Account": b, "Amount Paid": amount,
                     "Amount Received": amount, "Payment Currency": ccy,
                     "Receiving Currency": ccy, "Payment Format": "ACH"})
    return ci.normalise_frame(pd.DataFrame(rows))


@pytest.mark.parametrize("edges,expected", [
    ([("H", f"R{i}") for i in range(5)], "FAN-OUT"),
    ([(f"S{i}", "H") for i in range(5)], "FAN-IN"),
    ([("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")], "CYCLE"),
    ([("S", f"M{i}") for i in range(4)] + [(f"M{i}", "T") for i in range(4)], "SCATTER-GATHER"),
    ([(f"F{i}", "H") for i in range(3)] + [("H", f"P{i}") for i in range(3)], "GATHER-SCATTER"),
    ([(f"A{i}", f"B{i}") for i in range(4)], "BIPARTITE"),
    ([(f"A{i}", f"M{i}") for i in range(3)] + [(f"M{i}", f"Z{i}") for i in range(3)], "STACK"),
    ([("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")], "NONE"),     # random walk / chain
])
def test_shapes(edges, expected):
    d = ty.detect_typology(frame(edges))
    assert d.pattern == expected
    assert d.evidence


def test_single_transfer_is_ambiguous():
    d = ty.detect_typology(frame([("A", "B")]))
    assert d.pattern == "NONE" and d.confidence == "low"
    assert {"FAN-OUT", "FAN-IN", "BIPARTITE"} <= set(d.alternatives)


def test_round_trip_scatter_gather():
    d = ty.detect_typology(frame([("H", "A"), ("A", "H"), ("H", "B"), ("B", "H")]))
    assert d.pattern == "SCATTER-GATHER"


def test_custom_case_detection_and_flags(northgate_case):
    d, flags = ty.analyse_case(northgate_case)
    assert d.pattern == "GATHER-SCATTER" and d.roles["NG-4471"] == "hub"
    codes = {f.code: f for f in flags}
    assert codes["STRUCTURING"].severity == "high"          # cash just under $10k
    assert "7 cash deposits" in codes["STRUCTURING"].evidence
    assert "99%" in codes["RAPID_PASS_THROUGH"].evidence
    assert "AE, CY" in codes["CROSS_BORDER"].evidence
    assert "4.5×" in codes["BASELINE_DEVIATION"].evidence    # vs unflagged May activity
    assert codes["PROFILE_MISMATCH"].severity == "medium"   # 1.7× expected volume
    assert not ty.warrants_no_sar(d.pattern, flags)


def test_high_risk_jurisdiction(northgate_case):
    df = northgate_case.transactions.copy()
    df.loc[df["To_Account"] == "AE-77120", "To_Country"] = "IR"
    flags = ty.detect_red_flags(df[df["Flagged"]])
    hr = [f for f in flags if f.code == "HIGH_RISK_JURISDICTION"]
    assert hr and hr[0].severity == "high" and "Iran" in hr[0].evidence


def test_new_account_flag(northgate_case):
    northgate_case.subject.account_opened = "2024-05-20"
    _, flags = ty.analyse_case(northgate_case)
    assert "NEW_ACCOUNT" in {f.code for f in flags}


def test_negative_controls_warrant_no_sar():
    for attempt in (329, 179):          # IBM RANDOM attempts (cases 015, 016)
        case = ci.from_attempt(attempt)
        d, flags = ty.analyse_case(case)
        assert d.pattern == "NONE"
        assert ty.warrants_no_sar(ty.effective_pattern(case, d), flags)


def test_analyst_override_wins(northgate_case):
    northgate_case.pattern_override = "FAN-IN"
    d, _ = ty.analyse_case(northgate_case)
    assert ty.effective_pattern(northgate_case, d) == "FAN-IN"
