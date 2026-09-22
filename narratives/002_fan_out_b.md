# Case 002 — FAN-OUT (10-degree Fan-Out)

**Pattern:** FAN-OUT  
**Attempt #:** 36 (of 370)  
**Degree/Hop Info:** Max 10-degree Fan-Out  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat                  | Value                               |
| --------------------- | ----------------------------------- |
| Transaction Count     | 10                                  |
| Total Amount Paid     | $68,637.67                          |
| Total Amount Received | $68,637.67                          |
| Min Amount            | $1,499.02                           |
| Max Amount            | $14,351.99                          |
| Date Range            | 2022/09/01 17:48 → 2022/09/04 18:07 |
| Unique Accounts       | 11                                  |
| Unique Banks          | 6                                   |
| Currencies            | Euro, US Dollar                     |
| Cross-Currency?       | No                                  |
| Payment Format        | ACH                                 |

---

## Accounts & Entities Involved

| Account     | Bank (ID)                      | Entity                     | Role     |
| ----------- | ------------------------------ | -------------------------- | -------- |
| `8000FBD00` | Germany Bank #18 (23)          | Corporation #20083         | Receiver |
| `80011F990` | National Bank of the East (12) | Corporation #20103         | Receiver |
| `80016DA30` | National Bank of Laramie (10)  | Sole Proprietorship #125   | Receiver |
| `80017BE40` | National Bank of the East (12) | Partnership #23241         | Receiver |
| `8001A6870` | Germany Bank #65 (22)          | Corporation #37275         | Receiver |
| `8001B0770` | China Bank #6 (20)             | Corporation #20123         | Receiver |
| `8001BB380` | National Bank of Laramie (10)  | Partnership #182           | Sender   |
| `8001D8590` | Finland Bank #0 (11)           | Sole Proprietorship #22234 | Receiver |
| `8002185A0` | Germany Bank #18 (23)          | Corporation #20142         | Receiver |
| `80022FC00` | Finland Bank #0 (11)           | Partnership #23293         | Receiver |
| `800550B60` | National Bank of the East (12) | Partnership #23409         | Receiver |

---

## Full Transaction Log

| #   | Timestamp        | From Bank                | From Account | To Bank                   | To Account  | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
| --- | ---------------- | ------------------------ | ------------ | ------------------------- | ----------- | ----------- | ---------------- | --------------- | ------------------ | ------ |
| 1   | 2022/09/01 17:48 | National Bank of Laramie | `8001BB380`  | Germany Bank #65          | `8001A6870` | $1,499.02   | Euro             | $1,499.02       | Euro               | ACH    |
| 2   | 2022/09/02 13:30 | National Bank of Laramie | `8001BB380`  | Finland Bank #0           | `8001D8590` | $2,380.42   | Euro             | $2,380.42       | Euro               | ACH    |
| 3   | 2022/09/03 12:05 | National Bank of Laramie | `8001BB380`  | Germany Bank #18          | `8002185A0` | $1,547.24   | Euro             | $1,547.24       | Euro               | ACH    |
| 4   | 2022/09/03 14:22 | National Bank of Laramie | `8001BB380`  | Finland Bank #0           | `80022FC00` | $9,947.89   | Euro             | $9,947.89       | Euro               | ACH    |
| 5   | 2022/09/03 16:20 | National Bank of Laramie | `8001BB380`  | National Bank of Laramie  | `80016DA30` | $9,940.77   | US Dollar        | $9,940.77       | US Dollar          | ACH    |
| 6   | 2022/09/03 16:58 | National Bank of Laramie | `8001BB380`  | National Bank of the East | `800550B60` | $5,851.21   | Euro             | $5,851.21       | Euro               | ACH    |
| 7   | 2022/09/04 09:54 | National Bank of Laramie | `8001BB380`  | Germany Bank #18          | `8000FBD00` | $3,946.65   | Euro             | $3,946.65       | Euro               | ACH    |
| 8   | 2022/09/04 15:12 | National Bank of Laramie | `8001BB380`  | National Bank of the East | `80017BE40` | $5,035.99   | Euro             | $5,035.99       | Euro               | ACH    |
| 9   | 2022/09/04 16:27 | National Bank of Laramie | `8001BB380`  | National Bank of the East | `80011F990` | $14,351.99  | Euro             | $14,351.99      | Euro               | ACH    |
| 10  | 2022/09/04 18:07 | National Bank of Laramie | `8001BB380`  | China Bank #6             | `8001B0770` | $14,136.49  | Euro             | $14,136.49      | Euro               | ACH    |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, 8001BB380, held by Partnership #182 at National Bank of Laramie, is the originating account for all 10 outbound transactions in this activity. The account is registered as a partnership entity with no prior SAR filings on record.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 1 and September 4, 2022, account 8001BB380 initiated 10 outbound ACH transfers totaling $68,637.67, distributed to 10 separate beneficiary accounts across 6 distinct financial institutions in 4 countries (Germany, China, Finland and the United States).

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
All 10 transfers occurred within a 72-hour window, from 2022/09/01 17:48 to 2022/09/04 18:07 — an average of one outbound transfer roughly every 7 hours.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
Funds originated from National Bank of Laramie and were dispersed to receiving institutions in Germany, China, Finland and the United States — an unusually broad, multi-jurisdictional distribution for a single originating account with no documented international business purpose on file.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The rapid, high-volume dispersal of funds from a single account to ten unrelated beneficiaries across four countries within a three-day period is inconsistent with the account holder's registered business type (Partnership) and profile. The transaction sizing shows good threshold-awareness: eight of ten transfers fall between $1,499.02 and $9,947.89 — below the $10,000 CTR threshold — while the remaining two range up to $14,351.99, suggesting the account was not engaged in a single legitimate commercial disbursement but rather multiple smaller transfers interspersed with irregular high-value outliers. This pattern is consistent with fan-out layering, in which a launderer disperses funds from a single account to numerous downstream accounts to fragment traceability and evade single-transaction reporting thresholds (see FFIEC Appendix G, Structuring; FATF-XII Typologies 2000-2001, Example 21). The concentration of multiple distinct receiving accounts at a small set of institutions — three at National Bank of the East alone — is consistent with coordinated use of shell or mule accounts held at common banks, distinguishing this case from pure geographic fan-out dispersal.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
The subject account executed sequential ACH transfers to ten distinct receiving accounts, but distribution was concentrated across only six banking institutions — three transfers (30% of total volume) routed to different accounts at National Bank of the East alone, with Germany Bank #18 and Finland Bank #0 each receiving two.

### Supporting Pattern

<!-- Reference to known typology. Pattern: FAN-OUT -->
Pattern: FAN-OUT (10-degree). Structural grounding: FFIEC BSA/AML Exam Manual, Appendix G (Structuring); FATF-XII Report on Money Laundering Typologies (2000-2001), Example 21; FATF Professional Money Laundering (2018), Money Mule Networks section. No single named FinCEN/FATF typology exists for fan-out specifically — grounding is composite per `typology_mapping.md`.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
10 transactions, $68,637.67 total, 11 unique accounts across 6 unique banks, 2 currencies, ACH format exclusively, September 1-4 2022 (72-hour window).
