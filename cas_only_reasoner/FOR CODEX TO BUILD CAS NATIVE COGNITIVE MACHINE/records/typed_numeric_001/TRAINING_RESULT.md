# Completed typed-course GPU training

The full course completed successfully. Exact-answer accuracy on the exposed
564-question course increased from **18/564 (3.19%) to 196/564 (34.75%)**.
There were **195 gains and 17 losses**, for a net gain of 178 correct answers.
This demonstrates improved fit to this exposed course in one run. It does not
establish better learning than a matched control, untouched transfer, delayed
retention, or completion of the full CNCM machine.

## Executed work

- 160 main optimizer/backward updates and all 1,152 teaching presentations.
- Two additional, independently restored last-update replays: 162 actual updates
  in total. Restored historical counters were not counted again.
- 60,202 registered core forward calls and 2,328 prediction calls across the
  initial evaluation, teaching, final evaluation, restores and replays.
- Worker elapsed time: 1,451.214547069 seconds (24 minutes 11 seconds), excluding
  cloud provisioning, installation, collection and resource cleanup.
- Final learned checkpoint delivered. Initial/final checkpoint reconstruction
  matched recorded model, optimizer, random-state and encoder identities, with
  eight exact representative predictions per restore. Both last-update replays
  matched the original pre-update prediction bytes and final learned state.
  These checks ran in the same process on the same GPU worker.
- All 344 required worker artifacts passed the local byte/hash and recorded-join
  review. The local review did not run tensors, decode model checkpoints or rerun
  the semantic checker.

## Scores by question kind

These are exact complete-answer scores, not individual slot scores.

| Kind | Before | After | Newly correct | Became wrong |
| --- | ---: | ---: | ---: | ---: |
| analogy | 12/70 | 10/70 | 10 | 12 |
| context | 0/70 | 0/70 | 0 | 0 |
| correspondence | 0/88 | 82/88 | 82 | 0 |
| definition | 0/70 | 0/70 | 0 | 0 |
| edge_account | 0/70 | 0/70 | 0 | 0 |
| parts | 2/53 | 19/53 | 18 | 1 |
| reach | 2/107 | 80/107 | 80 | 2 |
| role_set | 2/36 | 5/36 | 5 | 2 |
| **Total** | **18/564** | **196/564** | **195** | **17** |

Only one initially correct answer remained correct. The aggregate gain therefore
does not erase the losses, the analogy decline, or the three kinds still scoring
zero. All 564 inputs were exposed; this is not a held-out test. Ordinary
dependency-graph ordering currently equals component-first ordering, so those
names alone do not define distinct experimental arms.

## Exact execution and evidence

- Job: `cas-meta2-typedcourse-20260917024221-2a221243`.
- Executed source: `2a221243bf2f82f82bdce19514fe04bcb6b26bb0`.
- Instance: `i-0016c39d90143e316`; GPU instance type: `g7.2xlarge`.
- Worker status: `COMPLETE_EXPOSED_TYPED_COURSE_AND_SAME_PROCESS_RELOAD_OBSERVED`.
- Delivery status: `TYPED_COURSE_DELIVERED`.
- Course: 564 registered packets, 64 source worlds, eight question kinds;
  source curriculum seed 101 and model/encoder seed 20260916.
- Numerical core: 16,384 trainable weights, with frozen projection and readout.
- Peak allocated CUDA memory: 159,627,776 bytes; peak reserved: 182,452,224 bytes.
- Full machine-readable result: `completed_review_002/stdout.json`.
- Review receipt: `completed_review_002/receipt.json`, SHA-256
  `d873885bb28c8d39df9f76f38e7690a7ad0f69100b31e90da1aeba702e6701e6`.
- Original worker artifacts: `receipt_002/collected/results/artifacts/`.
- Independent audit: `independent_review_002/receipt.json`, SHA-256
  `216e2d808494a9d1c4516ac9a2b8ba69c1f4e38cf7637c3a7da0f9d3dd8b682b`.
  It additionally verified all 504 collected files, 347 required objects,
  222 declared inputs, imported-source consistency and both complete replay
  update receipts.

The first attempt remains preserved separately: it timed out after 61 completed
updates and delivered no final learned checkpoint or final score. Its failed
status is not replaced by this corrected run. The corrected source adds bounded
slot-plan caching, progress files, partial checkpoints and a longer bounded child
time limit. All 564 initial answers and score maps match across the attempts;
their full source-bound records are not identical.

The reservation contains inherited descriptive fields from an older curriculum;
the actual workload is specified by the source-bound authority, config and
artifact records. This limitation is preserved in
`INTEGRATION_EXECUTION_NOTES.md`. Reserved campaign money is not an invoice.

## Next learning gate

Keep this run fixed as the completed engineering baseline. Diagnose the three
zero-score kinds and the lost answers from the saved results, then freeze a
genuinely distinct matched teaching contrast with equal information and budgets.
Test learning speed, untouched-family transfer and retention across paired model
seeds. The earlier negative three-seed recurrence result remains unchanged.

The first output-pattern diagnosis is now saved in
`result_diagnosis_002/DIAGNOSIS.md`. All 70 final definition function references
point outside the emitted whole's world; 51 of 57 nonempty context answers mix
participant and setting worlds. Final edge-account answers contain 65 self-edges
across 41 cases. Analogy choices concentrate on two worlds in 56/70 answers.
These are observed inconsistencies and concentrations, not an established causal
explanation; no new checker or model execution was used.

Resource cleanup and publication evidence are recorded in `STATUS.md` and the
final launcher lifecycle record; the worker's training result alone does not
prove resource termination.
