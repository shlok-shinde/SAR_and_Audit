# Regulatory source documents

These seven PDFs are the corpus behind the retrieval layer — 843 chunks in ChromaDB, embedded by `src/embed_typology_docs.py`. They are **not committed** to the repository: they are third-party publications, and linking to the publisher is both safer and more honest than redistributing a copy that may go out of date.

Download them into this directory under the exact filenames below. `fatf-gafi.org` refuses automated downloads (403), so fetch the FATF-hosted ones in a browser. Then run:

```bash
.venv/bin/python src/embed_typology_docs.py
```

| Filename | Document | Publisher | Where |
|---|---|---|---|
| `FFIEC Appendix L.pdf` | *Appendix L: SAR Quality Guidance*, BSA/AML Examination Manual | FFIEC | [bsaaml.ffiec.gov/manual/Appendices/13](https://bsaaml.ffiec.gov/manual/Appendices/13) — numbered 13, not 12, because "Appendix 1: Beneficial Ownership" precedes Appendix A |
| `FIN-2014-A005(for gather-scatter).pdf` | Advisory FIN-2014-A005, *Update on U.S. Currency Restrictions in Mexico: Funnel Accounts and TBML* (28 May 2014) | FinCEN | [fincen.gov](https://www.fincen.gov/system/files/advisory/FIN-2014-A005.pdf) |
| `July2014_Case7(for fan-in).pdf` | Case example, *Suspicious Activity Reports Document Bank Transactions on Behalf of Drug Trafficker* (July 2014) | FinCEN | [fincen.gov](https://www.fincen.gov/system/files/case_example/July2014_Case7.pdf) |
| `Money laundering typologies 2000-2001(for cycle).pdf` | *Report on Money Laundering Typologies 2000–2001* (February 2001) | FATF | No stable direct link found — search the FATF [Methods and trends](https://www.fatf-gafi.org/en/publications/Methodsandtrends.html) archive for the title |
| `Professional-Money-Laundering(for stacks).pdf` | *Professional Money Laundering* (July 2018) | FATF | [fatf-gafi.org](https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf) |
| `Trade_Based_ML_APGReport(for bipartite).pdf` | *APG Typology Report on Trade Based Money Laundering* (20 July 2012) | Asia/Pacific Group on Money Laundering, hosted by FATF | [fatf-gafi.org](https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Trade_Based_ML_APGReport.pdf.coredownload.pdf) |
| `GARG-AML paper(for scatter-gather).pdf` | Deprez, Baesens, Verdonck, Verbeke — *GARG-AML against Smurfing: A Scalable and Interpretable Graph-Based Framework for Anti-Money Laundering* | Preprint (arXiv) | [arxiv.org/abs/2506.04292](https://arxiv.org/abs/2506.04292) |

The parenthetical in each filename records which IBM laundering pattern the document was sourced to ground — see [TYPOLOGY_MAPPING.md](TYPOLOGY_MAPPING.md) for the full mapping.

`TYPOLOGY_MAPPING.md` (in this folder, committed) is embedded alongside these PDFs, so the retrieval layer also carries the project's own pattern-to-typology mapping.
