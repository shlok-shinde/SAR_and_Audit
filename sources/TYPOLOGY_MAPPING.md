# Typology Mapping — IBM AML Patterns to Regulatory/Academic Sources

Maps each of IBM AML's 8 synthetic laundering patterns (HI-Small Patterns.txt) to real-world
regulatory typology sources. Used to ground ChromaDB retrieval content and to write
structurally accurate gold-standard SAR narratives.

Sourcing note: Real SAR narratives are not public. No single regulatory body names all 8 of
IBM's graph-topology patterns individually — some map cleanly to named typologies (structuring,
funnel accounts), others required combining multiple partial sources or pulling from academic
AML-detection literature that uses this exact dataset. Gaps and composite sourcing are noted
explicitly rather than forced into a false 1:1 citation.

---

## All Patterns — Narrative Structure (applies globally)

Source: FFIEC BSA/AML Examination Manual, Appendix L — SAR Quality Guidance
https://bsaaml.ffiec.gov/docs/manual/10_Appendices/13.pdf

Defines the five required narrative elements (who/what/when/where/why) plus modus operandi
("how"). Structural template for every gold-standard narrative regardless of pattern.

---

## Fan-Out

Definition: Single source account disperses funds outward to many destination accounts.
Status: No single dedicated regulatory document. Composite citation required.

- FFIEC Appendix G — Structuring: mechanism definition, breaking down a sum into smaller
	  amounts to evade reporting, same logic applied outbound.
  https://bsaaml.ffiec.gov/manual/Appendices/08
- FATF-XII Typologies (2000-2001), Example 21: case precedent, single launderer using
  multiple foreign nationals to remit funds overseas under reporting thresholds.
  https://www.fincen.gov/system/files/shared/fatftypologie.pdf
- FATF Professional Money Laundering (2018), Money Mule Networks section: structural
  precedent, mule herder distributing funds from one controller to many mule accounts.

Caveat: document explicitly that fan-out is grounded via combined mechanism + case
precedent, not a single named typology.

---

## Fan-In

Source: FinCEN Case Example, July 2014, Case 7
https://www.fincen.gov/system/files/case_example/July2014_Case7.pdf

Real prosecuted case: 140 instances of structuring, small deposits converging into a single
account. Direct structural match.

---

## Cycle

Source: FATF-XII Report on Money Laundering Typologies (2000-2001), Example 11
https://www.fincen.gov/system/files/shared/fatftypologie.pdf

Real fraud case: $90 million moved through companies, returning to a third company owned by
the same Director — explicitly called a "U-turn movement of funds." Direct match.

---

## Scatter-Gather

Source: GARG-AML against Smurfing (Deprez, Baesens, Verdonck, Verbeke, 2025), citing
Altman et al. 2023
https://arxiv.org/html/2506.04292v2

Academic paper tested on IBM AML data. Scatter-gather: money sent from one source to its
destination via multiple money mules (one-to-many-to-one). Most commonly recognized
"smurfing" shape. Technical/structural source — pair with Fan-Out's regulatory sources for
narrative language.

---

## Gather-Scatter

Primary source: FinCEN Advisory FIN-2014-A005 — Funnel Accounts and TBML
https://www.fincen.gov/system/files/advisory/FIN-2014-A005.pdf

FinCEN's own definition: account receives multiple deposits below reporting thresholds,
withdrawn in a different geographic area shortly after. Named typology term ("funnel
account") available for direct citation.

Secondary: GARG-AML paper confirms direction — collecting from multiple accounts into one,
then sending to many destinations.

---

## Stack

Source: FATF Professional Money Laundering (2018), Box 6 — Dark Web Drug Stores case
https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf

Real case: funds moved through "a complex chain of different e-wallets" via automated
transit-panel before reaching destination. Sequential chain matches Stack.

Adaptation note: source uses virtual-currency e-wallets; IBM dataset is bank transactions.
Adapt language to accounts/wires, drop crypto terminology.

---

## Bipartite

Source: APG Typology Report on Trade Based Money Laundering (2012)
https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Trade_Based_ML_APGReport.pdf.coredownload.pdf

Covers related-party structures: transactions revealing links between companies with same
owners/management, requiring collusion at both ends.

Caveat — weakest citation in this set: match is structural, not topical. Source is
trade/goods-based; IBM dataset has no trade dimension. Drop invoice/shipment language, keep
only the structural insight (related account clusters, common control).

---

## Random

Excluded — negative/noise control, not a laundering typology.

---

## Summary Table

| Pattern        | Primary Source                          | Match Quality                        |
|----------------|------------------------------------------|---------------------------------------|
| Fan-Out        | Composite (3 sources)                    | Partial — no single named typology    |
| Fan-In         | FinCEN Case 7                            | Strong                                |
| Cycle          | FATF-XII Example 11                      | Strong                                |
| Scatter-Gather | GARG-AML paper                           | Strong (technical), pair w/ reg. lang |
| Gather-Scatter | FIN-2014-A005                            | Strong                                |
| Stack          | Professional Money Laundering, Box 6     | Strong (adapt terminology)            |
| Bipartite      | APG TBML Report                          | Weak — structural analogy only        |
| Random         | N/A                                      | Excluded                              |