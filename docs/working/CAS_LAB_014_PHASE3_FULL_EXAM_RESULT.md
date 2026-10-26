# CAS-LAB-014 — Phase 3 valve acceptance on the full 1,517-row exam: PASS (2026-10-25)

Status: **preregistered and executed on AWS. PASS on both conditions.** Preregistration:
`CAS_LAB_014_PHASE3_FULL_EXAM_PREREG.md` (frozen before the run). This closes the gap recorded in `CAS_LAB_013`,
which covered only the first 300 exam rows.

## 1. Result

| Condition | Rows | Fixture-rule violations | Clamped at G-ABSENT | Admitted | Violations admitted | Compliant items refused | Receipts recomputed | Unique full receipts | Oracle/controller mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A4-s1 step-1,000 generations | 1,517 | **391** | **391** | 1,126 | **0** | **0** | **1,517** | **1,517** | **0** |
| A4-s1 final (6,000) generations | 1,517 | **261** | **261** | 1,256 | **0** | **0** | **1,517** | **1,517** | **0** |

Every preregistered condition holds for both populations: no flagged reply admitted, no unflagged reply refused,
every row's full receipt recomputed and distinct, and the controller agreed with the independent fixture oracle on
every row.

## 2. What it adds to CAS-LAB_013

CAS-LAB_013 tested 300 rows (106 violations, 194 admitted). This run tests all 1,517 and adds a second reply
population. The late checkpoint writes better replies and produces fewer lexical violations (261 vs 391), and the valve
holds on both. The earlier 300-row slice was not unrepresentative in kind, only in size.

## 3. What it licenses, and does not

Licensed, in the preregistered words: *on this fixed 1,517-row exam and these two reply populations, the valve admitted
no reply that the lexical fixture oracle flags and refused no reply it does not flag, with a recomputable receipt per
row.*

Not licensed: general zero-hallucination, semantic correctness, factual truth beyond the listed lexical rules, live
product behaviour, or any claim about model change. The oracle is a separate implementation of the same lexical rules,
not a human or semantic judge.

## 4. Host, cost and one failed attempt

- Passing run: instance `i-0028607db7f9e3185`, `t3.small`, us-west-2, 96.5 s, estimated **US$0.00056**. Termination
  requested by the runner; volume set to delete on termination.
- Evidence: `s3://cas-harness-runpod-92754088/bridge-control-20260822/p3full-20261025-221315/`.
- First attempt `i-015b9665cad8a28d9` computed the same numbers but uploaded no result files: its generated `run.sh`
  had Windows CRLF line endings, so `cd` failed and the `aws s3 cp` could not find the outputs. The fix was to write
  the script with LF and absolute paths. Recorded because the failure was mine, not the valve's.

## 5. Reproduce

```
python phase3_full_exam.py --generation gen_A4-s1_step_01000.jsonl --exam mouth_exam.jsonl
python phase3_full_exam.py --generation gen_A4-s1_final.jsonl --exam mouth_exam.jsonl
```

Local CPU reproduces the same counts; the AWS run is the recorded one.

## 6. Claim status

| Statement | Status |
|---|---|
| Valve admits no fixture-flagged reply across all 1,517 rows, both populations | `REAL` (AWS) |
| Valve refuses no fixture-compliant reply across all 1,517 rows | `REAL` (AWS) |
| Every row carries a recomputed unique full receipt | `REAL` (AWS) |
| General zero-hallucination | `NOT LICENSED` |
| This closes the v0.4 "0-leak RPM interlock" gap from 300 to 1,517 rows | `REAL` |
