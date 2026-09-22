# Case 006 — CYCLE (5-hop Cycle)

**Pattern:** CYCLE  
**Attempt #:** 249 (of 370)  
**Degree/Hop Info:** Max 5 hops  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 5 |
| Total Amount Paid | $72,750.75 |
| Total Amount Received | $72,750.75 |
| Min Amount | $460.62 |
| Max Amount | $36,052.53 |
| Date Range | 2022/09/07 18:08 → 2022/09/10 01:24 |
| Unique Accounts | 5 |
| Unique Banks | 5 |
| Currencies | Rupee, US Dollar |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8004257C0` | First Bank of Springfield (701) | Corporation #7224 | Sender / Receiver |
| `801F694E0` | Sappo Bancorp (2843) | Corporation #1933 | Sender / Receiver |
| `8049DD1C0` | China Bank #14 (3) | Corporation #30450 | Sender / Receiver |
| `8056BC280` | India Bank #39 (114590) | Sole Proprietorship #31648 | Sender / Receiver |
| `80BB54BC0` | Bank of Laramie (13917) | Corporation #49361 | Sender / Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/07 18:08 | China Bank #14 | `8049DD1C0` | Bank of Laramie | `80BB54BC0` | $460.62 | US Dollar | $460.62 | US Dollar | ACH |
| 2 | 2022/09/09 05:12 | Bank of Laramie | `80BB54BC0` | Sappo Bancorp | `801F694E0` | $485.30 | US Dollar | $485.30 | US Dollar | ACH |
| 3 | 2022/09/09 14:21 | Sappo Bancorp | `801F694E0` | First Bank of Springfield | `8004257C0` | $485.30 | US Dollar | $485.30 | US Dollar | ACH |
| 4 | 2022/09/09 19:21 | First Bank of Springfield | `8004257C0` | India Bank #39 | `8056BC280` | $36,052.53 | Rupee | $36,052.53 | Rupee | ACH |
| 5 | 2022/09/10 01:24 | India Bank #39 | `8056BC280` | China Bank #14 | `8049DD1C0` | $35,267.00 | Rupee | $35,267.00 | Rupee | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, `8049DD1C0`, held by Corporation #30450 at China Bank #14, is both the originating and terminal point of a 5-hop closed transaction loop. Four other accounts — held by two additional corporations, one sole proprietorship, and a further corporation — serve as sequential intermediaries.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 7 and September 10, 2022, a chain of 5 sequential ACH transfers moved through 5 accounts at 5 distinct financial institutions, beginning and ending at the same account, with a combined transaction value of $72,750.75 and a currency shift from US Dollar to Rupee partway through the chain.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
The full loop completed within a 55-hour window, from 2022/09/07 18:08 to 2022/09/10 01:24 — an average of one hop roughly every 11 hours.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The loop traverses institutions associated with the United States, India, and China (First Bank of Springfield, Sappo Bancorp, China Bank #14, India Bank #39, Bank of Laramie), returning to its point of origin at China Bank #14.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Funds returning to their originating account after passing through four intermediary accounts is inconsistent with any known legitimate commercial purpose. Unlike a proportional round-trip, the value returning to the origin account ($35,267.00) is approximately 76 times larger than the amount it originally sent out ($460.62) — the first three hops move near-identical small amounts ($460.62, $485.30, $485.30), while the final two hops, denominated in Rupee rather than US Dollar, move amounts roughly 75 times larger ($36,052.53 and $35,267.00). This sharp value escalation coinciding precisely with a currency change is inconsistent with a simple proportional layering "U-turn" of the same funds (see FATF-XII Report on Money Laundering Typologies 2000-2001, Example 11) and instead suggests the small-value USD hops may have served to establish or test a transaction relationship between accounts, with a separate, substantially larger sum introduced and moved through the same established path once in Rupee. While recurring commercial relationships between counterparties can produce apparent cyclical fund movement, the sharp and unexplained ~76x value increase partway through the loop, combined with the short 55-hour completion window, is inconsistent with a legitimate netting or trade-settlement arrangement, where amounts would typically be consistent with invoiced goods or services rather than escalating disproportionately mid-chain.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
The chain began with three small, closely-matched USD transfers between China Bank #14, Bank of Laramie, and Sappo Bancorp before reaching First Bank of Springfield, at which point the currency and transaction size both changed sharply for the final two hops (First Bank of Springfield → India Bank #39 → China Bank #14) in Rupee. Each account received from exactly one counterparty and sent to exactly one counterparty, maintaining a strict single-path chain throughout.

### Supporting Pattern

<!-- Reference to known typology. Pattern: CYCLE -->
Pattern: CYCLE (5-hop). Structural grounding: FATF-XII Report on Money Laundering Typologies (2000-2001), Example 11 ("U-turn movement of funds"), adapted to account for the value-escalation anomaly noted above, which is not present in the cited example. Per `typology_mapping.md`.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
5 transactions, $72,750.75 cumulative movement, 5 unique accounts across 5 unique banks, 2 currencies (US Dollar, Rupee), ACH format exclusively, September 7–10 2022 (55-hour window), closed loop with ~76x value escalation between origin-side and return-side amounts.
