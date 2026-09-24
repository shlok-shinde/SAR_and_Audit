"""
audit_trail.py — Sentence-level provenance tracking for SAR narratives.

Captures:
  - Which ChromaDB chunks were retrieved for generation
  - Which transaction fields each sentence references
  - Structured JSON audit records linking every claim to its source data

This is the differentiator — not just "what the model said" but a provenance
record of *why* each claim was made.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd


# ── Data Structures ──────────────────────────────────────────────────────────

def _known(cls, data: dict):
    """Instantiate a dataclass from a dict, dropping keys it doesn't define."""
    from dataclasses import fields as dc_fields
    names = {f.name for f in dc_fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class RetrievedChunk:
    """Metadata for a single chunk retrieved from ChromaDB."""
    chunk_id: str
    source_file: str
    page_number: int
    pattern_type: str
    distance: float
    relevance_score: float  # 1 - distance
    text_preview: str  # first 200 chars of chunk text
    query_type: str  # "label" or "description"


@dataclass
class RetrievalMetadata:
    """Full metadata about the retrieval step."""
    label_query: str
    description_query: str
    top_k: int
    chunks_returned: list[RetrievedChunk] = field(default_factory=list)
    dedup_count: int = 0  # how many chunks were removed by deduplication
    total_candidates: int = 0  # total before dedup


@dataclass
class FieldReference:
    """A single data field reference found in a narrative sentence."""
    field_name: str  # e.g. "Amount Paid", "From_Account", "Timestamp"
    field_value: str  # the actual value found
    match_type: str  # "exact", "derived", "approximate", "entity_name", "case_fact",
                     # "regulatory" — or "unverified" (not found in the case data)
    note: str = ""   # for unverified values: the closest value that does exist


@dataclass
class SentenceProvenance:
    """Provenance record for a single sentence in the generated narrative."""
    sentence_index: int
    sentence_text: str
    section: str  # Which FFIEC section (Who, What, When, etc.)
    field_references: list[FieldReference] = field(default_factory=list)
    chunk_attributions: list[str] = field(default_factory=list)  # chunk_ids
    typology_match: str | None = None
    confidence_note: str = ""
    # Red-flag codes (typology.py) whose rule-based evidence the sentence restates
    rule_attributions: list[str] = field(default_factory=list)
    # Figures/identifiers in the sentence that the case data does not contain
    unverified_values: list[FieldReference] = field(default_factory=list)
    # Set when the sentence can't be checked mechanically (e.g. it negates case data)
    needs_review: str = ""


@dataclass
class AuditRecord:
    """Complete audit record for a generated SAR narrative."""
    case_id: str
    attempt_id: int | None          # None for uploaded / manual cases
    pattern_type: str
    model_used: str
    generated_at: str = ""
    generation_time_seconds: float = 0.0
    retrieval_metadata: RetrievalMetadata | None = None
    narrative_sentences: list[SentenceProvenance] = field(default_factory=list)
    transaction_summary: dict = field(default_factory=dict)
    case_source: str = "sample"     # sample | upload | manual
    detection: dict = field(default_factory=dict)       # typology.Detection
    red_flags: list[dict] = field(default_factory=list)  # typology.RedFlag
    case_facts: dict = field(default_factory=dict)      # analyst-provided KYC/alert facts
    generation_config: dict = field(default_factory=dict)  # model, seed, prompt version…

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditRecord":
        """Reconstruct from a dict (e.g., loaded from JSON/PostgreSQL).

        Tolerant in both directions: records written before a field existed
        get its default, and unknown keys are ignored.
        """
        data = dict(data)
        if data.get("retrieval_metadata"):
            rm = dict(data["retrieval_metadata"])
            rm["chunks_returned"] = [
                _known(RetrievedChunk, c) for c in rm.get("chunks_returned", [])
            ]
            data["retrieval_metadata"] = _known(RetrievalMetadata, rm)

        sentences = []
        for s in data.get("narrative_sentences", []):
            s = dict(s)
            s["field_references"] = [
                _known(FieldReference, f) for f in s.get("field_references", [])
            ]
            s["unverified_values"] = [
                _known(FieldReference, f) for f in s.get("unverified_values", [])
            ]
            sentences.append(_known(SentenceProvenance, s))
        data["narrative_sentences"] = sentences

        return _known(cls, data)


# ── Field Reference Extraction & Fact-Checking ───────────────────────────────
#
# Every amount, date and account identifier in a sentence is looked up in a
# FactIndex built once per record from the case data (all transactions, the
# statistics derived from them, the analyst's case facts and the rule-based
# red-flag evidence). Matches become field references; anything that can't be
# found becomes an *unverified value* — the hallucination guard.

# Transaction field patterns kept for backwards compatibility with older callers.
AMOUNT_PATTERN = re.compile(r"\$[\d,]+\.?\d*")
DATE_PATTERN = re.compile(r"\d{4}/\d{1,2}/\d{1,2}")
ACCOUNT_PATTERN = re.compile(r"\b[A-F0-9]{8,}\b")  # hex-like account IDs
PERCENTAGE_PATTERN = re.compile(r"\d+\.?\d*%")
COUNT_PATTERN = re.compile(r"\b(\d+)\s+(transaction|transfer|account|bank|institution|countr|currenc)", re.IGNORECASE)

# Currency names/codes/symbols → ISO-style code. "SAR" is deliberately absent:
# in a SAR narrative it means Suspicious Activity Report, not Saudi riyal.
_CCY_ALIASES = {
    "$": "USD", "usd": "USD", "us dollar": "USD", "us dollars": "USD", "dollar": "USD",
    "dollars": "USD", "u.s. dollars": "USD",
    "€": "EUR", "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "£": "GBP", "gbp": "GBP", "uk pound": "GBP", "uk pounds": "GBP", "pound": "GBP", "pounds": "GBP",
    "₹": "INR", "inr": "INR", "rupee": "INR", "rupees": "INR",
    "¥": "JPY", "jpy": "JPY", "yen": "JPY",
    "cny": "CNY", "yuan": "CNY", "rmb": "CNY",
    "chf": "CHF", "swiss franc": "CHF", "swiss francs": "CHF",
    "cad": "CAD", "canadian dollar": "CAD", "canadian dollars": "CAD",
    "aud": "AUD", "australian dollar": "AUD", "australian dollars": "AUD",
    "mxn": "MXN", "mexican peso": "MXN", "mexican pesos": "MXN",
    "brl": "BRL", "brazil real": "BRL", "brazilian real": "BRL", "brazilian reais": "BRL",
    "rub": "RUB", "ruble": "RUB", "rubles": "RUB",
    "saudi riyal": "SAR$", "saudi riyals": "SAR$",
    "ils": "ILS", "shekel": "ILS", "shekels": "ILS",
    "btc": "BTC", "bitcoin": "BTC", "bitcoins": "BTC",
    "aed": "AED", "dirham": "AED", "dirhams": "AED",
}
_CCY_WORDS = sorted((k for k in _CCY_ALIASES if k[0].isalpha()), key=len, reverse=True)
_CCY_WORD_RE = "|".join(re.escape(w) for w in _CCY_WORDS)
_NUM_RE = r"\d[\d,]*(?:\.\d+)?"
_PREFIXED_AMOUNT = re.compile(
    rf"(?P<cur>[$€£₹¥]|\b(?:USD|EUR|GBP|INR|JPY|CNY|CHF|CAD|AUD|MXN|BRL|RUB|ILS|BTC|AED)\s?)"
    rf"\s?(?P<num>{_NUM_RE})")
_SUFFIXED_AMOUNT = re.compile(rf"(?P<num>{_NUM_RE})\s?(?P<cur>{_CCY_WORD_RE})\b", re.IGNORECASE)
# Bare amounts: thousands separators or exactly two decimals ("36,052.53", "485.30").
_BARE_AMOUNT = re.compile(r"(?<![\w/#.$€£₹¥,-])(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{2})"
                          r"(?!\d)(?![\d,]*(?:%|×|x\b|\s?times|/|:))")
# Legal citations are not amounts: "31 CFR 1020.320", "12 CFR 21.11", "§ 5318".
_CITATION_BEFORE = re.compile(r"(?:\bCFR|U\.S\.C\.|§|\bSection|\bPart|\bRule)\s*$", re.IGNORECASE)
_SCALE_WORDS = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "mn": 1e6,
                "billion": 1e9, "bn": 1e9}

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
_MONTHS.update({k[:3]: v for k, v in list(_MONTHS.items())})
_MONTHS["sept"] = 9
_MON_RE = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.?"
_DATE_YMD = re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b")
_DATE_MDY = re.compile(rf"\b({_MON_RE})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*[–-]\s*(\d{{1,2}}))?(?:,?\s+(\d{{4}}))?\b",
                       re.IGNORECASE)
_DATE_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MON_RE})(?:,?\s+(\d{{4}}))?\b", re.IGNORECASE)
_DATE_NUMERIC = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
# Uppercase identifiers containing both a letter and a digit: 8049DD1C0, NG-4471, TM-2024-06-0193
_IDENTIFIER = re.compile(r"\b(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9][A-Z0-9-]{3,}[A-Z0-9]\b")

# Regulatory figures a narrative may legitimately quote without them being case data.
REGULATORY_AMOUNTS = {
    10000.0: "Currency Transaction Report threshold",
    5000.0: "SAR filing threshold (suspect identified)",
    25000.0: "SAR filing threshold (no suspect identified)",
    2000.0: "MSB SAR filing threshold",
    3000.0: "Funds-transfer recordkeeping threshold",
}
APPROXIMATE_TOLERANCE = 0.005   # "about $68,000" for $68,150.00 is within 0.5%
# Currencies that are themselves written with "$" ("$4,352.31 AUD" is not a slip).
DOLLAR_CURRENCIES = {"AUD", "CAD", "MXN", "NZD", "SGD", "HKD"}


def _ccy_code(text: str | None) -> str | None:
    if not text:
        return None
    return _CCY_ALIASES.get(str(text).strip().lower(), str(text).strip().upper())


def _to_float(num: str) -> float | None:
    try:
        return float(num.replace(",", ""))
    except ValueError:
        return None


def _format_money(value: float, ccy: str | None) -> str:
    if ccy in (None, "USD"):
        return f"${value:,.2f}"
    return f"{value:,.2f} {'Saudi Riyal' if ccy == 'SAR$' else ccy}"


class FactIndex:
    """Everything a narrative may cite, indexed for fast per-sentence lookup."""

    def __init__(self, txn_df: pd.DataFrame, case_facts: dict | None = None,
                 red_flags: list | None = None, detection: dict | None = None,
                 reference_text: str = ""):
        self.df = txn_df
        # Retrieved regulatory text: advisory numbers etc. quoted from it are legitimate.
        self.reference_text = reference_text
        self.case_facts = {k: str(v) for k, v in (case_facts or {}).items() if v}
        flagged = txn_df
        if "Flagged" in txn_df.columns and txn_df["Flagged"].astype(bool).any():
            flagged = txn_df[txn_df["Flagged"].astype(bool)]
        self.flagged = flagged
        self.amounts: list[tuple[float, str | None, str, str]] = []  # value, ccy, field, match
        self._index_amounts(txn_df, flagged)
        self._index_text_amounts(red_flags, detection)
        self.dates: dict = {}         # date → (field, match_type)
        self.months: set = set()
        self._index_dates(txn_df)
        self.accounts = set(txn_df["From_Account"].astype(str)) | set(txn_df["To_Account"].astype(str))
        self.accounts.discard("")
        self.accounts_upper = {a.upper(): a for a in self.accounts}
        numeric = [len(a) for a in self.accounts if a.isdigit()]
        self.numeric_id_lengths = range(min(numeric) - 1, max(numeric) + 2) if numeric else range(0)
        self.bank_ids = {str(b) for b in set(txn_df["From Bank"]) | set(txn_df["To Bank"]) if str(b)}
        # Entity name → its accounts, so "from Lumen Trade FZE" can be checked as a relation.
        self.entity_accounts: dict[str, set[str]] = {}
        for side in ("From", "To"):
            for name, acct in zip(txn_df[f"{side}_Entity_Name"].astype(str), txn_df[f"{side}_Account"]):
                if len(name) > 3 and name != "Unknown":
                    self.entity_accounts.setdefault(name, set()).add(acct)
        ts = pd.to_datetime(flagged["Timestamp"], errors="coerce").dropna()
        self.span = (ts.min(), ts.max()) if len(ts) else None
        # Candidate years for "June 3" style mentions: every year the transactions touch.
        self.years = {d.year for d, (f, _) in self.dates.items() if f == "Timestamp"}

    # ── amounts ──
    def _add(self, value, ccy, field_name, match_type):
        if value is None or pd.isna(value):
            return
        self.amounts.append((round(float(value), 2), ccy, field_name, match_type))

    def _index_amounts(self, df, flagged):
        for col, ccy_col in (("Amount Paid", "Payment Currency"),
                             ("Amount Received", "Receiving Currency")):
            if col not in df.columns:
                continue
            ccys = df[ccy_col].map(_ccy_code) if ccy_col in df.columns else pd.Series(None, index=df.index)
            for value, ccy in set(zip(df[col].round(2), ccys)):
                self._add(value, ccy, col, "exact")
            scopes = [("", flagged)] + ([(", all activity", df)] if len(df) != len(flagged) else [])
            for suffix, scope in scopes:
                if scope.empty:
                    continue
                codes = scope[ccy_col].map(_ccy_code)
                for ccy, rows in scope.groupby(codes):
                    vals = rows[col]
                    self._add(vals.sum(), ccy, f"{col} (total{suffix})", "derived")
                    self._add(vals.min(), ccy, f"{col} (min{suffix})", "derived")
                    self._add(vals.max(), ccy, f"{col} (max{suffix})", "derived")
                    self._add(vals.mean(), ccy, f"{col} (average{suffix})", "derived")
        # Per-account inflow/outflow and per-pair totals (flagged activity).
        if {"From_Account", "To_Account"} <= set(flagged.columns) and not flagged.empty:
            rcv = flagged.groupby(["To_Account", flagged["Receiving Currency"].map(_ccy_code)])["Amount Received"]
            for (acct, ccy), v in rcv.sum().items():
                self._add(v, ccy, f"Inflow to {acct} (total)", "derived")
            for (acct, ccy), v in rcv.mean().items():
                self._add(v, ccy, f"Inflow to {acct} (average)", "derived")
            paid = flagged.groupby(["From_Account", flagged["Payment Currency"].map(_ccy_code)])["Amount Paid"]
            for (acct, ccy), v in paid.sum().items():
                self._add(v, ccy, f"Outflow from {acct} (total)", "derived")
            for (acct, ccy), v in paid.mean().items():
                self._add(v, ccy, f"Outflow from {acct} (average)", "derived")
            pair = flagged.groupby(["From_Account", "To_Account",
                                    flagged["Payment Currency"].map(_ccy_code)])["Amount Paid"].sum()
            for (a, b, ccy), v in pair.items():
                self._add(v, ccy, f"{a} → {b} (total)", "derived")
        for key, value in self.case_facts.items():
            v = _to_float(value)
            if v is not None and re.fullmatch(r"[\d,]+(?:\.\d+)?", value.strip()):
                self._add(v, None, key, "case_fact")

    def _index_text_amounts(self, red_flags, detection):
        """Figures quoted in rule-based evidence (e.g. a baseline average) count as derived."""
        texts = []
        for f in red_flags or []:
            code = f.get("code") if isinstance(f, dict) else getattr(f, "code", "")
            ev = f.get("evidence") if isinstance(f, dict) else getattr(f, "evidence", "")
            texts.append((f"Red flag {code}", ev))
        for ev in (detection or {}).get("evidence", []):
            texts.append(("Typology detection", ev))
        for name, text in texts:
            for mention in _amount_mentions(text):
                self._add(mention.value, mention.ccy, name, "derived")

    def match_amount(self, value: float, ccy: str | None, tolerance: float = 0.0
                     ) -> tuple[FieldReference | None, str]:
        """(reference, closest-hint). Reference is None when the value isn't in the data.

        `tolerance` > 0 for figures stated with a scale word ("$1.2 million" ± 50,000).
        """
        if tolerance:
            for cand, cand_ccy, field_name, _ in self.amounts:
                if (not ccy or not cand_ccy or ccy == cand_ccy) and abs(cand - value) <= tolerance:
                    return FieldReference(field_name, _format_money(value, ccy or cand_ccy),
                                          "approximate",
                                          note=f"data value {_format_money(cand, cand_ccy)}"), ""
        best, best_gap = None, None
        for cand, cand_ccy, field_name, match_type in self.amounts:
            if ccy and cand_ccy and ccy != cand_ccy:
                continue
            gap = abs(cand - value)
            if gap < 0.006:
                return FieldReference(field_name, _format_money(value, ccy or cand_ccy), match_type), ""
            if best_gap is None or gap < best_gap:
                best, best_gap = (cand, cand_ccy, field_name, match_type), gap
        if value in REGULATORY_AMOUNTS:
            return FieldReference(REGULATORY_AMOUNTS[value], _format_money(value, ccy), "regulatory"), ""
        # Approximate only for rounded mentions ("about $68,000"); a figure given
        # to the cent must match exactly.
        rounded = abs(value - round(value)) < 0.005
        if best and rounded and best_gap <= max(best[0] * APPROXIMATE_TOLERANCE, 0.5):
            return FieldReference(best[2], _format_money(value, ccy or best[1]), "approximate",
                                  note=f"data value {_format_money(best[0], best[1])}"), ""
        elsewhere = next(((c, cc, f) for c, cc, f, _ in self.amounts
                          if ccy and cc and cc != ccy and abs(c - value) < 0.006), None)
        if elsewhere:
            return None, (f"wrong currency: the case data has {_format_money(elsewhere[0], elsewhere[1])} "
                          f"({elsewhere[2]})")
        hint = f"closest in the case data: {_format_money(best[0], best[1])} ({best[2]})" if best else ""
        return None, hint

    # ── dates ──
    def _index_dates(self, df):
        if "Timestamp" in df.columns:
            parsed = pd.to_datetime(df["Timestamp"], errors="coerce").dropna()
            for d in set(parsed.dt.date):
                self.dates[d] = ("Timestamp", "exact")
            self.months = {(d.year, d.month) for d in self.dates}
        from datetime import date as _date
        for key, value in self.case_facts.items():
            m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
            if m:
                d = _date(int(m[1]), int(m[2]), int(m[3]))
                self.dates.setdefault(d, (key, "case_fact"))

    def match_date(self, d) -> tuple[FieldReference | None, str]:
        if d in self.dates:
            field_name, match_type = self.dates[d]
            return FieldReference(field_name, d.isoformat(), match_type), ""
        if not self.dates:
            return None, ""
        closest = min(self.dates, key=lambda x: abs((x - d).days))
        return None, f"closest date in the case data: {closest.isoformat()}"


class Mention(NamedTuple):
    value: float
    ccy: str | None
    span: tuple[int, int]
    tolerance: float = 0.0    # > 0 when stated with a scale word ("$1.2 million")
    note: str = ""            # e.g. "$" written on a non-dollar amount


_SCALED_AMOUNT = re.compile(
    rf"(?P<cur>[$€£₹¥]|\b(?:USD|EUR|GBP|INR|JPY|CNY|CHF|CAD|AUD|MXN|BRL|RUB|ILS|BTC|AED)\s?)?"
    rf"(?P<num>\d+(?:\.\d+)?)\s?(?P<scale>thousand|million|billion|mn|bn|k|m)\b"
    rf"(?:\s?(?P<cur2>{_CCY_WORD_RE})\b)?", re.IGNORECASE)


def _amount_mentions(text: str) -> list[Mention]:
    found: list[Mention] = []
    spans: list[tuple[int, int]] = []

    def overlaps(span):
        return any(span[0] < e and s < span[1] for s, e in spans)

    for m in _SCALED_AMOUNT.finditer(text):
        cur = (m["cur"] or m["cur2"] or "").strip()
        if not cur:
            continue          # "1.2 million" with no currency may be a count
        decimals = len(m["num"].split(".")[1]) if "." in m["num"] else 0
        scale = _SCALE_WORDS[m["scale"].lower()]
        code = _ccy_code(cur)
        found.append(Mention(float(m["num"]) * scale, None if code == "SAR$" else code, m.span(),
                             tolerance=0.5 * 10 ** -decimals * scale))
        spans.append(m.span())
    for rx in (_PREFIXED_AMOUNT, _SUFFIXED_AMOUNT):
        for m in rx.finditer(text):
            if overlaps(m.span()):
                continue
            value = _to_float(m["num"])
            if value is None:
                continue
            code = _ccy_code(m["cur"].strip())
            span, note = m.span(), ""
            if rx is _PREFIXED_AMOUNT and m["cur"].strip() == "$":
                # "$58,696.90 EUR" / "$41,321.30 (Brazil Real)": the currency written after
                # the number wins. The $ contradicts it unless it is a dollar currency.
                after = re.match(rf"\s?\(?({_CCY_WORD_RE})\b\)?", text[m.end():], re.IGNORECASE)
                if after and _ccy_code(after.group(1)) not in ("USD", None):
                    code = _ccy_code(after.group(1))
                    span = (m.start(), m.end() + after.end())
                    if code not in DOLLAR_CURRENCIES:
                        note = f"written with a $ sign, but the amount is in {after.group(1)}"
            found.append(Mention(value, None if code == "SAR$" else code, span, note=note))
            spans.append(span)
    for m in _BARE_AMOUNT.finditer(text):
        if overlaps(m.span()) or _CITATION_BEFORE.search(text[:m.start()]):
            continue
        value = _to_float(m[1])
        if value is not None:
            found.append(Mention(value, None, m.span()))
            spans.append(m.span())
    return found


def _date_mentions(text: str, years: set[int]) -> list[tuple[list, str]]:
    """Calendar dates in the text as (candidate dates, raw text).

    An explicit year gives one candidate. A year-less "June 3" gives one per year the
    case data touches, so a case spanning New Year is still checked. An empty
    candidate list means the text names a date that doesn't exist ("June 31, 2024").
    """
    from datetime import date as _date
    out: list[tuple[list, str]] = []
    candidate_years = sorted(years)

    def make(y, mo, d):
        try:
            return _date(int(y), int(mo), int(d))
        except (ValueError, TypeError):
            return None

    def add(raw, ys, mo, d):
        out.append(([x for x in (make(y, mo, d) for y in ys) if x], raw))

    taken = []
    for m in _DATE_YMD.finditer(text):
        add(m.group(0), [m[1]], m[2], m[3])
        taken.append(m.span())
    for m in _DATE_NUMERIC.finditer(text):
        if not any(s <= m.start() < e for s, e in taken):
            a, b = int(m[1]), int(m[2])
            month, day = (a, b) if a <= 12 else (b, a)   # US order unless impossible
            add(m.group(0), [m[3]], month, day)
    for m in _DATE_MDY.finditer(text):
        ys = [m[4]] if m[4] else candidate_years
        if not ys:
            continue
        month = _MONTHS[m[1].lower().rstrip(".")]
        add(m.group(0), ys, month, m[2])
        if m[3]:
            add(m.group(0), ys, month, m[3])
    for m in _DATE_DMY.finditer(text):
        ys = [m[3]] if m[3] else candidate_years
        if ys:
            add(m.group(0), ys, _MONTHS[m[2].lower().rstrip(".")], m[1])
    return out


def dates_in_text(text: str, years: set[int]) -> set:
    """Every calendar date the text mentions (year-less ones resolved against `years`)."""
    return {d for dates, _ in _date_mentions(text, years) for d in dates}


_UNITS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
          "fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
         "eighty": 80, "ninety": 90}
_NUMBER_WORDS = {w: i for i, w in enumerate(_UNITS)} | _TENS | {"a dozen": 12}
_NUM_RE = (r"\d{1,4}|a dozen|(?:" + "|".join(_TENS) + r")(?:[- ](?:" + "|".join(_UNITS[1:10])
           + r"))?|" + "|".join(sorted(_UNITS, key=len, reverse=True)))


def _num_value(raw: str) -> int:
    raw = raw.lower()
    if raw.isdigit():
        return int(raw)
    if raw in _NUMBER_WORDS:
        return _NUMBER_WORDS[raw]
    tens, unit = re.split(r"[- ]", raw)
    return _TENS[tens] + _UNITS.index(unit)


_COUNT_ADJECTIVES = (
    "separate|distinct|different|individual|international|outgoing|incoming|outbound|inbound|"
    "unique|originating|sending|source|destination|beneficiary|counterparty|intermediary|mule|"
    "external|foreign|domestic|offshore|overseas|cross-border|suspicious|flagged|structured|"
    "sequential|consecutive|subsequent|related|linked|third-party|ACH|electronic|large")
_COUNT_CLAIM = re.compile(
    rf"\b({_NUM_RE})\s+(?:(?:{_COUNT_ADJECTIVES})\s+)*"
    r"(cash\s+deposits?|deposits?|wire\s+transfers?|wires?|withdrawals?|transactions?|"
    r"transfers?|payments?|senders?|depositors?|recipients?|beneficiar(?:y|ies)|"
    r"receiving\s+accounts?|accounts?|(?:financial\s+)?institutions?|banks?)\b",
    re.IGNORECASE)
# "the first three deposits", "another two wires": a subset, not the case's total.
_SUBSET_BEFORE = re.compile(r"\b(?:first|last|initial|final|another|additional|further|remaining|"
                            r"other|next|earliest|latest|largest|smallest|former|latter)\s+$",
                            re.IGNORECASE)


def _count_candidates(index: "FactIndex") -> dict[str, set[int]]:
    """Every count a sentence could legitimately state, by the noun it would use."""
    flagged, df = index.flagged, index.df
    fmt = flagged["Payment Format"].astype(str).str.lower()
    cash = flagged[fmt.str.contains("cash")]
    wire = flagged[fmt.str.contains("wire")]
    inflow = flagged.groupby("To_Account").size()
    outflow = flagged.groupby("From_Account").size()
    senders = flagged.groupby("To_Account")["From_Account"].nunique()
    recipients = flagged.groupby("From_Account")["To_Account"].nunique()
    per_format = set(flagged.groupby("Payment Format").size())
    totals = {len(flagged), len(df)}
    accounts = {len(set(flagged["From_Account"]) | set(flagged["To_Account"])),
                len(set(df["From_Account"]) | set(df["To_Account"]))}
    return {
        "cash deposit": {len(cash)} | set(cash.groupby("To_Account").size()),
        "deposit": set(inflow) | {len(cash)},
        "wire": {len(wire)} | set(wire.groupby("From_Account").size()) | set(outflow),
        "withdrawal": set(outflow),
        "transaction": totals | per_format | set(inflow) | set(outflow),
        "sender": set(senders) | {flagged["From_Account"].nunique()},
        "recipient": set(recipients) | {flagged["To_Account"].nunique()},
        "account": accounts | set(senders) | set(recipients),
        "bank": _bank_counts(flagged) | _bank_counts(df),
    }


def _bank_counts(df: pd.DataFrame) -> set[int]:
    """Total, sending-side and receiving-side institution counts (names, else IDs)."""
    out = set()
    for cols in (("From_Bank_Name", "To_Bank_Name"), ("From Bank", "To Bank")):
        if not set(cols) <= set(df.columns):
            continue
        send = set(df[cols[0]].astype(str)) - {"", "nan"}
        recv = set(df[cols[1]].astype(str)) - {"", "nan"}
        if send or recv:
            out |= {len(send | recv), len(send), len(recv)}
    return out


_COUNT_NOUN = [("financial institution", "bank"), ("institution", "bank"), ("bank", "bank"),
               ("cash deposit", "cash deposit"), ("depositor", "sender"), ("deposit", "deposit"),
               ("wire", "wire"), ("withdrawal", "withdrawal"), ("sender", "sender"),
               ("recipient", "recipient"), ("beneficiar", "recipient"),
               ("receiving account", "recipient"), ("account", "account"),
               ("transaction", "transaction"), ("transfer", "transaction"),
               ("payment", "transaction")]


def _check_counts(sentence: str, index: "FactIndex") -> list[FieldReference]:
    """Counts that match nothing in the case data ("nine cash deposits" when there were 7)."""
    if index.flagged.empty:
        return []
    candidates = None
    out = []
    for m in _COUNT_CLAIM.finditer(sentence):
        if _SUBSET_BEFORE.search(sentence[:m.start()]):
            continue
        raw, noun = m.group(1).lower(), re.sub(r"\s+", " ", m.group(2).lower())
        n = _num_value(raw)
        if n <= 1:
            continue
        key = next(k for prefix, k in _COUNT_NOUN if noun.startswith(prefix))
        candidates = candidates or _count_candidates(index)
        allowed = candidates[key]
        if n not in allowed:
            hint = ", ".join(str(x) for x in sorted(allowed)[:4])
            out.append(FieldReference("Count", m.group(0), "unverified",
                                      note=f"counts in the case data for this: {hint}"))
    return out


# Phrases that state how long the whole activity lasted. "within 48 hours" is left
# alone: it usually describes a sub-period (e.g. rapid pass-through).
_DURATION = re.compile(
    rf"\b(?:(?:spanning|spanned|spans|covering|covered|lasting|lasted)\s+(?:a\s+|an\s+)?|"
    rf"(?:total\s+)?(?:time\s?frame|period|span)\s+of\s+|"
    rf"(?:over|during|across|in)\s+(?:a|an)\s+(?=(?:{_NUM_RE})[- ](?:day|hour|week|month)[- ]"
    rf"(?:period|span|timeframe)))"
    rf"(?:(?:approximately|about|roughly|nearly|almost|some|just\s+over|just\s+under|a\s+total\s+of)\s+)?"
    rf"(?P<n>{_NUM_RE})[- ](?P<unit>day|hour|week|month)s?\b", re.IGNORECASE)


def _check_duration(sentence: str, index: "FactIndex") -> list[FieldReference]:
    """'approximately 16 days' for activity that lasted six (live year-boundary draft)."""
    if not index.span:
        return []
    first, last = index.span
    days = (last - first).total_seconds() / 86400
    calendar_days = (last.date() - first.date()).days + 1
    out = []
    for m in _DURATION.finditer(sentence):
        n, unit = _num_value(m["n"]), m["unit"].lower()
        if unit == "day":
            ok = min(abs(n - days), abs(n - calendar_days)) <= 1
            actual = f"{calendar_days} calendar days"
        elif unit == "hour":
            ok = abs(n - days * 24) <= max(1.5, 0.05 * days * 24)
            actual = f"{days * 24:.0f} hours"
        elif unit == "week":
            ok = abs(n - days / 7) <= 1
            actual = f"{days / 7:.1f} weeks"
        else:
            ok = abs(n - days / 30.44) <= 1
            actual = f"{days / 30.44:.1f} months"
        if not ok:
            out.append(FieldReference("Duration", m.group(0).strip(), "unverified",
                                      note=f"the flagged activity runs {first:%Y-%m-%d %H:%M} to "
                                           f"{last:%Y-%m-%d %H:%M} ({actual})"))
    return out


_TOKEN = re.compile(r"(?<![\w-])[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?![\w-])")


def _identifier_like(token: str, index: "FactIndex") -> bool:
    """Could this token be an account/reference number (so an unknown one is suspect)?"""
    if re.fullmatch(r"\d+-[a-z]+|\d+(?:st|nd|rd|th)", token):
        return False              # "150-degree", "95-hour", "4th"
    if _IDENTIFIER.fullmatch(token):
        return True
    digits = sum(ch.isdigit() for ch in token)
    if token.isdigit():
        return len(token) >= 6 and len(token) in index.numeric_id_lengths
    return any(ch.isalpha() for ch in token) and digits >= 3 and ("-" in token or len(token) >= 6)


def _check_identifiers(sentence: str, index: "FactIndex"
                       ) -> tuple[list[FieldReference], list[FieldReference]]:
    refs, unverified = [], []
    fact_values = {v.upper(): k for k, v in index.case_facts.items()}
    for token in dict.fromkeys(_TOKEN.findall(sentence)):
        up = token.upper()
        if up in index.accounts_upper:
            refs.append(FieldReference("Account", index.accounts_upper[up], "exact"))
        elif token in index.bank_ids and len(token) >= 3 and not token.isalpha():
            refs.append(FieldReference("Bank ID", token, "exact"))
        elif not _identifier_like(token, index):
            continue
        elif index.reference_text and token in index.reference_text:
            refs.append(FieldReference("Regulatory reference", token, "regulatory"))
        elif up in fact_values:
            refs.append(FieldReference(fact_values[up], token, "case_fact"))
        else:
            partial = next((a for u, a in sorted(index.accounts_upper.items())
                            if len(up) >= 4 and up in u), None)
            note = (f"partial account number — did you mean {partial}?" if partial
                    else "no account or reference with this ID in the case")
            unverified.append(FieldReference("Identifier", token, "unverified", note=note))
    return refs, unverified


def _word_in(needle: str, haystack: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None


# ── Relations: do the account, amount, direction and method belong together? ──

# Verbs only — "wires"/"transfers" are left out because they are usually nouns.
_OUT_VERB = re.compile(r"\b(?:send|sent|sends|wired|transferred|remitted|paid|pays|disbursed|"
                       r"forwarded|routed|initiated|executed|moved)\b", re.IGNORECASE)
_IN_VERB = re.compile(r"\b(?:receive|received|receives|collected|credited|accepted|obtained)\b",
                      re.IGNORECASE)
_METHODS = {"cash": r"\bcash\b", "wire": r"\bwires?\b|\bwire transfers?\b|\bwired\b",
            "ach": r"\bACH\b", "check": r"\bche(?:ck|que)s?\b", "bitcoin": r"\bbitcoin|crypto"}
_NEGATION = re.compile(r"\b(?:did|does|do|was|were|has|have|had) not\b|\bnever\b|n't\b|"
                       r"\bno (?:cash|deposits?|transfers?|transactions?|wires?|payments?|funds|activity)\b|"
                       r"\bwithout any\b", re.IGNORECASE)


def _account_mentions(sentence: str, index: "FactIndex") -> list[tuple[int, set[str]]]:
    """(position, accounts) for each account ID or known entity name in the sentence."""
    found = []
    for m in _TOKEN.finditer(sentence):
        acct = index.accounts_upper.get(m.group(0).upper())
        if acct:
            found.append((m.start(), {acct}))
    lower = sentence.lower()
    for name, accts in index.entity_accounts.items():
        m = re.search(rf"(?<!\w){re.escape(name.lower())}(?!\w)", lower)
        if m:
            found.append((m.start(), set(accts)))
    return sorted(found, key=lambda x: x[0])


def _roles(sentence: str, index: "FactIndex") -> tuple[set[str], set[str], str | None]:
    """(from-accounts, to-accounts, method) the sentence asserts, from prepositions
    ("from X", "to Y and Z") and the account named before an in/out verb."""
    tagged = []           # (position, accounts, role) with role "from" | "to" | None
    last = None
    for pos, accts in _account_mentions(sentence, index):
        before = sentence[max(0, pos - 30):pos].lower()
        prep = re.search(r"\b(from|to|into|and|or)\s+(?:(?:the|an?|account|accounts|holder|"
                         r"of|its|their)\s+)*$|(,)\s*$", before)
        word = prep and (prep.group(1) or prep.group(2))
        role = ("from" if word == "from" else "to" if word in ("to", "into")
                else last if word in ("and", "or", ",") else None)
        tagged.append((pos, accts, role))
        last = role
    senders = set().union(*[a for _, a, r in tagged if r == "from"])
    receivers = set().union(*[a for _, a, r in tagged if r == "to"])
    verbs = [v for v in (_OUT_VERB.search(sentence), _IN_VERB.search(sentence)) if v]
    if verbs:
        verb = min(verbs, key=lambda v: v.start())
        actor = [a for pos, a, r in tagged if pos < verb.start() and r is None]
        if actor:
            (senders if _OUT_VERB.fullmatch(verb.group(0)) else receivers).update(actor[-1])
    method = next((k for k, rx in _METHODS.items() if re.search(rx, sentence, re.IGNORECASE)), None)
    return senders, receivers, method


def _relation_rows(index: "FactIndex", senders, receivers, method) -> pd.DataFrame:
    rows = index.df
    if senders:
        rows = rows[rows["From_Account"].isin(senders)]
    if receivers:
        rows = rows[rows["To_Account"].isin(receivers)]
    if method:
        rows = rows[rows["Payment Format"].astype(str).str.contains(
            {"cash": "cash", "wire": "wire", "ach": "ach", "check": "che", "bitcoin": "bitcoin"}[method],
            case=False)]
    return rows


def _relation_values(rows: pd.DataFrame) -> list[tuple[float, str | None]]:
    """Every figure a sentence about these rows could state: each transfer, and the
    total / average / min / max, per currency and per flagged-or-all scope."""
    vals = []
    scopes = [rows]
    if "Flagged" in rows.columns and rows["Flagged"].astype(bool).any():
        scopes.append(rows[rows["Flagged"].astype(bool)])
    for scope in scopes:
        for col, ccy_col in (("Amount Paid", "Payment Currency"), ("Amount Received", "Receiving Currency")):
            for ccy, g in scope.groupby(scope[ccy_col].map(_ccy_code)):
                vals += [(v, ccy) for v in g[col]]
                vals += [(g[col].sum(), ccy), (g[col].mean(), ccy), (g[col].min(), ccy),
                         (g[col].max(), ccy)]
                for _, pair in g.groupby(["From_Account", "To_Account"]):
                    vals.append((pair[col].sum(), ccy))
    return vals


def _describe(index: "FactIndex", value: float) -> str:
    rows = index.df[(index.df["Amount Paid"] - value).abs() < 0.006]
    if rows.empty:
        return ""
    r = rows.iloc[0]
    return (f"{_format_money(value, _ccy_code(r['Payment Currency']))} was a {r['Payment Format']} "
            f"transfer from {r['From_Account']} to {r['To_Account']} on {str(r['Timestamp'])[:10]}")


# Where one claim ends and the next begins inside a sentence: "… aggregated into
# NG-4471, followed by the disbursement of $67,500.00 via two wires …".
_CLAUSE_BREAK = re.compile(r";|,\s*(?:and\s+)?(?:followed by|then|which|before|after|while|whereas|"
                           r"subsequently)\b|\b(?:followed by|and then|and subsequently)\b",
                           re.IGNORECASE)


def _clause_of(sentence: str, span: tuple[int, int]) -> str:
    start, end = 0, len(sentence)
    for m in _CLAUSE_BREAK.finditer(sentence):
        if m.end() <= span[0]:
            start = m.end()
        elif m.start() >= span[1]:
            end = m.start()
            break
    return sentence[start:end]


def _check_relations(sentence: str, mentions: list[Mention], index: "FactIndex"
                     ) -> list[FieldReference]:
    """A verified amount stated for the wrong account, direction or payment method.

    Roles and payment method are read from the amount's own clause only."""
    if len(mentions) != 1:
        return []     # several figures: can't tell which belongs to which account
    senders, receivers, method = _roles(_clause_of(sentence, mentions[0].span), index)
    if not senders and not receivers:
        return []
    mention = mentions[0]
    rows = _relation_rows(index, senders, receivers, method)
    for v, ccy in _relation_values(rows):
        if mention.ccy and ccy and mention.ccy != ccy:
            continue
        gap = abs(v - mention.value)
        rounded = abs(mention.value - round(mention.value)) < 0.005
        if (gap < 0.006 or (mention.tolerance and gap <= mention.tolerance)
                or (rounded and gap <= max(v * APPROXIMATE_TOLERANCE, 0.5))):
            return []
    parts = []
    if senders:
        parts.append("from " + "/".join(sorted(senders)))
    if receivers:
        parts.append("to " + "/".join(sorted(receivers)))
    if method:
        parts.append(f"by {method}")
    where = _describe(index, mention.value)
    return [FieldReference(
        "Relationship", f"{_format_money(mention.value, mention.ccy)} {' '.join(parts)}", "unverified",
        note=(f"no such transfer in the case data; {where}" if where
              else "the amount exists, but not for these accounts / this payment method"))]


_RELATIVE_TIME = re.compile(r"\b(?:before|after|prior to|until|since|previously|earlier)\b",
                            re.IGNORECASE)
_MONTH_YEAR = re.compile(rf"\b({_MON_RE})\s+(\d{{4}})\b", re.IGNORECASE)


def _check_negation(sentence: str, index: "FactIndex") -> list[FieldReference]:
    """'NG-4471 did not receive any cash deposits in June 2024' when the data shows seven.

    Only absolute claims are checked; "before May" style qualifiers are left to the
    reviewer (the sentence is marked needs-review instead)."""
    if not _NEGATION.search(sentence) or _RELATIVE_TIME.search(sentence):
        return []
    senders, receivers, method = _roles(sentence, index)
    if not senders and not receivers:
        return []
    rows = _relation_rows(index, senders, receivers, method)
    months = {(int(y), _MONTHS[m.lower().rstrip(".")]) for m, y in _MONTH_YEAR.findall(sentence)}
    if months and not rows.empty:
        ts = pd.to_datetime(rows["Timestamp"], errors="coerce")
        rows = rows[[(t.year, t.month) in months for t in ts]]
    if rows.empty:
        return []
    who = "/".join(sorted(receivers or senders))
    kind = f"{method} " if method else ""
    return [FieldReference(
        "Claim", sentence[:80], "unverified",
        note=f"the case data has {len(rows)} {kind}transfer(s) "
             f"{'into' if receivers else 'from'} {who}")]


def needs_review(sentence: str, refs: list[FieldReference]) -> str:
    """Why a sentence can't be trusted on its references alone ('' if it can)."""
    if refs and _NEGATION.search(sentence):
        return "States that something did not happen — check it against the case data"
    return ""


def check_sentence_facts(
    sentence: str,
    txn_df: pd.DataFrame,
    case_facts: dict | None = None,
    index: FactIndex | None = None,
) -> tuple[list[FieldReference], list[FieldReference]]:
    """(references found in the case data, unverified values) for one sentence."""
    index = index or FactIndex(txn_df, case_facts)
    df = index.df
    refs: list[FieldReference] = []
    unverified: list[FieldReference] = []
    lower = sentence.lower()

    # 1. Amounts
    mentions = _amount_mentions(sentence)
    data_mentions = []        # figures that come from the transactions themselves
    for mention in mentions:
        ref, hint = index.match_amount(mention.value, mention.ccy, mention.tolerance)
        if ref and ref.match_type in ("exact", "derived", "approximate") and not ref.field_name.startswith(
                ("Red flag", "Typology")):
            data_mentions.append(mention)
        if ref and not mention.note:
            refs.append(ref)
        elif ref:
            unverified.append(FieldReference("Amount", ref.field_value, "unverified",
                                             note=f"{mention.note} — fix the currency before filing"))
        else:
            unverified.append(FieldReference("Amount", _format_money(mention.value, mention.ccy),
                                             "unverified", note=hint))

    # 2. Dates
    for dates, raw in _date_mentions(sentence, index.years):
        if not dates:
            unverified.append(FieldReference("Date", raw, "unverified",
                                             note="not a valid calendar date"))
            continue
        matched = [d for d in dates if d in index.dates]
        if matched:
            refs.append(index.match_date(matched[0])[0])
        else:
            unverified.append(FieldReference("Date", dates[0].isoformat(), "unverified",
                                             note=index.match_date(dates[0])[1]))

    # 3. Account numbers and other identifiers (any shape: NG-4471, 5500123456, ab-12345)
    id_refs, id_unverified = _check_identifiers(sentence, index)
    refs += id_refs
    unverified += id_unverified

    # 4. Entity and bank names from the transactions (whole words only)
    for cols, min_len in ((("From_Entity_Name", "To_Entity_Name"), 3),
                          (("From_Bank_Name", "To_Bank_Name"), 4)):
        seen = set()
        for col in cols:
            if col not in df.columns:
                continue
            for name in df[col].dropna().unique():
                name = str(name)
                if (name and name != "Unknown" and name not in seen and len(name) > min_len
                        and _word_in(name.lower(), lower)):
                    seen.add(name)
                    refs.append(FieldReference(col, name, "entity_name"))

    # 5. Analyst-provided case facts quoted as text (name, occupation, address…)
    for key, value in index.case_facts.items():
        if len(value) >= 4 and not re.fullmatch(r"[\d,.\-]+", value) and _word_in(value.lower(), lower):
            refs.append(FieldReference(key, value, "case_fact"))

    # 6. Counts ("10 transactions", "11 accounts") — matched, never flagged:
    #    subset counts ("7 cash deposits") are legitimate.
    scopes = [index.flagged] + ([df] if len(df) != len(index.flagged) else [])
    for count_val, count_type in COUNT_PATTERN.findall(sentence):
        n, kind = int(count_val), count_type.lower()
        for scope in scopes:
            if "transaction" in kind or "transfer" in kind:
                actual, name = len(scope), "Transaction Count"
            elif "account" in kind:
                actual = len(set(scope["From_Account"]) | set(scope["To_Account"]))
                name = "Unique Account Count"
            elif "bank" in kind or "institution" in kind:
                banks = set(scope["From Bank"]) | set(scope["To Bank"])
                names = set(scope.get("From_Bank_Name", pd.Series(dtype=str))) | set(
                    scope.get("To_Bank_Name", pd.Series(dtype=str)))
                banks.discard("")
                names.discard("")
                actual, name = (len(banks) if banks else len(names)), "Unique Bank Count"
                if n == len(names):
                    actual = n
            else:
                continue
            if n == actual:
                refs.append(FieldReference(name, str(n), "derived"))
                break

    unverified += _check_counts(sentence, index)
    unverified += _check_duration(sentence, index)
    # 7. Relationships between verified values, and negated facts
    if not any(u.field_name == "Amount" for u in unverified) and len(data_mentions) == len(mentions):
        unverified += _check_relations(sentence, data_mentions, index)
    unverified += _check_negation(sentence, index)
    return refs, unverified


def extract_field_references(
    sentence: str,
    txn_df: pd.DataFrame,
    case_facts: dict | None = None,
    index: FactIndex | None = None,
) -> list[FieldReference]:
    """Identify which case-data fields a sentence references (see check_sentence_facts)."""
    return check_sentence_facts(sentence, txn_df, case_facts, index)[0]


# ── Rule attribution ─────────────────────────────────────────────────────────

RULE_KEYWORDS = {
    "STRUCTURING": r"structur|just (?:below|under)|below the \$?10,000|reporting threshold|\bCTR\b",
    "RAPID_PASS_THROUGH": r"rapid|quickly|promptly|pass[- ]through|same day|immediately|"
                          r"within (?:\d+|a|one|two|three|four|five|hours|days)\b",
    "CROSS_CURRENCY": r"currenc|convert|conversion|exchang",
    "CROSS_BORDER": r"cross-border|international|abroad|overseas|foreign|offshore",
    "HIGH_RISK_JURISDICTION": r"high-risk jurisdiction|\bFATF\b|grey list|gray list|call for action",
    "ROUND_AMOUNTS": r"round(?:-dollar|-number| number| amounts?| sums?)",
    "MULTI_INSTITUTION": r"(?:multiple|several|many|\d+|numerous) (?:different |distinct |separate )?"
                         r"(?:financial )?(?:institutions|banks)",
    "HIGH_VELOCITY": r"velocity|quick succession|within (?:a|one|the same) (?:single )?(?:day|24-hour)",
    "CRYPTO": r"bitcoin|crypto|virtual currenc",
    "PROFILE_MISMATCH": r"expected (?:monthly )?(?:activity|volume)|inconsistent with|"
                        r"customer profile|stated business|nature of (?:its|the) business|"
                        r"profile",
    "BASELINE_DEVIATION": r"historical|baseline|prior month|normal activity|previous(?:ly)? (?:month|activity)|"
                          r"typical(?:ly)? (?:activity|volume)",
    "NEW_ACCOUNT": r"newly opened|recently opened|new account",
}


def attribute_rules_to_sentences(sentences: list[SentenceProvenance],
                                 red_flags: list | None) -> None:
    """Link sentences to the rule-based red flags whose evidence they restate."""
    codes = []
    for f in red_flags or []:
        codes.append(f.get("code") if isinstance(f, dict) else getattr(f, "code", ""))
    patterns = {c: re.compile(RULE_KEYWORDS[c], re.IGNORECASE) for c in codes if c in RULE_KEYWORDS}
    for sent in sentences:
        for code, rx in patterns.items():
            if rx.search(sent.sentence_text) and code not in sent.rule_attributions:
                sent.rule_attributions.append(code)


def grounding_status(sent) -> str:
    """unverified > grounded (data + analysis) > partial (either) > ungrounded.

    Data = transaction fields or analyst case facts. Analysis = retrieved
    regulatory context or rule-based red-flag evidence. A sentence that needs
    review (e.g. a negation) is never "grounded".

    These measure SOURCING, not truth: a sentence can cite real values and still be
    wrong. The UI labels them Sourced / Partly sourced / Unsourced / Unverified.
    """
    if getattr(sent, "unverified_values", None):
        return "unverified"
    has_data = bool(sent.field_references)
    has_analysis = bool(sent.chunk_attributions) or bool(getattr(sent, "rule_attributions", None))
    if has_data and has_analysis and not getattr(sent, "needs_review", ""):
        return "grounded"
    if has_data or has_analysis:
        return "partial"
    return "ungrounded"


# ── Sentence Parsing ─────────────────────────────────────────────────────────

SECTION_HEADER_PATTERN = re.compile(r"^###?\s*(.+)$", re.MULTILINE)

# Markdown tables: "| a | b |" rows, with a "| --- | :---: |" separator under
# the header row. Header and separator rows are layout, not claims.
TABLE_SEPARATOR_PATTERN = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


def is_table_row(line: str) -> bool:
    return line.startswith("|") and line.count("|") >= 2


def table_cells(row: str) -> list[str]:
    """Cells of a Markdown table row (outer pipes optional)."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


_SECTION_WORDS = [("who", "Who"), ("what", "What"), ("when", "When"), ("where", "Where"),
                  ("why", "Why Suspicious"), ("how", "How"), ("supporting", "Supporting Pattern"),
                  ("quantitative", "Quantitative Summary")]
_SECTION_NAMES = {name for _, name in _SECTION_WORDS}


def _section_name(heading: str) -> str:
    lower = heading.lower()
    first = re.match(r"\W*(\w+)", lower)
    for word, name in _SECTION_WORDS:
        if first and first.group(1) == word:
            return name
    for word, name in _SECTION_WORDS:
        if re.search(rf"\b{word}\b", lower):
            return name
    return heading


# Abbreviations whose full stop doesn't end a sentence ("U.S. accounts", "Mr. Kumar").
_DOT = "\u2024"
_ABBREVIATIONS = re.compile(
    r"\b(?:U\.S|U\.K|U\.A\.E|e\.g|i\.e|Mr|Mrs|Ms|Dr|Inc|Ltd|Co|Corp|St|vs|approx)\.(?=\s)"
    r"|\bNo\.(?=\s*\d)|\b[ap]\.m\.(?=\s+[a-z])")


def _protect_abbreviations(line: str) -> str:
    return _ABBREVIATIONS.sub(lambda m: m.group(0).replace(".", _DOT), line)


def parse_narrative_into_sentences(narrative_text: str) -> list[SentenceProvenance]:
    """
    Parse a generated narrative into individual sentences with section labels.

    Returns a list of SentenceProvenance objects (without field references filled
    in — those are added separately).
    """
    sentences = []
    current_section = "Preamble"
    sent_idx = 0
    lines = [ln.strip() for ln in narrative_text.split("\n")]

    for pos, line in enumerate(lines):
        if not line:
            continue

        # Tables: each data row is one auditable claim (a transaction, a total…);
        # the header row and the separator row are skipped.
        if is_table_row(line):
            if TABLE_SEPARATOR_PATTERN.match(line):
                continue
            following = next((ln for ln in lines[pos + 1:] if ln), "")
            if TABLE_SEPARATOR_PATTERN.match(following):
                continue  # header row
            if any(table_cells(line)):
                sentences.append(SentenceProvenance(
                    sentence_index=sent_idx, sentence_text=line, section=current_section,
                ))
                sent_idx += 1
            continue

        # A bold line that names a section ("**Who (Subject Identification)**") is a
        # heading too — reviewers sometimes restyle headings in the editor.
        bold = re.fullmatch(r"\*\*([^*]+?)\*\*:?", line)
        if bold and _section_name(bold.group(1)) in _SECTION_NAMES:
            current_section = _section_name(bold.group(1))
            continue

        # Check for section header
        header_match = SECTION_HEADER_PATTERN.match(line)
        if header_match:
            current_section = re.sub(r"^\d+[.)]\s*", "", header_match.group(1).strip())
            # Normalize section names (whole words: "whole period" is not "Who")
            current_section = _section_name(current_section)
            continue

        # Skip the title, rules, and the bold metadata block above the first
        # section (**Pattern:**, **Attempt #:**, **Model:**). Bold-label lines
        # inside sections ("**Account Numbers Involved:** …") are claims and
        # are audited like any other text.
        if line.startswith("# ") or line.startswith("---"):
            continue
        if line.startswith("**") and current_section == "Preamble":
            continue

        # Split line into sentences (rough split on period + space or end)
        raw_sentences = re.split(r"(?<=[.!?])\s+", _protect_abbreviations(line))
        for raw_sent in raw_sentences:
            raw_sent = raw_sent.replace(_DOT, ".").strip()
            if len(raw_sent) < 10:  # skip very short fragments
                continue
            sentences.append(SentenceProvenance(
                sentence_index=sent_idx,
                sentence_text=raw_sent,
                section=current_section,
            ))
            sent_idx += 1

    return sentences


# ── Chunk Attribution ────────────────────────────────────────────────────────

def attribute_chunks_to_sentences(
    sentences: list[SentenceProvenance],
    chunks: list[RetrievedChunk],
    chunk_texts: dict[str, str],  # chunk_id → full text
) -> None:
    """
    For each sentence, identify which retrieved chunks are most relevant
    by checking for keyword overlap between the sentence and chunk text.

    Mutates sentences in place, adding chunk_ids to chunk_attributions.
    """
    for sent in sentences:
        sent_words = set(sent.sentence_text.lower().split())
        # Remove common stop words for better matching
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
            "to", "for", "of", "and", "or", "with", "by", "from", "this",
            "that", "these", "those", "it", "its", "has", "had", "have",
            "been", "be", "as", "not", "no", "but", "if", "which", "each",
        }
        sent_keywords = sent_words - stop_words
        if len(sent_keywords) < 2:
            continue

        for chunk in chunks:
            chunk_text = chunk_texts.get(chunk.chunk_id, chunk.text_preview)
            chunk_words = set(chunk_text.lower().split()) - stop_words

            # Calculate Jaccard-like overlap
            overlap = len(sent_keywords & chunk_words)
            overlap_ratio = overlap / max(len(sent_keywords), 1)

            # Threshold: at least 15% keyword overlap to attribute
            if overlap_ratio >= 0.15 and overlap >= 3:
                if chunk.chunk_id not in sent.chunk_attributions:
                    sent.chunk_attributions.append(chunk.chunk_id)

        # Also check for typology-specific keywords
        typology_keywords = {
            "fan-out": ["fan-out", "dispersal", "structuring", "smurfing"],
            "fan-in": ["fan-in", "aggregation", "convergence", "funnel"],
            "cycle": ["cycle", "circular", "u-turn", "round-trip", "layering"],
            "gather-scatter": ["gather-scatter", "funnel", "consolidation", "redistribution"],
            "scatter-gather": ["scatter-gather", "intermediary", "mule", "smurfing"],
            "stack": ["stack", "parallel", "chain", "sequential", "hops"],
            "bipartite": ["bipartite", "related-party", "disjoint", "coordinated"],
            "random": ["random", "unstructured", "no clear", "no typology"],
        }
        sent_lower = sent.sentence_text.lower()
        for pattern, keywords in typology_keywords.items():
            if any(kw in sent_lower for kw in keywords):
                sent.typology_match = pattern.upper()
                break


# ── Build Complete Audit Record ──────────────────────────────────────────────

def build_audit_record(
    case_id: str,
    attempt_id: int | None,
    pattern_type: str,
    model_used: str,
    generation_time: float,
    narrative_text: str,
    retrieval_metadata: RetrievalMetadata,
    chunk_texts: dict[str, str],
    txn_df: pd.DataFrame,
    *,
    case_facts: dict | None = None,
    detection: dict | None = None,
    red_flags: list | None = None,
    generation_config: dict | None = None,
    case_source: str = "sample",
) -> AuditRecord:
    """
    Build a complete audit record for a generated narrative.

    This is the main entry point — takes all the raw data from generation
    and produces a structured provenance record. Deterministic: the same text
    and case data always give the same record (so edits can be re-audited).
    """
    red_flags = [f if isinstance(f, dict) else f.to_dict() for f in (red_flags or [])]
    sentences = parse_narrative_into_sentences(narrative_text)

    # Facts: data/case-fact references and unverified values per sentence
    reference_text = " ".join(chunk_texts.values()) if chunk_texts else ""
    if retrieval_metadata:
        reference_text += " " + " ".join(
            f"{c.text_preview} {c.source_file}" for c in retrieval_metadata.chunks_returned)
    index = FactIndex(txn_df, case_facts, red_flags, detection, reference_text)
    for sent in sentences:
        sent.field_references, sent.unverified_values = check_sentence_facts(
            sent.sentence_text, txn_df, case_facts, index)
        if not sent.unverified_values:
            sent.needs_review = needs_review(sent.sentence_text, sent.field_references)

    # Analysis: retrieved regulatory context and rule-based red flags
    if retrieval_metadata and retrieval_metadata.chunks_returned:
        attribute_chunks_to_sentences(
            sentences,
            retrieval_metadata.chunks_returned,
            chunk_texts,
        )
    attribute_rules_to_sentences(sentences, red_flags)

    flagged = index.flagged
    txn_summary = {
        "transaction_count": len(flagged),
        "total_amount_paid": float(flagged["Amount Paid"].sum()),
        "total_amount_received": float(flagged["Amount Received"].sum()),
        "unique_accounts": len(
            set(flagged["From_Account"].unique()) | set(flagged["To_Account"].unique())
        ),
        "unique_banks": len(
            set(flagged["From Bank"].unique()) | set(flagged["To Bank"].unique())
        ),
        "currencies": sorted(
            set(flagged["Receiving Currency"].unique())
            | set(flagged["Payment Currency"].unique())
        ),
        "date_range": {
            "start": str(flagged["Timestamp"].min()),
            "end": str(flagged["Timestamp"].max()),
        },
        "payment_formats": sorted(flagged["Payment Format"].unique().tolist()),
        "context_transactions": int(len(txn_df) - len(flagged)),
    }

    for sent in sentences:
        status = grounding_status(sent)
        if status == "unverified":
            sent.confidence_note = ("Contains figures, identifiers or relationships not found "
                                    "in the case data — verify before filing")
        elif sent.needs_review:
            sent.confidence_note = sent.needs_review
        elif sent.field_references and (sent.chunk_attributions or sent.rule_attributions):
            sent.confidence_note = "Grounded in both case data and analysis (context or rules)"
        elif sent.field_references:
            sent.confidence_note = "Grounded in case data only"
        elif sent.chunk_attributions:
            sent.confidence_note = "Derived from retrieved typology context"
        elif sent.rule_attributions:
            sent.confidence_note = "Restates rule-based red-flag evidence"
        else:
            sent.confidence_note = "Model-generated claim — no direct source attribution"

    return AuditRecord(
        case_id=case_id,
        attempt_id=attempt_id,
        pattern_type=pattern_type,
        model_used=model_used,
        generation_time_seconds=generation_time,
        retrieval_metadata=retrieval_metadata,
        narrative_sentences=sentences,
        transaction_summary=txn_summary,
        case_source=case_source,
        detection=detection or {},
        red_flags=red_flags,
        case_facts=dict(case_facts or {}),
        generation_config=dict(generation_config or {}),
    )


def rebuild_audit_record(baseline: AuditRecord, new_text: str, retrieval_metadata,
                         chunk_texts: dict[str, str], txn_df: pd.DataFrame) -> AuditRecord:
    """Re-audit reviewer-edited text with the same case data and analysis as `baseline`."""
    return build_audit_record(
        case_id=baseline.case_id,
        attempt_id=baseline.attempt_id,
        pattern_type=baseline.pattern_type,
        model_used=baseline.model_used if baseline.model_used.endswith("human edit")
        else f"{baseline.model_used} + human edit",
        generation_time=baseline.generation_time_seconds,
        narrative_text=new_text,
        retrieval_metadata=retrieval_metadata,
        chunk_texts=chunk_texts,
        txn_df=txn_df,
        case_facts=baseline.case_facts,
        detection=baseline.detection,
        red_flags=baseline.red_flags,
        generation_config=baseline.generation_config,
        case_source=baseline.case_source,
    )


# ── Reviewer Edit Tracking ───────────────────────────────────────────────────

# Minimum similarity for a new sentence to count as an edit of a removed one
# (rather than an unrelated addition). 0.6 tolerates reworded clauses while
# keeping genuinely new claims separate.
EDIT_SIMILARITY = 0.6


def _normalise(text: str) -> str:
    """Formatting-insensitive key: collapse whitespace and table-cell padding."""
    text = re.sub(r"\s*\|\s*", " | ", text) if is_table_row(text.strip()) else text
    return re.sub(r"\s+", " ", text).strip()


def diff_provenance(
    baseline: list[SentenceProvenance],
    current: list[SentenceProvenance],
) -> tuple[dict[int, dict], list[SentenceProvenance]]:
    """
    Compare the current (reviewer-edited) sentences against the baseline
    (as-generated / as-loaded) sentences.

    Returns (changes, removed):
      - changes: current sentence_index → {"kind": "added"} or
        {"kind": "edited", "was": <baseline text>}. Unchanged sentences are absent.
      - removed: baseline sentences no longer in the narrative, so deletions stay
        visible in the audit trail instead of silently disappearing.
    """
    remaining: dict[str, list[SentenceProvenance]] = {}
    for sent in baseline:
        remaining.setdefault(_normalise(sent.sentence_text), []).append(sent)

    unmatched: list[SentenceProvenance] = []
    for sent in current:
        key = _normalise(sent.sentence_text)
        if remaining.get(key):
            remaining[key].pop(0)
        else:
            unmatched.append(sent)
    removed = [s for group in remaining.values() for s in group]
    removed.sort(key=lambda s: s.sentence_index)

    changes: dict[int, dict] = {}
    for sent in unmatched:
        best, best_ratio = None, EDIT_SIMILARITY
        for old in removed:
            ratio = SequenceMatcher(None, old.sentence_text, sent.sentence_text).ratio()
            if ratio >= best_ratio:
                best, best_ratio = old, ratio
        if best is not None:
            removed.remove(best)
            changes[sent.sentence_index] = {"kind": "edited", "was": best.sentence_text}
        else:
            changes[sent.sentence_index] = {"kind": "added"}
    return changes, removed


# ── Provenance Report ────────────────────────────────────────────────────────

def generate_provenance_report(audit_record: AuditRecord) -> str:
    """
    Generate a human-readable provenance report from an audit record.

    This is what a regulator or reviewer would use to verify each claim.
    """
    lines = []
    lines.append(f"# Provenance Report — Case {audit_record.case_id}")
    lines.append(f"")
    if audit_record.attempt_id is not None:
        lines.append(f"**Attempt #:** {audit_record.attempt_id}")
    lines.append(f"**Source:** {audit_record.case_source}")
    lines.append(f"**Pattern:** {audit_record.pattern_type}")
    lines.append(f"**Model:** {audit_record.model_used}")
    lines.append(f"**Generated:** {audit_record.generated_at}")
    lines.append(f"**Generation Time:** {audit_record.generation_time_seconds:.1f}s")
    cfg = audit_record.generation_config
    if cfg:
        lines.append(f"**Reproducibility:** prompt `{cfg.get('prompt_version')}` · input "
                     f"`{cfg.get('input_fingerprint')}` · seed {cfg.get('seed')} · "
                     f"num_ctx {cfg.get('num_ctx')} · temperature {cfg.get('temperature')}")
    lines.append("")

    det = audit_record.detection
    if det:
        lines.append("## Rule-Based Typology Detection")
        lines.append("")
        lines.append(f"**{det.get('pattern')}** ({det.get('confidence')} confidence)")
        for ev in det.get("evidence", []):
            lines.append(f"- {ev}")
        lines.append("")
    if audit_record.red_flags:
        lines.append("## Red Flags")
        lines.append("")
        for f in audit_record.red_flags:
            lines.append(f"- **[{f.get('severity', '').upper()}] {f.get('title')}** "
                         f"(`{f.get('code')}`): {f.get('evidence')}")
        lines.append("")
    if audit_record.case_facts:
        lines.append("## Analyst-Provided Case Facts")
        lines.append("")
        for k, v in audit_record.case_facts.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")

    # Retrieval summary
    if audit_record.retrieval_metadata:
        rm = audit_record.retrieval_metadata
        lines.append("## Retrieval Summary")
        lines.append("")
        lines.append(f"- **Label Query:** {rm.label_query}")
        lines.append(f"- **Description Query:** {rm.description_query}")
        lines.append(f"- **Top-K:** {rm.top_k}")
        lines.append(f"- **Candidates (pre-dedup):** {rm.total_candidates}")
        lines.append(f"- **Chunks Used:** {len(rm.chunks_returned)}")
        lines.append("")

        lines.append("### Retrieved Chunks")
        lines.append("")
        for chunk in rm.chunks_returned:
            lines.append(
                f"- **{chunk.chunk_id}** | {chunk.source_file} p.{chunk.page_number} | "
                f"Relevance: {chunk.relevance_score:.2f} | "
                f"Query: {chunk.query_type}"
            )
            lines.append(f"  > {chunk.text_preview}...")
        lines.append("")

    # Transaction summary
    ts = audit_record.transaction_summary
    if ts:
        lines.append("## Transaction Data Summary")
        lines.append("")
        lines.append(f"- **Transactions:** {ts.get('transaction_count')}")
        lines.append(f"- **Total Paid:** ${ts.get('total_amount_paid', 0):,.2f}")
        lines.append(f"- **Total Received:** ${ts.get('total_amount_received', 0):,.2f}")
        lines.append(f"- **Accounts:** {ts.get('unique_accounts')}")
        lines.append(f"- **Banks:** {ts.get('unique_banks')}")
        lines.append(f"- **Currencies:** {', '.join(ts.get('currencies', []))}")
        lines.append(f"- **Date Range:** {ts.get('date_range', {}).get('start')} → {ts.get('date_range', {}).get('end')}")
        lines.append("")

    # Sentence-level provenance
    lines.append("## Sentence-Level Provenance")
    lines.append("")

    current_section = ""
    grounded_count = 0
    ungrounded_count = 0
    unverified_count = 0
    icons = {"grounded": "🟢", "partial": "🟡", "ungrounded": "🔴", "unverified": "⚠️"}

    for sent in audit_record.narrative_sentences:
        if sent.section != current_section:
            current_section = sent.section
            lines.append(f"### {current_section}")
            lines.append("")

        status = grounding_status(sent)
        indicator = icons[status]
        if status in ("grounded", "partial"):
            grounded_count += 1
        elif status == "unverified":
            unverified_count += 1
        else:
            ungrounded_count += 1

        lines.append(f"{indicator} **S{sent.sentence_index}:** \"{sent.sentence_text}\"")

        if sent.field_references:
            ref_strs = []
            for ref in sent.field_references:
                ref_strs.append(f"`{ref.field_name}` = {ref.field_value} ({ref.match_type})")
            lines.append(f"  - **Data:** {'; '.join(ref_strs)}")

        if sent.chunk_attributions:
            lines.append(f"  - **Context:** {', '.join(sent.chunk_attributions)}")

        if sent.rule_attributions:
            lines.append(f"  - **Rules:** {', '.join(sent.rule_attributions)}")

        if sent.unverified_values:
            lines.append("  - **Not in case data:** " + "; ".join(
                f"{u.field_value}" + (f" ({u.note})" if u.note else "")
                for u in sent.unverified_values))

        if sent.typology_match:
            lines.append(f"  - **Typology:** {sent.typology_match}")

        lines.append(f"  - **Confidence:** {sent.confidence_note}")
        lines.append("")

    # Summary stats
    total_sentences = len(audit_record.narrative_sentences)
    lines.append("---")
    lines.append("")
    lines.append("## Provenance Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total sentences | {total_sentences} |")
    lines.append(f"| Sourced (data and/or context) | {grounded_count} ({grounded_count/max(total_sentences,1)*100:.0f}%) |")
    lines.append(f"| Unsourced | {ungrounded_count} ({ungrounded_count/max(total_sentences,1)*100:.0f}%) |")
    lines.append(f"| Unverified figures (not in case data) | {unverified_count} |")

    # Count unique field references
    all_fields = set()
    for sent in audit_record.narrative_sentences:
        for ref in sent.field_references:
            all_fields.add(ref.field_name)
    lines.append(f"| Unique data fields referenced | {len(all_fields)} |")

    # Count unique chunks attributed
    all_chunks = set()
    for sent in audit_record.narrative_sentences:
        for cid in sent.chunk_attributions:
            all_chunks.add(cid)
    lines.append(f"| Unique chunks attributed | {len(all_chunks)} |")
    lines.append("")

    return "\n".join(lines)


# ── File I/O ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = PROJECT_ROOT / "audit_logs"


def save_audit_record(audit_record: AuditRecord) -> Path:
    """Save an audit record as JSON to the audit_logs/ directory."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = AUDIT_DIR / f"{audit_record.case_id}_audit.json"
    filepath.write_text(audit_record.to_json(), encoding="utf-8")
    return filepath


def load_audit_record(case_id: str) -> AuditRecord:
    """Load an audit record from JSON."""
    filepath = AUDIT_DIR / f"{case_id}_audit.json"
    data = json.loads(filepath.read_text(encoding="utf-8"))
    return AuditRecord.from_dict(data)


def save_provenance_report(audit_record: AuditRecord) -> Path:
    """Generate and save a human-readable provenance report."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_provenance_report(audit_record)
    filepath = AUDIT_DIR / f"{audit_record.case_id}_provenance.md"
    filepath.write_text(report, encoding="utf-8")
    return filepath
