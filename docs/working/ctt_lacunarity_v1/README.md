# CAS-LAC-001 — Lacunarity, Recipe/RPM Labelling and Bounded Cell Steering (HELM/CTT)

**Programme name:** `CAS-LAC-001 — Lacunarity and Cell Steering Programme`
**Repository:** `github.com/LittleHenderson/noetic-compass`
**Branch:** `helm/creativity-rpa-valve-v1`
**Folder:** `docs/working/ctt_lacunarity_v1/`
**Status:** closed. One durable positive (a safe steering dose), one durable negative (no structural label beats plain
distance), and a set of preregistered failures kept as they are.

---

## 1. What this programme asked

Can a structural measurement — lacunarity, a recipe bottleneck, a Noetic cell, an RPM prerequisite — tell us where a
model is weak, how to repair it, and whether the repair worked?

It ran in two parts:

1. **Measurement** (`LAC-*`): can lacunarity detect a weak cell, and does adding data to that cell fix it?
2. **Control** (`CAS_LAB-*`): if the cell cannot be fixed by data, can it be steered at inference time, safely?

## 2. The short answer

- **Detection: partly.** Low-exposure Noetic cells carry higher held-out error on two independent data sets, 3 of 3
  seeds. But the lacunarity number adds nothing beyond the exposure count itself.
- **Repair by data: no.** Targeted replay made the targeted cells worse and cost reply quality (`LAC-07`).
- **Repair by steering: works internally, fails as a product.** An answer-free direction recovers 39.3%–62.4% of the
  gradient gain, and dose 0.20 is safe on all three seeds — but its efficiency falls to 17.5% on one seed, and no
  structural label reliably beats plain memory distance.

## 3. Document index

| File | What it is |
|---|---|
| `LAC-00_EVIDENCE_LEDGER.md` | verified facts; the corrections that reversed a published verdict |
| `LAC-01_EXISTING_MEASUREMENT_INVENTORY.md` | what lacunarity code already existed |
| `LAC-02_MEASUREMENT_SPECIFICATIONS.md` | Noetic, recipe and RPM definitions with baselines |
| `LAC-03_RESEARCH_SCORECARD.md` / `LAC-03A_MATHEMATICAL_VALIDATION.md` | status table; 30 hand-computed checks |
| `LAC-04_RANKED_COSTED_PLAN.md` | ranked experiment plan |
| `LAC-05_INDIVIDUAL_MEASURE_EVALUATION.md` | two-source Noetic evaluation |
| `LAC-07_TARGETED_INTERVENTION_PREREG_20261024.md` / `LAC-07_TARGETED_INTERVENTION_RESULT_20261024.md` | the failed replay trial |
| `LAC-10_PROGRAM_SYNTHESIS.md` | the measurement programme's conclusion |
| `CAS_HARNESS_STEERING_INVENTORY_20261024.md` | the scattered Harness steering work, consolidated |
| `CAS_LAB_001_LABELLING_AND_STEERING_v1.md` | labeller + first steering probe |
| `CAS_LAB_002_PROBE_RESULT.md` | the learned kNN probe |
| `CAS_LAB_003_CONFIRMATION_RESULT.md` | three-seed confirmation |
| `CAS_LAB_004_GUARD_RESULT.md` | the reply-quality rejection at full dose |
| `CAS_LAB_005_DOSE_PREREG_20261024.md` / `CAS_LAB_005_INCIDENT_LOCAL_GPU.md` | dose protocol; the local-GPU process incident |
| `CAS_LAB_006_DOSE_PARTIAL.md` | CPU-only dose curve |
| `CAS_LAB_007_RPM_GUIDED_PREREG.md` / `CAS_LAB_010_SELECTOR_RESULT.md` | the selector test and its 1.2283× failure |
| `CAS_LAB_008_DOSE_RESULT.md` / `CAS_LAB_009_REPLICATION_RESULT.md` | the safe dose and its mixed replication |
| `CAS_LAB_011_OPERATOR_PREREG.md` / `CAS_LAB_012_OPERATOR_RESULT.md` | the operator hypothesis and its 1-of-3 failure |

## 4. Key numbers

| Result | Value |
|---|---|
| Low-exposure Noetic cells vs high, held-out error | neglect 3/3 seeds on two sources; `Λ` adds nothing |
| Targeted replay (data repair) | failed 2 of 3 conditions; composite −0.024067 vs control |
| Answer-free kNN probe vs gradient oracle | 44.8%, 62.4%, 48.6% of the oracle gain |
| Full-dose steering on reply composite | 0.231817 → 0.118910 (−0.112907) |
| Dose 0.20 on reply composite | s1 −0.006223, s2 +0.004797, s3 +0.004032 — **safe 3/3** |
| Dose 0.20 efficiency | 30.6%, 22.7%, **17.5%** of full gain — bar 25% fails on s3 |
| Structural selector | best 1.2283× vs 1.25 bar — fails |
| Operator-only, three seeds | 1.2283, 1.0885, 0.9870 — 1 of 3 at a 1.15 bar — fails |
| Cell-identity gating | 0.4050, 0.1363, 0.1853 of unguided — harmful on every seed |

## 5. What is in this folder

- `code/` — every script used: the labeller, the steering probes, the scorers, the AWS launchers and drivers.
- `data/` — the two held-out Noetic sets, their labels, the RPM sample, and the six 300-row generation files whose
  composites are reported.
- `results/` — the raw AWS result JSONs and the probe/steering outputs.

Not included: model checkpoints (about 38 MB each) and the training payload. They live at
`C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\results\out\<seed>\step_01000.pt`; their SHA-256 values are in the
AWS run manifests referenced by the LAC documents.

## 6. How it was verified

- Every preregistration was committed before its run, and every bar was applied unchanged.
- Splits are by source, not by row, so no paraphrase of a training item appears in a confirmation half.
- Every steering claim is measured against a matched random direction of the same norm.
- Every reported number comes from an AWS instance whose id, region and run time are recorded in the result document;
  the earlier local runs are marked diagnostic and not claim-bearing.
- Failed and superseded results were patched with dated correction blocks, never deleted.

## 7. Cost

About **2.40 USD** for the historical training runs, plus about **1.18 USD** for the AWS evaluation runs in this
programme. The approved cap for the evaluation was 15.00 USD.

## 8. Reproduction

```
python code/cas_label.py --in data/notation_new100.jsonl --out labels.jsonl
python code/cell_probe.py --checkpoint <step_01000.pt>
python code/probe_confirm.py --seeds A4-s1,A4-s2,A4-s3
python code/gen_steer.py --seed A4-s1 --dose 0.2 --out-dir guard
python code/rt_score.py --gen guard/gen_A4-s1_steered_d0.2.jsonl --out scored.jsonl
python code/composite.py --scored scored.jsonl
```

GPU required for anything that loads the model. The AWS launchers show the exact instance, AMI, subnet and payload
path used for the reported runs.
