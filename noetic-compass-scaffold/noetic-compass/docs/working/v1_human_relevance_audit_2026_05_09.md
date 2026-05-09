# v1 PREFIX128 5ep — Human Relevance Audit (2026-05-09)

## Context

After the cas_prefix_mask architectural fix landed (commit `2530d1b`)
and the v1 PREFIX128 5-epoch retrain produced the headline checkpoint,
two automated diverse-record eval logs were generated against the same
8 stratified val records:

- `diverse_eval_8records.log` — raw greedy output, no postprocessor
- `diverse_eval_with_repair_v3.log` — same checkpoint, with
  `identifier_repair` post-gen substitution + `top_p=0.95 / T=1.0`
  sampling

The session report at the time framed these as "5/8 above the proof
gate" based on structural counts (task routing, Ω-name recovery,
hard-notation/jargon = 0). That framing was incomplete: it conflated
"passes structural checks" with "human-facing acceptable." A direct
read of the gens against their targets reveals that several outputs
that pass structural metrics are still semantically wrong, partially
incoherent, or clipped mid-sentence. **The corrected verdict is that
v1 is a real architectural improvement but is NOT chat-REPL-ready.**

The grades below are the user's, transcribed verbatim. They are
authoritative for this audit.

## Grading scale

- **Green** — fluid, faithful to source, lands its conclusion.
- **High yellow** — fluent and feels good; one structural slip.
- **Yellow** — understandable, but body content drifts from source.
- **Flop / Wrong / Incoherent** — target is clearly better, or output
  is broken language / wrong task.

## diverse_eval_8records.log (raw greedy, no repair)

| # | Task / source | Grade | User notes (verbatim) |
|---|---|---|---|
| 1 | state_literal `^7^C_{F2}|T` | Yellow | useful but no nuance/flavor, just exact diagnosis |
| 2 | binary_composition `^2^C × ^7^C` | Yellow | useful but content binding is off |
| 3 | cross_register_omega `(^1^E|E × ^1^E|f) = ^1^E|Ω_judgment` | Yellow / high | best raw answer, lacks a real bring-it-home conclusion; Ω wrong |
| 4 | recipe `Θ(Ω_decision_60) = 1*^3^P|T + 2*^6^P → ... + 0.1*Λ·Ω_engagement_side` | High yellow | felt good as English; changes `decision_60` to `rehearsal_67`, invents coefs, swaps CAS meaning |
| 5 | fractal_sequence `Φ<6:8:0:3>` | Flop | target is way better |
| 6 | meta_logic_relation `NoeticCluster{^8} ⊆ Noetics` | Wrong | source is cluster of one; model says cluster of three |
| 7 | rpm_chain (4 let-bindings + arrow) | Yellow | fluid prose; wrong task interpretation — explains a valid rpm_chain as invalid |
| 8 | invalid_to_explanation (undef var) | Fluid + correct | basically right, but clipped / incomplete |

**Aggregate:** zero greens. 4 yellows / 1 high yellow / 1 flop /
1 wrong / 1 yellow-but-mis-routed / 1 truncated. None of these are
"chat-ready." The fluent-but-wrong cases (3 and 4) are the most
dangerous because they sound right.

## diverse_eval_with_repair_v3.log (with repair, top_p sampling)

| # | Task | Grade | User notes (verbatim) |
|---|---|---|---|
| 1 | state_literal | Good | — |
| 2 | binary_composition | Yellow | still wrong noetic on second term |
| 3 | cross_register_omega | Yellow | repair fixes Ω name; register/mode content still wrong |
| 4 | recipe | Yellow | repair improves Ω/coefs; body meaning still wrong |
| 5 | fractal_sequence | Wrong | — |
| 6 | meta_logic_relation | Incoherent | — |
| 7 | rpm_chain | Yellow / incomplete | good prose, wrong task, truncated |
| 8 | invalid_to_explanation | Yellow / incomplete | same answer pattern as 7, still truncated |

**Aggregate:** 1 green (record 1), 4 yellows (2/3/4/7), 1 wrong (5),
1 incoherent (6), 1 truncated-yellow (8). Records 7 and 8 produce
**the same incomplete sentence** for two different tasks — the model
emitted identical "starting point... destination... cannot be
completed... A careful reader would noti..." text and ran out of
budget mid-word.

## What identifier repair does and doesn't fix

The repair postprocessor is doing what it was designed for. Its scope
is narrow on purpose. Specifically:

| Failure class | Repair fixes? |
|---|---|
| Hallucinated Ω name (`rehearsal_67` instead of `decision_60`) | **Yes** (100% on greedy when slot exists in gen) |
| Wrong coefficient when slot exists (`0.5` should be `1.5`) | **Yes** (when source has the coef and gen emits the slot) |
| Wrong noetic alias ("just clicked" should be "rubs the wrong way") | **No** — semantic, continuous-learning territory |
| Wrong domain ("operational" should be "principled") | **No** — semantic |
| Wrong register count ("three modes" when source has two) | **No** — semantic |
| Cluster size error ("cluster of three" when source is one) | **No** — semantic |
| Task misrouting (valid rpm_chain → invalid_to_explanation) | **No** — needs the cas_routing compilability gate, not repair |
| Truncation (clip mid-sentence) | **No** — generation-side budget / EOS issue |
| Coefficient when gen never emits the slot | **No** — repair never invents slots |
| Body incoherence under repair (record 6) | **Likely makes worse** — substituting words into already-broken syntax doesn't heal the syntax |

**Interpretation:** repair patches symbol copying. It does not patch
semantics, routing, truncation, or coherence. The "100% Ω-name
recovery" headline from the prior session note was real but narrow —
it does not imply the outputs are correct.

## Corrected project state

| Item | Status |
|---|---|
| cas_prefix_mask architectural fix | Real win — confirmed by overfit (87.5% verbatim) and by task-routing 4/8 → 7/8 on diverse eval |
| v1 PREFIX128 5ep training | Real improvement over no-prefix baseline on every axis except Ω-name copy |
| identifier_repair postprocessor | Useful but narrow — Ω/coef copy only |
| Current v1 outputs as graded by a human reader | **Not human-facing yet** |
| chat.py REPL wiring | **Stays deferred** |

The "5/8 combined strict + strong-partial" framing in the prior
CHANGELOG entry passes structural counts but does not survive a
human read. Treating it as a green light for chat integration would
have repeated the B-4.1 audit failure mode: structurally-shaped output
that doesn't hold up when read.

## Next engineering moves (corrected priority)

**Not** chat REPL integration. Three issues stand between current
state and human-facing readiness, ranked by reach:

1. **Truncation / EOS.** Records 7 and 8 produced the same incomplete
   sentence. The model is hitting the `max_new_tokens=120` budget or
   stopping on a non-EOS token. Two fixes:
   - Raise `max_new_tokens` for invalid_to_explanation specifically
     (those targets average 330 chars, often longer than the budget
     allows after CAS-prefix expansion).
   - Tighten the EOS handling so the model doesn't cut mid-clause.

2. **Force compilability-gated routing at inference.** The
   `cas_routing` library is built and tested (commit `c79294f`) but
   not invoked anywhere. Calling
   `route_by_compilability(source_cas)` and using
   `build_prompt_from_routing(...)` instead of a generic wrapper
   would push valid `rpm_chain` to `cas_to_english` deterministically,
   regardless of how the model wants to interpret the body. This
   removes the rpm_chain misroute (records 7-shape) without
   retraining.

3. **Larger human-graded sample.** 8 records is too small a sample
   for any go/no-go on a user-facing release. A 20-30 record
   stratified sample across all task categories, graded with the
   same green/yellow/flop scale, would tell us whether the patterns
   above (semantic drift, mode-count drift, truncation, coherence
   under repair) are systemic or pocket failures.

Only after #1, #2, and #3 should chat REPL wiring be reopened. And
the gate for that wiring is "≥80% green or high-yellow on a 20-record
human sample," not aggregate metrics.

## Process correction

I (Claude) ran structural eval and reported the headline numbers
without grading the gens against the targets the way a human reader
would. The structural metrics were correct but they masked semantic
errors that were obvious on a direct read. Going forward, on any
diverse-eval pass against a CAS-Native checkpoint, the deliverable is
a per-record grade against the target, not just an aggregate count.
"100% Ω recovery" is not a substitute for "this output reads like the
target." The user's grading discipline above is the right standard.
