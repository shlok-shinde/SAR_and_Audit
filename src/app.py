"""
app.py — Streamlit UI: SAR Narrative Generator with Audit Trail.

Analyst-facing case workspace:
  1. Build a case from your own data (case intake): upload a transaction
     export or type transactions in, add the subject's KYC profile, the alert,
     investigation steps/findings and prior SARs. Or start from a dataset sample.
  2. Rules detect the typology and red flags; a local model drafts the
     narrative; every sentence is audited against the case data.
  3. Review the draft side-by-side with its audit trail (unverified figures
     flagged), edit, then decide SAR / No SAR (maker-checker) and export the
     FinCEN filing text and case file.
Every edit rebuilds the audit record live, so provenance (and what gets saved or
approved) always reflects the current text.

Run from project root:
    docker compose up -d          # PostgreSQL
    streamlit run src/app.py
"""

from __future__ import annotations

import html
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Modules import each other by bare name (`from audit_trail import …`), with
# src/ on sys.path (streamlit puts the script's folder there). The app does the
# same so every module — and every dataclass — exists exactly once.
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import db  # noqa: E402
from audit_trail import (  # noqa: E402
    AuditRecord, grounding_status, rebuild_audit_record, stale_mentions, typology_mismatch,
)
from case_input import CaseInput, from_attempt  # noqa: E402
from data_loader import get_pattern_attempts  # noqa: E402
from evaluate_narratives import ALL_SECTIONS, REQUIRED_SECTIONS  # noqa: E402
from export import (  # noqa: E402
    continuing_due, events_to_dicts, export_bundle, filing_due, narrative_length,
)
from intake import render_funds_flow, render_intake, render_red_flags, seed_intake  # noqa: E402
from review_components import audit_pane, draft_pane, reviewer_changes  # noqa: E402
from generate_narrative import (  # noqa: E402
    CASE_TO_ATTEMPT,
    FALLBACK_MODEL,
    PATTERN_DESCRIPTIONS,
    PRIMARY_MODEL,
    NO_SAR_PATTERN,
    NarrativeGenerationError,
    conclusion_mismatch,
    draft_warnings,
    generate_with_audit,
    retrieve_by_queries,
)
from typology import warrants_no_sar  # noqa: E402

# Workflow status (db.py) -> pill tone
STATUS_TONE = {"Draft": "muted", "Pending": "warn", "Approved": "ok", "Rejected": "bad",
               "No SAR": "info", "Filed": "ok"}
SOURCE_LABEL = {"sample": "Dataset sample", "upload": "Uploaded case", "manual": "Manual case"}


def pill(label: str, tone: str = "muted") -> str:
    return f'<span class="pill {tone}"><span class="dot"></span>{html.escape(label)}</span>'

# ── Design layer: neutral "pro tool" system + light-reactive surfaces ────────
# Explicitly requested CSS + JS. Targets stable data-testids and st-key-*
# classes only (no hashed emotion classes), so it survives Streamlit upgrades.
# Accessibility: keeps WCAG text contrast, visible :focus-visible rings, and
# honors prefers-reduced-motion / prefers-reduced-transparency.
#
# Palette: near-monochrome greys on the #262626 base, a white primary action,
# and desaturated status colours (the same tokens are mirrored in
# review_components.py and .streamlit/config.toml).
#
# Light model (a restrained take on Tahoe / iOS 26 Liquid Glass):
#   * At rest there is no light: surfaces show only a neutral hairline edge.
#   * The pointer is a soft moving light: rims catch it on the nearest edge,
#     with a dimmer refracted highlight on the opposite edge.
#   * A press spawns a soft white light behind the UI that blooms and decays,
#     catching the edges of nearby surfaces with inverse-square falloff.
# JS only feeds light positions through custom properties (--lx/--ly rim,
# --ox/--oy refraction, --gx/--gy glow); CSS draws everything.

# Light-reactive surfaces: rims + glow pseudo-elements are attached to these.
_GLASS = (
    '[data-testid="stSidebar"]',
    '[class*="st-key-glass-"]',
    ".st-key-load-case-btn button", ".st-key-clear-btn button",
    ".st-key-save-draft-btn button", ".st-key-reject-btn button",
    ".st-key-reviewer-notes button",
    '[data-testid="stButtonGroup"] [role="radiogroup"]',
)
_SEL = ", ".join(_GLASS)
_BEFORE = ", ".join(s + "::before" for s in _GLASS)
_AFTER = ", ".join(s + "::after" for s in _GLASS)

_PRIMARY_KEYS = ["generate-btn", "approve-btn", "intake-generate-btn", "open-intake-btn",
                 "decide-pop"]
_PRIMARY_BTNS = ", ".join(f".st-key-{k} button" for k in _PRIMARY_KEYS)
_PRIMARY_TEXT = ", ".join(f".st-key-{k} button :is(p, span)" for k in _PRIMARY_KEYS)
_PRIMARY_HOVER = ", ".join(f".st-key-{k} button:hover" for k in _PRIMARY_KEYS)
_PRIMARY_OFF = ", ".join(f".st-key-{k} button:disabled" for k in _PRIMARY_KEYS)
_SECONDARY_BTNS = (".st-key-load-case-btn button, .st-key-clear-btn button, "
                   ".st-key-save-draft-btn button, .st-key-reviewer-notes button, "
                   ".st-key-export-pop button, .st-key-edit-inputs-btn button, "
                   ".st-key-sample-intake-btn button, .st-key-in-discard button")

LIQUID_GLASS_CSS = """
<style>
/* ── Tokens ──────────────────────────────────────────────────────────── */
:root {
  --bg: #262626;          /* page (requested base) */
  --surface: #2B2B2B;     /* cards, panes */
  --surface-2: #313131;   /* hover / raised */
  --well: #212121;        /* inputs, tracks */
  --line: rgb(255 255 255 / .07);
  --line-2: rgb(255 255 255 / .12);
  --text: #EDEDED;
  --text-2: #A3A3A3;
  --text-3: #767676;
  --ok: #6BC495;          /* grounded / approved */
  --warn: #D9AE5B;        /* partial / pending */
  --bad: #E2826F;         /* ungrounded / rejected */
  --info: #8FB3E8;        /* reviewer changes, focus */
  --radius: 12px;
}

/* ── Scene ───────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"], .stApp { background: var(--bg); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 3.2rem; max-width: 1320px; }
h1, h2, h3, h4 { letter-spacing: -.012em; }
[data-testid="stCaptionContainer"] { color: var(--text-2); }

/* ── Light-reactive surfaces: shared rim + inner glow ──────────────── */
__SEL__ {
  position: relative;
  isolation: isolate;
  --lx: 0px; --ly: 0px; --ox: 100%; --oy: 100%;
  --lr: 220px; --li: 0;
  --gx: 50%; --gy: 50%; --gr: 160px; --gi: 0;
}
__AFTER__ {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  pointer-events: none;
  z-index: 2;
  background:
    radial-gradient(var(--lr) circle at var(--lx) var(--ly),
      rgb(255 255 255 / calc(var(--li) * .55)), transparent 70%),
    radial-gradient(calc(var(--lr) * .8) circle at var(--ox) var(--oy),
      rgb(255 255 255 / calc(var(--li) * .16)), transparent 70%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
}
__BEFORE__ {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  z-index: 1;
  background: radial-gradient(var(--gr) circle at var(--gx) var(--gy),
    rgb(255 255 255 / calc(var(--gi) * .07)), transparent 70%);
  mix-blend-mode: plus-lighter;
}

/* Click light: soft, behind the UI layer, visible through translucency */
.lg-flare { position: fixed; width: 0; height: 0; pointer-events: none; z-index: 0; }
[data-testid="stSidebar"], [data-testid="stMain"] { z-index: 1; }
[data-testid="stMain"] { position: relative; }
.lg-flare::before, .lg-flare::after {
  content: ""; position: absolute; border-radius: 50%;
  transform: translate(-50%, -50%) scale(.3);
}
.lg-flare::before {
  width: 80px; height: 80px; filter: blur(8px);
  background: radial-gradient(circle, rgb(255 255 255 / .14), transparent 70%);
  animation: lg-core 600ms cubic-bezier(.2,.8,.2,1) forwards;
}
.lg-flare::after {
  width: 420px; height: 420px;
  background: radial-gradient(circle, rgb(255 255 255 / .06), rgb(255 255 255 / .02) 35%, transparent 68%);
  animation: lg-bloom 1100ms cubic-bezier(.16,1,.3,1) forwards;
}
@keyframes lg-core {
  0% { opacity: 0; } 15% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(1.5); }
}
@keyframes lg-bloom {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(.15); } 15% { opacity: 1; }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(1); }
}

/* ── Sidebar: floating inspector panel ─────────────────────────────── */
/* Width is left to Streamlit: it collapses the panel by width, so a pinned
   width/min-width here would keep reserving space when it is collapsed. */
[data-testid="stSidebar"] {
  background: transparent;
  border: none;
  padding: 12px 6px 12px 12px;
}
[data-testid="stSidebar"]::before, [data-testid="stSidebar"]::after {
  inset: 12px 6px 12px 12px;
  border-radius: 16px;
}
[data-testid="stSidebarContent"] {
  height: 100%;
  padding: 18px 16px 14px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgb(43 43 43 / .92);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  box-shadow: 0 16px 40px -18px rgb(0 0 0 / .6);
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: rgb(255 255 255 / .14) transparent;
}
[data-testid="stSidebarResizeHandle"] { opacity: .25; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: rgb(255 255 255 / .13); border-radius: 999px;
  border: 2px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background: rgb(255 255 255 / .24); background-clip: padding-box; }
::-webkit-scrollbar-track { background: transparent; }

.sb-brand { display: flex; align-items: center; gap: 10px; margin: 2px 0 4px; }
.sb-mark { width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center;
  background: var(--text); color: #1A1A1A; font-weight: 700; font-size: 12px; letter-spacing: -.02em; }
.sb-name { font-weight: 600; font-size: 14px; color: var(--text); line-height: 1.2; }
.sb-sub { font-size: 11.5px; color: var(--text-3); }
.sb-status { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text-2);
  margin: 12px 0 2px; }
[data-testid="stSidebarHeader"] { height: 2.4rem; min-height: 0; margin-bottom: 0; padding-top: .4rem; }
[data-testid="stMarkdownContainer"] p.lg-section, .lg-section {
  margin: 20px 2px 8px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--text-3);
}
.sb-foot { font-size: 11.5px; color: var(--text-3); line-height: 1.6; margin-top: 6px; }
.sb-foot code { font-size: 11px; color: var(--text-2); background: var(--well);
  padding: 1px 5px; border-radius: 5px; }
[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"] p {
  font-size: 12px; font-weight: 500; color: var(--text-2); margin-bottom: 2px;
}

/* ── Status dots + pills ──────────────────────────────────────────── */
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex: none; }
.dot.ok { background: var(--ok); box-shadow: 0 0 0 3px rgb(107 196 149 / .15); }
.dot.bad { background: var(--bad); box-shadow: 0 0 0 3px rgb(226 130 111 / .15); }
.pill { display: inline-flex; align-items: center; gap: 6px; height: 22px; padding: 0 9px;
  border-radius: 999px; font-size: 11.5px; font-weight: 500; color: var(--text-2);
  background: rgb(255 255 255 / .05); border: 1px solid var(--line); }
.pill .dot { width: 6px; height: 6px; box-shadow: none; }
.pill.ok .dot { background: var(--ok); } .pill.warn .dot { background: var(--warn); }
.pill.bad .dot { background: var(--bad); } .pill.info .dot { background: var(--info); }
.pill.muted .dot { background: var(--text-3); }

/* ── Case header ──────────────────────────────────────────────────── */
.st-key-case-header { gap: 16px; padding: 4px 0 18px; border-bottom: 1px solid var(--line);
  margin-bottom: 4px; }
.ch-eyebrow { font-size: 11px; font-weight: 500; letter-spacing: .07em; text-transform: uppercase;
  color: var(--text-3); margin-bottom: 4px; }
.ch-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ch-title h1 { font-size: 24px; font-weight: 600; margin: 0; padding: 0; color: var(--text); }
.ch-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 6px; font-size: 12.5px;
  color: var(--text-2); }
.ch-meta span + span::before { content: "·"; margin-right: 14px; color: var(--text-3); }
.ch-meta code { font-size: 12px; color: var(--text-2); background: none; padding: 0; }
.st-key-case-actions { gap: 8px; }

/* ── Stats strip ──────────────────────────────────────────────────── */
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface);
  overflow: hidden; }
.stat { padding: 14px 18px; }
.stat + .stat { border-left: 1px solid var(--line); }
.stat .k { font-size: 12px; color: var(--text-2); }
.stat .v { font-size: 22px; font-weight: 600; color: var(--text); margin-top: 4px;
  font-variant-numeric: tabular-nums; letter-spacing: -.01em; }
.stat .v small { font-size: 13px; font-weight: 500; color: var(--text-3); margin-left: 2px; }
.stat .h { font-size: 11.5px; color: var(--text-3); margin-top: 2px; }
.sections { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 10px; }
.sections .lbl { font-size: 12px; color: var(--text-3); margin-right: 4px; }
.sections .pill.off { color: var(--text-3); background: transparent; }
@media (max-width: 900px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat:nth-child(3) { border-left: none; }
  .stat:nth-child(n+3) { border-top: 1px solid var(--line); }
}

/* ── Cards (bordered containers keyed glass-*) ─────────────────────── */
[class*="st-key-glass-"] {
  border-color: var(--line) !important;
  background: var(--surface);
  border-radius: var(--radius);
}
[class*="st-key-glass-step-"] { border-radius: 16px; padding: 20px 20px 18px; }
[class*="st-key-glass-step-"] h3 { font-size: 15px; font-weight: 600; }
[class*="st-key-glass-step-"] { cursor: pointer; transition: border-color .15s ease, background-color .15s ease; }
[class*="st-key-glass-step-"]:hover { border-color: var(--line-2) !important; background: var(--surface-2); }
[class*="st-key-step-btn-"] { position: absolute; inset: 0; z-index: 3; margin: 0 !important;
  width: auto !important; max-width: none !important; height: auto !important; }
[class*="st-key-step-btn-"] > div, [class*="st-key-step-btn-"] .stButton { width: 100%; height: 100%; }
[class*="st-key-step-btn-"] button { width: 100%; height: 100%; min-height: 100%; border: none;
  background: transparent !important; color: transparent !important; box-shadow: none; cursor: pointer;
  border-radius: 16px; }
[class*="st-key-step-btn-"] button :is(p, span) { color: transparent !important; }
[class*="st-key-step-btn-"] button:focus-visible { outline: 2px solid rgb(143 179 232 / .8) !important;
  outline-offset: -2px !important; }
.step-cta { font-size: 12.5px; font-weight: 500; color: var(--text-2); margin-top: 2px;
  transition: color .15s ease; }
.step-cta span { display: inline-block; transition: transform .15s ease; }
[class*="st-key-glass-step-"]:hover .step-cta { color: var(--text); }
[class*="st-key-glass-step-"]:hover .step-cta span { transform: translateX(3px); }
.sb-pulse { border-radius: 10px; animation: sb-pulse 1.6s ease-out; }
@keyframes sb-pulse {
  0%, 30% { box-shadow: 0 0 0 3px rgb(143 179 232 / .55); }
  100% { box-shadow: 0 0 0 3px rgb(143 179 232 / 0); }
}
.step-n { font-family: 'Geist Mono', monospace; font-size: 11.5px; color: var(--text-3);
  letter-spacing: .04em; }

/* Empty state hero */
.hero { text-align: center; margin: 5vh auto 0; max-width: 640px; }
.hero .eyebrow { display: inline-flex; align-items: center; gap: 8px; font-size: 12px;
  color: var(--text-2); border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px;
  background: rgb(255 255 255 / .03); }
.hero h1 { font-size: 40px; font-weight: 600; letter-spacing: -.03em; margin: 18px 0 10px;
  padding: 0; line-height: 1.1; color: var(--text); }
.hero p { font-size: 15px; color: var(--text-2); line-height: 1.6; margin: 0; }

/* ── Review pane headers ──────────────────────────────────────────── */
[class*="st-key-pane-head-"] { min-height: 40px; }
[class*="st-key-pane-head-"] h3 { font-size: 15px; font-weight: 600; padding: 0; }

/* ── Segmented control ────────────────────────────────────────────── */
[data-testid="stButtonGroup"] [role="radiogroup"] {
  display: flex;
  box-sizing: border-box;
  flex-wrap: nowrap;
  width: 100%;
  background: var(--well);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 2px;
  gap: 2px;
}
button[data-variant="segmented_control"] {
  flex: 1 1 auto;
  white-space: nowrap;
  border-radius: 7px;
  border: none;
  background: transparent;
  box-shadow: none;
  min-height: 26px;
  padding: 3px 10px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-2);
  transition: background .15s ease, color .15s ease;
}
button[data-variant="segmented_control"]:hover { background: rgb(255 255 255 / .04); color: var(--text); }
button[data-variant="segmented_control"][aria-checked="true"] {
  background: #3A3A3A !important;
  color: var(--text) !important;
  box-shadow: 0 1px 2px rgb(0 0 0 / .35), inset 0 1px 0 rgb(255 255 255 / .06);
}

/* ── Buttons ──────────────────────────────────────────────────────── */
__PRIMARY__ {
  border-radius: 9px;
  border: 1px solid transparent;
  background: var(--text);
  color: #171717;
  font-weight: 600;
  box-shadow: 0 1px 2px rgb(0 0 0 / .3);
  transition: background .15s ease, transform .12s ease;
}
__PRIMARY_TEXT__ { color: #171717; }
__PRIMARY_HOVER__ { background: #FFFFFF; }
__PRIMARY_OFF__ {
  background: #3A3A3A; color: var(--text-3);
}
__SECONDARY__ {
  border-radius: 9px;
  border: 1px solid var(--line-2);
  background: var(--surface);
  color: var(--text);
  font-weight: 500;
  box-shadow: none;
  transition: background .15s ease, transform .12s ease;
}
.st-key-load-case-btn button:hover, .st-key-clear-btn button:hover,
.st-key-save-draft-btn button:hover, .st-key-reviewer-notes button:hover {
  background: var(--surface-2); border-color: var(--line-2);
}
.st-key-reject-btn button {
  border-radius: 9px;
  border: 1px solid var(--line-2);
  background: transparent;
  color: var(--bad);
  font-weight: 500;
  transition: background .15s ease, transform .12s ease;
}
.st-key-reject-btn button :is(p, span) { color: var(--bad); }
.st-key-reject-btn button:hover { background: rgb(226 130 111 / .08); border-color: rgb(226 130 111 / .35); }
.st-key-generate-btn button:active, .st-key-approve-btn button:active,
.st-key-load-case-btn button:active, .st-key-clear-btn button:active,
.st-key-save-draft-btn button:active, .st-key-reject-btn button:active { transform: scale(.98); }

/* ── Fields ───────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {
  background: var(--well) !important;
  border-radius: 9px !important;
  border-color: var(--line) !important;
  min-height: 36px;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:hover { border-color: var(--line-2) !important; }
[data-testid="stSelectboxVirtualDropdown"], [data-testid="stSelectbox"] [role="listbox"] {
  background: #2E2E2E !important;
  border: 1px solid var(--line-2);
  border-radius: 10px;
  box-shadow: 0 16px 40px -12px rgb(0 0 0 / .6);
}
[data-testid="stTextInput"] input, [data-testid="stTextInputField"],
[data-testid="stTextArea"] textarea {
  background: var(--well) !important;
  border-radius: 9px !important;
  border: 1px solid var(--line) !important;
  color: var(--text);
}
[data-testid="stTextArea"] textarea { font-family: 'Geist Mono', monospace; font-size: 13px; line-height: 1.65; }
[data-testid="stTextInput"] input:focus, [data-testid="stTextInputField"]:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: rgb(143 179 232 / .6) !important;
  box-shadow: 0 0 0 3px rgb(143 179 232 / .14);
}

/* ── Status + popovers ────────────────────────────────────────────── */
[data-testid="stStatusWidget"], [data-testid="stExpander"] details {
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--surface);
}
[data-testid="stPopoverBody"] { border-radius: var(--radius); border: 1px solid var(--line-2);
  background: #2E2E2E; }

/* ── Intake + case evidence ───────────────────────────────────────── */
.st-key-intake-head { gap: 16px; padding: 4px 0 14px; border-bottom: 1px solid var(--line);
  margin-bottom: 4px; }
.det { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 2px 0 6px; }
.det-p { font-size: 20px; font-weight: 600; letter-spacing: -.01em; color: var(--text); }
.det-e { margin: 4px 0; font-size: 13px; color: var(--text-2); line-height: 1.5; }
.det-a { margin: 6px 0 0; font-size: 12px; color: var(--text-3); }
.rf { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0;
  border-top: 1px solid var(--line); }
.rf .pill { flex: none; height: 20px; font-size: 10.5px; letter-spacing: .05em; }
.rf-t { font-size: 13px; font-weight: 500; color: var(--text); }
.rf-e { font-size: 12.5px; color: var(--text-2); line-height: 1.5; margin-top: 2px; }
.kv-grid { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; font-size: 13px; }
.kv-grid dt { color: var(--text-3); } .kv-grid dd { margin: 0; color: var(--text); }
.stat .v.alarm { color: var(--bad); }
.sb-who { font-size: 11.5px; color: var(--text-3); margin: -4px 0 4px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 6px; }

/* ── Accessibility ────────────────────────────────────────────────── */
button:focus-visible, input:focus-visible, textarea:focus-visible {
  outline: 2px solid rgb(143 179 232 / .8) !important;
  outline-offset: 2px !important;
}
@media (prefers-reduced-motion: reduce) {
  [data-testid^="stBaseButton-"] button, [class*="st-key-"] button {
    transition: none !important; transform: none !important;
  }
  .lg-flare::before, .lg-flare::after { animation-duration: 1ms; }
}
@media (prefers-reduced-transparency: reduce) {
  [data-testid="stSidebarContent"] { background: var(--surface); backdrop-filter: none;
    -webkit-backdrop-filter: none; }
}
</style>
""".replace("__SEL__", _SEL).replace("__BEFORE__", _BEFORE).replace("__AFTER__", _AFTER) \
   .replace("__PRIMARY__", _PRIMARY_BTNS).replace("__SECONDARY__", _SECONDARY_BTNS) \
   .replace("__PRIMARY_TEXT__", _PRIMARY_TEXT).replace("__PRIMARY_HOVER__", _PRIMARY_HOVER) \
   .replace("__PRIMARY_OFF__", _PRIMARY_OFF)

# Light engine. Installed once per browser tab (guarded on window), survives
# Streamlit reruns, and only animates while a light is changing.
LIQUID_GLASS_JS = """
<script>
(() => {
  if (window.__lgLight) return;
  window.__lgLight = true;

  const GLASS = __GLASS__;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const POINTER = { x: 0, y: 0, i: 0, target: 0 };
  const flashes = [];                     // {x, y, t0}
  const FLASH_RANGE = 320;                // px where a flash is at half strength
  const FLASH_MS = reduceMotion ? 250 : 1100;
  let frame = 0;

  // Flash envelope: fast attack, exponential decay (a bloom, not a blink).
  const flashLevel = (t) => t < 70 ? t / 70 : Math.exp(-(t - 70) / (FLASH_MS / 3.2));
  const falloff = (d, r) => 1 / (1 + (d / r) * (d / r));
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function paint(now) {
    frame = 0;
    POINTER.i += (POINTER.target - POINTER.i) * .18;
    for (let k = flashes.length - 1; k >= 0; k--)
      if (now - flashes[k].t0 > FLASH_MS * 1.6) flashes.splice(k, 1);

    const vw = innerWidth, vh = innerHeight;

    for (const el of document.querySelectorAll(GLASS)) {
      const r = el.getBoundingClientRect();
      if (!r.width || r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;

      // Each light lands on the rim at the edge point nearest to it.
      let wx = 0, wy = 0, wsum = 0, rim = 0, glow = 0, gx = r.width / 2, gy = r.height / 2;
      const add = (lx, ly, level, weight) => {
        const nx = clamp(lx, r.left, r.right), ny = clamp(ly, r.top, r.bottom);
        const w = level * level * weight;
        wx += (nx - r.left) * w; wy += (ny - r.top) * w; wsum += w; rim += level;
      };

      if (POINTER.i > .01) {
        const d = Math.hypot(POINTER.x - clamp(POINTER.x, r.left, r.right),
                             POINTER.y - clamp(POINTER.y, r.top, r.bottom));
        const lvl = .55 * POINTER.i * falloff(d, 180);
        add(POINTER.x, POINTER.y, lvl, 1.4);
        if (d === 0) { glow = .22 * POINTER.i; gx = POINTER.x - r.left; gy = POINTER.y - r.top; }
      }
      for (const f of flashes) {
        const d = Math.hypot(f.x - clamp(f.x, r.left, r.right), f.y - clamp(f.y, r.top, r.bottom));
        const lvl = flashLevel(now - f.t0) * falloff(d, FLASH_RANGE);
        add(f.x, f.y, .9 * lvl, 3);
        // The pressed surface lights up from within; neighbours only catch spill.
        const g = lvl * (d === 0 ? .9 : .3);
        if (g > glow) { glow = g; gx = f.x - r.left; gy = f.y - r.top; }
      }

      const s = el.style;
      if (wsum < 1e-6) {           // no light nearby: surface stays unlit
        s.setProperty("--li", "0");
        s.setProperty("--gi", "0");
        continue;
      }
      const lx = wx / wsum, ly = wy / wsum;
      s.setProperty("--lx", lx.toFixed(1) + "px");
      s.setProperty("--ly", ly.toFixed(1) + "px");
      s.setProperty("--ox", (r.width - lx).toFixed(1) + "px");
      s.setProperty("--oy", (r.height - ly).toFixed(1) + "px");
      s.setProperty("--lr", Math.round(Math.max(120, Math.min(r.width, r.height) * 1.1 + 90)) + "px");
      s.setProperty("--li", Math.min(1, rim).toFixed(3));
      s.setProperty("--gi", Math.min(1, glow).toFixed(3));
      s.setProperty("--gx", gx.toFixed(1) + "px");
      s.setProperty("--gy", gy.toFixed(1) + "px");
      s.setProperty("--gr", Math.round(Math.min(420, Math.max(r.width, r.height) * 1.2)) + "px");
    }
    const settling = Math.abs(POINTER.target - POINTER.i) > .005;
    if (flashes.length || settling) schedule();
  }
  const schedule = () => { if (!frame) frame = requestAnimationFrame(paint); };

  addEventListener("pointermove", (e) => {
    POINTER.x = e.clientX; POINTER.y = e.clientY; POINTER.target = 1; schedule();
  }, { passive: true });
  document.documentElement.addEventListener("pointerleave", () => {
    POINTER.target = 0; schedule();
  });
  addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    flashes.push({ x: e.clientX, y: e.clientY, t0: performance.now() });
    const flare = document.createElement("div");
    flare.className = "lg-flare";
    flare.style.left = e.clientX + "px";
    flare.style.top = e.clientY + "px";
    // Mount behind the UI layer (see .lg-flare z-index).
    (document.querySelector('[data-testid="stAppViewContainer"]') || document.body)
      .prepend(flare);
    setTimeout(() => flare.remove(), 1300);
    schedule();
  }, { passive: true, capture: true });
  addEventListener("scroll", schedule, { passive: true, capture: true });
  addEventListener("resize", schedule, { passive: true });
  // Streamlit re-renders elements on every rerun; relight new surfaces.
  new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
  schedule();
})();
</script>
""".replace("__GLASS__", repr(_SEL))


# ── Cached resources ─────────────────────────────────────────────────────────

@st.cache_resource
def init_database() -> bool:
    """Create schema if needed. Returns True if Postgres is reachable."""
    try:
        db.init_db()
        return True
    except Exception:  # noqa: BLE001 — any DB failure falls back to review-only mode
        return False


@st.cache_data(ttl=300)
def list_cases() -> list[dict]:
    return db.get_all_cases()


@st.cache_data(ttl=3600)
def pattern_attempts(pattern_type: str) -> list[int]:
    return get_pattern_attempts(pattern_type)


# Live audit input. Retrieval depends only on the two queries recorded in the
# baseline audit, so reviewer edits re-run provenance in milliseconds (and
# against exactly the chunks the draft was generated from).
@st.cache_data(show_spinner="Retrieving typology context for the audit trail…")
def case_retrieval(label_query: str, description_query: str):
    _, retrieval_meta, chunk_texts = retrieve_by_queries(label_query, description_query)
    return retrieval_meta, chunk_texts


# ── Metrics helpers ────────────────────────────────────────────────────────────

def score_text(text: str) -> dict:
    """Structural completeness of raw narrative text (same rules as score_narrative)."""
    results = {
        s: bool(re.search(rf"###?\s*{re.escape(s)}", text, re.IGNORECASE))
        for s in ALL_SECTIONS
    }
    required_hits = sum(1 for s in REQUIRED_SECTIONS if results[s])
    return {
        "sections": results,
        "total": sum(results.values()),
        "required": f"{required_hits}/{len(REQUIRED_SECTIONS)}",
    }


def grounding_counts(audit: AuditRecord) -> dict:
    """Sentences per status: grounded / partial / ungrounded / unverified."""
    counts = {"grounded": 0, "partial": 0, "ungrounded": 0, "unverified": 0}
    for sent in audit.narrative_sentences:
        counts[grounding_status(sent)] += 1
    counts["unverified_values"] = sum(len(s.unverified_values) for s in audit.narrative_sentences)
    return counts


# ── Session state ─────────────────────────────────────────────────────────────

CASE_KEYS = ("case_id", "case_input", "attempt_id", "pattern", "narrative", "audit", "model",
             "status", "last_saved", "narrative_editor", "baseline_narrative", "baseline_audit",
             "drafted_by", "approved_by", "decision_choice", "decision_rationale",
             "reviewer_notes", "ack_unverified", "ack_conclusion", "audit_for")


def _why_section(narrative: str) -> str:
    """The draft's Why Suspicious paragraph — the natural No-SAR rationale."""
    m = re.search(r"^###?\s*Why Suspicious[^\n]*\n(.*?)(?=^###?\s|\Z)", narrative,
                  re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def load_case_into_state(case_id: str, case: CaseInput, narrative: str,
                         audit: AuditRecord | None, model: str = "",
                         status: str = "Pending", *, drafted_by: str = "",
                         approved_by: str = "", decision: str = "",
                         decision_rationale: str = "", reviewer_notes: str = "") -> None:
    no_sar = bool(audit) and warrants_no_sar(audit.pattern_type, audit.red_flags)
    choice = decision or ("No SAR" if no_sar else "SAR")
    st.session_state.update(
        case_id=case_id, case_input=case,
        attempt_id=case.attempt_id if case else (audit.attempt_id if audit else None),
        pattern=(audit.pattern_type if audit else "") or (case.dataset_label if case else ""),
        narrative=narrative, audit=audit, audit_for=narrative, model=model,
        status=status, last_saved="" if status == "Draft" else narrative,
        narrative_editor=narrative,
        # Baseline = the text/audit as generated or loaded. Edits are diffed
        # against it so the trail can show added, edited and removed claims.
        baseline_narrative=narrative, baseline_audit=audit,
        drafted_by=drafted_by or "", approved_by=approved_by or "",
        decision_choice="No SAR" if choice == "No SAR" else "File SAR",
        decision_rationale=decision_rationale or (_why_section(narrative) if no_sar else ""),
        reviewer_notes=reviewer_notes or "",
        ack_unverified=False,
        ack_conclusion=False,
        screen="review",
    )


def clear_state() -> None:
    for key in CASE_KEYS:
        st.session_state.pop(key, None)
    st.session_state.pop("screen", None)


def rebuild_audit_for_edited_text(baseline: AuditRecord, new_text: str) -> AuditRecord:
    """Re-run sentence-level provenance for reviewer-edited narrative text.

    Every step of build_audit_record is deterministic given the case data and
    the retrieved chunks, so the rebuilt record is exactly what generation
    would have produced for this text. Retrieval re-runs the baseline's own
    queries (cached); if ChromaDB is unavailable, attribution falls back to
    the stored chunk previews.
    """
    rm = baseline.retrieval_metadata
    try:
        retrieval_meta, chunk_texts = (case_retrieval(rm.label_query, rm.description_query)
                                       if rm else (None, {}))
    except Exception:  # noqa: BLE001 — keep reviewing even if ChromaDB is down
        retrieval_meta, chunk_texts = rm, {}
    case = st.session_state.get("case_input")
    if case is None and baseline.attempt_id is not None:
        case = from_attempt(int(baseline.attempt_id), baseline.case_id)
    return rebuild_audit_record(baseline, new_text, retrieval_meta, chunk_texts,
                                case.transactions)


def refresh_audit() -> None:
    """Keep the audit trail in lockstep with the narrative after every edit.

    Sentence indices, draft links and audit cards are all derived from the same
    rebuilt record, so deleting, adding or rewording text re-wires everything.
    """
    baseline = st.session_state.get("baseline_audit")
    narrative = st.session_state.get("narrative")
    if baseline is None or narrative is None:
        return
    if narrative == st.session_state.get("baseline_narrative"):
        st.session_state["audit"] = baseline
    else:
        st.session_state["audit"] = rebuild_audit_for_edited_text(baseline, narrative)
    st.session_state["audit_for"] = narrative


def decided_no_sar() -> bool:
    return st.session_state.get("decision_choice") == "No SAR"


def consistency_notes(audit: AuditRecord | None, baseline: AuditRecord | None
                      ) -> dict[int, list[str]]:
    """Per-sentence pointers to problems that span sentences, recomputed on every rerun.

    Each sentence is fact-checked against the case data on its own, so an edit can
    leave the draft disagreeing with itself or with the decision. These notes point
    the reviewer at the other sentences to check; nothing is rewritten for them.
    """
    if audit is None:
        return {}
    changes, _ = reviewer_changes(audit, baseline)
    notes = stale_mentions(audit.narrative_sentences, changes)
    for sent in audit.narrative_sentences:
        if not decided_no_sar() and NO_SAR_PATTERN.search(sent.sentence_text):
            notes.setdefault(sent.sentence_index, []).append(
                "Concludes that no SAR is warranted, but the decision is File SAR")
        # Records audited before the typology check carry no needs_review for it.
        mismatch = typology_mismatch(sent.sentence_text, audit.pattern_type)
        if mismatch and mismatch != sent.needs_review:
            notes.setdefault(sent.sentence_index, []).append(mismatch)
    return notes


def user_name() -> str:
    return (st.session_state.get("user_name") or "").strip()


def log_event(action: str, details: dict | None = None) -> None:
    """Best-effort case history (never blocks the analyst if the DB is down)."""
    if not st.session_state.get("db_ok") or not st.session_state.get("case_id"):
        return
    try:
        db.log_event(st.session_state["case_id"], action, user_name(), details)
    except Exception:  # noqa: BLE001
        pass


# ── Generation flow ───────────────────────────────────────────────────────────

def request_generation(case: CaseInput) -> None:
    """Button callback: queue a generation request in session state.

    Generation takes ~a minute and any click during it makes Streamlit rerun the
    script, which aborts the run mid-way. Keeping the request in session state
    (instead of acting on the one-shot button value) means an interrupted run
    simply resumes, and the case on screen is only replaced once the new one is
    ready. The case is stored as a plain dict so it survives any rerun.
    """
    st.session_state["pending_generation"] = {"case": case.to_dict(), "case_id": case.case_id}


def request_sample_generation(attempt_id: int, case_id: str) -> None:
    request_generation(from_attempt(attempt_id, case_id))


def open_sample_in_intake(attempt_id: int, case_id: str) -> None:
    seed_intake(from_attempt(attempt_id, case_id))


def run_pending_generation() -> None:
    job = st.session_state["pending_generation"]
    case = CaseInput.from_dict(job["case"])
    case_id = job["case_id"]
    where = (f"attempt #{case.attempt_id}" if case.attempt_id is not None
             else f"{len(case.flagged())} flagged transactions")
    with st.status(f"Generating narrative — {case_id} ({where})", expanded=True) as status:
        st.caption(
            f"Model: `{PRIMARY_MODEL}` (fallback `{FALLBACK_MODEL}`) · detecting typology and red "
            "flags, retrieving regulatory context, drafting, building the audit trail"
        )
        try:
            narrative, audit = generate_with_audit(case, case_id=case_id, verbose=False)
        except NarrativeGenerationError as e:
            # The models answered, but every draft was rejected by validation
            # (refusal, missing FFIEC sections, cut off) — nothing is loaded.
            st.session_state.pop("pending_generation", None)
            status.update(label="No usable draft produced", state="error", expanded=True)
            st.error("The model's output was rejected, so no draft was loaded. "
                     "Try generating again; details below.")
            st.code(str(e), language=None)
            return
        except Exception as e:  # noqa: BLE001 — surface Ollama/ChromaDB failures
            st.session_state.pop("pending_generation", None)
            status.update(label="Generation failed", state="error", expanded=True)
            st.error(
                "Is Ollama running with the required models? "
                f"Try `ollama serve` and `ollama pull {PRIMARY_MODEL}`."
            )
            st.caption(str(e))
            return
        status.update(
            label=f"Narrative generated in {audit.generation_time_seconds:.0f}s",
            state="complete", expanded=False,
        )
    st.session_state.pop("pending_generation", None)
    load_case_into_state(case_id, case, narrative, audit, audit.model_used, status="Draft",
                         drafted_by=user_name())
    st.session_state.pop("intake", None)
    log_event("generated", {"model": audit.model_used,
                            "prompt_version": audit.generation_config.get("prompt_version"),
                            "input_fingerprint": audit.generation_config.get("input_fingerprint")})
    st.session_state["generated_notice"] = (
        f"Case {case_id} generated in {audit.generation_time_seconds:.0f}s"
    )
    st.rerun()  # redraw the sidebar, whose Generate button was disabled mid-run


def load_saved_case(row: dict) -> None:
    case = db.get_case_input(row["case_id"])
    if case is None:
        st.error(f"Case {row['case_id']} has no stored input data.")
        return
    load_case_into_state(
        row["case_id"], case, row["narrative_text"], db.get_audit_trail(row["case_id"]),
        row.get("model_used", ""), row["status"],
        drafted_by=row.get("drafted_by") or "", approved_by=row.get("approved_by") or "",
        decision=row.get("decision") or "", decision_rationale=row.get("decision_rationale") or "",
        reviewer_notes=row.get("reviewer_notes") or "",
    )


def start_new_case() -> None:
    seed_intake(None)


def discard_intake() -> None:
    st.session_state.pop("intake", None)
    st.session_state["screen"] = "review" if "narrative" in st.session_state else None


def edit_case_inputs() -> None:
    """Review → intake with the current case, to enrich it and regenerate."""
    case = st.session_state.get("case_input")
    if case is not None:
        seed_intake(case)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar(db_ok: bool) -> None:
    with st.sidebar:
        st.html(
            '<div class="sb-brand"><div class="sb-mark">SAR</div><div>'
            '<div class="sb-name">Narrative generator</div>'
            '<div class="sb-sub">AML case review</div></div></div>'
            '<div class="sb-status">'
            + ('<span class="dot ok"></span>Database connected' if db_ok else
               '<span class="dot bad"></span>Database offline · review only')
            + '</div>'
        )
        st.session_state.setdefault("user_name", "analyst")
        st.text_input("Signed in as", key="user_name",
                      help="Recorded on drafts and decisions. Maker-checker: the person who "
                           "drafted a case cannot approve it. (Local mode has no login; in "
                           "production this comes from SSO.)")

        st.markdown('<p class="lg-section">Case source</p>', unsafe_allow_html=True)
        st.session_state.setdefault("sb_mode", "New case")
        mode = st.segmented_control(
            "Mode", ["New case", "Samples", "Saved"], required=True, key="sb_mode",
        )
        busy = "pending_generation" in st.session_state

        if mode == "New case":
            st.caption("Upload a transaction export or type transactions in, then add the "
                       "customer profile, alert and investigation notes.")
            label = ("Continue case intake" if "intake" in st.session_state
                     else "Start a new case")
            st.button(label, type="primary", icon=":material/upload_file:", key="open-intake-btn",
                      width="stretch",
                      on_click=(lambda: st.session_state.update(screen="intake"))
                      if "intake" in st.session_state else start_new_case)

        elif mode == "Samples":
            st.session_state.setdefault("sb_source", "Curated case")
            source = st.segmented_control(
                "Source", ["Curated case", "All attempts"], required=True, key="sb_source",
            )
            if source == "Curated case":
                case_id = st.selectbox(
                    "Case",
                    sorted(CASE_TO_ATTEMPT), key="sb-case",
                    format_func=lambda c: f"Case {c} — attempt {CASE_TO_ATTEMPT[c]}",
                )
                attempt_id = CASE_TO_ATTEMPT[case_id]
            else:
                pattern = st.selectbox("Pattern", sorted(k for k in PATTERN_DESCRIPTIONS
                                                          if k != "NONE"))
                attempt_id = st.selectbox("Attempt", pattern_attempts(pattern))
                case_id = st.text_input(
                    "Case ID", value=f"C{attempt_id:03d}",
                ).strip()
            case_id = case_id or f"C{attempt_id:03d}"
            st.button(
                "Generate narrative", type="primary",
                icon=":material/auto_awesome:", key="generate-btn", width="stretch",
                on_click=request_sample_generation, args=(attempt_id, case_id),
                disabled=busy,
            )
            st.button("Open in case intake", icon=":material/edit_note:",
                      key="sample-intake-btn", width="stretch",
                      on_click=open_sample_in_intake, args=(attempt_id, case_id),
                      help="Add a customer profile, alert and findings before generating.")

        elif mode == "Saved":
            st.markdown('<p class="lg-section">Saved cases</p>',
                        unsafe_allow_html=True)
            if not db_ok:
                st.warning("PostgreSQL is offline — cannot load saved cases.")
            else:
                cases = list_cases()
                if not cases:
                    st.caption("No cases stored yet. Generate one first.")
                else:
                    options = {c["case_id"]: c for c in cases}
                    case_id = st.selectbox(
                        "Saved case", list(options), key="sb-saved-case",
                        format_func=lambda c: (
                            f"{c} · {options[c]['pattern_type'].title()} · {options[c]['status']}"
                        ),
                    )
                    if st.button("Load case", icon=":material/folder_open:",
                                 key="load-case-btn", width="stretch"):
                        load_saved_case(options[case_id])

        st.markdown('<p class="lg-section">Workspace</p>',
                    unsafe_allow_html=True)
        if st.button("Clear workspace", icon=":material/refresh:",
                     key="clear-btn"):
            clear_state()
            st.session_state.pop("intake", None)
            st.rerun()
        st.html(
            '<div class="sb-foot">Runs locally · model '
            f'<code>{html.escape(PRIMARY_MODEL)}</code>, fallback '
            f'<code>{html.escape(FALLBACK_MODEL)}</code></div>'
        )


# ── Main-area components ──────────────────────────────────────────────────────

# Draft and audit panes share one height so they line up and scroll independently.
PANE_HEIGHT = 650


def sync_narrative() -> None:
    """Markdown editor -> canonical narrative (widget state is dropped when hidden)."""
    if "narrative_editor" in st.session_state:
        st.session_state["narrative"] = st.session_state["narrative_editor"]
        refresh_audit()


def sync_rich_editor() -> None:
    """Rich-text editor -> canonical narrative."""
    markdown = (st.session_state.get("draft_doc") or {}).get("markdown")
    if markdown is not None and "narrative" in st.session_state:
        st.session_state["narrative"] = markdown
        refresh_audit()


def open_editor() -> None:
    """Seed the Markdown editor from the canonical text whenever it opens."""
    if (st.session_state.get("narrative_view") == "Markdown"
            and "narrative" in st.session_state):
        st.session_state["narrative_editor"] = st.session_state["narrative"]


def render_draft_pane(notes: dict[int, list[str]]) -> None:
    with st.container(horizontal=True, vertical_alignment="center", key="pane-head-draft"):
        st.subheader("Draft narrative", icon=":material/description:")
        st.space("stretch")
        view = st.segmented_control(
            "View", ["Preview", "Edit", "Markdown"], default="Preview", required=True,
            key="narrative_view", label_visibility="collapsed",
            on_change=open_editor,
            help="Preview: click a sentence to see its audit entry. "
                 "Edit: format text like a word processor. "
                 "Markdown: edit the raw source.",
        )
    if view == "Markdown":
        st.text_area(
            "Narrative (Markdown)", key="narrative_editor", on_change=sync_narrative,
            height=PANE_HEIGHT, label_visibility="collapsed",
        )
    else:
        draft_pane(
            st.session_state["narrative"], st.session_state.get("audit"),
            st.session_state.get("baseline_audit"),
            editing=view == "Edit", key="draft_doc",
            on_change=sync_rich_editor, height=PANE_HEIGHT, notes=notes,
        )


# Onboarding steps: (icon, title, description, call to action, target)
STEPS = [
    ("upload_file", "Create a case",
     "Upload a transaction export (CSV or Excel) or type transactions in, then add "
     "the customer profile, alert and investigation notes.", "Start a new case", "intake"),
    ("auto_awesome", "Detect and draft",
     "Rules detect the typology and red flags; FinCEN, FATF and FFIEC guidance "
     "grounds a local model's draft. Try it on a dataset sample.", "Try a sample", "generate"),
    ("fact_check", "Review and file",
     "Check every sentence against the case data, fix anything unverified, decide "
     "SAR or no SAR, and export the filing text.", "Open saved cases", "load"),
]


def start_step(step: int) -> None:
    """Onboarding card click: open the intake, or preselect + focus the sidebar."""
    target = STEPS[step][4]
    if target == "intake":
        st.session_state["sb_mode"] = "New case"
        start_new_case()
        return
    if target == "load":
        st.session_state["sb_mode"] = "Saved"
    else:
        st.session_state["sb_mode"] = "Samples"
        st.session_state["sb_source"] = "Curated case"
    st.session_state["sidebar_focus"] = target


def render_sidebar_focus(target: str) -> None:
    """Expand the sidebar if collapsed, then focus and pulse the target control."""
    selector = {
        "case": ".st-key-sb-case",
        "generate": ".st-key-generate-btn",
        "load": ".st-key-sb-saved-case, .st-key-load-case-btn, [data-testid='stSidebar'] [data-testid='stAlert']",
    }[target]
    st.html(
        f"""<script>
        (() => {{
          const run = () => {{
            const el = document.querySelector("{selector}");
            if (!el) return;
            el.classList.remove("sb-pulse"); void el.offsetWidth; el.classList.add("sb-pulse");
            (el.querySelector("input, button") || el).focus({{preventScroll: false}});
            setTimeout(() => el.classList.remove("sb-pulse"), 1800);
          }};
          const sb = document.querySelector('[data-testid="stSidebar"]');
          if (sb && sb.getAttribute("aria-expanded") !== "true") {{
            document.querySelector('[data-testid="stExpandSidebarButton"]')?.click();
            setTimeout(run, 450);
          }} else {{ setTimeout(run, 60); }}
        }})();
        /* {time.time()} */
        </script>""",
        unsafe_allow_javascript=True,
    )


def render_empty_state() -> None:
    st.html(
        '<div class="hero"><span class="eyebrow"><span class="dot ok"></span>'
        'Local RAG · rule-based typology · sentence-level provenance</span>'
        '<h1>Draft SAR narratives you can audit</h1>'
        '<p>Bring your own case — transactions, customer profile and findings. Rules detect '
        'the typology and red flags, a local model drafts an FFIEC-format narrative, and every '
        'sentence is checked against the case data it came from.</p></div>'
    )
    st.space("large")
    cols = st.columns(3, vertical_alignment="top")
    for i, (col, (icon, title, desc, cta, _)) in enumerate(zip(cols, STEPS)):
        with col.container(border=True, key=f"glass-step-{i}"):
            st.html(f'<div class="step-n">0{i + 1}</div>')
            st.subheader(title, icon=f":material/{icon}:")
            st.caption(desc)
            st.html(f'<div class="step-cta">{cta} <span aria-hidden="true">→</span></div>')
            # Invisible full-card button (stretched over the card by CSS).
            st.button(f"{title}: {cta}", key=f"step-btn-{i}", width="stretch",
                      on_click=start_step, args=(i,))


def _due_text(case: CaseInput | None) -> tuple[str, str]:
    """('Due 2024-07-10 · 12 days left', tone) from the alert date (30-day rule)."""
    if case is None:
        return "", "muted"
    due = filing_due(case.alert.detected_on)
    if case.is_continuing():
        cont = continuing_due(case.prior_sars)
        if cont and (due is None or cont < due):
            due = cont
    if not due:
        return "", "muted"
    left = (due - date.today()).days
    if left < 0:
        return f"Filing overdue by {-left} days (due {due.isoformat()})", "bad"
    return f"Filing due {due.isoformat()} · {left} days left", "warn" if left <= 7 else "muted"


def _save_case(narrative: str, audit: AuditRecord | None) -> None:
    case = st.session_state.get("case_input")
    due = filing_due(case.alert.detected_on) if case else None
    db.insert_case(
        st.session_state["case_id"], st.session_state.get("attempt_id"),
        st.session_state["pattern"] or (audit.pattern_type if audit else ""), narrative, audit,
        structural_score=score_text(narrative)["total"],
        source=case.source if case else None,
        case_input=case.to_dict() if case else None,
        detection=({"detection": audit.detection, "red_flags": audit.red_flags}
                   if audit else None),
        drafted_by=st.session_state.get("drafted_by") or user_name() or None,
        alert_date=(case.alert.detected_on or None) if case else None,
        filing_due=due.isoformat() if due else None,
    )
    if not st.session_state.get("drafted_by"):
        st.session_state["drafted_by"] = user_name()
    st.session_state["last_saved"] = narrative
    list_cases.clear()


def render_export(narrative: str, audit: AuditRecord | None) -> None:
    case = st.session_state.get("case_input")
    if case is None:
        st.caption("Nothing to export.")
        return
    events = []
    if st.session_state.get("db_ok"):
        try:
            events = events_to_dicts(db.get_events(st.session_state["case_id"]))
        except Exception:  # noqa: BLE001
            events = []
    meta = {"case_id": st.session_state["case_id"], "status": st.session_state.get("status"),
            "decision": st.session_state.get("decision_choice"),
            "decision_rationale": st.session_state.get("decision_rationale"),
            "reviewer_notes": st.session_state.get("reviewer_notes"),
            "drafted_by": st.session_state.get("drafted_by"),
            "approved_by": st.session_state.get("approved_by"),
            "filing_due": (filing_due(case.alert.detected_on) or "") and
            filing_due(case.alert.detected_on).isoformat(),
            "events": events}
    n, limit = narrative_length(narrative)
    st.caption(f"Filing text: **{n:,}** of {limit:,} characters allowed in FinCEN SAR Part V.")
    if n > limit:
        st.warning("The narrative is longer than FinCEN allows. Shorten it or move detail into "
                   "a transaction attachment.", icon=":material/warning:")
    bundle = export_bundle(case, audit, narrative, meta)
    for key, name in zip(("narrative", "html", "md", "json"), bundle["_names"]):
        label, content, mime = bundle[key]
        st.download_button(label, content, file_name=name, mime=mime, key=f"dl-{key}",
                           width="stretch", on_click=log_event, args=("exported", {"file": name}))


def render_decision(db_ok: bool, narrative: str, audit: AuditRecord | None) -> None:
    """Approve = decide SAR / No SAR, with maker-checker and the unverified-figure gate."""
    st.markdown("**Decision**")
    status = st.session_state.get("status")
    if status in ("Approved", "No SAR", "Filed"):
        st.caption(f"Recorded: **{status}** by {st.session_state.get('approved_by') or '—'}. "
                   "Deciding again replaces it.")
    choice = st.segmented_control("Decision", ["File SAR", "No SAR"], required=True,
                                  key="decision_choice", label_visibility="collapsed")
    st.text_area("Rationale", key="decision_rationale", height=110,
                 placeholder=("Why no SAR is warranted — required." if choice == "No SAR"
                              else "Optional summary for the case record."))
    counts = grounding_counts(audit) if audit else {"unverified_values": 0}
    ack = True
    if counts["unverified_values"]:
        ack = st.checkbox(f"I checked the {counts['unverified_values']} figure(s) the audit could "
                          "not find in the case data", key="ack_unverified")
    # The wording check is a regex, so a reviewer can confirm a false alarm
    # (e.g. "the prior review found it did not warrant a SAR") instead of rewording.
    if conflict := conclusion_mismatch(narrative, choice == "No SAR"):
        st.caption(f":material/warning: {conflict[0].upper()}{conflict[1:]}.")
        ack = st.checkbox("I checked that the narrative's conclusion matches this decision",
                          key="ack_conclusion") and ack
    maker, me = st.session_state.get("drafted_by", ""), user_name()
    same_person = bool(maker and me and maker.lower() == me.lower())
    missing_rationale = choice == "No SAR" and not st.session_state.get("decision_rationale", "").strip()
    if same_person:
        st.caption(f":material/block: Maker-checker: **{html.escape(maker)}** drafted this case, so "
                   "a different reviewer must approve it. Change *Signed in as* in the sidebar.")
    elif not me:
        st.caption("Enter your name under *Signed in as* in the sidebar.")
    label = "Approve SAR" if choice == "File SAR" else "Close — no SAR"
    if st.button(label, type="primary", icon=":material/check:", key="approve-btn",
                 width="stretch",
                 disabled=not db_ok or same_person or not me or not ack or missing_rationale):
        with st.status("Recording decision", expanded=False) as s:
            _save_case(narrative, audit)
            status = "Approved" if choice == "File SAR" else "No SAR"
            db.update_status(st.session_state["case_id"], status,
                             st.session_state.get("reviewer_notes", ""),
                             decision="SAR" if choice == "File SAR" else "No SAR",
                             decision_rationale=st.session_state.get("decision_rationale", ""),
                             approved_by=me)
            s.update(label=status, state="complete", expanded=False)
        st.session_state["status"] = status
        st.session_state["approved_by"] = me
        log_event("approved" if status == "Approved" else "closed_no_sar",
                  {"decision": status, "unverified_values": counts["unverified_values"]})
        list_cases.clear()
        st.toast(f"Case {st.session_state['case_id']} · {status}")
        st.rerun()


def render_case_header(db_ok: bool) -> None:
    """Record header: identity + status on the left, every case action on the right."""
    case_id = st.session_state.get("case_id", "")
    narrative = st.session_state["narrative"]
    audit = st.session_state.get("audit")
    case = st.session_state.get("case_input")
    edited = narrative != st.session_state.get("last_saved", "")
    status = st.session_state.get("status", "Pending")

    meta = []
    if case is not None:
        src = SOURCE_LABEL.get(case.source, case.source)
        meta.append(f"{src} · attempt #{case.attempt_id}" if case.attempt_id is not None else src)
    pattern = st.session_state.get("pattern") or ""
    if pattern:
        label = html.escape(pattern.replace("-", " ").title())
        if case is not None and case.dataset_label and case.dataset_label != pattern:
            label += f" <small>(dataset label {html.escape(case.dataset_label.title())})</small>"
        meta.append(label)
    if audit and audit.red_flags:
        high = sum(f.get("severity") == "high" for f in audit.red_flags)
        meta.append(f"{len(audit.red_flags)} red flags" + (f" · {high} high" if high else ""))
    if model := st.session_state.get("model"):
        meta.append(f"<code>{html.escape(model)}</code>")
    if st.session_state.get("drafted_by"):
        meta.append(f"Drafted by {html.escape(st.session_state['drafted_by'])}")
    decided = status in ("Approved", "No SAR", "Filed")
    if decided and st.session_state.get("approved_by"):
        meta.append(f"Approved by {html.escape(st.session_state['approved_by'])}")
    due, due_tone = _due_text(case) if not decided else ("", "muted")

    with st.container(horizontal=True, vertical_alignment="bottom", key="case-header"):
        st.html(
            '<div class="ch-eyebrow">SAR case</div>'
            f'<div class="ch-title"><h1>{html.escape(case_id)}</h1>'
            + pill(status, STATUS_TONE.get(status, "muted"))
            + (pill("Unsaved changes", "info") if edited else pill("Saved", "muted"))
            + (pill(due, due_tone) if due else "")
            + '</div><div class="ch-meta">'
            + "".join(f"<span>{m}</span>" for m in meta) + "</div>",
            width="stretch",
        )
        with st.container(horizontal=True, horizontal_alignment="right",
                          vertical_alignment="center", width="content",
                          key="case-actions"):
            with st.popover("Notes", icon=":material/sticky_note_2:",
                            key="reviewer-notes"):
                st.text_input("Reviewer notes", key="reviewer_notes",
                              placeholder="Stored with the decision")
            with st.popover("Export", icon=":material/download:", key="export-pop"):
                render_export(narrative, audit)
            st.button("Edit inputs", icon=":material/edit_note:", key="edit-inputs-btn",
                      on_click=edit_case_inputs, disabled=case is None,
                      help="Back to case intake with this case — add KYC or findings and "
                           "regenerate.")
            if st.button("Save draft", icon=":material/save:",
                         disabled=not db_ok or not edited, key="save-draft-btn"):
                _save_case(narrative, audit)
                st.session_state["status"] = "Pending"
                log_event("saved")
                st.toast(f"Case {case_id} saved as pending")
                st.rerun()

            if st.button("Reject", icon=":material/block:", disabled=not db_ok,
                         key="reject-btn", help="Send the draft back: it needs rework."):
                _save_case(narrative, audit)
                db.update_status(case_id, "Rejected",
                                 st.session_state.get("reviewer_notes", ""))
                st.session_state["status"] = "Rejected"
                log_event("rejected")
                st.toast(f"Case {case_id} rejected")
                st.rerun()

            with st.popover("Decide", icon=":material/gavel:", key="decide-pop",
                            disabled=not db_ok):
                render_decision(db_ok, narrative, audit)

    if not db_ok:
        st.caption("Database offline — save, decide and reject are disabled; export still works.")


def render_metrics(narrative: str, audit: AuditRecord | None) -> None:
    """Stats strip (quality at a glance) + FFIEC section checklist."""
    score = score_text(narrative)
    req_hit, req_total = score["required"].split("/")
    stats = [
        ("Structural completeness", f"{score['total']}<small>/{len(ALL_SECTIONS)}</small>",
         "FFIEC sections present", ""),
        ("Required elements", f"{req_hit}<small>/{req_total}</small>", "Who, what, when, where, why", ""),
    ]
    if audit:
        g = grounding_counts(audit)
        stats += [
            ("Fully sourced", f"{g['grounded']}<small>/{len(audit.narrative_sentences)}</small>",
             "Cite case data and analysis (not proof they're true)", ""),
            ("Needs attention", f"{g['unverified'] + g['ungrounded']}",
             f"{g['unverified_values']} figure(s) or relationship(s) not in the case data · "
             f"{g['ungrounded']} with no source", "alarm" if g["unverified"] else ""),
        ]
    tiles = "".join(
        f'<div class="stat"><div class="k">{k}</div><div class="v {cls}">{v}</div>'
        f'<div class="h">{h}</div></div>' for k, v, h, cls in stats
    )
    chips = "".join(
        pill(sec, "ok" if present else "off muted")
        for sec, present in score["sections"].items()
    )
    st.html(f'<div class="stats">{tiles}</div>'
            f'<div class="sections"><span class="lbl">FFIEC sections</span>{chips}</div>')


def _kv(rows: list[tuple[str, str]]) -> str:
    rows = [(k, v) for k, v in rows if v]
    if not rows:
        return ""
    return '<dl class="kv-grid">' + "".join(
        f"<dt>{html.escape(k)}</dt><dd>{html.escape(str(v))}</dd>" for k, v in rows) + "</dl>"


def draft_issues(narrative: str, audit: AuditRecord | None,
                 notes: dict[int, list[str]]) -> list[str]:
    """Everything wrong with the current text as a whole, re-checked on every edit:
    missing sections, no alternative explanation, prior SAR not cited, a conclusion
    that contradicts the decision, a different typology named, stale values."""
    case = st.session_state.get("case_input")
    # Generation rejects drafts missing a required section; an edit can still delete one.
    sections = score_text(narrative)["sections"]
    missing = [s for s in REQUIRED_SECTIONS if not sections[s]]
    issues = ([f"missing required sections: {', '.join(missing)}"] if missing else []) \
        + draft_warnings(narrative, case.prior_sars if case else ())
    if conflict := conclusion_mismatch(narrative, decided_no_sar()):
        issues.append(conflict)
    if audit:
        other = [f"S{s.sentence_index}" for s in audit.narrative_sentences
                 if typology_mismatch(s.sentence_text, audit.pattern_type)]
        if other:
            issues.append(f"{', '.join(other)} name{'s' if len(other) == 1 else ''} a different "
                          f"typology from this case's ({audit.pattern_type})")
    stale = [f"S{i}" for i, ns in sorted(notes.items()) if any(n.startswith("Still says") for n in ns)]
    if stale:
        issues.append(f"{', '.join(stale)} still state{'s' if len(stale) == 1 else ''} a value "
                      "you changed in another sentence")
    return issues


def render_draft_warnings(narrative: str, audit: AuditRecord | None,
                          notes: dict[int, list[str]]) -> None:
    """The banner clears only when the text is actually fixed."""
    issues = draft_issues(narrative, audit, notes)
    if not issues:
        return
    edited = narrative != st.session_state.get("baseline_narrative")
    st.warning(("**The edited draft still needs fixing:**" if edited
                else "**This draft needs fixing before approval:**")
               + "".join(f"\n- {i[0].upper()}{i[1:]}" for i in issues),
               icon=":material/rule:")


def render_case_evidence() -> None:
    """Funds flow, red flags, transactions, subject/investigation and history."""
    case = st.session_state.get("case_input")
    audit = st.session_state.get("audit")
    if case is None:
        return
    flags = audit.red_flags if audit else []
    flagged = case.flagged()
    with st.expander("Case evidence", icon=":material/account_tree:"):
        tabs = st.tabs(["Funds flow", f"Red flags ({len(flags)})",
                        f"Transactions ({len(flagged)})", "Subject & investigation", "History"])
        with tabs[0]:
            roles = (audit.detection or {}).get("roles", {}) if audit else {}
            render_funds_flow(flagged, roles, case.subject.accounts)
        with tabs[1]:
            det = audit.detection if audit else {}
            if det:
                st.markdown(f"**Typology:** {det.get('pattern')} ({det.get('confidence')} "
                            "confidence) — " + " ".join(det.get("evidence", [])))
            render_red_flags(flags)
        with tabs[2]:
            st.dataframe(case.transactions, hide_index=True, width="stretch", height=300,
                         column_order=["Flagged", "Timestamp", "From_Account", "From_Entity_Name",
                                       "To_Account", "To_Entity_Name", "Amount Paid",
                                       "Payment Currency", "Amount Received",
                                       "Receiving Currency", "Payment Format", "To_Country"])
        with tabs[3]:
            s, a, inv = case.subject, case.alert, case.investigation
            body = _kv([("Subject", s.name), ("Type", s.subject_type),
                        ("Occupation / business", s.occupation), ("Country", s.country),
                        ("Accounts", ", ".join(s.accounts)),
                        ("Relationship since", s.account_opened),
                        ("Expected monthly volume", f"${s.expected_monthly_volume:,.2f}"
                         if s.expected_monthly_volume else ""),
                        ("Risk rating", s.risk_rating), ("Alert", a.source),
                        ("Alert date", a.detected_on), ("Trigger", a.description),
                        ("Steps", "; ".join(inv.steps)), ("Findings", inv.findings),
                        ("Ruled out", inv.ruled_out),
                        ("Prior SARs", "; ".join(f"{p.filed_on} {p.reference}"
                                                 for p in case.prior_sars))])
            if body:
                st.html(body)
            else:
                st.caption("No customer profile or investigation notes on this case. Use "
                           "**Edit inputs** to add them — the narrative can then describe the "
                           "customer baseline and the steps you took.")
        with tabs[4]:
            events = []
            if st.session_state.get("db_ok"):
                try:
                    events = events_to_dicts(db.get_events(st.session_state["case_id"]))
                except Exception:  # noqa: BLE001
                    events = []
            if events:
                st.dataframe(pd.DataFrame(events)[["at", "actor", "action"]], hide_index=True,
                             width="stretch")
            else:
                st.caption("No recorded history yet (history is stored once the database is "
                           "connected).")
            if audit and audit.generation_config:
                cfg = audit.generation_config
                st.caption(f"Generation record: model `{cfg.get('model')}` · seed "
                           f"{cfg.get('seed')} · prompt `{cfg.get('prompt_version')}` · input "
                           f"`{cfg.get('input_fingerprint')}` · num_ctx {cfg.get('num_ctx')}")


def main() -> None:
    st.set_page_config(
        page_title="SAR narrative generator",
        page_icon=":material/shield:",
        layout="wide",
    )

    db_ok = init_database()
    st.session_state["db_ok"] = db_ok
    st.html(LIQUID_GLASS_CSS)
    st.html(LIQUID_GLASS_JS, unsafe_allow_javascript=True)
    # Before the sidebar, so the expand/focus script runs even if the sidebar errors.
    if target := st.session_state.pop("sidebar_focus", None):
        render_sidebar_focus(target)
    sidebar(db_ok)

    if "pending_generation" in st.session_state:
        run_pending_generation()
    if notice := st.session_state.pop("generated_notice", None):
        st.toast(notice, icon=":material/check_circle:")

    if st.session_state.get("screen") == "intake":
        render_intake(on_generate=request_generation, on_discard=discard_intake,
                      busy="pending_generation" in st.session_state)
        return
    if "narrative" not in st.session_state:
        render_empty_state()
        return

    # A rerun can interrupt the edit callback after the text is stored but before
    # its audit is (the first rebuild loads the embedding model), so re-sync here.
    if st.session_state.get("audit_for") != st.session_state["narrative"]:
        refresh_audit()
    render_case_header(db_ok)
    st.space("small")
    render_metrics(st.session_state["narrative"], st.session_state.get("audit"))
    notes = consistency_notes(st.session_state.get("audit"), st.session_state.get("baseline_audit"))
    render_draft_warnings(st.session_state["narrative"], st.session_state.get("audit"), notes)
    render_case_evidence()
    st.space("small")

    left, right = st.columns(2)
    with left:
        render_draft_pane(notes)
    with right:
        with st.container(horizontal=True, vertical_alignment="center", key="pane-head-audit"):
            st.subheader("Audit trail", icon=":material/fact_check:")
        audit_pane(st.session_state.get("audit"), st.session_state.get("baseline_audit"),
                   st.session_state["narrative"], key="audit_doc", height=PANE_HEIGHT,
                   notes=notes)


if __name__ == "__main__":
    main()