# Case 014 — BIPARTITE (8-tx Bipartite)

**Pattern:** BIPARTITE  
**Attempt #:** 344 (of 370)  
**Degree/Hop Info:** N/A  
**Narrative Status:** Draft pending  

---

## Summary Statistics

| Stat | Value |
|---|---|
| Transaction Count | 8 |
| Total Amount Paid | $1,373,256.74 |
| Total Amount Received | $1,373,256.74 |
| Min Amount | $647.73 |
| Max Amount | $1,085,990.71 |
| Date Range | 2022/09/10 11:09 → 2022/09/11 20:48 |
| Unique Accounts | 16 |
| Unique Banks | 15 |
| Currencies | Canadian Dollar, Euro, Mexican Peso, Rupee, US Dollar, Yuan |
| Cross-Currency? | No |
| Payment Format | ACH |

---

## Accounts & Entities Involved

| Account | Bank (ID) | Entity | Role |
|---|---|---|---|
| `80011FF60` | National Bank of the East (12) | Corporation #20099 | Sender |
| `80047AC40` | National Bank of Laramie (10) | Corporation #454 | Sender |
| `80235BCC0` | China Bank #6 (20) | Corporation #28307 | Receiver |
| `802410130` | France Bank #33 (3881) | Sole Proprietorship #22789 | Receiver |
| `802792890` | China Bank #6 (20) | Sole Proprietorship #23039 | Sender |
| `8029ADDF0` | France Bank #51 (1024) | Corporation #20467 | Receiver |
| `802B1AD20` | Germany Bank #536 (5425) | Corporation #20603 | Sender |
| `8041B2490` | Baltech Community Bank (15723) | Corporation #6431 | Sender |
| `804CF5230` | India Bank #40 (13157) | Partnership #32618 | Receiver |
| `80515A830` | Bank of Helena (25981) | Partnership #9261 | Sender |
| `805EF85E0` | Germany Bank #92 (15055) | Corporation #42035 | Receiver |
| `807DAC1F0` | Spruce Trust Bank (4403) | Sole Proprietorship #526 | Sender |
| `8086EB930` | Italy Bank #587 (14254) | Corporation #24742 | Sender |
| `8088B8A90` | Bank of Denver (18511) | Corporation #8549 | Receiver |
| `8093195F0` | Canada Bank #1 (24779) | Partnership #13377 | Receiver |
| `80B712AB0` | Canada Bank #26 (214) | Partnership #4261 | Receiver |

---

## Full Transaction Log

| # | Timestamp | From Bank | From Account | To Bank | To Account | Amount Paid | Payment Currency | Amount Received | Receiving Currency | Format |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2022/09/11 05:26 | Baltech Community Bank | `8041B2490` | China Bank #6 | `80235BCC0` | $105,545.24 | Yuan | $105,545.24 | Yuan | ACH |
| 2 | 2022/09/10 17:09 | National Bank of the East | `80011FF60` | Bank of Denver | `8088B8A90` | $18,105.95 | US Dollar | $18,105.95 | US Dollar | ACH |
| 3 | 2022/09/10 15:10 | Italy Bank #587 | `8086EB930` | Canada Bank #1 | `8093195F0` | $23,824.68 | Canadian Dollar | $23,824.68 | Canadian Dollar | ACH |
| 4 | 2022/09/11 20:48 | Spruce Trust Bank | `807DAC1F0` | Canada Bank #26 | `80B712AB0` | $122,507.63 | Mexican Peso | $122,507.63 | Mexican Peso | ACH |
| 5 | 2022/09/11 00:24 | Germany Bank #536 | `802B1AD20` | France Bank #51 | `8029ADDF0` | $1,156.69 | Euro | $1,156.69 | Euro | ACH |
| 6 | 2022/09/10 11:09 | Bank of Helena | `80515A830` | India Bank #40 | `804CF5230` | $1,085,990.71 | Rupee | $1,085,990.71 | Rupee | ACH |
| 7 | 2022/09/10 16:00 | National Bank of Laramie | `80047AC40` | France Bank #33 | `802410130` | $647.73 | Euro | $647.73 | Euro | ACH |
| 8 | 2022/09/11 11:36 | China Bank #6 | `802792890` | Germany Bank #92 | `805EF85E0` | $15,478.11 | Euro | $15,478.11 | Euro | ACH |

---

## SAR Narrative (FFIEC Format)

Write your gold-standard narrative below, covering all required elements:

### Who (Subject Identification)

<!-- Subject name/entity, account numbers, role, relationship to institution -->
This case involves eight single-hop transactions between two disjoint groups of accounts: eight distinct originating accounts and eight distinct destination accounts, with no account appearing in more than one transaction. Two of the sixteen entities involved — Sole Proprietorship #23039 (sender, account 802792890) and Corporation #28307 (receiver, account 80235BCC0) — are unrelated customers who happen to hold accounts at the same institution, China Bank #6, with one entity sending in this transaction set and the other receiving.

### What (Suspicious Activity)

<!-- Transaction types, amounts, instruments used -->
Between September 10 and September 11, 2022, eight independent ACH transfers moved funds from eight distinct originating accounts to eight distinct destination accounts, with no shared accounts between the origination and destination sides. Transaction amounts, once normalized for currency, fall within a comparatively narrow real-value range of approximately $667–$18,327 across six currencies (Canadian Dollar, Euro, Mexican Peso, Rupee, US Dollar, Yuan).

### When (Timeframe)

<!-- Dates/periods of suspicious activity -->
All eight transfers occurred within a 33.65-hour window, from September 10, 2022, 11:09 to September 11, 2022, 20:48 — a compressed timeframe for eight transactions between entirely unrelated account pairs.

### Where (Location)

<!-- Branches, jurisdictions, geographic indicators -->
The eight transactions span institutions across at least seven countries, including China, the United States, Italy, Canada, Germany, France, and India, with senders and receivers distributed across largely non-overlapping sets of jurisdictions.

### Why Suspicious

<!-- Explanation of why the activity is unusual, typology match -->
Eight single-hop transfers between eight entirely distinct account pairs, with no account repeating in either the sending or receiving role, is a topology that could describe eight unrelated customers making unrelated international payments. As in a comparable case reviewed elsewhere in this dataset, three features are difficult to reconcile with that reading: first, all eight transactions completed within a 33.65-hour window; second, two of the sixteen entities involved in this case — Sole Proprietorship #23039 and Corporation #28307 — are unrelated customers of a common institution, China Bank #6, one appearing as a sender and the other as a receiver elsewhere in the same window; and third, once currency face values are normalized, all eight transactions fall within a narrow real-value band of roughly $667–$18,327 — the file's own aggregate statistics ($1,373,256.74 total, $1,085,990.71 maximum) are inflated by summing the Rupee-denominated transaction ($1,085,990.71) at face value without conversion, which corresponds to approximately $13,660 once currency-adjusted, comfortably within the range of the other seven transfers. This combination — tight timing, two unrelated customers of a single institution appearing on opposite sides of the transaction set, and unusually uniform real-value sizing across nominally unrelated pairs — is more consistent with coordinated, deliberately structured activity than with organic, independent customer behavior, though the absence of any repeating account relationship means this case offers weaker structural grounding than typologies built on recurring related-party transactions (see APG Typology Report on Trade Based Money Laundering, 2012, related-party structuring discussion — cited here as a structural analogy given the absence of a closer topical match; the source describes trade/goods-based collusion between related parties, which does not directly apply to this dataset's transaction-only records). A burst of unrelated international transfers within a short window can occur coincidentally, but the presence of two unrelated customers of the same institution on opposite sides of the flow, combined with the narrow value banding across otherwise disconnected pairs, is not fully explained by coincidence alone.

### How (Method / Mechanism)

<!-- How the activity was conducted — structuring method, layering technique -->
Each of the eight transactions moved funds directly from a single originating account to a single destination account, with no intermediary hop and no account participating in more than one transaction.

### Supporting Pattern

<!-- Reference to known typology. Pattern: BIPARTITE -->
Pattern: BIPARTITE (8 disjoint single-hop pairs). Structural grounding: APG Typology Report on Trade Based Money Laundering (2012) — weakest citation in this project's typology mapping, as the source describes related-party trade collusion rather than this case's non-recurring transaction structure; treated as a structural analogy only. Per typology_mapping.md.

### Quantitative Summary

<!-- Total amounts, transaction counts, date ranges in aggregate -->
8 transactions total; 16 unique accounts across 15 unique banks (two unrelated entities at China Bank #6 appear as sender and receiver via separate accounts). Real transaction values, once currency-normalized, range approximately $667–$18,327; the file's raw aggregate statistics ($1,373,256.74 total, $1,085,990.71 maximum) are face-value artifacts from the unconverted Rupee-denominated transaction and do not reflect a genuine value outlier. September 10–11, 2022 (33.65-hour window).