# Case 008 — GATHER-SCATTER (10-degree Gather-Scatter)

**Pattern:** GATHER-SCATTER  
**Attempt #:** 92 (of 370)  
**Degree/Hop Info:** Max 10-degree Fan-In  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 21 |
| Total Amount Paid | $1,737,436.80 |
| Total Amount Received | $1,737,436.80 |
| Min Amount | $743.91 |
| Max Amount | $1,535,493.32 |
| Date Range | 2022/09/03 05:28 → 2022/09/10 02:09 |
| Unique Accounts | 22 |
| Unique Banks | 21 |
| Currencies | Euro, Swiss Franc, UK Pound, US Dollar, Yen |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8002B5EE0` | National Bank of Pittsburgh (220) | Sole Proprietorship #569 | Sender |
| `800360060` | Italy Bank #49 (1547) | Sole Proprietorship #3072 | Receiver |
| `802455070` | Brownstone Trust Bank (21258) | Corporation #3478 | Receiver |
| `8028AC420` | Spain Bank #64 (3123) | Corporation #41251 | Sender |
| `8045A70E0` | Japan Bank #24 (10656) | Sole Proprietorship #31280 | Receiver |
| `8057BA770` | Savings Bank of Sacramento (2991) | Partnership #18730 | Sender |
| `805E56740` | India Bank #76 (214050) | Partnership #32636 | Sender |
| `806689160` | National Bank of Denver (8805) | Corporation #8677 | Sender |
| `8066D7B00` | Spruce Cooperative Bank (22164) | Partnership #22550 | Sender |
| `806FA9C10` | Russia Bank #16 (9) | Sole Proprietorship #32941 | Sender |
| `808C1A610` | UK Bank #61 (122332) | Sole Proprietorship #51032 | Receiver |
| `808E06810` | First Bank of Los Angeles (13264) | Corporation #1568 | Receiver |
| `80AA05290` | China Bank #340 (21615) | Corporation #28308 | Sender |
| `80B503710` | Finland Bank #0 (11) | Corporation #45829 | Receiver |
| `80B828DE0` | Willows Thrift (14099) | Sole Proprietorship #16905 | Sender |
| `80B91CD20` | Italy Bank #17 (13083) | Sole Proprietorship #55144 | Receiver |
| `80CA4D110` | Savings Bank of Huron (3420) | Corporation #47311 | Receiver |
| `80DA5FC60` | Brownstone Trust Bank (21258) | Sole Proprietorship #43540 | Receiver |
| `80EB1E930` | Switzerland Bank #51 (139342) | Corporation #2477 | Sender / Receiver |
| `80ED75AC0` | Germany Bank #286 (26463) | Partnership #28196 | Sender |
| `8110882E0` | Spain Bank #439 (224555) | Sole Proprietorship #23645 | Receiver |
| `811C16680` | Oasis Community Bank (117299) | Sole Proprietorship #20115 | Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/03 05:28 | Spain Bank #64 | `8028AC420` | Switzerland Bank #51 | `80EB1E930` | $1,082.12 | Swiss Franc | $1,082.12 | Swiss Franc | ACH |
| 2 | 2022/09/04 06:05 | India Bank #76 | `805E56740` | Switzerland Bank #51 | `80EB1E930` | $10,457.51 | Swiss Franc | $10,457.51 | Swiss Franc | ACH |
| 3 | 2022/09/04 10:41 | Spruce Cooperative Bank | `8066D7B00` | Switzerland Bank #51 | `80EB1E930` | $5,928.97 | Swiss Franc | $5,928.97 | Swiss Franc | ACH |
| 4 | 2022/09/04 11:30 | National Bank of Pittsburgh | `8002B5EE0` | Switzerland Bank #51 | `80EB1E930` | $18,102.93 | Swiss Franc | $18,102.93 | Swiss Franc | ACH |
| 5 | 2022/09/05 01:28 | National Bank of Denver | `806689160` | Switzerland Bank #51 | `80EB1E930` | $13,631.38 | Swiss Franc | $13,631.38 | Swiss Franc | ACH |
| 6 | 2022/09/05 11:54 | Germany Bank #286 | `80ED75AC0` | Switzerland Bank #51 | `80EB1E930` | $14,619.24 | Swiss Franc | $14,619.24 | Swiss Franc | ACH |
| 7 | 2022/09/06 07:36 | Savings Bank of Sacramento | `8057BA770` | Switzerland Bank #51 | `80EB1E930` | $743.91 | Swiss Franc | $743.91 | Swiss Franc | ACH |
| 8 | 2022/09/06 12:47 | Willows Thrift | `80B828DE0` | Switzerland Bank #51 | `80EB1E930` | $10,209.43 | Swiss Franc | $10,209.43 | Swiss Franc | ACH |
| 9 | 2022/09/06 17:24 | China Bank #340 | `80AA05290` | Switzerland Bank #51 | `80EB1E930` | $13,837.79 | Swiss Franc | $13,837.79 | Swiss Franc | ACH |
| 10 | 2022/09/06 21:55 | Russia Bank #16 | `806FA9C10` | Switzerland Bank #51 | `80EB1E930` | $7,645.05 | Swiss Franc | $7,645.05 | Swiss Franc | ACH |
| 11 | 2022/09/06 04:09 | Switzerland Bank #51 | `80EB1E930` | Brownstone Trust Bank | `80DA5FC60` | $1,274.98 | US Dollar | $1,274.98 | US Dollar | ACH |
| 12 | 2022/09/06 04:50 | Switzerland Bank #51 | `80EB1E930` | Savings Bank of Huron | `80CA4D110` | $5,568.82 | US Dollar | $5,568.82 | US Dollar | ACH |
| 13 | 2022/09/06 06:15 | Switzerland Bank #51 | `80EB1E930` | Brownstone Trust Bank | `802455070` | $15,290.92 | US Dollar | $15,290.92 | US Dollar | ACH |
| 14 | 2022/09/06 14:09 | Switzerland Bank #51 | `80EB1E930` | Finland Bank #0 | `80B503710` | $1,854.59 | Euro | $1,854.59 | Euro | ACH |
| 15 | 2022/09/08 11:19 | Switzerland Bank #51 | `80EB1E930` | Japan Bank #24 | `8045A70E0` | $1,535,493.32 | Yen | $1,535,493.32 | Yen | ACH |
| 16 | 2022/09/08 14:11 | Switzerland Bank #51 | `80EB1E930` | First Bank of Los Angeles | `808E06810` | $17,625.65 | US Dollar | $17,625.65 | US Dollar | ACH |
| 17 | 2022/09/09 05:18 | Switzerland Bank #51 | `80EB1E930` | Spain Bank #439 | `8110882E0` | $14,635.16 | Euro | $14,635.16 | Euro | ACH |
| 18 | 2022/09/09 06:01 | Switzerland Bank #51 | `80EB1E930` | Italy Bank #49 | `800360060` | $6,398.44 | Euro | $6,398.44 | Euro | ACH |
| 19 | 2022/09/09 16:51 | Switzerland Bank #51 | `80EB1E930` | Italy Bank #17 | `80B91CD20` | $15,757.84 | Euro | $15,757.84 | Euro | ACH |
| 20 | 2022/09/09 17:03 | Switzerland Bank #51 | `80EB1E930` | Oasis Community Bank | `811C16680` | $19,845.21 | US Dollar | $19,845.21 | US Dollar | ACH |
| 21 | 2022/09/10 02:09 | Switzerland Bank #51 | `80EB1E930` | UK Bank #61 | `808C1A610` | $7,433.54 | UK Pound | $7,433.54 | UK Pound | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, 80EB1E930, held by Corporation #2477 at Switzerland Bank #51, served as the consolidation and dispersal point for the full 21-transaction sequence.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 3 and September 10, 2022, account 80EB1E930 received 10 inbound ACH transfers, all denominated in Swiss Franc, from 10 distinct originating accounts, totaling approximately $96,258.33 and ranging from $743.91 to $18,102.93. The account then initiated 11 outbound ACH transfers to 11 distinct beneficiary accounts across five currencies (US Dollar, Euro, Yen, UK Pound, and one further Swiss Franc-adjacent transfer), with individual transfer sizes broadly comparable to the inbound range once currency scale is accounted for.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
The full sequence spanned roughly 164.7 hours (September 3, 05:28 to September 10, 02:09). The gather and scatter phases overlapped rather than proceeding strictly in sequence: the first outbound transfer (September 6, 04:09) occurred before four of the ten inbound transfers had yet arrived.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
Inbound funds originated from accounts in six countries (Spain, India, the United States, Germany, China, and Russia). Outbound funds were dispersed to accounts in six countries (the United States, Finland, Japan, Spain, Italy, and the United Kingdom), including two separate transfers to different account numbers at the same institution, Brownstone Trust Bank.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The consolidation of ten distinct, uniformly Swiss Franc-denominated deposits from six countries into a single account, followed by dispersal to eleven accounts across six countries and five currencies within roughly a week, is consistent with funnel-account behavior in which fragmented deposits are aggregated before redistribution to obscure origin. Two of the eleven outbound transfers route to different account numbers at the same receiving institution (Brownstone Trust Bank), a concentration pattern inconsistent with genuinely independent counterparties. The single Yen-denominated outbound transfer ($1,535,493.32) is not treated here as a value anomaly — at approximate market exchange rates it is broadly comparable in scale to the account's other outbound transfers, unlike a true disproportionate outlier (see FinCEN Advisory FIN-2014-A005, Funnel Accounts and TBML; structural confirmation via Deprez et al. 2025, GARG-AML). While this pattern could plausibly reflect a legitimate corporate treasury or cash-pooling arrangement consolidating receivables before distributing them to affiliated entities, the absence of any documented intercompany agreement, combined with the repeated use of separate account numbers at a single receiving institution, is inconsistent with a standard treasury consolidation structure.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Ten unrelated sending accounts, spanning six countries and no shared receiving institution among themselves, independently transferred Swiss Franc-denominated amounts into the subject account over roughly four days. The subject account then redistributed funds outward across eleven accounts in five currencies, including two transfers routed to distinct accounts at a single institution — consistent with the account functioning as a currency-consolidation and redistribution point.

### Supporting Pattern

<!-- Reference to known typology. Pattern: GATHER-SCATTER -->
Pattern: GATHER-SCATTER (10-in / 11-out). Structural grounding: FinCEN Advisory FIN-2014-A005 (Funnel Accounts and TBML); Deprez, Baesens, Verdonck, Verbeke (2025), GARG-AML against Smurfing, citing Altman et al. 2023. Per typology_mapping.md.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
21 transactions total (10 inbound, 11 outbound); inbound total ≈ $96,258.33 (single currency, CHF); outbound total spans five currencies with no genuine value outlier once currency scale is accounted for. 22 unique accounts, 21 unique banks, September 3–10, 2022 (164.7-hour window, gather and scatter phases overlapping on September 6).
