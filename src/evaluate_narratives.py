"""
evaluate_narratives.py — Batch generate and structurally evaluate SAR narratives.

Generates narratives for all 13 evaluation cases (excluding 3 few-shot cases),
then scores each for FFIEC structural completeness.

Milestone 3: Generation now automatically produces audit trails (JSON + provenance
reports) alongside narratives. Use --audit to retroactively build audit trails
for existing generated narratives.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from generate_narrative import (
    CASE_TO_ATTEMPT,
    FEW_SHOT_CASE_IDS,
    generate_and_save,
    GENERATED_DIR,
)


# FFIEC required elements — presence is binary pass/fail
REQUIRED_SECTIONS = [
    "Who",
    "What",
    "When",
    "Where",
    "Why Suspicious",
]

# Expected sections — contribute to score but not hard failures
EXPECTED_SECTIONS = [
    "How",
    "Supporting Pattern",
    "Quantitative Summary",
]

ALL_SECTIONS = REQUIRED_SECTIONS + EXPECTED_SECTIONS


def score_narrative(filepath: Path) -> dict:
    """
    Score a generated narrative for structural completeness.

    Returns dict with section presence, required score, and total score.
    """
    content = filepath.read_text(encoding="utf-8")

    results = {}
    for section in ALL_SECTIONS:
        # Look for ### Section Name or ## Section Name (with variations)
        pattern = rf"###?\s*{re.escape(section)}"
        results[section] = bool(re.search(pattern, content, re.IGNORECASE))

    required_present = sum(1 for s in REQUIRED_SECTIONS if results[s])
    expected_present = sum(1 for s in EXPECTED_SECTIONS if results[s])
    total_present = required_present + expected_present

    return {
        "sections": results,
        "required_score": required_present / len(REQUIRED_SECTIONS) * 100,
        "expected_score": expected_present / len(EXPECTED_SECTIONS) * 100,
        "total_score": total_present / len(ALL_SECTIONS) * 100,
        "required_count": f"{required_present}/{len(REQUIRED_SECTIONS)}",
        "total_count": f"{total_present}/{len(ALL_SECTIONS)}",
    }


def run_evaluation(skip_existing: bool = False, build_audit: bool = False):
    """Generate and evaluate all 13 evaluation cases."""

    eval_cases = {
        k: v for k, v in CASE_TO_ATTEMPT.items()
        if k not in FEW_SHOT_CASE_IDS
    }

    print(f"=== SAR Narrative Evaluation ===")
    print(f"Evaluation set: {len(eval_cases)} cases")
    print(f"Few-shot (excluded): {sorted(FEW_SHOT_CASE_IDS)}")
    print(f"Model: gemma4:e2b (fallback: qwen3.5:4b)")
    if build_audit:
        print(f"Audit trail: enabled (will build for existing narratives)")
    print()

    # Phase 1: Generate
    print("--- Phase 1: Generation ---")
    skipped_cases = []
    for case_id, attempt_id in sorted(eval_cases.items()):
        output_path = GENERATED_DIR / f"{case_id}_generated.md"
        if skip_existing and output_path.exists():
            content = output_path.read_text(encoding="utf-8")
            # Check if it has actual narrative content (not just header)
            if len(content) > 200:
                print(f"  Case {case_id}: skipping (already exists)", flush=True)
                skipped_cases.append(case_id)
                continue

        print(f"\n  Case {case_id} (attempt #{attempt_id}):", flush=True)
        start = time.time()
        try:
            generate_and_save(attempt_id, case_id)
            elapsed = time.time() - start
            print(f"    Generated in {elapsed:.1f}s", flush=True)
        except Exception as e:
            print(f"    FAILED: {e}", flush=True)

    # Phase 1b: Build audit trails for skipped cases (if --audit)
    if build_audit and skipped_cases:
        print(f"\n--- Phase 1b: Building Audit Trails (skipped cases) ---")
        from src.build_audit_trails import build_audit_for_case
        for case_id in skipped_cases:
            print(f"\n  Case {case_id}:")
            build_audit_for_case(case_id)

    # Phase 2: Score
    print("\n--- Phase 2: Structural Evaluation ---\n")

    header = f"{'Case':>6} | {'Pattern':>18} | {'Req':>5} | {'Exp':>5} | {'Total':>5} | {'Sections'}"
    print(header)
    print("-" * len(header))

    all_scores = []
    for case_id in sorted(eval_cases.keys()):
        output_path = GENERATED_DIR / f"{case_id}_generated.md"
        if not output_path.exists():
            print(f"  {case_id:>4} | {'MISSING':>18} | {'N/A':>5} | {'N/A':>5} | {'N/A':>5} |")
            continue

        scores = score_narrative(output_path)
        all_scores.append(scores)

        # Get pattern from the file
        content = output_path.read_text(encoding="utf-8")
        pattern_match = re.search(r"\*\*Pattern:\*\*\s*(\S+)", content)
        pattern = pattern_match.group(1) if pattern_match else "?"

        # Section presence indicators
        section_indicators = ""
        for s in ALL_SECTIONS:
            section_indicators += "✓" if scores["sections"][s] else "✗"

        print(
            f"  {case_id:>4} | {pattern:>18} | "
            f"{scores['required_score']:5.0f}% | "
            f"{scores['expected_score']:5.0f}% | "
            f"{scores['total_score']:5.0f}% | "
            f"{section_indicators}"
        )

    # Aggregate
    if all_scores:
        avg_required = sum(s["required_score"] for s in all_scores) / len(all_scores)
        avg_total = sum(s["total_score"] for s in all_scores) / len(all_scores)
        perfect_required = sum(1 for s in all_scores if s["required_score"] == 100)

        print()
        print(f"Section key: {''.join(s[0] for s in ALL_SECTIONS)}")
        print(f"             W=Who, W=What, W=When, W=Where, W=Why, H=How, S=Supporting, Q=Quantitative")
        print()
        print(f"=== Aggregate Results ===")
        print(f"  Cases evaluated: {len(all_scores)}")
        print(f"  Required elements (5) avg:  {avg_required:.1f}%  (target: ≥90%)")
        print(f"  All elements (8) avg:       {avg_total:.1f}%  (target: ≥75%)")
        print(f"  Perfect required score:     {perfect_required}/{len(all_scores)} cases")

        # Pass/fail
        req_pass = "✓ PASS" if avg_required >= 90 else "✗ FAIL"
        total_pass = "✓ PASS" if avg_total >= 75 else "✗ FAIL"
        print(f"\n  Required ≥90%: {req_pass}")
        print(f"  Total ≥75%:    {total_pass}")


if __name__ == "__main__":
    import sys

    skip = "--skip-existing" in sys.argv
    audit = "--audit" in sys.argv
    run_evaluation(skip_existing=skip, build_audit=audit)

