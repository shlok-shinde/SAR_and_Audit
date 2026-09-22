# Case 012 — STACK (10-tx Stack with Bitcoin)

**Pattern:** STACK  
**Attempt #:** 260 (of 370)  
**Degree/Hop Info:** N/A  
**Narrative Status:** Draft pending  

> [!IMPORTANT]
> This is the **only laundering attempt** in the dataset with a non-ACH payment format. Contains 9 ACH + 1 Bitcoin transaction — added specifically for payment format diversity.

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 10 |
| Total Amount Paid | $79,294.74 |
| Total Amount Received | $79,294.74 |
| Min Amount | $0.37 |
| Max Amount | $15,740.65 |
| Date Range | 2022/09/08 11:04 -> 2022/09/12 18:32 |
| Unique Accounts | 16 |
| Unique Banks | 10 |
| Currencies | Bitcoin, Euro, US Dollar |
| Cross-Currency? | No |
| Payment Formats | ACH, Bitcoin |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| 800058470 | Germany Bank #18 (23) | Sole Proprietorship #22195 | Receiver |
| 80005BD00 | National Bank of Laramie (10) | Corporation #20088 | Sender |
| 8000E43B0 | Crytpo Bank #9 (225) | Sole Proprietorship #970 | Sender |
| 8000E43B1 | Crytpo Bank #9 (225) | Country #1 | Receiver |
| 8000F65C0 | Arbor Savings Bank (1) | Sole Proprietorship #53 | Sender / Receiver |
| 800103610 | China Bank #6 (20) | Partnership #23257 | Receiver |
| 8001325C0 | National Bank of Pittsburgh (220) | Corporation #84 | Sender |
| 800142410 | Germany Bank #18 (23) | Corporation #26583 | Receiver |
| 8001B3D10 | China Bank #6 (20) | Partnership #23279 | Sender |
| 8001B4210 | China Bank #6 (20) | Corporation #20124 | Receiver |
| 8001BA1D0 | Germany Bank #65 (22) | Partnership #42701 | Sender / Receiver |
| 8001BC960 | National Bank of the East (12) | Corporation #20129 | Sender |
| 8001D6370 | Finland Bank #0 (11) | Sole Proprietorship #48248 | Sender / Receiver |
| 8001FCB30 | National Bank of the East (12) | Sole Proprietorship #22240 | Sender / Receiver |
| 80023BB50 | National Bank of the East (12) | Partnership #42816 | Receiver |
| 800963A91 | France Bank #51 (1024) | Corporation #26041 | Sender |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/08 15:04 | China Bank #6 | 8001B3D10 | Germany Bank #65 | 8001BA1D0 | $14,715.45 | Euro | $14,715.45 | Euro | ACH |
| 2 | 2022/09/11 04:52 | Germany Bank #65 | 8001BA1D0 | China Bank #6 | 800103610 | $14,933.09 | Euro | $14,933.09 | Euro | ACH |
| 3 | 2022/09/09 23:49 | National Bank of Pittsburgh | 8001325C0 | Finland Bank #0 | 8001D6370 | $6,791.47 | Euro | $6,791.47 | Euro | ACH |
| 4 | 2022/09/12 18:32 | Finland Bank #0 | 8001D6370 | Germany Bank #18 | 800058470 | $6,862.86 | Euro | $6,862.86 | Euro | ACH |
| 5 | 2022/09/08 14:28 | National Bank of the East | 8001BC960 | National Bank of the East | 8001FCB30 | $1,567.66 | Euro | $1,567.66 | Euro | ACH |
| 6 | 2022/09/08 18:29 | National Bank of the East | 8001FCB30 | National Bank of the East | 80023BB50 | $1,606.60 | Euro | $1,606.60 | Euro | ACH |
| 7 | 2022/09/09 12:00 | France Bank #51 | 800963A91 | Crytpo Bank #9 | 8000E43B1 | $0.37 | Bitcoin | $0.37 | Bitcoin | Bitcoin |
| 8 | 2022/09/11 15:22 | Crytpo Bank #9 | 8000E43B0 | China Bank #6 | 8001B4210 | $3,749.45 | Euro | $3,749.45 | Euro | ACH |
| 9 | 2022/09/08 11:04 | National Bank of Laramie | 80005BD00 | Arbor Savings Bank | 8000F65C0 | $15,740.65 | US Dollar | $15,740.65 | US Dollar | ACH |
| 10 | 2022/09/10 18:49 | Arbor Savings Bank | 8000F65C0 | Germany Bank #18 | 800142410 | $13,327.14 | Euro | $13,327.14 | Euro | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
This case involves five parallel transaction sequences. Four (Chains A, B, C, E) follow a standard two-hop structure: an originating account, one intermediary, and a final destination. The fifth (Chain D) begins with a $0.37 Bitcoin transfer into account 8000E43B1 (entity listed as "Country #1") at Crytpo Bank #9, followed two days later by a $3,749.45 Euro transfer out of a different account, 8000E43B0 (Sole Proprietorship #970), at the same institution — the two accounts are not directly linked by any transaction in the dataset, only by shared institutional location and sequential timing.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 8 and September 12, 2022, ten transactions moved funds through five parallel two-hop (or apparent two-hop) sequences. Nine transactions were standard ACH transfers ranging from $1,567.66 to $15,740.65, denominated in Euro or US Dollar. The tenth was a $0.37 Bitcoin transfer — the only non-ACH, non-fiat transaction in this case.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
Activity spanned approximately 103.5 hours, from September 8, 2022, 11:04 to September 12, 2022, 18:32. Individual chain completions ranged from under 3 hours (Chain C) to roughly 2.5 days (Chain B).

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The five sequences span institutions in at least five countries — China, Germany, the United States, Finland, and France — plus one transaction routed through Crytpo Bank #9, a virtual-currency-linked institution with no clear jurisdictional designation in the account records. Chain C is notable for remaining entirely within a single institution, National Bank of the East, rather than crossing between banks.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The parallel short chains operating within the same 103.5-hour window are consistent with a coordinated layering structure rather than unrelated independent activity. Three of the five chains (A, B, C) convert Euro to Euro with no currency change required, yet each shows a value increase of 1.05% to 2.48% between the inbound and outbound leg — inconsistent with any standard processing-fee structure, which would be expected to reduce value, not grow it, and inconsistent with genuine currency conversion, since no conversion was needed. Chain E converts US Dollar to Euro at an implied rate of approximately 0.847, notably below the roughly 0.95–1.00 range in which the Euro traded against the Dollar during September 2022, suggesting this conversion was not executed at a genuine market rate. Chain C additionally moves funds through three accounts entirely within a single institution (National Bank of the East) — two unnecessary internal hops with no clear legitimate business rationale. Most notably, the Bitcoin-linked activity in Chain D shows no direct transactional link between the account receiving the $0.37 Bitcoin transfer and the account sending the $3,749.45 Euro transfer two days later; the two are connected only by shared institution and proximate timing. A Bitcoin transfer of a trivial, sub-$1 amount, followed by a substantially larger fiat transfer from a differently-numbered, differently-named account at the same virtual-currency institution, is a pattern consistent with using a nominal transaction to establish or verify a channel before moving a larger, unrelated sum — though this specific inference is not directly evidenced by a traceable fund flow between the two accounts and should be treated as a lower-confidence observation relative to the other findings in this case. This layering behavior — sequential hops through intermediary accounts to obscure the connection between origin and destination — matches the mechanism described in FATF Professional Money Laundering (2018), Box 6, adapted from that source's e-wallet chain description to this case's mixed bank-transfer/Bitcoin structure. Parallel same-day transfers among unrelated customers can occur coincidentally, but the combination of same-currency value inflation across three chains, an off-market conversion in a fourth, and the unlinked Bitcoin/fiat pairing in a fifth is not adequately explained by ordinary customer activity.

### How (Method / Mechanism)

<!-- How the activity was conducted -- structuring method, layering technique, note the Bitcoin transaction -->
Four of the five chains followed a standard two-hop structure, with a single intermediary account receiving from one source and forwarding to one destination, in three cases altering the transferred value without a corresponding currency conversion to justify the change. The fifth apparent chain paired a nominal Bitcoin transfer into one account with a substantially larger Euro transfer out of a separate, differently-named account at the same institution two days later, with no direct transactional link between the two.

### Supporting Pattern

<!-- Reference to known typology. Pattern: STACK -->
Pattern: STACK (5 parallel two-hop sequences, including one virtual-currency-linked sequence). Structural grounding: FATF Professional Money Laundering (2018), Box 6 ("complex chain of e-wallets"), adapted to this case's mixed bank-transfer and single Bitcoin-leg structure. Per typology_mapping.md.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
10 transactions total across 5 parallel sequences (9 ACH, 1 Bitcoin); 16 unique accounts across 10 unique banks. Transaction amounts range $0.37 (Bitcoin) to $15,740.65, denominated in Bitcoin, Euro, and US Dollar. Three same-currency (EUR→EUR) chains show value increases of 1.05–2.48%; one cross-currency (USD→EUR) chain shows an implied rate (~0.847) below prevailing September 2022 market levels; one chain's two legs share no direct transactional link, only institutional co-location. September 8–12, 2022 (103.5-hour window).

