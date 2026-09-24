"""
case_input.py — The case an analyst investigates, independent of where it came from.

A `CaseInput` bundles everything a SAR narrative is written from:
  * transactions in one canonical schema (the column names of the enriched
    IBM parquet, so the audit trail and prompt formatting work unchanged)
  * the subject's KYC profile — the "customer baseline" examiners look for
  * the alert that triggered the review, the investigation steps and findings
  * prior SARs on the subject (continuing-activity filings)

Sources:
  * `from_attempt()` — a laundering attempt from the IBM dataset (samples)
  * `read_table()` + `detect_format()` + `apply_mapping()` — an uploaded CSV/XLSX
    in IBM `Trans.csv` format, the enriched parquet format, a generic
    from/to export, or a single-account statement (debit/credit columns)
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime

import pandas as pd

# ── Canonical schema ─────────────────────────────────────────────────────────

CANONICAL_COLUMNS = [
    "Timestamp",
    "From Bank", "From_Account", "From_Bank_Name", "From_Entity_Name",
    "To Bank", "To_Account", "To_Bank_Name", "To_Entity_Name",
    # Paid and Received stay separate (RULES.md): they differ on cross-currency rows.
    "Amount Received", "Receiving Currency", "Amount Paid", "Payment Currency",
    "Payment Format",
    "From_Country", "To_Country",
    "Flagged",       # in scope for the SAR (alerted); unflagged rows are context
    "Txn_ID",
]
TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M"   # the IBM format, used everywhere downstream

ALERT_SOURCES = [
    "Transaction monitoring alert",
    "Employee / branch referral",
    "314(a) request",
    "Law enforcement inquiry",
    "Subpoena",
    "Other",
]

INVESTIGATION_STEPS = [
    "Reviewed KYC / customer due diligence file",
    "Reviewed account activity for the lookback period",
    "Searched for prior SARs on the subject",
    "Reviewed counterparties and beneficiaries",
    "Screened parties against sanctions / watchlists",
    "Conducted adverse media / open-source search",
    "Contacted the customer for an explanation",
    "Requested supporting documentation",
]

SUBJECT_TYPES = ["", "Individual", "Business"]
RISK_RATINGS = ["", "Low", "Medium", "High"]


# ── Case model ───────────────────────────────────────────────────────────────

@dataclass
class Subject:
    """Who the SAR is about — FFIEC Appendix L "Who" + the customer baseline."""
    name: str = ""
    subject_type: str = ""            # Individual / Business
    occupation: str = ""              # occupation or nature of business
    country: str = ""
    address: str = ""
    accounts: list[str] = field(default_factory=list)   # subject's own account IDs
    account_opened: str = ""          # ISO date the relationship began
    expected_monthly_volume: float | None = None
    expected_monthly_count: int | None = None
    risk_rating: str = ""
    notes: str = ""


@dataclass
class Alert:
    source: str = ""
    alert_id: str = ""
    detected_on: str = ""             # ISO date — starts the 30-day filing clock
    description: str = ""


@dataclass
class Investigation:
    steps: list[str] = field(default_factory=list)
    findings: str = ""
    ruled_out: str = ""               # explanations considered and why they fail


@dataclass
class PriorSAR:
    filed_on: str = ""                # ISO date
    reference: str = ""               # BSA ID / internal reference
    amount: float | None = None
    period_start: str = ""
    period_end: str = ""


def _build(cls, data: dict | None):
    """Dataclass from a dict, ignoring unknown keys (forward/backward compatible)."""
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in names})


@dataclass
class CaseInput:
    case_id: str
    transactions: pd.DataFrame
    source: str = "upload"            # sample | upload | manual
    attempt_id: int | None = None     # set for IBM dataset samples
    dataset_label: str = ""           # IBM ground-truth pattern (samples only)
    degree_info: str = ""
    subject: Subject = field(default_factory=Subject)
    alert: Alert = field(default_factory=Alert)
    investigation: Investigation = field(default_factory=Investigation)
    prior_sars: list[PriorSAR] = field(default_factory=list)
    pattern_override: str = ""        # analyst's typology choice (overrides detection)
    override_reason: str = ""         # why the analyst overrode the rule-based detection

    # ── Views ──
    def flagged(self) -> pd.DataFrame:
        """Transactions in scope for the SAR (all of them when nothing is flagged)."""
        df = self.transactions
        if "Flagged" in df.columns and df["Flagged"].any():
            return df[df["Flagged"].astype(bool)]
        return df

    def context(self) -> pd.DataFrame:
        """Unflagged activity — the baseline the suspicious activity is compared to."""
        df = self.transactions
        if "Flagged" in df.columns and df["Flagged"].any():
            return df[~df["Flagged"].astype(bool)]
        return df.iloc[0:0]

    def is_continuing(self) -> bool:
        return any(p.filed_on or p.reference for p in self.prior_sars)

    def continuing_totals(self) -> dict | None:
        """Prior-SAR total, this period's amount and the cumulative total, computed here so
        the model copies the figure instead of doing the arithmetic.

        This period = money received by the subject's own accounts from others (USD only);
        without subject accounts, or in other currencies, only the prior total is given.
        """
        prior = [p for p in self.prior_sars if p.filed_on or p.reference]
        if not prior:
            return None
        prior_total = sum(p.amount or 0 for p in prior)
        out = {"prior_total": prior_total, "current": None, "basis": "", "cumulative": None}
        accounts = set(self.subject.accounts)
        df = self.flagged()
        inflow = df[df["To_Account"].isin(accounts) & ~df["From_Account"].isin(accounts)]
        if accounts and len(inflow) and inflow["Receiving Currency"].map(is_usd).all():
            current = float(inflow["Amount Received"].sum())
            out.update(current=current, cumulative=prior_total + current,
                       basis="received by the subject's accounts in the flagged activity")
        return out

    def case_facts(self) -> dict[str, str]:
        """Analyst-provided facts, flattened for the audit trail's matcher."""
        s, a = self.subject, self.alert
        facts = {
            "Subject name": s.name,
            "Subject type": s.subject_type,
            "Occupation / business": s.occupation,
            "Subject country": s.country,
            "Subject address": s.address,
            "Account opened": s.account_opened,
            "Risk rating": s.risk_rating,
            "Alert source": a.source,
            "Alert ID": a.alert_id,
            "Alert date": a.detected_on,
        }
        if s.expected_monthly_volume:
            facts["Expected monthly volume"] = f"{s.expected_monthly_volume:,.2f}"
        if s.expected_monthly_count:
            facts["Expected monthly count"] = str(s.expected_monthly_count)
        for i, p in enumerate(self.prior_sars, 1):
            if p.reference:
                facts[f"Prior SAR {i} reference"] = p.reference
            if p.filed_on:
                facts[f"Prior SAR {i} filed"] = p.filed_on
            if p.amount:
                facts[f"Prior SAR {i} amount"] = f"{p.amount:,.2f}"
        totals = self.continuing_totals()
        if totals and totals["prior_total"]:
            facts["Prior SARs total"] = f"{totals['prior_total']:,.2f}"
        if totals and totals["cumulative"] is not None:
            facts["Current period amount"] = f"{totals['current']:,.2f}"
            facts["Cumulative amount incl. prior SARs"] = f"{totals['cumulative']:,.2f}"
        if self.override_reason:
            facts["Pattern override reason"] = self.override_reason
        return {k: str(v) for k, v in facts.items() if v not in ("", None)}

    # ── Serialisation ──
    def to_dict(self) -> dict:
        df = self.transactions.copy()
        return {
            "case_id": self.case_id,
            "source": self.source,
            "attempt_id": self.attempt_id,
            "dataset_label": self.dataset_label,
            "degree_info": self.degree_info,
            "subject": asdict(self.subject),
            "alert": asdict(self.alert),
            "investigation": asdict(self.investigation),
            "prior_sars": [asdict(p) for p in self.prior_sars],
            "pattern_override": self.pattern_override,
            "override_reason": self.override_reason,
            "transactions": json.loads(df.to_json(orient="records")),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CaseInput":
        df = pd.DataFrame(data.get("transactions") or [])
        return cls(
            case_id=data.get("case_id", ""),
            transactions=normalise_frame(df),
            source=data.get("source", "upload"),
            attempt_id=data.get("attempt_id"),
            dataset_label=data.get("dataset_label", ""),
            degree_info=data.get("degree_info", ""),
            subject=_build(Subject, data.get("subject")),
            alert=_build(Alert, data.get("alert")),
            investigation=_build(Investigation, data.get("investigation")),
            prior_sars=[_build(PriorSAR, p) for p in data.get("prior_sars") or []],
            pattern_override=data.get("pattern_override", ""),
            override_reason=data.get("override_reason", ""),
        )

    def fingerprint(self) -> str:
        """Stable hash of every input the narrative depends on (reproducibility)."""
        payload = self.to_dict()
        payload.pop("case_id", None)
        blob = json.dumps(payload, sort_keys=True, default=str).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


# ── Normalisation ────────────────────────────────────────────────────────────

_TRUTHY = {"1", "true", "yes", "y", "x", "t", "flagged", "suspicious"}

# Currency spellings → the IBM dataset's names (used by the prompt and the rules).
# Without this, "Euro" and "EUR" in one file looked like a currency conversion.
CURRENCY_CODES = {
    "US Dollar": "USD", "Euro": "EUR", "UK Pound": "GBP", "Yuan": "CNY", "Rupee": "INR",
    "Yen": "JPY", "Swiss Franc": "CHF", "Australian Dollar": "AUD", "Canadian Dollar": "CAD",
    "Saudi Riyal": "SAR", "Mexican Peso": "MXN", "Ruble": "RUB", "Shekel": "ILS",
    "Brazil Real": "BRL", "Bitcoin": "BTC",
}
_CURRENCY_ALIASES = {
    "$": "US Dollar", "us$": "US Dollar", "dollar": "US Dollar", "dollars": "US Dollar",
    "us dollars": "US Dollar", "u.s. dollar": "US Dollar", "u.s. dollars": "US Dollar",
    "€": "Euro", "euros": "Euro", "£": "UK Pound", "pound": "UK Pound", "pounds": "UK Pound",
    "uk pounds": "UK Pound", "pound sterling": "UK Pound", "sterling": "UK Pound",
    "rmb": "Yuan", "renminbi": "Yuan", "₹": "Rupee", "rupees": "Rupee", "¥": "Yen",
    "swiss francs": "Swiss Franc", "australian dollars": "Australian Dollar",
    "canadian dollars": "Canadian Dollar", "riyal": "Saudi Riyal", "saudi riyals": "Saudi Riyal",
    "peso": "Mexican Peso", "pesos": "Mexican Peso", "mexican pesos": "Mexican Peso",
    "rouble": "Ruble", "roubles": "Ruble", "rubles": "Ruble", "shekels": "Shekel",
    "new israeli shekel": "Shekel", "brazilian real": "Brazil Real", "real": "Brazil Real",
    "reais": "Brazil Real", "xbt": "Bitcoin", "bitcoins": "Bitcoin",
}
_CURRENCY_ALIASES.update({name.lower(): name for name in CURRENCY_CODES})
_CURRENCY_ALIASES.update({code.lower(): name for name, code in CURRENCY_CODES.items()})


def canonical_currency(value) -> str:
    """'EUR', 'euro', '€' → 'Euro'. Unknown spellings are kept as given."""
    text = str(value).strip()
    return _CURRENCY_ALIASES.get(text.lower(), text)


def currency_code(value) -> str:
    """'Euro' / 'EUR' / '€' → 'EUR' (unknown spellings upper-cased)."""
    name = canonical_currency(value)
    return CURRENCY_CODES.get(name, name.upper())


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return str(value).strip().lower() in _TRUTHY


def normalise_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Give any partially-filled canonical frame every column with sane types."""
    df = df.copy()
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    for col in ("Amount Received", "Amount Paid"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    text_cols = [c for c in CANONICAL_COLUMNS
                 if c not in ("Amount Received", "Amount Paid", "Flagged")]
    for col in text_cols:
        df[col] = df[col].astype("object").where(df[col].notna(), "")
        df[col] = df[col].astype(str).str.strip()
    for col in ("From_Entity_Name", "To_Entity_Name"):
        df[col] = df[col].replace("", "Unknown")
    df["Payment Format"] = df["Payment Format"].replace("", "Unknown")
    for col in ("Payment Currency", "Receiving Currency"):
        df[col] = df[col].map(canonical_currency)
    df["Flagged"] = df["Flagged"].map(_truthy) if df["Flagged"].notna().any() else True
    df["Flagged"] = df["Flagged"].astype(bool)
    missing_id = df["Txn_ID"] == ""
    df.loc[missing_id, "Txn_ID"] = [f"T{i + 1}" for i in range(int(missing_id.sum()))]
    return df[CANONICAL_COLUMNS].reset_index(drop=True)


def empty_transactions(rows: int = 0) -> pd.DataFrame:
    return normalise_frame(pd.DataFrame(index=range(rows)))


# ── Samples: IBM dataset attempts ────────────────────────────────────────────

def from_attempt(attempt_id: int, case_id: str = "") -> CaseInput:
    """A laundering attempt from the enriched IBM parquet, as a case."""
    from data_loader import get_attempt

    df = get_attempt(attempt_id)
    first = df.iloc[0]
    txns = df.drop(columns=["attempt_id", "pattern_type", "degree_info"], errors="ignore")
    txns = txns.assign(Flagged=True)
    return CaseInput(
        case_id=case_id or f"C{attempt_id:03d}",
        transactions=normalise_frame(txns),
        source="sample",
        attempt_id=int(attempt_id),
        dataset_label=str(first.get("pattern_type", "")),
        degree_info=str(first.get("degree_info", "") or ""),
    )


def as_case(case_or_attempt, case_id: str = "") -> CaseInput:
    """Accept a CaseInput or a bare attempt ID (backwards-compatible callers)."""
    if isinstance(case_or_attempt, (int,)) or str(case_or_attempt).isdigit():
        return from_attempt(int(case_or_attempt), case_id)
    return case_or_attempt


# ── Uploads ──────────────────────────────────────────────────────────────────

# Logical field → header synonyms (normalised: lower case, single spaces).
FIELDS: dict[str, tuple[str, list[str]]] = {
    "timestamp": ("Date / time", ["timestamp", "date", "datetime", "date time", "transaction date",
                                  "txn date", "value date", "posting date", "booking date", "time"]),
    "from_account": ("From account", ["from account", "sender account", "originator account",
                                      "debit account", "source account", "payer account",
                                      "remitter account", "ordering account"]),
    "to_account": ("To account", ["to account", "receiver account", "beneficiary account",
                                  "credit account", "destination account", "payee account",
                                  "account.1"]),
    "amount": ("Amount (single)", ["amount", "value", "transaction amount", "amt", "sum"]),
    "amount_paid": ("Amount paid", ["amount paid", "paid amount", "sent amount"]),
    "amount_received": ("Amount received", ["amount received", "received amount"]),
    "currency": ("Currency (single)", ["currency", "ccy", "curr", "currency code"]),
    "payment_currency": ("Payment currency", ["payment currency", "paid currency", "sent currency"]),
    "receiving_currency": ("Receiving currency", ["receiving currency", "received currency"]),
    "payment_format": ("Payment method", ["payment format", "payment method", "method", "channel",
                                          "transaction type", "txn type", "type", "instrument"]),
    "from_bank": ("From bank", ["from bank", "sender bank", "originator bank", "from bank id",
                                "debit bank"]),
    "to_bank": ("To bank", ["to bank", "receiver bank", "beneficiary bank", "to bank id",
                            "credit bank"]),
    "from_bank_name": ("From bank name", ["from bank name", "sender bank name",
                                          "originator bank name"]),
    "to_bank_name": ("To bank name", ["to bank name", "beneficiary bank name",
                                      "receiver bank name"]),
    "from_name": ("From name", ["from name", "sender name", "originator name", "payer",
                                "payer name", "from entity", "sender", "originator", "remitter",
                                "from"]),
    "to_name": ("To name", ["to name", "receiver name", "beneficiary", "beneficiary name",
                            "payee", "payee name", "to entity", "receiver", "to"]),
    "from_country": ("From country", ["from country", "sender country", "originator country",
                                      "origin country"]),
    "to_country": ("To country", ["to country", "receiver country", "beneficiary country",
                                  "destination country"]),
    "flagged": ("Flagged (in scope)", ["flagged", "suspicious", "alerted", "in scope",
                                       "is laundering", "flag"]),
    "txn_id": ("Transaction ID", ["transaction id", "txn id", "id", "reference", "ref",
                                  "transaction reference"]),
    # Single-account statements: one side is the subject's account.
    "debit": ("Debit (money out)", ["debit", "debits", "withdrawal", "withdrawals", "money out",
                                    "paid out", "debit amount"]),
    "credit": ("Credit (money in)", ["credit", "credits", "deposit", "deposits", "money in",
                                     "paid in", "credit amount"]),
    "counterparty": ("Counterparty account", ["counterparty", "counterparty account",
                                              "other account", "counter account"]),
    "counterparty_name": ("Counterparty name", ["counterparty name", "other party",
                                                "description", "details", "narrative"]),
}

IBM_TRANS_MAPPING = {
    "timestamp": "Timestamp", "from_bank": "From Bank", "from_account": "Account",
    "to_bank": "To Bank", "to_account": "Account.1",
    "amount_received": "Amount Received", "receiving_currency": "Receiving Currency",
    "amount_paid": "Amount Paid", "payment_currency": "Payment Currency",
    "payment_format": "Payment Format", "flagged": "Is Laundering",
}


def _norm_header(name: str) -> str:
    h = re.sub(r"[\s_\-]+", " ", str(name).strip().lower())
    # "Sender Acct", "Beneficiary A/C", "From Acc No", "To Account #" → "... account"
    h = re.sub(r"\b(?:acct|acc|a/c|account)(?:\s*(?:no|number|num|#|id))?\.?$", "account", h)
    return h.strip()


def _header_index(rows: list[list]) -> int:
    """Row index of the column headers: the first row nearly as wide as the widest
    row near the top. Bank exports often put a title or account line above it."""
    def filled(row):
        return sum(1 for c in row if str(c).strip() not in ("", "nan", "None"))
    counts = [filled(r) for r in rows[:30]]
    if not counts:
        return 0
    target = max(counts)
    return next((i for i, n in enumerate(counts) if n >= max(2, 0.8 * target)), 0)


def read_table(file, filename: str = "") -> pd.DataFrame:
    """Read an uploaded CSV / XLSX as strings (types are parsed in apply_mapping).

    Notes about how the file was read (encoding fallback, skipped title lines) are
    kept in `df.attrs["read_notes"]` and reported by `apply_mapping` / `import_table`.
    """
    notes: list[dict] = []
    name = (filename or getattr(file, "name", "")).lower()
    if name.endswith((".xlsx", ".xls")):
        grid = pd.read_excel(file, dtype=str, header=None)
        hdr = _header_index(grid.fillna("").values.tolist())
        df = grid.iloc[hdr + 1:].reset_index(drop=True)
        df.columns = [str(c).strip() for c in grid.iloc[hdr]]
    else:
        raw = file.read() if hasattr(file, "read") else open(file, "rb").read()
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                raw = raw.decode("cp1252", errors="replace")
                notes.append({"level": "warning", "message":
                              "The file is not UTF-8, so it was read as Windows-1252 (Western "
                              "European). Check that accented names came through correctly."})
        sample = raw[:4096]
        sep = ";" if sample.count(";") > sample.count(",") else ("\t" if "\t" in sample else ",")
        lines = raw.splitlines()
        hdr = _header_index([next(csv.reader([ln], delimiter=sep), []) for ln in lines[:30]])
        df = pd.read_csv(io.StringIO("\n".join(lines[hdr:])), dtype=str, sep=sep,
                         skipinitialspace=True)
    if hdr:
        notes.append({"level": "warning", "message":
                      f"Skipped {hdr} line(s) above the column headers."})
    df.attrs["read_notes"] = notes
    df.attrs["header_row"] = hdr
    return df


def detect_format(df: pd.DataFrame) -> str:
    """'ibm_trans' | 'canonical' | 'generic'."""
    cols = set(df.columns)
    if {"Account", "Account.1", "Amount Paid", "Payment Format"} <= cols:
        return "ibm_trans"
    if {"Timestamp", "From_Account", "To_Account", "Amount Paid"} <= cols:
        return "canonical"
    return "generic"


def suggest_mapping(columns) -> dict[str, str]:
    """Best-guess logical field → source column, each column used at most once."""
    headers = {c: _norm_header(c) for c in columns}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    # Pass 1: exact synonym matches, in FIELDS order (specific before generic).
    for key, (_, synonyms) in FIELDS.items():
        for col, h in headers.items():
            if col not in used and h in synonyms:
                mapping[key] = col
                used.add(col)
                break
    # Pass 2: a synonym contained in the header ("Transaction Date (UTC)").
    for key, (_, synonyms) in FIELDS.items():
        if key in mapping:
            continue
        for col, h in headers.items():
            if col in used:
                continue
            if any(len(s) > 3 and s in h for s in synonyms):
                mapping[key] = col
                used.add(col)
                break
    # A lone "amount" should not also be read as paid/received, and vice versa.
    if "amount_paid" in mapping or "amount_received" in mapping:
        mapping.pop("amount", None)
    # Exports with names but no account numbers: the name identifies the party.
    for side in ("from", "to"):
        if f"{side}_account" not in mapping and f"{side}_name" in mapping and not (
                "debit" in mapping or "credit" in mapping):
            mapping[f"{side}_account"] = mapping[f"{side}_name"]
    return mapping


_CURRENCY_AFFIX = re.compile(r"^(?:[A-Za-z]{3}\$?|US\$|[$€£₹¥])\s*|\s*(?:[A-Za-z]{3}|[$€£₹¥])$")
_SCALE = {"k": 1e3, "m": 1e6, "mm": 1e6, "mn": 1e6, "bn": 1e9}
_SPACES = re.compile(r"[\s\u00a0\u202f']")


def _amount_core(value) -> tuple[str, float, bool] | None:
    """(digits with separators, scale multiplier, negative) — None for a blank cell."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    negative = (text.startswith("(") and text.endswith(")")) or text.startswith(("-", "−")) \
        or text.endswith("-")
    text = text.strip("()").strip().lstrip("-−").rstrip("-").strip()
    for _ in range(2):
        text = _CURRENCY_AFFIX.sub("", text).strip()
    scale = 1.0
    m = re.fullmatch(r"(.*\d)\s*(k|m|mm|mn|bn)", text, re.IGNORECASE)
    if m:
        text, scale = m.group(1), _SCALE[m.group(2).lower()]
    return _SPACES.sub("", text), scale, negative


def amount_style(values) -> str:
    """',' when a column writes amounts the European way (9.800,00), else '.'."""
    comma = dot = dotted_thousands = comma_thousands = 0
    for v in list(values)[:500]:
        core = _amount_core(v)
        if not core:
            continue
        t = core[0]
        if re.search(r"\d,\d{1,2}$", t) or re.search(r"\.\d{3},", t):
            comma += 1
        elif re.search(r"\d\.\d{1,2}$", t) or re.search(r",\d{3}\.", t):
            dot += 1
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", t):
            dotted_thousands += 1
        elif re.fullmatch(r"\d{1,3}(?:,\d{3})+", t):
            comma_thousands += 1
    if comma > dot or (not dot and not comma and dotted_thousands > comma_thousands):
        return ","
    return "."


def _parse_amount(value, decimal: str = ".") -> float | None:
    """'$9,800.00', '9.800,00' (decimal=','), '1 234,56', '(250.00)', '$9.8k' → float.

    Anything that still isn't a number after removing a currency symbol/code,
    separators and a k/M/bn suffix is NaN (reported as an error), never a guess.
    """
    core = _amount_core(value)
    if core is None:
        return None
    text, scale, negative = core
    if decimal == ",":
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float("nan")
    amount = float(text) * scale
    return -amount if negative else amount


def _scaled(values) -> bool:
    return any((c := _amount_core(v)) and c[1] != 1.0 for v in list(values)[:500])


def date_order_ambiguous(values) -> bool:
    """True when dates are numeric d/m/y or m/d/y and no value shows which it is."""
    seen = False
    for v in list(values)[:500]:
        m = re.match(r"^\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", str(v))
        if not m:
            continue
        a, b = int(m[1]), int(m[2])
        if a > 12 or b > 12:
            return False
        seen = seen or a != b
    return seen


def hygiene_issues(df: pd.DataFrame, row_offset: int = 2) -> tuple[pd.DataFrame, list[dict]]:
    """Warnings about data that is readable but probably not what the analyst meant.

    Also merges account IDs that differ only in case or spacing ("ng-4471" / "NG-4471"),
    which would otherwise be two accounts in the money-flow graph.
    """
    issues: list[dict] = []
    if df.empty:
        return df, issues
    df = df.copy()

    def rows(mask):
        return ", ".join(str(i + row_offset) for i in mask[mask].index[:5])

    ids = pd.concat([df["From_Account"], df["To_Account"]])
    ids = ids[ids != ""]
    merged = []
    for _, group in ids.groupby(ids.str.upper().str.replace(r"\s+", "", regex=True)):
        spellings = group.value_counts()
        if len(spellings) > 1:
            keep = spellings.index[0]
            for other in spellings.index[1:]:
                df.loc[df["From_Account"] == other, "From_Account"] = keep
                df.loc[df["To_Account"] == other, "To_Account"] = keep
                merged.append(f"{other} → {keep}")
    if merged:
        issues.append({"level": "warning", "message":
                       "Merged account IDs that differ only in capitalisation or spacing: "
                       + ", ".join(merged[:5]) + ("…" if len(merged) > 5 else "") + "."})
    key = ["Timestamp", "From_Account", "To_Account", "Amount Paid", "Payment Currency",
           "Amount Received", "Receiving Currency", "Payment Format"]
    dup = df.duplicated(subset=key)
    if dup.any():
        issues.append({"level": "warning", "message":
                       f"{int(dup.sum())} duplicate row(s) exactly repeat an earlier row (file rows "
                       f"{rows(dup)}). They are kept and counted; delete them if the export "
                       "listed a transaction twice."})
    same = (df["From_Account"] == df["To_Account"]) & (df["From_Account"] != "")
    if same.any():
        issues.append({"level": "warning", "message":
                       f"{int(same.sum())} row(s) move money from an account to itself "
                       f"(file rows {rows(same)})."})
    zero = df["Amount Paid"].fillna(1) == 0
    if zero.any():
        issues.append({"level": "warning", "message":
                       f"{int(zero.sum())} row(s) have a zero amount (file rows {rows(zero)})."})
    return df, issues


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str], *, dayfirst: bool = False,
                  statement_account: str = "",
                  default_currency: str = "US Dollar") -> tuple[pd.DataFrame, list[dict]]:
    """Convert an uploaded table to the canonical schema.

    Returns (canonical_frame, issues). Issues are {"level": "error"|"warning",
    "message": str}; any error means the case can't be generated yet.
    """
    issues: list[dict] = list(df.attrs.get("read_notes", []))
    row_offset = 2 + int(df.attrs.get("header_row", 0))

    def err(msg):
        issues.append({"level": "error", "message": msg})

    def warn(msg):
        issues.append({"level": "warning", "message": msg})

    def col(key):
        src = mapping.get(key)
        return df[src] if src and src in df.columns else None

    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        err("The file has no rows.")
        return empty_transactions(), issues

    out = pd.DataFrame(index=df.index)
    statement = col("from_account") is None and col("to_account") is None and (
        col("debit") is not None or col("credit") is not None)

    # Timestamp
    ts_src = col("timestamp")
    if ts_src is None:
        err("Map a date / time column.")
    else:
        parsed = pd.to_datetime(ts_src, errors="coerce", dayfirst=dayfirst, format="mixed")
        bad = parsed.isna() & ts_src.notna()
        if bad.any():
            rows = ", ".join(str(i + 2) for i in bad[bad].index[:5])
            err(f"{int(bad.sum())} date(s) could not be read (file rows {rows}).")
        out["Timestamp"] = parsed.dt.strftime(TIMESTAMP_FORMAT)
        if date_order_ambiguous(ts_src.dropna()):
            example = ts_src.dropna().astype(str).iloc[0]
            warn(f"Every date could be read either way (e.g. {example}); they were read as "
                 f"{'day/month' if dayfirst else 'month/day'}. Switch the day-first setting "
                 "if that is wrong.")

    amount_cols = [c for c in (col("debit"), col("credit"), col("amount"), col("amount_paid"),
                               col("amount_received")) if c is not None]
    values = pd.concat(amount_cols) if amount_cols else pd.Series(dtype=str)
    decimal = amount_style(values)
    if decimal == ",":
        warn("Amounts use ',' as the decimal separator (e.g. 9.800,00 = 9,800.00) and were "
             "read that way.")
    if _scaled(values):
        warn("Amounts with k / M / bn suffixes were expanded (e.g. 9.8k = 9,800.00).")

    def parse(series):
        return series.map(lambda v: _parse_amount(v, decimal))

    if statement:
        if not statement_account:
            err("This looks like a single-account statement (debit/credit columns). "
                "Enter the statement's account number.")
        debit = (parse(col("debit")) if col("debit") is not None
                 else pd.Series(None, index=df.index, dtype=float))
        credit = (parse(col("credit")) if col("credit") is not None
                  else pd.Series(None, index=df.index, dtype=float))
        cp = col("counterparty")
        cp_name = col("counterparty_name")
        counterparty = (cp.fillna("") if cp is not None else
                        (cp_name.fillna("") if cp_name is not None else pd.Series("", index=df.index)))
        if cp is None:
            warn("No counterparty account column mapped; the counterparty name/description is "
                 "used as the account identifier.")
        is_out = debit.fillna(0).abs() > 0
        amount = debit.abs().where(is_out, credit.abs())
        out["From_Account"] = counterparty.where(~is_out, statement_account)
        out["To_Account"] = pd.Series(statement_account, index=df.index).where(~is_out, counterparty)
        if cp_name is not None:
            out["From_Entity_Name"] = cp_name.where(~is_out, "")
            out["To_Entity_Name"] = cp_name.where(is_out, "")
        paid = received = amount
    else:
        if col("from_account") is None or col("to_account") is None:
            err("Map both a From account and a To account column "
                "(or Debit/Credit columns for a single-account statement).")
        out["From_Account"] = col("from_account") if col("from_account") is not None else ""
        out["To_Account"] = col("to_account") if col("to_account") is not None else ""
        single = col("amount")
        paid_src = col("amount_paid") if col("amount_paid") is not None else single
        recv_src = col("amount_received") if col("amount_received") is not None else single
        if paid_src is None and recv_src is None:
            err("Map an amount column.")
            paid = received = pd.Series(float("nan"), index=df.index)
        else:
            paid = parse(paid_src if paid_src is not None else recv_src)
            received = parse(recv_src if recv_src is not None else paid_src)

    paid = pd.to_numeric(paid, errors="coerce")
    received = pd.to_numeric(received, errors="coerce")
    bad_amount = paid.isna() | received.isna()
    if bad_amount.any() and not any(i["message"].startswith("Map an amount") for i in issues):
        rows = ", ".join(str(i + row_offset) for i in bad_amount[bad_amount].index[:5])
        err(f"{int(bad_amount.sum())} amount(s) could not be read (file rows {rows}).")
    if (paid < 0).any() or (received < 0).any():
        warn("Negative amounts were converted to positive values; direction comes from the "
             "From/To accounts.")
    out["Amount Paid"] = paid.abs()
    out["Amount Received"] = received.abs()

    # Currencies — a single currency column fills both sides (not a merge: the
    # file only has one value per row).
    single_ccy = col("currency")
    pay_ccy = col("payment_currency") if col("payment_currency") is not None else single_ccy
    recv_ccy = col("receiving_currency") if col("receiving_currency") is not None else single_ccy
    if pay_ccy is None and recv_ccy is None:
        warn(f"No currency column mapped; assuming {default_currency}.")
    out["Payment Currency"] = (pay_ccy if pay_ccy is not None else recv_ccy
                               if recv_ccy is not None else default_currency)
    out["Receiving Currency"] = (recv_ccy if recv_ccy is not None else pay_ccy
                                 if pay_ccy is not None else default_currency)

    for key, target in (("payment_format", "Payment Format"), ("from_bank", "From Bank"),
                        ("to_bank", "To Bank"), ("from_bank_name", "From_Bank_Name"),
                        ("to_bank_name", "To_Bank_Name"), ("from_country", "From_Country"),
                        ("to_country", "To_Country"), ("txn_id", "Txn_ID")):
        if col(key) is not None:
            values = col(key)
            # A "bank" column holding names ("Harbor Community Bank") rather than
            # IDs ("021174") belongs in the bank-name column.
            if key in ("from_bank", "to_bank") and f"{key}_name" not in mapping:
                sample = values.dropna().astype(str).head(50)
                if len(sample) and sample.str.contains(r"[A-Za-z]{3,}").mean() > 0.5:
                    target = "From_Bank_Name" if key == "from_bank" else "To_Bank_Name"
            out[target] = values
    if col("from_name") is not None:
        out["From_Entity_Name"] = col("from_name")
    if col("to_name") is not None:
        out["To_Entity_Name"] = col("to_name")
    if col("flagged") is not None:
        out["Flagged"] = col("flagged").map(_truthy)
        if not out["Flagged"].any():
            warn("No rows are marked as flagged, so every transaction is treated as in scope.")
            out["Flagged"] = True

    canonical = normalise_frame(out)
    missing_accounts = (canonical["From_Account"] == "") | (canonical["To_Account"] == "")
    if missing_accounts.any() and not any("account" in i["message"].lower() and
                                          i["level"] == "error" for i in issues):
        rows = ", ".join(str(i + 2) for i in missing_accounts[missing_accounts].index[:5])
        err(f"{int(missing_accounts.sum())} row(s) are missing an account (file rows {rows}).")
    canonical, hygiene = hygiene_issues(canonical, row_offset)
    return canonical, issues + hygiene


def import_table(df: pd.DataFrame, mapping: dict[str, str] | None = None, **kwargs
                 ) -> tuple[pd.DataFrame, list[dict], str, dict[str, str]]:
    """Detect the format, map, convert and (for IBM data) enrich names.

    Returns (canonical_frame, issues, format, mapping_used).
    """
    fmt = detect_format(df)
    if fmt == "canonical" and mapping is None:
        canonical, issues = hygiene_issues(normalise_frame(df),
                                           2 + int(df.attrs.get("header_row", 0)))
        return canonical, list(df.attrs.get("read_notes", [])) + issues, fmt, {}
    if mapping is None:
        mapping = IBM_TRANS_MAPPING if fmt == "ibm_trans" else suggest_mapping(df.columns)
    canonical, issues = apply_mapping(df, mapping, **kwargs)
    if fmt == "ibm_trans":
        from data_loader import enrich_with_accounts
        canonical = normalise_frame(enrich_with_accounts(canonical))
        if "Is Laundering" in df.columns:
            issues.append({"level": "warning", "message":
                           "IBM format: the 'Is Laundering' column is used as the monitoring "
                           "system's alert flag (Flagged)."})
    return canonical, issues, fmt, mapping


def template_csv() -> str:
    """A generic upload template with two example rows."""
    rows = [
        {"Date": "2024-03-04 10:15", "From Account": "ACC-1001", "From Name": "Jane Doe",
         "From Bank": "First Example Bank", "To Account": "ACC-2002", "To Name": "Acme Imports LLC",
         "To Bank": "Second Example Bank", "Amount": "9,500.00", "Currency": "USD",
         "Method": "Cash", "Flagged": "yes"},
        {"Date": "2024-03-05 16:40", "From Account": "ACC-2002", "From Name": "Acme Imports LLC",
         "From Bank": "Second Example Bank", "To Account": "ACC-3003", "To Name": "Beta Holdings",
         "To Bank": "Offshore Example Bank", "Amount": "9,200.00", "Currency": "USD",
         "Method": "Wire", "Flagged": "yes"},
    ]
    return pd.DataFrame(rows).to_csv(index=False)


# ── Helpers shared by the engine, prompt and UI ──────────────────────────────

def parse_iso_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value if not isinstance(value, datetime) else value.date()
    try:
        return pd.to_datetime(str(value)).date()
    except (ValueError, TypeError):
        return None


USD_NAMES = {"usd", "us dollar", "us dollars", "u.s. dollar", "dollar", "$"}


def is_usd(currency) -> bool:
    return str(currency).strip().lower() in USD_NAMES


def guess_dayfirst(values) -> bool:
    """True when dates look like dd/mm (some first field > 12), e.g. 13/06/2024."""
    values = list(values)[:200]
    if values and all(re.match(r"^\s*\d{1,2}\.\d{1,2}\.\d{2,4}", str(v)) for v in values):
        return True   # dd.mm.yyyy: dotted dates are day-first by convention
    for v in values:
        m = re.match(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", str(v))
        if m and int(m[1]) > 12:
            return True
        if m and int(m[2]) > 12:
            return False
    return False


_KEY_FIELDS = ["Timestamp", "From_Account", "To_Account", "Amount Paid", "Amount Received"]


def finalize_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Clean a hand-edited grid: drop blank rows, canonicalise dates, fill the
    obvious gaps (received = paid for same-currency entries) and report errors."""
    issues: list[dict] = []
    df = df.copy()
    for col in _KEY_FIELDS:
        if col not in df.columns:
            df[col] = pd.NA
    blank = df[_KEY_FIELDS].apply(
        lambda col: col.isna() | (col.astype(str).str.strip().isin(["", "nan", "None", "<NA>"]))
    ).all(axis=1)
    df = df[~blank].reset_index(drop=True)
    if df.empty:
        return empty_transactions(), [{"level": "error", "message": "Add at least one transaction."}]

    df = normalise_frame(df)
    ts = pd.to_datetime(df["Timestamp"].replace("", pd.NA), errors="coerce", format="mixed")
    bad = ts.isna()
    if bad.any():
        rows = ", ".join(str(i + 1) for i in bad[bad].index[:5])
        issues.append({"level": "error", "message":
                       f"{int(bad.sum())} row(s) have a missing or unreadable date (rows {rows}). "
                       "Use e.g. 2024/06/03 14:40."})
    df["Timestamp"] = ts.dt.strftime(TIMESTAMP_FORMAT).where(~bad, df["Timestamp"])

    df["Amount Received"] = df["Amount Received"].fillna(df["Amount Paid"])
    df["Amount Paid"] = df["Amount Paid"].fillna(df["Amount Received"])
    df["Receiving Currency"] = df["Receiving Currency"].replace("", pd.NA).fillna(
        df["Payment Currency"].replace("", pd.NA)).fillna("US Dollar")
    df["Payment Currency"] = df["Payment Currency"].replace("", pd.NA).fillna(df["Receiving Currency"])
    missing_amount = df["Amount Paid"].isna()
    if missing_amount.any():
        rows = ", ".join(str(i + 1) for i in missing_amount[missing_amount].index[:5])
        issues.append({"level": "error", "message":
                       f"{int(missing_amount.sum())} row(s) have no amount (rows {rows})."})
    missing_acct = (df["From_Account"] == "") | (df["To_Account"] == "")
    if missing_acct.any():
        rows = ", ".join(str(i + 1) for i in missing_acct[missing_acct].index[:5])
        issues.append({"level": "error", "message":
                       f"{int(missing_acct.sum())} row(s) are missing a From or To account "
                       f"(rows {rows})."})
    if (df["Amount Paid"] < 0).any():
        df["Amount Paid"] = df["Amount Paid"].abs()
        df["Amount Received"] = df["Amount Received"].abs()
        issues.append({"level": "warning", "message": "Negative amounts were made positive."})
    if not df["Flagged"].any():
        issues.append({"level": "warning", "message":
                       "No rows are flagged, so every transaction is treated as in scope."})
    df, hygiene = hygiene_issues(df, row_offset=1)
    return df, issues + [dict(i, message=i["message"].replace("file rows", "rows"))
                         for i in hygiene]
