"""
build_audit_trails.py — Rebuild audit trails for existing generated narratives.

Reads each draft from generated/, reconstructs the case exactly as generation
saw it — the same CaseInput, dataset-label pattern, rule-based detection and
red flags, and therefore the same pattern/flag-aware retrieval queries — and
rebuilds the sentence-level provenance record without re-running the LLM.

Facts only the generation run can know (how long it took, which model settings
it ran under, when it happened) are carried over from the audit record being
replaced instead of being reset to zero.

Usage:
    python src/build_audit_trails.py              # all cases
    python src/build_audit_trails.py 002 005 010  # specific cases
    python src/build_audit_trails.py --store-db   # also store in PostgreSQL
"""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Modules import each other by bare name (`from audit_trail import …`), so src/
# has to be on the path however this file is started: as a script, as
# `python -m src.build_audit_trails`, or imported from evaluate_narratives.py.
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audit_trail import (  # noqa: E402 — needs the sys.path bootstrap above
    AUDIT_DIR,
    AuditRecord,
    build_audit_record,
    load_audit_record,
    save_audit_record,
    save_provenance_report,
)
from case_input import CaseInput, from_attempt  # noqa: E402
from generate_narrative import (  # noqa: E402
    CASE_TO_ATTEMPT,
    GENERATED_DIR,
    PRIMARY_MODEL,
    retrieve_context_with_metadata,
)
from typology import analyse_case, effective_pattern  # noqa: E402


# generate_and_save writes a metadata header above the narrative, closed by a
# `---` rule on its own line. Only the body below that rule is the narrative —
# auditing the header would add sentences the generator never produced.
_HEADER_RULE = re.compile(r"^---[ \t]*$", re.MULTILINE)
_MODEL_LINE = re.compile(r"\*\*Model:\*\*\s*(\S+)")


def narrative_body(content: str) -> str:
    """The narrative text from a generated draft, without its metadata header."""
    match = _HEADER_RULE.search(content)
    return content[match.end():].strip() if match else content.strip()


def previous_record(case_id: str) -> AuditRecord | None:
    """The audit record this rebuild replaces, if one is on disk."""
    if not (AUDIT_DIR / f"{case_id}_audit.json").exists():
        return None
    try:
        return load_audit_record(case_id)
    except Exception as e:  # noqa: BLE001 — a corrupt record must not block the rebuild
        print(f"  ! Could not read the existing audit record: {e}")
        return None


def rebuild_case_audit(
    case_id: str,
    verbose: bool = True,
) -> tuple[AuditRecord, CaseInput] | None:
    """
    Rebuild the audit trail for an existing generated narrative.

    Mirrors generate_narrative.prepare_generation (with use_dataset_label=True,
    which is what batch generation uses) so the rebuilt record matches the one
    generation wrote — everything except the model call itself.

    Returns (audit record, the case it was built from).
    """
    attempt_id = CASE_TO_ATTEMPT.get(case_id)
    if attempt_id is None:
        if verbose:
            print(f"  ✗ Unknown case ID: {case_id}")
        return None

    narrative_path = GENERATED_DIR / f"{case_id}_generated.md"
    if not narrative_path.exists():
        if verbose:
            print(f"  ✗ No generated narrative for case {case_id}")
        return None

    content = narrative_path.read_text(encoding="utf-8")
    narrative_text = narrative_body(content)
    previous = previous_record(case_id)

    # The header records which model actually produced this draft.
    model_match = _MODEL_LINE.search(content)
    if model_match:
        model_used = model_match.group(1)
    elif previous:
        model_used = previous.model_used
    else:
        model_used = PRIMARY_MODEL

    # Samples are drafted around their dataset label rather than rule-based
    # detection, so evaluation stays comparable — reproduce that here.
    case = from_attempt(attempt_id, case_id)
    if case.dataset_label:
        case.pattern_override = case.dataset_label
    detection, flags = analyse_case(case)
    pattern = effective_pattern(case, detection)

    if verbose:
        print(f"  Retrieving typology context for attempt #{attempt_id}...", flush=True)

    start = time.time()
    _, retrieval_meta, chunk_texts = retrieve_context_with_metadata(
        case, pattern=pattern, flags=flags,
    )
    retrieval_time = time.time() - start

    if verbose:
        print(f"  Retrieved {len(retrieval_meta.chunks_returned)} chunks "
              f"in {retrieval_time:.1f}s", flush=True)

    # Model settings and timing can't be recovered from the narrative text.
    # Carry them over, and record that the provenance was rebuilt afterwards.
    generation_config = dict(previous.generation_config) if previous else {}
    if previous:
        generation_config["rebuilt_at"] = datetime.now(timezone.utc).isoformat()
    elif verbose:
        print("  ! No previous audit record — generation config and timing unavailable")

    audit_record = build_audit_record(
        case_id=case_id,
        attempt_id=case.attempt_id,
        pattern_type=pattern,
        model_used=model_used,
        generation_time=previous.generation_time_seconds if previous else 0.0,
        narrative_text=narrative_text,
        retrieval_metadata=retrieval_meta,
        chunk_texts=chunk_texts,
        txn_df=case.transactions,
        case_facts=case.case_facts(),
        detection=detection.to_dict(),
        red_flags=[f.to_dict() for f in flags],
        generation_config=generation_config,
        case_source=case.source,
    )
    # The narrative was generated then, not now.
    if previous and previous.generated_at:
        audit_record.generated_at = previous.generated_at

    audit_path = save_audit_record(audit_record)
    report_path = save_provenance_report(audit_record)

    if verbose:
        grounded = sum(
            1 for s in audit_record.narrative_sentences
            if s.field_references or s.chunk_attributions
        )
        total = len(audit_record.narrative_sentences)
        rules = sum(1 for s in audit_record.narrative_sentences if s.rule_attributions)
        print(f"  → {total} sentences, {grounded} grounded "
              f"({grounded/max(total,1)*100:.0f}%), {rules} rule-attributed")
        print(f"  → {len(flags)} red flags, detection {detection.pattern} "
              f"({detection.confidence} confidence)")
        print(f"  → Saved: {audit_path.name}, {report_path.name}")

    return audit_record, case


def build_audit_for_case(case_id: str, verbose: bool = True) -> AuditRecord | None:
    """Rebuild one case's audit trail (see `rebuild_case_audit`)."""
    result = rebuild_case_audit(case_id, verbose=verbose)
    return result[0] if result else None


def run_all(
    case_ids: list[str] | None = None,
    store_db: bool = False,
    verbose: bool = True,
) -> None:
    """Rebuild audit trails for all (or specified) generated narratives."""

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

    results: list[tuple[str, AuditRecord, CaseInput]] = []
    for case_id in case_ids:
        print(f"Case {case_id} (attempt #{CASE_TO_ATTEMPT.get(case_id, '?')}):")
        rebuilt = rebuild_case_audit(case_id, verbose=verbose)
        if rebuilt:
            results.append((case_id, *rebuilt))
        print()

    # Store in PostgreSQL if requested
    if store_db and results:
        print("--- Storing in PostgreSQL ---")
        try:
            from db import init_db, insert_case
            init_db()
            for case_id, audit, case in results:
                narrative_path = GENERATED_DIR / f"{case_id}_generated.md"
                narrative = narrative_path.read_text(encoding="utf-8")
                row_id = insert_case(
                    case_id=case_id,
                    attempt_id=audit.attempt_id,
                    pattern_type=audit.pattern_type,
                    narrative_text=narrative,
                    audit_record=audit,
                    source=audit.case_source,
                    case_input=case.to_dict(),
                    detection=audit.detection,
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
    for _, audit, _ in results:
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
