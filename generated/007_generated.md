# Generated SAR Narrative — Case 007

**Pattern:** GATHER-SCATTER  
**Attempt #:** 49  
**Model:** gemma4:e2b (fallback: qwen3.5:4b)  

---

### Who (Subject Identification)

The subject account, 8075AC7C0, held by Savings Bank of Bridgeport, is the central account involved in the movement of funds. This account is registered as a partnership entity with no prior SAR filings on record.

### What (Suspicious Activity)

Between September 2 and September 8, 2022, account 8075AC7C0 initiated 15 outbound ACH transfers and received 13 inbound ACH transfers, resulting in the movement of funds across multiple currencies, including US Dollar, Australian Dollar, Brazil Real, Euro, Mexican Peso, Ruble, and Yen.

### When (Timeframe)

The activity spanned a seven-day period, commencing on September 2, 2022, at 03:26 and concluding on September 8, 2022, at 18:45.

### Where (Location)

The funds originated from 13 distinct senders across 28 financial institutions and were dispersed to 15 distinct recipients across various jurisdictions, including Australia, Brazil, Belgium, Canada, Italy, Japan, and the United States.

### Why Suspicious

The rapid and high-volume dispersal of funds across multiple currencies and numerous institutions from a single account within a seven-day window is inconsistent with the account holder's registered profile. The activity aligns with the Gather-Scatter pattern, which involves collecting funds from multiple sources and distributing them to many destinations, suggesting an attempt to fragment the traceability of the funds. While these transfers could potentially represent legitimate international business transactions, the combination of high transaction velocity, cross-currency conversion within the flow, and the sheer number of disparate counterparties strongly indicates an attempt to obscure the source and destination of the funds.

### How (Method / Mechanism)

Account 8075AC7C0 executed sequential ACH transfers, simultaneously receiving funds from 13 distinct senders and subsequently disbursing the total amount to 15 distinct recipients, involving complex cross-currency conversions (e.g., US Dollar to Australian Dollar, Euro, and Yen) during the flow.

### Supporting Pattern

Pattern: GATHER-SCATTER (Max 13-degree Fan-In). Structural grounding: FATF Professional Money Laundering (2018), Box 6, adapted to describe the collection from multiple accounts and distribution to many destinations. Per typology_mapping.md.

### Quantitative Summary

15 outbound transfers and 13 inbound transfers totaling $154,264,039.64 Australian Dollar, 63,889.74 Brazil Real, 21,814.61 Euro, 4,436.75 Mexican Peso, 2,462,123.00 Ruble, $155,311.78, and 1,533,548.11 Yen across 28 unique banks and 29 unique accounts over a 7-day period.