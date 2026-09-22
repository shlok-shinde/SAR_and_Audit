"""
review_components.py — Custom Streamlit components for the review workspace.

Two st.components.v2 components render the side-by-side review panes:

  * draft_pane — the narrative as a formatted document. In "preview" mode each
    audited sentence is clickable; in "edit" mode the same document becomes a
    Word-style rich-text editor (toolbar + shortcuts) that writes Markdown back
    to Python, so reviewers never have to touch Markdown syntax.
  * audit_pane — sentence-level provenance cards grouped by FFIEC section.

Both panes are driven by the *live* audit record (rebuilt after every edit) and
a baseline (as generated / loaded), so reviewer changes are tracked: edited and
added sentences are marked in the draft and on their cards, and removed claims
stay listed in the trail.

The panes talk to each other through a window-level "sar-sentence" event:
clicking a sentence in the draft scrolls to and highlights its audit card, and
clicking an audit card does the reverse. Only Markdown constructs the
generator produces (headings, bold/italic/code, rules, lists, hard breaks) are
supported, which keeps the Markdown <-> document round trip lossless.
"""

from __future__ import annotations

import hashlib
import re

import streamlit as st

from audit_trail import (
    TABLE_SEPARATOR_PATTERN, AuditRecord, diff_provenance, grounding_status, is_table_row,
    table_cells,
)

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^\d+[.)]\s+(.*)$")
_RULE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")


# ── Python-side data shaping ──────────────────────────────────────────────────

def reviewer_changes(audit: AuditRecord | None,
                     baseline: AuditRecord | None) -> tuple[dict[int, dict], list]:
    """Edited/added sentences in `audit` and sentences removed since `baseline`."""
    if audit is None or baseline is None or audit is baseline:
        return {}, []
    return diff_provenance(baseline.narrative_sentences, audit.narrative_sentences)


def _link_sentences(line: str, sentences: list, used: set[int],
                    changes: dict[int, dict]) -> list[dict]:
    """Split one Markdown line into segments, tagging audited sentences by index.

    Audit sentences are verbatim slices of narrative lines (see
    parse_narrative_into_sentences), so exact substring matching is reliable.
    Sentences that no longer match (text edited since the audit) stay unlinked.
    """
    hits = []
    for sent in sentences:
        if sent.sentence_index in used:
            continue
        pos = line.find(sent.sentence_text)
        if pos >= 0:
            hits.append((pos, pos + len(sent.sentence_text), sent))
    hits.sort(key=lambda h: h[0])

    segments, cursor = [], 0
    for start, end, sent in hits:
        if start < cursor:  # overlapping match; keep the earlier one
            continue
        if start > cursor:
            segments.append({"md": line[cursor:start]})
        segments.append({"md": line[start:end], "s": sent.sentence_index,
                         "g": grounding_status(sent),
                         "c": changes.get(sent.sentence_index, {}).get("kind", "")})
        used.add(sent.sentence_index)
        cursor = end
    if cursor < len(line):
        segments.append({"md": line[cursor:]})
    return segments


def narrative_blocks(markdown: str, audit: AuditRecord | None,
                     changes: dict[int, dict] | None = None) -> list[dict]:
    """Parse narrative Markdown into render blocks with sentence links."""
    sentences = list(audit.narrative_sentences) if audit else []
    changes = changes or {}
    used: set[int] = set()
    blocks: list[dict] = []
    para: list[dict] = []   # lines of the paragraph being collected
    listing: dict | None = None

    def flush() -> None:
        nonlocal para, listing
        if para:
            blocks.append({"type": "p", "lines": para})
            para = []
        if listing:
            blocks.append(listing)
            listing = None

    lines = markdown.split("\n")
    pos = 0
    while pos < len(lines):
        raw = lines[pos]
        line = raw.strip()
        pos += 1
        if not line:
            flush()
            continue
        # Table: header row followed by a separator row, then data rows.
        if (is_table_row(line) and pos < len(lines)
                and TABLE_SEPARATOR_PATTERN.match(lines[pos].strip())):
            flush()
            table = {"type": "table", "head": table_cells(line), "rows": []}
            pos += 1  # separator
            while pos < len(lines) and is_table_row(lines[pos].strip()):
                row = lines[pos].strip()
                pos += 1
                linked = _link_sentences(row, sentences, used, changes)
                sent = next((g for g in linked if "s" in g and g["md"] == row), None)
                table["rows"].append({
                    "cells": table_cells(row),
                    **({"s": sent["s"], "g": sent["g"], "c": sent["c"]} if sent else {}),
                })
            blocks.append(table)
            continue
        if _RULE.match(line):
            flush()
            blocks.append({"type": "hr"})
            continue
        if m := _HEADING.match(line):
            flush()
            level = min(len(m.group(1)), 3)
            blocks.append({"type": f"h{level}",
                           "segments": _link_sentences(m.group(2), sentences, used, changes)})
            continue
        list_match = _BULLET.match(line) or _NUMBERED.match(line)
        if list_match:
            kind = "ul" if _BULLET.match(line) else "ol"
            if para or (listing and listing["type"] != kind):
                flush()
            listing = listing or {"type": kind, "items": []}
            listing["items"].append(_link_sentences(list_match.group(1), sentences, used, changes))
            continue
        if listing:
            flush()
        # Every source line keeps its own line: generated narratives put one
        # labelled fact per line ("**Account Numbers:** …"), which strict
        # Markdown would run together into a single paragraph.
        para.append({"segments": _link_sentences(line, sentences, used, changes), "br": True})
    flush()
    return blocks


def table_headers(markdown: str) -> dict[str, list[str]]:
    """Map each table data row (stripped line) to its table's header cells."""
    headers: dict[str, list[str]] = {}
    lines = [ln.strip() for ln in markdown.split("\n")]
    current: list[str] | None = None
    for pos, line in enumerate(lines):
        if not is_table_row(line):
            current = None
            continue
        if TABLE_SEPARATOR_PATTERN.match(line):
            continue
        nxt = lines[pos + 1] if pos + 1 < len(lines) else ""
        if TABLE_SEPARATOR_PATTERN.match(nxt):
            current = table_cells(line)
        elif current:
            headers[line] = current
    return headers


def _row_cells(text: str, headers: dict[str, list[str]]) -> list[dict]:
    if not is_table_row(text):
        return []
    head = headers.get(text.strip(), [])
    return [{"h": head[k] if k < len(head) else "", "v": v}
            for k, v in enumerate(table_cells(text))]


def audit_payload(audit: AuditRecord | None, baseline: AuditRecord | None = None,
                  markdown: str = "") -> dict:
    """Serialize the audit record into what the audit pane renders."""
    if audit is None:
        return {"empty": True}
    changes, removed = reviewer_changes(audit, baseline)
    headers = table_headers(markdown)
    sections: list[dict] = []
    counts = {"grounded": 0, "partial": 0, "ungrounded": 0, "unverified": 0}
    flag_titles = {f.get("code"): f.get("title", f.get("code")) for f in audit.red_flags}
    for sent in audit.narrative_sentences:
        status = grounding_status(sent)
        counts[status] += 1
        if not sections or sections[-1]["name"] != sent.section:
            sections.append({"name": sent.section, "items": []})
        sections[-1]["items"].append({
            "i": sent.sentence_index,
            "text": sent.sentence_text,
            "cells": _row_cells(sent.sentence_text, headers),
            "status": status,
            "data": [{"f": r.field_name, "v": str(r.field_value), "m": r.match_type}
                     for r in sent.field_references],
            "context": list(sent.chunk_attributions),
            "rules": [flag_titles.get(c, c) for c in getattr(sent, "rule_attributions", [])],
            "unverified": [{"v": str(u.field_value), "n": u.note}
                           for u in getattr(sent, "unverified_values", [])],
            "typology": sent.typology_match or "",
            "confidence": sent.confidence_note,
            "change": changes.get(sent.sentence_index, {}).get("kind", ""),
            "was": changes.get(sent.sentence_index, {}).get("was", ""),
        })

    chunks = []
    if rm := audit.retrieval_metadata:
        chunks = [{
            "id": c.chunk_id, "source": c.source_file, "page": c.page_number,
            "query": c.query_type, "relevance": round(c.relevance_score, 2),
            "preview": c.text_preview,
        } for c in rm.chunks_returned]

    return {
        "counts": counts,
        "total": len(audit.narrative_sentences),
        "sections": sections,
        "chunks": chunks,
        "dedup": audit.retrieval_metadata.dedup_count if audit.retrieval_metadata else 0,
        "removed": [{"text": r.sentence_text, "section": r.section,
                     "status": grounding_status(r)} for r in removed],
        "edits": {"edited": sum(c["kind"] == "edited" for c in changes.values()),
                  "added": sum(c["kind"] == "added" for c in changes.values()),
                  "removed": len(removed)},
        "flags": [{"t": f.get("title", ""), "s": f.get("severity", ""), "e": f.get("evidence", "")}
                  for f in audit.red_flags],
        "detection": ({"p": audit.detection.get("pattern", ""),
                       "c": audit.detection.get("confidence", ""),
                       "e": audit.detection.get("evidence", [])} if audit.detection else None),
        "queries": ([audit.retrieval_metadata.label_query,
                     audit.retrieval_metadata.description_query]
                    if audit.retrieval_metadata else []),
    }


# ── Shared browser code ───────────────────────────────────────────────────────

# Inline Markdown -> HTML for the subset the generator emits. HTML is escaped
# first, so model output can never inject markup.
_INLINE_JS = r"""
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const inlineMd = (md) => esc(md)
  .replace(/`([^`]+)`/g, "<code>$1</code>")
  .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
  .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
"""

_SCROLL_JS = r"""
// Smooth-scroll a pane, then snap if the browser skipped the animation
// (some embedded/throttled views never run smooth scrolling).
const scrollPane = (pane, top) => {
  top = Math.max(0, Math.min(top, pane.scrollHeight - pane.clientHeight));
  pane.scrollTo({ top, behavior: "smooth" });
  setTimeout(() => { if (Math.abs(pane.scrollTop - top) > 2) pane.scrollTop = top; }, 600);
};
"""

_SHARED_CSS = """
:host {
  display: block; height: 100%; color: inherit; font: inherit;
  --surface: #2B2B2B; --surface-2: #313131; --well: #212121;
  --line: rgb(255 255 255 / .07); --line-2: rgb(255 255 255 / .12);
  --text: #EDEDED; --text-2: #A3A3A3; --text-3: #767676;
  --ok: #6BC495; --warn: #D9AE5B; --bad: #E2826F; --info: #8FB3E8;
  --mono: 'Geist Mono', 'JetBrains Mono', ui-monospace, monospace;
}
.frame {
  box-sizing: border-box; height: 100%; display: flex; flex-direction: column;
  border: 1px solid var(--line); border-radius: 12px; background: var(--surface);
  overflow: hidden; transition: border-color .15s ease, box-shadow .15s ease;
}
.scroll {
  flex: 1; min-height: 0; overflow-y: auto; position: relative;
  scrollbar-width: thin; scrollbar-color: rgb(255 255 255 / .14) transparent;
}
.bar {
  display: flex; align-items: center; gap: 8px; min-height: 42px; box-sizing: border-box;
  padding: 6px 10px 6px 16px; border-bottom: 1px solid var(--line); flex: none;
}
.muted { font-size: 12px; color: var(--text-3); }
.flash { animation: flash 1.4s ease-out; }
@keyframes flash { 0% { background-color: rgb(143 179 232 / .20); } }
@media (prefers-reduced-motion: reduce) { .flash { animation: none; } }
code { font-family: var(--mono); }
"""


# ── Draft pane ────────────────────────────────────────────────────────────────

_DRAFT_CSS = _SHARED_CSS + """
.wrap { height: 100%; container-type: inline-size; }
.toolbar { display: none; align-items: center; gap: 2px; flex-wrap: wrap; width: 100%; }
.preview-bar { display: flex; align-items: center; gap: 12px; width: 100%; min-width: 0; }
.preview-bar .muted { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.wrap.editing .toolbar { display: flex; }
.wrap.editing .preview-bar { display: none; }
.wrap.editing .frame { border-color: rgb(143 179 232 / .45); box-shadow: 0 0 0 3px rgb(143 179 232 / .10); }
.toolbar button, .toolbar select {
  font: inherit; font-size: 13px; color: var(--text-2); background: transparent; border: none;
  border-radius: 6px; min-width: 30px; height: 28px; padding: 0 8px; cursor: pointer;
}
.toolbar select { padding-right: 4px; color: var(--text); }
.toolbar select option { background: #2E2E2E; }
.toolbar button:hover, .toolbar select:hover { background: rgb(255 255 255 / .06); color: var(--text); }
.toolbar button.on { background: rgb(255 255 255 / .10); color: var(--text); }
.toolbar .sep { width: 1px; height: 16px; margin: 0 4px; background: var(--line-2); }
.hint { margin-left: auto; font-size: 11.5px; color: var(--text-3); padding-right: 4px; }
@container (max-width: 560px) { .hint { display: none; } }

/* Highlight-grounding switch */
.switch { flex: none; margin-left: auto; display: inline-flex; align-items: center; gap: 8px; cursor: pointer;
  font-size: 12px; color: var(--text-2); user-select: none; border: none; background: none;
  font-family: inherit; padding: 4px 6px; border-radius: 6px; }
.switch:hover { color: var(--text); }
.switch .track { width: 26px; height: 16px; border-radius: 999px; background: #3A3A3A;
  position: relative; transition: background .15s ease; }
.switch .track::after { content: ""; position: absolute; top: 2px; left: 2px; width: 12px; height: 12px;
  border-radius: 50%; background: #BDBDBD; transition: transform .15s ease, background .15s ease; }
.switch[aria-checked="true"] .track { background: var(--text); }
.switch[aria-checked="true"] .track::after { transform: translateX(10px); background: #1F1F1F; }
.legend { display: none; flex: none; gap: 12px; font-size: 11.5px; color: var(--text-3); }
.legend > span { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
.legend i { display: block; width: 7px; height: 7px; border-radius: 50%; }
.hl-on .legend { display: inline-flex; }
.hl-on .preview-bar .muted { flex-basis: 0; }
/* Responsive bar: drop the legend first, then the hint; the switch always fits */
@container (max-width: 520px) { .legend { display: none !important; } }
@container (max-width: 400px) { .preview-bar .muted { display: none; } }
.switch { white-space: nowrap; }

/* Document typography */
.doc { max-width: 74ch; padding: 22px 28px 48px; line-height: 1.7; font-size: 14.5px;
  color: #D9D9D9; outline: none; caret-color: var(--text); }
.doc h1 { font-size: 20px; font-weight: 600; letter-spacing: -.015em; color: var(--text);
  margin: 2px 0 14px; line-height: 1.3; }
.doc h2 { font-size: 15px; font-weight: 600; color: var(--text); margin: 28px 0 6px; }
.doc h3 { font-size: 11.5px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase;
  color: var(--text-2); margin: 24px 0 6px; }
.doc p { margin: 0 0 10px; }
.doc strong { color: var(--text); font-weight: 600; }
.doc hr { border: none; border-top: 1px solid var(--line); margin: 18px 0; }
.doc code { font-size: 12.5px; background: var(--well); padding: 1px 5px; border-radius: 5px; }
.doc ul, .doc ol { margin: 0 0 10px; padding-left: 22px; }

/* Tables (e.g. transaction ledgers) */
.tw { overflow-x: auto; margin: 6px 0 16px; border: 1px solid var(--line); border-radius: 10px;
  scrollbar-width: thin; }
.doc table { border-collapse: collapse; width: 100%; min-width: 560px; font-size: 12.5px; line-height: 1.45;
  font-variant-numeric: tabular-nums; }
.doc th { text-align: left; font-size: 10.5px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--text-3); padding: 9px 12px; white-space: nowrap;
  border-bottom: 1px solid var(--line); background: rgb(255 255 255 / .02); }
.doc td { padding: 8px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
.doc tbody tr:last-child td { border-bottom: none; }
.doc tr.s { box-shadow: none !important; background: none !important; text-decoration: none; }
.doc tr.s:hover td { background: rgb(255 255 255 / .04); }
.doc tr.s.active td { background: rgb(143 179 232 / .14); }
.hl-on .doc tr.s.grounded td { background: rgb(107 196 149 / .07); }
.hl-on .doc tr.s.partial td { background: rgb(217 174 91 / .08); }
.hl-on .doc tr.s.ungrounded td { background: rgb(226 130 111 / .10); }
.doc tr.s.unverified td { text-decoration: underline wavy rgb(226 130 111 / .9);
  text-decoration-thickness: 1px; text-underline-offset: 3px; }
.hl-on .doc tr.s.active td { background: rgb(143 179 232 / .16); }
.wrap.editing .doc tr.s td { background: none; }
.doc tr.s.edited td, .doc tr.s.added td { text-decoration: underline dotted rgb(143 179 232 / .8);
  text-decoration-thickness: 1.5px; text-underline-offset: 4px; }

/* Linked sentences */
.s { border-radius: 3px; cursor: pointer; transition: background-color .15s ease, box-shadow .15s ease;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.s:hover { background: rgb(255 255 255 / .06); }
.s.active { background: rgb(143 179 232 / .16); box-shadow: 0 0 0 2px rgb(143 179 232 / .16); }
.hl-on .s.grounded   { box-shadow: inset 0 -2px 0 rgb(107 196 149 / .55); }
.hl-on .s.partial    { box-shadow: inset 0 -2px 0 rgb(217 174 91 / .6); }
.hl-on .s.ungrounded { background: rgb(226 130 111 / .10); box-shadow: inset 0 -2px 0 rgb(226 130 111 / .7); }
/* Figures not in the case data: always visible, like a spell-check squiggle */
.s.unverified { text-decoration: underline wavy rgb(226 130 111 / .9); text-decoration-thickness: 1px;
  text-underline-offset: 3px; }
.hl-on .s.unverified { background: rgb(226 130 111 / .12); }
/* Reviewer changes, like tracked changes */
.s.edited, .s.added { text-decoration: underline dotted rgb(143 179 232 / .8);
  text-decoration-thickness: 1.5px; text-underline-offset: 4px; }
.wrap.editing .s { cursor: text; background: none !important; box-shadow: none !important; }
"""

_DRAFT_JS = _INLINE_JS + _SCROLL_JS + r"""
// Document model -> HTML (blocks come from narrative_blocks in Python).
const segHtml = (segs) => segs.map((g) => g.s === undefined
  ? inlineMd(g.md)
  : `<span class="s ${g.g} ${g.c}" data-s="${g.s}"${g.c ? ` title="${g.c === "added" ? "Added" : "Edited"} by reviewer"` : ""}>${inlineMd(g.md)}</span>`).join("");

function renderBlocks(blocks) {
  return blocks.map((b) => {
    if (b.type === "hr") return "<hr>";
    if (b.type === "p") return "<p>" + b.lines.map((l, i) =>
      segHtml(l.segments) + (i < b.lines.length - 1 ? (l.br ? "<br>" : " ") : "")).join("") + "</p>";
    if (b.type === "table") return `<div class="tw"><table><thead><tr>` +
      b.head.map((h) => `<th>${inlineMd(h)}</th>`).join("") + `</tr></thead><tbody>` +
      b.rows.map((r) => `<tr${r.s === undefined ? "" : ` class="s ${r.g} ${r.c || ""}" data-s="${r.s}"`}>` +
        r.cells.map((c) => `<td>${inlineMd(c)}</td>`).join("") + `</tr>`).join("") +
      `</tbody></table></div>`;
    if (b.type === "ul" || b.type === "ol")
      return `<${b.type}>` + b.items.map((it) => `<li>${segHtml(it)}</li>`).join("") + `</${b.type}>`;
    return `<${b.type}>${segHtml(b.segments)}</${b.type}>`;
  }).join("");
}

// Edited document -> Markdown (inverse of the renderer above).
function inlineToMd(node) {
  let out = "";
  for (const n of node.childNodes) {
    if (n.nodeType === 3) { out += n.textContent.replace(/\u00a0/g, " "); continue; }
    if (n.nodeType !== 1) continue;
    const tag = n.tagName, inner = inlineToMd(n);
    if (tag === "BR") out += "  \n";
    else if (!inner.trim()) out += inner;
    else if (tag === "STRONG" || tag === "B") out += `**${inner.trim()}**`;
    else if (tag === "EM" || tag === "I") out += `*${inner.trim()}*`;
    else if (tag === "CODE") out += "`" + inner + "`";
    else out += inner;
  }
  return out;
}
const BLOCK = /^(P|DIV|H[1-6]|UL|OL|HR|BLOCKQUOTE|TABLE)$/;
const cellMd = (td) => inlineToMd(td).replace(/\s*\n\s*/g, " ").trim();
const rowMd = (tr) => "| " + [...tr.children].map(cellMd).join(" | ") + " |";
function tableToMd(table) {
  const rows = [...table.querySelectorAll("tr")].filter((tr) => tr.children.length);
  if (!rows.length) return "";
  const head = rows[0];
  const sep = "| " + [...head.children].map(() => "---").join(" | ") + " |";
  return [rowMd(head), sep, ...rows.slice(1).map(rowMd)].join("\n");
}
function blocksToMd(root) {
  const out = [];
  let loose = null;   // stray inline nodes at block level become a paragraph
  const flushLoose = () => { if (loose) { const t = inlineToMd(loose).trim(); if (t) out.push(t); loose = null; } };
  for (const n of root.childNodes) {
    if (n.nodeType === 1 && BLOCK.test(n.tagName)) {
      flushLoose();
      const tag = n.tagName;
      if (tag === "HR") out.push("---");
      else if (tag === "TABLE") { const t = tableToMd(n); if (t) out.push(t); }
      else if (/^H[1-6]$/.test(tag)) {
        const t = inlineToMd(n).trim();
        if (t) out.push("#".repeat(+tag[1]) + " " + t);
      } else if (tag === "UL" || tag === "OL") {
        const items = [...n.children].filter((c) => c.tagName === "LI")
          .map((li, i) => (tag === "UL" ? "- " : `${i + 1}. `) + inlineToMd(li).trim());
        if (items.length) out.push(items.join("\n"));
      } else if (tag === "DIV" && [...n.children].some((c) => BLOCK.test(c.tagName))) {
        const nested = blocksToMd(n);
        if (nested) out.push(nested);
      } else {
        const t = inlineToMd(n).replace(/[ \t]+$/gm, (m) => m === "  " ? m : "").trim();
        if (t) out.push(t);
      }
    } else {
      loose = loose || document.createElement("p");
      loose.appendChild(n.cloneNode(true));
    }
  }
  flushLoose();
  return out.join("\n\n");
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  let st = parentElement.__sar;
  if (!st) {
    st = parentElement.__sar = {};
    const wrap = document.createElement("div");
    wrap.className = "wrap";
    wrap.innerHTML = `<div class="frame"><div class="bar">
      <div class="preview-bar">
        <span class="muted">Click a sentence to see its evidence</span>
        <span class="legend" aria-hidden="true"><span><i style="background:var(--ok)"></i>Grounded</span>
          <span><i style="background:var(--warn)"></i>Partial</span>
          <span><i style="background:var(--bad)"></i>Ungrounded</span></span>
        <button class="switch" role="switch" aria-checked="false" data-hl>
          <span class="track"></span>Highlight grounding</button>
      </div>
      <div class="toolbar" role="toolbar" aria-label="Formatting">
        <select data-block aria-label="Text style" title="Text style">
          <option value="p">Normal text</option>
          <option value="h2">Heading</option>
          <option value="h3">Subheading</option>
        </select>
        <span class="sep"></span>
        <button data-cmd="bold" title="Bold (Ctrl+B)" aria-label="Bold"><b>B</b></button>
        <button data-cmd="italic" title="Italic (Ctrl+I)" aria-label="Italic"><i>I</i></button>
        <span class="sep"></span>
        <button data-cmd="insertUnorderedList" title="Bulleted list" aria-label="Bulleted list">&#8226;&#8801;</button>
        <button data-cmd="insertOrderedList" title="Numbered list" aria-label="Numbered list">1.&#8801;</button>
        <span class="sep"></span>
        <button data-cmd="undo" title="Undo (Ctrl+Z)" aria-label="Undo">&#8630;</button>
        <button data-cmd="redo" title="Redo (Ctrl+Y)" aria-label="Redo">&#8631;</button>
        <span class="hint">Saves when you click away</span>
      </div></div>
      <div class="scroll"><div class="doc" spellcheck="true" aria-label="Draft narrative"></div></div></div>`;
    parentElement.appendChild(wrap);
    st.wrap = wrap;
    st.pane = wrap.querySelector(".scroll");
    st.doc = wrap.querySelector(".doc");

    // Grounding highlight (remembered per browser).
    const hlBtn = wrap.querySelector("[data-hl]");
    const setHl = (on) => {
      wrap.classList.toggle("hl-on", on);
      hlBtn.setAttribute("aria-checked", on ? "true" : "false");
      try { localStorage.setItem("sar-hl", on ? "1" : "0"); } catch (_) {}
    };
    let hlSaved = false;
    try { hlSaved = localStorage.getItem("sar-hl") === "1"; } catch (_) {}
    setHl(hlSaved);
    hlBtn.addEventListener("click", () => setHl(hlBtn.getAttribute("aria-checked") !== "true"));
    st.select = wrap.querySelector("select[data-block]");
    st.dirty = false;

    // Toolbar: keep focus in the document while formatting.
    wrap.querySelector(".toolbar").addEventListener("mousedown", (e) => {
      if (e.target.closest("button")) e.preventDefault();
    });
    wrap.querySelectorAll("button[data-cmd]").forEach((b) => b.addEventListener("click", () => {
      document.execCommand(b.dataset.cmd);
      st.dirty = true; syncToolbar();
    }));
    st.select.addEventListener("change", () => {
      st.doc.focus();
      document.execCommand("formatBlock", false, st.select.value);
      st.dirty = true;
    });

    st.doc.addEventListener("input", () => { st.dirty = true; });
    // Paste as plain text so Word/web formatting can't smuggle in markup.
    st.doc.addEventListener("paste", (e) => {
      e.preventDefault();
      document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
    });
    const syncToolbar = () => {
      if (!st.editing) return;
      wrap.querySelectorAll("button[data-cmd]").forEach((b) => {
        try { b.classList.toggle("on", document.queryCommandState(b.dataset.cmd)); } catch (_) {}
      });
      const block = (document.queryCommandValue("formatBlock") || "p").toLowerCase();
      st.select.value = ["h2", "h3"].includes(block) ? block : (block === "h1" ? "h2" : "p");
    };
    document.addEventListener("selectionchange", syncToolbar);

    // Commit on leaving the editor (toolbar clicks don't count as leaving).
    wrap.addEventListener("focusout", (e) => {
      if (!st.editing || !st.dirty || wrap.contains(e.relatedTarget)) return;
      st.dirty = false;
      st.sent = blocksToMd(st.doc);
      setStateValue("markdown", st.sent);
    });

    // Preview: sentence -> audit card.
    st.doc.addEventListener("click", (e) => {
      if (st.editing) return;
      const s = e.target.closest(".s");
      if (!s) return;
      focusSentence(+s.dataset.s, false);
      window.dispatchEvent(new CustomEvent("sar-sentence", { detail: { i: +s.dataset.s, from: "draft" } }));
    });
    const focusSentence = (i, scroll) => {
      st.doc.querySelectorAll(".s.active").forEach((x) => x.classList.remove("active", "flash"));
      const el = st.doc.querySelector(`.s[data-s="${i}"]`);
      if (!el) return;
      el.classList.add("active", "flash");
      if (scroll) scrollPane(st.pane, el.offsetTop - st.pane.clientHeight / 3);
    };
    st.onEvent = (e) => { if (e.detail.from !== "draft" && !st.editing) focusSentence(e.detail.i, true); };
    window.addEventListener("sar-sentence", st.onEvent);
    st.cleanup = () => {
      // Last-chance commit if the editor is torn down with unsaved changes
      // (e.g. switching straight to the Markdown view unmounts this pane).
      if (st.editing && st.dirty) {
        st.dirty = false;
        try { setStateValue("markdown", blocksToMd(st.doc)); } catch (_) {}
      }
      window.removeEventListener("sar-sentence", st.onEvent);
      document.removeEventListener("selectionchange", syncToolbar);
    };
  }

  const editing = data.mode === "edit";
  // Safety net: leaving Edit mode always commits pending changes, even if the
  // editor never received a blur (e.g. the view switched programmatically).
  if (!editing && st.editing && st.dirty) {
    st.dirty = false;
    st.sent = blocksToMd(st.doc);
    setStateValue("markdown", st.sent);
  }
  // Never rebuild the document under the reviewer's cursor. (Inside a shadow
  // root, document.activeElement is the host, so ask the root instead.)
  const active = parentElement.activeElement || document.activeElement;
  const typing = st.editing && editing && active && st.doc.contains(active);
  if (st.rev !== data.rev && !(typing && st.dirty)) {
    st.doc.innerHTML = renderBlocks(data.blocks);
    st.rev = data.rev;
    st.dirty = false;
  }
  if (editing !== st.editing) {
    st.editing = editing;
    st.wrap.classList.toggle("editing", editing);
    st.doc.contentEditable = editing ? "true" : "false";
    st.doc.setAttribute("role", editing ? "textbox" : "document");
    st.doc.setAttribute("aria-multiline", editing ? "true" : "false");
    if (editing) { try { document.execCommand("defaultParagraphSeparator", false, "p"); } catch (_) {} }
  }
  return () => st.cleanup && st.cleanup();
}
"""

# ── Audit pane ────────────────────────────────────────────────────────────────

_AUDIT_CSS = _SHARED_CSS + """
.body { padding: 14px 14px 28px; font-size: 13px; line-height: 1.55; }
.sum { padding: 2px 2px 14px; }
.sum-top { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 8px; }
.sum-title { font-size: 12px; color: var(--text-2); font-weight: 500; }
.sum-n { font-size: 12px; color: var(--text-3); font-variant-numeric: tabular-nums; }
.meter { display: flex; gap: 2px; height: 6px; border-radius: 999px; overflow: hidden; background: var(--well); }
.meter i { display: block; min-width: 3px; }
.meter .ok { background: var(--ok); } .meter .warn { background: var(--warn); } .meter .bad { background: var(--bad); }
.key { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 8px; font-size: 12px; color: var(--text-2); }
.key b { font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums; margin-right: 3px; }
.key .d { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; }
.changes { margin-top: 10px; font-size: 12px; color: var(--info); display: flex; gap: 6px; align-items: center; }
.changes::before { content: ""; width: 7px; height: 7px; border-radius: 2px; border: 1.5px dotted var(--info); }

details.ctx { border: 1px solid var(--line); border-radius: 10px; margin: 2px 0 10px; }
details.ctx summary { cursor: pointer; list-style: none; display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; color: var(--text-2); font-size: 12.5px; }
details.ctx summary::-webkit-details-marker { display: none; }
details.ctx summary::before { content: "›"; color: var(--text-3); transition: transform .15s ease;
  display: inline-block; width: 8px; }
details.ctx[open] summary::before { transform: rotate(90deg); }
details.ctx summary .n { margin-left: auto; color: var(--text-3); font-size: 12px; }
.ctx-in { padding: 0 12px 10px; }
.q-row { font-size: 12px; color: var(--text-3); margin-bottom: 6px; }
.q-row span { color: var(--text-2); }
.src { border-top: 1px solid var(--line); padding: 8px 0 2px; }
.src-h { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--text-2); }
.src-h code { color: var(--text); font-size: 11.5px; }
.src-h .rel { margin-left: auto; color: var(--text-3); font-variant-numeric: tabular-nums; }
.src p { margin: 4px 0 0; font-size: 12px; color: var(--text-3); }

.sec { display: flex; align-items: center; gap: 8px; margin: 18px 2px 8px; font-size: 11px;
  font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--text-3); }
.sec::after { content: ""; flex: 1; height: 1px; background: var(--line); }

.card { border: 1px solid var(--line); border-radius: 10px; padding: 11px 13px 12px; margin-bottom: 8px;
  cursor: pointer; background: rgb(255 255 255 / .012);
  transition: border-color .15s ease, background-color .15s ease; }
.card:hover { border-color: var(--line-2); background: rgb(255 255 255 / .03); }
.card:focus-visible { outline: 2px solid rgb(143 179 232 / .8); outline-offset: 2px; }
.card.active { border-color: rgb(143 179 232 / .5); background: rgb(143 179 232 / .06); }
.top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.id { font-family: var(--mono); font-size: 11px; color: var(--text-3); }
.st { margin-left: auto; display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px;
  font-weight: 500; color: var(--text-2); }
.st .d { width: 6px; height: 6px; border-radius: 50%; }
.st.grounded .d { background: var(--ok); } .st.partial .d { background: var(--warn); }
.st.ungrounded .d { background: var(--bad); } .st.ungrounded { color: #E9A596; }
.st.unverified .d { background: transparent; border: 1.5px solid var(--bad); width: 5px; height: 5px; }
.st.unverified { color: #E9A596; font-weight: 600; }
.card.unverified { border-color: rgb(226 130 111 / .45); }
.miss { color: #E9A596; }
.miss small { display: block; color: var(--text-3); font-size: 11.5px; }
.meter .alarm { background: repeating-linear-gradient(135deg, var(--bad) 0 3px, transparent 3px 6px); }
.flag { border-top: 1px solid var(--line); padding: 8px 0 2px; font-size: 12px; }
.flag-h { display: flex; gap: 8px; align-items: center; color: var(--text); font-weight: 500; }
.sev { font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
  border-radius: 4px; padding: 0 5px; line-height: 16px; border: 1px solid var(--line-2); color: var(--text-2); }
.sev.high { color: #E9A596; border-color: rgb(226 130 111 / .5); }
.sev.medium { color: var(--warn); border-color: rgb(217 174 91 / .45); }
.flag p { margin: 3px 0 0; color: var(--text-3); }
.tag { font-size: 10.5px; font-weight: 600; color: var(--info); border: 1px dotted rgb(143 179 232 / .7);
  border-radius: 5px; padding: 0 5px; line-height: 16px; }
.q { margin: 0; color: var(--text); font-size: 13px; }
.q strong { font-weight: 600; }
.cells { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 3px 14px; margin: 0;
  font-size: 12.5px; }
.cells dt { font-size: 10.5px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase;
  color: var(--text-3); padding-top: 2px; }
.cells dd { margin: 0; color: var(--text); font-variant-numeric: tabular-nums; min-width: 0; }
.was { margin: 6px 0 0; font-size: 12px; color: var(--text-3); text-decoration: line-through; }
.ev { display: grid; grid-template-columns: 62px 1fr; gap: 5px 8px; margin: 10px 0 0; padding-top: 9px;
  border-top: 1px solid var(--line); }
.ev dt { font-size: 10.5px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
  color: var(--text-3); padding-top: 2px; }
.ev dd { margin: 0; min-width: 0; font-size: 12px; color: var(--text-2); }
.kv { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.kv + .kv { margin-top: 3px; }
.kv code { font-size: 11px; color: var(--text-3); }
.kv span { color: var(--text); }
.chip { font-family: var(--mono); font-size: 11px; color: var(--text-2); background: var(--well);
  border: 1px solid var(--line); border-radius: 5px; padding: 0 5px; }

.card.removed { cursor: default; border-style: dashed; background: transparent; }
.card.removed:hover { border-color: var(--line); }
.card.removed .q { color: var(--text-3); text-decoration: line-through; }
.empty { padding: 28px 18px; color: var(--text-3); text-align: center; }
"""

_AUDIT_JS = _SCROLL_JS + r"""
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const LABEL = { grounded: "Grounded", partial: "Partial", ungrounded: "Ungrounded", unverified: "Unverified" };
// Light inline Markdown for claim text (bold labels like "**Amount:**").
const inl = (t) => esc(t).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
// One-line plain version of a claim (table rows become "a · b · c").
const plain = (t) => t.trim().startsWith("|")
  ? t.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()).filter(Boolean).join(" · ")
  : t.replace(/\*\*/g, "");

function render(d) {
  if (d.empty) return `<div class="empty">No audit trail for this case.</div>`;
  const c = d.counts, t = Math.max(d.total, 1);
  let h = `<div class="sum">
    <div class="sum-top"><span class="sum-title">Sentence grounding</span><span class="sum-n">${d.total} sentences</span></div>
    <div class="meter" role="img" aria-label="${c.grounded} grounded, ${c.partial} partial, ${c.ungrounded} ungrounded, ${c.unverified} unverified">
      ${c.grounded ? `<i class="ok" style="flex:${c.grounded / t}"></i>` : ""}
      ${c.partial ? `<i class="warn" style="flex:${c.partial / t}"></i>` : ""}
      ${c.ungrounded ? `<i class="bad" style="flex:${c.ungrounded / t}"></i>` : ""}
      ${c.unverified ? `<i class="alarm" style="flex:${c.unverified / t}"></i>` : ""}
    </div>
    <div class="key">
      <span><i class="d" style="background:var(--ok)"></i><b>${c.grounded}</b>grounded</span>
      <span><i class="d" style="background:var(--warn)"></i><b>${c.partial}</b>partial</span>
      <span><i class="d" style="background:var(--bad)"></i><b>${c.ungrounded}</b>ungrounded</span>
      ${c.unverified ? `<span class="miss"><b>${c.unverified}</b>unverified figures</span>` : ""}
    </div>`;
  const e = d.edits, parts = [];
  if (e.edited) parts.push(`${e.edited} edited`);
  if (e.added) parts.push(`${e.added} added`);
  if (e.removed) parts.push(`${e.removed} removed`);
  if (parts.length) h += `<div class="changes">Reviewer changes · ${parts.join(" · ")}</div>`;
  h += `</div>`;

  if (d.chunks.length) {
    h += `<details class="ctx"><summary>Retrieved context<span class="n">${d.chunks.length} source${d.chunks.length > 1 ? "s" : ""}${d.dedup ? ` · ${d.dedup} duplicate${d.dedup > 1 ? "s" : ""} removed` : ""}</span></summary><div class="ctx-in">` +
      d.queries.map((q, n) => `<div class="q-row">${n ? "Description" : "Label"} query · <span>${esc(q)}</span></div>`).join("") +
      d.chunks.map((k) => `<div class="src"><div class="src-h"><code>${esc(k.id)}</code>${esc(k.source)} · p.${k.page}<span class="rel">${k.relevance.toFixed(2)}</span></div><p>${esc(k.preview)}…</p></div>`).join("") +
      `</div></details>`;
  }

  if (d.detection || d.flags.length) {
    const hi = d.flags.filter((f) => f.s === "high").length;
    h += `<details class="ctx"><summary>Rule-based analysis<span class="n">${d.detection ? esc(d.detection.p) : ""}${d.flags.length ? ` · ${d.flags.length} red flag${d.flags.length > 1 ? "s" : ""}${hi ? ` (${hi} high)` : ""}` : ""}</span></summary><div class="ctx-in">` +
      (d.detection ? `<div class="q-row">Typology · <span>${esc(d.detection.p)} (${esc(d.detection.c)} confidence)</span></div>` +
        d.detection.e.map((x) => `<div class="q-row"><span>${esc(x)}</span></div>`).join("") : "") +
      d.flags.map((f) => `<div class="flag"><div class="flag-h"><span class="sev ${esc(f.s)}">${esc(f.s)}</span>${esc(f.t)}</div><p>${esc(f.e)}</p></div>`).join("") +
      `</div></details>`;
  }

  for (const sec of d.sections) {
    h += `<div class="sec">${esc(sec.name)}</div>`;
    for (const it of sec.items) {
      const ev = [];
      if (it.data.length) ev.push(`<dt>Data</dt><dd>${it.data.map((r) =>
        `<div class="kv"><code>${esc(r.f)}</code><span>${esc(r.v)}</span></div>`).join("")}</dd>`);
      if (it.unverified.length) ev.unshift(`<dt class="miss">Check</dt><dd>${it.unverified.map((u) =>
        `<div class="miss">${esc(u.v)} is not in the case data${u.n ? `<small>${esc(u.n)}</small>` : ""}</div>`).join("")}</dd>`);
      if (it.context.length) ev.push(`<dt>Source</dt><dd>${it.context.map((x) => `<span class="chip">${esc(x)}</span>`).join(" ")}</dd>`);
      if (it.rules.length) ev.push(`<dt>Rules</dt><dd>${it.rules.map((x) => esc(x)).join(" · ")}</dd>`);
      if (it.typology) ev.push(`<dt>Typology</dt><dd>${esc(it.typology)}</dd>`);
      h += `<div class="card ${it.status === "unverified" ? "unverified" : ""}" data-s="${it.i}" tabindex="0" role="button" title="${esc(it.confidence)}"
                 aria-label="Sentence ${it.i}, ${LABEL[it.status]}">
        <div class="top"><span class="id">S${it.i}${it.cells.length ? " · table row" : ""}</span>` +
        (it.change ? `<span class="tag">${it.change === "added" ? "Added" : "Edited"}</span>` : "") +
        `<span class="st ${it.status}"><i class="d"></i>${LABEL[it.status]}</span></div>
        ` + (it.cells.length
          ? `<dl class="cells">${it.cells.map((c) => `<dt>${esc(c.h)}</dt><dd>${inl(c.v)}</dd>`).join("")}</dl>`
          : `<p class="q">${inl(it.text)}</p>`) +
        (it.was ? `<p class="was" title="Generated text">${esc(plain(it.was))}</p>` : "") +
        (ev.length ? `<dl class="ev">${ev.join("")}</dl>` : "") +
        `</div>`;
    }
  }
  if (d.removed.length) {
    h += `<div class="sec">Removed by reviewer</div>` +
      d.removed.map((r) => `<div class="card removed">
        <div class="top"><span class="id">${esc(r.section)}</span><span class="st ${r.status}"><i class="d"></i>${LABEL[r.status]}</span></div>
        <p class="q">${esc(plain(r.text))}</p></div>`).join("");
  }
  return h;
}

export default function (component) {
  const { data, parentElement } = component;
  let st = parentElement.__sar;
  if (!st) {
    st = parentElement.__sar = {};
    const frame = document.createElement("div");
    frame.className = "frame";
    frame.innerHTML = `<div class="scroll"><div class="body"></div></div>`;
    parentElement.appendChild(frame);
    st.pane = frame.querySelector(".scroll");
    st.body = st.pane.querySelector(".body");

    const focusCard = (i, scroll) => {
      st.body.querySelectorAll(".card.active").forEach((x) => x.classList.remove("active", "flash"));
      const el = st.body.querySelector(`.card[data-s="${i}"]`);
      if (!el) return;
      el.classList.add("active", "flash");
      if (scroll) scrollPane(st.pane, el.offsetTop - 12);
    };
    const pick = (card) => {
      focusCard(+card.dataset.s, false);
      window.dispatchEvent(new CustomEvent("sar-sentence", { detail: { i: +card.dataset.s, from: "audit" } }));
    };
    st.body.addEventListener("click", (e) => { const c = e.target.closest(".card"); if (c) pick(c); });
    st.body.addEventListener("keydown", (e) => {
      const c = e.target.closest(".card");
      if (c && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); pick(c); }
    });
    st.onEvent = (e) => { if (e.detail.from !== "audit") focusCard(e.detail.i, true); };
    window.addEventListener("sar-sentence", st.onEvent);
  }
  if (st.rev !== data.rev) {
    st.body.innerHTML = render(data.audit);
    st.rev = data.rev;
  }
  return () => window.removeEventListener("sar-sentence", st.onEvent);
}
"""

_draft_component = st.components.v2.component(
    "sar_draft_pane", css=_DRAFT_CSS, js=_DRAFT_JS,
)
_audit_component = st.components.v2.component(
    "sar_audit_pane", css=_AUDIT_CSS, js=_AUDIT_JS,
)


def _rev(*parts: object) -> str:
    return hashlib.md5(repr(parts).encode()).hexdigest()[:12]


def draft_pane(markdown: str, audit: AuditRecord | None,
               baseline: AuditRecord | None, *, editing: bool,
               key: str, on_change, height: int) -> None:
    """Render the formatted draft; in edit mode it is a rich-text editor.

    ``on_change`` fires after the reviewer leaves the editor with changes; the
    new Markdown is then at ``st.session_state[key]["markdown"]``.
    """
    changes, _ = reviewer_changes(audit, baseline)
    blocks = narrative_blocks(markdown, audit, changes)
    _draft_component(
        key=key,
        data={"mode": "edit" if editing else "preview", "blocks": blocks,
              "rev": _rev(blocks)},
        on_markdown_change=on_change,
        height=height,
    )


def audit_pane(audit: AuditRecord | None, baseline: AuditRecord | None,
               markdown: str, *, key: str, height: int) -> None:
    payload = audit_payload(audit, baseline, markdown)
    _audit_component(
        key=key, data={"audit": payload, "rev": _rev(payload)}, height=height,
    )
