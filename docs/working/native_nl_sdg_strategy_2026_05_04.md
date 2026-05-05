# Native NL SDG Strategy — v1 (2026-05-04)

Author: SDG-strategy agent (one of the 5-agent Opus team building the
native CAS-Native English generation head).
Companion artifacts:

- `cas-synthetic/scripts/generate_native_nl_sdg_v1.py` — seed generator.
- `cas-synthetic/data/native_nl/v1_seed_5k.jsonl` — 5K seed corpus.
- `cas-synthetic/data/native_nl/v1_seed_5k_manifest.json` — full provenance.
- `cas-synthetic/tests/test_native_nl_sdg.py` — schema / coverage / cost-cap tests.

This document is the strategy reference. The seed script is a working
proof-of-pipeline; the corpus described here is the full
50K-200K-record build the four other agents will train against.

---

## §1 Goal

Build a paired (CAS-state, English reply) corpus that lets the from-scratch
6-layer / d_model=512 / ~50M-parameter decoder learn to produce fluent
English directly conditioned on a CAS expression — without any borrowed
pretrained weights in the production stack.

Two things have to be true at the end of training:

1. **Conditioning works.** Given a CAS expression prefix and the same
   continuous bottleneck the v1 Full Stack classifier already produces,
   the decoder writes English that expresses that exact structural
   dynamic. Same Noetic, same Domain, same Drive, same Register.

2. **Fluency is from the data.** The 50M decoder has no language prior.
   Every grammar pattern, every idiom, every register cue must come from
   the SDG corpus. That means the corpus has to be human-quality English
   AND CAS-grounded, at scale, at low cost, with full traceability so we
   can debug what the model learned and why.

The 5K seed in this strategy is **proof-of-pipeline** — it shows the
3-tier mechanics work end-to-end and the traceability fields hold. It
is NOT training-scale. The full corpus described in §3 below is the
training-scale build, scheduled for the next two weeks.

## §2 Three-tier corpus design

The corpus is built in three tiers, each with a different
generator, different cost profile, and different role in training. Tiers
compose: Tier 2 records carry `parent_ids` pointing at Tier 1 records;
Tier 3 records can optionally cite Tier 1 templates as ancestors.

### Tier 1 — deterministic templates (~40K records, $0, ~1 hour)

Source: `noetic-compass-scaffold/noetic-compass/cas-native/data/english_generator.py`,
extended to v7.5/v7.6/v7.7 grammar. Tier 1 is what we own without any
external dependency. Every CAS expression on the (10 Noetics × 4 Domains
× 7 Drives × 4 Registers) cube gets at least one English replyform. The
generator is purely procedural: a grammar that swaps in operator
templates, drive-context phrases, and scenario contexts.

Tier 1's role:
- **Axis-completeness floor.** The corpus cannot have empty cells. A
  decoder trained on a corpus missing `^4^O_{F3}|E` will silently
  refuse-to-generate that state. Tier 1 guarantees coverage.
- **Schema validator.** Tier 1 outputs are fully introspectable. We use
  them to test that the trace fields, the manifest, and the validator
  all behave correctly before we spend a dollar on Tier 2.
- **Anti-drift ground truth.** Each Tier 1 template is keyed to the
  authoritative Noetic colloquialism (^3 visceral, ^6 analytical, ^8
  associative, ^9 deductive landing). The decoder sees the right verb
  for the right Noetic before it ever sees a Claude rewrite.

Limits:
- Surface diversity is bounded by template count.
- Reads as templated — fine for grounding, not enough for fluency.

### Tier 2 — Claude-API rewrites of Tier 1 (~50K-100K records, $50-200, 2-3 days)

Source: each Tier 1 record is rewritten by Claude across the 8
demographic profiles × 5 tonal registers spec'd in
`cas-synthetic/generator/demographic_tonal_axes.py`. Stratified sampling
picks K=4 (profile, tone) cells per Tier 1 parent, deterministic on a
seed derived from the parent ID.

Tier 2's role:
- **Surface diversity at controlled cost.** Each Tier 1 parent fans out
  to ~4 paraphrases in distinct voices. The decoder sees the same
  CAS state expressed by P1 (young technical professional) in T3
  (frustrated) and by P2 (senior academic) in T5 (reflective) for the
  exact same CAS prefix. That is what teaches the conditioning to be
  voice-invariant.
- **Provenance lineage.** Each Tier 2 record carries `parent_ids = [tier1_id]`
  so the validator and any downstream eval can trace fluency
  regressions back to the template family that produced them.

Constraints:
- Anti-drift register-aware nudges (visceral ^3, analytical ^6,
  associative ^8) are reused from `generate_paired_replies_v1.py`. The
  rewriter is told what register the parent is in and what colloquialism
  family is canonical.
- Validator pass: length, jargon-absence, template-opener filter,
  letter-density minimum (the validator from `generate_paired_replies_v1.py`
  is reused verbatim because it is the load-bearing reference).

### Tier 3 — Claude-API dialogue triples (~50K-200K records, $200-500, 5-7 days)

Source: Claude generates `(user prompt, CAS state, fluent reply)` triples
end-to-end. Unlike Tier 2 (which transforms a known reply), Tier 3
generates the full dialogue shape directly. The CAS state is sampled
first; Claude is asked to invent a conversational user prompt that would
naturally elicit that exact state and a 1-3 sentence reply that
expresses it.

Tier 3's role:
- **Dialogue shape.** Tier 1 and Tier 2 are reply-only. Tier 3 teaches
  the decoder how to take a USER question and produce a CAS-conditioned
  ANSWER. This matches the runtime shape: the CAS-Native classifier
  reads the user prompt, predicts a CAS state, then the generation head
  conditions on that state to write the reply.
- **Compound expression coverage.** Tier 3 is where the recipe (v7.6),
  register-set (v7.7 `|⟨A,f,T⟩`), co-presence (v7.7 `+`), and emergent
  cross-register fusion (v7.7 `(A × B) = Ω`) get represented. Tier 1
  templates handle these awkwardly; a generative model handles them
  fluently.
- **Anti-drift adversarial cases.** Tier 3 deliberately includes
  near-misses on the colloquialism map: "I want to take a hard look at
  this" (^6, NOT ^3), "that reminds me — and that means therefore" (^8,
  NOT ^6 + ^9). The decoder needs to learn the boundary, not memorize
  one side.

Constraints:
- Cost cap of $500 enforced in script. Concurrency = 5 parallel
  asyncio. Retries = 5 with exponential backoff.
- Validator pass: same surface filters as Tier 2, plus a
  CAS-grounding heuristic (deferred — see §5).

## §3 CAS coverage requirements

The corpus must cover four orthogonal axes plus a curated set of
compound expressions and anti-drift cases.

### Base axes (1,120 cells)

`10 Noetics × 4 Domains × 7 Drives × 4 Registers = 1,120 base
combinations.` Every cell must have at least 5 records in the final
50K corpus, 20 records in the 200K corpus. Tier 1 puts a floor of 1
record per cell; Tier 2 multiplies that by K=4 paraphrase cells; Tier
3 fills underrepresented cells via stratified resampling on the
manifest.

### Compound expressions (v7.5 / v7.6 / v7.7)

- v7.5 register specification: `^n|R`, `F_k|R`, `^n^D_{F_k}|R`,
  `^n|R_n^D_{F_k|R_d}`. All 4 register values, all 4 notational
  positions.
- v7.6 recipe notation: `Θ(Ω) = a₁·X₁ + a₂·X₂ + ... → Ω`. Single-,
  two-, and three-prerequisite recipes. Limiting-reagent and yield
  expressions on the Ω side.
- v7.7 register multiplicity: `|⟨R1,R2,R3⟩` set-spec, `+` co-presence,
  `(A × B) = Ω` named emergent fusion. Same-Noetic multi-register
  expressions using `×` MUST have an explicit emergent result, per the
  admissibility rule — the validator rejects bare `^3^P|A × ^3^P|f`.

### Anti-drift cases (load-bearing)

Per `CLAUDE.md` "Anti-drift annotations":

- **^3 visceral vs ^6 analytical.** ^3 = "can't stomach it / rubs me
  the wrong way / wouldn't touch it with a ten-foot pole." ^6 =
  "unpacking, breaking it down, looking at what's underneath."
  Audit/scrutinize/find-flaws vocabulary is ^6, NOT ^3. The corpus
  must contain enough ^6 records using audit vocabulary that the
  decoder cannot collapse them to ^3.
- **^8 associative vs ^9 deductive landing.** ^8 = "that reminds me
  / one thing leads to another / triggered a memory." ^9 = the
  surfaced Idea, "popped into my head / it just clicked." Deductive
  causal reasoning is a compound (^6 + ^9), NOT ^8.
- **^4 vibration etymological cognate.** "Struck a chord" is literal
  vibration vocabulary. Records using vibration vocabulary should
  carry ^4.

The full anti-drift set is encoded as a curated register/colloquialism
table in the seed script (the `NOETIC_NUDGES` dict, ported from
`generate_paired_replies_v1.py`).

## §4 Reply quality criteria

A valid reply meets all of:

1. **Length:** 1-3 sentences, 10-600 characters.
2. **No template phrasings:** rejects "Reading this as...",
   "This maps to...", "I sense...", "I detect...".
3. **No CAS jargon:** rejects "noetic", "domain", "drive", "register",
   "CAS", "F1-F7", "operator", "compound state", "^N", "|TAfE".
4. **Letter density:** ≥50% letters (rejects symbol-heavy outputs).
5. **Register-consistent:** the surface vocabulary aligns with the
   declared Register (analytical = step/premise; affective =
   feeling-toned; embodied = body/sensory; transcendent = abstract
   meaning). Currently checked qualitatively at sample review;
   automatic check is deferred to post-training scoring.
6. **Anti-drift respected:** when the CAS state is ^3 the reply does
   not use audit vocabulary; when ^8 the reply does not contain
   "therefore". Currently checked qualitatively; automatic check
   uses a token-presence heuristic.

The validator from `generate_paired_replies_v1.py` is the canonical
reference. The seed script reuses it verbatim.

## §5 Validation pass

Three layers of validation, increasingly expensive:

1. **Surface filters (script-time, fast).** Length, letter-density,
   jargon-absence, template-opener absence. Implemented in the seed
   script. Failure path: retry once at lower temperature, then drop.
2. **CAS-grounding heuristic (script-time, cheap).** Heuristic check
   that the colloquialism family in the reply matches the declared
   Noetic. Currently a token-presence check against a curated map;
   produces a "validator_pass" boolean on the record. Records that
   fail the heuristic are kept with `validator_pass=False` so the
   training pipeline can choose to drop or downweight them; we do
   NOT discard at SDG time because a strict rule would cull
   legitimate records and bias the corpus.
3. **Round-trip validation (deferred to post-training).** Once the
   trained classifier exists, generated replies are scored back
   through the classifier; if the predicted CAS state matches the
   conditioning CAS, the record is "round-trip valid." This is the
   gold standard but requires the trained model. Tracked in the
   manifest as `round_trip_validator: deferred`.

## §6 Object traceability (load-bearing)

Per the user-ratified architectural rule: every record carries the
following provenance fields. NO silent black boxes.

```json
{
  "id": "<sha256(cas_expression || prompt || tier || generator_model || generation_timestamp)[:32]>",
  "schema_version": "native_nl.v1",
  "trace_id": "<UUID grouping the cohort of related generations>",
  "tier": "tier1" | "tier2" | "tier3",
  "parent_ids": ["<tier1 id>", ...],   // empty list for tier1
  "source": "english_generator.py" | "claude_api" | ...,
  "source_template_id": "<template id when tier1, else null>",
  "generator_model": "deterministic" | "claude-sonnet-4-6" | "claude-3-5-sonnet-20241022",
  "generation_timestamp": "2026-05-04T17:30:00.000000+00:00",

  "cas_expression": "^3^P_{F2}|A",
  "noetic": "^3",
  "domain": "P",
  "drive": "F2",
  "register": "A",

  "prompt": "Where do you draw the line on cutting safety corners at work?",
  "reply": "I will not sign off on a build that puts the line workers at risk. That is the floor.",

  "demographic_profile": "young_professional_technical",
  "demographic_profile_code": "P1",
  "tone": "frustrated",
  "tone_code": "T3",

  "validator_pass": true,
  "validator_reasons": []
}
```

ID determinism: `id = sha256(canonical_input).hexdigest()[:32]` where
`canonical_input` is the concatenation of `cas_expression`, `prompt`,
`tier`, `generator_model`, `generation_timestamp`, joined by `\x1f`
(unit separator). Re-running the seed script with the same `--seed`
parameter and the same wall-clock granularity (timestamps are stable
inside a single run) produces identical IDs — re-run idempotency.

`trace_id` is a UUID4 generated once per script invocation and
stamped on every record produced by that invocation. Cohorting at the
trace_id level lets the validator answer "which run produced this
record?" without scanning the whole corpus.

`parent_ids` is the lineage. A Tier 2 record produced from Tier 1
record `t1_abc123` carries `parent_ids = ["t1_abc123"]`. A Tier 3
record produced fresh carries `parent_ids = []` (no template parent)
or, if cited, carries the parent Tier 1 template ID.

## §7 Cost + timeline

| Tier | Records | Cost | Time | Status |
|---|---|---|---|---|
| Tier 1 | 2,500 (seed) → 40K (full) | $0 | ~1 hour | Seed shipped today; full build is a follow-on script run. |
| Tier 2 | 2,500 (seed) → 50K-100K (full) | $50-200 | 2-3 days | Seed shipped today; full build pending API budget approval. |
| Tier 3 | 0 (seed) → 50K-200K (full) | $200-500 | 5-7 days | Not in seed; spec'd for follow-on agent. |
| **Total** | **5K seed → 100K-340K full** | **$0 (seed) / $250-700 (full)** | **~1 week (full)** | |

Hard cost cap on the seed script is $50 (Tier 2 only consumes API
budget). Cap is enforced at the per-record commit boundary so a
runaway loop cannot exceed the cap by more than one record's worth
of tokens.

If the API key is missing or invalid: the seed script produces Tier 1
only (2,500 records), documents the gap in the manifest with
`api_key_status: "missing"`, and aborts BEFORE any spend. This
guarantees the strategy doc + Tier 1 corpus + manifest + tests still
ship even when the API is unavailable.

## §8 Open questions for the user

1. **Tier 3 dialogue triples or full multi-turn?** The seed handles
   single-turn (one user prompt + one reply). Multi-turn dialogue
   (Phase 2-3 of Version B per memory) needs DST conditioning. Should
   the SDG generate single-turn for the v1 generation head and defer
   multi-turn to a separate Phase 5 SDG, or should v1 already include
   short multi-turn cases?

2. **Anti-drift adversarial budget.** What share of the corpus should
   be deliberate anti-drift cases (^3-but-actually-^6,
   ^8-but-actually-^6+^9)? Suggested: 5-10% of Tier 3, 0% of Tier 1
   and Tier 2 (those are clean grounding). Confirm or adjust.

3. **Round-trip validator timing.** Should the SDG agent build the
   round-trip validator now (against the v1 Full Stack classifier
   that finishes ~10 hrs from now per HONEST_STATUS.md), or defer to
   the eval agent? Recommendation: defer to eval agent; SDG ships
   clean records with `round_trip_validator: deferred` in the
   manifest, eval agent does the round-trip pass.

4. **Demographic and tonal balance enforcement.** The 8 profiles × 5
   tones taxonomy from `cas-synthetic/generator/demographic_tonal_axes.py`
   is uneven — P7 (anxious_first_timer) and P8 (confident_veteran) are
   rarer in real conversational data than P5 (lay_casual). Should the
   SDG enforce uniform 1/40 per (profile, tone) cell, or weight by
   real-world prevalence? Recommendation: uniform for the seed
   (validator can detect skew), real-world weighting for the full
   build.

5. **Compound expression budget.** What share of the full corpus should
   be v7.6 recipe / v7.7 register-multiplicity expressions? These are
   the harder cases for the decoder but the higher-value cases for the
   product. Recommendation: 60% base (single Noetic^Domain_{F_k}|R), 25%
   v7.5 register-specified, 10% v7.6 recipe, 5% v7.7 register-
   multiplicity. Confirm or adjust.

6. **Replay attacks against the validator.** The validator rejects
   records mentioning "noetic", "domain", "register", etc. — but a
   legitimate reply about a music album titled "Domain" would also
   be rejected. We accept this false-positive rate as the cost of
   purity. Confirm.

---

## Word count

This document is approximately 2,100 words (excluding the front-matter
and the ASCII art tables). Within the §1-§8 range requested.
