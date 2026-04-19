# docs/ — Noetic Compass Evidence & Reference

This directory hosts reference material supporting the Noetic Compass platform, the peer-review paper, the book appendices, and regulator/stakeholder briefings.

## Navigation

### Primary document

- **[AI_MISALIGNMENT_INCIDENTS_DATABASE.md](AI_MISALIGNMENT_INCIDENTS_DATABASE.md)** — verified-source catalog of documented AI failures with CAS structural analysis. Grows one verified-source session at a time.

### Supporting taxonomy and claims

- **[INCIDENT_CATEGORIES.md](INCIDENT_CATEGORIES.md)** — definitions of the 12 CAS failure classes used in the main database.
- **[CAS_PREVENTION_CLAIMS.md](CAS_PREVENTION_CLAIMS.md)** — conservative subset: incidents where CAS-based prevention (not just detection) is defensible.
- **[REGULATORY_MAPPING.md](REGULATORY_MAPPING.md)** — CAS capabilities mapped to EU AI Act, NIST AI RMF, ISO/IEC 42001, and other instruments.

### Bibliography

- **[CITATION_INDEX.md](CITATION_INDEX.md)** — master bibliography of every source cited in the database, with the fetch log from every verification session.

### Machine-readable data

- **[data/incidents.json](data/incidents.json)** — structured records for every verified incident, 1:1 with the markdown entries.
- **[data/incident_analytics.json](data/incident_analytics.json)** — aggregate statistics, regenerated as incidents are added.
- **[data/rejected_candidates.md](data/rejected_candidates.md)** — candidates investigated and excluded, with reason.

## Source-rigor standard

Every incident in the main database has primary-source documentation that was fetched and read in the verification session where the incident was added. Citations from model memory are prohibited. If a source could not be fetched, the incident is either excluded or marked pending until a future session.

## Session protocol (short form)

Each verification session follows the five-step workflow defined in `AI_MISALIGNMENT_INCIDENTS_DATABASE.md`:

1. **Propose** a batch of 5–10 candidates and wait for approval.
2. **Fetch and verify**, one URL at a time, each fetch approved individually.
3. **Write** the incident entry using only facts traceable to the session's fetched sources.
4. **Commit** the main markdown, the JSON record, and the citation index update together.
5. **Report** — honest accounting of what was verified, what was rejected, and what remains pending.

Commit per session. Push only once at least three incidents in the session are fully verified.

## Current status

- **Verified incidents:** 1 (Session 1 of verified-source research, 2026-04-19)
- **Scaffold committed:** 2026-04-19
- **Most recent incident added:** Uber ATG fatal collision with pedestrian, Tempe, Arizona (NTSB HAR-19-03).
- **Methodology amendments in force:** 3 (see "Methodology Protocol Amendments" section of the main database file).
- **Next step:** Session 2 batch (proposed) — Mata v. Avianca, Air Canada chatbot, Robodebt Royal Commission, Dutch Childcare POK inquiry, NHTSA Tesla Autopilot investigation. All five are Tier 1 (government/court) primary sources.
