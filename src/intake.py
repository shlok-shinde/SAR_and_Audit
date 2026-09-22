"""
intake.py — The "new case" screen: build a CaseInput from the analyst's own data.

Four tabs, all rendered on every run (so no widget state is ever dropped when
the analyst moves between them):
  1. Transactions        — upload CSV/XLSX (IBM, canonical, generic export or a
                           single-account statement), map columns, edit the grid
  2. Subject & alert     — KYC profile (the customer baseline) and the trigger
  3. Investigation       — steps taken, findings, ruled-out explanations, prior SARs
  4. Review & generate   — rule-based typology + red flags, funds-flow graph,
                           prompt budget, then queue generation

Also home to the funds-flow graph (reused in the review workspace).
"""

from __future__ import annotations

import html
from datetime import date, datetime

import pandas as pd
import streamlit as st

from case_input import (
    ALERT_SOURCES, FIELDS, INVESTIGATION_STEPS, RISK_RATINGS, SUBJECT_TYPES, Alert, CaseInput,
    Investigation, PriorSAR, Subject, empty_transactions, finalize_transactions, guess_dayfirst,
    import_table, parse_iso_date, read_table, suggest_mapping, template_csv,
)
from typology import PATTERNS, analyse_case, effective_pattern, warrants_no_sar

S = st.session_state
NONE = "—"
USE_DETECTION = "Use rule-based detection"

GRID_ORDER = ["Flagged", "Timestamp", "From_Account", "From_Entity_Name", "From_Bank_Name",
              "To_Account", "To_Entity_Name", "To_Bank_Name", "Amount Paid", "Payment Currency",
              "Amount Received", "Receiving Currency", "Payment Format", "From_Country",
              "To_Country", "From Bank", "To Bank", "Txn_ID"]

# Mapping fields shown for generic uploads (the rest stay in "More fields").
MAIN_FIELDS = ["timestamp", "from_account", "to_account", "amount", "currency",
               "payment_format", "from_name", "to_name", "flagged"]

KYC_TEXT = {"kyc_name": "name", "kyc_occ": "occupation", "kyc_country": "country",
            "kyc_address": "address", "kyc_notes": "notes"}


# ── State ────────────────────────────────────────────────────────────────────

def _empty_prior() -> pd.DataFrame:
    return pd.DataFrame({"Filed on": pd.Series(dtype="datetime64[ns]"),
                         "Reference": pd.Series(dtype=str),
                         "Amount": pd.Series(dtype=float),
                         "Period start": pd.Series(dtype="datetime64[ns]"),
                         "Period end": pd.Series(dtype="datetime64[ns]")})


def _intake() -> dict:
    if "intake" not in S:
        S["intake"] = {"base": empty_transactions(), "raw": None, "fmt": "", "filename": "",
                       "issues": [], "source": "manual", "attempt_id": None,
                       "dataset_label": "", "degree_info": "", "prior_base": _empty_prior(),
                       "rev": 0}
    return S["intake"]


def new_case_id() -> str:
    return f"C-{datetime.now():%y%m%d-%H%M}"


def seed_intake(case: CaseInput | None = None) -> None:
    """Load a case (sample / saved / current) or a blank one into the intake form.

    Must run in a callback (before widgets render) because it sets widget keys.
    """
    rev = _intake()["rev"] + 1
    S["intake"] = {
        "base": case.transactions.copy() if case else empty_transactions(),
        "raw": None, "fmt": "", "filename": "", "issues": [],
        "source": case.source if case else "manual",
        "attempt_id": case.attempt_id if case else None,
        "dataset_label": case.dataset_label if case else "",
        "degree_info": case.degree_info if case else "",
        "prior_base": _prior_frame(case.prior_sars) if case else _empty_prior(),
        "rev": rev,
    }
    subj = case.subject if case else Subject()
    alert = case.alert if case else Alert()
    inv = case.investigation if case else Investigation()
    S["in_case_id"] = case.case_id if case and case.case_id else new_case_id()
    for key, attr in KYC_TEXT.items():
        S[key] = getattr(subj, attr) or ""
    S["kyc_type"] = subj.subject_type or ""
    S["kyc_risk"] = subj.risk_rating or ""
    S["kyc_accounts"] = list(subj.accounts)
    S["kyc_opened"] = parse_iso_date(subj.account_opened)
    S["kyc_vol"] = subj.expected_monthly_volume
    S["kyc_count"] = subj.expected_monthly_count
    S["al_source"] = alert.source or ""
    S["al_id"] = alert.alert_id or ""
    S["al_date"] = parse_iso_date(alert.detected_on)
    S["al_desc"] = alert.description or ""
    S["inv_steps"] = [s for s in inv.steps if s in INVESTIGATION_STEPS]
    S["inv_findings"] = inv.findings or ""
    S["inv_ruled"] = inv.ruled_out or ""
    S["in_override"] = case.pattern_override if case and case.pattern_override else USE_DETECTION
    S.pop("in_upload", None)
    S["screen"] = "intake"


def _prior_frame(prior: list[PriorSAR]) -> pd.DataFrame:
    if not prior:
        return _empty_prior()
    return pd.DataFrame({
        "Filed on": pd.to_datetime([p.filed_on or None for p in prior]),
        "Reference": [p.reference for p in prior],
        "Amount": [p.amount for p in prior],
        "Period start": pd.to_datetime([p.period_start or None for p in prior]),
        "Period end": pd.to_datetime([p.period_end or None for p in prior]),
    })


def _iso(value) -> str:
    if value is None or (not isinstance(value, (str, date)) and pd.isna(value)):
        return ""
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    d = parse_iso_date(value)
    return d.isoformat() if d else ""


# ── Upload / mapping callbacks ───────────────────────────────────────────────

def _on_upload() -> None:
    f = S.get("in_upload")
    if f is None:
        return
    it = _intake()
    try:
        raw = read_table(f, f.name)
    except Exception as e:  # noqa: BLE001 — surface any parse failure to the analyst
        it["issues"] = [{"level": "error", "message": f"Could not read {f.name}: {e}"}]
        return
    it.update(raw=raw, filename=f.name, source="upload", attempt_id=None, dataset_label="",
              degree_info="")
    from case_input import detect_format
    it["fmt"] = detect_format(raw)
    if it["fmt"] == "generic":
        mapping = suggest_mapping(raw.columns)
        for key in FIELDS:
            S[f"map_{key}"] = mapping.get(key, NONE)
        ts_col = mapping.get("timestamp")
        S["in_dayfirst"] = bool(ts_col and guess_dayfirst(raw[ts_col].dropna()))
    _remap()


def _remap() -> None:
    it = _intake()
    raw = it.get("raw")
    if raw is None:
        return
    mapping = None
    if it["fmt"] == "generic":
        mapping = {k: S.get(f"map_{k}") for k in FIELDS if S.get(f"map_{k}") not in (None, NONE)}
    canonical, issues, _, _ = import_table(
        raw, mapping, dayfirst=bool(S.get("in_dayfirst")),
        statement_account=(S.get("in_stmt_acct") or "").strip())
    it.update(base=canonical, issues=issues)
    it["rev"] += 1


def _start_blank() -> None:
    it = _intake()
    it.update(base=empty_transactions(), raw=None, fmt="", filename="", issues=[],
              source="manual", attempt_id=None, dataset_label="", degree_info="")
    it["rev"] += 1


# ── Building the case ────────────────────────────────────────────────────────

def current_case() -> tuple[CaseInput, list[dict]]:
    """The CaseInput described by the form right now, plus grid validation issues."""
    it = _intake()
    edited = it.get("edited", it["base"])
    txns, issues = finalize_transactions(edited)
    prior_df = it.get("prior_edited", it["prior_base"])
    prior = []
    for _, r in prior_df.iterrows():
        entry = PriorSAR(filed_on=_iso(r.get("Filed on")), reference=str(r.get("Reference") or ""),
                         amount=float(r["Amount"]) if pd.notna(r.get("Amount")) else None,
                         period_start=_iso(r.get("Period start")),
                         period_end=_iso(r.get("Period end")))
        if entry.filed_on or entry.reference:
            prior.append(entry)
    override = S.get("in_override", USE_DETECTION)
    case = CaseInput(
        case_id=(S.get("in_case_id") or "").strip() or new_case_id(),
        transactions=txns,
        source=it["source"],
        attempt_id=it["attempt_id"],
        dataset_label=it["dataset_label"],
        degree_info=it["degree_info"],
        subject=Subject(
            name=S.get("kyc_name", "").strip(), subject_type=S.get("kyc_type") or "",
            occupation=S.get("kyc_occ", "").strip(), country=S.get("kyc_country", "").strip(),
            address=S.get("kyc_address", "").strip(),
            accounts=[a for a in S.get("kyc_accounts", []) if a],
            account_opened=_iso(S.get("kyc_opened")),
            expected_monthly_volume=S.get("kyc_vol") or None,
            expected_monthly_count=int(S["kyc_count"]) if S.get("kyc_count") else None,
            risk_rating=S.get("kyc_risk") or "", notes=S.get("kyc_notes", "").strip()),
        alert=Alert(source=S.get("al_source") or "", alert_id=S.get("al_id", "").strip(),
                    detected_on=_iso(S.get("al_date")), description=S.get("al_desc", "").strip()),
        investigation=Investigation(steps=list(S.get("inv_steps") or []),
                                    findings=S.get("inv_findings", "").strip(),
                                    ruled_out=S.get("inv_ruled", "").strip()),
        prior_sars=prior,
        pattern_override="" if override == USE_DETECTION else override,
    )
    return case, issues


# ── Funds-flow graph ─────────────────────────────────────────────────────────

ROLE_COLOUR = {  # hubs amber, pass-through grey, endpoints neutral
    "hub": "#D9AE5B", "source": "#D9AE5B", "collector": "#D9AE5B",
    "source and destination": "#D9AE5B", "cycle member": "#D9AE5B",
    "intermediary": "#A3A3A3", "chain": "#A3A3A3", "round-trip member": "#A3A3A3",
}


def funds_flow_dot(df: pd.DataFrame, roles: dict | None = None,
                   subject_accounts=(), max_nodes: int = 40) -> str:
    """Graphviz DOT of who paid whom: nodes = accounts, edges = aggregated transfers."""
    roles = roles or {}
    subject_accounts = set(subject_accounts)
    if df.empty:
        return "digraph { }"
    pairs = (df.groupby(["From_Account", "To_Account", "Payment Currency"])
             .agg(n=("Amount Paid", "size"), total=("Amount Paid", "sum"))
             .reset_index().sort_values("total", ascending=False))
    volume = pd.concat([pairs.groupby("From_Account")["total"].sum(),
                        pairs.groupby("To_Account")["total"].sum()]).groupby(level=0).sum()
    keep = set(volume.sort_values(ascending=False).head(max_nodes).index)
    names: dict[str, str] = {}
    for side in ("From", "To"):
        for acct, name, bank in zip(df[f"{side}_Account"], df[f"{side}_Entity_Name"],
                                    df[f"{side}_Bank_Name"]):
            names.setdefault(acct, " · ".join(x for x in (name, bank) if x and x != "Unknown"))

    def q(text: str) -> str:
        return '"' + (str(text).replace("\\", "\\\\").replace('"', '\\"')
                      .replace("\n", "\\n")) + '"'

    lines = ['digraph G {', 'graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.25, '
             'ranksep=0.55, fontname="Helvetica"];',
             'node [shape=box, style="rounded,filled", fillcolor="#2F2F2F", color="#4A4A4A", '
             'fontcolor="#EDEDED", fontname="Helvetica", fontsize=12, penwidth=1.2, margin="0.14,0.07"];',
             'edge [color="#767676", fontcolor="#A3A3A3", fontname="Helvetica", fontsize=11, '
             'arrowsize=0.6, penwidth=1.1];']
    for acct in keep:
        role = roles.get(acct, "")
        name = names.get(acct, "")
        label = acct + (f"\n{name[:26] + ('…' if len(name) > 26 else '')}" if name else "")
        attrs = [f"label={q(label)}"]
        if role in ROLE_COLOUR:
            attrs.append(f'color="{ROLE_COLOUR[role]}"')
        if acct in subject_accounts:
            attrs += ['color="#8FB3E8"', "penwidth=2.2", 'fillcolor="#2C3440"']
        lines.append(f"{q(acct)} [{', '.join(attrs)}];")
    for _, r in pairs.iterrows():
        if r["From_Account"] in keep and r["To_Account"] in keep:
            ccy = "$" if str(r["Payment Currency"]).lower() in ("usd", "us dollar") else ""
            amount = (f"{ccy}{r['total']:,.0f}" if ccy
                      else f"{r['total']:,.0f} {r['Payment Currency']}")
            label = f"{int(r['n'])}× {amount}" if r["n"] > 1 else amount
            lines.append(f"{q(r['From_Account'])} -> {q(r['To_Account'])} [label={q(label)}];")
    hidden = len(volume) - len(keep)
    if hidden > 0:
        lines.append(f'more [shape=plaintext, style="", label="+{hidden} smaller accounts", '
                     'fontcolor="#767676"];')
    lines.append("}")
    return "\n".join(lines)


def render_funds_flow(df: pd.DataFrame, roles=None, subject_accounts=()) -> None:
    if df.empty:
        st.caption("No transactions to draw.")
        return
    st.graphviz_chart(funds_flow_dot(df, roles, subject_accounts), width="stretch")
    st.caption("Boxes are accounts; arrows show money moving, with transfer count and total. "
               "Amber outline = hub or origin in the detected pattern · grey = pass-through · "
               "blue = the subject's accounts.")


# ── Rendering helpers ────────────────────────────────────────────────────────

SEVERITY_TONE = {"high": "bad", "medium": "warn", "low": "muted"}


def pill(label: str, tone: str = "muted") -> str:
    return f'<span class="pill {tone}"><span class="dot"></span>{html.escape(label)}</span>'


def render_red_flags(flags) -> None:
    if not flags:
        st.caption("No red flags raised by the rules.")
        return
    for f in flags:
        sev = f.severity if hasattr(f, "severity") else f.get("severity", "")
        title = f.title if hasattr(f, "title") else f.get("title", "")
        ev = f.evidence if hasattr(f, "evidence") else f.get("evidence", "")
        st.html(f'<div class="rf">{pill(sev.upper(), SEVERITY_TONE.get(sev, "muted"))}'
                f'<div><div class="rf-t">{html.escape(title)}</div>'
                f'<div class="rf-e">{html.escape(ev)}</div></div></div>')


def _issues(issues: list[dict]) -> None:
    for i in issues:
        (st.error if i["level"] == "error" else st.warning)(i["message"],
                                                            icon=":material/error:" if i["level"] == "error"
                                                            else ":material/warning:")


# ── Tabs ─────────────────────────────────────────────────────────────────────

def _tab_transactions() -> None:
    it = _intake()
    with st.container(horizontal=True, vertical_alignment="bottom", key="in-upload-row"):
        st.file_uploader("Upload transactions (CSV or Excel)", type=["csv", "xlsx", "xls", "txt"],
                         key="in_upload", on_change=_on_upload,
                         help="IBM AML Trans.csv, a from/to transaction export, or a single-account "
                              "statement with Debit/Credit columns.")
        with st.container(width="content"):
            st.download_button("CSV template", template_csv(), "sar_case_template.csv", "text/csv",
                               icon=":material/download:", key="in-template")
            st.button("Start blank", icon=":material/add:", key="in-blank", on_click=_start_blank)

    if it.get("raw") is not None:
        label = {"ibm_trans": "IBM AML Trans.csv format", "canonical": "Canonical format",
                 "generic": "Generic export — check the column mapping"}.get(it["fmt"], "")
        st.caption(f"**{html.escape(it['filename'])}** · {len(it['raw'])} rows · {label}")
        if it["fmt"] == "generic":
            options = [NONE] + list(it["raw"].columns)
            with st.expander("Column mapping", icon=":material/table_edit:",
                             expanded=any(i["level"] == "error" for i in it["issues"])):
                cols = st.columns(3)
                for n, key in enumerate(MAIN_FIELDS):
                    S.setdefault(f"map_{key}", NONE)
                    cols[n % 3].selectbox(FIELDS[key][0], options, key=f"map_{key}", on_change=_remap)
                with st.popover("More fields", icon=":material/more_horiz:"):
                    for key in FIELDS:
                        if key not in MAIN_FIELDS:
                            S.setdefault(f"map_{key}", NONE)
                            st.selectbox(FIELDS[key][0], options, key=f"map_{key}", on_change=_remap)
                c1, c2 = st.columns(2)
                c1.toggle("Dates are day-first (dd/mm/yyyy)", key="in_dayfirst", on_change=_remap)
                if (S.get("map_debit", NONE) != NONE or S.get("map_credit", NONE) != NONE):
                    c2.text_input("Statement account number", key="in_stmt_acct", on_change=_remap,
                                  help="The account this statement belongs to (one side of every row).")
        _issues(it["issues"])

    st.caption("Tick **Flagged** for the transactions the SAR is about; unflagged rows are used as the "
               "account's normal baseline. Dates like 2024/06/03 14:40.")
    edited = st.data_editor(
        it["base"], key=f"in_grid_{it['rev']}", num_rows="dynamic", hide_index=True,
        width="stretch", height=360, column_order=GRID_ORDER,
        column_config={
            "Flagged": st.column_config.CheckboxColumn("Flagged", default=True, width="small"),
            "Timestamp": st.column_config.TextColumn("Date / time", required=True),
            "From_Account": st.column_config.TextColumn("From account", required=True),
            "From_Entity_Name": st.column_config.TextColumn("From name"),
            "From_Bank_Name": st.column_config.TextColumn("From bank"),
            "To_Account": st.column_config.TextColumn("To account", required=True),
            "To_Entity_Name": st.column_config.TextColumn("To name"),
            "To_Bank_Name": st.column_config.TextColumn("To bank"),
            "Amount Paid": st.column_config.NumberColumn("Amount paid", format="%.2f", min_value=0),
            "Payment Currency": st.column_config.TextColumn("Paid ccy"),
            "Amount Received": st.column_config.NumberColumn("Amount received", format="%.2f",
                                                             min_value=0),
            "Receiving Currency": st.column_config.TextColumn("Received ccy"),
            "Payment Format": st.column_config.TextColumn("Method"),
            "From_Country": st.column_config.TextColumn("From country"),
            "To_Country": st.column_config.TextColumn("To country"),
            "From Bank": st.column_config.TextColumn("From bank ID"),
            "To Bank": st.column_config.TextColumn("To bank ID"),
            "Txn_ID": st.column_config.TextColumn("Ref"),
        },
    )
    it["edited"] = edited
    _, grid_issues = finalize_transactions(edited)
    it["grid_issues"] = grid_issues
    if not edited.empty:
        _issues([i for i in grid_issues if i not in it["issues"]])


def _tab_subject(accounts: list[str]) -> None:
    st.markdown("**Subject (KYC profile)**")
    st.caption("The customer baseline examiners look for. The narrative only uses facts you enter; "
               "nothing here is invented.")
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.text_input("Name", key="kyc_name", placeholder="Person or business the SAR is about")
    c2.selectbox("Type", SUBJECT_TYPES, key="kyc_type", format_func=lambda x: x or "—")
    c3.selectbox("Risk rating", RISK_RATINGS, key="kyc_risk", format_func=lambda x: x or "—")
    c1, c2 = st.columns([2, 1])
    c1.text_input("Occupation / nature of business", key="kyc_occ",
                  placeholder="e.g. Retail auto parts store")
    c2.text_input("Country", key="kyc_country", placeholder="e.g. US")
    st.text_input("Address", key="kyc_address")
    options = sorted(set(accounts) | set(S.get("kyc_accounts", [])))
    st.multiselect("Subject's accounts", options, key="kyc_accounts", accept_new_options=True,
                   help="Which accounts in the data belong to the subject. Drives the profile checks "
                        "and highlights them in the funds-flow graph.")
    c1, c2, c3 = st.columns(3)
    c1.date_input("Relationship since / account opened", key="kyc_opened", format="YYYY-MM-DD")
    c2.number_input("Expected monthly incoming volume ($)", key="kyc_vol", min_value=0.0,
                    step=1000.0, format="%.2f")
    c3.number_input("Expected transactions per month", key="kyc_count", min_value=0, step=1)
    st.text_area("Other KYC notes", key="kyc_notes", height=68)

    st.markdown("**Alert / referral**")
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.selectbox("Source", [""] + ALERT_SOURCES, key="al_source", format_func=lambda x: x or "—")
    c2.text_input("Alert ID", key="al_id")
    c3.date_input("Detected on", key="al_date", format="YYYY-MM-DD",
                  help="Starts the 30-day SAR filing clock.")
    st.text_area("What triggered the review", key="al_desc", height=68)


def _tab_investigation() -> None:
    it = _intake()
    st.pills("Investigation steps completed", INVESTIGATION_STEPS, selection_mode="multi",
             key="inv_steps", help="Only these steps will be described in the narrative.")
    st.text_area("Findings", key="inv_findings", height=100,
                 placeholder="What the review established, customer explanations, documents obtained…")
    st.text_area("Explanations considered and ruled out", key="inv_ruled", height=80,
                 placeholder="e.g. Seasonal sales ruled out: prior months show no cash activity.")
    st.markdown("**Prior SARs on this subject**")
    st.caption("Adding one makes this a continuing-activity SAR: the draft cites prior filings by "
               "date and amount instead of re-narrating them.")
    it["prior_edited"] = st.data_editor(
        it["prior_base"], key=f"in_prior_{it['rev']}", num_rows="dynamic", hide_index=True,
        width="stretch",
        column_config={
            "Filed on": st.column_config.DateColumn("Filed on", format="YYYY-MM-DD"),
            "Reference": st.column_config.TextColumn("BSA ID / reference"),
            "Amount": st.column_config.NumberColumn("Amount reported ($)", format="%.2f"),
            "Period start": st.column_config.DateColumn("Period start", format="YYYY-MM-DD"),
            "Period end": st.column_config.DateColumn("Period end", format="YYYY-MM-DD"),
        },
    )


def _tab_review(case: CaseInput, issues: list[dict], on_generate, busy: bool) -> None:
    from generate_narrative import NUM_CTX, NUM_PREDICT, estimate_prompt_tokens

    errors = [i for i in issues if i["level"] == "error"]
    if errors:
        st.error("Fix the transaction errors on the **Transactions** tab before generating.",
                 icon=":material/error:")
        for e in errors:
            st.caption(f"• {e['message']}")
        return

    detection, flags = analyse_case(case)
    flagged, context = case.flagged(), case.context()
    ccys = flagged.groupby("Payment Currency")["Amount Paid"].sum()
    total = " + ".join(f"${v:,.0f}" if str(c).lower() in ("usd", "us dollar") else f"{v:,.0f} {c}"
                       for c, v in ccys.items())
    tiles = [("In scope", f"{len(flagged)}", f"{len(context)} baseline rows"),
             ("Accounts", f"{len(set(flagged['From_Account']) | set(flagged['To_Account']))}",
              "in the flagged activity"),
             ("Period", f"{flagged['Timestamp'].min()[:10]}",
              f"to {flagged['Timestamp'].max()[:10]}"),
             ("Moved", total or "0", "flagged total paid")]
    st.html('<div class="stats">' + "".join(
        f'<div class="stat"><div class="k">{k}</div><div class="v">{html.escape(v)}</div>'
        f'<div class="h">{html.escape(h)}</div></div>' for k, v, h in tiles) + "</div>")

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("**Typology**")
        tone = {"high": "ok", "medium": "warn", "low": "muted"}[detection.confidence]
        st.html(f'<div class="det"><span class="det-p">{html.escape(detection.pattern)}</span>'
                f'{pill(detection.confidence + " confidence", tone)}'
                + (pill(f"dataset label: {case.dataset_label}", "info")
                   if case.dataset_label else "") + "</div>"
                + "".join(f'<p class="det-e">{html.escape(e)}</p>' for e in detection.evidence)
                + (f'<p class="det-a">Also consistent with: {", ".join(detection.alternatives)}</p>'
                   if detection.alternatives else ""))
        st.selectbox("Pattern used for the narrative", [USE_DETECTION] + PATTERNS, key="in_override",
                     help="Override the rule-based detection if your investigation found otherwise.")
        pattern = effective_pattern(case, detection)
        if warrants_no_sar(pattern, flags):
            st.info("No known typology and no high-severity red flag: the draft will conclude that "
                    "the activity does not warrant a SAR. You still make the final decision.",
                    icon=":material/info:")
        if case.is_continuing():
            st.info("Continuing-activity SAR: prior filings will be cited by date and amount.",
                    icon=":material/history:")
    with right:
        st.markdown("**Red flags**")
        render_red_flags(flags)
    st.markdown("**Funds flow**")
    render_funds_flow(flagged, detection.roles, case.subject.accounts)

    tokens = estimate_prompt_tokens(case, detection, flags)
    budget = NUM_CTX - NUM_PREDICT
    st.progress(min(tokens / budget, 1.0),
                text=f"Prompt size ≈ {tokens:,} of {budget:,} tokens available "
                     f"({NUM_CTX:,} context − {NUM_PREDICT:,} reserved for the answer)")
    over = tokens > budget
    if over:
        st.error("The case is too large for the model's context window. Flag fewer transactions "
                 "or shorten the notes.", icon=":material/error:")
    st.button("Generate draft and audit trail", type="primary", icon=":material/auto_awesome:",
              key="intake-generate-btn", disabled=over or busy, on_click=on_generate, args=(case,),
              width="stretch")


def render_intake(on_generate, on_discard, busy: bool = False) -> None:
    """The new-case screen. `on_generate(case)` queues generation."""
    it = _intake()
    S.setdefault("in_case_id", new_case_id())
    with st.container(horizontal=True, vertical_alignment="bottom", key="intake-head"):
        st.html('<div class="ch-eyebrow">New case</div>'
                '<div class="ch-title"><h1>Case intake</h1></div>'
                '<div class="ch-meta"><span>Your transactions, customer profile and findings</span>'
                '<span>Rules detect the typology before the model writes</span></div>',
                width="stretch")
        st.text_input("Case ID", key="in_case_id", width=200)
        st.button("Discard", icon=":material/close:", key="in-discard", on_click=on_discard)

    case, issues = current_case()
    accounts = sorted(set(case.transactions["From_Account"]) | set(case.transactions["To_Account"]))
    n, flagged = len(case.transactions), int(case.transactions["Flagged"].sum())
    done = [
        f"{n} transactions · {flagged} flagged" if n else "No transactions yet",
        "Subject ✓" if case.subject.name else "No subject profile",
        "Alert ✓" if case.alert.source or case.alert.detected_on else "No alert details",
        f"{len(case.investigation.steps)} investigation steps",
        f"{len(case.prior_sars)} prior SARs" if case.prior_sars else "",
    ]
    st.html('<div class="ch-meta intake-progress">'
            + "".join(f"<span>{html.escape(d)}</span>" for d in done if d) + "</div>")
    # Tab labels must stay constant: a label that changes (e.g. a live count)
    # makes Streamlit treat it as a new tab and jump back to the first one.
    tabs = st.tabs(["1 · Transactions", "2 · Subject & alert", "3 · Investigation",
                    "4 · Review & generate"])
    with tabs[0]:
        _tab_transactions()
    # Re-read after the grid rendered, so later tabs see this run's edits.
    case, issues = current_case()
    with tabs[1]:
        _tab_subject(accounts)
    with tabs[2]:
        _tab_investigation()
    case, issues = current_case()
    with tabs[3]:
        _tab_review(case, issues, on_generate, busy)
