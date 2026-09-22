# Generated SAR Narrative — Case 003

**Pattern:** FAN-IN  
**Attempt #:** 285  
**Model:** gemma4:e2b (fallback: qwen3.5:4b)  

---

### Who (Subject Identification)

The subject account, 8079DDC30, held by Savings Bank of Butte, is the recipient account for all 16 inbound ACH transfers in this activity. The account is registered as a corporation with no prior SAR filings on record.

### What (Suspicious Activity)

Between September 8 and September 12, 2022, account 8079DDC30 received 16 inbound ACH transfers totaling $181,262.75, originating from 16 distinct senders across 17 unique financial institutions.

### When (Timeframe)

All 16 transfers occurred within a 94-hour window, from 2022/09/08 19:02 to 2022/09/12 14:15.

### Where (Location)

Funds originated from various institutions in Australia, France, Japan, Switzerland, and India, and were converged onto Savings Bank of Butte, demonstrating a multi-jurisdictional flow into a single account.

### Why Suspicious

The convergence of funds from sixteen unrelated senders across seventeen distinct financial institutions into a single account over four days is inconsistent with routine business receivables for an entity of this registered size. The activity aligns with the typology of Fan-In aggregation, where multiple deposits are collected into one account, which is a method used to facilitate the placement and layering of illicit funds (see FinCEN Case Example, July 2014, Case 7). This pattern is consistent with funnel account activity, where multiple deposits below reporting thresholds are collected before being withdrawn in a different geographic area.

### How (Method / Mechanism)

Sixteen distinct originating accounts across seventeen different banks independently transferred funds into the subject account, 8079DDC30, over the 94-hour period, demonstrating a mechanism of aggregation where funds from multiple sources were channeled into a single destination account.

### Supporting Pattern

Pattern: FAN-IN (16-degree). Structural grounding: FinCEN Case Example, July 2014, Case 7 (structuring/aggregation into a single account). Per `typology_mapping.md`.

### Quantitative Summary

16 transactions, $181,262.75 total, 16 unique accounts across 17 unique banks, single currency (USD), ACH format exclusively, September 8–12, 2022 (94-hour window).