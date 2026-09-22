"""
build_audit_trails.py — Build audit trails for existing generated narratives.

Reads each generated narrative from generated/, retrieves the same typology
context that would have been used during generation, and constructs
sentence-level provenance records without re-running the LLM.

Usage:
    python -m src.build_audit_trails              # all cases
    python -m src.build_audit_trails 002 005 010  # specific cases
    python -m src.build_audit_trails --store-db   # also store in PostgreSQL
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from audit_trail import (
    AuditRecord,
    build_audit_record,
    save_audit_record,
    save_provenance_report,
    generate_provenance_report,
    AUDIT_DIR,
)
from src.generate_narrative import (
    CASE_TO_ATTEMPT,
    FEW_SHOT_CASE_IDS,
    GENERATED_DIR,
    PRIMARY_MODEL,
    FALLBACK_MODEL,
    retrieve_context_with_metadata,
)
from data_loader import get_attempt


def build_audit_for_case(
    case_id: str,
    verbose: bool = True,
) -> AuditRecord | None:
    """
    Build an audit trail for an existing generated narrative.

    Reads the narrative from generated/{case_id}_generated.md,
    retrieves the same typology context, and constructs the audit record.
    """
    attempt_id = CASE_TO_ATTEMPT.get(case_id)
    if attempt_id is None:
        if verbose:
            print(f"  ✗ Unknown case ID: {case_id}")
        return None

    # Read the existing generated narrative
    narrative_path = GENERATED_DIR / f"{case_id}_generated.md"
    if not narrative_path.exists():
        if verbose:
            print(f"  ✗ No generated narrative for case {case_id}")
        return None

    content = narrative_path.read_text(encoding="utf-8")

    # Extract just the narrative text (skip the header block)
    # Header ends at the first "---" after the metadata
    parts = content.split("---", 2)
    if len(parts) >= 3:
        narrative_text = parts[2].strip()
    else:
        narrative_text = content

    # Detect which model was used from the header
    model_match = re.search(r"\*\*Model:\*\*\s*(\S+)", content)
    model_used = model_match.group(1) if model_match else PRIMARY_MODEL

    if verbose:
        print(f"  Retrieving typology context for attempt #{attempt_id}...", flush=True)

    # Retrieve the same context that would have been used
    start = time.time()
    _, retrieval_meta, chunk_texts = retrieve_context_with_metadata(attempt_id)
    retrieval_time = time.time() - start

    if verbose:
        print(f"  Retrieved {len(retrieval_meta.chunks_returned)} chunks in {retrieval_time:.1f}s", flush=True)

    # Load transaction data
    txn_df = get_attempt(attempt_id)
    pattern = txn_df.iloc[0]["pattern_type"]

    # Build the audit record
    audit_record = build_audit_record(
        case_id=case_id,
        attempt_id=attempt_id,
        pattern_type=pattern,
        model_used=model_used,
        generation_time=0.0,  # unknown for pre-existing narratives
        narrative_text=narrative_text,
        retrieval_metadata=retrieval_meta,
        chunk_texts=chunk_texts,
        txn_df=txn_df,
    )

    # Save
    audit_path = save_audit_record(audit_record)
    report_path = save_provenance_report(audit_record)

    if verbose:
        # Quick stats
        grounded = sum(
            1 for s in audit_record.narrative_sentences
            if s.field_references or s.chunk_attributions
        )
        total = len(audit_record.narrative_sentences)
        print(f"  → {total} sentences, {grounded} grounded ({grounded/max(total,1)*100:.0f}%)")
        print(f"  → Saved: {audit_path.name}, {report_path.name}")

    return audit_record


def run_all(
    case_ids: list[str] | None = None,
    store_db: bool = False,
    verbose: bool = True,
) -> None:
    """Build audit trails for all (or specified) generated narratives."""

    if case_ids is None:
        # All cases that have generated narratives
        case_ids = sorted(
            cid for cid in CASE_TO_ATTEMPT.keys()
            if (GENERATED_DIR / f"{cid}_generated.md").exists()
        )

    print(f"=== Building Audit Trails ===")
    print(f"Cases: {len(case_ids)}")
    print(f"Output: {AUDIT_DIR}/")
    print()

    results = []
    for case_id in case_ids:
        print(f"Case {case_id} (attempt #{CASE_TO_ATTEMPT.get(case_id, '?')}):")
        audit = build_audit_for_case(case_id, verbose=verbose)
        if audit:
            results.append((case_id, audit))
        print()

    # Store in PostgreSQL if requested
    if store_db and results:
        print("--- Storing in PostgreSQL ---")
        try:
            from db import init_db, insert_case
            init_db()
            for case_id, audit in results:
                narrative_path = GENERATED_DIR / f"{case_id}_generated.md"
                narrative = narrative_path.read_text(encoding="utf-8")
                row_id = insert_case(
                    case_id=case_id,
                    attempt_id=audit.attempt_id,
                    pattern_type=audit.pattern_type,
                    narrative_text=narrative,
                    audit_record=audit,
                )
                print(f"  Case {case_id} → row {row_id}")
            print(f"  ✓ {len(results)} cases stored in PostgreSQL")
        except Exception as e:
            print(f"  ✗ PostgreSQL storage failed: {e}")
            print(f"    (Run 'docker compose up -d' first, then retry with --store-db)")

    # Summary
    print("=== Summary ===")
    total_sentences = 0
    total_grounded = 0
    total_ungrounded = 0
    for case_id, audit in results:
        for sent in audit.narrative_sentences:
            total_sentences += 1
            if sent.field_references or sent.chunk_attributions:
                total_grounded += 1
            else:
                total_ungrounded += 1

    print(f"Cases processed:    {len(results)}")
    print(f"Total sentences:    {total_sentences}")
    print(f"Grounded:           {total_grounded} ({total_grounded/max(total_sentences,1)*100:.0f}%)")
    print(f"Ungrounded:         {total_ungrounded} ({total_ungrounded/max(total_sentences,1)*100:.0f}%)")
    print(f"Audit records:      {AUDIT_DIR}/")


if __name__ == "__main__":
    args = sys.argv[1:]
    store_db = "--store-db" in args
    case_ids_arg = [a for a in args if not a.startswith("--")]

    run_all(
        case_ids=case_ids_arg if case_ids_arg else None,
        store_db=store_db,
    )
