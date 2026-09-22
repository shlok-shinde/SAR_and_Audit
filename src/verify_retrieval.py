"""
verify_retrieval.py — Test ChromaDB retrieval quality against gold-standard cases.

For each of the 16 gold-standard SAR narratives, queries ChromaDB with both:
  A) Pattern-label queries (e.g., "fan-out structuring")
  B) Transaction-description queries (natural language)

Checks whether the correct typology source document appears in top-k results.
"""

import chromadb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "typology_docs"

# ── Gold-standard case definitions ───────────────────────────────────────────
# Each case: (case_id, pattern_type, expected_source_files, label_query, description_query)
GOLD_STANDARD_CASES = [
    {
        "case": "001",
        "pattern": "FAN-OUT",
        "expected_sources": [
            "Money laundering typologies 2000-2001(for cycle).pdf",  # FATF-XII has Example 21
            "Professional-Money-Laundering(for stacks).pdf",  # has money mule networks
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "fan-out structuring dispersal of funds from single account to multiple accounts",
        "description_query": "A single account sent 16 separate ACH transfers to 16 different accounts across 11 countries over 4 days, with amounts ranging from $300 to $835,000 in 5 different currencies.",
    },
    {
        "case": "002",
        "pattern": "FAN-OUT",
        "expected_sources": [
            "Money laundering typologies 2000-2001(for cycle).pdf",
            "Professional-Money-Laundering(for stacks).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "fan-out structuring dispersal of funds from single account to multiple accounts",
        "description_query": "A single account sent 10 ACH transfers to 10 different accounts at only 6 banks, with 3 transfers going to accounts at the same institution.",
    },
    {
        "case": "003",
        "pattern": "FAN-IN",
        "expected_sources": [
            "July2014_Case7(for fan-in).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "fan-in aggregation convergence of funds from multiple accounts into single account structuring",
        "description_query": "16 different accounts across 12 countries sent ACH transfers to a single account over 5 days, with amounts below the $10,000 CTR reporting threshold.",
    },
    {
        "case": "004",
        "pattern": "FAN-IN",
        "expected_sources": [
            "July2014_Case7(for fan-in).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "fan-in aggregation convergence of funds into single account structuring deposits",
        "description_query": "8 accounts from 6 banks sent transfers to a single sole proprietorship account, with 7 of 8 amounts below the $10,000 CTR reporting threshold.",
    },
    {
        "case": "005",
        "pattern": "CYCLE",
        "expected_sources": [
            "Money laundering typologies 2000-2001(for cycle).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "cycle circular movement of funds returning to origin U-turn round-trip layering",
        "description_query": "Funds moved through 13 accounts across 5 currencies in a circular chain, returning to the originating account after 10 hops over 7 days.",
    },
    {
        "case": "006",
        "pattern": "CYCLE",
        "expected_sources": [
            "Money laundering typologies 2000-2001(for cycle).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "cycle circular movement of funds returning to origin U-turn round-trip",
        "description_query": "A circular chain of 5 transfers across 5 accounts returned funds to the originating account, with escalating values at each hop suggesting test-then-exploit behavior.",
    },
    {
        "case": "007",
        "pattern": "GATHER-SCATTER",
        "expected_sources": [
            "FIN-2014-A005(for gather-scatter).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "gather-scatter funnel account aggregation then dispersal consolidation and redistribution",
        "description_query": "13 accounts sent sub-threshold USD transfers into a single account, which then redistributed funds outward to 15 accounts across 7 currencies including one disproportionately large transfer.",
    },
    {
        "case": "008",
        "pattern": "GATHER-SCATTER",
        "expected_sources": [
            "FIN-2014-A005(for gather-scatter).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "gather-scatter funnel account aggregation then dispersal consolidation",
        "description_query": "5 accounts sent transfers into a single account, which then redistributed to 3 different accounts, acting as a funnel point for consolidation and redistribution.",
    },
    {
        "case": "009",
        "pattern": "SCATTER-GATHER",
        "expected_sources": [
            "GARG-AML paper(for scatter-gather).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "scatter-gather smurfing one source to one destination via multiple intermediary money mules",
        "description_query": "A single account dispersed funds to 16 intermediary accounts, each of which forwarded a Yen-denominated payment to a single destination account, with implied exchange rates varying by 48% across supposedly simultaneous conversions.",
    },
    {
        "case": "010",
        "pattern": "SCATTER-GATHER",
        "expected_sources": [
            "GARG-AML paper(for scatter-gather).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "scatter-gather smurfing dispersal through intermediaries to single destination",
        "description_query": "A single account sent 11 payments to 11 intermediary accounts, each of which forwarded a Euro payment to the same destination, with same-currency transfers showing inconsistent value ratios between 0.877 and 1.009.",
    },
    {
        "case": "011",
        "pattern": "STACK",
        "expected_sources": [
            "Professional-Money-Laundering(for stacks).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "stack parallel chain layering sequential hops through intermediary accounts e-wallet transit",
        "description_query": "15 structurally identical two-hop chains operated in parallel over 93 hours, each moving funds from an originating account through one intermediary to a destination, with no shared accounts between chains.",
    },
    {
        "case": "012",
        "pattern": "STACK",
        "expected_sources": [
            "Professional-Money-Laundering(for stacks).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "stack parallel chain layering through intermediary accounts including cryptocurrency Bitcoin",
        "description_query": "5 parallel two-hop chains including one Bitcoin transaction of $0.37 followed by a $3,749 Euro transfer from a different account at the same crypto institution, with 3 chains showing same-currency value increases.",
    },
    {
        "case": "013",
        "pattern": "BIPARTITE",
        "expected_sources": [
            "Trade_Based_ML_APGReport(for bipartite).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "bipartite related-party transaction pairs disjoint groups coordinated transfers",
        "description_query": "15 single-hop transfers between 15 entirely distinct account pairs completed within 34.5 hours, with two destination accounts sharing the same bank and all amounts falling in a narrow value band once currency-normalized.",
    },
    {
        "case": "014",
        "pattern": "BIPARTITE",
        "expected_sources": [
            "Trade_Based_ML_APGReport(for bipartite).pdf",
            "TYPOLOGY_MAPPING.md",
        ],
        "label_query": "bipartite related-party transaction pairs disjoint groups coordinated transfers trade-based",
        "description_query": "8 single-hop transfers between 8 distinct account pairs in a 33.65-hour window, with two unrelated customers of the same bank appearing on opposite sides of the transaction set.",
    },
    {
        "case": "015",
        "pattern": "RANDOM",
        "expected_sources": [],  # negative control — should NOT match any specific typology
        "label_query": "random unstructured transaction chain no typology match",
        "description_query": "A sequential chain of 11 transfers through 12 accounts over 80 hours with consistent value banding and regular timing between hops, showing no structural pattern matching any known laundering typology.",
    },
    {
        "case": "016",
        "pattern": "RANDOM",
        "expected_sources": [],  # negative control
        "label_query": "random unstructured transaction chain no typology match",
        "description_query": "A sequential chain of 8 transfers through 9 accounts over 90 hours with tight value banding and no structural features matching known laundering typologies.",
    },
]


# ── Retrieval Functions ──────────────────────────────────────────────────────
def query_chromadb(
    query_text: str,
    n_results: int = 5,
    pattern_filter: str | None = None,
) -> list[dict]:
    """
    Query ChromaDB and return top-k results with metadata and distances.
    """
    from embed_typology_docs import get_embedding_function

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = get_embedding_function()
    collection = client.get_collection(COLLECTION_NAME, embedding_function=ef)

    where_filter = None
    if pattern_filter:
        where_filter = {
            "$or": [
                {"pattern_type": pattern_filter},
                {"pattern_type": "ALL"},
            ]
        }

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i],
            "source_file": results["metadatas"][0][i]["source_file"],
            "pattern_type": results["metadatas"][0][i]["pattern_type"],
            "page_number": results["metadatas"][0][i]["page_number"],
            "text_preview": results["documents"][0][i][:120] + "...",
        })
    return output


def check_retrieval(case: dict, query_type: str = "label") -> dict:
    """
    Run retrieval for a single case and check if expected sources appear.

    Returns dict with: case, pattern, query_type, top1_source, top1_distance,
                        expected_in_top5, all_sources
    """
    query = case["label_query"] if query_type == "label" else case["description_query"]
    results = query_chromadb(query, n_results=5)

    retrieved_sources = [r["source_file"] for r in results]
    expected = case["expected_sources"]

    if not expected:
        # RANDOM — success = no specific typology source in top results
        # (TYPOLOGY_MAPPING.md and FFIEC Appendix L are acceptable since they're generic)
        specific_sources = [
            s for s in retrieved_sources
            if s not in ("TYPOLOGY_MAPPING.md", "FFIEC Appendix L.pdf")
        ]
        in_top5 = len(specific_sources) == 0 or all(
            r["distance"] > 0.5 for r in results if r["source_file"] in specific_sources
        )
    else:
        in_top5 = any(s in retrieved_sources for s in expected)

    return {
        "case": case["case"],
        "pattern": case["pattern"],
        "query_type": query_type,
        "top1_source": results[0]["source_file"] if results else "NONE",
        "top1_distance": results[0]["distance"] if results else 999,
        "expected_in_top5": in_top5,
        "all_sources": retrieved_sources,
        "all_distances": [r["distance"] for r in results],
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def run_verification() -> None:
    """Run retrieval verification for all 16 gold-standard cases."""
    print("=" * 90)
    print("RETRIEVAL QUALITY VERIFICATION — All 16 Gold-Standard Cases")
    print("=" * 90)

    for query_type in ["label", "description"]:
        print(f"\n{'─' * 90}")
        print(f"Query Type: {query_type.upper()}")
        print(f"{'─' * 90}")
        print(f"{'Case':<6} {'Pattern':<18} {'Top-1 Source':<50} {'Dist':>6} {'Top-5?':>6}")
        print(f"{'─'*6} {'─'*18} {'─'*50} {'─'*6} {'─'*6}")

        pass_count = 0
        for case in GOLD_STANDARD_CASES:
            result = check_retrieval(case, query_type)
            status = "✅" if result["expected_in_top5"] else "❌"
            if result["expected_in_top5"]:
                pass_count += 1

            # Truncate source name for display
            source_display = result["top1_source"][:48]
            print(
                f"{result['case']:<6} {result['pattern']:<18} "
                f"{source_display:<50} {result['top1_distance']:>6.3f} {status:>6}"
            )

        print(f"\n  Pass rate: {pass_count}/{len(GOLD_STANDARD_CASES)}")

    # Detailed view for RANDOM cases
    print(f"\n{'=' * 90}")
    print("RANDOM CASE ANALYSIS (Negative Controls)")
    print(f"{'=' * 90}")
    for case in GOLD_STANDARD_CASES:
        if case["pattern"] != "RANDOM":
            continue
        for qt in ["label", "description"]:
            query = case["label_query"] if qt == "label" else case["description_query"]
            results = query_chromadb(query, n_results=5)
            print(f"\nCase {case['case']} ({qt} query):")
            for r in results:
                print(f"  dist={r['distance']:.3f}  {r['source_file']:<55} p.{r['page_number']}")

    print("\nDone.")


if __name__ == "__main__":
    run_verification()
