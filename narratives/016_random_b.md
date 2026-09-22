# Case 016 — RANDOM (8-hop Random)

**Pattern:** RANDOM  
**Attempt #:** 179 (of 370)  
**Degree/Hop Info:** Max 8 hops  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 8 |
| Total Amount Paid | $24,677.81 |
| Total Amount Received | $24,677.81 |
| Min Amount | $2,472.05 |
| Max Amount | $4,352.31 |
| Date Range | 2022/09/05 19:55 → 2022/09/09 14:25 |
| Unique Accounts | 9 |
| Unique Banks | 9 |
| Currencies | Australian Dollar, Euro, US Dollar |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8013F90B0` | Mountain Trust Bank (2627) | Partnership #1028 | Sender / Receiver |
| `802748380` | Savings Bank of Sacramento (2991) | Sole Proprietorship #783 | Sender / Receiver |
| `80AC30BC0` | First Bank of New Orleans (21550) | Partnership #3738 | Sender / Receiver |
| `80AD0E740` | Australia Bank #32 (127999) | Corporation #50225 | Receiver |
| `80C0D3710` | Germany Bank #388 (221279) | Corporation #25469 | Sender / Receiver |
| `80D26F0E0` | Spain Bank #992 (17649) | Partnership #5780 | Sender / Receiver |
| `80DF47A40` | National Bank of Tuscon (6276) | Corporation #15413 | Sender / Receiver |
| `80E064980` | First Bank of Huron (117453) | Partnership #44819 | Sender / Receiver |
| `810D87E20` | Italy Bank #2133 (32405) | Sole Proprietorship #26593 | Sender |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/05 19:55 | Italy Bank #2133 | `810D87E20` | National Bank of Tuscon | `80DF47A40` | $3,375.20 | US Dollar | $3,375.20 | US Dollar | ACH |
| 2 | 2022/09/07 04:44 | National Bank of Tuscon | `80DF47A40` | Savings Bank of Sacramento | `802748380` | $3,283.36 | US Dollar | $3,283.36 | US Dollar | ACH |
| 3 | 2022/09/07 17:31 | Savings Bank of Sacramento | `802748380` | First Bank of New Orleans | `80AC30BC0` | $3,000.43 | US Dollar | $3,000.43 | US Dollar | ACH |
| 4 | 2022/09/08 02:29 | First Bank of New Orleans | `80AC30BC0` | First Bank of Huron | `80E064980` | $2,766.74 | US Dollar | $2,766.74 | US Dollar | ACH |
| 5 | 2022/09/08 08:45 | First Bank of Huron | `80E064980` | Mountain Trust Bank | `8013F90B0` | $2,896.71 | US Dollar | $2,896.71 | US Dollar | ACH |
| 6 | 2022/09/08 14:50 | Mountain Trust Bank | `8013F90B0` | Spain Bank #992 | `80D26F0E0` | $2,472.05 | Euro | $2,472.05 | Euro | ACH |
| 7 | 2022/09/09 03:38 | Spain Bank #992 | `80D26F0E0` | Germany Bank #388 | `80C0D3710` | $2,531.01 | Euro | $2,531.01 | Euro | ACH |
| 8 | 2022/09/09 14:25 | Germany Bank #388 | `80C0D3710` | Australia Bank #32 | `80AD0E740` | $4,352.31 | Australian Dollar | $4,352.31 | Australian Dollar | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
This case involves a sequential chain of eight ACH transfers passing through nine accounts, held by a mix of partnerships, corporations, and sole proprietorships. Each account in the chain, apart from the first and last, both received one inbound transfer and sent one outbound transfer.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 5 and September 9, 2022, funds moved through a single linear sequence of eight transfers, originating at account 810D87E20 (Italy Bank #2133) and terminating at account 80AD0E740 (Australia Bank #32). Transaction amounts, once normalized for currency, ranged from approximately $2,545 to $3,375 across all eight hops.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
The chain completed over approximately 90.5 hours, from September 5, 2022, 19:55 to September 9, 2022, 14:25 — an average of roughly 12.9 hours between hops, with no unusual clustering or acceleration at any point in the sequence.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The chain traverses institutions in at least five countries — Italy, the United States, Spain, Germany, and Australia, with three separate hops occurring between distinct US institutions — with each hop moving to a different institution and no institution appearing more than once.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Structural analysis does not support a typology match for this transaction chain. The chain shows no return-to-origin at any point, ruling out CYCLE. No single account receives from multiple distinct sources, ruling out FAN-IN and GATHER-SCATTER's convergence phase. No single account disperses to multiple distinct destinations, ruling out FAN-OUT and SCATTER-GATHER's dispersal phase. There is no evidence of parallel, structurally identical chains operating alongside this one within the same window, ruling out STACK. There is no disjoint two-group transaction set with multiple simultaneous pairs, ruling out BIPARTITE. Currency-normalized transaction values are tightly and consistently banded (approximately $2,545–$3,375 across all eight hops, including both non-USD-denominated legs once properly converted), showing none of the threshold-avoidance clustering, disproportionate outliers, or inconsistent implied-conversion-rate patterns identified as red flags in other cases reviewed under this project's typology mapping. Timing between hops is regular and unremarkable, with no compression or acceleration suggesting coordinated urgency. On the totality of this structural review, this transaction chain does not correspond to any of the seven laundering typologies mapped in this project and does not independently warrant a Suspicious Activity Report.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Each account in the chain received a single inbound transfer and forwarded a single outbound transfer to a different account at a different institution, in sequence, until reaching the final destination. No account received from or sent to more than one counterparty. The chain does not return to its point of origin at any point.

### Supporting Pattern

<!-- Reference to known typology. Pattern: RANDOM -->
RANDOM (no regulatory typology grounding). This case is included as a negative control, consistent with its designation in the source dataset as a structurally unremarkable multi-hop chain included specifically to test whether pattern classification correctly withholds a typology match rather than over-flagging structurally plausible-looking but ultimately unremarkable activity.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
8 transactions across 9 unique accounts and 9 unique banks. Currency-normalized transaction values range approximately $2,545–$3,375, a tight and unremarkable band. September 5–9, 2022 (90.5-hour window, average 12.9 hours between hops, no timing anomalies).
