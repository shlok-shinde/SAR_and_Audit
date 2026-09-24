import pandas as pd

import case_input as ci
import export
import generate_narrative as gn
import typology as ty

GOOD = "\n\n".join(f"### {h}\n\nText." for h in
                   ["Who (Subject Identification)", "What (Suspicious Activity)", "When (Timeframe)",
                    "Where (Location)", "Why Suspicious", "How (Method / Mechanism)",
                    "Supporting Pattern", "Quantitative Summary"])


def test_validation_rules():
    assert gn.validate_narrative(GOOD, "stop", "FAN-OUT") == []
    assert "model refused the task" in gn.validate_narrative("I cannot fulfill this request.")
    assert any("missing required" in p for p in gn.validate_narrative("### Who\n\nx"))
    assert any("cut off" in p for p in gn.validate_narrative(GOOD, "length"))
    assert any("does not warrant" in p for p in gn.validate_narrative(GOOD, "stop", no_sar=True))
    assert gn.validate_narrative(GOOD + " It does not warrant a SAR.", "stop", no_sar=True) == []
    # a positive case that concludes "no SAR" contradicts itself (stored case-006 draft)
    assert any("does not warrant a SAR although" in p for p in
               gn.validate_narrative(GOOD + " It does not warrant a SAR.", "stop", "CYCLE"))


def test_directives():
    assert "does not warrant" in gn.case_directive("RANDOM")          # backwards compatible
    assert gn.case_directive("FAN-OUT") == ""
    high = [ty.RedFlag("STRUCTURING", "t", "high", "e")]
    no_pattern_high = gn.case_directive("NONE", high)                 # a high flag blocks no-SAR…
    assert "does not warrant a SAR filing." not in no_pattern_high
    assert "high-severity red flags: t" in no_pattern_high            # …and says what to rely on
    assert "classified this activity as CYCLE" in gn.case_directive("CYCLE", detected="FAN-IN")
    assert "continuing-activity" in gn.case_directive("FAN-OUT", [], continuing=True)


def test_case_file_and_prompt_blocks(northgate_case):
    d, flags = ty.analyse_case(northgate_case)
    block = gn.format_case_file(northgate_case, d, flags)
    assert "Retail auto parts store" in block and "RED FLAGS" in block
    assert "Contacted the customer for an explanation" in block
    txt = gn.format_transaction_data(northgate_case, d.pattern, d)
    assert "SUBJECT" in txt and "OTHER ACCOUNT ACTIVITY" in txt
    assert "rule-based detection" in txt
    sample = ci.from_attempt(249)
    assert gn.format_case_file(sample, None, []) == ""                 # nothing analyst-provided
    assert "LAUNDERING ATTEMPT #249" in gn.format_transaction_data(sample, "CYCLE")


def test_large_logs_are_summarised():
    n = gn.MAX_LOG_ROWS + 40
    df = pd.DataFrame({"Timestamp": [f"2024/01/{1 + i % 28:02d} 10:00" for i in range(n)],
                       "From_Account": [f"A{i % 7}" for i in range(n)],
                       "To_Account": [f"B{i % 11}" for i in range(n)],
                       "Amount Paid": [100.0 + i for i in range(n)],
                       "Amount Received": [100.0 + i for i in range(n)],
                       "Payment Currency": "US Dollar", "Receiving Currency": "US Dollar"})
    case = ci.CaseInput("BIG", ci.normalise_frame(df))
    txt = gn.format_transaction_data(case, "NONE")
    assert f"summarised: {n} transactions" in txt and "LARGEST" in txt
    assert len(txt.splitlines()) < n


def test_prompt_fits_the_context_window(northgate_case):
    d, flags = ty.analyse_case(northgate_case)
    assert gn.estimate_prompt_tokens(northgate_case, d, flags) + gn.NUM_PREDICT < gn.NUM_CTX


def test_fincen_text_and_limits():
    text = export.fincen_narrative("### Who (Subject)\n\n**Name:** A *b*\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "WHO (SUBJECT)" in text and "**" not in text and "|" not in text and "1; 2" in text
    assert export.FINCEN_NARRATIVE_LIMIT == 17_000


def test_deadlines(northgate_case):
    assert export.filing_due("2024-06-10").isoformat() == "2024-07-10"
    northgate_case.prior_sars = [ci.PriorSAR(filed_on="2024-01-15", reference="BSA-1")]
    assert export.continuing_due(northgate_case.prior_sars).isoformat() == "2024-05-14"


def test_case_file_exports(northgate_case):
    import audit_trail as at
    d, flags = ty.analyse_case(northgate_case)
    rec = at.build_audit_record("NG", None, d.pattern, "m", 0, GOOD, None, {},
                                northgate_case.transactions, detection=d.to_dict(),
                                red_flags=flags, case_facts=northgate_case.case_facts())
    bundle = export.export_bundle(northgate_case, rec, GOOD, {"case_id": "NG", "status": "Approved"})
    assert "Retail auto parts store" in bundle["md"][1]
    assert bundle["html"][1].startswith("<!doctype html>") and "<script" not in bundle["html"][1]
    assert '"case_id": "NG"' in bundle["json"][1]
