# Case 003 — FAN-IN (16-degree Fan-In)

**Pattern:** FAN-IN  
**Attempt #:** 285 (of 370)  
**Degree/Hop Info:** Max 16-degree Fan-In  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat                  | Value                               |
| --------------------- | ----------------------------------- |
| Transaction Count     | 16                                  |
| Total Amount Paid     | $181,262.75                         |
| Total Amount Received | $181,262.75                         |
| Min Amount            | $715.72                             |
| Max Amount            | $18,923.30                          |
| Date Range            | 2022/09/08 19:02 → 2022/09/12 14:15 |
| Unique Accounts       | 17                                  |
| Unique Banks          | 17                                  |
| Currencies            | US Dollar                           |
| Cross-Currency?       | No                                  |
| Payment Format        | ACH                                 |

---

## Accounts & Entities Involved

| Account     | Bank (ID)                         | Entity                     | Role     |
| ----------- | --------------------------------- | -------------------------- | -------- |
| `801FD9E70` | France Bank #103 (24482)          | Partnership #24454         | Sender   |
| `803B70100` | Japan Bank #36 (19925)            | Partnership #31815         | Sender   |
| `804BD06D0` | India Bank #69 (212789)           | Sole Proprietorship #43116 | Sender   |
| `8057C54A0` | Savings Bank of Huron (7478)      | Sole Proprietorship #9256  | Sender   |
| `8061C7360` | India Bank #25 (7)                | Partnership #33830         | Sender   |
| `8061CCEA0` | Australia Bank #0 (28)            | Sole Proprietorship #32941 | Sender   |
| `80657C030` | Bank of Arkadelphia (1244)        | Sole Proprietorship #46354 | Sender   |
| `8079DDC30` | Savings Bank of Butte (19888)     | Corporation #16523         | Receiver |
| `80A98C410` | Australia Bank #33 (28222)        | Partnership #36506         | Sender   |
| `80BBC79B0` | Bank of Billings (11904)          | Partnership #15977         | Sender   |
| `80C46DE50` | Japan Bank #40 (210185)           | Partnership #31646         | Sender   |
| `80D051180` | Bank of the East (12381)          | Partnership #17168         | Sender   |
| `80E446440` | Switzerland Bank #9 (116)         | Sole Proprietorship #36680 | Sender   |
| `80EC7E760` | First Bank of Pittsburgh (215841) | Corporation #1110          | Sender   |
| `80ECEABA0` | National Bank of Milford (12803)  | Corporation #14533         | Sender   |
| `811BCF2E0` | Switzerland Bank #8 (118)         | Corporation #36573         | Sender   |
| `811E71060` | First Bank of Hartford (30974)    | Sole Proprietorship #20212 | Sender   |

---

## Full Transaction Log

| #   | Timestamp        | From Bank                | From Account | To Bank               | To Account  | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
| --- | ---------------- | ------------------------ | ------------ | --------------------- | ----------- | ----------- | ---------------- | --------------- | ------------------ | ------ |
| 1   | 2022/09/08 19:02 | Australia Bank #0        | `8061CCEA0`  | Savings Bank of Butte | `8079DDC30` | $13,104.96  | US Dollar        | $13,104.96      | US Dollar          | ACH    |
| 2   | 2022/09/09 10:12 | First Bank of Hartford   | `811E71060`  | Savings Bank of Butte | `8079DDC30` | $18,923.30  | US Dollar        | $18,923.30      | US Dollar          | ACH    |
| 3   | 2022/09/09 10:49 | France Bank #103         | `801FD9E70`  | Savings Bank of Butte | `8079DDC30` | $14,539.47  | US Dollar        | $14,539.47      | US Dollar          | ACH    |
| 4   | 2022/09/10 07:32 | Japan Bank #36           | `803B70100`  | Savings Bank of Butte | `8079DDC30` | $7,287.29   | US Dollar        | $7,287.29       | US Dollar          | ACH    |
| 5   | 2022/09/10 08:51 | Bank of the East         | `80D051180`  | Savings Bank of Butte | `8079DDC30` | $11,729.11  | US Dollar        | $11,729.11      | US Dollar          | ACH    |
| 6   | 2022/09/10 12:21 | Switzerland Bank #8      | `811BCF2E0`  | Savings Bank of Butte | `8079DDC30` | $6,889.99   | US Dollar        | $6,889.99       | US Dollar          | ACH    |
| 7   | 2022/09/10 16:15 | Switzerland Bank #9      | `80E446440`  | Savings Bank of Butte | `8079DDC30` | $2,093.55   | US Dollar        | $2,093.55       | US Dollar          | ACH    |
| 8   | 2022/09/11 02:32 | India Bank #25           | `8061C7360`  | Savings Bank of Butte | `8079DDC30` | $16,639.48  | US Dollar        | $16,639.48      | US Dollar          | ACH    |
| 9   | 2022/09/11 06:30 | National Bank of Milford | `80ECEABA0`  | Savings Bank of Butte | `8079DDC30` | $6,934.48   | US Dollar        | $6,934.48       | US Dollar          | ACH    |
| 10  | 2022/09/11 07:45 | India Bank #69           | `804BD06D0`  | Savings Bank of Butte | `8079DDC30` | $18,048.55  | US Dollar        | $18,048.55      | US Dollar          | ACH    |
| 11  | 2022/09/11 08:12 | Savings Bank of Huron    | `8057C54A0`  | Savings Bank of Butte | `8079DDC30` | $6,405.11   | US Dollar        | $6,405.11       | US Dollar          | ACH    |
| 12  | 2022/09/11 15:04 | First Bank of Pittsburgh | `80EC7E760`  | Savings Bank of Butte | `8079DDC30` | $10,129.71  | US Dollar        | $10,129.71      | US Dollar          | ACH    |
| 13  | 2022/09/11 16:21 | Bank of Billings         | `80BBC79B0`  | Savings Bank of Butte | `8079DDC30` | $13,391.90  | US Dollar        | $13,391.90      | US Dollar          | ACH    |
| 14  | 2022/09/12 07:57 | Australia Bank #33       | `80A98C410`  | Savings Bank of Butte | `8079DDC30` | $15,914.76  | US Dollar        | $15,914.76      | US Dollar          | ACH    |
| 15  | 2022/09/12 11:09 | Bank of Arkadelphia      | `80657C030`  | Savings Bank of Butte | `8079DDC30` | $715.72     | US Dollar        | $715.72         | US Dollar          | ACH    |
| 16  | 2022/09/12 14:15 | Japan Bank #40           | `80C46DE50`  | Savings Bank of Butte | `8079DDC30` | $18,515.37  | US Dollar        | $18,515.37      | US Dollar          | ACH    |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, 8079DDC30, held by Corporation #16523 at Savings Bank of Butte, is the recipient account for all 16 inbound transactions in this activity. The account is registered as a corporate entity with no prior SAR filings on record.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 8 and September 12, 2022, account 8079DDC30 received 16 inbound ACH transfers totaling $181,262.75, from 16 separate beneficiary accounts across 16 distinct financial institutions in 6 countries (Australia, France, Switzerland, India, Japan and the United States).

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
All 16 transfers occurred within a 91-hour window, from 2022/09/08 19:02 to 2022/09/12 14:15 — an average of one inbound transfer roughly every 5.7 hours.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
Funds converged on Savings Bank of Butte from originating institutions spanning six countries across four continents — an unusually broad, multi-jurisdictional pattern of inbound activity for a single corporate recipient account with no documented international trade or business relationship on file.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The rapid convergence of funds from sixteen unrelated senders across six countries into a single corporate account within a four-day period is inconsistent with routine commercial receivables activity. Unlike classic structuring, most individual transfers here do not cluster below the $10,000 CTR threshold — 10 of 16 transactions exceed $10,000, up to $18,923.30 — indicating this pattern reflects deliberate fund aggregation/consolidation rather than threshold evasion at the transaction level. Notably, all 16 transfers settled in US Dollars despite originating from banks in five foreign-currency jurisdictions, suggesting either pre-converted USD-denominated sending accounts or normalization prior to transfer — reducing cross-currency friction and traceability complexity for the receiving entity. This pattern is consistent with fan-in aggregation, in which a single account is used to consolidate funds from numerous geographically dispersed sources ahead of further layering or withdrawal (see FinCEN Case Example, July 2014, Case 7).

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Sixteen distinct originating accounts, each domiciled at a separate institution, independently initiated ACH transfers converging on the same recipient account within a 91-hour window. No two transactions shared a common sending institution, indicating either a coordinated network of unrelated funding sources or the use of complicit/mule accounts specifically selected to avoid concentration at any single sending institution — a structural hallmark of fan-in consolidation.

### Supporting Pattern

<!-- Reference to known typology. Pattern: FAN-IN -->
Pattern: FAN-IN (16-degree). Structural grounding: FinCEN Case Example, July 2014, Case 7 (structuring/aggregation into a single account). Per `typology_mapping.md`.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
16 transactions, $181,262.75 total, 17 unique accounts across 17 unique banks, single currency (USD), ACH format exclusively, September 8–12 2022 (91-hour window).
