# Analogy wiring probe v0.2: before-reading and self-test RESULT (2026-09-23)

**The rules** are `PREREG_ANALOGY_WIRING_PROBE_v0_2.md` (with amendments A1 and A2) and `PREREG_PROBE_SELF_TEST.md`.
Both were committed before these runs.

**Where it ran.** AWS `g4dn.2xlarge` (Tesla T4), instance `i-07e0016d92bd6197b`. The run is logged in `RUN_LOG.md`
(attempt 5). The reading was made by a program: `../aws_probe_job/read_results.py`, which writes
`../aws_probe_job/RESULTS_READING.json`.

**What these numbers are.** Forward passes only. They are wiring measurements, not answer accuracy. Each is labelled
by what it can support: `DIAGNOSTIC_NOT_CLAIM_BEARING` for Helm's abilities. They are the acceptance **reference**
for checking Codex's repair.

## 1. Unchanged Helm 2.0 (source `20208c92`): the prediction HOLDS on all 9 models

| Model | Verdict | delta0 | M1z | M2z | max M3z | max K |
|---|---|---|---|---|---|---|
| fresh, initial.pt, final.pt x seeds 20260917 / 20260918 / 20260919 (9 models) | `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT`, all 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

**What it means.** Changing the focus world's graph, or its domain, moves **no** other candidate's score, on any of
the 24 distinct foci, in any model: untrained, saved-initial or trained. This measures, on real weights, the
mechanism Codex's judge A7 identified: the analogy scorer never compares the focus world with the candidates.

**The laptop readings agree.** The 5 models also read on the laptop's RTX 4070 (attempt 4) give the same verdicts.

## 2. Probe self-test: all 3 expectations MET, so the probe is fit to check the repair

| Variant, patched in memory; source file unchanged (hash equal before and after) | Expected | Read | Key numbers |
|---|---|---|---|
| `POSITIVE_COMPARISON`: a real focus-vs-candidate comparison of graph and domain | `PRESENT_GRAPH_AND_DOMAIN` | **`PRESENT_GRAPH_AND_DOMAIN`** | K>0 on 24/24; M3z above floor 24/24; median RC 4.881481316230698; bystander ok 24/24; RC_dom ok 24/24 |
| `NEGATIVE_UNIFORM`: the same focus-dependent shift for every candidate | `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` | **`FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT`** | max M3z 8.593126210598712e-13; K = 0 |
| `NEGATIVE_COUPLED`: a pool over all worlds | not PRESENT | **`COUPLED_NOT_COMPARISON`** | K>0 on 24/24, but bystander ok on 0/24; 39 top-1 answers changed, and it was still refused |

**What it means.** The probe detects a real comparison. It refuses a uniform shift. It refuses a global coupling
even when that coupling changes answers.

## 3. Preservation reference (the switch-OFF reference), on the T4

- **Complete:** all 9 models, every one at 174,303 parameters.
- **Per-model digests:** `RESULTS_READING.json` -> `preservation_T4`.
- **Full files:** `../aws_probe_job/results/preservation_reference_20208c92_T4_seed*.json`.

**The digests depend on the GPU type (MEASURED).**

| Compared | Result |
|---|---|
| T4 vs RTX 4070, seed 20260919 (3 models) | 0 of 3 bit-identical |
| T4 vs RTX 4070, the 4 printed digests for seeds 20260917 and 20260918 | 0 of 4 bit-identical |

Float32 kernels differ in their last bits between GPU models.

**What follows, a tightening of acceptance item 1 before any repair exists.** The switch-OFF check must run on a
T4, and **in the same job** it must re-fingerprint unchanged `20208c92`, as a same-machine control.
- **Pass:** switch-OFF equals that same-job control, bit for bit, on all 9 models, and the control equals this
  reference.
- **If only the control differs from this reference:** the result is `REFERENCE_NOT_REPRODUCIBLE_ON_T4`. That is a
  finding about the reference, not a pass.

**Still open.** T4 run-to-run reproducibility across separate machines has not been measured yet. The same-job
control above measures it.
