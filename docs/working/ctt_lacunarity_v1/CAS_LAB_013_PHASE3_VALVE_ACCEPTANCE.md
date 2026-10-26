# CAS-LAB-013 — Phase 3 G-ABSENT Fixture Acceptance (Corrected)

**Current result:** 🟨 **PARTIAL — REAL / VALIDATED**, limited to the explicit lexical fixture rules below.

**General zero-hallucination guarantee:** ⬜ **NULL / NOT RUN — NOT LICENSED**.

## Correction to the first report

The first report is preserved at [CAS_LAB_013_PHASE3_VALVE_ACCEPTANCE_INITIAL_20261024.md](CAS_LAB_013_PHASE3_VALVE_ACCEPTANCE_INITIAL_20261024.md). Its unconditional “zero-hallucination” verdict is withdrawn: 🟥 **FAILED / WITHDRAWN — WITHDRAWN**.

The first test suite counted a refusal as an error but never incremented its `gated_errors` variable. The AWS driver then wrote `baseline_gated_errors: 0` and `hallucination_suppression_pct: 100.0` as fixed values. The controller did not check `reading.slot`, and the saved result contained only 10 refusal receipts and 10 admitted receipts. The first test checked that receipt strings were 16 characters long; it did not recompute the hashes. Its reported 78 was therefore a count of the old controller's checks, not a complete factual-error audit.

The first report's `$0.0388` was a runner estimate, not a confirmed AWS bill. The runner's calculation was `$1.10/hour × 126.9 seconds = $0.038775` before its display rounding. The actual billed cost for that run is unavailable from the EC2 receipt.

## Corrected AWS check

The revised controller checks whether the expected entity, value, and slot terms are grounded in the input and present in the proposal. It also checks replacement values, repeated words, and the required question or answer shape. A small listed set of word forms handles inflections such as `went`/`go` and `moved`/`move`.

The test oracle is a separate implementation of those lexical rules. It is not a human rating, semantic judge, or independent source of factual truth. The test code and rules were fixed in the uploaded AWS input package before this corrective run, but this was not a separately preregistered experiment.

The source exam file has **1,517** rows. This run evaluated the **first 300 rows in file order**, matched to the 300-row baseline and steered generation files. It did not evaluate the remaining 1,217 exam rows.

| Condition | Items | Fixture-rule violations | Admitted | G-ABSENT refusals | Violations admitted | Compliant items refused | Full SHA-256 receipts checked |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 300 | 106 | 194 | 106 | 0 | 0 | 300 / 300 |
| Steered dose 0.20 | 300 | 111 | 189 | 111 | 0 | 0 | 300 / 300 |

The AWS suite ran **3 tests; 3 passed**. The test oracle and valve decisions agreed on every row. Each condition had **300 distinct full SHA-256 digests**. The 16-character `receipt_hash` is the first 16 hexadecimal characters of the full digest. The full receipt binds the item, input, structured reading, proposal, decision, refusal or response, and failure reason. The hashes are unsigned integrity checks; they do not prove who ran the code.

The refusal text is a clean refusal under the tested contract. No proposal flagged by the fixture oracle was admitted, and no fixture-compliant proposal was refused. These counts apply only to the stated text rules and these saved outputs.

## Claim status

- 🟨 **PARTIAL — REAL / VALIDATED:** The revised valve blocked all 106 baseline and all 111 steered fixture-rule violations in the selected 300-row slice, and the suite recomputed every saved receipt.
- 🔧 **METHOD / PROCESS WIN:** The AWS package now records source hashes, saves the full item ledgers, checks receipt digests, and terminates the cloud instance and root disk.
- ⬜ **NULL / NOT RUN — NOT LICENSED:** General factual accuracy, semantic slot equivalence, performance on the other 1,217 exam rows, live product behavior, and user-facing reply quality were not tested.
- ⬜ **NULL / NOT RUN — NOT LICENSED:** This does not show that lacunarity repairs CTT, improves training, or improves generated replies. No model was trained or changed.
- 🟥 **FAILED / WITHDRAWN — WITHDRAWN:** The first report's general “zero-hallucination” claim and its 78-item completeness claim.

## AWS run and exact artifacts

- Run ID: `phase3-valve-v2-20261025-022234-93c2551d`
- Instance: `i-03b08702d49e62047`, `t3.small`, `us-west-2`; 2 vCPU, 2 GiB memory, 60 GiB gp3 root volume.
- EC2 launch: `2026-10-25T02:22:37Z`; termination initiated: `2026-10-25T02:24:14Z` (97 seconds). AWS later reported `terminated`; the attached-volume query returned no volumes.
- Limits: 600 seconds maximum; `$0.50` EC2 compute and temporary root-volume budget. The current AWS On-Demand rate was `$0.0208000000/hour`; the exact compute estimate at the 600-second limit is `13/3750 USD`. The actual billed amount is unavailable. Retained S3 audit storage is outside this cap.
- Cleanup: termination confirmed; root disk marked for deletion and absent after termination. S3 input and outputs remain for audit.
- S3 run folder: `s3://cas-harness-runpod-92754088/bridge-control-20260822/phase3-valve-v2-20261025-022234-93c2551d/`
- Input archive: 88,697 bytes; SHA-256 `ddb3ff4b3b93889a6ae9be55a09090094096fcdf804e582b99c87ce57f603f64`.
- Results JSON: 819,412 bytes; SHA-256 `159c68381cdfc0d670677373884f83900c37eab904ecbe464b836f4d35b44f82`.
- Test log: 808 bytes; SHA-256 `6fc2212070ddfe4cdfb06fae30ac3264f8c8b4c9ab907a69135ed7eb71a84c1e`.
- Input manifest SHA-256: `3c2386c3b3b5918c4fc0cdcfbb503e6fa3f240bfdecdf1758024b40768c22eb8`.
- Controller SHA-256: `c2f94aeab9be3c5997482977550acf9ec21a792dc03e60f79e242b795441f1c4`.
- Test source SHA-256: `e2db48aae143c640cebbe07f6a390499540cff852d77a6a5e5d2f118059545c7`.
- Baseline generation SHA-256: `6225eb3d6ddcd46c455a36f247c479155a65d972e34f7d1923088b6ef5700cdc`.
- Steered generation SHA-256: `05f937b5be4c248c652ea1569d79a4c892294b366d8fbecd1db1479cf4458891`.
- Exam source SHA-256: `bb8ad7a4c08b406d787441b609d3da50ed3fc7755a6397c713997e991535aa42`.

Saved files: [AWS result ledger](results/phase3_valve_acceptance_results_v2.json), [AWS test log](results/phase3_valve_test_log_v2.txt), [AWS driver log](results/phase3_valve_driver_log_v2.txt), [cloud receipt](results/phase3_valve_cloud_receipt_v2.json), and [input manifest](results/phase3_valve_input_manifest_v2.json).

## Next step

Freeze the v5 scenario, its independent scoring rules, and its AWS time and cost limits before running another experiment. Keep the broad repair question open: this valve refuses some unsupported proposals; it does not repair the model.
