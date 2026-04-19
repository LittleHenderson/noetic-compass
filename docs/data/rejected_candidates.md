# Rejected Incident Candidates

Incidents that were investigated in a verified-source session and excluded. Recorded here so future sessions can revisit if new primary sources emerge.

Format:
```
## [Candidate name]
- Session: [date / id]
- Reason rejected: [insufficient sourcing / conflicting authoritative sources / entity dispute without adjudication / other]
- URLs attempted: [list]
- Notes: [specific gaps — what would need to emerge for re-inclusion]
```

## Moffatt v. Air Canada (2024 BCCRT 149)
- Session: 2026-04-19 (Session 2)
- Reason: Insufficient sourcing this session — not a permanent rejection. Three Tier 1 attempts failed:
  - `decisions.civilresolutionbc.ca/` — reachable but no citation resolver on the landing page (routing-only per Amendment 4).
  - `canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html` — HTTP 403 (server bot detection; precipitated Amendment 5).
  - `decisions.civilresolutionbc.ca/crt/sd/en/nav.do` — HTTP 404 (Lexum `nav.do` convention not deployed at this CRT instance).
- Notes: Candidate remains high-value and low-structural-difficulty. Revisit when (a) CanLII's bot detection is bypassable via a confirmed method, (b) the CRT exposes a citation-lookup URL pattern, or (c) user-assisted fetch (Path B) is activated for this specific incident. The decision is genuinely public — this is a delivery problem, not a sourcing problem.

## Mata v. Avianca, Inc. (1:22-cv-01461-PKC, S.D.N.Y., Judge Castel)
- Session: 2026-04-19 (Session 2)
- Reason: **Environment-constraint deferral, not sourcing failure.** The June 22, 2023 sanctions opinion is publicly available via PACER and has been widely reproduced in secondary literature, but is not reachable through the automated pipeline in this environment.
- Fetches attempted (six total — all navigation-only under Amendment 4; zero sources consumed against the 3-source limit):
  - `courtlistener.com/docket/?q=1%3A22-cv-01461-PKC&type=r` — HTTP 403 (server bot detection, same pattern as CanLII; precipitated Amendment 5 extension noting CourtListener is Tier 2 / reachable-but-refuses).
  - `nysd.uscourts.gov/opinions-significant-cases` — HTTP 404 (guessed slug).
  - `nysd.uscourts.gov/` — success; navigation identified `/cases/rulings-of-special-interest`.
  - `nysd.uscourts.gov/cases/rulings-of-special-interest?combine=Mata` — success but Drupal `combine` parameter silently no-op'd.
  - `nysd.uscourts.gov/cases/rulings-of-special-interest?page=9` — success; May–Feb 2023 entries, no Mata.
  - `nysd.uscourts.gov/cases/rulings-of-special-interest?page=8` — success; Oct 2023–May 2023 entries including Ripple Labs and People v. Trump, but **no Mata**. The curated index deliberately excluded this opinion despite including other June 2023-era significant rulings.
  - `nysd.uscourts.gov/search?keys=Mata+Avianca` — HTTP 404 (Drupal search endpoint not exposed at this path).
- Curation-exclusion finding: S.D.N.Y.'s decision not to feature Mata in its curated significant-rulings index (while featuring Ripple, Trump, Flores, Buyer from the same date range) is itself a datapoint — see the "Institutional Posture Observation" in `docs/INCIDENT_CATEGORIES.md` under Taxonomy Development Notes.
- Revisit when (a) CourtListener's bot detection is bypassable, (b) the opinion is hosted at another Tier 1 URL we haven't yet tested, or (c) user-assisted fetch (Path B) is activated for this specific incident.

## CourtListener as a Tier-2 source (general note, not incident-specific)
- Session: 2026-04-19 (Session 2)
- Observation: `courtlistener.com` returned HTTP 403 on first test, same bot-detection pattern as CanLII. This is a meaningful structural constraint because CourtListener was the expected primary access path for U.S. federal court decisions in this database. Its Tier 2 status lowers incidents-per-session estimates for U.S.-legal-heavy batches and implies that future Section 230 AI cases, algorithmic-bias class actions, and ChatGPT-hallucination cases will require `.uscourts.gov`-direct navigation per incident, case-by-case, rather than the more efficient CourtListener docket-query approach originally planned.
- Classification: Tier 2 (reachable-but-refuses). Precipitates extension of Amendment 5 beyond CanLII to cover CourtListener as well.

