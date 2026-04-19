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

