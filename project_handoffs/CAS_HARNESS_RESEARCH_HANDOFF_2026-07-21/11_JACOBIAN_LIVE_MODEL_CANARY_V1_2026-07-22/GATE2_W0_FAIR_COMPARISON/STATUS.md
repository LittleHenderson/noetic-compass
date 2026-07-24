# Gate 2 — W0 injection-detection experiment family: 4 attempts, 4 honest FAILs, family CLOSED

Controlling status:

`GATE_2_STILL_OPEN / FOUR_ATTEMPTS_EXECUTED_ON_REAL_WEIGHTS / ALL_FAIL_AT_PRE_REGISTERED_BAR / FAMILY_CLOSED_BY_PRE_COMMITMENT / NOT_LICENSED / NO_THRESHOLD_EVER_MOVED`

## What was tested

The Gate-2 sentence is "the scoring actually works on a small model, with fair
comparisons and honest error bars." This family of experiments tried to satisfy
it by showing that a small model's internal state detects prompt injection
BETTER than cheap surface text tricks can, on the 640-scenario matched bank
(`hidden_prompt_injection_bank_v0_20260617`, 320 PRESENT / 320 ABSENT,
80 prompt groups, 5 payload classes).

Fair-comparison discipline (identical in all four attempts):
- grouped 5-fold cross-validation — a whole `prompt_group_id` stays inside one
  fold, so no paraphrase of a prompt is ever in both train and test;
- four surface controls the hidden state must beat: char-ngram hash, text hash,
  prompt length, and (from attempt 2 onward) **layer-0 token identity** — the
  model's own embeddings pooled the same way, i.e. a bag of tokens with ZERO
  transformer computation;
- honest error bars: within-payload permutation null (2,000 label-shuffled
  re-fits), shuffled-label control, and a group-level bootstrap CI (2,000
  rounds) on the hidden-minus-strongest-control margin;
- ONE pre-registered primary layer per attempt, declared before any numbers.

Pre-registered bars, fixed in code and tests, **never moved**: BA >= `0.75`,
margin >= `0.15` over EVERY control, within-payload permutation p < `0.001`,
bootstrap CI lower bound > `0`, shuffled control <= `0.60`.

## The four results

| # | Model | Readout | Primary layer | Hidden BA | Strongest control | Margin | Bootstrap CI on margin | Perm p | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pythia-160m | last-token | 6 | `0.700` | char-ngram `0.600` | `+0.100` | `[-0.030, +0.232]` | `0.0005` | FAIL |
| 2 | pythia-160m | mean-pool | 6 | `0.6875` | l0 token-id `0.650` | `+0.0375` | `[-0.075, +0.151]` | `0.0005` | FAIL |
| 3 | pythia-1b | mean-pool | 8 | `0.7375` | l0 token-id `0.625` | `+0.1125` | `[+0.025, +0.203]` | `0.0005` | FAIL |
| 4 | pythia-2.8b | mean-pool | 16 | `0.7125` | l0 token-id `0.6875` | `+0.025` | `[-0.071, +0.131]` | `0.0005` | FAIL |

Extraction npz sha256, each verified identical after download and in archive:
attempt 1 `a02ad4c2…`, attempt 3 `de958e1f…`, attempt 4 `36a4c285…`.

## What the numbers mean

Two separate true statements, which must not be blended:

1. **A real signal exists.** In every attempt the hidden state predicted
   injection presence far above chance and far above its own shuffled-label
   control (~`0.50`), with permutation p = `0.0005`. That part is real, measured
   on real weights.
2. **The experiments cannot show the signal is more than surface reading.**
   Against the layer-0 token-identity control — which does no model computation
   at all — the hidden state's advantage was `+0.0375`, `+0.1125`, and `+0.025`
   at 160M / 1B / 2.8b. Only attempt 3's bootstrap CI excluded zero, and that
   did not replicate at 2.8b.

**The scale hypothesis was falsified, not confirmed.** The token-identity
control got STRONGER with model size (`0.65` → `0.625` → `0.6875`) because wider
embeddings carry more linear surface capacity, while hidden accuracy stayed flat
(~`0.70`–`0.74`). At 2.8b layer 24 the hidden state scored *below* the l0
control (`-0.025`).

## Family closure (by pre-commitment, not by hindsight)

Attempt 4's registration stated in advance that four disclosed attempts without
a pass closes the family. That condition was met, so the family is CLOSED — no
attempt 5 of the same design.

Recorded conclusion: linear probes on pooled or last-token W0 states, over a
bank whose label is a property of the INPUT TEXT, cannot demonstrate
above-surface detection at accessible scales. When the label is a text property,
surface controls are structurally competitive and strengthen with embedding
width — the deck is stacked against a "beyond surface" claim by construction.

Structural lesson recorded for the next route: a fair "hidden beats surface"
claim needs labels that surface CANNOT carry by construction. The already-ported,
already-tested v5 pre-speech gate is exactly that design — the SAME EXACT prompt
text producing BOTH behaviors (`COMPLIED` and `REFUSED`) across sampled runs, so
the label varies while the surface is constant, making surface controls chance
by construction.

## Honesty record

- No threshold was ever weakened; every FAIL is reported at the bar as written.
- Every attempt is in `injection_detection_attempts_registry.json`, pass or fail,
  so any future PASS must disclose the full attempt count and confirm on a fresh
  held-out bank.
- Under-resolved early runs were killed BEFORE writing any report, so each
  pre-registration was made without having seen result numbers.
- Claim status stays `NOT_LICENSED`. Gate 2 remains OPEN; the score stays `0.38`.

## Artifacts

- Branch `feat/joined-canary-reconciliation-20260724`: `8a8624d` (scorer +
  extractor + honesty tests), `20b3ffb` (parallelism, wall-clock only), `94f3f4e`
  (attempt 1), `4b91e25` (l0 control + 6 tests), `07c3738` (attempt 2),
  `bcf7009` (attempt 3), `d4ba548` (attempt 4 + closure). The worktree's origin
  is the read-only Attempt-5 bundle, so the branch travels as
  `joined_canary_reconciliation_20260724.bundle`.
- `evidence/`: all four report JSONs, attempts registry, run stdout, W0 npz.
- Archive: `D:\tksCAS-archive\gate2_w0_fair_comparison_attempt1_20260724\`.

## Next

A 14-agent expert panel was commissioned to diagnose the failure and rank
legitimate routes to Gate 2 (five investigative lenses, four adversarial
stances, an integrator, three refutation reviewers, one report writer). Its
findings and the chosen route are recorded separately when complete.
