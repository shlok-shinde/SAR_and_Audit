# Generated SAR Narrative — Case 003

**Pattern:** FAN-IN  
**Attempt #:** 285  
**Model:** gemma4:e2b (fallback: qwen3.5:4b)  

---

### Who (Subject Identification)

The subject account, 8079DDC30, held by Savings Bank of Butte, is the recipient account for all 16 inbound ACH transfers in this activity. The account is registered as a corporation with no prior SAR filings on record.

### What (Suspicious Activity)

Between September 8 and September 12, 2022, account 8079DDC30 received 16 inbound ACH transfers totaling $181,262.75, originating from 16 distinct senders across 17 unique financial institutions in various countries.

### When (Timeframe)

All 16 transfers occurred within a 94-hour window, from 2022/09/08 19:02 to 2022/09/12 14:15, indicating a rapid aggregation of funds over a four-day period.

### Where (Location)

Funds originated from 16 distinct sending accounts located in various countries, including Australia, France, Japan, Switzerland, and India, and were all consolidated into Savings Bank of Butte. This multi-jurisdictional convergence of funds into a single account is highly unusual for a standard corporate receiving account.

### Why Suspicious

The convergence of funds from sixteen unrelated senders across seventeen financial institutions into a single account within a four-day period is inconsistent with routine business receivables for a corporation of this size. The activity aligns with the Fan-In typology, where multiple deposits below reporting thresholds are aggregated into one account, which is a known method for structuring funds. While these transfers could represent legitimate business payments, the pattern suggests deliberate aggregation to obscure the true source and dispersal of the funds.

### How (Method / Mechanism)

Sixteen distinct originating accounts executed sequential ACH transfers, with each transfer routed to the subject account 8079DDC30, effectively aggregating funds from multiple sources into a single destination account over the specified timeframe.

### Supporting Pattern

Pattern: FAN-IN (16-degree). Structural grounding: FinCEN Case Example, July 2014, Case 7 (structuring/aggregation into a single account). This pattern is consistent with the mechanism described in the Gather-Scatter typology, where funds are collected from multiple accounts into one, then sent to many destinations.

### Quantitative Summary

16 transactions, $181,262.75 total, 17 unique accounts across 17 unique banks, US Dollar, ACH format exclusively, September 8–12, 2022 (94-hour window).