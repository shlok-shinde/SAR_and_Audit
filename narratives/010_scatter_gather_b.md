# Case 010 — SCATTER-GATHER (22-tx Scatter-Gather)

**Pattern:** SCATTER-GATHER  
**Attempt #:** 271 (of 370)  
**Degree/Hop Info:** N/A  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 22 |
| Total Amount Paid | $971,811.64 |
| Total Amount Received | $971,811.64 |
| Min Amount | $280.84 |
| Max Amount | $261,675.02 |
| Date Range | 2022/09/08 08:02 → 2022/09/12 03:44 |
| Unique Accounts | 13 |
| Unique Banks | 12 |
| Currencies | Euro, US Dollar |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8000EE420` | Germany Bank #65 (22) | Corporation #20093 | Receiver |
| `8001576B0` | National Bank of Pittsburgh (220) | Corporation #420 | Sender / Receiver |
| `8001BA930` | Arbor Savings Bank (1) | Partnership #4212 | Sender / Receiver |
| `8001E6840` | Arbor Savings Bank (1) | Sole Proprietorship #196 | Sender / Receiver |
| `80027A2B0` | Germany Bank #18 (23) | Corporation #4739 | Sender / Receiver |
| `8002DA960` | China Bank #6 (20) | Sole Proprietorship #22300 | Sender / Receiver |
| `8003AA6D0` | Germany Bank #126 (410) | Sole Proprietorship #22632 | Sender / Receiver |
| `8005A64B0` | First Bank of Montpelier (795) | Partnership #896 | Sender / Receiver |
| `8005C1970` | Plandor Savings Bank (908) | Partnership #7228 | Sender / Receiver |
| `8006A4A30` | Savings Bank of Los Angeles (1665) | Sole Proprietorship #3353 | Sender / Receiver |
| `8007F79F0` | Finland Bank #0 (11) | Sole Proprietorship #22421 | Sender / Receiver |
| `8009FD120` | Portugal Bank #43 (1502) | Sole Proprietorship #22373 | Sender / Receiver |
| `800AEAC00` | France Bank #75 (2591) | Partnership #27410 | Sender |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/08 08:02 | France Bank #75 | `800AEAC00` | Arbor Savings Bank | `8001E6840` | $19,874.09 | US Dollar | $19,874.09 | US Dollar | ACH |
| 2 | 2022/09/10 16:36 | Arbor Savings Bank | `8001E6840` | Germany Bank #65 | `8000EE420` | $15,526.31 | Euro | $15,526.31 | Euro | ACH |
| 3 | 2022/09/08 08:46 | France Bank #75 | `800AEAC00` | Arbor Savings Bank | `8001BA930` | $16,439.17 | US Dollar | $16,439.17 | US Dollar | ACH |
| 4 | 2022/09/10 17:44 | Arbor Savings Bank | `8001BA930` | Germany Bank #65 | `8000EE420` | $12,675.54 | Euro | $12,675.54 | Euro | ACH |
| 5 | 2022/09/08 09:52 | France Bank #75 | `800AEAC00` | Germany Bank #18 | `80027A2B0` | $4,428.75 | Euro | $4,428.75 | Euro | ACH |
| 6 | 2022/09/11 10:28 | Germany Bank #18 | `80027A2B0` | Germany Bank #65 | `8000EE420` | $4,411.66 | Euro | $4,411.66 | Euro | ACH |
| 7 | 2022/09/08 14:41 | France Bank #75 | `800AEAC00` | National Bank of Pittsburgh | `8001576B0` | $16,880.57 | US Dollar | $16,880.57 | US Dollar | ACH |
| 8 | 2022/09/11 12:23 | National Bank of Pittsburgh | `8001576B0` | Germany Bank #65 | `8000EE420` | $13,322.20 | Euro | $13,322.20 | Euro | ACH |
| 9 | 2022/09/08 16:16 | France Bank #75 | `800AEAC00` | Portugal Bank #43 | `8009FD120` | $261,675.02 | Euro | $261,675.02 | Euro | ACH |
| 10 | 2022/09/11 13:19 | Portugal Bank #43 | `8009FD120` | Germany Bank #65 | `8000EE420` | $261,675.02 | Euro | $261,675.02 | Euro | ACH |
| 11 | 2022/09/08 18:01 | France Bank #75 | `800AEAC00` | Savings Bank of Los Angeles | `8006A4A30` | $172,117.87 | US Dollar | $172,117.87 | US Dollar | ACH |
| 12 | 2022/09/11 15:51 | Savings Bank of Los Angeles | `8006A4A30` | Germany Bank #65 | `8000EE420` | $122,502.72 | Euro | $122,502.72 | Euro | ACH |
| 13 | 2022/09/08 19:17 | France Bank #75 | `800AEAC00` | China Bank #6 | `8002DA960` | $1,929.85 | Euro | $1,929.85 | Euro | ACH |
| 14 | 2022/09/11 17:19 | China Bank #6 | `8002DA960` | Germany Bank #65 | `8000EE420` | $1,947.17 | Euro | $1,947.17 | Euro | ACH |
| 15 | 2022/09/09 12:39 | France Bank #75 | `800AEAC00` | Germany Bank #126 | `8003AA6D0` | $306.49 | Euro | $306.49 | Euro | ACH |
| 16 | 2022/09/11 19:33 | Germany Bank #126 | `8003AA6D0` | Germany Bank #65 | `8000EE420` | $280.84 | Euro | $280.84 | Euro | ACH |
| 17 | 2022/09/09 22:47 | France Bank #75 | `800AEAC00` | Finland Bank #0 | `8007F79F0` | $15,362.82 | Euro | $15,362.82 | Euro | ACH |
| 18 | 2022/09/11 21:15 | Finland Bank #0 | `8007F79F0` | Germany Bank #65 | `8000EE420` | $13,468.05 | Euro | $13,468.05 | Euro | ACH |
| 19 | 2022/09/10 10:50 | France Bank #75 | `800AEAC00` | First Bank of Montpelier | `8005A64B0` | $6,792.95 | US Dollar | $6,792.95 | US Dollar | ACH |
| 20 | 2022/09/11 23:03 | First Bank of Montpelier | `8005A64B0` | Germany Bank #65 | `8000EE420` | $5,553.65 | Euro | $5,553.65 | Euro | ACH |
| 21 | 2022/09/10 13:46 | France Bank #75 | `800AEAC00` | Plandor Savings Bank | `8005C1970` | $2,382.00 | US Dollar | $2,382.00 | US Dollar | ACH |
| 22 | 2022/09/12 03:44 | Plandor Savings Bank | `8005C1970` | Germany Bank #65 | `8000EE420` | $2,258.90 | Euro | $2,258.90 | Euro | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The primary subject is Corporation #20093, account 8000EE420, held at Germany Bank #65. This account is the sole beneficiary of an 11-leg inbound consolidation. The scheme was funded by a single originating account, 800AEAC00, held by Partnership #27410 at France Bank #75, which routed funds through eleven intermediary accounts across nine institutions before reaching the subject account.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 8 and September 12, 2022, the subject account received 11 incoming ACH credits, all denominated in Euro, ranging from $280.84 to $261,675.02. Each credit originated from a distinct intermediary account that had, in turn, received a single ACH payment from the same originating account within the preceding one to three days. The full scheme comprised 22 ACH transactions across 13 accounts at 12 institutions.
### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
Activity spanned September 8, 2022, 08:02 through September 12, 2022, 03:44 — approximately 91.7 hours. The outbound (scatter) payments were issued between 09/08 08:02 and 09/10 13:46; the corresponding inbound payments to the subject account (gather) followed between 09/10 16:36 and 09/12 03:44, with the first gather payment occurring roughly 2 hours 50 minutes after the final scatter payment — a clean sequential split between the two phases, with no overlap.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The originating account was held at France Bank #75. The eleven intermediary accounts were distributed across nine institutions, including two separate intermediary accounts held at the same bank, Arbor Savings Bank (8001BA930 and 8001E6840) — accounting for the discrepancy between 13 unique accounts and only 12 unique banks in this case. All funds ultimately consolidated at Germany Bank #65.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Two of the eleven intermediary accounts share a common institution (Arbor Savings Bank), a concentration pattern inconsistent with genuinely independent counterparties. More significantly, the implied value relationship between scatter and gather legs is internally inconsistent in a way not explainable by legitimate currency conversion or processing fees. The six USD-to-EUR legs imply exchange rates ranging from 0.712 to 0.948 EUR per USD — a roughly 33% spread among transfers occurring within a one-to-three-day window, far exceeding real EUR/USD movement over that period. More notably, the five Euro-to-Euro legs — transfers requiring no currency conversion at all — show value ratios ranging from 0.877 to 1.009, including one exact zero-change pass-through and one leg that increases in value (from $1,929.85 to $1,947.17), alongside others that decrease by as much as 12.3%. No consistent fee structure, legitimate or otherwise, produces same-currency transfers that sometimes gain value and sometimes lose over a tenth of their value — this pattern of arbitrarily assigned, rather than genuinely computed, transfer amounts is consistent with the one-source-to-one-destination-via-multiple-intermediary typology described in recent academic AML literature evaluating this transaction population (Deprez, Baesens, Verdonck & Verbeke, 2025). The inconsistent same-currency value changes are difficult to reconcile with any legitimate processing arrangement, though this pattern alone does not establish wrongdoing absent further review of the relationship between the originating and intermediary account holders.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
The scheme operated in two phases. In the scatter phase, the originating account issued 11 separate outbound ACH payments to the eleven intermediary accounts, denominated in either US Dollar or Euro depending on the recipient, with values ranging from $306.49 to $261,675.02. In the gather phase, each intermediary forwarded a Euro-denominated payment to the subject account, but the value relationship between what was received and what was forwarded varied inconsistently — both across the six USD-denominated legs (implied rates 0.712–0.948) and across the five Euro-denominated legs, which required no conversion yet still ranged from an exact pass-through to a 12.3% reduction, including one leg that increased in value. No intermediary account received more than one inbound or sent more than one outbound payment within the observed window, and no funds were returned to the originating account.
### Supporting Pattern

<!-- Reference to known typology. Pattern: SCATTER-GATHER -->
SCATTER-GATHER. Primary technical citation: Deprez, Baesens, Verdonck & Verbeke (2025), "GARG-AML" (arXiv:2506.04292v2), which defines this one-to-many-to-one structure and validates it against this same underlying transaction dataset (citing Altman et al., 2023, as the dataset's creator). Supplementary mechanism citation: FATF, Professional Money Laundering (2018), description of mule-network fund distribution by a single controller.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
22 transactions total (11 scatter, 11 gather); 13 unique accounts across 12 unique banks (2 intermediary accounts share one institution, Arbor Savings Bank). Scatter-phase outbound amounts span two currencies (US Dollar, Euro), ranging $306.49–$261,675.02; gather-phase inbound amounts are uniformly Euro, ranging $280.84–$261,675.02. Implied value ratios are inconsistent across both currency groups: USD-to-EUR legs range 0.712–0.948 (~33% spread), and EUR-to-EUR legs — which require no conversion — range 0.877–1.009, including one exact pass-through and one value increase. September 8–12, 2022 (91.7-hour window); scatter phase (09/08 08:02–09/10 13:46) and gather phase (09/10 16:36–09/12 03:44) are cleanly sequential with no overlap.
