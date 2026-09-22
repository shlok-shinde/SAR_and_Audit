# Regulatory source documents

These seven PDFs are the corpus behind the retrieval layer — 843 chunks in ChromaDB, embedded by `src/embed_typology_docs.py`. They are **not committed** to the repository: they are third-party publications, and linking to the publisher is both safer and more honest than redistributing a copy that may go out of date.

Download them into this directory under the exact filenames below, then run:

```bash
.venv/bin/python src/embed_typology_docs.py
```

| Filename | Document | Publisher | Where |
|---|---|---|---|
| `FFIEC Appendix L.pdf` | *Appendix L: SAR Quality Guidance*, BSA/AML Examination Manual | FFIEC | [bsaaml.ffiec.gov/manual/Appendices](https://bsaaml.ffiec.gov/manual/Appendices) |
| `FIN-2014-A005(for gather-scatter).pdf` | Advisory FIN-2014-A005, *Update on U.S. Currency Restrictions in Mexico: Funnel Accounts and TBML* (28 May 2014) | FinCEN | [fincen.gov](https://www.fincen.gov/system/files/advisory/FIN-2014-A005.pdf) |
| `July2014_Case7(for fan-in).pdf` | *SAR Activity Review — Case 7: Suspicious Activity Reports Document Bank Transactions on Behalf of Drug Trafficker* (July 2014) | FinCEN | [fincen.gov](https://www.fincen.gov/sar-stats) |
| `Money laundering typologies 2000-2001(for cycle).pdf` | *Report on Money Laundering Typologies 2000–2001* (February 2001) | FATF | [fatf-gafi.org](https://www.fatf-gafi.org/en/publications/Methodsandtrends.html) |
| `Professional-Money-Laundering(for stacks).pdf` | *Professional Money Laundering* (July 2018) | FATF | [fatf-gafi.org](https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf) |
| `Trade_Based_ML_APGReport(for bipartite).pdf` | *APG Typology Report on Trade Based Money Laundering* (20 July 2012) | Asia/Pacific Group on Money Laundering | [apgml.org](https://www.apgml.org/methods-and-trends/page.aspx?p=8ca43d5c-d0d2-45c4-b874-ba9ff90ba81d) |
| `GARG-AML paper(for scatter-gather).pdf` | Deprez, Baesens, Verdonck, Verbeke — *GARG-AML against Smurfing: A Scalable and Interpretable Graph-Based Framework for Anti-Money Laundering* | Preprint (arXiv) | [arxiv.org/abs/2506.04292](https://arxiv.org/abs/2506.04292) |

The parenthetical in each filename records which IBM laundering pattern the document was sourced to ground — see [docs/TYPOLOGY_MAPPING.md](../docs/TYPOLOGY_MAPPING.md) for the full mapping.

`docs/TYPOLOGY_MAPPING.md` is embedded alongside these PDFs, so the retrieval layer also carries the project's own pattern-to-typology mapping.
