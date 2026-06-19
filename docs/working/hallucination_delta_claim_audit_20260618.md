# Hallucination Delta Claim Audit

Date: 2026-06-18

Audited inputs:

- `docs/working/HALLUCINATION_AUDIT_PACKAGE.md`
- `docs/working/CAS_HARBOR_TRAJECTORY_DELTA_20260618.md`
- local scratch scripts `pt_q15.py`, `pt_q15_delta.py`, `pt_adm2.py`
- attempted pod check: `root@195.26.233.21 -p 44506` timed out, so `/root/capture_hall_q15_v2_*` artifacts could not be verified locally

## Verdict

`OPEN` / `NOT LICENSED`.

The W0-to-W1 structural trajectory delta is a serious research lead, but the current package does not yet license a hallucination-detection claim.

## Blocking Findings

1. The package calls the result licensable while the active-goal auditor still has hallucination detection/prevention `OPEN` / `NOT LICENSED`.

2. The reported permutation row says `p=0.00100` passes a `< 0.001` threshold. That is not claim-safe as written. With 1000 permutations, the usual plus-one p-value is `1 / 1001 = 0.000999...`; reports must store the exact numeric value and gate evaluation, not rounded prose.

3. The Qwen-1.5B scaling statement (`L27 delta: 0.7795`) is not backed by a pulled local report artifact. The only local Qwen-1.5B evidence found is scratch code pointing at pod paths under `/root/capture_hall_q15_v2_W0` and `/root/capture_hall_q15_v2_W1`; the pod timed out during audit.

4. `pt_q15_delta.py` computes the printed layer delta with an invalid balanced-accuracy expression:

   `((pred == y).mean() + (pred != y).mean()) / 2`

   That expression is always `0.5`, so this scratch script cannot substantiate the claimed `0.7795` result.

5. `pt_q15.py` computes the main real BA correctly, but its permutation loop uses the same invalid accuracy-plus-not-accuracy expression, making the p-value and max-permutation comparison unusable.

6. The package does not yet include a generated-prefix/token-identity/shuffled-time/layer-0/report-schema-backed control artifact. Identical prompt text is a good control against prompt leakage, but it is not enough to license an internal hidden-state hallucination detector by itself.

7. The new local `--evaluate-w0-static` evaluator addition is not yet license-grade. It lacks layer-0, generated-prefix, token-identity, per-stratum floor, and permutation controls for the W0-static subclaim, and it is not wired into the active-goal auditor as a required-gate schema.

## What Can Be Claimed Now

Safe wording:

> CAS Harness has a promising W0-to-W1 hidden-state trajectory-delta research lead for hallucination-risk detection on a small matched stale-majority subset. It needs a schema-backed confirmatory report with full controls before it is `LICENSED`.

Unsafe wording:

> CAS Harness has a licensed hidden-state hallucination detector.

Unsafe wording:

> Qwen-1.5B validates the method.

## Required Next Gate

Produce a committed JSON report using the hardened evaluator, not scratch scripts. The report must include:

- exact model ID and layer
- row count and label distribution
- exact prompt-group / challenge-mode contract
- grouped or otherwise justified CV split
- correct balanced accuracy
- exact p-value with gate result
- prompt word and char controls
- generated-prefix word and char controls for any post-W0 timing
- token-identity baseline
- layer-0 baseline
- shuffled-time baseline
- shuffled-label and within-stratum permutation
- per-topic or per-stratum floors
- row-retention gate if any timing intersection is used
- active-goal auditor visibility

Until that exists, the result remains `OPEN` / `NOT LICENSED`.

---

## 2026-06-18 UPDATE — Required Next Gate produced and run; result is `NOT LICENSED` (now disproven, not merely unverified)

The hardened evaluator was built (`lic_eval.py`) and run on the pod against
`/root/capture_hall_q15_v2_{W0,W1}`. Committed machine report:
`docs/working/lic_report_q15_pooled.json`. Full write-up:
`docs/working/HALLUCINATION_LICENSE_EVAL_QWEN1.5B.md`.

Findings #4 and #5 (the `(acc + (1-acc))/2 ≡ 0.5` balanced-accuracy bug) are **FIXED**
and committed. Finding #3 (no pulled artifact) is **RESOLVED**: the `L27 = 0.7795`
number reproduces, but only under **ungrouped CV + full-data direction** — a leak.

Under the required **leakage-safe, grouped** evaluation (GroupKFold by exact prompt;
risk direction trained inside each fold) with the full hard-control panel, the
hidden-state delta **loses to text in every configuration**:

| Configuration | Hidden BA | Best text control | Margin |
|---|---|---|---|
| Pooled all-mode (61 groups, data gate OK) | 0.634 | 0.711 | −0.077 |
| mv-only (cleanest design) | 0.807 | 0.832 (first token) | −0.025 |
| Shared-first-token (token neutralized) | 0.640 | 0.678 (prompt) | −0.039 |

Pooled gate panel: accuracy_floor FAIL (0.634), margin_over_text FAIL (−0.077),
residual FAIL (0.480 = chance), held-out-topic FAIL (0.573). `LICENSED = False`.

**Root cause:** W0 is identical within a same-prompt group (zero pre-answer signal by
construction); W1's only signal is the first emitted token, which itself leaks the
label; even with the token held constant the prompt leaks. The delta carries nothing
beyond visible text.

**Verdict stands and is strengthened:** `OPEN` / `NOT LICENSED` — the hidden-state
hallucination detector is **disproven** for these captures, not merely unconfirmed.
A real license requires a **new teacher-forced identical-prefix capture** (prompt +
prefix + first token held byte-identical across labels, hidden state read before the
answer-value token). That experiment does not exist yet.
