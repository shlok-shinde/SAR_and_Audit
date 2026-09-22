# Generated SAR Narrative — Case 010

**Pattern:** SCATTER-GATHER  
**Attempt #:** 271  
**Model:** gemma4:e2b (fallback: qwen3.5:4b)  

---

### Who (Subject Identification)

The activity involves multiple accounts, including 800AEAC00, 8001E6840, 8000EE420, 8001BA930, 80027A2B0, 8001576B0, 8009FD120, 8006A4A30, 8002DA960, 8003AA6D0, 8007F79F0, 8005A64B0, and 8005C1970, which are associated with various entities including Partnerships and Sole Proprietorships.

### What (Suspicious Activity)

Between September 8 and September 12, 2022, twenty-two ACH transfers totaling 737,324.99 Euro and $234,486.65 moved funds across 12 financial institutions, involving 13 unique accounts. The activity involved a complex flow where Account 800AEAC00 sent funds to 11 distinct recipients, and Account 8000EE420 received funds from 11 distinct senders.

### When (Timeframe)

The transactions occurred over a four-day period, spanning from September 8, 2022, 08:02 to September 12, 2022, 03:44, demonstrating rapid movement of funds.

### Where (Location)

The funds were dispersed across multiple jurisdictions and institutions, including France Bank #75, Arbor Savings Bank, Germany Bank #65, Portugal Bank #43, and various other financial institutions across Europe and the United States.

### Why Suspicious

The activity exhibits a Scatter-Gather pattern, where funds were collected from multiple sources and dispersed to many destinations, consistent with a money mule methodology. The rapid movement of funds through multiple accounts and institutions, coupled with currency conversions (US Dollar to Euro) within the flow, is inconsistent with the registered profiles of the account holders. This pattern aligns with the typology of scatter-gather, where money is sent via multiple mule accounts to obscure the origin and destination of the funds (see GARG-AML paper(for scatter-gather).pdf).

### How (Method / Mechanism)

The funds were moved through a sequence where Account 800AEAC00 initiated 11 transfers to various recipients, while Account 8000EE420 received 11 inbound transfers from these same recipients, utilizing sequential ACH transfers across different banks to fragment traceability. Currency conversion occurred within the flow, for example, between 8001BA930 and 8000EE420, suggesting layering to obscure the true movement of fiat currency.

### Supporting Pattern

Pattern: SCATTER-GATHER (nan). Structural grounding: GARG-AML against Smurfing (Deprez et al. 2025), which describes money being sent from one source to its destination via multiple money mules (one-to-many-to-one). This pattern is supported by the observation of funds being spread across 12 institutions and involving multiple cross-currency transfers.

### Quantitative Summary

22 transactions, $737,324.99 Euro and $234,486.65 total, involving 13 unique accounts across 12 unique banks, executed via ACH format between September 8 and September 12, 2022.