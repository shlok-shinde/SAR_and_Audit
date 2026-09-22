# Case 001 — FAN-OUT (16-degree Fan-Out)

**Pattern:** FAN-OUT  
**Attempt #:** 307 (of 370)  
**Degree/Hop Info:** Max 16-degree Fan-Out  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 16 |
| Total Amount Paid | $1,008,796.36 |
| Total Amount Received | $1,008,796.36 |
| Min Amount | $1,886.82 |
| Max Amount | $834,985.93 |
| Date Range | 2022/09/09 12:00 → 2022/09/13 11:37 |
| Unique Accounts | 17 |
| Unique Banks | 17 |
| Currencies | Australian Dollar, Euro, Ruble, Shekel, US Dollar |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account     | Bank (ID)                           | Entity                     | Role     |
| ----------- | ----------------------------------- | -------------------------- | -------- |
| `801D08580` | Savings Bank of Fairfield (14549)   | Corporation #7625          | Receiver |
| `801F99F20` | Germany Bank #58 (13862)            | Corporation #7729          | Receiver |
| `80212D6B0` | France Bank #28 (3514)              | Sole Proprietorship #53377 | Receiver |
| `802E7F950` | Savings Bank of New York (5836)     | Partnership #6599          | Receiver |
| `8043C7360` | Spruce Bancorp (27637)              | Sole Proprietorship #7951  | Receiver |
| `805DB7F20` | India Bank #43 (214749)             | Partnership #33657         | Sender   |
| `806FD7DE0` | Russia Bank #40 (18405)             | Sole Proprietorship #54662 | Receiver |
| `808252DC0` | Acme Federal Bank (16109)           | Partnership #10715         | Receiver |
| `80A090510` | Austria Bank #233 (17321)           | Sole Proprietorship #26409 | Receiver |
| `80A37E600` | Spain Bank #309 (219449)            | Corporation #27970         | Receiver |
| `80AD14210` | Japan Bank #0 (15)                  | Corporation #34069         | Receiver |
| `80AEBD9D0` | Savings Bank of Huron (3420)        | Partnership #42665         | Receiver |
| `80E427DE0` | Greece Bank #452 (124368)           | Corporation #23149         | Receiver |
| `81071EAA0` | Netherlands Bank #1680 (122352)     | Sole Proprietorship #25557 | Receiver |
| `8107E4020` | Israel Bank #14 (43460)             | Corporation #35871         | Receiver |
| `811F005C0` | Acme Cooperative Bank (1601)        | Partnership #39708         | Receiver |
| `8123CC980` | Savings Bank of Montpelier (213580) | Sole Proprietorship #11222 | Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/09 12:00 | India Bank #43 | `805DB7F20` | Greece Bank #452 | `80E427DE0` | $8,834.78 | Euro | $8,834.78 | Euro | ACH |
| 2 | 2022/09/09 14:43 | India Bank #43 | `805DB7F20` | Germany Bank #58 | `801F99F20` | $10,064.89 | Euro | $10,064.89 | Euro | ACH |
| 3 | 2022/09/09 17:48 | India Bank #43 | `805DB7F20` | Savings Bank of Huron | `80AEBD9D0` | $9,254.38 | US Dollar | $9,254.38 | US Dollar | ACH |
| 4 | 2022/09/09 18:37 | India Bank #43 | `805DB7F20` | Israel Bank #14 | `8107E4020` | $8,516.15 | Shekel | $8,516.15 | Shekel | ACH |
| 5 | 2022/09/09 20:16 | India Bank #43 | `805DB7F20` | Netherlands Bank #1680 | `81071EAA0` | $7,578.70 | Euro | $7,578.70 | Euro | ACH |
| 6 | 2022/09/10 09:47 | India Bank #43 | `805DB7F20` | Savings Bank of Fairfield | `801D08580` | $12,729.42 | US Dollar | $12,729.42 | US Dollar | ACH |
| 7 | 2022/09/11 05:55 | India Bank #43 | `805DB7F20` | Russia Bank #40 | `806FD7DE0` | $834,985.93 | Ruble | $834,985.93 | Ruble | ACH |
| 8 | 2022/09/11 15:01 | India Bank #43 | `805DB7F20` | Austria Bank #233 | `80A090510` | $13,922.94 | Euro | $13,922.94 | Euro | ACH |
| 9 | 2022/09/11 17:43 | India Bank #43 | `805DB7F20` | Acme Cooperative Bank | `811F005C0` | $11,390.33 | US Dollar | $11,390.33 | US Dollar | ACH |
| 10 | 2022/09/12 02:38 | India Bank #43 | `805DB7F20` | Spruce Bancorp | `8043C7360` | $18,132.22 | US Dollar | $18,132.22 | US Dollar | ACH |
| 11 | 2022/09/12 06:56 | India Bank #43 | `805DB7F20` | Savings Bank of New York | `802E7F950` | $15,716.83 | US Dollar | $15,716.83 | US Dollar | ACH |
| 12 | 2022/09/12 14:30 | India Bank #43 | `805DB7F20` | Savings Bank of Montpelier | `8123CC980` | $1,886.82 | US Dollar | $1,886.82 | US Dollar | ACH |
| 13 | 2022/09/12 18:28 | India Bank #43 | `805DB7F20` | France Bank #28 | `80212D6B0` | $14,295.77 | Euro | $14,295.77 | Euro | ACH |
| 14 | 2022/09/12 19:14 | India Bank #43 | `805DB7F20` | Spain Bank #309 | `80A37E600` | $4,682.39 | Euro | $4,682.39 | Euro | ACH |
| 15 | 2022/09/13 11:27 | India Bank #43 | `805DB7F20` | Japan Bank #0 | `80AD14210` | $27,152.44 | Australian Dollar | $27,152.44 | Australian Dollar | ACH |
| 16 | 2022/09/13 11:37 | India Bank #43 | `805DB7F20` | Acme Federal Bank | `808252DC0` | $9,652.37 | US Dollar | $9,652.37 | US Dollar | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, 805DB7F20, held by Partnership #33657 at India Bank #43, is the originating account for all 16 outbound transactions in this activity. The account is registered as a partnership entity with no prior SAR filings on record.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 9 and September 13, 2022, account 805DB7F20 initiated 16 outbound ACH transfers totaling $1,008,796.36, distributed to 16 separate beneficiary accounts across 15 distinct financial institutions in 10 countries (Germany, France, Russia, Austria, Spain, Japan, Greece, the Netherlands, Israel, and the United States).

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
All 16 transfers occurred within a 95-hour window, from 2022/09/09 12:00 to 2022/09/13 11:37 — an average of one outbound transfer roughly every 6 hours.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
Funds originated from India Bank #43 and were dispersed to receiving institutions in Australia, Germany, France, Russia, Austria, Spain, Japan, Greece, the Netherlands, Israel, and the United States — an unusually broad, multi-jurisdictional distribution for a single originating account with no documented international business purpose on file.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The rapid, high-volume dispersal of funds from a single account to sixteen unrelated beneficiaries across eleven countries within a four-day period is inconsistent with the account holder's registered business type (Partnership) and profile. The transaction sizing shows partial threshold-awareness: six of sixteen transfers fall between $1,886 and $9,652 — below the $10,000 CTR threshold — while the remainder range up to $834,985.93, suggesting the account was not engaged in a single legitimate commercial disbursement but rather multiple smaller transfers interspersed with irregular high-value outliers. This pattern is consistent with fan-out layering, in which a launderer disperses funds from a single account to numerous downstream accounts to fragment traceability and evade single-transaction reporting thresholds (see FFIEC Appendix G, Structuring; FATF-XII Typologies 2000-2001, Example 21).

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
The subject account executed sequential ACH transfers to newly-observed counterparties, each transaction routed to a different receiving bank, minimizing the number of transactions any single downstream institution would observe from this source — a hallmark of fan-out structuring designed to fragment a large sum below individual detection thresholds at each receiving point.

### Supporting Pattern

<!-- Reference to known typology. Pattern: FAN-OUT -->
Pattern: FAN-OUT (16-degree). Structural grounding: FFIEC BSA/AML Exam Manual, Appendix G (Structuring); FATF-XII Report on Money Laundering Typologies (2000-2001), Example 21; FATF Professional Money Laundering (2018), Money Mule Networks section. No single named FinCEN/FATF typology exists for fan-out specifically — grounding is composite. Per typology_mapping.md.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
16 transactions, $1,008,796.36 total, 17 unique accounts across 17 unique banks, 5 currencies, ACH format exclusively, September 9–13 2022 (95-hour window).
