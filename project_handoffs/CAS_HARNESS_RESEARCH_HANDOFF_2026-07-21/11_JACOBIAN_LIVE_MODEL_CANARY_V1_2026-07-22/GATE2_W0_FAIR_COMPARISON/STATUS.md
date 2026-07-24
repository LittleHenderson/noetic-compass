# Gate 2 — first real W0 fair-comparison experiment (Attempt 1): honest FAIL

Controlling status:

`GATE_2_STILL_OPEN / ATTEMPT_1_EXECUTED_ON_REAL_WEIGHTS / PRE_REGISTERED_PRIMARY_FAIL / REAL_SIGNAL_PRESENT_BUT_NOT_ABOVE_SURFACE / NOT_LICENSED / NO_THRESHOLD_MOVED`

## What this experiment was

The first real test of the Gate-2 sentence — "the scoring actually works on a
small model, with fair comparisons and honest error bars" — on the
prompt-injection detection target (PRESENT vs ABSENT):

- **Model / data (all real):** `EleutherAI/pythia-160m` last-token residual
  stream at layers 3/6/9, extracted on the A40 pod for all 640 prompts of the
  surface-clean matched bank (`hidden_prompt_injection_bank_v0_20260617`,
  320 PRESENT / 320 ABSENT, 80 prompt groups, 5 payload classes).
  Extraction npz sha256 `a02ad4c204ca82260a87ec5fb299719a40ac52ec52987df3160f49308fe04249`
  (verified identical after download, in the handoff copy, and in
  `D:\tksCAS-archive\gate2_w0_fair_comparison_attempt1_20260724\`).
- **Fair comparison:** grouped cross-validation (no prompt group split across
  train/test), against three surface controls — char-ngram hash (the strong
  one), text hash, prompt length.
- **Honest error bars:** within-payload permutation null (2,000 label-shuffled
  re-fits), shuffled-label control, and a group-level bootstrap CI (2,000
  rounds) on the hidden-minus-surface margin.
- **Pre-registration:** layer 6 declared the single confirmatory endpoint
  BEFORE any result was seen (earlier under-resolved runs were killed before
  writing any report — zero result numbers observed prior to registration).
  Thresholds fixed in code and tests before the run: BA >= 0.75, margin >= 0.15
  over every surface control, permutation p < 0.001, bootstrap CI lower bound > 0.

## The result (primary layer 6)

| Measure | Value | Bar | Verdict |
|---|---|---|---|
| Hidden balanced accuracy | `0.700` | >= 0.75 | **fail** |
| Char-ngram surface control | `0.600` | — | binding control |
| Margin over char-ngram | `+0.100` | >= 0.15 | **fail** |
| Bootstrap CI on that margin | `[-0.030, +0.232]` | lower > 0 | **fail** (includes zero) |
| Within-payload permutation p | `0.0005` | < 0.001 | pass |
| Shuffled-label control mean | `0.506` | <= 0.60 | pass |
| Margin over text hash / length | `+0.300` / `+0.275` | >= 0.15 | pass |

Secondary (exploratory, license nothing): layer 3 BA `0.7125`, layer 9 BA `0.6625`
— same failure pattern.

## Honest reading

Two true sentences that must be kept separate:

1. **A real signal exists.** The layer-6 hidden state predicts injection
   presence far better than chance (0.700 vs 0.506 shuffled), and the
   permutation test says luck alone produces that less than 1 time in 2,000
   (p = `0.0005`).
2. **The experiment cannot show the signal is more than surface reading.**
   Against the char-ngram control — a probe that only sees character patterns
   of the prompt text — the hidden state's advantage is `+0.100`, and the
   honest error bar on that advantage stretches from `-0.030` to `+0.232`.
   Because it includes zero, we cannot rule out that the hidden state is just
   re-encoding the surface text. That is exactly the claim Gate 2 exists to
   test, so the verdict is **FAIL**, and no threshold was moved to change it.

## Multiplicity discipline (attempts registry)

`injection_detection_attempts_registry.json` (in evidence/ and in the repo
branch) records every attempt, pass or fail. Any future PASS must disclose the
full attempt count, and confirmatory license additionally requires a fresh
held-out bank. Repeating variants until one passes is the failure mode this
registry exists to prevent.

## Legitimate follow-ups (each a NEW pre-registered attempt)

- **Attempt 2 (planned):** mean-pooled token features instead of last-token
  (the injected payload sits mid-prompt; a 160M model's last-token state may
  simply not carry it forward), same bank, same thresholds, primary endpoint
  declared before any numbers.
- **Attempt 3 (if needed):** larger model (pythia-1b), where prior harness
  work found stronger drive-local structure.

## Artifacts

- Repo branch `feat/joined-canary-reconciliation-20260724` commits `8a8624d`
  (scorer + extractor + 3 honesty tests), `20b3ffb` (parallelism, wall-clock
  only), `94f3f4e` (this evidence). Bundle:
  `joined_canary_reconciliation_20260724.bundle` (sha256 `0e29a60cc26ed807…`,
  verified okay) — origin of the worktree is the read-only Attempt-5 bundle,
  so the branch travels by bundle.
- `evidence/`: full report JSON, run stdout, attempts registry, W0 npz.
- Archive: `D:\tksCAS-archive\gate2_w0_fair_comparison_attempt1_20260724\`.
