# GRAPH6_CONFIRMATION_001 — preregistration (frozen candidate, three learners, fresh panel)

Status: **PREPARED — NOT LAUNCHED.** No reservation, no owner authorization
record, no AWS call exists for this job. This document is the executable design
the paid job would follow, written before execution.

Supersedes the earlier `CONFIRMATION_RUN_001.md` design (three dataset seeds on
newly generated panels): the owner's directive replaces it with three
independently initialized LEARNERS on one shared dataset, one shared encoder and
one shared fresh panel, so the trained-vs-untrained comparison is paired case by
case. The earlier package and request were never registered, reserved or
launched.

Owner directive this answers: *"Prepare `GRAPH6_CONFIRMATION_001`. Preserve
competence run 005 as the successful baseline. … Prepare one combined job
containing three independently initialized candidate learners … Prepare a fresh
evaluation panel of 30 graph families with one question per operation, totaling
90 cases … Preregister the new transfer criterion and uncertainty calculation
before execution … Preparation only until owner approval; no automatic
reservation or launch."*

## 1. Preserved baseline (competence run 005)

| Element | Frozen value | Evidence |
| --- | --- | --- |
| Encoder / tokenizer | relationship-preserving encoder, `d_model=64`, encoder seed `20260909` | `real_framework.build_encoder` |
| Tokenizer fitting set | the 30 train+practice whole-part records ONLY — the fresh panel never enters it | worker source + test |
| Module | registered `cas.cjt.operation.^6.decompose/0.2` candidate copy, `operation:^6` plasticity only | `trainer.scope_parameters` |
| Teaching records | the same 30 train+practice records, same order | `trainer.training_records(20260909)` |
| Optimizer allowance | `learning_rate=0.003`, 64 updates per candidate, 600 s per candidate | `trainer.TrainingBudget` |
| Fit comparison | `mean(after_loss) < mean(before_loss) − 0.02` (unchanged) | `confirmation.FIT_MARGIN` |
| Run-005 numbers kept as history | loss `1.09836→0.56441`, familiar 24/30, sealed 7/12 on the examined panel | `ATTEMPT_COMPETENCE_005_RESULT.md` |

### The preserved checkpoint itself does NOT exist — stated plainly

Run 005 persisted only the parameter **digest**
`cb008721b92144b4e0ef52e86c2c449415935110747aca18ff23229c05240e50`. The
weights were never written to evidence (the receipt directory holds JSON and the
source zip only), and `RegisteredOperationBank.__init__` builds
`_DecomposeTransform` from `nn.Linear` layers with **no seed** (wheel
`cas_cjt/neural.py` lines 174–188), so those exact weights are not reproducible.
The requested table row *"Preserved successful checkpoint — fresh evaluation
only"* therefore cannot be filled from the original weights.

Two honest options are prepared (decision item 1):

* **default `baseline_mode="none"`** — the row is reported `UNAVAILABLE` with the
  digest and the reason above; the trained-vs-untrained comparison on the new
  panel is unaffected because every candidate is measured before AND after
  training;
* **`baseline_mode="reproduce"`** — a fourth declared candidate runs the same
  frozen configuration with a recorded initialization seed and its trained
  digest is compared with `cb008721…`; it is reported
  `BASELINE_REPRODUCED` only on an exact digest match, otherwise
  `BASELINE_NOT_REPRODUCED`. Cost: +64 updates, +600 s.

## 2. Three independently initialized learners (not three rounds)

| Item | Value |
| --- | --- |
| Learner seeds (declared before execution) | `20260913`, `20260914`, `20260915` |
| Encoder seed | `20260909` (fixed; one shared projection) |
| What the seed varies | module + optimizer initialization only (`torch.manual_seed(seed)` immediately before the module bank is built) |
| Optimizer state | separate per candidate |
| Updates | 64 per candidate → **192 total** |
| Wall ceiling | 600 s per candidate → 1,800 s total |
| Instance ceiling | 5,400 s (1.5 h) |
| Reservation | one new reservation of **`$6.00`** = 1.5 h × `$2.52` + `$1.48` ancillary, rounded up |

Controls recorded by the run: `encoder_identity_shared` must be true (one
projection for all candidates), `initial_checkpoints_distinct` must be true
(three different starting weights), containment must show changes only in the
`operation:^6` group, and **every** scheduled candidate is reported.

PyTorch's own caveat applies and is recorded: a seed alone does not guarantee
identical behavior across releases or platforms
(<https://docs.pytorch.org/docs/stable/notes/randomness.html>). The job therefore
records the software identity (`torch 2.11.0+cu128`, CUDA 12.8, same AMI and
instance type) alongside the seeds.

## 3. Fresh evaluation panel — 30 families, 90 cases

Deterministic, non-neural evidence: `tools/graph6_fresh_panel_check.py` →
`GRAPH6_FRESH_PANEL_001.json` (sha256 `c7876508fd3853556569134191a126f19113d02aac6f59c51b9556b7c46cc15a`,
`neural_work: false`, `gpu_used: false`).

| Item | Value |
| --- | --- |
| Panel seed | `20260920` (declared before execution) |
| Families | 30 (one question per operation each) |
| Cases | 90 — `LIST_PARTS` 30, `FIND_SHARED_PART` 30, `REACHED_VIA` 30 |
| Reach coverage | 10 `direct` / 10 `via` / 10 `absent` |
| Pattern coverage | 30 distinct family patterns; 56 distinct case patterns out of the 90 |
| Panel content digest | `d1076de3ae310562e97552c4f854fab10661bed78f9d4108187ea2f549ae8209` |
| Generator | the frozen lesson generator (`lessons._whole_part_exercises`), same vocabulary and difficulty |
| Excluded | the 42 whole-part records of the previously examined dataset (seed `20260909`, all splits, which contains the examined attempt-010 panel) |
| Exclusion is label-invariant | exact record ids **and** structural signatures: 31 distinct used signatures were excluded, so a trivially renamed duplicate of a used case is rejected too |
| Overlap with used cases | **0 ids, 0 signatures** |
| Panel isolation | no training, no checkpoint selection, no tokenizer fitting, no answer exposure before the registered predictions are sealed |

Candidate pool and rejections are recorded in the evidence file (409 accepted
candidates; 169 families skipped for a missing operation, 2,422 rejected because
a whole family repeated a used case up to renaming).

## 4. Pre-registered decision rule (declared before execution)

Per candidate, on the SAME 90-case panel, predictions recorded before answers:

* **Fit (unchanged from run 005):** `mean(after_loss) < mean(before_loss) − 0.02`.
* **Fresh transfer — candidate passes iff all three hold:**
  * **T1 paired margin:** `after_accuracy − before_accuracy ≥ +0.10` (9 of 90 cases) **and** the family-clustered 95 % interval's lower bound `> 0`;
  * **T2 absolute level:** `after_accuracy ≥ 0.50` (45 of 90), well above the 1/3 chance level of the three-slot interface;
  * **T3 per operation:** no operation regresses, and at least two operations gain `≥ +0.10`.
* **Uncertainty:** family-clustered percentile bootstrap, 10,000 resamples, seed
  `20260921`, 30 clusters of 3 cases (the 90 cases are not independent — three
  questions share a family) **plus** an exact McNemar test on the discordant case
  pairs.
* **Verdict:** `FRESH_TRANSFER_CONFIRMED` iff **≥ 2 of 3** candidates pass;
  otherwise `FRESH_TRANSFER_NOT_CONFIRMED`. Every candidate's numbers are
  reported either way.

The old **6/12** pilot threshold is **not** reused: it belonged to that specific
12-case panel.

## 5. What the job reports

The owner's compact table, per candidate: practice accuracy before → after;
fresh accuracy before → after; per-operation before/after counts; paired
improvement with interval and McNemar p; fit margin; containment; checkpoint
identities; execution and cleanup results. Plus the budget actually consumed
(updates, wall seconds) and the three controls above.

## 6. What this experiment does NOT claim

No composition claim, no specialist claim, no two-framing comparison (still
postponed), no claim about the frozen sealed splits of the original panel, and
no reliability claim beyond "three repetitions on one pre-registered panel".
A `FRESH_TRANSFER_CONFIRMED` verdict would mean: the same frozen candidate, with
three independently initialized learners, improved on 90 genuinely new questions
by the pre-registered margin in at least two of three cases. Nothing more.

## 7. After confirmation (prepared later, NOT part of this job)

1. **Curriculum for the weakest operation** — teach
   "directly contained / reached through another part / not connected" as a
   focused lesson set (changed names, reordered records, different surrounding
   nodes, different questions), with practice on the other two operations kept
   so maintenance is measured. Separate curriculum experiment; not an
   unrecorded change to the replication.
2. **One learned child call inside CASformer** — parent question → trained ^6
   child → checked result → parent resumes using that result, recording whether
   the final answer is correct, whether the child's actual result was consumed,
   and whether the caller's position and remaining budget were preserved.

## 8. Authority

One new owner-signed authorization record + one new `$6.00` reservation
(ledger revision 45 → 46: `$236.00` reserved / `$164.00` unreserved against the
`$400.00` cap). The paid path requires a hash-bound launch request and an owner
authority naming the job, source sha, archive sha256, manifest sha256, the frozen
budget, the learner seeds, the panel seed and the baseline mode. Plan output
stays inert. **No launch happens until the owner says GO.**
