# Phase 3 SDG: Native Free-Form English Generation — Canonical Spec

**Date**: 2026-05-04
**Track**: SDG / CAS-Native v2 conversational training data
**Status**: Implemented (rule-based v1), pending RunPod corpus scale-up
**Owner**: free-form generator subsystem
**Related work**: Lever 3 (paired-data Claude rewrite, in flight) and
the demographic + tonal axes expansion (Task #68, shipped PR #34)

---

## 1. Motivation — why native free-form generation > Lever 3 retrofit

The CAS-Native K=9 baseline was trained on prompts of the form
`"As a notation exercise, map this structure into CAS: families: state
expression; states: Noetic ^N; domain D; drive F#; register |R."`. That
template stem is structurally informative — every prediction label is
literally enumerated in the surface — but it is also the single most
populated input distribution the model has ever seen. When deployed
users type colloquial English ("I can't stand it when meetings run
long") the predictor collapses to its prior because nothing in the
input distribution matches.

Two SDG strategies address this:

1. **Lever 3 (retrofit, sibling track).** Take the existing canonical
   prompt and ask Claude Sonnet 4.6 to rewrite it into colloquial
   English. Pros: the natural-language rewriter has read the canonical
   colloquialism map and can produce idiomatic surfaces. Cons: API
   cost (~$0.0008/record at scale 5k+); two-pass latency; non-
   deterministic outputs that complicate provenance auditing; quality
   varies with prompt and bucket.

2. **Phase 3 (native, this spec).** Generate the colloquial English
   directly from the CAS expression using a hand-curated colloquialism
   lexicon and compositional rules. Pros: fully deterministic given a
   seed; pure stdlib (zero external API calls); cost-free at any
   corpus scale; verifiable anti-drift guarantees by lexicon
   partition. Cons: surface variety bounded by lexicon size; phrasing
   can be slightly stilted on edge buckets compared to a strong LLM
   rewriter.

Phase 3 is the "proper fix" version of the Lever 3 shortcut. The two
are complementary, not exclusive — the recommended training corpus
includes BOTH (see Section 6 below).

## 2. The colloquialism lexicon structure

The lexicon (`cas-synthetic/generator/free_form/colloquialism_lexicon.py`)
is the single biggest deliverable. It is data-heavy: ~700 phrases
across the 10 Noetics, 4 Domains, 7 Drives, 4 Registers, plus
structural connectives, integration openers, recipe scaffolds, and
meta-logic relation glosses.

Per-Noetic structure: each Noetic `^N` has FIVE phrase categories:

- `base` — register-neutral colloquialisms (the verbatim CLAUDE.md
  Colloquialism Test entries, plus pedagogically-faithful neighbours).
- `transcendent_modifier` — phrases for `^N|T` (high-abstraction).
- `analytical_modifier` — phrases for `^N|A` (sequential / logical).
- `felt_modifier` — phrases for `^N|f` (value-laden).
- `embodied_modifier` — phrases for `^N|E` (sensorimotor).

Each category has at least 6 phrases; most have 12-16.

Domain flavor markers (`P`/`C`/`E`/`O`) and Drive flavor markers
(`F1`-`F7`) provide "background colour" the surface generator weaves
into a sentence. Register frames are sentence-opener phrases keyed on
the operating Register.

The lexicon is the **only** place new phrasing is added. The surface
generator is intentionally thin — it composes from the lexicon and
never invents content of its own.

## 3. Compositional rules table

| Shape           | Detector                                           | Renderer                                                                                                       | Example surface                                                                                                          |
| --------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `simple`        | `^N(^D)?(_{Fk})?(\|R)?` only                       | Register frame + Domain flavor + grammar-aware Noetic frame + Drive flavor                                     | "At the level of meaning, on the practice side of things, I'm drawn to the higher arc — vital."                          |
| `copresence`    | `+` separators, no `=` integration                 | Render each constituent simple state, glue with co-presence conjunctions ("and at the same time", "alongside") | "When I think it through I have to disagree, and on top of that the practice my hands know..."                           |
| `integration`   | `(... × ... × ...) = ... \|Omega_*`                | Integration opener + comma-listed contributing phrases + Omega gloss landing                                   | "Where all those tracks fuse, when I let watching the logic and tracking the felt sense enter the same place, I land on a sense of clarity." |
| `recipe`        | `Theta(...) = ... -> Omega_*` (with `->` or `→`)   | Recipe opener with target gloss + comma-listed `coef parts of phrase` ingredients + optional leakage tail      | "What goes into producing a grounded creative insight is 0.73 parts of made me think of the argument that, ..."          |
| `meta_logic`    | `StateCluster{...}`, `Product(...)`, `∩`, `∪`, `∖` | Meta-logic opener + relation phrase + de-duplicated noun-phrase list of cognitive moves                        | "Considering the cluster of cognitive moves at play, the overlap is an operational Male move, a principled Vibration move..." |

Detection priority (first match wins):
`recipe` → `meta_logic` → `integration` → `copresence` → `simple` →
`unknown`.

The parser (`compositional_rules.py`) is intentionally tolerant. It does
not validate the surrounding expression — that is the CAS compiler's
job. It only extracts the load-bearing slots that drive lexicon
selection, and it never crashes on malformed input (it falls back to
the `unknown` shape and returns a generic "something is going on
cognitively that's hard to put a label on" sentence).

## 4. Anti-drift verification approach

The CLAUDE.md anti-drift annotations specify three classes of error
pattern that recur across prior Scheme-A/B/C artifacts:

1. **`^3` Negative is VISCERAL, not analytical.** Words like "audit",
   "scrutinise", "critique", "find flaws", "tear apart" belong to `^6`
   Male (compositional decomposition), not `^3`.
2. **`^8` Above/Cause is associative TRIGGERING, not deductive.**
   Words like "therefore", "thus", "q.e.d.", "ergo", "consequently",
   "deduce", "it follows that" belong to a `^6 + ^9` compound, not
   `^8`.
3. **`^4` Vibration retains the etymological cognate.** "Struck a
   chord" / "resonate" are not metaphors — they ARE the canonical
   colloquialisms.

Phase 3 enforces all three at TWO layers:

- **Lexicon partition (compile-time).** The `^3` lexicon contains zero
  analytical decomposition vocabulary. The `^8` lexicon contains zero
  deductive vocabulary. The `^4` lexicon retains "chord" and
  "resonate" as load-bearing anchors. Tests
  `test_negative_lexicon_has_no_analytical_vocabulary`,
  `test_above_cause_lexicon_has_no_deductive_vocabulary`, and
  `test_vibration_lexicon_retains_etymological_cognate` are CI-gated.
- **Runtime guard (defence in depth).** The surface generator inspects
  every candidate phrase against `_NEG_FORBIDDEN_RE` and
  `_AC_FORBIDDEN_RE` before emitting. If a future lexicon edit
  accidentally introduces forbidden vocabulary, the runtime guard
  reshuffles the choice; if every option is forbidden it falls back to
  the `base` category. End-to-end tests
  `test_negative_generated_surface_has_no_analytical_vocabulary` and
  `test_above_cause_generated_surface_has_no_deductive_vocabulary`
  exercise the guard across 40 (expression × seed) combinations per
  Noetic.

The two layers ensure the anti-drift contract survives not just
careful authoring but also future lexicon expansion by other
contributors.

## 5. Integration with demographic + tonal axes (Task #68)

Phase 3 produces the *content* surface (which colloquialisms, what
sentence frame, what Domain/Drive flavor). Task #68's demographic +
tonal axes produce the *speaker* surface (who is talking — anxious
first-timer in a frustrated tone vs senior academic in a reflective
tone).

The two are orthogonal and compose naturally:

```
canonical record (training-surface CAS prompt)
    -> Lever 3 + Phase 3   (content surface diversification)
    -> demographic-tonal   (speaker surface diversification)
    = combined corpus
```

The composition is left-to-right: a Phase 3 free-form prompt
("At the level of meaning, on the practice side of things, I'm drawn
to the higher arc.") can be passed to the demographic-tonal rewriter
and re-spoken in P7+T2 (anxious first-timer) voice ("Sorry, I think
maybe at the level of meaning, on the practice side of things, I'm
kind of drawn to the higher arc, I think?"). The CAS structure and
all 12 prediction labels are preserved through both stages.

The `style` parameter on `generate_free_form` is reserved for the
direct integration path: a future iteration can wire
`style="P7+T2"` straight into the surface generator without going
through a second pass. For now, the pipeline composes the two
generators.

## 6. Sequencing — combined corpus recommendation

The recommended retrain mix combines four sources:

| Source                          | Origin                                | Surface diversity         | Cost           |
| ------------------------------- | ------------------------------------- | ------------------------- | -------------- |
| Canonical training-surface      | `level3_recoverable_full.jsonl`       | low (template stem)       | already paid   |
| Lever 3 paired free-form        | Claude Sonnet 4.6 rewrite             | high (LLM rewriter)       | $4-6 per 5k    |
| **Phase 3 native free-form**    | rule-based generator (this spec)      | medium-high, deterministic | $0             |
| Demographic-tonal expansion     | rule-based rewrite (Task #68)         | high (8×5 cells)          | $0             |

Multiplicative scale:
- canonical (~36k) +
- Lever 3 retrofit (~5k API-bounded, expandable) +
- Phase 3 native (3 variants × 36k = 108k) +
- demographic-tonal (4 variants × any of the above) =
  **roughly 500k records** when fully composed.

Rationale for keeping all four:
- Canonical anchors the training-surface distribution and provides
  the "easy win" baseline the model can fall back to.
- Lever 3 brings idiomatic LLM-rewriter diversity that no rule-based
  system fully captures.
- Phase 3 brings deterministic, auditable, scale-free coverage —
  particularly valuable for the bucket buckets where Lever 3 is
  expensive at scale (v76_production, v77_omega, meta_logic).
- Demographic-tonal multiplies any of the above into 8×5 speaker
  cells.

The four sources are **not** redundant; they sit at different points
on the (cost × surface-diversity × determinism) frontier. A combined
training run including all four has been the standing recommendation
since the demographic-tonal landing on 2026-05-04.

## 7. Quality bar — the three CI gates

Phase 3 is governed by three CI gates that the test suite enforces:

1. **Human-readability.** Sample inspection of generated surfaces (5
   diverse buckets × 3 variants = 15 surfaces) is part of the
   completion-report template. The generator MUST NOT produce
   surfaces that contain CAS jargon ("Noetic", "domain", "drive",
   "register", `^N`, `|R`) — Phase 3 outputs are colloquial English
   that never names the formalism.

2. **Label preservation.** Every variant must have byte-identical
   values for all 12 prediction labels (turn_type, expression_family,
   transition_kind, noetic, domain, drive, register_mode, registers,
   authority, has_omega, has_meta_logic, meta_relations) plus all
   sacred fields (cas_expression, soft targets, natural_language_
   mapping, assistant_response, follow_up_question, source_level2_id,
   bucket). The `expand_record` API enforces this contract by
   deep-copying the canonical and ONLY mutating `user_prompt` plus a
   small bag of provenance / metadata fields. Tests
   `test_expand_record_preserves_every_sacred_field` and
   `test_expand_record_only_touches_user_prompt_and_metadata` are
   CI-gated.

3. **Lexicon-coverage.** Each Noetic must populate all five
   categories (base / transcendent / analytical / felt / embodied),
   each with at least 6 phrases. Each Domain must have at least 8
   flavor markers; each Drive at least 6; each Register at least 4
   frame phrases. Tests
   `test_every_noetic_has_all_five_lexicon_categories`,
   `test_domain_and_drive_flavor_tables_are_populated`,
   `test_register_frames_present_for_all_four_registers` are
   CI-gated.

A future Phase 3 v2 lexicon expansion (more phrases per category,
more nuanced register-domain interaction templates) is planned as a
follow-on; the current v1 lexicon is the minimum viable surface area.

---

## File map

```
cas-synthetic/generator/free_form/
├── __init__.py                     # public surface re-exports
├── colloquialism_lexicon.py        # ~700 phrase entries (data-heavy)
├── compositional_rules.py          # parse_cas_expression -> StructuralPlan
└── surface_generator.py            # generate_free_form, expand_record

cas-synthetic/scripts/
└── generate_freeform_corpus.py     # driver (no API)

cas-synthetic/tests/
└── test_free_form_generator.py     # 37 tests, runs <1 second

docs/working/
├── phase3_free_form_spec_2026_05_04.md          # this file
└── phase3_completion_2026_05_04.md              # completion report
```

## Driver invocation

```bash
# smoke test (50 records -> 150 variants)
python cas-synthetic/scripts/generate_freeform_corpus.py \
    --input cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \
    --output cas-synthetic/data/level2_scaffold/level3_freeform_phase3_smoke.jsonl \
    --variants-per-canonical 3 \
    --seed 42 \
    --limit 50

# full run (RunPod / cloud) — DO NOT run on local CPU at scale
python cas-synthetic/scripts/generate_freeform_corpus.py \
    --input cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl \
    --output cas-synthetic/data/level2_scaffold/level3_freeform_phase3.jsonl \
    --variants-per-canonical 3 \
    --seed 42
```

The driver is pure-Python and CPU-bound; it processes ~5,000 variants
per second on a single core, so even the full ~108k-record output is
~20 seconds. The "RunPod recommended" guidance applies only when this
is composed with the demographic-tonal expansion for the full
~500k-record combined corpus.

## CHANGELOG anchors

- 2026-05-04 — Phase 3 lexicon + parser + surface generator landed
  with 37 passing tests; smoke run on 50 canonicals validated.
