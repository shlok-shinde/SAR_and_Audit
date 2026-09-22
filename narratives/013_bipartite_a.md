# Case 013 — BIPARTITE (15-tx Bipartite)

**Pattern:** BIPARTITE  
**Attempt #:** 163 (of 370)  
**Degree/Hop Info:** N/A  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 15 |
| Total Amount Paid | $2,578,276.47 |
| Total Amount Received | $2,578,276.47 |
| Min Amount | $1,547.94 |
| Max Amount | $1,888,824.55 |
| Date Range | 2022/09/05 08:13 → 2022/09/06 18:45 |
| Unique Accounts | 30 |
| Unique Banks | 29 |
| Currencies | Euro, US Dollar, Yen, Yuan |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `800928170` | Germany Bank #126 (410) | Partnership #51819 | Sender |
| `800A21910` | France Bank #40 (1299) | Sole Proprietorship #22551 | Receiver |
| `800BD1990` | National Bank of the East (12) | Sole Proprietorship #1783 | Receiver |
| `8019409A0` | Brownstone Bancorp (23885) | Sole Proprietorship #3852 | Receiver |
| `801A06BB0` | Plateau Community Bank (3242) | Sole Proprietorship #12917 | Receiver |
| `802583B00` | Italy Bank #84 (24850) | Partnership #52288 | Sender |
| `8029821C0` | Belgium Bank #87 (21918) | Corporation #20488 | Sender |
| `803249220` | First Bank of Lacrosse (6803) | Partnership #12454 | Sender |
| `80348E920` | National Bank of Detroit (1068) | Corporation #5523 | Sender |
| `8035A4F50` | China Bank #10 (18200) | Partnership #30399 | Receiver |
| `803AB9C40` | Japan Bank #8 (9679) | Corporation #30206 | Receiver |
| `803CEFB70` | Germany Bank #39 (15863) | Sole Proprietorship #3072 | Receiver |
| `80407D1F0` | Japan Bank #36 (19925) | Partnership #31639 | Sender |
| `80440A040` | Japan Bank #46 (10099) | Sole Proprietorship #31141 | Receiver |
| `804F0BFF0` | India Bank #36 (13078) | Corporation #30734 | Sender |
| `805DF0860` | First Bank of Springfield (10642) | Corporation #39946 | Receiver |
| `8068B91C0` | First Bank of Pittsburgh (215841) | Corporation #8882 | Receiver |
| `807B0DEE0` | Austria Bank #107 (16011) | Corporation #23985 | Receiver |
| `80832C3E0` | Italy Bank #201 (17610) | Sole Proprietorship #26423 | Sender |
| `808586D90` | Savings Bank of Fairfield (11813) | Partnership #12971 | Receiver |
| `808F215B0` | Future Cooperative Bank (2824) | Partnership #5329 | Sender |
| `80993EAE0` | Savings Bank of Montpelier (213580) | Partnership #16958 | Sender |
| `809DDA830` | Canada Bank #33 (24922) | Sole Proprietorship #50911 | Sender |
| `80B3A54F0` | First Bank of Danbury (5394) | Partnership #15777 | Sender |
| `80B5D7AC0` | France Bank #409 (115415) | Corporation #39460 | Receiver |
| `80B61F6E0` | Bank of Denver (18511) | Partnership #7795 | Sender |
| `80CADC170` | China Bank #30 (21381) | Partnership #31135 | Sender |
| `80CAED3D0` | China Bank #31 (131808) | Corporation #29001 | Sender |
| `80D2D89A0` | Brownstone Bancorp (23885) | Partnership #17482 | Receiver |
| `80D7E33E0` | National Bank of Dallas (35655) | Corporation #14941 | Receiver |

---

## Full Transaction Log

| #   | Timestamp        | From Bank                  | From Account | To Bank                   | To Account  | Amount Paid   | Payment Currency | Amount Received | Receiving Currency | Format |
| --- | ---------------- | -------------------------- | ------------ | ------------------------- | ----------- | ------------- | ---------------- | --------------- | ------------------ | ------ |
| 1   | 2022/09/06 17:34 | Germany Bank #126          | `800928170`  | France Bank #409          | `80B5D7AC0` | $15,555.56    | Euro             | $15,555.56      | Euro               | ACH    |
| 2   | 2022/09/06 08:37 | Future Cooperative Bank    | `808F215B0`  | National Bank of the East | `800BD1990` | $7,213.89     | US Dollar        | $7,213.89       | US Dollar          | ACH    |
| 3   | 2022/09/06 01:53 | China Bank #31             | `80CAED3D0`  | National Bank of Dallas   | `80D7E33E0` | $9,287.13     | US Dollar        | $9,287.13       | US Dollar          | ACH    |
| 4   | 2022/09/06 18:45 | First Bank of Danbury      | `80B3A54F0`  | France Bank #40           | `800A21910` | $11,950.68    | Euro             | $11,950.68      | Euro               | ACH    |
| 5   | 2022/09/06 12:07 | India Bank #36             | `804F0BFF0`  | Austria Bank #107         | `807B0DEE0` | $12,168.29    | Euro             | $12,168.29      | Euro               | ACH    |
| 6   | 2022/09/05 16:03 | Italy Bank #84             | `802583B00`  | Japan Bank #46            | `80440A040` | $570,286.33   | Yen              | $570,286.33     | Yen                | ACH    |
| 7   | 2022/09/06 09:27 | National Bank of Detroit   | `80348E920`  | Plateau Community Bank    | `801A06BB0` | $6,114.24     | US Dollar        | $6,114.24       | US Dollar          | ACH    |
| 8   | 2022/09/06 15:46 | Japan Bank #36             | `80407D1F0`  | Savings Bank of Fairfield | `808586D90` | $5,137.37     | US Dollar        | $5,137.37       | US Dollar          | ACH    |
| 9   | 2022/09/05 08:13 | Canada Bank #33            | `809DDA830`  | First Bank of Springfield | `805DF0860` | $1,547.94     | US Dollar        | $1,547.94       | US Dollar          | ACH    |
| 10  | 2022/09/06 11:00 | Italy Bank #201            | `80832C3E0`  | Japan Bank #8             | `803AB9C40` | $1,888,824.55 | Yen              | $1,888,824.55   | Yen                | ACH    |
| 11  | 2022/09/05 15:53 | First Bank of Lacrosse     | `803249220`  | Germany Bank #39          | `803CEFB70` | $6,457.02     | Euro             | $6,457.02       | Euro               | ACH    |
| 12  | 2022/09/05 12:55 | Bank of Denver             | `80B61F6E0`  | China Bank #10            | `8035A4F50` | $17,048.15    | Yuan             | $17,048.15      | Yuan               | ACH    |
| 13  | 2022/09/05 14:01 | China Bank #30             | `80CADC170`  | Brownstone Bancorp        | `80D2D89A0` | $2,109.50     | US Dollar        | $2,109.50       | US Dollar          | ACH    |
| 14  | 2022/09/05 23:43 | Belgium Bank #87           | `8029821C0`  | First Bank of Pittsburgh  | `8068B91C0` | $10,585.46    | US Dollar        | $10,585.46      | US Dollar          | ACH    |
| 15  | 2022/09/05 16:35 | Savings Bank of Montpelier | `80993EAE0`  | Brownstone Bancorp        | `8019409A0` | $13,990.36    | US Dollar        | $13,990.36      | US Dollar          | ACH    |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
This case involves fifteen single-hop transactions between two disjoint groups of accounts: fifteen distinct originating accounts and fifteen distinct destination accounts, with no account appearing in more than one transaction and no transaction occurring within either group. Two of the fifteen destination accounts — held by different entities, receiving from two different originators — are located at the same institution, Brownstone Bancorp.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 5 and September 6, 2022, fifteen independent ACH transfers moved funds from fifteen distinct originating accounts to fifteen distinct destination accounts, with no shared accounts between the origination and destination sides. Transaction amounts, once normalized for currency, fall within a comparatively narrow real-value range of approximately $1,500–$17,000 across four currencies (US Dollar, Euro, Yen, Yuan).

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
All fifteen transfers occurred within a 34.5-hour window, from September 5, 2022, 08:13 to September 6, 2022, 18:45 — an unusually compressed timeframe for fifteen transactions between entirely unrelated account pairs.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The fifteen transactions span institutions across at least ten countries, including Germany, France, the United States, Italy, Japan, India, Austria, Canada, Belgium, and China, with senders and receivers distributed across largely non-overlapping sets of jurisdictions.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Fifteen single-hop transfers between fifteen entirely distinct account pairs, with no account repeating in either the sending or receiving role, is a topology that could describe fifteen unrelated customers making unrelated international payments. Three features are difficult to reconcile with that reading: first, all fifteen transactions completed within a 34.5-hour window; second, two of the fifteen destination accounts, despite belonging to different entities and receiving from different originators, share a single receiving institution (Brownstone Bancorp); and third, once currency face values are normalized, all fifteen transactions fall within a comparatively narrow real-value band of roughly $1,500–$17,000 — the file's own aggregate statistics ($2,578,276.47 total, $1,888,824.55 maximum) are inflated by summing Yen and Yuan face values without conversion, and both apparent large-value Yen transactions (transactions 6 and 10) convert to approximately $3,800 and $12,600 respectively, comfortably within the range of the other thirteen transfers rather than representing genuine outliers. This combination — tight timing, one shared receiving institution, and unusually uniform real-value sizing across nominally unrelated pairs — is more consistent with coordinated, deliberately structured activity than with organic, independent customer behavior, though the absence of any repeating account relationship means this case offers weaker structural grounding than typologies built on recurring related-party transactions (see APG Typology Report on Trade Based Money Laundering, 2012, related-party structuring discussion — cited here as a structural analogy given the absence of a closer topical match; the source describes trade/goods-based collusion between related parties, which does not directly apply to this dataset's transaction-only records). A burst of unrelated international transfers within a short window can occur coincidentally, but the shared institution and narrow value banding across otherwise disconnected pairs are not fully explained by coincidence alone.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Each of the fifteen transactions moved funds directly from a single originating account to a single destination account, with no intermediary hop and no account participating in more than one transaction.

### Supporting Pattern

<!-- Reference to known typology. Pattern: BIPARTITE -->
Pattern: BIPARTITE (15 disjoint single-hop pairs). Structural grounding: APG Typology Report on Trade Based Money Laundering (2012) — weakest citation in this project's typology mapping, as the source describes related-party trade collusion rather than this case's non-recurring transaction structure; treated as a structural analogy only. Per typology_mapping.md.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
15 transactions total; 30 unique accounts across 29 unique banks (2 destination accounts share one institution, Brownstone Bancorp). Real transaction values, once currency-normalized, range approximately $1,500–$17,000; the file's raw aggregate statistics ($2,578,276.47 total, $1,888,824.55 maximum) are face-value artifacts from unconverted Yen and Yuan figures and do not reflect genuine value outliers. September 5–6, 2022 (34.5-hour window).