# Case 009 — SCATTER-GATHER (32-tx Scatter-Gather)

**Pattern:** SCATTER-GATHER  
**Attempt #:** 334 (of 370)  
**Degree/Hop Info:** N/A  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 32 |
| Total Amount Paid | $267,135,089.28 |
| Total Amount Received | $267,135,089.28 |
| Min Amount | $1,892.73 |
| Max Amount | $243,308,041.20 |
| Date Range | 2022/09/10 02:46 → 2022/09/13 21:42 |
| Unique Accounts | 18 |
| Unique Banks | 18 |
| Currencies | Euro, Mexican Peso, Ruble, Rupee, US Dollar, Yen |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8001694F0` | Germany Bank #18 (23) | Corporation #40245 | Sender / Receiver |
| `803C62630` | Italy Bank #6 (16643) | Partnership #24172 | Sender / Receiver |
| `8040AE4F0` | Germany Bank #7 (7548) | Partnership #28955 | Sender |
| `8041293F0` | Japan Bank #50 (210690) | Corporation #29525 | Sender / Receiver |
| `80465E020` | Japan Bank #52 (11128) | Corporation #29863 | Receiver |
| `8056D24A0` | Germany Bank #234 (14663) | Sole Proprietorship #24041 | Sender / Receiver |
| `805990DF0` | China Bank #14 (3) | Partnership #39325 | Sender / Receiver |
| `805F23670` | India Bank #16 (113304) | Partnership #33499 | Sender / Receiver |
| `8061AD3B0` | Russia Bank #16 (9) | Partnership #33830 | Sender / Receiver |
| `8062E7A30` | Belgium Bank #1228 (213137) | Sole Proprietorship #27047 | Sender / Receiver |
| `80780EAF0` | First Bank of Harrisburg (15040) | Sole Proprietorship #1440 | Sender / Receiver |
| `80A42A870` | National Bank of the East (12) | Partnership #44561 | Sender / Receiver |
| `80A66B910` | Belgium Bank #152 (16254) | Corporation #38502 | Sender / Receiver |
| `80A716810` | Plateau Bank (125699) | Partnership #5333 | Sender / Receiver |
| `80AE6EAD0` | National Bank of Pittsburgh (220) | Partnership #3923 | Sender / Receiver |
| `80C136480` | Flagstone Community Bank (115915) | Sole Proprietorship #48654 | Sender / Receiver |
| `80C54A950` | Germany Bank #92 (15055) | Sole Proprietorship #55147 | Sender / Receiver |
| `80C95D120` | Sea Bank (2845) | Corporation #15193 | Sender / Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/10 02:46 | Germany Bank #7 | `8040AE4F0` | Flagstone Community Bank | `80C136480` | $2,232,050.16 | US Dollar | $2,232,050.16 | US Dollar | ACH |
| 2 | 2022/09/12 07:57 | Flagstone Community Bank | `80C136480` | Japan Bank #52 | `80465E020` | $243,308,041.20 | Yen | $243,308,041.20 | Yen | ACH |
| 3 | 2022/09/10 10:49 | Germany Bank #7 | `8040AE4F0` | Sea Bank | `80C95D120` | $5,925.62 | US Dollar | $5,925.62 | US Dollar | ACH |
| 4 | 2022/09/12 10:54 | Sea Bank | `80C95D120` | Japan Bank #52 | `80465E020` | $512,183.03 | Yen | $512,183.03 | Yen | ACH |
| 5 | 2022/09/10 11:14 | Germany Bank #7 | `8040AE4F0` | National Bank of Pittsburgh | `80AE6EAD0` | $19,841.51 | US Dollar | $19,841.51 | US Dollar | ACH |
| 6 | 2022/09/12 11:51 | National Bank of Pittsburgh | `80AE6EAD0` | Japan Bank #52 | `80465E020` | $1,727,893.08 | Yen | $1,727,893.08 | Yen | ACH |
| 7 | 2022/09/10 12:03 | Germany Bank #7 | `8040AE4F0` | Germany Bank #234 | `8056D24A0` | $13,478.31 | Euro | $13,478.31 | Euro | ACH |
| 8 | 2022/09/12 17:06 | Germany Bank #234 | `8056D24A0` | Japan Bank #52 | `80465E020` | $1,664,651.67 | Yen | $1,664,651.67 | Yen | ACH |
| 9 | 2022/09/10 13:17 | Germany Bank #7 | `8040AE4F0` | National Bank of the East | `80A42A870` | $266,245.77 | Mexican Peso | $266,245.77 | Mexican Peso | ACH |
| 10 | 2022/09/12 19:37 | National Bank of the East | `80A42A870` | Japan Bank #52 | `80465E020` | $1,327,255.90 | Yen | $1,327,255.90 | Yen | ACH |
| 11 | 2022/09/10 14:21 | Germany Bank #7 | `8040AE4F0` | Plateau Bank | `80A716810` | $6,117.71 | US Dollar | $6,117.71 | US Dollar | ACH |
| 12 | 2022/09/12 21:50 | Plateau Bank | `80A716810` | Japan Bank #52 | `80465E020` | $782,654.51 | Yen | $782,654.51 | Yen | ACH |
| 13 | 2022/09/10 17:36 | Germany Bank #7 | `8040AE4F0` | Italy Bank #6 | `803C62630` | $12,613.68 | Euro | $12,613.68 | Euro | ACH |
| 14 | 2022/09/12 23:51 | Italy Bank #6 | `803C62630` | Japan Bank #52 | `80465E020` | $1,557,864.56 | Yen | $1,557,864.56 | Yen | ACH |
| 15 | 2022/09/10 22:22 | Germany Bank #7 | `8040AE4F0` | Belgium Bank #1228 | `8062E7A30` | $13,291.54 | Euro | $13,291.54 | Euro | ACH |
| 16 | 2022/09/13 03:00 | Belgium Bank #1228 | `8062E7A30` | Japan Bank #52 | `80465E020` | $1,641,584.88 | Yen | $1,641,584.88 | Yen | ACH |
| 17 | 2022/09/11 01:00 | Germany Bank #7 | `8040AE4F0` | Germany Bank #92 | `80C54A950` | $2,022.81 | Euro | $2,022.81 | Euro | ACH |
| 18 | 2022/09/13 06:13 | Germany Bank #92 | `80C54A950` | Japan Bank #52 | `80465E020` | $218,720.89 | Yen | $218,720.89 | Yen | ACH |
| 19 | 2022/09/11 08:34 | Germany Bank #7 | `8040AE4F0` | India Bank #16 | `805F23670` | $1,177,087.33 | Rupee | $1,177,087.33 | Rupee | ACH |
| 20 | 2022/09/13 11:01 | India Bank #16 | `805F23670` | Japan Bank #52 | `80465E020` | $1,689,246.28 | Yen | $1,689,246.28 | Yen | ACH |
| 21 | 2022/09/11 10:17 | Germany Bank #7 | `8040AE4F0` | First Bank of Harrisburg | `80780EAF0` | $1,892.73 | US Dollar | $1,892.73 | US Dollar | ACH |
| 22 | 2022/09/13 12:39 | First Bank of Harrisburg | `80780EAF0` | Japan Bank #52 | `80465E020` | $170,485.49 | Yen | $170,485.49 | Yen | ACH |
| 23 | 2022/09/11 12:10 | Germany Bank #7 | `8040AE4F0` | Belgium Bank #152 | `80A66B910` | $14,359.71 | Euro | $14,359.71 | Euro | ACH |
| 24 | 2022/09/13 14:23 | Belgium Bank #152 | `80A66B910` | Japan Bank #52 | `80465E020` | $1,796,611.66 | Yen | $1,796,611.66 | Yen | ACH |
| 25 | 2022/09/11 13:03 | Germany Bank #7 | `8040AE4F0` | Germany Bank #18 | `8001694F0` | $9,411.91 | Euro | $9,411.91 | Euro | ACH |
| 26 | 2022/09/13 15:10 | Germany Bank #18 | `8001694F0` | Japan Bank #52 | `80465E020` | $1,129,217.23 | Yen | $1,129,217.23 | Yen | ACH |
| 27 | 2022/09/11 14:51 | Germany Bank #7 | `8040AE4F0` | China Bank #14 | `805990DF0` | $652,633.41 | Rupee | $652,633.41 | Rupee | ACH |
| 28 | 2022/09/13 17:13 | China Bank #14 | `805990DF0` | Japan Bank #52 | `80465E020` | $753,826.48 | Yen | $753,826.48 | Yen | ACH |
| 29 | 2022/09/11 16:21 | Germany Bank #7 | `8040AE4F0` | Russia Bank #16 | `8061AD3B0` | $237,303.80 | Ruble | $237,303.80 | Ruble | ACH |
| 30 | 2022/09/13 18:31 | Russia Bank #16 | `8061AD3B0` | Japan Bank #52 | `80465E020` | $290,938.96 | Yen | $290,938.96 | Yen | ACH |
| 31 | 2022/09/12 03:44 | Germany Bank #7 | `8040AE4F0` | Japan Bank #50 | `8041293F0` | $1,949,818.73 | Yen | $1,949,818.73 | Yen | ACH |
| 32 | 2022/09/13 21:42 | Japan Bank #50 | `8041293F0` | Japan Bank #52 | `80465E020` | $1,949,818.73 | Yen | $1,949,818.73 | Yen | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The primary subject is Corporation #29863, account 80465E020, held at Japan Bank #52 (Bank ID 11128). This account is the sole beneficiary of a 16-leg inbound consolidation described below. The scheme was funded by a single originating account held by a partnership at a German institution (Bank ID 7548), which routed funds through sixteen intermediary accounts — held by a mix of corporations, partnerships, and sole proprietorships across Germany, the United States, Italy, Belgium, India, China, Russia, and Japan — before the funds reached the subject account. The originating and intermediary accounts are addressed collectively in the sections below rather than individually identified.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 10 and September 13, 2022, the subject account received 16 incoming ACH credits, all denominated in Japanese Yen, ranging from ¥170,485.49 (paired scatter-phase leg through First Bank of Harrisburg: $1,892.73) to ¥243,308,041.20 (paired scatter-phase leg through Flagstone Community Bank: $2,232,050.16). Each credit originated from a distinct intermediary account that had, in turn, received a single ACH payment from the same originating account within the preceding one to two days. The full scheme comprised 32 ACH transactions across 18 accounts at 18 institutions.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
Activity spanned September 10, 2022, 02:46 through September 13, 2022, 21:42 — approximately 91 hours. The outbound (scatter) payments from the originating account were issued between 09/10 02:46 and 09/12 03:44; the corresponding inbound payments to the subject account (gather) followed between 09/12 07:57 and 09/13 21:42, cleanly separated by roughly four hours with no overlap between phases.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The originating and intermediary accounts spanned at least eight jurisdictions: Germany (originating account plus three intermediaries), the United States (six intermediaries at separate domestic institutions), Italy, Belgium (two intermediaries), India, China, Russia, and Japan (one intermediary in addition to the subject account). No two intermediary accounts shared a common bank.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The sixteen intermediary transfers converge on a single beneficiary account within a compressed 91-hour window, with each intermediary forwarding funds within one to two days of receipt — a structure consistent with scatter-gather layering designed to obscure the funds' single point of origin. The clearest indicator of manipulation is the gather-phase currency conversion: implied Yen rates vary substantially within currency groups rather than tracking a single real exchange rate. The five USD-denominated legs alone imply rates ranging from approximately 86.4 to 127.9 Yen per dollar — a roughly 48% spread within a one-to-three-day window, far wider than genuine USD/JPY movement over that period. The Euro-denominated legs are more internally consistent (five cluster near 120–125 Yen per Euro), but one diverges to roughly 108, and the two Rupee-denominated legs differ by a further 24%. Yen amounts that correspond to no single, real-world exchange rate at time of transfer indicate the gather-phase amounts were assigned without reference to market rates — a hallmark of layering intended to obscure the true value relationship between what was sent and what was consolidated. This inconsistency is systemic across the gather phase, not confined to one outlier: the largest single leg (¥243,308,041.20, implied rate ~109.0) falls within the broader USD-leg spread rather than standing apart from it. This scatter-then-gather structure matches the one-source-to-one-destination-via-multiple-intermediary typology described in recent academic AML literature evaluating this transaction population (Deprez, Baesens, Verdonck & Verbeke, 2025). This pattern alone does not establish wrongdoing absent further review of counterparty relationships.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
The scheme operated in two phases. In the scatter phase, the originating account issued 16 separate outbound ACH payments to the sixteen intermediary accounts, each denominated in the recipient's local currency (US Dollar, Euro, Mexican Peso, Indian Rupee, Russian Ruble, and Japanese Yen), with values ranging from $1,892.73 to $2,232,050.16 or currency equivalent — several below common reporting thresholds, several well above. In the gather phase, fifteen of the sixteen intermediaries forwarded a Yen-converted payment to the subject account at implied conversion rates that varied inconsistently within each currency group rather than tracking a single real exchange rate, particularly among the five USD-denominated legs. The remaining intermediary (Japan Bank #50) received and forwarded an identical Yen-denominated amount ($1,949,818.73) with no value change — a direct pass-through rather than a conversion, since both legs at that account were already Yen-denominated. No intermediary account received more than one inbound or sent more than one outbound payment within the observed window, and no funds were returned to the originating account.

### Supporting Pattern

<!-- Reference to known typology. Pattern: SCATTER-GATHER -->
SCATTER-GATHER. Primary technical citation: Deprez, Baesens, Verdonck & Verbeke (2025), "GARG-AML" (arXiv:2506.04292v2), which defines this one-to-many-to-one structure and validates it against this same underlying transaction dataset (citing Altman et al., 2023, as the dataset's creator). Supplementary mechanism citation: FATF, Professional Money Laundering (2018), description of mule-network fund distribution by a single controller, which describes the dispersal mechanism observed in the scatter phase.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
32 transactions total (16 scatter, 16 gather); 18 unique accounts across 18 unique banks. Scatter-phase outbound amounts span six currencies (US Dollar, Euro, Mexican Peso, Rupee, Ruble, Yen), ranging $1,892.73–$2,232,050.16 in local-currency terms. Gather-phase inbound amounts are uniformly Yen, ranging ¥170,485.49–¥243,308,041.20. Implied gather-phase conversion rates are inconsistent within currency groups — USD-denominated legs span ~86.4–127.9 Yen/USD (~48% spread), EUR-denominated legs mostly cluster ~120–125 Yen/EUR with one outlier at ~108, and INR-denominated legs span 1.16–1.44 (~24% spread) — inconsistent with genuine contemporaneous currency conversion. September 10–13, 2022 (91-hour window); scatter phase (09/10 02:46–09/12 03:44) and gather phase (09/12 07:57–09/13 21:42) are cleanly sequential with no overlap.