# Case 004 — FAN-IN (8-degree Fan-In)

**Pattern:** FAN-IN  
**Attempt #:** 352 (of 370)  
**Degree/Hop Info:** Max 8-degree Fan-In  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 8 |
| Total Amount Paid | $61,854.70 |
| Total Amount Received | $61,854.70 |
| Min Amount | $4,197.12 |
| Max Amount | $12,030.97 |
| Date Range | 2022/09/10 14:58 → 2022/09/14 13:19 |
| Unique Accounts | 9 |
| Unique Banks | 6 |
| Currencies | Euro |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `8000FC360` | Germany Bank #65 (22) | Sole Proprietorship #11575 | Receiver |
| `800151C60` | National Bank of the East (12) | Corporation #5284 | Sender |
| `8001A6870` | Germany Bank #65 (22) | Corporation #37275 | Sender |
| `8001B94D0` | China Bank #6 (20) | Corporation #26391 | Sender |
| `800219480` | Germany Bank #65 (22) | Corporation #20143 | Sender |
| `80021B2C0` | National Bank of the East (12) | Partnership #23600 | Sender |
| `800296920` | Portugal Bank #43 (1502) | Corporation #22807 | Sender |
| `8002A0E00` | Germany Bank #18 (23) | Sole Proprietorship #22283 | Sender |
| `8002AE470` | Spain Bank #23 (1522) | Corporation #47920 | Sender |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/10 14:58 | Portugal Bank #43 | `800296920` | Germany Bank #65 | `8000FC360` | $12,030.97 | Euro | $12,030.97 | Euro | ACH |
| 2 | 2022/09/10 21:13 | Germany Bank #18 | `8002A0E00` | Germany Bank #65 | `8000FC360` | $4,197.12 | Euro | $4,197.12 | Euro | ACH |
| 3 | 2022/09/11 09:56 | Germany Bank #65 | `800219480` | Germany Bank #65 | `8000FC360` | $4,443.22 | Euro | $4,443.22 | Euro | ACH |
| 4 | 2022/09/11 11:01 | National Bank of the East | `800151C60` | Germany Bank #65 | `8000FC360` | $8,392.45 | Euro | $8,392.45 | Euro | ACH |
| 5 | 2022/09/12 12:37 | Germany Bank #65 | `8001A6870` | Germany Bank #65 | `8000FC360` | $7,762.42 | Euro | $7,762.42 | Euro | ACH |
| 6 | 2022/09/13 12:44 | Spain Bank #23 | `8002AE470` | Germany Bank #65 | `8000FC360` | $6,894.67 | Euro | $6,894.67 | Euro | ACH |
| 7 | 2022/09/13 13:26 | National Bank of the East | `80021B2C0` | Germany Bank #65 | `8000FC360` | $9,466.64 | Euro | $9,466.64 | Euro | ACH |
| 8 | 2022/09/14 13:19 | China Bank #6 | `8001B94D0` | Germany Bank #65 | `8000FC360` | $8,667.21 | Euro | $8,667.21 | Euro | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, 8000FC360, held by Sole Proprietorship #11575 at Germany Bank #65, is the recipient account for all 8 inbound transactions in this activity. The account is registered as a sole proprietorship with no prior SAR filings on record.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 10 and September 14, 2022, account `8000FC360` received 8 inbound ACH transfers totaling $61,854.70, from 8 separate originating accounts across 6 distinct financial institutions in 5 countries (Germany, Portugal, Spain, China, and the United States).

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
All 8 transfers occurred within a 94-hour window, from 2022/09/10 14:58 to 2022/09/14 13:19 — an average of one inbound transfer roughly every 13.5 hours.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
Funds converged on Germany Bank #65 from originating institutions in Germany, Portugal, Spain, China, and the United States. Notably, 2 of the 8 originating accounts (`800219480`, `8001A6870`) are held at the _same_ receiving institution, Germany Bank #65 — an internal concentration pattern distinct from the purely cross-institutional convergence seen in comparable fan-in cases.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The convergence of funds from eight unrelated senders across five countries into a single sole-proprietorship account within a four-day period is inconsistent with routine business receivables for an entity of this registered size. Threshold-awareness is pronounced: 7 of 8 transfers fall between $4,197.12 and $9,466.64 — below the $10,000 CTR threshold — with only one transaction ($12,030.97) exceeding it, suggesting deliberate structuring to keep the majority of inbound activity under individual reporting scrutiny. The mix of intra-bank transfers (from accounts already held at the receiving institution) alongside cross-border inbound transfers further suggests the subject account may be functioning as a consolidation point for both externally-sourced and internally-repositioned funds. This pattern is consistent with fan-in aggregation ahead of further layering or withdrawal (see FinCEN Case Example, July 2014, Case 7).

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Eight distinct originating accounts across six institutions — including two accounts already domiciled at the receiving bank — independently transferred funds into the subject account over a 94-hour period, with National Bank of the East acting as the source for two of the eight transfers from two separate accounts.

### Supporting Pattern

<!-- Reference to known typology. Pattern: FAN-IN -->
Pattern: FAN-IN (8-degree). Structural grounding: FinCEN Case Example, July 2014, Case 7 (structuring/aggregation into a single account). Per `typology_mapping.md`.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
8 transactions, $61,854.70 total, 9 unique accounts across 6 unique banks, single currency (EUR), ACH format exclusively, September 10–14 2022 (94-hour window).

