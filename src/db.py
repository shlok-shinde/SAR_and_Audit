"""
db.py — PostgreSQL storage for SAR cases and audit trails.

Stores generated narratives alongside their structured audit records
using JSONB columns for flexible querying.

Schema supports the approve/reject workflow described in ARCHITECTURE.md.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from audit_trail import AuditRecord


# ── Connection ───────────────────────────────────────────────────────────────

# Defaults match the docker-compose.yml configuration
DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "sar_audit"),
    "user": os.environ.get("POSTGRES_USER", "sar_user"),
    "password": os.environ.get("POSTGRES_PASSWORD", "sar_pass"),
}


@contextmanager
def get_connection() -> Generator:
    """Get a database connection with automatic commit/rollback."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor(dict_cursor: bool = True) -> Generator:
    """Get a database cursor with automatic connection management."""
    cursor_factory = RealDictCursor if dict_cursor else None
    with get_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        yield cursor


# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- SAR cases table: stores generated narratives with audit trails
CREATE TABLE IF NOT EXISTS sar_cases (
    id              SERIAL PRIMARY KEY,
    case_id         VARCHAR(40) UNIQUE NOT NULL,
    attempt_id      INTEGER,                -- NULL for uploaded / manual cases
    pattern_type    VARCHAR(50) NOT NULL,
    model_used      VARCHAR(100),

    -- Generated narrative (full text)
    narrative_text  TEXT,

    -- Structured audit trail (JSONB for flexible querying)
    audit_trail     JSONB,

    -- Workflow status
    status          VARCHAR(20) DEFAULT 'Pending',
    reviewer_notes  TEXT,

    -- Metrics
    generation_time_seconds  FLOAT,
    structural_score         FLOAT,  -- FFIEC completeness %

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sar_cases_case_id ON sar_cases(case_id);
CREATE INDEX IF NOT EXISTS idx_sar_cases_pattern ON sar_cases(pattern_type);
CREATE INDEX IF NOT EXISTS idx_sar_cases_status ON sar_cases(status);

-- GIN index on JSONB audit trail for content queries
CREATE INDEX IF NOT EXISTS idx_sar_cases_audit_gin ON sar_cases USING GIN(audit_trail);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Migration for custom cases + decision workflow (idempotent: safe on old
-- databases created before these columns existed, and on new ones).
ALTER TABLE sar_cases ALTER COLUMN attempt_id DROP NOT NULL;
ALTER TABLE sar_cases ALTER COLUMN case_id TYPE VARCHAR(40);
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS source             VARCHAR(20) DEFAULT 'sample';
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS case_input         JSONB;   -- CaseInput.to_dict()
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS detection          JSONB;   -- typology + red flags
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS decision           VARCHAR(10);  -- SAR | No SAR
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS decision_rationale TEXT;
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS alert_date         DATE;
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS filing_due         DATE;
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS drafted_by         VARCHAR(80);
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS approved_by        VARCHAR(80);
ALTER TABLE sar_cases ADD COLUMN IF NOT EXISTS approved_at        TIMESTAMPTZ;
ALTER TABLE sar_cases DROP CONSTRAINT IF EXISTS sar_cases_status_check;
ALTER TABLE sar_cases ADD CONSTRAINT sar_cases_status_check
    CHECK (status IN ('Pending', 'Approved', 'Rejected', 'No SAR', 'Filed'));

-- Case history: who did what, when (the audit trail of the case itself)
CREATE TABLE IF NOT EXISTS case_events (
    id       SERIAL PRIMARY KEY,
    case_id  VARCHAR(40) NOT NULL,
    actor    VARCHAR(80),
    action   VARCHAR(40) NOT NULL,
    details  JSONB,
    at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_case_events_case ON case_events(case_id, at);

DROP TRIGGER IF EXISTS update_sar_cases_updated_at ON sar_cases;
CREATE TRIGGER update_sar_cases_updated_at
    BEFORE UPDATE ON sar_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


def init_db() -> None:
    """Create the database schema. Safe to run multiple times (idempotent)."""
    with get_cursor(dict_cursor=False) as cursor:
        cursor.execute(SCHEMA_SQL)
    print("Database schema initialized.")


# ── CRUD Operations ──────────────────────────────────────────────────────────

def insert_case(
    case_id: str,
    attempt_id: int | None,
    pattern_type: str,
    narrative_text: str,
    audit_record: AuditRecord,
    structural_score: float | None = None,
    *,
    source: str | None = None,
    case_input: dict | None = None,
    detection: dict | None = None,
    drafted_by: str | None = None,
    alert_date: str | None = None,
    filing_due: str | None = None,
) -> int:
    """
    Insert (or update) a SAR case with its narrative and audit trail.

    Keyword-only extras describe custom cases; batch callers that don't pass
    them keep whatever the row already had (COALESCE). Saving resets the
    status to Pending — a changed narrative needs a fresh decision.

    Returns the row ID.
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO sar_cases
                (case_id, attempt_id, pattern_type, model_used,
                 narrative_text, audit_trail, generation_time_seconds,
                 structural_score, source, case_input, detection, drafted_by,
                 alert_date, filing_due)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, 'sample'), %s, %s, %s, %s, %s)
            ON CONFLICT (case_id) DO UPDATE SET
                narrative_text = EXCLUDED.narrative_text,
                audit_trail = EXCLUDED.audit_trail,
                pattern_type = EXCLUDED.pattern_type,
                model_used = EXCLUDED.model_used,
                generation_time_seconds = EXCLUDED.generation_time_seconds,
                structural_score = EXCLUDED.structural_score,
                source = COALESCE(%s, sar_cases.source),
                case_input = COALESCE(EXCLUDED.case_input, sar_cases.case_input),
                detection = COALESCE(EXCLUDED.detection, sar_cases.detection),
                drafted_by = COALESCE(EXCLUDED.drafted_by, sar_cases.drafted_by),
                alert_date = COALESCE(EXCLUDED.alert_date, sar_cases.alert_date),
                filing_due = COALESCE(EXCLUDED.filing_due, sar_cases.filing_due),
                status = 'Pending',
                decision = NULL,
                approved_by = NULL,
                approved_at = NULL,
                updated_at = NOW()
            RETURNING id
            """,
            (
                case_id,
                attempt_id,
                pattern_type,
                audit_record.model_used,
                narrative_text,
                Json(audit_record.to_dict()),
                audit_record.generation_time_seconds,
                structural_score,
                source,
                Json(case_input) if case_input is not None else None,
                Json(detection) if detection is not None else None,
                drafted_by or None,
                alert_date or None,
                filing_due or None,
                source,
            ),
        )
        return cursor.fetchone()["id"]


def get_case_input(case_id: str):
    """The CaseInput a saved case was built from (legacy rows: rebuilt from the attempt)."""
    from case_input import CaseInput, from_attempt

    row = get_case(case_id)
    if not row:
        return None
    if row.get("case_input"):
        return CaseInput.from_dict({**row["case_input"], "case_id": case_id})
    if row.get("attempt_id") is not None:
        return from_attempt(int(row["attempt_id"]), case_id)
    return None


def log_event(case_id: str, action: str, actor: str = "", details: dict | None = None) -> None:
    """Append to the case history (generated, saved, decision, approved, exported…)."""
    with get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO case_events (case_id, actor, action, details) VALUES (%s, %s, %s, %s)",
            (case_id, actor or None, action, Json(details or {})),
        )


def get_events(case_id: str) -> list[dict]:
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT actor, action, details, at FROM case_events WHERE case_id = %s ORDER BY at, id",
            (case_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_case(case_id: str) -> dict | None:
    """Retrieve a SAR case by case_id."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM sar_cases WHERE case_id = %s",
            (case_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_cases(status: str | None = None) -> list[dict]:
    """Retrieve all SAR cases, optionally filtered by status."""
    with get_cursor() as cursor:
        if status:
            cursor.execute(
                "SELECT * FROM sar_cases WHERE status = %s ORDER BY case_id",
                (status,),
            )
        else:
            cursor.execute("SELECT * FROM sar_cases ORDER BY updated_at DESC, case_id")
        return [dict(row) for row in cursor.fetchall()]


STATUSES = ("Pending", "Approved", "Rejected", "No SAR", "Filed")


def update_status(
    case_id: str,
    status: str,
    reviewer_notes: str = "",
    *,
    decision: str | None = None,
    decision_rationale: str | None = None,
    approved_by: str | None = None,
) -> bool:
    """
    Record a workflow decision on a case.

    Args:
        case_id: The case identifier
        status: One of Pending / Approved / Rejected / No SAR / Filed
        reviewer_notes: Optional reviewer comments
        decision: "SAR" or "No SAR"
        decision_rationale: Why (required by the UI for No SAR)
        approved_by: The checker who approved (maker-checker)

    Returns:
        True if a row was updated, False if case_id not found.
    """
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {', '.join(STATUSES)}.")

    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE sar_cases
            SET status = %s, reviewer_notes = %s,
                decision = COALESCE(%s, decision),
                decision_rationale = COALESCE(%s, decision_rationale),
                approved_by = CASE WHEN %s IN ('Approved', 'No SAR', 'Filed') THEN %s ELSE approved_by END,
                approved_at = CASE WHEN %s IN ('Approved', 'No SAR', 'Filed') THEN NOW() ELSE approved_at END
            WHERE case_id = %s
            """,
            (status, reviewer_notes, decision, decision_rationale,
             status, approved_by, status, case_id),
        )
        return cursor.rowcount > 0


def update_narrative(case_id: str, new_text: str) -> bool:
    """Update the narrative text for a case (human-in-the-loop edit)."""
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE sar_cases SET narrative_text = %s WHERE case_id = %s",
            (new_text, case_id),
        )
        return cursor.rowcount > 0


def get_audit_trail(case_id: str) -> AuditRecord | None:
    """Retrieve and reconstruct the AuditRecord for a case."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT audit_trail FROM sar_cases WHERE case_id = %s",
            (case_id,),
        )
        row = cursor.fetchone()
        if row and row["audit_trail"]:
            return AuditRecord.from_dict(row["audit_trail"])
        return None


# ── JSONB Queries (the power of PostgreSQL for audit data) ───────────────────

def find_cases_by_chunk(chunk_id: str) -> list[dict]:
    """
    Find all cases where a specific ChromaDB chunk was used in generation.
    Demonstrates JSONB querying capability.
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT case_id, pattern_type, status
            FROM sar_cases
            WHERE audit_trail -> 'retrieval_metadata' -> 'chunks_returned'
                  @> %s::jsonb
            """,
            (json.dumps([{"chunk_id": chunk_id}]),),
        )
        return [dict(row) for row in cursor.fetchall()]


def find_ungrounded_cases(min_ungrounded: int = 3) -> list[dict]:
    """
    Find cases with a high number of ungrounded sentences
    (sentences with no data or context attribution).
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT case_id, pattern_type,
                   jsonb_array_length(audit_trail -> 'narrative_sentences') as total_sentences
            FROM sar_cases
            WHERE (
                SELECT COUNT(*)
                FROM jsonb_array_elements(audit_trail -> 'narrative_sentences') AS sent
                WHERE sent -> 'confidence_note' = '"Model-generated claim — no direct source attribution"'
            ) >= %s
            ORDER BY case_id
            """,
            (min_ungrounded,),
        )
        return [dict(row) for row in cursor.fetchall()]


# ── Bulk Operations ──────────────────────────────────────────────────────────

def store_all_cases(
    cases: list[tuple[str, int, str, str, AuditRecord, float | None]],
) -> int:
    """
    Bulk insert/upsert multiple cases.

    Each tuple: (case_id, attempt_id, pattern_type, narrative_text, audit_record, score)

    Returns count of rows affected.
    """
    count = 0
    for case_id, attempt_id, pattern_type, narrative, audit, score in cases:
        insert_case(case_id, attempt_id, pattern_type, narrative, audit, score)
        count += 1
    return count


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        cases = get_all_cases()
        print(f"Total cases: {len(cases)}")
        for case in cases:
            print(
                f"  {case['case_id']} | {case['pattern_type']:>18} | "
                f"{case['status']:>10} | {case.get('structural_score', 'N/A')}"
            )
    else:
        print("Usage:")
        print("  python -m src.db init     # Initialize database schema")
        print("  python -m src.db status   # Show all cases")
