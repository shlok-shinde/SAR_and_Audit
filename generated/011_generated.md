# Generated SAR Narrative — Case 011

**Pattern:** STACK  
**Attempt #:** 240  
**Model:** gemma4:e2b (fallback: qwen3.5:4b)  

---

### Who (Subject Identification)

The activity involves 45 unique accounts across 43 distinct financial institutions, including entities registered as Partnerships, Corporations, and Sole Proprietorships such as `803D8E3A0` (Japan Bank #0, Partnership #31863) and `801314930` (Golden Bancorp, Partnership #3128), which served as both senders and receivers in the observed transactions.

### What (Suspicious Activity)

Between September 7 and September 11, 2022, thirty transactions moved funds across multiple currencies, including Australian Dollar, Euro, Mexican Peso, Rupee, Swiss Franc, UK Pound, US Dollar, Yen, and Yuan, through sequential transfers across various international banks, demonstrating rapid cross-border movement and complex currency conversion.

### When (Timeframe)

The suspicious activity spanned a 4-day period, from September 7, 2022, 09:34 to September 11, 2022, 18:32, involving 30 transactions within this timeframe.

### Where (Location)

The funds originated from and were dispersed across institutions in at least 9 countries, including Australia, Germany, Italy, China, Japan, Switzerland, Portugal, and the United States, utilizing 43 different financial institutions.

### Why Suspicious

The rapid movement of funds through multiple accounts and institutions, coupled with significant cross-currency conversions, is inconsistent with the typical financial activity of the registered entities. The activity aligns with patterns identified as funnel account activity and trade-based money laundering, where funds are dispersed across geographically distant branches to evade identification and record-keeping requirements, as described in FIN-2014-A005. While these transfers could represent legitimate international trade or personal remittances, the combination of high transaction velocity, multiple currency changes, and the use of numerous intermediary accounts strongly suggests layering designed to obscure the origin and destination of illicit proceeds.

### How (Method / Mechanism)

The funds were moved through a complex chain of thirty transactions, involving sequential ACH transfers between accounts held at different banks, often involving currency conversion within the flow, such as Yuan being converted to US Dollar, and US Dollar being converted to Rupee, across multiple institutions.

### Supporting Pattern

Pattern: STACK (nan). Structural grounding: FIN-2014-A005 (Funnel Accounts and Trade-Based Money Laundering); FATF Professional Money Laundering (2018), Box 6 (complex chain of e-wallets).

### Quantitative Summary

30 transactions total across 45 unique accounts and 43 unique banks, involving nine different currencies (Australian Dollar, Euro, Mexican Peso, Rupee, Swiss Franc, UK Pound, US Dollar, Yen, Yuan). The total sum of all transfer legs, paid, is $2,726,901.16 (Rupee) plus other amounts in various currencies. The activity occurred over a 4-day window.