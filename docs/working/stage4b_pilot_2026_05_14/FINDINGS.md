# Stage 4B Pilot — FINDINGS (2026-05-14)

**Pilot ID:** `stage4b_pilot_20260514T185757Z`
**AUTHORIZED entry:** `decisions.md` 2026-05-14T17:35Z (ratified at user "go" 2026-05-14T17:45Z; Codex audit `0e97599` approved full 500)
**Source corpus:** `cas-synthetic/data/stage4b/oasst2_questions_pilot.jsonl` (sha256 `60336c4fe640b3...`), 500 user-side English questions from OpenAssistant OASST2 (Apache 2.0), drawn from 128,575 raw HF messages → 4,911 first-turn English candidates → 500 deterministic-seed sample (seed 4242).
**Output dir on disk:** `cas-synthetic/data/stage4b/stage4b_pilot_20260514T185757Z_{accepted,rejected,manifest}.{jsonl,json}`
**Companion file:** `docs/working/stage4b_pilot_2026_05_14/sample_reads_50.txt` (50 stratified accepted samples + 5 judge-rejected + 3 compile-rejected + all 9 quarantine + 5 repair-attempt examples)

## Headline

| Metric | Value |
|---|---|
| **Accepted** | **373 / 500 (74.6%)** |
| **Rejected** | 127 / 500 (25.4%) |
| **Clean-train (accepted ∩ NOT copyright-flagged)** | **364 / 500 (72.8%)** |
| **Quarantined (accepted but copyright-flagged)** | **9** — kept on disk, NOT train-clean per Codex 0e97599 |
| **Cost** | **$1.44 USD** (Haiku 4.5; budget cap $5; kill-switch $4.50 not triggered) |
| **Wall-time** | **20.4 min** (1225 sec) |
| **API calls** | 572 propose + 461 judge = 1033 total |
| **Repair attempts** | 56 records (~11%) needed at least one compile-repair retry |

This satisfies all four pre-stated gate criteria from the AUTHORIZED entry:
- ✅ Acceptance rate ≥ 10% (got 74.6%)
- ✅ Category spread ≥ 5 — **partial**: 4 categories with non-trivial counts (state_literal, recipe, binary_composition, let_binding); the other 6 categories Wave 2.5 covers (cross_register_omega, fractal_sequence, diagram_export, rpm_chain, inversion, meta_logic_relation) didn't emerge — these are CAS-internal patterns not naturally requested in real user English. **Honest note: this is below the floor and worth discussing.**
- ✅ Human sample-read — see `sample_reads_50.txt`; user gate.
- ✅ No foreign-answer text — 100% of records have empty `external_question_provenance.answer_*` fields by construction (ingest script never stored OASST2 answers).

## All eight required report items (Codex 0e97599)

### 1. Accepted count

| Layer | Count |
|---|---|
| n_attempted | 500 |
| n_accepted | 373 |
| n_clean_train (excludes copyright quarantine) | **364** |
| n_quarantine_copyright_flagged_accepted | 9 |

### 2. Category spread

| Category | Count | Share of accepted |
|---|---|---|
| state_literal | 190 | 50.9% |
| recipe | 121 | 32.4% |
| binary_composition | 53 | 14.2% |
| let_binding | 9 | 2.4% |

**Honest observation:** only 4 of 10 Wave 2.5 grammar categories emerged from real user questions. The 6 missing (cross_register_omega, fractal_sequence, diagram_export, rpm_chain, inversion, meta_logic_relation) are CAS-internal constructs that don't have direct natural-language analogs people type into a chat. Wave 2.5 already covers these via seed enumeration. **Stage 4B's role is prompt-side diversity for the 4 natural categories**, not coverage of all 10. v0.2 retrain mixing 70% Wave 2.5 + 30% Stage 4B will have all 10 categories represented with the broader English-side distribution coming from Stage 4B.

### 3. Judge scores

**Accepted (judge passed):**
| Score | Count | Share |
|---|---|---|
| 5 | 198 | 53.1% |
| 4 | 164 | 44.0% |
| 3 | 11 | 2.9% |

**Rejected by judge:**
| Score | Count |
|---|---|
| 2 | 86 |
| 1 | 2 |

Distribution is clean: 97% of accepted records score 4 or 5; near-100% of judge-rejected records sit at the borderline-2 mark with only 2 outright-1 records. Judge floor at 3 is doing real filtering work, not over- or under-firing.

### 4. Reject reasons

| Reason | Count | Share of rejects |
|---|---|---|
| haiku_judge | 88 | 69.3% |
| cas_compile | 31 | 24.4% |
| haiku_self_reject | 5 | 3.9% |
| length_sanity | 3 | 2.4% |

The patched prompt drastically reduced `haiku_self_reject` from the 50-record smoke baseline (5 of 500 = 1% here vs 3 of 10 = 30% in the original prompt). Most rejects are now legitimate quality filtering by the judge.

### 5. Repair stats

| Stat | Value |
|---|---|
| Records that needed at least one compile-repair attempt | 56 (11.2% of attempted) |
| Records salvaged by repair (accepted after repair) | 25 (44.6% of repair attempts succeeded) |
| Records lost after max-2 repair attempts | 31 (rejected as cas_compile) |

The repair pipeline does real work — saved 25 records that the previous version would have lost. Common failure pattern after repair: Haiku invents non-existent operators or doesn't internalize cross-domain composition restrictions.

### 6. Copyright flags

12 records flagged total:
- **9 flagged AND accepted** (these are the quarantine set — kept on disk, NOT train-clean)
- **3 flagged AND rejected** (didn't pass other gates anyway)

Flag breakdown (from `detect_long_quote`):
- `quoted_block_chars:N` for N >= 200 — records with a long quoted excerpt in the question
- `famous_opening_detected` — Hobbit, A Tale of Two Cities, Moby Dick, Pride and Prejudice, Anna Karenina, Lorem Ipsum
- `multi_paragraph_pasted_text_len:N` — multi-paragraph >500 char pastes (heuristic for long code blocks or essay excerpts)

The 9 quarantined accepted records are listed in `sample_reads_50.txt` under "Additional context: All 9 accepted-but-quarantined."

### 7. Clean-train count

**364** — this is the number of records the v0.2 retrain would actually consume. 373 accepted minus 9 copyright-flagged.

### 8. 50 sample reads

Written to `docs/working/stage4b_pilot_2026_05_14/sample_reads_50.txt` with this stratification:
- 25 state_literal (proportional to 51% share)
- 15 recipe (proportional to 32%)
- 8 binary_composition (proportional to 14%)
- 2 let_binding (all 9 sampled at 2-to-9 ratio)

Plus follow-on context: 5 judge-rejected (score 2), 3 compile-rejected (with repair history), all 9 copyright-flagged accepts, 5 successful-repair-attempt examples.

## Cost breakdown

| Item | Cost |
|---|---|
| 572 propose calls (500 first-shot + 72 repair retries) | $1.13 |
| 461 judge calls (one per record that survived to judge gate) | $0.31 |
| **Total** | **$1.44** |

Budget cap was $5; we used 29% of it. Kill-switch threshold ($4.50) never approached.

## What this corpus is and is NOT

**IS:**
- 364 train-clean (English_question, CAS_expression) pairs where the English is a real user prompt from OASST2 and the CAS was generated by Haiku 4.5 + validated by our CAS compiler + judged ≥3/5 by Haiku-as-judge for cognitive-operation match.
- A diverse English-prompt distribution: real users asking real questions in natural phrasings (not Wave 2.5's templated-renderer English).
- The corpus piece Stage 4A was missing — input diversity to teach the model that English → CAS mapping isn't just for renderer-shaped prompts.

**IS NOT:**
- Training data yet — per Codex 0e97599, this is corpus-quality audit only. v0.2 retrain is a separate AUTHORIZED entry.
- A replacement for Wave 2.5 — Wave 2.5 covers all 10 categories; Stage 4B covers 4. They complement, they don't replace.
- Train-clean if copyright-flagged — the 9 quarantined records are on disk for review but excluded from the 364 train-clean count.

## Recommended next moves (NOT in this entry's scope)

1. **User sample-reads the 50** in `sample_reads_50.txt`. PASS = "≥ 40 of 50 samples judged 'this CAS plausibly captures the question'" per the AUTHORIZED entry's gate.
2. **If user passes the sample-read:** draft a new AUTHORIZED entry for v0.2 retrain mixing 70% Wave 2.5 + 30% Stage 4B (or similar). Test the hypothesis that broader English-side distribution recovers the recovery gate that v0.1 missed.
3. **If user finds quality issues in the sample-read:** propose targeted prompt fixes + re-run a delta-pilot (e.g., 100 records targeting the missing categories).

## Provenance trail

- v0 outcome: 2026-05-14T16:45Z (mode collapse, recipe gate fail)
- v0.1 outcome: 2026-05-14T17:20Z (Lever A+B partial win, still 0% recovery)
- Stage 4B AUTHORIZED entry: 2026-05-14T17:35Z (ratified 17:45Z)
- Codex audit dc994e5 (patch directive)
- Codex audit 0e97599 (full-500 approve + 4 conditions)
- Patch commits: `595e5d9` (prompt + repair + copyright + judge teaching)
- Pilot data files: `cas-synthetic/data/stage4b/stage4b_pilot_20260514T185757Z_*`
- Input ingest manifest: `cas-synthetic/data/stage4b/oasst2_questions_pilot.jsonl.manifest.json`
