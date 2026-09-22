# Case 015 — RANDOM (11-hop Random)

**Pattern:** RANDOM  
**Attempt #:** 329 (of 370)  
**Degree/Hop Info:** Max 11 hops  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 11 |
| Total Amount Paid | $202,297.59 |
| Total Amount Received | $202,297.59 |
| Min Amount | $2,008.50 |
| Max Amount | $177,998.05 |
| Date Range | 2022/09/09 21:29 → 2022/09/13 06:36 |
| Unique Accounts | 12 |
| Unique Banks | 12 |
| Currencies | Canadian Dollar, Euro, Rupee, US Dollar |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8000FD100` | Finland Bank #0 (11) | Partnership #23254 | Sender / Receiver |
| `800DCD640` | First Bank of the North (21575) | Partnership #2246 | Sender |
| `802B7F0F0` | Hilltop Trust Bank (26024) | Partnership #6105 | Sender / Receiver |
| `8054C12F0` | National Bank of Arkadelphia (8798) | Corporation #43739 | Sender / Receiver |
| `80598ED20` | India Bank #298 (215186) | Sole Proprietorship #44753 | Sender / Receiver |
| `806ACD410` | Italy Bank #685 (10404) | Sole Proprietorship #45591 | Sender / Receiver |
| `8092F0090` | Canada Bank #4 (225215) | Partnership #36102 | Sender / Receiver |
| `8093EFCC0` | Germany Bank #76 (27140) | Corporation #38535 | Sender / Receiver |
| `809BEDF40` | Savings Bank of Phoenix (16031) | Sole Proprietorship #5712 | Sender / Receiver |
| `809FCC180` | Golden Thrift (4503) | Corporation #13973 | Sender / Receiver |
| `80AB23890` | France Bank #477 (120691) | Corporation #22693 | Receiver |
| `80ABDE970` | Spain Bank #12 (26860) | Sole Proprietorship #45986 | Sender / Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/09 21:29 | First Bank of the North | `800DCD640` | Hilltop Trust Bank | `802B7F0F0` | $2,463.18 | US Dollar | $2,463.18 | US Dollar | ACH |
| 2 | 2022/09/10 14:11 | Hilltop Trust Bank | `802B7F0F0` | Spain Bank #12 | `80ABDE970` | $2,063.96 | Euro | $2,063.96 | Euro | ACH |
| 3 | 2022/09/10 19:57 | Spain Bank #12 | `80ABDE970` | Savings Bank of Phoenix | `809BEDF40` | $2,656.67 | US Dollar | $2,656.67 | US Dollar | ACH |
| 4 | 2022/09/11 04:44 | Savings Bank of Phoenix | `809BEDF40` | Canada Bank #4 | `8092F0090` | $3,504.95 | Canadian Dollar | $3,504.95 | Canadian Dollar | ACH |
| 5 | 2022/09/11 06:23 | Canada Bank #4 | `8092F0090` | India Bank #298 | `80598ED20` | $177,998.05 | Rupee | $177,998.05 | Rupee | ACH |
| 6 | 2022/09/11 08:24 | India Bank #298 | `80598ED20` | National Bank of Arkadelphia | `8054C12F0` | $2,423.59 | US Dollar | $2,423.59 | US Dollar | ACH |
| 7 | 2022/09/11 16:00 | National Bank of Arkadelphia | `8054C12F0` | Germany Bank #76 | `8093EFCC0` | $2,486.79 | Euro | $2,486.79 | Euro | ACH |
| 8 | 2022/09/11 18:44 | Germany Bank #76 | `8093EFCC0` | Finland Bank #0 | `8000FD100` | $2,266.17 | Euro | $2,266.17 | Euro | ACH |
| 9 | 2022/09/12 07:53 | Finland Bank #0 | `8000FD100` | Italy Bank #685 | `806ACD410` | $2,072.21 | Euro | $2,072.21 | Euro | ACH |
| 10 | 2022/09/12 11:23 | Italy Bank #685 | `806ACD410` | Golden Thrift | `809FCC180` | $2,353.52 | US Dollar | $2,353.52 | US Dollar | ACH |
| 11 | 2022/09/13 06:36 | Golden Thrift | `809FCC180` | France Bank #477 | `80AB23890` | $2,008.50 | Euro | $2,008.50 | Euro | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
This case involves a sequential chain of eleven ACH transfers passing through twelve accounts, held by a mix of partnerships, corporations, and sole proprietorships. Each account in the chain, apart from the first and last, both received one inbound transfer and sent one outbound transfer.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 9 and September 13, 2022, funds moved through a single linear sequence of eleven transfers, originating at account 800DCD640 (First Bank of the North) and terminating at account 80AB23890 (France Bank #477). Transaction amounts, once normalized for currency, ranged from approximately $2,008.50 to $3,504.95, with one Rupee-denominated transfer ($177,998.05 face value, approximately $2,140 currency-adjusted) falling within the same range once converted.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
The chain completed over approximately 80.2 hours, from September 9, 2022, 21:29 to September 13, 2022, 06:36 — an average of roughly 7.3 hours between hops, with no unusual clustering or acceleration at any point in the sequence.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The chain traverses institutions in at least eight countries — the United States, Spain, Canada, India, Germany, Finland, Italy, and France — with each hop moving to a different institution and no institution appearing more than once.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Structural analysis does not support a typology match for this transaction chain. The chain shows no return-to-origin at any point, ruling out CYCLE. No single account receives from multiple distinct sources, ruling out FAN-IN and GATHER-SCATTER's convergence phase. No single account disperses to multiple distinct destinations, ruling out FAN-OUT and SCATTER-GATHER's dispersal phase. There is no evidence of parallel, structurally identical chains operating alongside this one within the same window, ruling out STACK. There is no disjoint two-group transaction set with multiple simultaneous pairs, ruling out BIPARTITE. Currency-normalized transaction values are tightly and consistently banded (approximately $2,008–$3,505 across all eleven hops, including the one large-face-value Rupee transfer once properly converted), showing none of the threshold-avoidance clustering, disproportionate outliers, or inconsistent implied-conversion-rate patterns identified as red flags in other cases reviewed under this project's typology mapping. Timing between hops is regular and unremarkable, with no compression or acceleration suggesting coordinated urgency. On the totality of this structural review, this transaction chain does not correspond to any of the seven laundering typologies mapped in this project and does not independently warrant a Suspicious Activity Report.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Each account in the chain received a single inbound transfer and forwarded a single outbound transfer to a different account at a different institution, in sequence, until reaching the final destination. No account received from or sent to more than one counterparty. The chain does not return to its point of origin at any point.

### Supporting Pattern

<!-- Reference to known typology. Pattern: RANDOM -->
RANDOM (no regulatory typology grounding). This case is included as a negative control, consistent with its designation in the source dataset as a structurally unremarkable multi-hop chain included specifically to test whether pattern classification correctly withholds a typology match rather than over-flagging structurally plausible-looking but ultimately unremarkable activity.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
11 transactions across 12 unique accounts and 12 unique banks. Currency-normalized transaction values range approximately $2,008–$3,505, a tight and unremarkable band; the file's raw face-value figures ($202,297.59 total, $177,998.05 maximum) are inflated by one unconverted Rupee-denominated transaction and do not reflect a genuine value outlier once currency-adjusted. September 9–13, 2022 (80.2-hour window, average 7.3 hours between hops, no timing anomalies).
