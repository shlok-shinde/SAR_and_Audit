# Case 007 — GATHER-SCATTER (13-degree Gather-Scatter)

**Pattern:** GATHER-SCATTER  
**Attempt #:** 49 (of 370)  
**Degree/Hop Info:** Max 13-degree Fan-In  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 28 |
| Total Amount Paid | $158,505,163.63 |
| Total Amount Received | $158,505,163.63 |
| Min Amount | $211.15 |
| Max Amount | $154,264,039.64 |
| Date Range | 2022/09/02 03:26 → 2022/09/08 18:45 |
| Unique Accounts | 29 |
| Unique Banks | 28 |
| Currencies | Australian Dollar, Brazil Real, Euro, Mexican Peso, Ruble, US Dollar, Yen |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `801812250` | National Bank of the East (12) | Corporation #20567 | Sender |
| `8026D5C10` | Italy Bank #86 (5464) | Sole Proprietorship #28062 | Receiver |
| `80286F5F0` | Savings Bank of New Orleans (11107) | Corporation #37945 | Sender |
| `802E5E710` | Italy Bank #97 (13858) | Sole Proprietorship #24891 | Receiver |
| `802FDD680` | China Bank #6 (20) | Sole Proprietorship #29394 | Sender |
| `80314D0C0` | Ireland Bank #358 (27684) | Sole Proprietorship #24408 | Receiver |
| `80451C2E0` | Acme Federal Bank (16109) | Partnership #6922 | Sender |
| `804B9FA50` | India Bank #28 (213005) | Partnership #32618 | Sender |
| `80615F190` | Australia Bank #0 (28) | Sole Proprietorship #32941 | Receiver |
| `8063F1030` | Germany Bank #19 (16388) | Partnership #23897 | Sender |
| `806861BF0` | First Bank of Tampa (10344) | Sole Proprietorship #10523 | Sender |
| `806A8A380` | Future Cooperative Bank (2824) | Partnership #45967 | Receiver |
| `80705A7B0` | Russia Bank #106 (218502) | Sole Proprietorship #32947 | Receiver |
| `8075AC7C0` | Savings Bank of Bridgeport (214615) | Partnership #11986 | Sender / Receiver |
| `8077CEBE0` | Belgium Bank #87 (21918) | Partnership #26440 | Sender |
| `8096C6720` | Canada Bank #36 (25202) | Partnership #35725 | Sender |
| `809ABFB20` | Japan Bank #50 (210690) | Partnership #32497 | Receiver |
| `809F5BDC0` | First Bank of Chicago (24161) | Sole Proprietorship #13555 | Sender |
| `80A937600` | Australia Bank #84 (128557) | Partnership #36506 | Receiver |
| `80B81F350` | The Pine Thrift (21611) | Partnership #45429 | Sender |
| `80C5BF860` | Canada Bank #26 (214) | Sole Proprietorship #40443 | Receiver |
| `80D71C940` | Brazil Bank #25 (136334) | Corporation #18817 | Receiver |
| `80E05A280` | First Bank of Pittsburgh (215841) | Corporation #45613 | Receiver |
| `80E6A81F0` | National Bank of Helena (1457) | Partnership #52595 | Sender |
| `80E6C34F0` | National Bank of Boston (1588) | Corporation #15931 | Receiver |
| `810DDAA00` | Acme Bank (132445) | Partnership #8830 | Receiver |
| `810E74260` | Belgium Bank #87 (21918) | Partnership #47361 | Receiver |
| `811611D00` | Italy Bank #49 (1547) | Partnership #46281 | Sender |
| `811A18940` | Bank of Boston (146713) | Sole Proprietorship #16510 | Receiver |

---

## Full Transaction Log

| #   | Timestamp        | From Bank                   | From Account | To Bank                    | To Account  | Amount Paid     | Payment Currency  | Amount Received | Receiving Currency | Format |
| --- | ---------------- | --------------------------- | ------------ | -------------------------- | ----------- | --------------- | ----------------- | --------------- | ------------------ | ------ |
| 1   | 2022/09/02 03:26 | India Bank #28              | `804B9FA50`  | Savings Bank of Bridgeport | `8075AC7C0` | $2,517.30       | US Dollar         | $2,517.30       | US Dollar          | ACH    |
| 2   | 2022/09/02 06:43 | Belgium Bank #87            | `8077CEBE0`  | Savings Bank of Bridgeport | `8075AC7C0` | $589.68         | US Dollar         | $589.68         | US Dollar          | ACH    |
| 3   | 2022/09/02 12:15 | First Bank of Tampa         | `806861BF0`  | Savings Bank of Bridgeport | `8075AC7C0` | $5,990.44       | US Dollar         | $5,990.44       | US Dollar          | ACH    |
| 4   | 2022/09/03 00:09 | Acme Federal Bank           | `80451C2E0`  | Savings Bank of Bridgeport | `8075AC7C0` | $10,398.03      | US Dollar         | $10,398.03      | US Dollar          | ACH    |
| 5   | 2022/09/03 08:52 | National Bank of Helena     | `80E6A81F0`  | Savings Bank of Bridgeport | `8075AC7C0` | $11,582.87      | US Dollar         | $11,582.87      | US Dollar          | ACH    |
| 6   | 2022/09/03 14:51 | Germany Bank #19            | `8063F1030`  | Savings Bank of Bridgeport | `8075AC7C0` | $18,688.51      | US Dollar         | $18,688.51      | US Dollar          | ACH    |
| 7   | 2022/09/03 17:39 | China Bank #6               | `802FDD680`  | Savings Bank of Bridgeport | `8075AC7C0` | $9,113.83       | US Dollar         | $9,113.83       | US Dollar          | ACH    |
| 8   | 2022/09/04 05:43 | National Bank of the East   | `801812250`  | Savings Bank of Bridgeport | `8075AC7C0` | $6,752.14       | US Dollar         | $6,752.14       | US Dollar          | ACH    |
| 9   | 2022/09/04 10:11 | Canada Bank #36             | `8096C6720`  | Savings Bank of Bridgeport | `8075AC7C0` | $2,952.40       | US Dollar         | $2,952.40       | US Dollar          | ACH    |
| 10  | 2022/09/05 08:31 | The Pine Thrift             | `80B81F350`  | Savings Bank of Bridgeport | `8075AC7C0` | $4,994.66       | US Dollar         | $4,994.66       | US Dollar          | ACH    |
| 11  | 2022/09/05 12:59 | Savings Bank of New Orleans | `80286F5F0`  | Savings Bank of Bridgeport | `8075AC7C0` | $15,873.31      | US Dollar         | $15,873.31      | US Dollar          | ACH    |
| 12  | 2022/09/05 15:46 | First Bank of Chicago       | `809F5BDC0`  | Savings Bank of Bridgeport | `8075AC7C0` | $2,241.01       | US Dollar         | $2,241.01       | US Dollar          | ACH    |
| 13  | 2022/09/05 19:55 | Italy Bank #49              | `811611D00`  | Savings Bank of Bridgeport | `8075AC7C0` | $16,310.56      | US Dollar         | $16,310.56      | US Dollar          | ACH    |
| 14  | 2022/09/05 06:35 | Savings Bank of Bridgeport  | `8075AC7C0`  | Australia Bank #84         | `80A937600` | $154,264,039.64 | Australian Dollar | $154,264,039.64 | Australian Dollar  | ACH    |
| 15  | 2022/09/05 11:21 | Savings Bank of Bridgeport  | `8075AC7C0`  | Acme Bank                  | `810DDAA00` | $6,242.91       | US Dollar         | $6,242.91       | US Dollar          | ACH    |
| 16  | 2022/09/05 12:51 | Savings Bank of Bridgeport  | `8075AC7C0`  | Bank of Boston             | `811A18940` | $12,090.25      | US Dollar         | $12,090.25      | US Dollar          | ACH    |
| 17  | 2022/09/05 15:32 | Savings Bank of Bridgeport  | `8075AC7C0`  | Ireland Bank #358          | `80314D0C0` | $7,964.31       | Euro              | $7,964.31       | Euro               | ACH    |
| 18  | 2022/09/05 16:44 | Savings Bank of Bridgeport  | `8075AC7C0`  | Future Cooperative Bank    | `806A8A380` | $19,327.52      | US Dollar         | $19,327.52      | US Dollar          | ACH    |
| 19  | 2022/09/05 19:47 | Savings Bank of Bridgeport  | `8075AC7C0`  | Italy Bank #97             | `802E5E710` | $211.15         | Euro              | $211.15         | Euro               | ACH    |
| 20  | 2022/09/06 11:09 | Savings Bank of Bridgeport  | `8075AC7C0`  | Japan Bank #50             | `809ABFB20` | $1,533,548.11   | Yen               | $1,533,548.11   | Yen                | ACH    |
| 21  | 2022/09/06 15:06 | Savings Bank of Bridgeport  | `8075AC7C0`  | Australia Bank #0          | `80615F190` | $1,112,468.70   | Ruble             | $1,112,468.70   | Ruble              | ACH    |
| 22  | 2022/09/07 23:09 | Savings Bank of Bridgeport  | `8075AC7C0`  | Canada Bank #26            | `80C5BF860` | $4,436.75       | Mexican Peso      | $4,436.75       | Mexican Peso       | ACH    |
| 23  | 2022/09/08 10:22 | Savings Bank of Bridgeport  | `8075AC7C0`  | Italy Bank #86             | `8026D5C10` | $1,658.03       | Euro              | $1,658.03       | Euro               | ACH    |
| 24  | 2022/09/08 14:59 | Savings Bank of Bridgeport  | `8075AC7C0`  | National Bank of Boston    | `80E6C34F0` | $756.02         | US Dollar         | $756.02         | US Dollar          | ACH    |
| 25  | 2022/09/08 15:11 | Savings Bank of Bridgeport  | `8075AC7C0`  | First Bank of Pittsburgh   | `80E05A280` | $8,890.34       | US Dollar         | $8,890.34       | US Dollar          | ACH    |
| 26  | 2022/09/08 16:53 | Savings Bank of Bridgeport  | `8075AC7C0`  | Belgium Bank #87           | `810E74260` | $11,981.12      | Euro              | $11,981.12      | Euro               | ACH    |
| 27  | 2022/09/08 17:55 | Savings Bank of Bridgeport  | `8075AC7C0`  | Brazil Bank #25            | `80D71C940` | $63,889.74      | Brazil Real       | $63,889.74      | Brazil Real        | ACH    |
| 28  | 2022/09/08 18:45 | Savings Bank of Bridgeport  | `8075AC7C0`  | Russia Bank #106           | `80705A7B0` | $1,349,654.30   | Ruble             | $1,349,654.30   | Ruble              | ACH    |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
The subject account, 8075AC7C0, held by Partnership #11986 at Savings Bank of Bridgeport, served as the consolidation and dispersal point for the full 28-transaction sequence — the only account acting in both a receiving and sending capacity in this case.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 2 and September 8, 2022, account 8075AC7C0 received 13 inbound ACH transfers from 13 distinct originating accounts, all denominated in US Dollars and totaling approximately $108,004.74, ranging from $589.68 to $18,688.51 per transaction. The account then initiated 15 outbound ACH transfers to 15 distinct beneficiary accounts across seven currencies (US Dollar, Euro, Australian Dollar, Yen, Ruble, Mexican Peso, Brazil Real), fourteen of which ranged from $211.15 to $19,327.52 in local-currency terms. One outbound transfer — to Australia Bank #84, account 80A937600 — moved $154,264,039.64, a sum roughly 1,400 times larger than the total amount gathered on the inbound side.

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
The full sequence spanned 159.3 hours (September 2, 03:26 to September 8, 18:45). Gather-side transfers ran from September 2 to September 5, but the first scatter-side transfer (September 5, 06:35) occurred before the final gather-side transfer (September 5, 19:55) — the two phases overlapped rather than proceeding in strict sequence.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
Inbound funds originated from accounts across seven countries (India, Belgium, Germany, China, Canada, Italy, and the United States). Outbound funds were dispersed to accounts across nine countries (Australia, Ireland, Italy, Japan, Canada, Brazil, Russia, Belgium, and the United States), with the single largest transfer routed to Australia.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
The consolidation of thirteen distinct, sub-$20,000 USD-denominated deposits into a single account, followed by rapid dispersal to fifteen accounts across nine countries and seven currencies within days, is consistent with funnel-account behavior in which small, individually unremarkable deposits are aggregated before redistribution to obscure origin. This is compounded by a severe scale mismatch: one outbound transfer ($154,264,039.64 AUD) dwarfs the entire gathered inbound total by roughly three orders of magnitude, meaning the bulk of outbound value bears no proportional relationship to the funds actually consolidated through this account. The uniform USD denomination on the gather side, contrasted with seven-currency diversity on the scatter side, further suggests the account functioned as a conversion and layering point rather than a legitimate operating account (see FinCEN Advisory FIN-2014-A005, Funnel Accounts and TBML; structural confirmation via Deprez et al. 2025, GARG-AML). While an account of this kind could plausibly represent a legitimate payment aggregator collecting receivables from multiple counterparties before disbursing payouts, such an arrangement would typically show outbound amounts proportionate to what was collected and consistent settlement currency — neither of which holds here, given the disproportionate single large-value transfer and the currency diversification specifically on the outbound side.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Thirteen unrelated sending accounts, none sharing a common institution, independently transferred sub-threshold USD amounts into the subject account over roughly three days. The subject account then redistributed funds outward across fifteen separate accounts spanning multiple currencies and jurisdictions, including one transfer of disproportionate scale relative to the account's apparent inbound capacity.

### Supporting Pattern

<!-- Reference to known typology. Pattern: GATHER-SCATTER -->
Pattern: GATHER-SCATTER (13-in / 15-out). Structural grounding: FinCEN Advisory FIN-2014-A005 (Funnel Accounts and TBML); Deprez, Baesens, Verdonck, Verbeke (2025), GARG-AML against Smurfing, citing Altman et al. 2023. Per typology_mapping.md.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
28 transactions total (13 inbound, 15 outbound); inbound total ≈ $108,004.74 (single currency, USD); outbound total includes one outlier transfer of $154,264,039.64 AUD plus 14 transfers ranging $211.15–$63,889.74 across six other currencies. Note: the file's aggregate "$158,505,163.63" statistic sums face values across seven currencies without conversion and should not be read as a single meaningful dollar total. 29 unique accounts, 28 unique banks, September 2–8, 2022 (159.3-hour window, gather and scatter phases overlapping on September 5).
