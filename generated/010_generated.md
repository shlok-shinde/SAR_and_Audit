# Generated SAR Narrative — Case 010

**Pattern:** SCATTER-GATHER  
**Attempt #:** 271  
**Model:** gemma4:e2b (fallback: qwen3.5:4b)  

---

### Who (Subject Identification)

The activity involves multiple accounts, including Account 800AEAC00, held by Partnership #27410 at France Bank #75, which initiated the transfers. The funds were dispersed to 11 distinct recipients, including Account 8000EE420, held by Corporation #20093 at Germany Bank #65, and other accounts across 12 financial institutions.

### What (Suspicious Activity)

Between September 8 and September 12, 2022, the activity involved 22 ACH transfers, demonstrating a Scatter-Gather pattern where funds were sent from Account 800AEAC00 to 11 distinct recipients, resulting in a total of $234,486.65 in US Dollars and 283,702.93 Euro.

### When (Timeframe)

The transactions occurred over a 4-day period, spanning from 2022/09/08 08:02 to 2022/09/12 03:44.

### Where (Location)

The funds originated from France Bank #75 and were dispersed across 11 distinct receiving institutions in various countries, including Germany Bank #65, Arbor Savings Bank, Portugal Bank #43, China Bank #6, and Finland Bank #0.

### Why Suspicious

The rapid dispersal of funds from a single originating account across multiple international banks within a short timeframe is inconsistent with routine commercial activity. The activity exhibits clear layering behavior, utilizing multiple intermediary accounts and cross-currency conversions (US Dollar to Euro) to obscure the origin and destination of the funds. This pattern aligns with the Scatter-Gather typology, where funds are sent from one source to many destinations via multiple mule accounts, suggesting an attempt to fragment the money flow and evade detection thresholds (see GARG-AML paper(for scatter-gather).pdf). Alternative explanations for this activity could include complex international business settlements or multi-party investment transfers.

### How (Method / Mechanism)

Account 800AEAC00 executed 11 separate ACH transfers, sending a total of $234,486.65 in US Dollars and 283,702.93 Euro to 11 distinct recipients. These transfers involved multiple currency conversions within the flow, as evidenced by transfers between US Dollar and Euro accounts, routed through various intermediary accounts.

### Supporting Pattern

Pattern: SCATTER-GATHER (nan). Structural grounding: GARG-AML paper(for scatter-gather).pdf, which defines the pattern as money being sent from one source to its destination via multiple money mules. The activity involved 13 unique accounts across 12 unique banks, demonstrating the fragmentation of funds across multiple jurisdictions.

### Quantitative Summary

22 transactions total, $234,486.65 in US Dollars and 283,702.93 Euro, 13 unique accounts across 12 unique banks, ACH format exclusively, September 8–12, 2022 (103.5-hour window).