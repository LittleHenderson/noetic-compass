# Stage 2 checker: builder evidence

Codex added a separately named six-node checker and matching correspondence
syntax. The original five modules remain byte-identical. The original
complete-assignment decoder functions remain identical under syntax-tree
comparison. No model was run or trained for this change.

Source implementation: 45828c45. First tested source snapshot:
b87fcc150e5818a7b1a4efd11f56b764fa15c219. Branch:
codex/helm-stage2-checker-20260923. Prior checkpoint d206b42a is preserved.

## Current evidence

- Unit/regression job on AWS: 110 passed in 17.01 seconds; 40 test functions.
  New: 18 functions / 68 cases. Existing: 22 functions / 42 cases.
- Performance: 1,000 generated five-node analogy questions, three worlds per
  bank, 23.554114344 seconds. Maximum 240 actual permutations per question;
  240,000 in total. This is AWS timing, not laptop timing. The theoretical
  six-node/64-world ceiling is 46,080 permutations per question.
- Complete historical comparison: PASS. All 564 records have identical accepted
  answers, witnesses and coverage; all 564 slot plans have identical canonical
  bytes. All 6,768 historical prediction decisions agree. There are zero
  mismatches. This took 2,727.837589011 seconds on AWS.
- The prediction comparison made 1,290 fresh exact-input checks with each checker
  and reused 5,478 identical inputs. Target derivation covered 244 unique inputs
  across the 564 records. These counts are not additional pytest test cases.
- The frozen profile digest matches both original historical anchors. All 12
  transferred prediction files match those anchors' original raw hashes.
- No selected test failed, errored or skipped. Two files were loaded; 1,074 other
  tracked test filenames were not loaded. This filename census is not a whole
  repository test collection or claim of full-suite acceptance.
- Claude's independent A1–A6 acceptance: OPEN. Builder checks do not replace it.

## Meaning and limits

The new checker uses exact directed graph bijections and distinct declared
domains. Every valid answer is retained in canonical order. More than 64
accepted correspondence mappings is refused, never truncated. The syntax
compiler still offers every assignment, including wrong ones: 121 candidates
for five nodes and 721 for six nodes, including NO_MATCH.

Original supported slot plans use the original compiler and profile, preserving
their full bytes. Extended correspondence plans have a new profile. Answer
objects and correctness flags must match the original checker on old records;
new target/check digests differ because their semantic profile differs.

The original learner still imports the original slot compiler. This change
does not claim that larger public learned inference is integrated or that any
new question is answered correctly by a trained model. HSET generation remains
Claude's responsibility; enforce the unchanged reader's degree limit there.
The six-node star is a checker-cap refusal fixture, not a proposed learning item.

## Resources and custody

The owner instructed AWS use because the laptop had only a reported 354 MB
free out of 16 GB. The standing instruction is in global Codex/Claude files,
repository/homebase AGENTS.md, and docs/AWS_EXECUTION_PREFERENCE_20260923.md.
No tests, builds, model inference, or training were run locally after that request.
Lightweight editing, inspection, transport and receipt download stayed local.

AWS: i-00787ea718c2631ea, us-west-2, t3.large, two vCPUs, 8 GiB RAM;
one test process, CPU quota one core, worker memory ceiling 4 GiB. Automatic
shutdown after 120 minutes terminates the instance. Unit tests and the benchmark
used standard CPU credits. At 13:27:03 UTC, after CloudWatch showed a nearly zero
credit balance, the operator enabled paid credits for the continuing comparison.
The one-core worker quota, memory/time limits, source and $1 budget stayed fixed.
AWS_CREDIT_INSPECTION.json and AWS_JOB.json preserve that amendment and its rates.
See AWS_JOB.json, AWS_RESOURCE_VERIFICATION.json and WORK_PLAN.md for limits,
actual provider responses, pricing estimate and explicit cleanup status.
Cleanup is verified complete: instance terminated, disposable volume absent,
and temporary S3 bucket absent. Downloaded archive SHA256:
078fdb3612248d45786f5f3e64da4c0c4a73ecb1db27fe2b9f2a38c2e149d965.
AWS_CLEANUP.json includes the provider responses and archive/S3 integrity check.

INPUT_MANIFEST.json binds transferred source and each historical prediction
file to exact bytes. Historical predictions come from the retained q4-live
checkout; that does not make them Q4 predictions. Their actual model identities
are af0970cf (Helm 1.0) and 20208c92 (Helm 2.0 experimental), recorded separately.
The original labels remain Helm 1.0 pass/pass/pass and Helm 2.0 pass/pass/fail.

The compatibility runner streams the 564 original registry records, retaining
only bounded semantic results and exact-input check reuse. It calls both actual
checker implementations; it does not replace correctness with a new scoring rule.
This is a new compatibility run, not a regenerated historical receipt or grader run.

Exact receipts are in run001/builder_tests.xml, run001/builder_tests.txt,
run001/compatibility.json, run001/compatibility.log, run001/performance.json,
run001/performance.log, and run001/run_status.json. TEST_ACCOUNTING.json separates
functions, cases, new/existing coverage and unloaded filenames. OUTPUT_MANIFEST.json
gives paths and raw SHA256 fingerprints for the acceptance records and source.

Frozen semantic profile: 2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81.
New semantic profile: b0e565314a91083f8c5559ce1be16fd667e82a52d7dd224de88440bdb0709075.

## Commands run on AWS

From the extracted job root, with the package directory on PYTHONPATH:

```text
python -B -m pytest -q research/CAS_META_2_COMPOSITION/tests/test_stage2_checker.py research/CAS_META_2_COMPOSITION/tests/test_typed_teaching_checker.py --junitxml=records/helm_stage2_checker_20260923/builder_tests.xml
python -B records/helm_stage2_checker_20260923/verify_stage2.py benchmark
python -B records/helm_stage2_checker_20260923/verify_stage2.py compatibility
```

Exact transport, time limits, environment, process limits and scripts are in
aws_run_001.sh and the SSM invocation receipt. No GPU, cloud model API, training,
or inference process is selected by these commands.

The next scientific gate is Claude's independent oracle/compatibility acceptance.
See _handoffs/HELM_NEXT_PHASE_20260923/CODEX_D1_STATUS.md for the version-selection
and test-harness integration notes. Do not feed sealed final answers into builder
development feedback.
