# Citation Index

Master bibliography for the AI Misalignment Incident Database. Every source cited in an incident entry must appear here, grouped by source type. Entries are added only after the source has been fetched and read in a verified-source research session.

**Current session-verified entries:** 2 (from 2 incidents across 2 sessions)

---

## Source-Type Categories

Citations are grouped by authoritative tier:

### A. Court Filings and Legal Rulings
*Docket numbers, court, date of filing/ruling, URL to official record.*

*(Empty — scaffold.)*

### B. Government and Regulatory Reports
*Issuing agency, report ID or title, publication date, URL to official release.*

**[B-001]** National Transportation Safety Board. *Collision Between Vehicle Controlled by Developmental Automated Driving System and Pedestrian, Tempe, Arizona, March 18, 2018.* Highway Accident Report NTSB/HAR-19-03, PB2019-101402, Notation 59392. Adopted November 19, 2019; reissued June 26, 2020 with title-page corrections. Washington, DC.
- Docket URL: `https://www.ntsb.gov/investigations/Pages/HWY18MH010.aspx`
- Full-report URL: `https://www.ntsb.gov/investigations/AccidentReports/Reports/HAR1903.pdf`
- Retrieved via WebFetch 2026-04-19 (docket page; PDF retrieved via WebFetch, parsed locally via Read tool, pages 1–12 of 78).
- Used in: Incident 1.

### C. Academic Papers (Peer-Reviewed)
*Author(s), title, journal/conference, DOI or preprint ID, year.*

*(Empty — scaffold.)*

### D. Official Disclosures (Company / Operator)
*Entity, disclosure title, date, URL to original statement.*

*(Empty — scaffold.)*

### E. Journalism (Established Outlets)
*Outlet, author, headline, date, URL.*

Accepted outlets (non-exhaustive): Reuters, Associated Press, The New York Times, The Wall Street Journal, Bloomberg, BBC, Financial Times, The Guardian, MIT Technology Review, ProPublica, STAT News, Wired (long-form investigative only), The Verge (long-form investigative only).

*(Empty — scaffold.)*

### F. Incident Databases and Aggregators
*Entry ID, aggregator, date of entry/last update, URL. Used only as navigational aids — every fact cited must trace back to a tier A–E primary source, not to the aggregator entry itself.*

Known aggregators: AI Incident Database (AIID, incidentdatabase.ai), MIT AI Risk Repository, OECD AI Policy Observatory, AlgorithmWatch.

**[E-001]** Koning, Merel (25 October 2021). "Dutch childcare benefit scandal an urgent wake-up call to ban racist algorithms." Amnesty International.
- URL: `https://www.amnesty.org/en/latest/news/2021/10/xenophobic-machines-dutch-child-benefit-scandal/`
- Retrieved via WebFetch 2026-04-19.
- Tier: 2 (NGO primary-in-English; Amnesty International).
- Used in: Incident 2.
- Linked full-report URL (pending parse, noted for Session 3+): `https://www.amnesty.org/en/documents/eur35/4686/2021/en/` (*Xenophobic Machines*, EUR 35/4686/2021).

---

## Rejected Sources

Sources that were fetched and excluded from a given incident. Reasons include: blog-of-blog chains, uncorroborated single-source claims, sources that contradicted more authoritative records, sources that were retracted or heavily corrected after initial publication.

*(Empty — scaffold.)*

---

## Session-Fetch Log

Every URL fetched in a verified-source session is recorded here, whether or not the incident was ultimately included. This gives us a reproducible audit trail — a reviewer can see exactly which sources were consulted when.

Format:
```
YYYY-MM-DD [session-id] | URL | status | used-for-incident-N-or-rejected
```

**Session 2026-04-19 (Session 1):**
```
2026-04-19 | https://www.ntsb.gov/investigations/Pages/HWY18MH010.aspx        | success                           | used for Incident 1 (NTSB docket index)
2026-04-19 | https://www.ntsb.gov/investigations/AccidentReports/Reports/HAR1903.pdf | success (retrieved); local Read parse needed | used for Incident 1 (NTSB full report, pp. 1–12 of 78)
2026-04-19 | https://www.reuters.com/article/us-autos-selfdriving-uber/...idUSKBN1GV296 | tool-blocked                      | not used; Tier 3 domain block
2026-04-19 | https://www.theguardian.com/technology/2018/mar/19/uber-self-driving-car-kills-woman-arizona-tempe | tool-blocked | not used; Tier 3 domain block
2026-04-19 | https://web.archive.org/web/2018/https://www.theguardian.com/... | tool-blocked                      | not used; Tier 3 (Wayback)
```

**Session 2026-04-19 (Session 2):**
```
2026-04-19 | https://decisions.civilresolutionbc.ca/                                                        | success                  | routing-only (no citation resolver); Air Canada deferred
2026-04-19 | https://canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html                         | HTTP 403                 | Tier 2 reclass; Air Canada deferred
2026-04-19 | https://decisions.civilresolutionbc.ca/crt/sd/en/nav.do                                        | HTTP 404                 | not used; Air Canada deferred
2026-04-19 | https://courtlistener.com/docket/?q=1%3A22-cv-01461-PKC&type=r                                 | HTTP 403                 | Tier 2 reclass; Mata deferred
2026-04-19 | https://nysd.uscourts.gov/opinions-significant-cases                                           | HTTP 404                 | not used; Mata nav
2026-04-19 | https://nysd.uscourts.gov/                                                                     | success                  | routing-only; Mata nav
2026-04-19 | https://nysd.uscourts.gov/cases/rulings-of-special-interest?combine=Mata                       | success (filter no-op)   | routing-only; Mata nav
2026-04-19 | https://nysd.uscourts.gov/cases/rulings-of-special-interest?page=9                             | success                  | routing-only; Mata nav (May–Feb 2023, no Mata)
2026-04-19 | https://nysd.uscourts.gov/cases/rulings-of-special-interest?page=8                             | success                  | routing-only; Mata nav (Oct–May 2023, Mata excluded)
2026-04-19 | https://nysd.uscourts.gov/search?keys=Mata+Avianca                                             | HTTP 404                 | not used; Mata deferred
2026-04-19 | https://www.nhtsa.gov/recalls?nhtsaId=23V838                                                   | HTTP 403                 | Amendment 6 data point; NHTSA deferred
2026-04-19 | https://api.nhtsa.gov/recalls/recallsByCampaign?campaignNumber=23V838                          | HTTP 403                 | Amendment 6 data point; NHTSA deferred
2026-04-19 | https://robodebt.royalcommission.gov.au/                                                       | timeout (>60s, x2)       | Amendment 6 new failure mode; Robodebt deferred
2026-04-19 | https://www.tweedekamer.nl/                                                                    | success                  | routing-only; Amendment 7 confirmed
2026-04-19 | https://www.houseofrepresentatives.nl/                                                         | success                  | routing-only; Amendment 7 second data point
2026-04-19 | https://www.amnesty.org/en/latest/news/2021/10/xenophobic-machines-dutch-child-benefit-scandal/ | success                  | **source-consuming — used for Incident 2**
```
