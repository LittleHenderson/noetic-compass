# PREFLIGHT_REVIEW — what an adversarial review found before any money was spent, and what was changed

**2026-09-18. $0.00. No AWS call, no torch, no GPU.** Four independent reviewers (launch mechanics, worker
numerics path, scientific validity, time and money), each serious finding re-checked by a separate skeptic
told to refute it. Full findings and verdicts: `preflight_review_findings.txt`.

## Run-killers — both confirmed, both fixed

| finding | what would have happened | fix |
|---|---|---|
| **Growing log files under `results/`** (found independently by three reviewers; one reproduced it against a fake create-only store) | The live evidence publisher uploads each new file name once, create-only. A pass log created empty and then appended to would change after its first upload; the final upload fails with `EVIDENCE_DIGEST_CONFLICT`, `result.json` is never uploaded, the job is recorded failed after ~2 hours and $15, and the study stops. | Pass and interference logs now grow in the staging directory outside `results/` and are moved in whole. Every other file the worker writes is written as `<name>.partial` (which the publisher skips) and renamed. The dry run now runs a create-only publisher simulation that rescans `results/` ten times a second and fails on any file that changes after being seen. |
| **One network error ends a healthy job** | The inherited wait loop has no SDK retries; a Wi-Fi drop or sleep on the operator's machine raises out of `wait()`, and the lifecycle terminates a running instance. | `TypedPracticeProvider.wait` records transient provider errors (connection, timeout, throttling, 5xx) and keeps polling to the deadline; any other error still ends the wait. Test: `test_wait_survives_a_transient_network_error_and_not_a_real_one`. |

## Misleading-result risks — all confirmed, all fixed by redesign

| finding | fix |
|---|---|
| Rule twins: 16 held records had a trained twin (same world, same question, other rule), 12 with the same answer | Held back by **world**: every rule and record of a held world is held. |
| 26 of 51 held questions sat with their correct answers as worked supports in 132 trained records | The 10 records carrying a worked support about a held world are **excluded** from training. |
| A same-world answer prior got 14/28 held `reach` records right; no mechanism-free baseline | No trained answer comes from a held world. The remaining world-agnostic shortcut (`reach` → DIRECT, most common `role_set`) answers 8 of 50 held questions; the gate uses the other 42. |
| Record-level pooled test: one question flipping in three near-copy seeds could pass | Unit is the **question**; each seed is tested separately and all three must pass; improvements must span ≥ 2 kinds. Test: `test_gate_counts_questions_and_one_flip_cannot_pass`. |
| Labels named more than they measured (pass 1 → 10 called "memorises only") | Primary gate is pass 0 → 10 on held worlds; pass 1 → 10 and trained-question tests are separate flags. |
| Retention panel mixed never-taught with taught questions | Retention reported by side (held-world / trained-world). |
| Gate reader crashed instead of printing VOID on missing files; duplicate seeds unchecked | Every integrity block maps errors to its gate; `I0` requires exactly the three seeds. |
| `execute_study.py` relied on `assert` (removed under `python -O`) to stop after a failed job | Explicit `SystemExit` stops. |

## Minor, recorded not changed

- The inherited lifecycle's receipts show its generic `$7.00 / 7,200 s` scope in `reservation_scope` and
  `permit.resource_plan`; the ledger entry carries the real `$15.00 / 14,400 s` (protocol §3).
- The shared collector's truncation guard checks the wrong key (`NextToken`); expected bucket objects are
  ~490, below the 1,000-key listing page, so it is not reached.

## Second review of the world-level redesign — three more leak channels, all confirmed, all fixed

Two fresh reviewers (validity; run mechanics) plus a skeptic per serious finding. Full findings:
`preflight_rereview_findings.txt`. Run mechanics: only minor findings. Validity:

| finding | fix |
|---|---|
| Held world `3b0abc92` has exactly the shape of TRAINED world `68987078`; copying the twin's answers by node position answers 9 of the 42 gate questions | Only worlds with **no shape twin anywhere in the 64-world bank** are eligible (12 of 24). |
| 17 trained analogy records have correct answers naming held worlds (a reverse lookup answers every held analogy question) | A world's exposure now includes records whose **correct answers** name it; all are excluded (6 records mention a held world only there). |
| Worked supports reach held worlds through their **arguments and worked answers**, not just their focus | Exposure is now **any mention anywhere** in a record; all such records are excluded. 79 excluded in total, 358 trained. |
| The shortcut test was literal text; in the learner's symbols a constant analogy answer and positional constants were missed | The shortcut is computed in the learner's own output symbols (global `W`, per-world `N`). 5 of 50 held questions; 45 eligible. |
| Questions about one world move together | Gains must now span **≥ 2 held worlds** as well as ≥ 2 kinds; per-world tables reported. |
| Minor: staging logs lost on a failed run; transient-error list too broad and too narrow; gate reader crashed on malformed study JSON; dry run could not prove every write was whole | Staging salvaged as `failed_*` artifacts; transient errors classified by class name (network only) plus clock-skew codes; malformed studies read as `VOID`; the dry run now records every write-mode open under `results/` and fails on any not named `*.partial`. |

The split is frozen as constants in the contract, so the worker never reads a correct answer before
training; `holdout_audit.py` re-derives it from the rules with the answer checker, and a test asserts equality.

## What the review found fine

Time estimate ~1.5 h worker per job at the measured 3.43 s per update, inside a 12,300 s deadline; the
reservation arithmetic ($11.56 ≤ $15.00); the learner ceilings and total forward work (~225,000 of
600,000); the same-random-start check (the starting network code is unchanged since the matched study's
source commit `e6bdf305`); the exact binomial arithmetic; restore through the practice subclass.
