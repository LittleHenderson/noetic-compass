# v1e Architecture — Pointer/Copy + Fractal-Aware Decoder Design

**Date:** 2026-05-10
**Status:** User-audited 2026-05-10; proceed with modifications listed
below. Phase 0 in_progress.
**Triggering decision:** v1d 2-epoch retrain net-regressed the 24-record pack
from v1c+scaffolds 16/24 → 15/24 acceptable+; record 14 lifted but records
13/15 still failed and 4 binary_composition / recipe / meta-logic records
regressed. User directive: freeze v1c+scaffolds as v0 candidate, pivot
architecture.
**Source artifacts:** 4 Wave-1 specialist agent specs (A pointer/copy, B
fractal-aware decoder, C aux heads, D integration) + 2 Wave-2 critic agents
(Maximalist / Minimalist) debating sequencing.

## User audit verdict (2026-05-10)

Direction approved: B-first is the correct next experiment because it does
not mutate the checkpoint. But the original draft overclaimed in two places
that the audit explicitly corrects:

1. **"B cannot regress v0" was too strong.** B does not mutate weights, but
   it CAN regress generated fractal output if the mask fires wrong, clips
   EOS, or forces awkward phrases. The protection has to be engineered, not
   asserted.
2. **The 24-record pack alone is not a promote/pivot gate.** Good as a
   fixed canary; too small to decide ship-vs-pivot-vs-build-C+A by itself.

Modifications mandated by the audit (apply BEFORE Phase 1B implementation):

- **Phase 0 freeze is non-negotiable and goes first.** No B work before
  v0-rc1 is tagged + archived.
- **B ships as opt-in shadow / eval-only first.** `apply_fractal_decoder`
  defaults to `False` until B earns production-default status from data.
- **No first-token masking alone.** Use a tokenized phrase-trie / phrase
  state machine over approved Noetic colloquialism phrases. First-token
  masks fire on common words ("a", "that", "who", "popped") and are too
  brittle. Phrase-trie is multi-token-aware by construction.
- **Fail closed.** If constrained decoding dead-ends, truncates, produces
  failing verifier output, or visibly degrades prose quality vs baseline,
  return the baseline (unconstrained) generation and LOG the failed
  constrained attempt. Never ship constrained output that is worse than
  baseline.
- **Expanded eval gate.** Build a dedicated fractal suite of 30-60 records
  stratified by k=2..8, with repeats, long sequences, shared-prefix
  phrases, and edge cases. Add non-fractal negative controls. The 24-pack
  is a required canary, not the sole judge. α/β/γ labels in §3.3 are
  heuristic labels for synthesis, not hard statistical promote/pivot gates.
- **v0-canary CI check is required but automated/deterministic.** No fresh
  human grading per PR; structural diff against frozen baseline outputs.

The bottom line, in the user's words: *"Do Phase 0, then do a modified
Phase 1B as opt-in constrained decoding with stricter gates and expanded
eval. Do not jump to C/A yet. Do not pivot simplex immediately. B is cheap
and informative, but it has to earn production default status."*

---

## TL;DR (the user-approved plan, post-audit)

1. **Phase 0 — tag `v0-rc1` THIS WEEK (non-negotiable, first).** Archive
   the v1c+scaffolds checkpoint, hashes, flag profile, baseline outputs.
   Wire the 24-record pack as a **deterministic/automated** required
   regression check on PRs touching `cas_native/inference/**` or
   `cas_native/model/**` — structural diff against frozen baseline outputs,
   not fresh human grading per PR.

2. **Phase 1B — ship Mechanism B as OPT-IN SHADOW/EVAL-ONLY first.**
   `apply_fractal_decoder=False` by default. The mechanism is:
   - **Phrase-trie / phrase state machine** over approved Noetic
     colloquialism phrases (NOT first-token masking alone — too brittle,
     fires on common words like "a", "that", "who", "popped").
   - Alternative path: a guarded deterministic fractal route.
   - Four-layer source-shape gate (same pattern as `seed_rpm_silhouette`).
   - **Fail closed**: if constrained decoding dead-ends, truncates,
     produces failing verifier output, or degrades prose quality vs
     baseline, return the baseline generation and log the failed
     constrained attempt.
   - No checkpoint mutation, no GPU spend.

3. **Expanded eval gate** (not the 24-pack alone):
   - **Required canary**: 24-record pack against v1c+scaffolds frozen
     baseline (automated, structural diff).
   - **Primary fractal suite**: 30-60 fractal records stratified by k=2..8,
     with repeats, long sequences, shared-prefix phrases, edge cases.
   - **Non-fractal negative controls**: verify B never fires on
     state_literal, binary_composition, cross_register_omega, recipe,
     meta_logic, rpm_chain, invalid_to_explanation.
   - Sample-read fractal outputs against targets per
     `feedback_samples_are_the_only_true_eval_for_cas_native`. Report
     per-k fractal accuracy, false-fire rate on negatives, fail-closed
     trigger rate, prose-quality degradation.

4. **Three-way decision gate after Phase 1B data** — α/β/γ are **heuristic
   labels for synthesis, not hard statistical promote/pivot gates**:

   | B-grade pattern (heuristic) | Suggested user-facing next move |
   |---|---|
   | α — B moves fractal suite materially, 24-pack canary holds, no false-fires on negatives, fail-closed trigger rate low | Ship v0 + B as v0.1; surface simplex Δ°₃₉ rebuild vs unified C+A decision to user with B-data in hand. |
   | β — B partial (some k buckets work, others don't; or prose-quality regression on edge cases) | Consider unified C (3 aux heads, 1-epoch fine-tune from v1c) with B's gate re-implemented against C's H2 head. Defer A. Decision goes to user, not auto-greenlit. |
   | γ — B null (fractal suite flat or worse) | The structural-prediction wedge isn't closeable by decode-side levers. Pivot to simplex Δ°₃₉ rebuild. |

5. **Mechanism A (pointer/copy over `cas_prefix_ids`) is sequenced last,
   not second.** Funded ONLY if Path β AND C lifts records 10/11/12 each
   by ≥1 band. v1d evidence shows content semantics (drive identity,
   coefficient values, cluster membership) drifts under fine-tune; A's
   pointer/copy targets identifier-copy specifically and is narrower than
   the v1d regression pattern suggests.

The asymmetry that drives B-first: **B does not mutate the checkpoint, so
the worst case is "constrained output worse than baseline" which the
fail-closed wrapper catches.** Every other phase carries the
fine-tune-destabilization risk envelope that just cost v1d its
acceptable+ row.

---

## 1. The four Wave-1 specs in one table

| Spec | What it is | Touches checkpoint? | New params | GPU-hours | Targets which eval records | Self-stated honest limit |
|---|---|---|---|---|---|---|
| **A pointer/copy** | Single-layer context-conditional pointer-generator over `cas_prefix_ids`; learned `p_gen` gate; free supervision from token overlap | Yes (fine-tune) | ~1.6M (~3% of head) | 7-8 | 10/11/12 (recipe Ω/coef) | Does NOT fix per-stage rpm_chain content drift; does NOT fix fractal k-mapping |
| **B fractal-aware decoder** | Inference-time phrase-trie / phrase-state-machine constraint over approved Noetic colloquialism phrases (NOT first-token mask alone); clause-boundary detector; EOS bias after final slot; **fail-closed wrapper** (return baseline if constrained output worse) | **No weights mutation; output regression possible if mask misfires — mitigated by fail-closed wrapper** | 0 | 0 | 13/14/15 (fractal sequence) | Doesn't help long-fractal vocabulary breadth (record 15); needs cooperation from existing checkpoint's distribution; opt-in (default OFF) until production-default is earned from data |
| **C aux heads + losses** | 3 encoder-pool heads: cardinality, per-position Noetic class, cluster membership; source-derived labels at batch time | Yes (1-epoch fine-tune) | ~200k | ~3-4 | 13/15 (structural), 16/17 (cluster count) | Does NOT fix 10/11/12 content semantics; aux loss may interfere with LM loss |
| **D integration** | v0-rc1 freeze, phased C → A → B, per-phase 24-pack gate, 6-item risk register, kill-switch to simplex if all phases stuck at 15-17/24 | N/A | N/A | N/A | All | ~11 eng-weeks + 4 careful regrade sessions; phasing assumes A/B/C deployable independently |

---

## 2. Where Wave-2 critics sharpened the picture

### 2.1 Minimalist's load-bearing point — B is asymmetric

D's C→A→B sequencing treats B as the architecturally hardest piece
(highest risk last). The Minimalist correctly inverts this: B is the
*easiest* piece because it doesn't mutate any checkpoint. v1d's net
regression demonstrated empirically that even a cleaner-corpus 2-epoch
fine-tune can destabilize v1c-acquired patterns. C and A both propose
the same intervention type. B does not. Therefore B should ship first,
not last.

### 2.2 Maximalist's load-bearing point — C's H2 is B's natural supervised gate

If C and B both ship, B's hard mask over Noetic first-token IDs becomes
`argmax_n p_H2(n | position)` plus a confidence threshold — gradient-trained
instead of statistical-heuristic. The Wave-1 B-architect's clause-boundary
detector is admitted-heuristic; if C trains a per-position Noetic-class
head, B's mask graduates from regex-with-weights to learned signal. This
synergy is real BUT conditional on a decision to build C. It is not an
argument for building B and C *simultaneously*; it is an argument for
sequencing C *after* B-evaluated, then re-implementing B's gate against
C's H2 head if both are in the v1e mix.

### 2.3 Both critics surfaced the simplex rebuild as a peer option

D treated the simplex Δ°₃₉ rebuild
(`project_simplex_redesign_revisit_after_v0`) as a kill-switch destination
("abandon v1e if all phases stuck at 15-17/24"). Both Wave-2 critics
escalated it to a peer option:

- Minimalist: 11 eng-weeks for v1e is competitive with 10-14 eng-weeks for
  simplex rebuild. If v1e ceiling is 17-18/24 and simplex floor is
  21-22/24, "successful" v1e is the worst outcome (consumes 11 weeks and
  lands below where a clean rebuild would have landed).
- Maximalist: simplex rebuild promotes traceability from "engineered probe"
  to "geometric property" — load-bearing per
  `feedback_traceability_is_the_whole_purpose`. A+B+C do not.

The honest user-facing decision is not "which order for C/A/B?" — it is
**"after B grades, do we fund unified C+A, or pivot to simplex?"** B's
empirical result is what determines which is right.

### 2.4 Where the two critics disagree (and what the data will decide)

- **Maximalist:** build A+B+C as one unified `v1e` checkpoint, all-on/all-off
  flag. Synergy and shared representation pressure beat phased build.
- **Minimalist:** ship B first, hold A and C to a 24-pack-no-regress
  threshold before any retraining is funded.

The synthesis takes the Minimalist's sequencing (B first, no retraining
risk before evidence) but accepts the Maximalist's integration argument
*conditionally* — if the B-grade decision gate selects "build C," then C
is built as a single unified fine-tune with B's gate re-implemented
against C's H2 head, not as the C-then-A-then-B chain D proposed.

---

## 3. Phase plan (concrete, source-cited)

### Phase 0 — v0-rc1 freeze (THIS WEEK, non-negotiable, first)

Per D §1, with the audit's automated-canary modification:

1. Annotated tag `v0-rc1` on the freeze commit (commits `83a0cde` /
   `810b66e` / `1ad6e02` era or whichever is the head of `master`).
2. Archive `model_final.pt` + `tokenizer.json` + `english_bpe.json` +
   `checkpoint_manifest.json` from RunPod into a stable local path.
   SHA-256 each.
3. Write `docs/releases/V0_RELEASE_CANDIDATE.md`: tag SHA, checkpoint
   SHAs, `routed_generate` flag profile (`apply_repair=True`,
   `seed_rpm_silhouette=True`, `apply_rpm_retry=False`,
   `prepend_task_token=True`, `apply_fractal_decoder=False`), the 16/24
   acceptable+ Claude-graded eval
   (`cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T191358Z_CLAUDE_GRADED.md`)
   frozen as the v0-canary baseline (including raw model outputs, not
   just band grades), and the kill-switch list from §4.
4. **Wire `v0-canary-evaluation` as a DETERMINISTIC AUTOMATED required
   check** on PRs touching `cas_native/inference/**` or
   `cas_native/model/**`. Structural diff: run the 24-record pack
   against the archived v1c+scaffolds checkpoint with the frozen flag
   profile, compare per-record `final_text` token-for-token against the
   archived baseline outputs. Any byte-level diff blocks the PR and
   surfaces the diff for human review. **No fresh human grading per
   PR.** Re-baseline only when the user explicitly approves a
   v0.N-rc bump.

Cost: ~0.5 eng-week. No GPU.

### Phase 1B — opt-in shadow-mode fractal decoder (post-Phase-0)

Audit-modified Wave-1-B-architect spec. Key changes from draft:
**opt-in default OFF**, **phrase-trie not first-token mask**,
**fail-closed wrapper**, **expanded eval gate**.

**1. Source parse.** Reuse `parse_fractal()` from
`cas_native/inference/fractal_repair.py`. Already returns
`FractalSequence(k_values, notation)`.

**2. Four-layer source-shape gate** (same pattern as
`seed_rpm_silhouette` in `cas_native/inference/routed_generate.py:240-242`):
- `apply_fractal_decoder` flag True (**default `False`**; opt-in until
  earned)
- `routing.task_type == "cas_to_english"`
- `parse_fractal(source)` returns non-None
- source-shape regex `_FRACTAL_RX` matches

**3. Decoder state.** `expected_K: list[int]`, `pos: int = 0`,
`phrase_trie_state: TrieNode | None`. Carried alongside `seq` in
`cas_native/inference/native_nl_generate.py:generate_reply`.

**4. Phrase-trie / phrase-state-machine constraint** (replacing the
draft's first-token mask, per audit):
- Build a trie at model load over every approved Noetic colloquialism
  phrase from `_NOETIC_INDICATORS[k]` for k=0..9, tokenized against the
  extended tokenizer. Each leaf carries the Noetic class label.
- When the slot detector fires AND `pos < n`, enter "constraint mode":
  the decoder is restricted to tokens that extend SOME phrase in the
  subtrie under `_NOETIC_INDICATORS[K[pos]]`. As tokens commit, walk
  the trie; when a leaf is reached, exit constraint mode and increment
  `pos += 1`.
- This is fundamentally different from a first-token mask: tokens like
  "a", "that", "who", "popped" are not flagged in isolation. They only
  constrain in the *context* of an incomplete approved phrase. A "popped"
  in a non-fractal context never trips anything because constraint mode
  is never entered.
- Alternative implementation path: a **guarded deterministic fractal
  route** that pre-selects one approved phrase per slot and uses
  `seed_decoder_text` to commit it. Evaluate both during Phase 1B; pick
  the one that wins on prose quality with equivalent fractal accuracy.

**5. Slot detector** — statistical, no new head: fires when (a) tail ends
with clause-boundary signature (rightmost non-whitespace is in
`{".", ";", ","}` OR last whitespace-token is in `{"then", "which",
"and", "finally", "so", "led", "became", "into"}`), AND (b) previous
slot was just committed, AND (c) `pos < n`. Soft secondary trigger:
force after `MAX_TOKENS_BETWEEN_SLOTS` (12) tokens since last commit.

**6. EOS bias.** After `pos == n`, add `+λ` to EOS logit.

**7. Fail-closed wrapper** (mandated by audit):
- Run TWO generations per fractal source: (a) constrained via §4 above,
  (b) baseline unconstrained.
- After both complete, score each via `verify_fractal_rendering` and a
  prose-quality heuristic (length sanity, no truncation marker, no
  repeated-phrase glitches per `generation_cleanup` rules).
- Return whichever is better. If constrained is worse on EITHER axis
  (verifier OR prose quality), return baseline AND log the failed
  constrained attempt to `postprocess_result.fractal_decoder_fail_log`
  for debugging.
- Cost: 2× inference per fractal record on the eval suite only.
  Acceptable. Eventually optimized by short-circuit (skip constrained if
  greedy probability of any approved phrase falls below a confidence
  threshold).

**8. Tokenizer-trie cache.** Build the phrase trie once at model load
against the actual extended tokenizer (handles BPE drift across
checkpoint loads). Stable lookup at decode time.

**Expanded eval suite** (replacing the draft's "24-pack only"):

| Eval surface | Size | Purpose |
|---|---:|---|
| 24-record pack | 24 | Required automated canary (no human regrade per PR) |
| Primary fractal suite (new) | 30-60 | Stratified by k=2..8, with repeats, long sequences, shared-prefix phrases, edge cases |
| Non-fractal negative controls | 8-16 | One per non-fractal category; verify B never fires |
| Fail-closed trigger log | n/a | Track rate of constrained → baseline fallback; should be < ~30% on the primary suite, ~0% on negatives |
| Prose-quality regression check | n/a | Sample-read N=10 random outputs from primary suite + N=4 random outputs from negatives per checkpoint |

Run on v1c, v1c-VALIDTOK, and v1d checkpoints with
`apply_fractal_decoder=True` set per-call (not via the v0-canary
defaults).

**Specifically watch for:**
- Record 13's `^9` loop (constrained mode should mechanically prevent it,
  but the fail-closed wrapper will catch a constrained-but-stilted output)
- Record 14's prose quality (must stay yellow+ or improve to green)
- Record 15's long-fractal performance (the deep vocabulary problem)
- Records 1-9 non-fractal (must not regress; source-shape gate +
  trie-only-when-in-constraint-mode keeps these untouched)
- Fail-closed trigger rate across the 30-60 record primary suite
  (informs whether the constraint is too tight)

**Risks** (audit-revised):
- **Phrase-trie misses unattested-but-valid phrasings** → fail-closed
  wrapper falls back to baseline; logged for trie expansion.
- **Constrained output is grammatical-but-stilted** → prose-quality
  heuristic in fail-closed wrapper catches it.
- **Source-shape gate false-fires on non-fractal** → mitigated by the
  four-layer gate; negative-control eval set specifically tests this.
- **2× inference cost during eval** → acceptable; only eval-mode runs
  both branches. Production mode (once earned) can short-circuit.

Cost: ~1 eng-week implementation + ~0.5 eng-week eval-suite build +
~0.5 eng-week sample-read. 0 GPU-hours.

### Phase 1B implementation status (2026-05-10)

Shipped in commit (this commit) with these artifacts:

| File | Role |
|---|---|
| `cas_native/inference/fractal_decoder.py` (NEW) | Phrase trie, state machine, logits-mask processor, fail-closed comparator |
| `cas_native/inference/native_nl_generate.py` | New `step_callback` parameter applied to logits pre-sample |
| `cas_native/inference/routed_generate.py` | New `apply_fractal_decoder: bool = False` parameter, dual-decode + fail-closed selector |
| `cas_native/tests/inference/test_fractal_decoder.py` (NEW) | 25 unit tests covering trie / boundary / fire / mask / comparator |
| `cas-synthetic/scripts/v1_eval_pack_24records.py` | `USE_FRACTAL_DECODER` env var; serializes `fractal_decoder_log` to JSONL |
| `cas-synthetic/scripts/v0_canary.py` | `USE_FRACTAL_DECODER="0"` defensively pinned in v0 env |

**Verification gates** (all passed):

- 25/25 unit tests pass on the fractal_decoder module.
- 93 adjacent inference tests pass (no regressions).
- v0 canary (`v0_canary.py --check`) PASSES — Phase 1B does not
  change v0 byte-equality when `apply_fractal_decoder=False`.

**3-record shadow-mode smoke** (`USE_FRACTAL_DECODER=1` against v0 checkpoint):

| Record | Source | Constrained slot_commits in order | Fail-closed selected | Reason |
|---|---|---|---|---|
| 13 | `Phi<6:9:7:0:9:5:2:0>` | [6, 9, 7, 0, 9, 5, 2, 0] — **EXACT MATCH** | baseline | constrained LOST cardinality (trailing prose adds extras) |
| 14 | `Φ<3:7>` | [3, 7] — **EXACT MATCH** | baseline | neither side achieved cardinality match in verifier |
| 15 | `Φ<1:0:3:3:1:1:7:5>` | [1, 0, 3, 3, 1, 1, 7, 5] — **EXACT MATCH** | baseline | neither side achieved cardinality match in verifier |

**Diagnostic conclusion:** The phrase-trie + state machine lands the
expected source k-sequence in source order, ON EVERY FRACTAL RECORD,
including the n=8 case that defeated v1d (record 13's `^9` loop).
This is the mechanical inductive bias the design targeted. The
fail-closed wrapper currently selects baseline on all three because
the constrained output's TRAILING PROSE past the final slot adds extra
noetic indicators that push the verifier's `found_k_count` above the
expected count. Two Task-#135 tuning levers identified from smoke:

1. **EOS bias after final slot.** Add `+λ` to EOS logit once
   `state.pos == n`, suppressing trailing prose.
2. **Comparator refinement.** Score only the FIRST `n` found
   noetics (rather than the full extracted sequence) so the trailing
   prose doesn't contaminate the cardinality check.

Both improvements are evaluated in Task #135 against the expanded
fractal suite (30-60 records stratified by k=2..8) before any
promotion to production-default.

### Phase 2 — heuristic decision gate after Phase 1B data

After Phase 1B ships and the expanded eval suite + 24-pack canary
return, surface a three-way decision **to the user, with empirical
data**. α/β/γ below are **heuristic labels for synthesis, not hard
statistical thresholds.** No auto-promotion or auto-pivot.

#### Path α — B looks like a clear win

Heuristic signal: B materially improves the primary fractal suite across
most k buckets, 24-pack canary holds (no byte-diff regressions on
non-fractal records), negative-control set shows zero false-fires,
fail-closed trigger rate is low.

- Promote `apply_fractal_decoder=True` to production-default.
- Ship v0 + B as **v0.1**. Update `V0_RELEASE_CANDIDATE.md` to v0.1-rc
  with a new automated canary baseline (24-pack outputs with B on).
- Surface to user: **simplex Δ°₃₉ rebuild vs unified C+A v1e**, with B's
  data in hand. The 11-week v1e budget is still on the table; so is the
  10-14-week simplex rebuild. Side-by-side comparison with concrete B
  evidence. **User decides; no engineering auto-trigger.**

#### Path β — B is partial / mixed

Heuristic signal: B works on some k buckets but not others; or prose
quality regresses on edge cases; or fail-closed trigger rate is high
(constraint is too tight for current model distribution).

- Surface to user: **build C unified vs pivot simplex**, with B's data.
  C unified = 3 aux heads on encoder pool per Wave-1 C-architect spec,
  with B's gate re-implemented against C's H2 head's argmax (Maximalist
  synergy claim, activated conditionally). Fine-tune from v1c (NOT v1d).
  1 epoch. Aux-loss curriculum ramps DOWN. Auto-alert if
  `loss_lm / loss_structured > 5×` at step 5000.
- Defer A regardless.
- Cost if C funded: ~3 eng-weeks, ~3-4 GPU-hours.

#### Path γ — B doesn't help

Heuristic signal: fractal suite flat or worse, fail-closed wrapper
returning baseline most of the time, no per-k improvement pattern.

- Diagnosis: the structural-prediction wedge is not closeable by
  decode-side levers on the current checkpoint distribution.
- Surface to user: **pivot to simplex Δ°₃₉ rebuild** per
  `project_simplex_redesign_revisit_after_v0`. Do not auto-fund A or C.
- The 11-week v1e budget converts to the 10-14-week simplex budget at
  net-zero opportunity cost. **User confirms before pivot.**

In all three paths, `apply_fractal_decoder` stays `False` by default
until Path α explicitly promotes it. Simplex is a peer option throughout,
not a kill-switch destination.

### Phase 3 — Mechanism A, conditional

A is funded ONLY if Path β was selected AND C's grade shows concrete
content-semantics signal that A's pointer/copy could amplify (e.g.,
records 10/11/12 lifted by ≥1 band each under C alone). Otherwise A is
not funded.

If A is funded:
- Per Wave-1 A-architect spec. Single-layer context-conditional
  pointer-generator over `cas_prefix_ids`. Free supervision from
  token overlap. ~1.6M new params.
- Fine-tune from `v1e_phaseC` (NOT v1c). The combined checkpoint stays
  `v1e`; the all-on/all-off `use_v1e` flag governs deployment.
- Cost: ~3 eng-weeks. ~7-8 GPU-hours.

---

## 4. Kill-switch criteria (heuristic, user-confirmed)

These are heuristic patterns that surface a user decision, not
automatic-pivot triggers.

- **B-grade pattern looks like Path γ** (fractal suite flat or worse,
  fail-closed mostly returning baseline). Surface simplex pivot to user.
- **C-grade pattern returns regression** (24-pack canary byte-diffs
  regress vs frozen baseline; primary fractal suite worse than B-only).
  v1e checkpoint discarded; v0-rc1 stays deployed. User confirms next
  move.
- **A-grade pattern returns flat** (records 10/11/12 don't lift after
  A's fine-tune). A is the wrong mechanism; v1e shipped as v0+B+C only.
- **Cumulative cost exceeds 12 eng-weeks before A ships.** Cost overrun
  → simplex rebuild competitive on calendar; surface to user.
- **`v0-canary-evaluation` ever fails on the deployed v0-rc1 checkpoint**
  with `apply_fractal_decoder=False`. The freeze guarantee broke. Debug
  before any further v1e work.

---

## 5. Open questions — user answers (2026-05-10 audit)

1. **24-record pack as the sole gate?** → **No.** Use the 24-pack as a
   required automated canary plus the expanded fractal eval (30-60
   records stratified by k=2..8 + non-fractal negative controls).
   Sample-read fractal outputs against targets, per
   `feedback_samples_are_the_only_true_eval_for_cas_native`.

2. **Defer simplex vs unified C+A decision until B-data is in hand?**
   → **Yes.** B's empirical data materially changes the expected value
   of both options. But simplex stays a **peer option**, not a failure
   destination. The user weighs simplex alongside C+A in Path α, not
   only after Paths β/γ.

3. **v0-canary as a required GitHub check?** → **Yes** for
   `cas_native/inference/**` and `cas_native/model/**`. Make it
   **deterministic/automated** (structural diff against frozen baseline
   outputs). **Do NOT require fresh human grading on every PR.**
   Re-baseline only on explicit v0.N-rc bump.

---

## 6. Cost summary

| Phase | Eng-weeks | GPU-hours | Action |
|---|---:|---:|---|
| 0 — v0-rc1 freeze | 0.5 | 0 | Tag, archive, write release doc, wire canary |
| 1 — B (fractal decoder, inference-only) | 1 | 0 | Implement mask + detector + EOS bias; grade |
| 2 — decision gate | 0.25 | 0 | Surface to user with B-data |
| 2β — C (only if Path β) | 3 | 3-4 | Fine-tune from v1c with 3 aux heads |
| 3 — A (only if 2β AND C lifts 10/11/12) | 3 | 7-8 | Pointer/copy fine-tune from v1e_phaseC |
| **Total if best case (Path α + simplex)** | **1.75 + 10-14 simplex** | **0 + simplex** | |
| **Total if Path β through A** | **~8** | **~10-12** | |
| **Total if Path γ (simplex pivot)** | **1.75 + 10-14 simplex** | **0 + simplex** | |

The Minimalist's hidden-cost critique stands: each phase carries 0.5-1
evaluator-day for 24-record careful regrades. Budget 3-4 evaluator-days
across the full v1e plan in addition to engineering time.

---

## 7. Source traceability

- **Wave-1 specs** (full text in agent run logs from this session):
  - A — Pointer/Copy Mechanism architect
  - B — Fractal-Aware Constrained Decoder architect
  - C — Auxiliary Heads + Losses architect
  - D — Systems Integration & Rollout architect
- **Wave-2 critics:**
  - Maximalist — argued unified parallel A+B+C; surfaced C's H2 ↔ B's
    mask synergy.
  - Minimalist — argued B-first asymmetry (zero retraining); escalated
    simplex from kill-switch to peer option.
- **Key project memory pulled:**
  - `feedback_v1d_decision_rule_pointer_copy.md` — the rule that fired
  - `feedback_postprocessor_policy_line.md` — scaffolds are hygiene
  - `feedback_samples_are_the_only_true_eval_for_cas_native.md` —
    grading discipline
  - `feedback_aggregate_metrics_never_get_to_be_the_audit.md` —
    grading discipline
  - `feedback_traceability_is_the_whole_purpose.md` — informs the
    simplex-as-peer-option escalation
  - `project_simplex_redesign_revisit_after_v0.md` — the simplex option
  - `feedback_always_restore_baseline_hparams_for_full_retrains.md` —
    flagged for Path β + Phase 3 hparam discipline
- **Empirical baseline:**
  - `cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T191358Z_CLAUDE_GRADED.md`
    — the v1d audit (15/24 acceptable+) that triggered this design

---

*Core synthesis (audit-revised): B first as opt-in shadow mode with
phrase-trie constraint, fail-closed wrapper, and expanded eval —
because it does not mutate weights and the fail-closed wrapper protects
against output regression. Then a three-way **heuristic** decision
gate (not auto-thresholds) surfaces ship+simplex, unified C(+A), or
pivot-to-simplex to the user with empirical data. Simplex is a peer
option, not a failure destination. The Maximalist's integration
synergies are accepted conditionally inside Path β; the Minimalist's
"earn your slot" discipline is accepted unconditionally for A and C —
and now also for B's promotion to production-default.*
