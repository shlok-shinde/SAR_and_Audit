"""
typology.py — Deterministic, explainable typology detection and red flags.

Custom cases arrive without a pattern label, so the typology the narrative is
built around has to come from the data. This module does it with rules over
the money-flow graph (accounts = nodes, transfers = edges) — not a model — so
every conclusion comes with evidence an analyst or examiner can re-check.

  detect_typology(df)            → Detection(pattern, confidence, evidence, roles…)
  detect_red_flags(df, subject…) → [RedFlag(code, title, severity, evidence…)]

Accuracy against the 370 labelled IBM attempts: see evaluate_typology.py and
docs/EVALUATION.md.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

import networkx as nx
import pandas as pd

from case_input import is_usd, parse_iso_date

PATTERNS = ["FAN-OUT", "FAN-IN", "CYCLE", "GATHER-SCATTER", "SCATTER-GATHER",
            "STACK", "BIPARTITE", "NONE"]

# "NONE" is what the IBM dataset calls RANDOM: a random walk with no typology.
DATASET_EQUIVALENT = {"RANDOM": "NONE"}


@dataclass
class Detection:
    pattern: str                      # one of PATTERNS
    confidence: str                   # high | medium | low
    evidence: list[str] = field(default_factory=list)
    roles: dict[str, str] = field(default_factory=dict)   # account → role
    alternatives: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RedFlag:
    code: str
    title: str
    severity: str                     # high | medium | low
    evidence: str
    txn_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Formatting helpers ───────────────────────────────────────────────────────

def _money(amount: float, currency: str = "") -> str:
    if currency and not is_usd(currency):
        return f"{amount:,.2f} {currency}"
    return f"${amount:,.2f}"


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")


def _day(ts: str) -> str:
    return str(ts)[:10]


def _label(df: pd.DataFrame, account: str) -> str:
    """'8049DD1C0 (Corporation #30450)' — account plus entity name when known."""
    for side in ("From", "To"):
        rows = df[df[f"{side}_Account"] == account]
        if not rows.empty:
            name = str(rows.iloc[0][f"{side}_Entity_Name"])
            if name and name != "Unknown":
                return f"{account} ({name})"
    return account


# ── Typology detection ───────────────────────────────────────────────────────

def build_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Directed graph of distinct account pairs; edge weight = transfer count."""
    g = nx.DiGraph()
    for src, dst in zip(df["From_Account"], df["To_Account"]):
        if src == dst:
            continue                  # self-transfers carry no flow structure
        if g.has_edge(src, dst):
            g[src][dst]["n"] += 1
        else:
            g.add_edge(src, dst, n=1)
    return g


def _is_simple_path(c: nx.DiGraph) -> bool:
    ins, outs = dict(c.in_degree()), dict(c.out_degree())
    return (max(ins.values()) <= 1 and max(outs.values()) <= 1
            and nx.is_directed_acyclic_graph(c))


def detect_typology(df: pd.DataFrame) -> Detection:
    """Classify the flow structure of the (flagged) transactions."""
    g = build_graph(df)
    n_txn = len(df)
    if g.number_of_edges() == 0:
        return Detection("NONE", "low", ["No transfers between distinct accounts."])

    ins, outs = dict(g.in_degree()), dict(g.out_degree())
    sources = [n for n in g if ins[n] == 0]
    sinks = [n for n in g if outs[n] == 0]
    mids = [n for n in g if ins[n] > 0 and outs[n] > 0]
    comps = [g.subgraph(c).copy() for c in nx.weakly_connected_components(g)]
    stats = {"accounts": g.number_of_nodes(), "links": g.number_of_edges(),
             "transactions": n_txn, "components": len(comps),
             "sources": len(sources), "sinks": len(sinks), "intermediaries": len(mids),
             "max_out": max(outs.values()), "max_in": max(ins.values())}
    small = g.number_of_edges() <= 2
    conf = "low" if small else "high"

    def done(pattern, evidence, roles, confidence=conf, alternatives=()):
        return Detection(pattern, confidence, evidence, roles, list(alternatives), stats)

    # CYCLE: one ring — every account passes the money on exactly once and it
    # comes back to where it started.
    if (len(comps) == 1 and all(ins[n] == 1 and outs[n] == 1 for n in g)
            and nx.is_strongly_connected(g)):
        ring = [e[0] for e in nx.find_cycle(g)]
        path = " → ".join(ring + [ring[0]])
        alts = ["STACK", "SCATTER-GATHER"] if len(ring) == 2 else []
        return done("CYCLE", [
            f"Funds moved {path}: {len(ring)} hops that return to the originating account.",
            f"Every account in the ring received once and sent once "
            f"({n_txn} transfers).",
        ], {n: "cycle member" for n in g}, "low" if len(ring) == 2 else "high", alts)

    # Components that are all single transfers (A → B, C → D, …).
    if all(c.number_of_edges() == 1 for c in comps):
        if len(comps) == 1:
            (a, b), = g.edges()
            return done("NONE", [
                f"A single transfer relationship ({_label(df, a)} → {_label(df, b)}); "
                "one link has no network structure to classify.",
            ], {a: "sender", b: "receiver"}, "low", ["FAN-OUT", "FAN-IN", "BIPARTITE"])
        return done("BIPARTITE", [
            f"{len(comps)} separate sender → receiver pairs with no account in common: "
            "disjoint groups making coordinated transfers.",
            f"{len(sources)} sending and {len(sinks)} receiving accounts; none both sends "
            "and receives.",
        ], {**{s: "sender" for s in sources}, **{t: "receiver" for t in sinks}})

    # STACK: several parallel chains of the same length (layering in lockstep).
    if len(comps) >= 2 and all(_is_simple_path(c) for c in comps):
        lengths = Counter(c.number_of_edges() for c in comps)
        hops = lengths.most_common(1)[0][0]
        return done("STACK", [
            f"{len(comps)} parallel chains, most with {hops} hops "
            f"(sender → {hops - 1} intermediary layer(s) → receiver).",
            f"{len(mids)} intermediary accounts each receive once and pass the funds on once.",
        ], {**{s: "sender" for s in sources}, **{m: "intermediary" for m in mids},
            **{t: "receiver" for t in sinks}}, "high" if len(comps) >= 3 else "medium")

    if len(comps) == 1:
        # FAN-OUT / FAN-IN: a single hub, no onward movement.
        if len(sources) == 1 and not mids and len(sinks) >= 2:
            hub = sources[0]
            return done("FAN-OUT", [
                f"{_label(df, hub)} sent {n_txn} transfers to {len(sinks)} different "
                "accounts, with no onward movement recorded.",
                "Dispersal from one account to many is consistent with splitting funds "
                "across recipients.",
            ], {hub: "source", **{t: "recipient" for t in sinks}})
        if len(sinks) == 1 and not mids and len(sources) >= 2:
            hub = sinks[0]
            return done("FAN-IN", [
                f"{_label(df, hub)} received {n_txn} transfers from {len(sources)} "
                "different accounts.",
                "Convergence of many senders on one account is consistent with "
                "aggregation (a collection or funnel account).",
            ], {hub: "collector", **{s: "sender" for s in sources}})

        # SCATTER-GATHER: 1 source → k intermediaries → 1 sink.
        if (len(sources) == 1 and len(sinks) == 1 and len(mids) >= 2
                and all(ins[m] == 1 and outs[m] == 1 for m in mids)
                and all(g.has_edge(sources[0], m) and g.has_edge(m, sinks[0]) for m in mids)):
            s, t = sources[0], sinks[0]
            return done("SCATTER-GATHER", [
                f"{_label(df, s)} split funds across {len(mids)} intermediary accounts, "
                f"which all forwarded them to {_label(df, t)}.",
                "One origin and one destination linked only through parallel "
                "intermediaries is consistent with money-mule layering.",
            ], {s: "source", t: "destination", **{m: "intermediary" for m in mids}})

        # A single chain with no branching: IBM's RANDOM (a random walk).
        if _is_simple_path(g):
            path = list(nx.topological_sort(g))
            return done("NONE", [
                f"A single chain of {len(path) - 1} transfer(s) "
                f"({' → '.join(path[:6])}{' → …' if len(path) > 6 else ''}) "
                "with no fan-out, fan-in, cycle or parallel structure.",
                "This matches no known laundering typology on its own.",
            ], {n: "chain" for n in path}, "medium" if len(path) > 3 else "low",
                ["STACK"] if len(path) == 3 else [])

    # Parallel round trips (A ⇄ B, C ⇄ D): a stack whose sender and receiver
    # are the same account.
    if len(comps) >= 2 and all(c.number_of_nodes() == 2 and c.number_of_edges() == 2
                               for c in comps):
        return done("STACK", [
            f"{len(comps)} parallel round trips: each pair of accounts sends funds out and "
            "back again through one intermediary.",
        ], {n: "round-trip member" for n in g}, "medium", ["CYCLE"])

    # GATHER-SCATTER: a hub that both collects from many and pays out to many.
    hub = max(g, key=lambda n: min(ins[n], outs[n]) * 1000 + ins[n] + outs[n])
    touching = sum(1 for u, v in g.edges() if hub in (u, v))

    # SCATTER-GATHER where origin and destination coincide: the hub splits funds
    # across intermediaries that each send them straight back.
    others = [n for n in g if n != hub]
    if (touching == g.number_of_edges() and len(others) >= 2
            and set(g.successors(hub)) == set(g.predecessors(hub)) == set(others)):
        return done("SCATTER-GATHER", [
            f"{_label(df, hub)} split funds across {len(others)} intermediary accounts, "
            "each of which sent them back to the same account.",
            "Origin and destination are the same account, linked only through parallel "
            "intermediaries (money-mule layering with a round trip).",
        ], {hub: "source and destination", **{m: "intermediary" for m in others}},
            "medium", ["GATHER-SCATTER"])

    if ins[hub] >= 2 and outs[hub] >= 2 and touching / g.number_of_edges() >= 0.7:
        feeders = [u for u in g.predecessors(hub)]
        payees = [v for v in g.successors(hub)]
        return done("GATHER-SCATTER", [
            f"{_label(df, hub)} collected funds from {len(feeders)} accounts and paid "
            f"out to {len(payees)} accounts.",
            f"{touching} of {g.number_of_edges()} account links run through this one hub "
            "(aggregation followed by dispersal).",
        ], {hub: "hub", **{u: "feeder" for u in feeders}, **{v: "payee" for v in payees}},
            "high" if touching == g.number_of_edges() else "medium")

    # Dominant-structure fallbacks for noisier real-world graphs.
    top_out = max(g, key=lambda n: outs[n])
    top_in = max(g, key=lambda n: ins[n])
    e = g.number_of_edges()
    if outs[top_out] >= 3 and outs[top_out] / e >= 0.6:
        return done("FAN-OUT", [
            f"{_label(df, top_out)} accounts for {outs[top_out]} of {e} account links as "
            "the sender (dominant dispersal).",
        ], {top_out: "source"}, "medium")
    if ins[top_in] >= 3 and ins[top_in] / e >= 0.6:
        return done("FAN-IN", [
            f"{_label(df, top_in)} accounts for {ins[top_in]} of {e} account links as the "
            "receiver (dominant aggregation).",
        ], {top_in: "collector"}, "medium")
    try:
        cycle = nx.find_cycle(g)
        ring = [u for u, _ in cycle]
        if len(ring) >= 3:
            return done("CYCLE", [
                f"Part of the flow returns to its origin: {' → '.join(ring + [ring[0]])}.",
            ], {n: "cycle member" for n in ring}, "medium")
    except nx.NetworkXNoCycle:
        pass
    return done("NONE", [
        f"{g.number_of_nodes()} accounts and {e} links with no dominant fan, cycle, "
        "chain or hub structure.",
    ], {}, "low")


# ── Red flags ────────────────────────────────────────────────────────────────

CTR_THRESHOLD = 10_000.0
STRUCTURING_FLOOR = 8_000.0
PASS_THROUGH_DAYS = 7
PASS_THROUGH_SHARE = 0.8

# FATF lists as of the June 2026 plenary (19 June 2026). These change three
# times a year — refresh from fatf-gafi.org before relying on them.
FATF_AS_OF = "FATF plenary, June 2026"
FATF_CALL_FOR_ACTION = {"KP": "North Korea (DPRK)", "IR": "Iran", "MM": "Myanmar"}
FATF_INCREASED_MONITORING = {
    "AO": "Angola", "BO": "Bolivia", "BA": "Bosnia and Herzegovina", "BG": "Bulgaria",
    "CM": "Cameroon", "CI": "Côte d'Ivoire", "CD": "Democratic Republic of the Congo",
    "HT": "Haiti", "IQ": "Iraq", "KE": "Kenya", "KW": "Kuwait", "LA": "Laos",
    "LB": "Lebanon", "MC": "Monaco", "NP": "Nepal", "PG": "Papua New Guinea",
    "SS": "South Sudan", "SY": "Syria", "VE": "Venezuela", "VN": "Vietnam",
    "VG": "British Virgin Islands", "YE": "Yemen",
}
_COUNTRY_ALIASES = {
    "north korea": "KP", "dprk": "KP", "democratic people's republic of korea": "KP",
    "iran": "IR", "myanmar": "MM", "burma": "MM", "cote d'ivoire": "CI", "ivory coast": "CI",
    "drc": "CD", "congo, democratic republic": "CD", "bvi": "VG", "viet nam": "VN",
    "lao pdr": "LA", "bosnia": "BA",
}


def country_code(value: str) -> str:
    v = str(value).strip()
    if len(v) == 2:
        return v.upper()
    low = v.lower()
    if low in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[low]
    for code, name in {**FATF_CALL_FOR_ACTION, **FATF_INCREASED_MONITORING}.items():
        if low == name.lower():
            return code
    return v.upper()


def _ids(rows: pd.DataFrame) -> list[str]:
    return [str(x) for x in rows["Txn_ID"].tolist()] if "Txn_ID" in rows else []


def _structuring(df: pd.DataFrame) -> list[RedFlag]:
    flags = []
    usd = df[df["Payment Currency"].map(is_usd)]
    band = usd[(usd["Amount Paid"] >= STRUCTURING_FLOOR) & (usd["Amount Paid"] < CTR_THRESHOLD)]
    if len(band) < 2:
        return flags
    band = band.assign(_t=pd.to_datetime(band["Timestamp"], errors="coerce"))
    for account, rows in band.groupby("To_Account"):
        rows = rows.sort_values("_t")
        # Largest set of just-under-threshold deposits inside any 7-day window.
        best = rows.iloc[0:1]
        for i in range(len(rows)):
            window = rows[(rows["_t"] >= rows["_t"].iloc[i]) &
                          (rows["_t"] < rows["_t"].iloc[i] + pd.Timedelta(days=7))]
            if len(window) > len(best):
                best = window
        if len(best) < 2:
            continue
        cash = best["Payment Format"].str.lower().str.contains("cash").all()
        senders = best["From_Account"].nunique()
        what = "cash deposits" if cash else "transfers"
        note = ("each just below the $10,000 Currency Transaction Report threshold"
                if cash else "each just below $10,000 (the CTR threshold applies to cash, "
                "but amounts clustered under it can indicate threshold avoidance)")
        flags.append(RedFlag(
            "STRUCTURING", "Amounts just below the $10,000 reporting threshold",
            "high" if cash else "medium",
            f"{len(best)} {what} of ${best['Amount Paid'].min():,.2f} to "
            f"${best['Amount Paid'].max():,.2f} into {account} between "
            f"{_day(best['Timestamp'].min())} and {_day(best['Timestamp'].max())}"
            f"{f' from {senders} different senders' if senders > 1 else ''}, {note}.",
            _ids(best)))
    return flags


def _pass_through(df: pd.DataFrame) -> list[RedFlag]:
    hits: list[tuple[str, list[str]]] = []
    t = pd.to_datetime(df["Timestamp"], errors="coerce")
    for account in set(df["To_Account"]) & set(df["From_Account"]):
        inflow = df[(df["To_Account"] == account) & (df["From_Account"] != account)]
        outflow = df[(df["From_Account"] == account) & (df["To_Account"] != account)]
        if inflow.empty or outflow.empty:
            continue
        first_in, last_out = t[inflow.index].min(), t[outflow.index].max()
        if pd.isna(first_in) or pd.isna(last_out) or last_out < first_in:
            continue
        days = (last_out - first_in).total_seconds() / 86400
        if days > PASS_THROUGH_DAYS:
            continue
        in_ccy = set(inflow["Receiving Currency"])
        out_ccy = set(outflow["Payment Currency"])
        span = "within a day" if days < 1 else f"within {days:.0f} days"
        if len(in_ccy) == 1 and in_ccy == out_ccy:
            received = inflow["Amount Received"].sum()
            sent = outflow["Amount Paid"].sum()
            share = sent / received if received else 0
            if share < PASS_THROUGH_SHARE:
                continue
            ccy = next(iter(in_ccy))
            evidence = (f"{account} received {_money(received, ccy)} and sent out "
                        f"{_money(sent, ccy)} ({min(share, 9.99):.0%}) {span}, leaving little "
                        "of the funds in the account.")
        else:
            evidence = (f"{account} received funds in {', '.join(sorted(in_ccy))} and sent them "
                        f"on in {', '.join(sorted(out_ccy))} {span}.")
        hits.append((evidence, _ids(pd.concat([inflow, outflow]))))
    if not hits:
        return []
    hits.sort()
    evidence = " ".join(e for e, _ in hits[:3])
    if len(hits) > 3:
        evidence += f" ({len(hits) - 3} more pass-through account(s).)"
    return [RedFlag("RAPID_PASS_THROUGH", "Rapid movement of funds through an account",
                    "medium", evidence, sorted({i for _, ids in hits for i in ids}))]


def detect_red_flags(df: pd.DataFrame, subject=None, context: pd.DataFrame | None = None
                     ) -> list[RedFlag]:
    """Red flags on the flagged transactions (FFIEC Appendix F style indicators).

    `subject` (case_input.Subject) enables the profile checks; `context` is the
    unflagged activity used as the account's own baseline.
    """
    flags: list[RedFlag] = []
    if df.empty:
        return flags
    flags += _structuring(df)
    flags += _pass_through(df)

    cross = df[df["Payment Currency"] != df["Receiving Currency"]]
    # Conversion can also happen inside an account: received in one currency,
    # sent on in another (e.g. USD in, Rupee out).
    converters = []
    # Sorted: set order varies per process (hash randomisation), and only the
    # first three are named below — unsorted, the evidence text changed per run.
    for account in sorted(set(df["To_Account"]) & set(df["From_Account"])):
        got = set(df.loc[df["To_Account"] == account, "Receiving Currency"])
        sent = set(df.loc[df["From_Account"] == account, "Payment Currency"])
        if got and sent and got != sent:
            converters.append(f"{account} ({', '.join(sorted(got))} in → "
                              f"{', '.join(sorted(sent))} out)")
    if not cross.empty or converters:
        parts = []
        if not cross.empty:
            pairs = Counter(zip(cross["Payment Currency"], cross["Receiving Currency"]))
            parts.append(f"{len(cross)} transfer(s) paid in one currency and received in "
                         f"another ({', '.join(f'{a} → {b}' for (a, b), _ in pairs.most_common(3))})")
        if converters:
            parts.append("currency changes inside " + "; ".join(converters[:3]))
        flags.append(RedFlag("CROSS_CURRENCY", "Currency conversion within the flow", "medium",
                             _sentence("; ".join(parts)), _ids(cross)))

    fmt = df["Payment Format"].str.lower()
    ccy = (df["Payment Currency"] + " " + df["Receiving Currency"]).str.lower()
    crypto = df[fmt.str.contains("bitcoin|crypto") | ccy.str.contains("bitcoin|btc|ether|usdt")]
    if not crypto.empty:
        flags.append(RedFlag("CRYPTO", "Virtual currency involved", "medium",
                             f"{len(crypto)} transfer(s) use virtual currency "
                             f"({', '.join(sorted(set(crypto['Payment Format'])))}).",
                             _ids(crypto)))

    countries = df[(df["From_Country"] != "") & (df["To_Country"] != "")]
    if not countries.empty:
        codes_from = countries["From_Country"].map(country_code)
        codes_to = countries["To_Country"].map(country_code)
        border = countries[codes_from != codes_to]
        if not border.empty:
            dests = sorted(set(border["To_Country"].map(country_code)))
            flags.append(RedFlag(
                "CROSS_BORDER", "Cross-border transfers", "medium",
                f"{len(border)} transfer(s) totalling "
                f"{_money(border['Amount Paid'].sum(), border['Payment Currency'].iloc[0])} "
                f"crossed borders (to {', '.join(dests)}).", _ids(border)))
        involved = set(codes_from) | set(codes_to)
        black = sorted(c for c in involved if c in FATF_CALL_FOR_ACTION)
        grey = sorted(c for c in involved if c in FATF_INCREASED_MONITORING)
        if black or grey:
            names = [FATF_CALL_FOR_ACTION.get(c) or FATF_INCREASED_MONITORING[c]
                     for c in black + grey]
            mask = codes_from.isin(black + grey) | codes_to.isin(black + grey)
            flags.append(RedFlag(
                "HIGH_RISK_JURISDICTION", "High-risk jurisdiction", "high",
                f"Transfers involve {', '.join(names)} "
                f"({'FATF call for action' if black else 'FATF increased monitoring'}, "
                f"{FATF_AS_OF}).", _ids(countries[mask])))

    amounts = df["Amount Paid"]
    round_rows = df[(amounts >= 1000) & (amounts % 1000 == 0)]
    if len(df) >= 3 and len(round_rows) / len(df) >= 0.5:
        flags.append(RedFlag("ROUND_AMOUNTS", "Round-dollar amounts", "low",
                             f"{len(round_rows)} of {len(df)} transfers are round thousands.",
                             _ids(round_rows)))

    banks = set(df["From_Bank_Name"].replace("", pd.NA).dropna()) | set(
        df["To_Bank_Name"].replace("", pd.NA).dropna())
    if not banks:
        banks = set(df["From Bank"].replace("", pd.NA).dropna()) | set(
            df["To Bank"].replace("", pd.NA).dropna())
    if len(banks) >= 4:
        flags.append(RedFlag("MULTI_INSTITUTION", "Funds spread across many institutions", "low",
                             f"The activity spans {len(banks)} financial institutions.", []))

    t = pd.to_datetime(df["Timestamp"], errors="coerce").dropna().sort_values()
    if len(t) >= 5:
        best = max(((t >= x) & (t < x + pd.Timedelta(hours=24))).sum() for x in t)
        if best >= 5:
            flags.append(RedFlag("HIGH_VELOCITY", "High transaction velocity", "low",
                                 f"{best} transfers occurred within a single 24-hour window.",
                                 []))

    flags += _profile_flags(df, subject, context)
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(flags, key=lambda f: order[f.severity])


def _monthly_inflow(df: pd.DataFrame, accounts: set[str]) -> pd.Series:
    """Money coming into the subject's accounts per month (pass-through isn't double-counted)."""
    rows = df[df["To_Account"].isin(accounts) & ~df["From_Account"].isin(accounts)]
    if rows.empty:
        return pd.Series(dtype=float)
    month = pd.to_datetime(rows["Timestamp"], errors="coerce").dt.to_period("M")
    return rows["Amount Received"].groupby(month).sum()


def _profile_flags(df, subject, context) -> list[RedFlag]:
    """Checks against the customer baseline (KYC profile and the account's history)."""
    flags: list[RedFlag] = []
    accounts = set(getattr(subject, "accounts", []) or [])
    if not accounts:
        return flags
    volume = _monthly_inflow(df, accounts)
    expected = getattr(subject, "expected_monthly_volume", None)
    if expected and not volume.empty:
        month, peak = volume.idxmax(), volume.max()
        ratio = peak / expected
        if ratio >= 1.5:
            flags.append(RedFlag(
                "PROFILE_MISMATCH", "Activity inconsistent with the customer profile",
                "high" if ratio >= 3 else "medium",
                f"Incoming funds of ${peak:,.2f} in {month.strftime('%B %Y')} are "
                f"{ratio:.1f}× the expected monthly volume of ${expected:,.2f} "
                f"recorded at onboarding.", []))
    if context is not None and not context.empty and not volume.empty:
        baseline = _monthly_inflow(context, accounts)
        if not baseline.empty and baseline.mean() > 0:
            ratio = volume.max() / baseline.mean()
            if ratio >= 2:
                flags.append(RedFlag(
                    "BASELINE_DEVIATION", "Departure from the account's own history", "medium",
                    f"Incoming funds in the flagged period (${volume.max():,.2f} in a month) are "
                    f"{ratio:.1f}× the account's average monthly inflow of "
                    f"${baseline.mean():,.2f} in the unflagged history.", []))
    opened = parse_iso_date(getattr(subject, "account_opened", ""))
    first = pd.to_datetime(df["Timestamp"], errors="coerce").min()
    if opened and pd.notna(first):
        age = (first.date() - opened).days
        if 0 <= age < 90:
            flags.append(RedFlag("NEW_ACCOUNT", "Newly opened account", "medium",
                                 f"The account was opened on {opened.isoformat()}, {age} days "
                                 "before the first flagged transaction.", []))
    return flags


# ── Case-level helpers ───────────────────────────────────────────────────────

def analyse_case(case) -> tuple[Detection, list[RedFlag]]:
    """Detection + red flags for a CaseInput (flagged rows; unflagged = baseline)."""
    flagged = case.flagged()
    detection = detect_typology(flagged)
    flags = detect_red_flags(flagged, case.subject, case.context())
    return detection, flags


def effective_pattern(case, detection: Detection | None) -> str:
    """The typology the narrative is written around: analyst override first."""
    if case.pattern_override:
        return case.pattern_override
    return detection.pattern if detection else "NONE"


def warrants_no_sar(pattern: str, flags: list) -> bool:
    """No typology and no high-severity red flag → the draft should conclude no SAR."""
    high = [f for f in flags if (f.severity if hasattr(f, "severity") else f.get("severity")) == "high"]
    return pattern.upper() in ("NONE", "RANDOM") and not high
