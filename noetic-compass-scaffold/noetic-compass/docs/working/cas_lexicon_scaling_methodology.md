# CAS Lexicon Scaling Methodology — Wave 2-A

**Status:** Design only. No production code in this document. No existing files modified.
**Author:** Wave 2-A background-agent dispatch, May 1, 2026.
**Audience:** the engineer/agent who picks up `cas-native/tokenizer/lexicon/` and grows it from 98 entries to 15K-30K.
**Scope:** methodology + tooling spec for source priorities, vetting, scaling cadence, inter-rater protocol, the `lexicon_extract.py` tool, demographic coverage, coverage metrics, and Wave 4 rollout gates.

This document is bound by CLAUDE.md "Authoritative Noetic Definitions" and "Colloquialism Test" sections, and by `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 6. Where this document and CLAUDE.md / Clarifications appear to disagree, those govern; flag the discrepancy and update this document, never the canon.

---

## 0. Non-negotiable constraints (read first)

1. **No external lexicons as primary sources.** WordNet, Roget's, BabelNet, ConceptNet, FrameNet, etc. may be consulted only as cross-checks during vetting. The "us or nothing" rule means every entry must be defensible from CAS material alone — colloquialism map, authoritative verbs, SDG corpus, expert curation. If an entry's only justification is "WordNet says so," it does not land.
2. **Anti-drift discipline is load-bearing, not aspirational.** Every entry passes the four anti-drift checks (`^3` visceral, `^8` associative, `^4` etymological-cognate preference, authoritative-verb preservation) before it is admitted. Methodology surfaces drift; it does not paper over it.
3. **Universal Applicability Test is a gate.** A lexicon entry's signature must apply to human minds, AI systems, biological cognitive systems, and hypothetical cognitive architectures equally. Anthropomorphizing a definition (e.g., reading `^2 Positive` as "feeling fond of") fails the gate.
4. **Authoritative verbs preserved verbatim.** "Affinity for," "attracted toward," "adverse to," "repelled by," "resonates with," "impregnated with," "triggers," "brought to Mind." When an entry's `notes` field cites a verb, the wording matches the canonical definition exactly.
5. **The seed lexicon is the source of truth for v1 conventions.** Any new entry that conflicts with the conventions in `build_seed.py` (confidence tiers, role-tag vocabulary, axis sign discipline) must either follow the convention or trigger a methodology amendment via PR.

---

## 1. Source priorities (ranked)

Sources are ranked by canonical authority. Higher-ranked sources contribute first; lower-ranked sources fill gaps and require stricter vetting.

### Priority 1 — Authoritative CAS material (canonical anchors)

The 10 authoritative Noetic definitions, the canonical colloquialism map, the authoritative verbs, and the four anti-drift annotations from CLAUDE.md / Clarification 6. These are already exhausted in the 98-entry seed; the only growth here is (a) **morphological expansions** of existing canonical anchors (e.g., `resonates with → resonate, resonates, resonating, resonated, resonance` as separate entries with consistent axis vectors), and (b) **inflectional and tense variants** that should not be left to the learned tagger.

Estimated headroom: ~250-400 additional entries (morphology and inflection).

### Priority 2 — CAS framework material outside the colloquialism map

Terminology load-bearing in CAS itself: domain names, drive names, register names, RPM-chain vocabulary, inversion-axis names, NCCS scoring vocabulary, capability-pathway labels, and the verbatim phrases used in the book manuscript Chapters 2-21, the peer-review paper, the `INCIDENT_CATEGORIES.md` taxonomy, and the operations manual. These are vocabulary the system must recognize when the user *talks about CAS* (regulator-facing, pedagogical, incident-analysis).

Vetting rule: each phrase gets a signature derived from the CAS structure it names. "Domain Coherence" carries the `domain` axis tagging by definition; "Limiting Reagent" carries v7.6 production-semantics role tags. No interpretation involved; the source IS the signature.

Estimated headroom: ~600-1,000 entries.

### Priority 3 — SDG-derived high-association vocabulary

The Level-3 conversational SDG corpus pairs `user_prompt` natural-language text with explicit `cas_expression`, `soft_operator_targets`, `soft_domain_targets`, and `tags`. This is the largest source of *empirical* word-axis correlation in the project. The methodology is:

- Tokenize all prompts, count word frequencies per (Noetic, Domain, Drive, Register) target axis.
- Compute a per-word association score: `lift(word, axis) = P(axis | word) / P(axis)`. Filter to words with corpus frequency ≥ N_min and lift ≥ L_min on at least one axis.
- Score the *top remaining axis lift* per candidate; surface the candidate with `(word, primary_axis, primary_lift, secondary_axes_with_lift>1.5)`.
- Candidates that survive the lift filter enter the vetting protocol below. SDG-mined candidates do NOT auto-land — they are *proposed* entries. Every proposed entry is sanity-checked against the canonical Noetic definition and the colloquialism map before commit.

This is the primary channel for getting from 1K to 10K+ entries. Discipline: **lift correlation is evidence, not authorization.** The SDG corpus is generated from CAS templates, so the correlation is real; but the templates can carry their own drift, and high lift can come from confounded co-occurrence (e.g., the word "preserve" lifts highly on `v75_register` repair-check templates because of template wording, not because "preserve" is intrinsically register-laden). Vetting catches this.

Estimated headroom: ~10,000-20,000 entries (the bulk of growth).

### Priority 4 — Parallel-register variants for demographic coverage

Once a Priority-1/2/3 entry lands, the methodology requires generating its **register-parallel variants** (academic / working_class / child / regional dialect / professional jargon / cross-cultural English) — each with the *same* CAS-axis vector, differing only in surface form and `register_variants` metadata. The seed already does this for `tired → exhausted → hella tired → super sleepy → profoundly fatigued` on F3 vitality; production-scale needs full parallel coverage.

This source is *derivative* — variants do not introduce new CAS structure; they assert that an existing CAS structure has multiple natural-language realizations. This is the demographic-robustness guarantee at the lexicon level.

Estimated headroom: ~3,000-6,000 variant entries (multiplicative on Priority-1/2/3 base).

### Priority 5 — Expert-curated edge cases for AI-safety scenarios

Manipulation vocabulary, Overton-window-drift markers, jailbreak phrasings, sycophancy markers, deceptive-compliance markers, refusal-bypass attempts. These are too rare in the SDG corpus and too high-stakes to leave to mined statistics. Curated by the safety team against the 12-class CAS failure taxonomy in `INCIDENT_CATEGORIES.md` and the verified-source incidents in `AI_MISALIGNMENT_INCIDENTS_DATABASE.md`.

Vetting is strictest here: every safety-edge entry requires two-rater agreement (see Section 4) and a citation to a specific incident or scenario.

Estimated headroom: ~500-1,500 entries. Ongoing — never "done."

**Total target:** 15K-30K entries by end of Wave 4 lexicon-readiness gate, distributed roughly 2% Priority 1, 5% Priority 2, 65-75% Priority 3, 15-20% Priority 4, 3-5% Priority 5.

---

## 2. Vetting protocol (per-candidate)

Every candidate entry — regardless of source — runs through this gate before it appears in `seed_lexicon.jsonl` or any successor file. Failures are kicked back to the proposer with a typed reason; they do not silently drop, because dropped candidates without a reason re-emerge later as the "same" mistake.

### Gate 2.1 — Colloquialism Test

Per Clarification 6: write down the most natural colloquialism a native speaker would use for the phenomenon the candidate names, then match it against the canonical map (CLAUDE.md "Colloquialism Test" section). Three outcomes:

- **Clean match** to one canonical colloquialism family → primary axis confirmed; proceed.
- **No match** → drift signal. Candidate is rejected as a single-axis entry; may be reproposed as a compound or as a non-axis role-tagged entry (e.g., `confidence_hedge`, `demonstrative`).
- **Multiple matches** → compound expression. Candidate must declare a compound signature (multiple non-zero axes with documented role tags) or be split into multiple entries.

Outcome and supporting colloquialism are recorded in the entry's `notes` field — not as decoration, as audit trail.

### Gate 2.2 — Anti-drift checks

Mechanical, performed after Gate 2.1:

- If primary axis is `^3 Negative`: check for analytical-critique vocabulary (audit, scrutinize, examine, dissect, find-flaws). Presence forces re-classification to `^6 Male`. The seed lexicon's `audit` and `scrutinize` entries are the load-bearing exemplars.
- If primary axis is `^8 Above/Cause`: check for deductive-reasoning vocabulary (therefore, hence, implies, because-it-follows). Presence forces re-classification to `^6 + ^9` compound. Surface-level `because` is allowed only as a weak `^9` link with `effect_link` role tag (see seed convention).
- If primary axis is `^4 Vibration`: prefer etymological cognates (struck-a-chord, resonance, vibration-of, hit-a-note) when the candidate has one. Non-cognate phrasings get lower confidence even when they match.
- Authoritative-verb preservation: if the candidate's `notes` cites an authoritative verb, the wording must match exactly. "Adverse to" is canonical; "averse to" / "averse-against" / "feels averse" are surface variants whose `notes` must say "authoritative verb: 'adverse to'" not paraphrase.

### Gate 2.3 — Universal Applicability Test

For each non-zero axis in the proposed signature, the reviewer must mentally substitute four cognitive substrates: human mind, AI system, biological non-human cognition, hypothetical artificial cognition. The signature must remain coherent across all four. If "drawn to" is `^2 Positive` for a human, it must also be `^2 Positive` for an LLM that places higher probability on a phrase, and for a moth that flies toward light. A candidate that requires anthropomorphic framing to make sense fails the gate.

### Gate 2.4 — Compositional consistency

If the candidate is multi-word, check whether its components are already in the lexicon and whether the proposed signature is consistent with simple composition. Sharp inconsistency (e.g., proposing `^2` for a multiword whose components individually score `^3`) signals either (a) a real idiomatic inversion that the entry must justify in `notes`, or (b) a mis-classification. Either is information; neither is silently absorbed.

### Gate 2.5 — Confidence tier discipline

Per `build_seed.py` lines 96-103:

- 1.00 — verbatim CAS notation literal (handled by the recognizer, never by the lexicon).
- 0.90-0.95 — canonical colloquialism / authoritative verb / etymological cognate.
- 0.80-0.89 — strong domain-specific term.
- 0.70-0.79 — single content word with clear axis affinity.
- 0.55-0.69 — common word with weak axis bias.

A candidate's confidence must match its provenance. SDG-mined entries that are not canonical colloquialisms cannot be confidence ≥ 0.9. Inflating confidence to land an entry is a vetting failure.

### Gate 2.6 — Schema validation

Final mechanical check: the entry passes `LexiconEntry.validate()` (non-empty surface, confidence in (0.0, 1.0], multiword flag matches whitespace, regex predicates compile, signature axis lengths correct). Surface duplicates are rejected.

---

## 3. Scaling cadence

### 3.1 Batch model

Lexicon growth happens in **named, dated, signed batches**. Each batch is a PR adding N entries, with:

- A batch manifest (YAML) listing each new entry, source priority, primary axis, vetting decisions, reviewer signatures.
- A regenerated `seed_lexicon.jsonl` (or successor file).
- A delta to a typed Python source-of-truth (so `build_seed.py` discipline scales — the JSONL is generated, not hand-edited).
- CI-enforced anti-drift tests run on the full lexicon, not just the delta.

Batch size targets:

- Bootstrap phase (entries 99 – ~2,000): 50-150 entries per batch, weekly cadence. High human review proportion (≥ 50%).
- Growth phase (~2,000 – ~10,000): 200-500 per batch, weekly cadence. Mixed automation and human review (~25% direct human review; 100% gate-checked).
- Saturation phase (~10,000 – ~25,000): 500-1,000 per batch, biweekly cadence. Bulk SDG-mined Priority-3, automation-vetted with sampled human audit (~10%).
- Maintenance phase (post-rollout): targeted batches against eval gaps, no fixed cadence.

### 3.2 CI lexicon-coverage gate

CI runs on every PR that modifies lexicon files:

- All existing anti-drift property tests (`test_seed_lexicon_anti_drift_visceral_negatives`, etc.) pass against the full updated lexicon.
- Per-axis density floor (Section 7) holds.
- Round-trip: regenerate JSONL from typed source, byte-identical.
- Schema validation on all entries (`LexiconEntry.validate()` returns empty list for every entry).
- Recall@k metric (Section 7) does not regress against the held-out NL eval set; tolerance ±0.5 absolute pp.
- New-entry sample: CI randomly selects 5% of new entries and re-runs the full vetting gate as an automated audit. If automated audit fails on any sampled new entry, CI fails.

### 3.3 Human-review proportion by source

| Source priority | Human review proportion | Automation discipline |
|---|---|---|
| Priority 1 (CAS canonical) | 100% | Two reviewers; trivial morphology may be one. |
| Priority 2 (CAS framework material) | 100% | One reviewer; cross-check against book manuscript / paper. |
| Priority 3 (SDG-mined) | 25% direct, 100% gated | `lexicon_extract.py` (Section 5) runs all gates automatically; sampled batch goes to human reviewer. |
| Priority 4 (register variants) | 25% direct | Variant must share CAS axes with parent entry within a tolerance band; CI enforces. |
| Priority 5 (safety edge) | 100%, 2-rater | Citation to incident/scenario required. |

---

## 4. Inter-rater protocol

When multiple human reviewers examine the same candidate or batch:

### 4.1 The framework is the arbiter

CAS, the canonical Noetic definitions, the colloquialism map, and the anti-drift annotations are the source of truth. Reviewer disagreement is treated as **information about the candidate's ambiguity, not as a vote to be averaged.** A "compromise" entry — splitting the difference between two reviewer signatures — is forbidden because it would launder ambiguity into the lexicon and propagate drift.

### 4.2 Disagreement resolution procedure

1. Reviewers each record their proposed signature and the supporting colloquialism.
2. If colloquialisms differ: the candidate is a probable compound expression. It is either split into two entries (each with its single colloquialism) or admitted as a single compound entry with both reviewers' axes ANDed.
3. If colloquialisms agree but signatures differ: the disagreement is on confidence/intensity, not structure. Take the lower confidence. (Confidence is a calibration claim, not an averaging target.)
4. If colloquialisms agree and signatures agree on primary axis but differ on secondary axes: the entry lands with only the primary axis; secondary axes are noted as "unresolved" and queued for the learned tagger (Wave 2-B) rather than committed to the lexicon.
5. If no colloquialism in the canonical map fits: the candidate is **rejected from this batch and queued for Clarification update**. Lexicon entries do not invent new Noetic semantics; if the project genuinely needs a new colloquialism family, it goes through `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, not through the lexicon. This is the load-bearing inversion of the usual "let's just add it" pressure.

### 4.3 Logged outcomes

Every disagreement and its resolution is logged in `docs/working/lexicon_review_log.md` (created on first use) with date, candidate, reviewers, disagreement category, and resolution. Repeated disagreements on the same axis or colloquialism family signal a documentation gap and trigger a Clarification PR.

---

## 5. Tooling spec — `lexicon_extract.py` (do NOT implement here)

A standalone Python module under `cas-native/tokenizer/lexicon/tools/lexicon_extract.py`. Design only.

### 5.1 Inputs

- `--corpus` — path or glob of CAS SDG JSONL files (e.g., `cas-synthetic/data/level3_*.jsonl`).
- `--existing-lexicon` — path to current lexicon JSONL (used to avoid duplicate proposals and to compute consistency scores against accepted entries).
- `--min-frequency` — minimum corpus frequency for a candidate word (default 25).
- `--min-lift` — minimum lift on at least one CAS axis (default 1.8).
- `--max-candidates` — upper bound on output proposals per run (default 1,000).
- `--axis-filter` — optional subset of axes to mine for (e.g., `noetic:3,4,8` or `drive:F3` to backfill known coverage gaps).
- `--out` — output directory for diff-ready JSONL chunks.

### 5.2 Outputs

- `proposals.jsonl` — one candidate per line. Each carries: surface, candidate signature (axes with lift ≥ threshold), provenance (corpus filepath, line indices, count), top-3 colloquialism map suggestions matched by string-similarity to canonical anchors, automated vetting outcome (per-gate pass/fail with reason).
- `proposals_review.md` — human-readable companion: each proposal as a card with corpus evidence (5 example user_prompts using the word), the proposed signature, the suggested colloquialism, the gate-by-gate verdict, and a "Reviewer decision" checkbox row (`[ ] accept | [ ] reject | [ ] revise → ___ | [ ] split`).
- `proposals_rejected_auto.jsonl` — candidates the automated gates rejected, with typed rejection reasons. Kept for audit; never dropped silently.
- `proposals_diff.jsonl` — accepted proposals formatted as ready-to-merge `LexiconEntry.to_dict()` payloads. This is the file the human reviewer's merge produces.

### 5.3 Scoring functions

- `frequency(word, corpus) -> int`.
- `axis_lift(word, axis, corpus) -> float` — per the formula in Section 1.3.
- `consistency_with_existing(candidate_sig, lexicon) -> float` — for each existing entry whose surface is morphologically related (shared lemma, edit distance ≤ 2, or shared prefix/suffix), measure cosine similarity of signatures. High consistency boosts confidence; sharp inconsistency triggers a manual-review flag.
- `colloquialism_match(word, canonical_map) -> list[(family, score)]` — string-similarity (rapidfuzz or equivalent) against the canonical colloquialism anchors plus the surface forms of accepted lexicon entries with the same primary axis. Output ranked.
- `anti_drift_check(candidate) -> list[str]` — runs the four anti-drift annotations mechanically. Returns failure reasons (empty list = pass).
- `confidence_estimate(candidate) -> float` — derived from frequency, lift, consistency, colloquialism match strength. Clamped to (0.0, 0.85] for SDG-mined entries (they cannot claim canonical-colloquialism tier; Priority-1 is the only path to ≥ 0.9).

### 5.4 Vetting integration

`lexicon_extract.py` runs the full Section 2 vetting protocol on every proposal as an automated pre-filter. Failures go to `proposals_rejected_auto.jsonl` with reason. Passes go to `proposals.jsonl` for human review. **A pass at this stage is not admission;** it is a queue position.

### 5.5 Diff-ready chunking

Output JSONL files are chunked by primary axis (`proposals_noetic_2.jsonl`, `proposals_drive_F3.jsonl`, etc.) with ≤ 200 entries per chunk, so PRs stay reviewable. The merge script (separate, not in scope here) takes accepted chunks and integrates them into the typed source-of-truth Python file, then regenerates the JSONL.

### 5.6 What `lexicon_extract.py` MUST NOT do

- Auto-merge accepted entries.
- Modify the existing lexicon file.
- Use external pretrained NL models for embedding similarity (the "us or nothing" rule). Word similarity uses surface-level metrics (rapidfuzz, lemma matching, edit distance, shared canonical-axis context windows) and signature-level cosine on already-accepted CAS axes.
- Use external lexicons (WordNet, etc.) as primary authority. They may appear as a *cross-check column* in `proposals_review.md` showing whether the external lexicon agrees, but agreement is not authorization and disagreement is not rejection.

---

## 6. Demographic coverage plan

The seed has 3 register variants on 1 axis (F3 vitality) as a smoke test. Production targets, by register variant, total parallel-coverage entries:

| Register variant | Description | Target count | Notes |
|---|---|---|---|
| `academic` | Formal, register-precise, hedge-laden | 1,200 | Source: peer-review paper, book manuscript Ch.2-21, professional journals. |
| `working_class` | Vernacular, intensifier-heavy ("hella," "real," "dead"), short clauses | 800 | Source: SDG demographic-extension corpus (Wave 3), curated. |
| `child` | Age-band aware (5-7, 8-11, 12-15); simple syntax, intensifier "super," "really" | 600 | Three age sub-bands × ~200 each. |
| `regional_dialect_us_south` | "Fixin' to," "y'all," "ain't" | 250 | |
| `regional_dialect_us_neng` | New England compounds, "wicked" intensifier | 200 | |
| `regional_dialect_uk` | "Knackered," "gobsmacked," "chuffed" | 350 | High-yield for `^3` aversion and `^4` vibration. |
| `regional_dialect_aus_nz` | "Stoked," "rooted," "shattered" | 200 | |
| `regional_dialect_caribbean_english` | "Vex," "joygi" | 150 | |
| `regional_dialect_indian_english` | Indian-English idiom | 250 | |
| `regional_dialect_west_african_english` | West-African English idiom | 150 | |
| `professional_jargon_medical` | "Affect," "presentation," "ideation" | 500 | Note: clinical "affect" must NOT collide with Register `|f`; flagged for context_required disambiguation. |
| `professional_jargon_legal` | "Ipso facto," "prima facie," "actus reus" | 400 | |
| `professional_jargon_engineering` | "Decompose," "fault-tolerant," "fail closed" | 400 | |
| `professional_jargon_finance` | "Risk-on / risk-off," "exposure," "haircut" | 300 | |
| `professional_jargon_aiml` | "Hallucinate," "drift," "alignment," "RLHF" | 400 | High importance for safety scenarios. |
| `cross_cultural_english_l2` | English as additional language; simplified syntax, calques | 500 | Captures phrasings non-native speakers actually produce. |

**Total parallel-coverage target: ~6,650 register-variant entries**, layered on top of the Priority-1/2/3 base.

Discipline: every register variant must share its parent's primary CAS axis within a tolerance of ±0.10 on the primary, ±0.15 on each secondary. CI enforces this. A variant that *changes* the axis is not a register variant — it is a different entry, vetted independently.

---

## 7. Coverage metrics — "is the lexicon done enough?"

### 7.1 Recall@k against held-out NL corpus

Held-out: 2,000 user prompts from the level-3 corpus, never seen by `lexicon_extract.py` and never used to derive entries. For each prompt, count what fraction of content words (non-stopword, non-CAS-notation) are covered by a lexicon entry that asserts at least one non-zero CAS axis.

Targets:
- Bootstrap-phase floor: Recall@content-words ≥ 0.30
- Growth-phase target: Recall@content-words ≥ 0.55
- Saturation-phase target: Recall@content-words ≥ 0.75
- Wave-4 readiness gate: Recall@content-words ≥ 0.80

### 7.2 Per-axis density floor

Per-axis entry count must clear a floor; per-axis vocabulary cannot be lopsided.

- Each Noetic `^0`-`^9`: ≥ 200 entries with that as primary axis.
- Each Domain P / C / E / O: ≥ 100 entries with that as primary domain.
- Each Drive F1-F7: ≥ 80 entries with that as primary drive.
- Each Register T / A / f / E: ≥ 80 entries with that as primary register.
- Compound (multi-axis) entries: ≥ 1,500 total.

CI fails if any floor is violated, with a clear "Drive F2 has only 73 entries; minimum 80" message.

### 7.3 Demographic robustness eval pass rate

A specialized evaluator runs the 16 register-variant cohorts (Section 6) against an axis-prediction task: given a prompt with a register-variant phrase, the tokenizer must produce the same primary CAS axis as the academic-register parent. Pass rate target ≥ 0.95 per cohort. Cohorts with pass rate < 0.90 are flagged for variant-pair audit.

### 7.4 Anti-drift property-test count

The seed has 6 load-bearing anti-drift tests. Each major batch should add at least one new property test if it touches a new colloquialism family, and the test count tracks the lexicon's structural diversity. Wave-4 floor: ≥ 60 anti-drift property tests.

### 7.5 Confidence-tier distribution

Healthy lexicon distribution: ~5-8% confidence ≥ 0.9 (canonical anchors), ~30-40% in 0.75-0.89 (strong domain terms), ~50-60% in 0.55-0.74 (common content words). Massive concentration at 0.85 with no spread (the failure mode where reviewers default to a comfortable middle confidence) flags calibration drift.

---

## 8. Wave 4 GPU-training rollout gates

Before lexicon ships into Wave 4 GPU encoder training:

1. **Size:** ≥ 15,000 entries.
2. **Recall@content-words ≥ 0.80** on held-out NL eval set.
3. **Per-axis density floors all met** (Section 7.2).
4. **Demographic-robustness eval pass rate ≥ 0.95** on 12 of 16 cohorts; ≥ 0.90 on all 16. (No cohort below 0.90.)
5. **Anti-drift property tests ≥ 60**, all green.
6. **Inter-rater audit:** sample 200 entries at random; two-reviewer audit; cohen's kappa on primary-axis agreement ≥ 0.85.
7. **Round-trip determinism:** typed-Python source generates byte-identical JSONL across three independent runs.
8. **Confidence-tier distribution within healthy bands** (Section 7.5).
9. **Zero outstanding Clarification-update PRs from disagreement resolution.** A pending Clarification means the lexicon is encoding canonical ambiguity — which is exactly what the methodology forbids.
10. **Fallback rate on held-out NL ≤ 0.20.** Tokens going to the FALLBACK source class (neutral signature, confidence 0.0) must be the minority, even before the Wave-2-B learned tagger lands.

A gate failure does not cause a slip in Wave 4 GPU planning; it causes a *focused lexicon batch* aimed at the specific failing gate. The structure is "fail clear, fix narrow, re-test."

---

## 9. Out of scope for this document

- The learned CAS-axis tagger (Wave 2-B). The lexicon and the tagger compose; this document specifies the lexicon side of that compose.
- Encoder-integration design (Wave 2-C). The lexicon's outputs are `StructuredToken`s; how the embedding layer consumes them is Wave 2-C.
- Multilingual lexicons. English only in v1.
- Sarcasm / tonal-inversion detection. Tokenizer is honest; sarcasm handling is encoder-level (Wave 4).

---

## 10. One-paragraph executive summary

The lexicon scales from 98 → 15K-30K entries through a four-priority source pipeline (CAS canonical material, CAS framework vocabulary, SDG-mined high-association words, parallel-register variants, safety-edge curation), gated entry-by-entry by a six-step vetting protocol that mechanically applies the Colloquialism Test, anti-drift annotations, Universal Applicability Test, and authoritative-verb preservation before any candidate lands. Growth happens in named, dated, signed batches with weekly cadence in bootstrap and biweekly in saturation, CI-enforced anti-drift property tests, per-axis density floors, recall-against-held-out-corpus tracking, and a 16-cohort demographic-robustness eval. Inter-rater disagreement is treated as information about ambiguity, not as a vote: when two reviewers disagree on canonical semantics, the candidate goes to Clarification update, not to a compromise entry. The `lexicon_extract.py` tool mines candidates from the SDG corpus, runs all gates as a pre-filter, and emits diff-ready JSONL chunks for human merge — never auto-merging. The Wave 4 GPU-training rollout gate is ten numerical checks, the most load-bearing of which is "zero outstanding Clarification-update PRs from disagreement resolution," because a pending Clarification means the lexicon is laundering ambiguity that downstream training will then learn as truth.
