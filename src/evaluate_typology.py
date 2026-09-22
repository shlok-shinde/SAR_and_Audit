"""
evaluate_typology.py — Score the rule-based typology detector against IBM labels.

Every one of the 370 laundering attempts in the enriched parquet has a
ground-truth pattern label. The detector never sees it; we run
`detect_typology()` on the attempt's transactions and compare.

Attempts with at most two distinct account links are reported separately:
one transfer (A → B) is simultaneously a 1-degree fan-out, fan-in and bipartite
pair, so no method can recover the label from the data alone.

Usage:
    python src/evaluate_typology.py            # print report
    python src/evaluate_typology.py --write    # also update docs/EVALUATION.md
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_input import normalise_frame  # noqa: E402
from data_loader import PARQUET_OUT  # noqa: E402
from typology import DATASET_EQUIVALENT, PATTERNS, build_graph, detect_red_flags, detect_typology  # noqa: E402

DOC = Path(__file__).resolve().parent.parent / "docs" / "EVALUATION.md"
START, END = "<!-- typology-eval:start -->", "<!-- typology-eval:end -->"


def run() -> dict:
    df = pd.read_parquet(PARQUET_OUT)
    rows = []
    for attempt_id, g in df.groupby("attempt_id"):
        label = g["pattern_type"].iloc[0]
        truth = DATASET_EQUIVALENT.get(label, label)
        txns = normalise_frame(g.drop(columns=["attempt_id", "pattern_type", "degree_info"]))
        det = detect_typology(txns)
        flags = detect_red_flags(txns)
        rows.append({
            "attempt_id": attempt_id, "label": label, "truth": truth,
            "predicted": det.pattern, "confidence": det.confidence,
            "links": build_graph(txns).number_of_edges(),
            "high_flags": sum(f.severity == "high" for f in flags),
            "flags": ",".join(sorted({f.code for f in flags})),
        })
    return {"rows": pd.DataFrame(rows)}


def report(res: dict) -> str:
    r = res["rows"]
    r["correct"] = r["truth"] == r["predicted"]
    clear = r[r["links"] > 2]
    ambiguous = r[r["links"] <= 2]
    lines = [
        f"**Typology detector vs IBM labels** (`src/evaluate_typology.py`, "
        f"{len(r)} attempts; RANDOM ≡ NONE)",
        "",
        "| Subset | Attempts | Correct | Accuracy |",
        "|---|---|---|---|",
        f"| All | {len(r)} | {int(r['correct'].sum())} | {r['correct'].mean():.1%} |",
        f"| Structured (≥3 account links) | {len(clear)} | {int(clear['correct'].sum())} | "
        f"{clear['correct'].mean():.1%} |",
        f"| Ambiguous (≤2 links) | {len(ambiguous)} | {int(ambiguous['correct'].sum())} | "
        f"{ambiguous['correct'].mean():.1%} |",
        "",
        "**Per pattern (structured subset)**",
        "",
        "| Pattern | Attempts | Recall | Precision |",
        "|---|---|---|---|",
    ]
    for p in PATTERNS:
        truth = clear[clear["truth"] == p]
        pred = clear[clear["predicted"] == p]
        if truth.empty and pred.empty:
            continue
        recall = truth["correct"].mean() if len(truth) else float("nan")
        precision = pred["correct"].mean() if len(pred) else float("nan")
        lines.append(f"| {p} | {len(truth)} | {recall:.0%} | {precision:.0%} |")
    lines += ["", "**Confusion matrix (structured subset; rows = label, columns = predicted)**", ""]
    cm = pd.crosstab(clear["truth"], clear["predicted"])
    lines.append("| label \\ predicted | " + " | ".join(cm.columns) + " |")
    lines.append("|---" * (len(cm.columns) + 1) + "|")
    for label, row in cm.iterrows():
        lines.append(f"| {label} | " + " | ".join(str(v) for v in row.values) + " |")
    misses = clear[~clear["correct"]]
    if not misses.empty:
        lines += ["", "Misclassified structured attempts: " + ", ".join(
            f"#{a} ({t}→{p})" for a, t, p in
            misses[["attempt_id", "truth", "predicted"]].itertuples(index=False))]
    none = r[r["truth"] == "NONE"]
    lines += [
        "",
        f"**Negative controls:** {int((none['high_flags'] > 0).sum())} of {len(none)} RANDOM "
        "attempts raise a high-severity red flag (a high flag would stop the draft from "
        "concluding \"no SAR\").",
        "",
        "Red flags raised across all attempts: " + ", ".join(
            f"{k} {v}" for k, v in Counter(
                c for f in r["flags"] if f for c in f.split(",")).most_common()),
    ]
    return "\n".join(lines)


def write_doc(text: str) -> None:
    body = DOC.read_text(encoding="utf-8")
    block = f"{START}\n{text}\n{END}"
    if START in body:
        head, rest = body.split(START, 1)
        body = head + block + rest.split(END, 1)[1]
    else:
        body = body.rstrip() + "\n\n---\n\n## Typology Detection Accuracy\n\n" + block + "\n"
    DOC.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    text = report(run())
    print(text)
    if "--write" in sys.argv:
        write_doc(text)
        print(f"\nUpdated {DOC}")
