# Case 005 — CYCLE (12-hop Cycle)

**Pattern:** CYCLE  
**Attempt #:** 218 (of 370)  
**Degree/Hop Info:** Max 12 hops  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 12 |
| Total Amount Paid | $155,139.05 |
| Total Amount Received | $155,139.05 |
| Min Amount | $5,935.92 |
| Max Amount | $41,321.30 |
| Date Range | 2022/09/06 19:29 → 2022/09/10 18:52 |
| Unique Accounts | 12 |
| Unique Banks | 12 |
| Currencies | Brazil Real, Euro, Saudi Riyal, Swiss Franc, US Dollar |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `80005F430` | Finland Bank #0 (11) | Sole Proprietorship #23073 | Sender / Receiver |
| `8005F0660` | National Bank of Laramie (10) | Sole Proprietorship #13098 | Sender / Receiver |
| `801771410` | National Bank of New Orleans (513) | Partnership #3783 | Sender / Receiver |
| `803E47E50` | Acme Federal Bank (16109) | Corporation #6254 | Sender / Receiver |
| `808FE2E00` | Acme Cooperative Bank (1601) | Corporation #50964 | Sender / Receiver |
| `80C813A70` | Bank of Denver (18511) | Sole Proprietorship #5471 | Sender / Receiver |
| `80D59FF50` | Brazil Bank #12 (235551) | Partnership #36866 | Sender / Receiver |
| `80DCF9990` | Germany Bank #118 (234222) | Corporation #25876 | Sender / Receiver |
| `80EDF8C80` | Switzerland Bank #44 (240774) | Partnership #49752 | Sender / Receiver |
| `80F95BC50` | First Bank of Lacrosse (15747) | Partnership #355 | Sender / Receiver |
| `811B86440` | Saudi Arabia Bank #4 (223) | Corporation #36539 | Sender / Receiver |
| `811F4AF40` | Saudi Arabia Bank #14 (148016) | Corporation #19043 | Sender / Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/06 19:29 | Acme Cooperative Bank | `808FE2E00` | Saudi Arabia Bank #14 | `811F4AF40` | $26,096.16 | Saudi Riyal | $26,096.16 | Saudi Riyal | ACH |
| 2 | 2022/09/07 12:42 | Saudi Arabia Bank #14 | `811F4AF40` | Bank of Denver | `80C813A70` | $6,956.93 | US Dollar | $6,956.93 | US Dollar | ACH |
| 3 | 2022/09/08 08:35 | Bank of Denver | `80C813A70` | Finland Bank #0 | `80005F430` | $5,935.92 | Euro | $5,935.92 | Euro | ACH |
| 4 | 2022/09/08 10:00 | Finland Bank #0 | `80005F430` | Switzerland Bank #44 | `80EDF8C80` | $6,366.97 | Swiss Franc | $6,366.97 | Swiss Franc | ACH |
| 5 | 2022/09/08 14:53 | Switzerland Bank #44 | `80EDF8C80` | National Bank of New Orleans | `801771410` | $7,295.37 | US Dollar | $7,295.37 | US Dollar | ACH |
| 6 | 2022/09/08 15:41 | National Bank of New Orleans | `801771410` | Brazil Bank #12 | `80D59FF50` | $41,321.30 | Brazil Real | $41,321.30 | Brazil Real | ACH |
| 7 | 2022/09/08 19:49 | Brazil Bank #12 | `80D59FF50` | Germany Bank #118 | `80DCF9990` | $5,977.73 | Euro | $5,977.73 | Euro | ACH |
| 8 | 2022/09/09 00:47 | Germany Bank #118 | `80DCF9990` | National Bank of Laramie | `8005F0660` | $7,225.51 | US Dollar | $7,225.51 | US Dollar | ACH |
| 9 | 2022/09/09 04:58 | National Bank of Laramie | `8005F0660` | First Bank of Lacrosse | `80F95BC50` | $7,225.51 | US Dollar | $7,225.51 | US Dollar | ACH |
| 10 | 2022/09/09 07:46 | First Bank of Lacrosse | `80F95BC50` | Saudi Arabia Bank #4 | `811B86440` | $26,554.30 | Saudi Riyal | $26,554.30 | Saudi Riyal | ACH |
| 11 | 2022/09/10 17:48 | Saudi Arabia Bank #4 | `811B86440` | Acme Federal Bank | `803E47E50` | $7,079.07 | US Dollar | $7,079.07 | US Dollar | ACH |
| 12 | 2022/09/10 18:52 | Acme Federal Bank | `803E47E50` | Acme Cooperative Bank | `808FE2E00` | $7,104.28 | US Dollar | $7,104.28 | US Dollar | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, `808FE2E00`, held by Corporation #50964 at Acme Cooperative Bank, functions as both the originating and terminal point of a 12-hop transaction chain. All twelve accounts in this chain serve as sequential intermediaries, each receiving funds and forwarding them onward within hours of receipt.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 6 and September 10, 2022, a chain of 12 sequential ACH transfers totaling $155,139.05 in cumulative movement passed through 12 accounts at 12 distinct financial institutions across 5 currencies, ultimately returning to the account that initiated the first transfer.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
The full loop completed within a 95-hour window, from 2022/09/06 19:29 to 2022/09/10 18:52 — an average of one hop roughly every 7.9 hours, indicating rapid sequential movement rather than incidental overlap between unrelated transfers.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The loop traverses institutions in six countries — Saudi Arabia, the United States, Finland, Switzerland, Brazil, and Germany — before returning to its point of origin. No single jurisdiction receives more than two hops, consistent with deliberate geographic dispersion to obscure the closed nature of the loop from any single reviewing institution.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Money returning to its originating account or a related party after passing through eleven intermediary accounts is inconsistent with any known legitimate commercial purpose — legitimate cross-border payment chains do not typically terminate at their own starting point. The transaction sizing shows a mix of moderate transfers ($5,935.92–$7,295.37) and two notable outliers (a $26,096.16 transfer at hop 1 and a $41,321.30 transfer at hop 6), with the amount roughly stabilizing near $7,000–7,300 across hops 2–5 and 7–9 before a second outlier cluster near the loop's close. The closed-loop structure, combined with rapid sequential timing (under 8 hours between hops on average) and no two hops sharing a common institution until the final return to Acme Cooperative Bank, is consistent with layering via circular fund movement, in which funds are cycled through unrelated jurisdictions to fabricate a legitimate-looking transaction history before returning to common control (see FATF-XII Report on Money Laundering Typologies 2000-2001, Example 11). While recurring commercial relationships between counterparties can produce apparent cyclical fund movement, the number of distinct intermediary entities (12), the breadth of unrelated jurisdictions traversed, and the absence of any documented invoicing or trade relationship between the parties are inconsistent with a legitimate netting or settlement arrangement.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Each account in the chain received a single inbound transfer and forwarded a corresponding outbound transfer within hours, with no account receiving from or sending to more than one counterparty — a strict one-in-one-out sequential structure in which twelve accounts pass value through a single deliberate route, each acting as a temporary pass-through. The use of five different currencies across the loop (Saudi Riyal, US Dollar, Euro, Swiss Franc, Brazil Real) without cross-currency conversion loss suggests either pre-funded multi-currency accounts or currency-matched intermediaries selected specifically to add jurisdictional complexity without altering the underlying value transferred.

### Supporting Pattern

<!-- Reference to known typology. Pattern: CYCLE -->
Pattern: CYCLE (12-hop). Structural grounding: FATF-XII Report on Money Laundering Typologies (2000-2001), Example 11 ("U-turn movement of funds"). Per `typology_mapping.md`.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
12 transactions, $155,139.05 cumulative movement, 12 unique accounts across 12 unique banks, 5 currencies, ACH format exclusively, September 6–10 2022 (95-hour window), closed loop returning to point of origin.
