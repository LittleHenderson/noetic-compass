# Candidate E Stage 3 — Wrap-Up (2026-05-13)

Canonical end-of-loop summary for the Candidate E free-decode source-copying line of work. Both dev and held-out gates passed; Codex audit at commit `707249b` (2026-05-13T07:55Z) closed the loop with "Stage 3 is done for this Candidate E loop... No higher ratio, no longer run, no DAgger. That would be tuning after a pass." Next authorized work (per `decisions.md` 2026-05-13T06:30Z) is chat REPL + Mode 7 traceability planning — docs only, no further training runs.

## TL;DR

- Free-decode source-identifier recovery moved from **0.4412** (E2c-continuation baseline) to **0.7778** on dev and **0.6439** on held-out — both clear the **0.50** primary gate.
- Hard safety stayed perfect throughout: source-swap **cross_emission_count = 0** at every measurement point.
- Both load-bearing gates passed on both dev (strong-pass, ≥ 0.70) and held-out (primary-pass, ≥ 0.50).
- No further Stage 3 training authorized. The next move is chat REPL + Mode 7 traceability integration planning.

## The Candidate E journey

Each row is one stage. The "headline value" column reports the metric the stage's gate hinged on (TF identifier-level recovery for E2b–E2c-cont, free-decode aggregate recovery for e3-baseline forward).

| Stage | What changed | Headline value | Notes | Commit |
|---|---|---|---|---|
| Pre-Candidate-E baseline | n/a | n/a | A/B/C/D postmortem: TF ~0.30, free-decode 0.00 — exposure-bias collapse | `939acb7` |
| Stage 1B corpus | New `rpm_copy_grounding_v2` corpus generator + cross-chain coverage | n/a | Audit data plumbing for source-pointer supervision | `0fc1089`, `32a7a86`, `a267f9d` |
| E2a (warmup) | LM + slot stability, `copy=0.0` | TF id_recovery 0.00 (expected) | Informational warmup; LM/slot trace stable | `8ad6a3b` |
| E2b (full Stage 2) | Added copy + span + contrastive + coverage losses | TF id_recovery **0.0062** (4/648); free-decode **0.3137** | Missed the 0.80 design-doc gate; revised gate later focused on TF per-token | `f8cc8b4`, `f53baca` |
| E2c | Added `L_start_anchor` (2.0) + `L_anchor_contrastive` (1.0) | TF per-token **0.628** | Missed locked 0.70 gate. `right_start_drift = 412/648` dominated — anchor working but body drifting | `a0bb9cd`, `cfcbc39` |
| E2c continuation (1000 more steps) | Same losses, same hparams, warm-start | TF per-token **0.923** | Cleared 0.70 gate with 0.223 margin. TF id_recovery 0.660; right_start_drift 412 → 195; exact spans 181 → 428 | (continuation only) |
| e3-baseline (decision point) | No training; free-decode measurement on E2c-cont checkpoint | Free-decode id_recovery **0.4412** | Middle branch per plan §2 (0.30 < x < 0.50) → scheduled-sampling Stage 3 training authorized | `ef468d2` |
| Stage 3 (scheduled sampling) | `--ablation e3`, `--scheduled-sampling-schedule "linear:0.0-0.5:1-1000"`, 1000 steps | Free-decode id_recovery **0.7778** (dev) | Strong pass (≥ 0.70). All E2c losses retained verbatim. Pod run `stage_e3_20260513T043823Z` | `dd07bdb`, `e9a0b76`, `df22112` |
| Held-out confirmation | Same Stage 3 checkpoint; evaluated on never-seen test pack + swap-eval pack | Free-decode id_recovery **0.6439** | Primary pass; strong-pass missed. Cross-emission stayed at 0 | `f3adfe9` |

The eval-result files for each measured stage are archived under `docs/working/candidate_e/eval_results/` and `docs/working/candidate_e/e2{a,b}_run_*/`.

## Headline numbers (Stage 3 final checkpoint, dev vs held-out)

Both columns evaluate the same checkpoint, `stage_e3_20260513T043823Z/ckpt_final.pt`. The dev pack is `rpm_copy_grounding_v2_dev.jsonl`; the held-out pack is `rpm_copy_grounding_v2_test.jsonl` for free-decode + `rpm_copy_grounding_v2_source_swap_eval.jsonl` for swap. Each pack is 200 records / 50 swap pairs.

| Metric | Dev | Held-out | Threshold | Pass on dev | Pass on held-out |
|---|---|---|---|---|---|
| Free-decode `aggregate_recovery_rate` (PRIMARY gate) | **0.7778** (476/612) | **0.6439** (387/601) | ≥ 0.50 | yes | yes |
| Free-decode `full_recovery_rate` (whole-record) | 0.535 (107/200) | 0.400 (80/200) | — | — | — |
| Swap `pair_pass_rate` (diagnostic) | 0.38 (19/50) | 0.16 (8/50) | — | — | — |
| Swap `cross_emission_count` (HARD safety) | **0** | **0** | exactly 0 | yes | yes |
| TF `identifier_recovery_rate` | 0.7392 (479/648) | 0.7218 (467/647) | — informational at e3 | — | — |
| TF `per_token_accuracy` | 0.9166 | 0.8937 | — informational at e3 | — | — |
| Free-decode strong-pass annotation | 0.7778 vs 0.70 | 0.6439 vs 0.70 | ≥ 0.70 | yes | no |

Both load-bearing gates (PRIMARY free-decode ≥ 0.50, HARD safety swap cross-emission == 0) pass on both packs.

## The TF → free-decode gap reversal

Before Stage 3 training (E2c-continuation checkpoint, measured under `--stage e3-baseline`):

- TF identifier recovery: 0.6605
- Free-decode identifier recovery: 0.4412
- Gap: **−21.93 pp** (TF much stronger than free-decode — the textbook exposure-bias signature from the A/B/C/D postmortems).

After Stage 3 training (same evaluator, dev pack):

- TF identifier recovery: 0.7392
- Free-decode identifier recovery: 0.7778
- Gap: **+3.86 pp** (free-decode slightly stronger than TF on dev).

Held-out:

- TF identifier recovery: 0.7218
- Free-decode identifier recovery: 0.6439
- Gap: **−7.79 pp** (TF stronger again, but the gap is roughly a third of the baseline gap, and free-decode is still well above the 0.50 floor).

The dev free-decode-beats-TF outcome is not unusual after scheduled-sampling training. Codex's read (`codex_audit.md` 2026-05-13T05:57Z): "after scheduled sampling, the model has been trained to recover from its own slightly imperfect prefixes. That can make free-decode look better than strict teacher-forced pointer scoring, especially when the TF metric requires exact pointer argmax for every token in a span." It is not a metric bug; it is a real consequence of training under mixed-prefix conditioning.

Dev → held-out generalization is asymmetric:

- TF per-token drops by only **1.7–2.3 pp** dev → held-out.
- Free-decode drops by **13.4 pp** dev → held-out.

This says the copy-pointer module generalizes cleanly across the data split, but the model's ability to keep that pointer alive across its own self-generated continuations is somewhat over-fit to the dev distribution. The held-out result still clears the 0.50 gate by 0.14, so the dev → held-out drop is acceptable, but it is real and worth surfacing.

## Variant honesty

The Stage 3 mechanism is the **Bengio et al. (2015) one-step (TF-conditioned) variant** of scheduled sampling. It is **NOT** a full autoregressive student rollout. Authoritative statement of the variant lives in `noetic-compass-scaffold/noetic-compass/cas-native/training/scheduled_sampling.py:1-71`.

What the cheap variant actually does, per training step:

1. **Pass 1 (no-grad, one forward):** `model(batch)` at the gold prefix → greedy argmax over `lm_logits` → "what the model would say next, given the gold prefix so far."
2. **Mix:** per-position Bernoulli(ratio) decides whether each non-BOS decoder input position is replaced with the previous-position greedy prediction. Position 0 (BOS) is never substituted.
3. **Pass 2 (with-grad, one forward):** `model(mixed_batch)` against gold targets — supervised forward with a (partially) self-fed decoder input.

What the cheap variant is NOT: a fully autoregressive student rollout that iterates L times so each substituted token sees the already-substituted prefix at positions 0..t−1. The full variant correctly models the test-time distribution at the cost of ~L no-grad forwards per training step (≈96× more compute for L=192).

Cost rationale: 2 forwards per step (cheap) vs ~L forwards per step (full). The cheap variant is the standard published implementation (Bengio 2015 §3.1, T5, NMT systems). Codex's re-audit verdict at commit `3d77ffd`: "the implementation is the cheap 'one-step' version, not full autoregressive rollout. That's acceptable for this first test, but the docs/comments need to say that honestly." The docstring now says so.

If the held-out 0.6439 turns out to be insufficient for downstream chat/REPL behavior, the cheap → full rollout upgrade is a **strict superset** — nothing in the current implementation has to be unwound. That work is explicitly not authorized today.

## What is locked in for future runs

The Stage 3 work landed three pieces of stable surface that future Candidate E (or successor) work inherits without re-derivation:

- **`--ablation e3`** inherits e2c loss weights verbatim. No new losses. The ablation alias exists purely so manifests and logs are unambiguous between e2c (TF baseline) and e3 (scheduled sampling). See `noetic-compass-scaffold/noetic-compass/cas-native/training/config.py` (`ABLATION_OVERRIDES` table).
- **`--scheduled-sampling-schedule "linear:<start>-<end>:<warmup>-<full>"`** is the canonical schedule format. A constant alternative (`--scheduled-sampling-ratio <float>`) is also supported; the schedule wins when both are set. Empty default disables. Stage 3 itself used `"linear:0.0-0.5:1-1000"` over 1000 steps.
- **Two public helpers** in `noetic-compass-scaffold/noetic-compass/cas-native/training/scheduled_sampling.py`: `forward_with_scheduled_sampling` (top-level entry) and `build_scheduled_sampling_input` (factored substitution-mask builder, exposed for direct test inspection). Plus `resolve_ratio_at_step` for the linear schedule.

Equivalence at `ratio=0` is bit-for-bit guaranteed: `tests/training/test_scheduled_sampling.py` pins three checks using `torch.equal` (no `allclose`) on every output tensor and every per-parameter gradient — `test_forward_at_ratio_zero_returns_identical_outputs`, `test_forward_at_ratio_zero_gradients_match_tf`, `test_forward_at_ratio_zero_loss_matches_tf`. 23 tests total in that file, plus regression pins in the evaluator gate-semantics test file. All 23 + 81 tests pass as of commit `e9a0b76`.

## Limitations and open questions

- **One-step variant, not full rollout.** The cheap variant trains on a "gold prefix → one substituted step" mix, not on a fully self-fed prefix. If chat/REPL integration shows the 0.6439 held-out rate is insufficient for the demo target, the full rollout is the strict-superset upgrade. Not authorized today.
- **Dev → held-out generalization gap.** Free-decode `aggregate_recovery_rate` drops 13.4 pp dev → held-out; TF drops only 1.7–2.3 pp. The copy module generalizes; the keep-copying-while-generating behavior is somewhat dev-tuned. Held-out still clears the gate by 0.14.
- **Strong-pass (≥ 0.70) reached on dev only.** Held-out is 0.6439. The first chat/REPL version should surface recovery confidence and traces, not pretend every multi-ID output is perfect (Codex 2026-05-13T07:55Z: "it matters for product behavior").
- **Swap `pair_pass_rate` dropped 22 pp dev → held-out** (0.38 → 0.16) while `cross_emission_count` stayed at 0. Plain reading: the model is still safe (not leaking the other pair member's body), but is less complete at recovering every ID across both members of a held-out pair. Completeness, not source confusion, is the residual weakness.
- **Pack sizes are small.** 200-record dev / 200-record test / 50 swap pairs. Larger held-out confirmation could tighten the generalization estimates if a future loop wants more confidence before pushing the architecture into product.
- **TF-vs-free reversal on dev.** Free-decode beating TF on dev (+3.86 pp) is unusual at face value but explained by the scheduled-sampling objective: the model is trained to recover from imperfect prefixes, and the strict TF identifier metric demands exact argmax for every token in a span. The held-out gap (−7.79 pp, TF stronger) is more conventional and is the better generalization signal.

## What is authorized next

Per `decisions.md` 2026-05-13T06:30Z (ratified by Codex audit `707249b` and user "go"):

- **Three parallel docs only, no code, no pod work:** this wrap-up; the chat REPL Stage 3 integration plan (`docs/working/chat_repl_stage3_integration_plan_2026_05_13.md`); the Mode 7 traceability design (`docs/working/mode_7_traceability_design_2026_05_13.md`).
- **No new training runs without a fresh decision.** Codex explicitly closed: "No higher ratio, no longer run, no DAgger. That would be tuning after a pass."
- **No DAgger.** Reserved for the case where scheduled sampling missed the gate; it did not.
- **No higher scheduled-sampling ratio.** Same reason.
- **No move to integration execution until Codex audits the three plan docs and user issues a go on which integration step runs first.**

The Stage 3 mechanism is locked. Whether the held-out 0.6439 is enough for the first chat/REPL demo is a product question to be answered by integration planning and a smoke pack, not by more training.

## Artifact pointers

### Commits

- `dd07bdb` — scheduled sampling implementation (`scheduled_sampling.py` + trainer hookup + 23 tests).
- `e9a0b76` — Codex re-audit blocker patches (mixed-input direct inspection tests; docstring variant-honesty note; CPU smoke flag refresh).
- `ef468d2` — e3-baseline result on E2c-continuation checkpoint (decision point, 0.4412).
- `df22112` — Stage 3 dev result (strong pass, 0.7778).
- `f3adfe9` — Stage 3 held-out confirmation (primary pass, 0.6439, generalization confirmed).

### Pod run directory (Stage 3 training)

- `/workspace/tksCAS/stage_e3_20260513T043823Z/` on RunPod. Final checkpoint: `ckpt_final.pt`. Intermediate: `ckpt_step_500.pt`. Warm-started from `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/ckpt_final.pt`.

### Eval result files (local archive)

All in `docs/working/candidate_e/eval_results/`:

- `e3_baseline_findings_20260513T030500Z.md` + `e3_baseline_report_20260513T030500Z.json` — the 0.4412 decision-point measurement.
- `e3_post_training_findings_20260513T054125Z.md` + `e3_post_training_report_20260513T054125Z.json` — Stage 3 dev result, 0.7778 strong pass.
- `e3_heldout_findings_20260513T061539Z.md` + `e3_heldout_report_20260513T061539Z.json` — held-out confirmation, 0.6439 primary pass.
- `e3_cpu_smoke_report_20260513.json` + `e3_cpu_smoke_trainer_log_20260513.jsonl` — pre-launch CPU smoke verifying the scheduled-sampling implementation and trainer wiring.

### Prior-stage archives

- `docs/working/candidate_e/e2a_run_20260512T150330Z/` — E2a warmup.
- `docs/working/candidate_e/e2b_run_20260512T172129Z/` — E2b full-loss run (gate miss, dominant `right_start_drift`).
- E2c and E2c-continuation archives live on pod-side runs referenced by `decisions.md` 2026-05-12T17Z, 2026-05-13T00:20Z, 2026-05-13T02:00Z.

### Plan and audit anchors

- Stage 3 plan v2 (executed): `docs/working/candidate_e/stage3_plan_2026_05_13.md`.
- Codex audits: `docs/working/agent_exchange/codex_audit.md`, sections 2026-05-13T05:57Z (Stage 3 dev pass), 2026-05-13T06:30Z (held-out pass + "done for this loop"), 2026-05-13T07:55Z (closing verdict at commit `707249b`).
- Decisions: `docs/working/agent_exchange/decisions.md`, entries 2026-05-13T03:30Z (baseline), 2026-05-13T03:45Z (local build), 2026-05-13T04:25Z (training), 2026-05-13T06:05Z (held-out), 2026-05-13T06:30Z (post-Stage-3 planning authorization).
