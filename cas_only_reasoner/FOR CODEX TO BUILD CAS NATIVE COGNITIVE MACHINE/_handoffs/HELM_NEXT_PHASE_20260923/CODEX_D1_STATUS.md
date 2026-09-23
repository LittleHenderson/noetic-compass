# D-1 implementation and AWS handoff

Codex is the builder. Claude remains the independent checker and custodian of
the sealed evaluation. No duplicate model experiment is selected here.

Starting checkpoint: d206b42aa1b68d24f65ab01ec58cc82aad432859.
Branch: codex/helm-stage2-checker-20260923, in Codex's existing isolated
helm-integrated-repairs working folder. The prior branch remains at its checkpoint.
Implementation commit: 45828c45. First cloud source snapshot: b87fcc15.

New public modules in research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching:

- checker_v2.py: six-node exact directed isomorphism, new semantic profile 0.2.
- answers_v2.py: all syntactic correspondence assignments up to six nodes.
- slots_v2.py: unchanged original plans for old supported packets; new profile
  for larger correspondence; original complete-assignment scoring semantics.

The original checker.py, answers.py, slots.py, source.py, pointer_inputs.py,
grader, old models and receipts are not edited. Answer objects and correct flags
are the compatibility requirement. New checker target/check digests differ by
design because their semantic profile differs. Old slot plans must be byte-identical.

The owner instructed: "use aws as there is only 354 mb of 16 gbs locally".
This is saved in global Codex and Claude instructions, repository/homebase
AGENTS.md, and docs/AWS_EXECUTION_PREFERENCE_20260923.md. It supersedes the
local-device selection for new checks. Preserve old records' actual devices.
Do not rerun the memory-exhausted laptop probe automatically.

AWS CPU job limits and actual provider identity are recorded under
records/helm_stage2_checker_20260923/WORK_PLAN.md and AWS_JOB.json.
Benchmark timing from this job is AWS timing, not a local acceptance measurement.
No neural inference, training, GPU execution, or sealed final-test reading occurs.

Independent-review handoff details:

1. The current a2_compare_harness imports the original package before adding
   --v2-package-root. Python normally keeps that imported package's search path;
   adding sys.path alone may not expose the separate v2 module. Run a reviewed
   integrated checkout or explicitly select package paths before the first import.
2. That harness compares answer sets and correct flags but does not yet compare
   slot plans, despite the A2 specification requiring it. The builder's separate
   stream check includes all old plans; Claude should independently cover them.
3. Pure reader input syntax already accepts larger node inventories, but the
   public learner still imports the original slots module. D-1 is a checker/slot
   capability, not a claim that larger public learned inference is integrated.
4. The copied owner D-1 decision is Claude's recorded chat transcription.
   Codex has not created an owner signature or claimed independent custody of
   that separate conversation. Current user continuation/AWS instructions are
   directly present in this task.

Builder checks are complete on AWS: 110 test cases (40 functions), all 564
registry targets and plans, and all 6,768 saved prediction decisions passed.
No answer, witness, coverage, plan or correctness differences were found.
The 1,000-question five-node benchmark took 23.554114344 seconds. It used three
worlds per bank; do not describe that timing as a 64-world benchmark.
Complete receipts, resource amendment, cleanup, custody and fingerprints are in
records/helm_stage2_checker_20260923/README.md and OUTPUT_MANIFEST.json.
The instance, disk and temporary bucket are confirmed deleted. No models ran.
Independent acceptance stays open until Claude runs and records its own checks.

Next command, on Claude's reviewed AWS integration checkout containing both
the new modules and its independent harness (not on the laptop):

```text
python -B records/helm_eval_design_20260923/d1_acceptance/a2_compare_harness.py --v2-module cas_meta2.typed_teaching.checker_v2 --out a2_result.json
```

This next command has not been run by Codex. Apply the package-path and missing
slot-plan coverage notes above, and run Claude's separate A3 oracle before use.
