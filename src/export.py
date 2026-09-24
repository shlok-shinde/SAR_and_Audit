"""
export.py — What leaves the tool: a filing-ready narrative and the case file.

  fincen_narrative(markdown)  → plain text for FinCEN SAR Part V
  case_file_markdown(...)     → the whole case as Markdown (for the record)
  case_file_html(...)         → the same, printable (browser → Print → PDF)
  audit_json(audit)           → the machine-readable audit record

FinCEN's Part V narrative is plain text: at most 20 records of 850 characters
(BSA E-Filing "Narrative Description (5A)" record) = 17,000 characters, and
no Markdown survives the form. Anything longer must be trimmed or attached.
"""

from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, timezone

import pandas as pd

FINCEN_NARRATIVE_LIMIT = 17_000   # 20 × 850-character narrative records

_TABLE_SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


def fincen_narrative(markdown: str) -> str:
    """Markdown narrative → plain text: headings in capitals, no markup."""
    out: list[str] = []
    for raw in markdown.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if _TABLE_SEP.match(line) or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", line):
            continue
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading:
            if out and out[-1] != "":
                out.append("")
            out.append(re.sub(r"[*_`]", "", heading.group(1)).upper())
            continue
        if line.startswith("|"):
            line = "; ".join(c.strip() for c in line.strip("|").split("|") if c.strip())
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", line)
        line = line.replace("`", "")
        line = re.sub(r"^[-*+]\s+", "- ", line)
        out.append(line)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def narrative_length(markdown: str) -> tuple[int, int]:
    """(characters in the filing text, FinCEN limit)."""
    return len(fincen_narrative(markdown)), FINCEN_NARRATIVE_LIMIT


STATUS_LABELS = {"grounded": "sourced", "partial": "partly sourced", "ungrounded": "unsourced",
                 "unverified": "unverified"}


def _status_of(sent) -> str:
    from audit_trail import grounding_status
    return STATUS_LABELS[grounding_status(sent)]


def case_file_markdown(case, audit, narrative: str, meta: dict) -> str:
    """The complete case record: facts, analysis, narrative, audit, decision, history."""
    s, a, inv = case.subject, case.alert, case.investigation
    lines = [
        f"# SAR case file — {meta.get('case_id', case.case_id)}",
        "",
        f"- **Status:** {meta.get('status', 'Pending')}"
        + (f" · **Decision:** {meta['decision']}" if meta.get("decision") else ""),
        f"- **Source:** {case.source}" + (f" (IBM AML attempt #{case.attempt_id})"
                                          if case.attempt_id is not None else ""),
        f"- **Drafted by:** {meta.get('drafted_by') or '—'} · **Approved by:** "
        f"{meta.get('approved_by') or '—'}",
        f"- **Filing due:** {meta.get('filing_due') or '—'}",
        f"- **Exported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    if meta.get("decision_rationale"):
        lines += ["## Decision rationale", "", meta["decision_rationale"], ""]
    if meta.get("reviewer_notes"):
        lines += ["## Reviewer notes", "", meta["reviewer_notes"], ""]

    facts = [("Name", s.name), ("Type", s.subject_type), ("Occupation / business", s.occupation),
             ("Country", s.country), ("Address", s.address), ("Accounts", ", ".join(s.accounts)),
             ("Relationship since", s.account_opened),
             ("Expected monthly volume", f"${s.expected_monthly_volume:,.2f}"
              if s.expected_monthly_volume else ""),
             ("Expected monthly transactions", s.expected_monthly_count or ""),
             ("Risk rating", s.risk_rating)]
    facts = [(k, v) for k, v in facts if v]
    if facts:
        lines += ["## Subject", ""] + [f"- **{k}:** {v}" for k, v in facts] + [""]
    alert = [(k, v) for k, v in (("Source", a.source), ("Alert ID", a.alert_id),
                                 ("Detected on", a.detected_on), ("Description", a.description)) if v]
    if alert:
        lines += ["## Alert", ""] + [f"- **{k}:** {v}" for k, v in alert] + [""]
    if inv.steps or inv.findings or inv.ruled_out:
        lines += ["## Investigation", ""]
        lines += [f"- [x] {step}" for step in inv.steps]
        if inv.findings:
            lines += ["", f"**Findings:** {inv.findings}"]
        if inv.ruled_out:
            lines += ["", f"**Ruled out:** {inv.ruled_out}"]
        lines.append("")
    prior = [p for p in case.prior_sars if p.filed_on or p.reference]
    if prior:
        lines += ["## Prior SARs", ""] + [
            f"- {p.filed_on} · {p.reference} · "
            f"{f'${p.amount:,.2f}' if p.amount else ''} · {p.period_start} – {p.period_end}"
            for p in prior] + [""]

    det = audit.detection if audit else {}
    if det:
        lines += ["## Typology (rule-based)", "",
                  f"**{det.get('pattern')}** ({det.get('confidence')} confidence)", ""]
        lines += [f"- {e}" for e in det.get("evidence", [])] + [""]
    if audit and audit.red_flags:
        lines += ["## Red flags", ""] + [
            f"- **[{f.get('severity', '').upper()}] {f.get('title')}** — {f.get('evidence')}"
            for f in audit.red_flags] + [""]

    lines += ["## Narrative", "", narrative.strip(), ""]

    df = case.flagged()
    lines += ["## Transactions in scope", "",
              "| Date | From | To | Paid | Received | Method |", "|---|---|---|---|---|---|"]
    for _, r in df.sort_values("Timestamp").iterrows():
        lines.append(
            f"| {r['Timestamp']} | {r['From_Account']} ({r['From_Entity_Name']}) | "
            f"{r['To_Account']} ({r['To_Entity_Name']}) | {r['Amount Paid']:,.2f} "
            f"{r['Payment Currency']} | {r['Amount Received']:,.2f} {r['Receiving Currency']} | "
            f"{r['Payment Format']} |")
    lines.append("")

    if audit:
        lines += ["## Audit trail (sentence-level provenance)", ""]
        for sent in audit.narrative_sentences:
            status = _status_of(sent)
            lines.append(f"- **S{sent.sentence_index} · {sent.section} · {status}** — "
                         f"{sent.sentence_text}")
            if sent.field_references:
                lines.append("  - Data: " + "; ".join(
                    f"{r.field_name} = {r.field_value} ({r.match_type})"
                    for r in sent.field_references))
            if sent.chunk_attributions:
                lines.append("  - Regulatory context: " + ", ".join(sent.chunk_attributions))
            if getattr(sent, "rule_attributions", None):
                lines.append("  - Red-flag rules: " + ", ".join(sent.rule_attributions))
            if getattr(sent, "unverified_values", None):
                lines.append("  - NOT IN CASE DATA: " + "; ".join(
                    f"{u.field_value}" + (f" ({u.note})" if u.note else "")
                    for u in sent.unverified_values))
        lines.append("")
        cfg = audit.generation_config
        if cfg:
            lines += ["## Generation record (model risk / reproducibility)", ""] + [
                f"- **{k}:** {v}" for k, v in cfg.items() if k != "rejected_attempts"]
            if cfg.get("rejected_attempts"):
                lines.append("- **rejected attempts:** " + " | ".join(cfg["rejected_attempts"]))
            lines.append("")
        if audit.retrieval_metadata:
            lines += ["## Retrieved regulatory sources", ""] + [
                f"- `{c.chunk_id}` {c.source_file} p.{c.page_number} "
                f"(relevance {c.relevance_score:.2f})"
                for c in audit.retrieval_metadata.chunks_returned] + [""]

    events = meta.get("events") or []
    if events:
        lines += ["## Case history", ""] + [
            f"- {e.get('at')} · {e.get('actor') or '—'} · {e.get('action')}" for e in events] + [""]
    return "\n".join(lines)


_HTML_CSS = """
body { font: 14px/1.55 -apple-system, "Segoe UI", Inter, sans-serif; color: #1d1d1f; max-width: 880px;
  margin: 32px auto; padding: 0 20px; }
h1 { font-size: 22px; margin: 0 0 12px; } h2 { font-size: 15px; margin: 26px 0 8px;
  border-bottom: 1px solid #ddd; padding-bottom: 4px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; }
th, td { border: 1px solid #ddd; padding: 4px 6px; text-align: left; vertical-align: top; }
code { font-size: 12px; } li { margin: 2px 0; }
.bad { color: #b3261e; font-weight: 600; }
@media print { body { margin: 0; } h2 { break-after: avoid; } }
"""


def case_file_html(case, audit, narrative: str, meta: dict) -> str:
    """Printable HTML version of case_file_markdown (no external assets)."""
    md = case_file_markdown(case, audit, narrative, meta)
    body: list[str] = []
    in_list = in_table = False
    for raw in md.split("\n"):
        line = raw.rstrip()
        if in_table and not line.startswith("|"):
            body.append("</table>")
            in_table = False
        if in_list and not line.startswith(("- ", "  - ")):
            body.append("</ul>")
            in_list = False
        if not line:
            continue
        esc = html.escape(line)
        esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
        esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
        esc = esc.replace("NOT IN CASE DATA", '<span class="bad">NOT IN CASE DATA</span>')
        if line.startswith("# "):
            body.append(f"<h1>{esc[2:]}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{esc[3:]}</h2>")
        elif line.startswith("### "):
            body.append(f"<h3>{esc[4:]}</h3>")
        elif line.startswith("|"):
            if _TABLE_SEP.match(line):
                continue
            cells = [c.strip() for c in esc.strip("|").split("|")]
            tag = "th" if not in_table else "td"
            if not in_table:
                body.append("<table>")
                in_table = True
            body.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif line.startswith(("- ", "  - ")):
            if not in_list:
                body.append("<ul>")
                in_list = True
            indent = ' style="margin-left:18px;list-style:circle"' if line.startswith("  - ") else ""
            body.append(f"<li{indent}>{esc.strip()[2:]}</li>")
        else:
            body.append(f"<p>{esc}</p>")
    if in_table:
        body.append("</table>")
    if in_list:
        body.append("</ul>")
    title = html.escape(f"SAR case file {meta.get('case_id', case.case_id)}")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>{_HTML_CSS}</style></head><body>{''.join(body)}</body></html>")


def audit_json(audit) -> str:
    return audit.to_json() if audit else "{}"


def filing_due(detected_on, days: int = 30) -> date | None:
    """FinCEN: file within 30 calendar days of initial detection of the facts."""
    from case_input import parse_iso_date
    d = parse_iso_date(detected_on)
    return d + pd.Timedelta(days=days).to_pytimedelta() if d else None


def continuing_due(prior_sars) -> date | None:
    """Continuing activity: 90-day review + 30 days to file = 120 days after the last SAR."""
    from case_input import parse_iso_date
    dates = [parse_iso_date(p.filed_on) for p in prior_sars if p.filed_on]
    dates = [d for d in dates if d]
    return max(dates) + pd.Timedelta(days=120).to_pytimedelta() if dates else None


def export_bundle(case, audit, narrative: str, meta: dict) -> dict[str, tuple[str, str, str]]:
    """name → (label, content, mime) for every export."""
    cid = meta.get("case_id", case.case_id)
    return {
        "narrative": ("FinCEN narrative (.txt)", fincen_narrative(narrative), "text/plain"),
        "html": ("Case file (.html, printable)", case_file_html(case, audit, narrative, meta),
                 "text/html"),
        "md": ("Case file (.md)", case_file_markdown(case, audit, narrative, meta),
               "text/markdown"),
        "json": ("Audit trail (.json)", audit_json(audit), "application/json"),
        "_names": (f"{cid}_narrative.txt", f"{cid}_case_file.html", f"{cid}_case_file.md",
                   f"{cid}_audit.json"),
    }


def events_to_dicts(rows) -> list[dict]:
    out = []
    for r in rows or []:
        at = r.get("at")
        out.append({**r, "at": at.strftime("%Y-%m-%d %H:%M") if hasattr(at, "strftime") else at})
    return out


def dumps(obj) -> str:
    return json.dumps(obj, indent=2, default=str)
