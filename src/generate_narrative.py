"""
generate_narrative.py — RAG generation chain for SAR narratives.

Takes a case — a `CaseInput` built from an analyst's upload (transactions plus
KYC profile, alert, investigation findings and prior SARs) or an IBM dataset
attempt — and:
  1. runs the rule-based typology and red-flag engine (typology.py),
  2. retrieves matching regulatory guidance from ChromaDB,
  3. drafts a FFIEC-structured SAR narrative via Ollama
     (primary Gemma 4 E2B, fallback Qwen 3.5 4B),
  4. validates the draft and builds its sentence-level audit record.

Callers that pass a bare attempt ID (batch evaluation, older code) still work:
it's wrapped into a sample case.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path

import pandas as pd

from case_input import CaseInput, as_case, is_usd
from data_loader import PARQUET_OUT, get_attempt  # noqa: F401 — re-exported for callers
from typology import analyse_case, effective_pattern, warrants_no_sar

# Config
PROJECT_ROOT = Path(__file__).resolve().parent.parent
NARRATIVES_DIR = PROJECT_ROOT / "narratives"
GENERATED_DIR = PROJECT_ROOT / "generated"
# Ollama endpoint. Defaults to the local server; set OLLAMA_HOST when the app
# runs in a container and Ollama stays on the host.
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
PRIMARY_MODEL = "gemma4:e2b"
FALLBACK_MODEL = "qwen3.5:4b"
TEMPERATURE = 0.3  # low for factual, structured output

# Context window. The full prompt (system + 3 few-shot narratives + retrieved
# chunks + case file + transaction log) is ~5-8k tokens and the answer can use
# up to NUM_PREDICT more. Ollama's default window here is 4096, and when a
# prompt doesn't fit it *silently keeps only the tail* — which dropped the
# system prompt and all few-shot examples (log: "truncating input prompt
# limit=2051 prompt=6766"). That caused both the refusals and the
# off-format narratives. Always set num_ctx explicitly.
NUM_CTX = 16384
NUM_PREDICT = 4096
SEED = 42                 # reproducible drafts; retries use SEED + attempt
ATTEMPTS_PER_MODEL = 2    # re-sample once before falling back to the next model

# Transaction-log budget. Beyond this many flagged rows the log sent to the
# model is summarised (per account pair + largest transfers); the audit trail
# still checks the narrative against every row.
MAX_LOG_ROWS = 60
TOP_ROWS_WHEN_SUMMARISED = 20

# Few-shot example case IDs (attempt IDs from Patterns.txt)
# 001 = attempt 307 (FAN-OUT), 004 = attempt 284 (FAN-IN), 012 = attempt 260 (STACK)
FEW_SHOT_FILES = ["001_fan_out_a.md", "004_fan_in_b.md", "012_stack_b.md"]

# Cases to exclude from evaluation (used as few-shot training)
FEW_SHOT_CASE_IDS = {"001", "004", "012"}

# Map narrative file prefixes to attempt IDs (from narrative file headers)
CASE_TO_ATTEMPT = {
    "001": 307,  # FAN-OUT A (16-degree)
    "002": 36,   # FAN-OUT B (10-degree)
    "003": 285,  # FAN-IN A (16-degree)
    "004": 352,  # FAN-IN B (8-degree)
    "005": 218,  # CYCLE A
    "006": 249,  # CYCLE B
    "007": 49,   # GATHER-SCATTER A
    "008": 92,   # GATHER-SCATTER B
    "009": 334,  # SCATTER-GATHER A
    "010": 271,  # SCATTER-GATHER B
    "011": 240,  # STACK A
    "012": 260,  # STACK B (few-shot)
    "013": 163,  # BIPARTITE A
    "014": 344,  # BIPARTITE B
    "015": 329,  # RANDOM A (negative control)
    "016": 179,  # RANDOM B (negative control)
}


# ── 1. Case data formatting ──────────────────────────────────────────────────

def _money(amount: float, currency: str) -> str:
    return f"${amount:,.2f}" if is_usd(currency) else f"{amount:,.2f} {currency}"


def _totals(df: pd.DataFrame, amount_col: str, ccy_col: str) -> str:
    """'$61,854.70' for one currency, '485.30 US Dollar; 71,319.53 Rupee' for several."""
    parts = [_money(v, c) for c, v in df.groupby(ccy_col)[amount_col].sum().items()]
    return "; ".join(parts) if parts else "0.00"


def _banks(df: pd.DataFrame) -> set[str]:
    names = set(df["From_Bank_Name"]) | set(df["To_Bank_Name"])
    ids = set(df["From Bank"]) | set(df["To Bank"])
    names.discard("")
    ids.discard("")
    return ids if len(ids) >= len(names) else names


def _txn_line(row) -> str:
    frm_bank = row["From_Bank_Name"] or row["From Bank"] or "bank not given"
    to_bank = row["To_Bank_Name"] or row["To Bank"] or "bank not given"
    route = ""
    if row["From_Country"] or row["To_Country"]:
        route = f" | {row['From_Country'] or '?'} → {row['To_Country'] or '?'}"
    return (
        f"  {row['Timestamp']} | {row['From_Account']} ({frm_bank}) "
        f"→ {row['To_Account']} ({to_bank}) | "
        f"Paid: {row['Amount Paid']:,.2f} {row['Payment Currency']} | "
        f"Received: {row['Amount Received']:,.2f} {row['Receiving Currency']} | "
        f"{row['Payment Format']}{route}"
    )


def format_transaction_data(case_or_attempt, pattern: str | None = None,
                            detection=None) -> str:
    """The case's transactions as structured text for the LLM."""
    case = as_case(case_or_attempt)
    df = case.flagged()
    if pattern is None:
        pattern = case.pattern_override or case.dataset_label or (
            detection.pattern if detection else "NONE")
    subject_accounts = set(case.subject.accounts)

    if case.attempt_id is not None:
        header = f"LAUNDERING ATTEMPT #{case.attempt_id}"
    else:
        header = f"CASE {case.case_id}"
    if case.dataset_label and pattern == case.dataset_label:
        pattern_line = f"Pattern: {pattern}" + (f" ({case.degree_info})" if case.degree_info else "")
    elif case.pattern_override:
        pattern_line = f"Pattern: {pattern} (selected by the analyst)"
    else:
        conf = f", {detection.confidence} confidence" if detection else ""
        pattern_line = f"Pattern: {pattern} (rule-based detection{conf})"

    currencies = sorted(set(df["Receiving Currency"]) | set(df["Payment Currency"]))
    formats = sorted(set(df["Payment Format"]))
    unique_accounts = set(df["From_Account"]) | set(df["To_Account"])
    first_ccy = df["Payment Currency"].iloc[0] if len(df) else "USD"
    lines = [
        header,
        pattern_line,
        f"Transaction Count: {len(df)}",
        f"Total Amount Paid: {_totals(df, 'Amount Paid', 'Payment Currency')}",
        f"Total Amount Received: {_totals(df, 'Amount Received', 'Receiving Currency')}",
        f"Min Amount: {_money(df['Amount Paid'].min(), first_ccy)}"
        if len(currencies) == 1 else "Min Amount: see transaction log (several currencies)",
        f"Max Amount: {_money(df['Amount Paid'].max(), first_ccy)}"
        if len(currencies) == 1 else "Max Amount: see transaction log (several currencies)",
        f"Date Range: {df['Timestamp'].min()} → {df['Timestamp'].max()}",
        f"Unique Accounts: {len(unique_accounts)}",
        f"Unique Banks: {len(_banks(df))}",
        f"Currencies: {', '.join(currencies)}",
        f"Cross-Currency: {'Yes' if len(currencies) > 1 else 'No'}",
        f"Payment Formats: {', '.join(formats)}",
    ]
    # Exact breakdowns, so the model copies counts instead of inferring them
    # (live test: "Transaction Count: 9" became "nine cash deposits" when there
    # were 7 cash deposits and 2 wires).
    if len(formats) > 1:
        by_format = df.groupby("Payment Format").agg(n=("Amount Paid", "size"))
        lines.append("By Payment Format: " + "; ".join(
            f"{fmt} {int(r['n'])} ({_totals(df[df['Payment Format'] == fmt], 'Amount Paid', 'Payment Currency')})"
            for fmt, r in by_format.iterrows()))
    hubs = []
    for acct in sorted(unique_accounts):
        inflow = df[(df["To_Account"] == acct) & (df["From_Account"] != acct)]
        outflow = df[(df["From_Account"] == acct) & (df["To_Account"] != acct)]
        if len(inflow) >= 2 or len(outflow) >= 2:
            hubs.append((len(inflow) + len(outflow), acct, inflow, outflow))
    for _, acct, inflow, outflow in sorted(hubs, reverse=True)[:5]:
        parts = []
        if len(inflow):
            parts.append(f"received {len(inflow)} transfers "
                         f"({_totals(inflow, 'Amount Received', 'Receiving Currency')}) from "
                         f"{inflow['From_Account'].nunique()} distinct senders")
        if len(outflow):
            parts.append(f"sent {len(outflow)} transfers "
                         f"({_totals(outflow, 'Amount Paid', 'Payment Currency')}) to "
                         f"{outflow['To_Account'].nunique()} distinct recipients")
        lines.append(f"Account {acct}: " + "; ".join(parts))
    lines += ["", "ACCOUNTS & ENTITIES:"]

    account_info: dict[str, dict] = {}
    for _, row in df.iterrows():
        for side, role in (("From", "Sender"), ("To", "Receiver")):
            acct = row[f"{side}_Account"]
            info = account_info.setdefault(acct, {
                "bank": row[f"{side}_Bank_Name"] or row[f"{side} Bank"] or "bank not given",
                "entity": row[f"{side}_Entity_Name"] or "Unknown",
                "country": row[f"{side}_Country"],
                "roles": set(),
            })
            info["roles"].add(role)
    for acct, info in account_info.items():
        roles = "/".join(sorted(info["roles"]))
        extra = f" | {info['country']}" if info["country"] else ""
        mark = " | SUBJECT" if acct in subject_accounts else ""
        lines.append(f"  {acct} | {info['bank']} | {info['entity']} | {roles}{extra}{mark}")

    lines.append("")
    if len(df) <= MAX_LOG_ROWS:
        lines.append("TRANSACTION LOG:")
        lines += [_txn_line(row) for _, row in df.sort_values("Timestamp").iterrows()]
    else:
        # Keep the prompt inside the context window: per-pair totals + the
        # largest transfers, instead of thousands of lines.
        lines.append(f"TRANSACTION LOG (summarised: {len(df)} transactions):")
        pairs = (df.groupby(["From_Account", "To_Account", "Payment Currency"])
                 .agg(n=("Amount Paid", "size"), total=("Amount Paid", "sum"),
                      first=("Timestamp", "min"), last=("Timestamp", "max"))
                 .sort_values("total", ascending=False).head(MAX_LOG_ROWS // 2))
        for (frm, to, ccy), r in pairs.iterrows():
            lines.append(f"  {frm} → {to} | {int(r['n'])} transfers | total "
                         f"{r['total']:,.2f} {ccy} | {r['first']} → {r['last']}")
        lines.append(f"LARGEST {TOP_ROWS_WHEN_SUMMARISED} TRANSACTIONS:")
        top = df.sort_values("Amount Paid", ascending=False).head(TOP_ROWS_WHEN_SUMMARISED)
        lines += [_txn_line(row) for _, row in top.iterrows()]

    context = case.context()
    if not context.empty:
        lines += ["", "OTHER ACCOUNT ACTIVITY (not flagged; the account's normal baseline):"]
        month = pd.to_datetime(context["Timestamp"], errors="coerce").dt.strftime("%Y-%m")
        for m, rows in context.groupby(month):
            if subject_accounts:
                inflow = rows[rows["To_Account"].isin(subject_accounts)]
                outflow = rows[rows["From_Account"].isin(subject_accounts)]
                lines.append(
                    f"  {m}: {len(rows)} transactions | in "
                    f"{_totals(inflow, 'Amount Received', 'Receiving Currency') if len(inflow) else '0.00'}"
                    f" | out {_totals(outflow, 'Amount Paid', 'Payment Currency') if len(outflow) else '0.00'}"
                    f" | formats: {', '.join(sorted(set(rows['Payment Format'])))}")
            else:
                lines.append(f"  {m}: {len(rows)} transactions | total "
                             f"{_totals(rows, 'Amount Paid', 'Payment Currency')}")

    return "\n".join(lines)


def _or_none(value) -> str:
    return str(value) if value not in (None, "", []) else ""


def format_case_file(case: CaseInput, detection=None, flags=(),
                     include_detection: bool = True) -> str:
    """Analyst-provided facts + rule-based findings, as a prompt block ("" if empty)."""
    s, a, inv = case.subject, case.alert, case.investigation
    out: list[str] = []

    subject = [
        ("Name", s.name), ("Type", s.subject_type), ("Occupation / business", s.occupation),
        ("Country", s.country), ("Address", s.address),
        ("Subject's accounts", ", ".join(s.accounts)), ("Relationship since", s.account_opened),
        ("Expected monthly volume", f"${s.expected_monthly_volume:,.2f}"
         if s.expected_monthly_volume else ""),
        ("Expected monthly transactions", _or_none(s.expected_monthly_count)),
        ("Risk rating", s.risk_rating), ("Notes", s.notes),
    ]
    subject = [(k, v) for k, v in subject if v]
    if subject:
        out += ["SUBJECT (KYC profile):"] + [f"  {k}: {v}" for k, v in subject]

    alert = [("Source", a.source), ("Alert ID", a.alert_id), ("Detected on", a.detected_on),
             ("Description", a.description)]
    alert = [(k, v) for k, v in alert if v]
    if alert:
        out += ["ALERT / REFERRAL:"] + [f"  {k}: {v}" for k, v in alert]

    if inv.steps:
        out += ["INVESTIGATION STEPS COMPLETED:"] + [f"  - {step}" for step in inv.steps]
    if inv.findings:
        out += ["INVESTIGATION FINDINGS:", f"  {inv.findings}"]
    if inv.ruled_out:
        out += ["EXPLANATIONS CONSIDERED AND RULED OUT:", f"  {inv.ruled_out}"]

    prior = [p for p in case.prior_sars if p.filed_on or p.reference]
    if prior:
        out.append("PRIOR SARS ON THIS SUBJECT (continuing activity):")
        for p in prior:
            bits = [f"filed {p.filed_on}" if p.filed_on else "",
                    f"reference {p.reference}" if p.reference else "",
                    f"amount ${p.amount:,.2f}" if p.amount else "",
                    f"covering {p.period_start} to {p.period_end}"
                    if p.period_start and p.period_end else ""]
            out.append("  - " + ", ".join(b for b in bits if b))

    if include_detection and detection is not None:
        out.append(f"RULE-BASED TYPOLOGY DETECTION: {detection.pattern} "
                   f"({detection.confidence} confidence)")
        out += [f"  - {e}" for e in detection.evidence]
    if flags:
        out.append("RED FLAGS (rule-based, from the transaction data):")
        for f in flags:
            out.append(f"  - [{f.severity.upper()}] {f.title}: {f.evidence}")

    if not out:
        return ""
    return "CASE FILE:\n" + "\n".join(out)


# ── 2. Hybrid Retrieval ──────────────────────────────────────────────────────

# Shared pattern descriptions for queries
PATTERN_DESCRIPTIONS = {
    "FAN-OUT": "fan-out structuring dispersal of funds from single account to multiple accounts to evade reporting thresholds",
    "FAN-IN": "fan-in aggregation convergence of funds from multiple accounts into single account structuring deposits",
    "CYCLE": "cycle circular movement of funds returning to origin U-turn round-trip layering",
    "GATHER-SCATTER": "gather-scatter funnel account aggregation then dispersal consolidation and redistribution",
    "SCATTER-GATHER": "scatter-gather smurfing one source to one destination via multiple intermediary money mules",
    "STACK": "stack parallel chain layering sequential hops through intermediary accounts",
    "BIPARTITE": "bipartite related-party transaction pairs disjoint groups coordinated transfers",
    "RANDOM": "random unstructured transaction activity no clear typology match",
}
PATTERN_DESCRIPTIONS["NONE"] = PATTERN_DESCRIPTIONS["RANDOM"]


def build_queries(case: CaseInput, pattern: str, flags=()) -> tuple[str, str]:
    """Label query (typology) + description query (what the data looks like)."""
    df = case.flagged()
    label_query = PATTERN_DESCRIPTIONS.get(pattern, f"{pattern} money laundering pattern")
    n_accounts = len(set(df["From_Account"]) | set(df["To_Account"]))
    n_currencies = len(set(df["Receiving Currency"]) | set(df["Payment Currency"]))
    formats = " and ".join(sorted(set(df["Payment Format"]))[:3])
    desc_query = (
        f"{len(df)} {formats} transactions across {n_accounts} accounts at "
        f"{len(_banks(df))} institutions involving {n_currencies} currencies, "
        f"pattern labeled as {pattern}"
    )
    salient = [f.title.lower() for f in flags if f.severity in ("high", "medium")][:2]
    if salient:
        desc_query += "; red flags: " + ", ".join(salient)
    return label_query, desc_query


def retrieve_by_queries(label_query: str, desc_query: str, n_results: int = 5
                        ) -> tuple[str, "RetrievalMetadata", dict[str, str]]:
    """Query ChromaDB with both queries, dedupe, keep the top n by distance.

    Returns (context_str for the prompt, RetrievalMetadata, chunk_id → text).
    """
    from audit_trail import RetrievalMetadata, RetrievedChunk
    import chromadb
    from embed_typology_docs import get_embedding_function, CHROMA_DIR, COLLECTION_NAME

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = get_embedding_function()
    collection = client.get_collection(COLLECTION_NAME, embedding_function=ef)

    results = {
        query_type: collection.query(
            query_texts=[query], n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        for query_type, query in (("label", label_query), ("description", desc_query))
    }

    # Deduplicate by chunk ID, keeping the lower distance; remember which query found it.
    chunk_query_source: dict[str, str] = {}
    seen: dict[str, dict] = {}
    total_candidates = 0
    for query_type, res in results.items():
        for i in range(len(res["ids"][0])):
            total_candidates += 1
            chunk_id = res["ids"][0][i]
            dist = res["distances"][0][i]
            if chunk_id not in seen or dist < seen[chunk_id]["distance"]:
                meta = res["metadatas"][0][i]
                seen[chunk_id] = {
                    "chunk_id": chunk_id,
                    "distance": dist,
                    "text": res["documents"][0][i],
                    "source": meta["source_file"],
                    "page": meta["page_number"],
                    "pattern_type": meta.get("pattern_type", "UNKNOWN"),
                }
                chunk_query_source[chunk_id] = query_type

    ranked = sorted(seen.values(), key=lambda x: x["distance"])[:n_results]

    retrieved_chunks = []
    chunk_texts = {}
    for item in ranked:
        cid = item["chunk_id"]
        chunk_texts[cid] = item["text"]
        retrieved_chunks.append(RetrievedChunk(
            chunk_id=cid,
            source_file=item["source"],
            page_number=item["page"],
            pattern_type=item["pattern_type"],
            distance=item["distance"],
            relevance_score=round(1 - item["distance"], 4),
            text_preview=item["text"][:200],
            query_type=chunk_query_source.get(cid, "unknown"),
        ))

    retrieval_meta = RetrievalMetadata(
        label_query=label_query,
        description_query=desc_query,
        top_k=n_results,
        chunks_returned=retrieved_chunks,
        dedup_count=total_candidates - len(seen),
        total_candidates=total_candidates,
    )
    context_str = "\n\n".join(
        f"[Source {i}: {item['source']}, p.{item['page']}, relevance={1 - item['distance']:.2f}]\n"
        f"{item['text']}"
        for i, item in enumerate(ranked, 1)
    )
    return context_str, retrieval_meta, chunk_texts


def retrieve_context_with_metadata(case_or_attempt, n_results: int = 5, pattern: str | None = None,
                                   flags=()) -> tuple[str, "RetrievalMetadata", dict[str, str]]:
    """Retrieve typology context for a case (or attempt ID) with hybrid queries.

    Without an explicit `pattern`, samples use their dataset label (the original
    behaviour, so batch audits stay reproducible) and uploads use detection.
    """
    case = as_case(case_or_attempt)
    if pattern is None:
        if case.pattern_override or case.dataset_label:
            pattern = case.pattern_override or case.dataset_label
        else:
            detection, flags = analyse_case(case)
            pattern = detection.pattern
    label_query, desc_query = build_queries(case, pattern, flags)
    return retrieve_by_queries(label_query, desc_query, n_results)


def retrieve_context(attempt_id: int, n_results: int = 5) -> str:
    """Backwards-compatible wrapper — returns only the context string."""
    context_str, _, _ = retrieve_context_with_metadata(attempt_id, n_results)
    return context_str


# ── 3. Few-Shot Examples ─────────────────────────────────────────────────────

def load_few_shot_examples() -> str:
    """Load the narrative sections from few-shot example files."""
    examples = []
    for filename in FEW_SHOT_FILES:
        filepath = NARRATIVES_DIR / filename
        content = filepath.read_text(encoding="utf-8")

        # Extract just the SAR narrative section (from "## SAR Narrative" onward)
        narrative_match = re.search(
            r"(## SAR Narrative.*?)(?=\Z)", content, re.DOTALL
        )
        if narrative_match:
            narrative_text = narrative_match.group(1).strip()
        else:
            # Fallback: extract from ### Who onward
            who_match = re.search(r"(### Who.*?)(?=\Z)", content, re.DOTALL)
            narrative_text = who_match.group(1).strip() if who_match else content

        # Also extract the header info for context
        pattern_match = re.search(r"\*\*Pattern:\*\*\s*(.+)", content)
        pattern = pattern_match.group(1).strip() if pattern_match else "Unknown"

        # Drop template scaffolding (HTML comments, "Write your … below" line)
        # so the model doesn't copy it and the prompt stays small.
        narrative_text = re.sub(r"<!--.*?-->\s*", "", narrative_text, flags=re.DOTALL)
        narrative_text = re.sub(r"^Write your gold-standard narrative below.*\n+", "",
                                narrative_text, flags=re.MULTILINE)
        examples.append(f"--- EXAMPLE ({pattern}) ---\n{narrative_text.strip()}")

    return "\n\n".join(examples)


# ── 4. Generation Chain ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a BSA/AML compliance analyst drafting a Suspicious Activity Report (SAR) narrative. Follow FFIEC SAR Quality Guidance (Appendix L) structure exactly.

CONTEXT: You are the drafting assistant inside an internal case-review tool used by a financial institution's compliance team. The case data comes from the institution's own records or a synthetic anti-money-laundering research dataset (IBM AML). Your output is a DRAFT that a qualified human analyst reviews, edits and approves before anything is filed. Drafting it is a routine, legitimate compliance task: always write the narrative. Do not refuse, and do not add disclaimers, advice about contacting authorities, or commentary outside the narrative.

Your narrative MUST include these sections in this exact order:

### Who (Subject Identification)
### What (Suspicious Activity)
### When (Timeframe)
### Where (Location)
### Why Suspicious
### How (Method / Mechanism)
### Supporting Pattern
### Quantitative Summary

RULES:
1. Ground EVERY claim in the provided transaction data, case file or retrieved typology context. Do not invent details.
2. Reference specific transaction amounts, dates, account numbers, and entity names from the input data. Copy figures exactly as they appear in the data; do not round or recompute them.
3. Include one sentence acknowledging alternative explanations in the Why Suspicious section.
4. Keep the How section focused on the mechanical description of how funds moved — no interpretive judgment.
5. Reference specific regulatory sources (FFIEC, FinCEN, FATF) when matching typologies, only if they appear in the retrieved context.
6. Only when the case's pattern is RANDOM or NONE (no typology match), state in Why Suspicious and Supporting Pattern that the activity does not match any known laundering typology and does not warrant a SAR filing. For every other pattern, never write that the activity does not warrant a SAR.
7. Be concise but thorough. Each section should be 1-3 sentences for simple cases, up to a paragraph for complex cases.
8. If a CASE FILE is provided, it holds facts from the investigating analyst (KYC profile, alert, investigation steps and findings, prior SARs). Use them: describe the subject's occupation or business and expected activity in Who, and explain in Why Suspicious how the activity departs from that baseline. Never invent KYC facts (occupation, address, account opening date, expected activity); if one is not in the case file, leave it out.
9. Describe only the investigation steps listed in the case file, and include the findings and any explanations the analyst ruled out.
10. The typology detection and red flags in the case file were computed by rules from the transaction data. Use their evidence, citing the specific amounts, dates and accounts behind them.

OUTPUT FORMAT:
- Output only the narrative in Markdown. Start directly with "### Who (Subject Identification)".
- Use exactly the eight headings above, in order, each followed by prose paragraphs (like the examples). Do not number sections, and do not use tables or bullet lists."""

HUMAN_TEMPLATE = """Here are examples of well-written SAR narratives to follow as style and structure references:

{few_shot_examples}

---

Here is regulatory typology context retrieved for the current case:

{retrieved_context}

---

Here is the case you must analyze:

{case_file}{transaction_data}

---

Write a complete SAR narrative for the above case following the exact section structure shown in the examples. Use the retrieved typology context to ground your suspicion analysis. Reference specific data points from the transaction log and case file.

Reminder: output only the narrative, starting with "### Who (Subject Identification)" and using the eight FFIEC headings in order, in prose.{case_directive}"""

# Identifies the exact instructions a draft was produced with (SR 11-7 style
# reproducibility: model + prompt version + input fingerprint + seed).
PROMPT_VERSION = hashlib.sha256((SYSTEM_PROMPT + HUMAN_TEMPLATE).encode()).hexdigest()[:12]


def build_prompt():
    """Build the ChatPromptTemplate with system + few-shot + context + case."""
    from langchain_core.prompts import ChatPromptTemplate
    return ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_TEMPLATE)])


# Per-case instructions placed at the very end of the prompt, where small
# models weight them most. Without the no-SAR one the model imitates the three
# (positive) few-shot SARs and calls random activity suspicious despite rule 6.
NEGATIVE_CONTROL_DIRECTIVE = (
    "\n\nIMPORTANT: The rule-based review found no known laundering typology in this "
    "activity (pattern RANDOM / NONE) and no high-severity red flag. In Why Suspicious "
    "and Supporting Pattern, state explicitly that the activity does not match any known "
    "laundering typology and does not warrant a SAR filing. Do not describe it as "
    "layering, structuring or any other typology."
)
CONTINUING_DIRECTIVE = (
    "\n\nIMPORTANT: This is a continuing-activity SAR. Reference each prior SAR listed in "
    "the case file by its filing date and reference, state the amount previously reported "
    "and the cumulative total including this period, and describe only the new activity "
    "in detail. Do not restate the prior narratives."
)


def case_directive(pattern: str, flags=(), continuing: bool = False) -> str:
    directive = NEGATIVE_CONTROL_DIRECTIVE if warrants_no_sar(str(pattern), list(flags)) else ""
    if continuing:
        directive += CONTINUING_DIRECTIVE
    return directive


# ── Output validation ────────────────────────────────────────────────────────

REQUIRED_HEADINGS = ["Who", "What", "When", "Where", "Why Suspicious"]
REFUSAL_PATTERN = re.compile(
    r"\b(I cannot|I can't|I can not|I am unable|I'm unable|I won't|I will not|"
    r"I am an AI|as an AI|cannot fulfill|can't fulfill|not able to (?:help|assist|generate|provide))\b",
    re.IGNORECASE,
)


class NarrativeGenerationError(RuntimeError):
    """Every model/attempt produced unusable output (refusal, wrong format, cut off)."""


NO_SAR_PATTERN = re.compile(r"\b(?:does|do|would) not warrant\b|\bno SAR\b|\bnot warrant(?:ed)?\b",
                            re.IGNORECASE)


def validate_narrative(text: str, done_reason: str | None = None,
                       pattern: str | None = None, no_sar: bool | None = None) -> list[str]:
    """Return the problems that make `text` unusable as a SAR draft ([] = valid)."""
    problems = []
    if not text.strip():
        return ["empty output"]
    if REFUSAL_PATTERN.search(text[:600]):
        problems.append("model refused the task")
    missing = [h for h in REQUIRED_HEADINGS
               if not re.search(rf"^###?\s*{re.escape(h)}", text, re.IGNORECASE | re.MULTILINE)]
    if missing:
        problems.append(f"missing required FFIEC sections: {', '.join(missing)}")
    if done_reason == "length":
        problems.append(f"output cut off at {NUM_PREDICT} tokens")
    if no_sar is None:
        no_sar = str(pattern).upper() == "RANDOM"
    if no_sar and not NO_SAR_PATTERN.search(text):
        problems.append("no typology / high red flag, but the draft doesn't conclude "
                        "'does not warrant a SAR'")
    if (not no_sar and pattern and str(pattern).upper() not in ("RANDOM", "NONE")
            and NO_SAR_PATTERN.search(text)):
        # Small models copy rule 6's wording into positive cases, producing a
        # self-contradicting draft ("…consistent with layering… does not warrant a SAR").
        problems.append(f"draft says the activity does not warrant a SAR although the "
                        f"pattern is {pattern}")
    return problems


def estimate_tokens(messages) -> int:
    """Conservative token estimate (≈3.2 chars/token for English + numbers)."""
    return int(sum(len(m.content) for m in messages) / 3.2)


def prepare_generation(case_or_attempt, case_id: str = "", use_dataset_label: bool = False
                       ) -> dict:
    """Everything the model call needs, without calling it (also used for the UI's
    prompt-budget check). Returns a dict of case, detection, flags, pattern,
    messages, retrieval results and token estimate."""
    case = as_case(case_or_attempt, case_id)
    if use_dataset_label and case.dataset_label and not case.pattern_override:
        case.pattern_override = case.dataset_label
    detection, flags = analyse_case(case)
    pattern = effective_pattern(case, detection)
    no_sar = warrants_no_sar(pattern, flags)

    txn_data = format_transaction_data(case, pattern, detection)
    context, retrieval_meta, chunk_texts = retrieve_context_with_metadata(
        case, pattern=pattern, flags=flags)
    case_file = format_case_file(case, detection, flags,
                                 include_detection=not use_dataset_label)
    messages = build_prompt().format_messages(
        few_shot_examples=load_few_shot_examples(),
        retrieved_context=context,
        case_file=f"{case_file}\n\n" if case_file else "",
        transaction_data=txn_data,
        case_directive=case_directive(pattern, flags, case.is_continuing()),
    )
    return {
        "case": case, "detection": detection, "flags": flags, "pattern": pattern,
        "no_sar": no_sar, "messages": messages, "retrieval_meta": retrieval_meta,
        "chunk_texts": chunk_texts, "prompt_tokens": estimate_tokens(messages),
    }


# Retrieved context is ~5 chunks of ≤1,000 characters plus source headers.
RETRIEVAL_ALLOWANCE_CHARS = 6000
_FEW_SHOT_CACHE: dict[str, str] = {}


def estimate_prompt_tokens(case: CaseInput, detection, flags) -> int:
    """Prompt size without querying ChromaDB (for the intake's budget check)."""
    if "text" not in _FEW_SHOT_CACHE:
        _FEW_SHOT_CACHE["text"] = load_few_shot_examples()
    pattern = effective_pattern(case, detection)
    chars = (len(SYSTEM_PROMPT) + len(HUMAN_TEMPLATE) + len(_FEW_SHOT_CACHE["text"])
             + RETRIEVAL_ALLOWANCE_CHARS
             + len(format_transaction_data(case, pattern, detection))
             + len(format_case_file(case, detection, flags))
             + len(case_directive(pattern, flags, case.is_continuing())))
    return int(chars / 3.2)


def generate_with_audit(
    case_or_attempt,
    case_id: str = "",
    verbose: bool = False,
    use_dataset_label: bool = False,
) -> tuple[str, "AuditRecord"]:
    """
    Generate a SAR narrative with full audit trail for a CaseInput (or attempt ID).

    `use_dataset_label` makes IBM samples use their ground-truth pattern instead
    of rule-based detection (batch evaluation keeps its metrics comparable).

    Returns (narrative_text, audit_record).
    """
    from audit_trail import build_audit_record

    start_time = time.time()
    if verbose:
        print("Analysing case, retrieving typology context, building prompt...", flush=True)
    prep = prepare_generation(case_or_attempt, case_id, use_dataset_label)
    case, messages = prep["case"], prep["messages"]

    # Fail loudly instead of letting Ollama silently drop the start of the prompt.
    if prep["prompt_tokens"] + NUM_PREDICT > NUM_CTX:
        raise NarrativeGenerationError(
            f"Prompt (~{prep['prompt_tokens']} tokens) + output ({NUM_PREDICT}) exceeds "
            f"num_ctx={NUM_CTX}; raise NUM_CTX or trim the prompt."
        )

    from langchain_ollama import ChatOllama

    result, model_used, seed_used = "", "", None
    failures: list[str] = []
    # Try each model; re-sample once with a new seed before falling back.
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        for attempt in range(ATTEMPTS_PER_MODEL):
            label = f"{model_name} (attempt {attempt + 1})"
            try:
                if verbose:
                    print(f"  Trying {label}...", flush=True)

                extra_kwargs = {}
                # Disable Qwen's thinking mode to prevent empty outputs
                if "qwen" in model_name.lower():
                    extra_kwargs["think"] = False

                llm = ChatOllama(
                    model=model_name,
                    base_url=OLLAMA_URL,
                    temperature=TEMPERATURE,
                    num_ctx=NUM_CTX,
                    num_predict=NUM_PREDICT,
                    seed=SEED + attempt,
                    keep_alive="10m",
                    **extra_kwargs,
                )
                reply = llm.invoke(messages)
                # Strip any <think>...</think> blocks from output
                text = re.sub(r"<think>.*?</think>", "", reply.content, flags=re.DOTALL).strip()
                problems = validate_narrative(
                    text, reply.response_metadata.get("done_reason"), prep["pattern"],
                    no_sar=prep["no_sar"])
            except Exception as e:  # noqa: BLE001 — model missing, Ollama down, etc.
                problems = [f"error: {e}"]

            if not problems:
                result, model_used, seed_used = text, model_name, SEED + attempt
                if verbose:
                    print(f"  ✓ Generated with {label}", flush=True)
                break
            failures.append(f"{label}: {'; '.join(problems)}")
            if verbose:
                print(f"  ✗ {failures[-1]}", flush=True)
        if model_used:
            break

    if not model_used:
        raise NarrativeGenerationError(
            "No usable narrative was produced:\n- " + "\n- ".join(failures)
        )

    generation_time = time.time() - start_time
    generation_config = {
        "model": model_used,
        "fallback_model": FALLBACK_MODEL,
        "temperature": TEMPERATURE,
        "num_ctx": NUM_CTX,
        "num_predict": NUM_PREDICT,
        "seed": seed_used,
        "prompt_version": PROMPT_VERSION,
        "input_fingerprint": case.fingerprint(),
        "prompt_tokens_estimate": prep["prompt_tokens"],
        "few_shot_examples": FEW_SHOT_FILES,
        "rejected_attempts": failures,
        "pattern_source": ("analyst" if case.pattern_override and not use_dataset_label
                           else "dataset label" if use_dataset_label else "rule-based detection"),
    }

    audit_record = build_audit_record(
        case_id=case_id or case.case_id,
        attempt_id=case.attempt_id,
        pattern_type=prep["pattern"],
        model_used=model_used,
        generation_time=generation_time,
        narrative_text=result,
        retrieval_metadata=prep["retrieval_meta"],
        chunk_texts=prep["chunk_texts"],
        txn_df=case.transactions,
        case_facts=case.case_facts(),
        detection=prep["detection"].to_dict(),
        red_flags=[f.to_dict() for f in prep["flags"]],
        generation_config=generation_config,
        case_source=case.source,
    )
    return result, audit_record


def generate(attempt_id: int, verbose: bool = False) -> str:
    """Backwards-compatible — returns only the narrative text."""
    result, _ = generate_with_audit(attempt_id, verbose=verbose)
    return result


def generate_and_save(
    attempt_id: int,
    case_id: str,
    verbose: bool = True,
    save_audit: bool = True,
) -> Path:
    """
    Generate a narrative for a dataset attempt and save it to generated/.
    Also saves audit trail (JSON + provenance report) if save_audit=True.
    Uses the dataset label as the pattern so evaluation stays comparable.
    """
    from audit_trail import save_audit_record, save_provenance_report

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    narrative, audit_record = generate_with_audit(
        attempt_id, case_id=case_id, verbose=verbose, use_dataset_label=True,
    )

    output_path = GENERATED_DIR / f"{case_id}_generated.md"
    header = f"# Generated SAR Narrative — Case {case_id}\n\n"
    header += f"**Pattern:** {audit_record.pattern_type}  \n"
    header += f"**Attempt #:** {attempt_id}  \n"
    header += f"**Model:** {audit_record.model_used} (fallback: {FALLBACK_MODEL})  \n\n---\n\n"

    output_path.write_text(header + narrative, encoding="utf-8")

    if verbose:
        print(f"  → Saved narrative to {output_path}")

    if save_audit:
        audit_path = save_audit_record(audit_record)
        report_path = save_provenance_report(audit_record)
        if verbose:
            print(f"  → Saved audit record to {audit_path}")
            print(f"  → Saved provenance report to {report_path}")

    return output_path


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        case_id = sys.argv[1]
        attempt_id = CASE_TO_ATTEMPT.get(case_id)
        if attempt_id is None:
            print(f"Unknown case ID: {case_id}")
            print(f"Valid cases: {sorted(CASE_TO_ATTEMPT.keys())}")
            sys.exit(1)
    else:
        # Default: generate for case 002 (first evaluation case)
        case_id = "002"
        attempt_id = CASE_TO_ATTEMPT["002"]

    print(f"Generating narrative for Case {case_id} (attempt #{attempt_id})...")
    generate_and_save(attempt_id, case_id)
    print("Done.")
