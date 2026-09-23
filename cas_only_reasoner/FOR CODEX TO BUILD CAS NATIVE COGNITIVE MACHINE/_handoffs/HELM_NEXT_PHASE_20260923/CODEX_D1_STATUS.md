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

Builder test receipts and completion status will be recorded in the D-1 README.
Independent acceptance stays open until Claude runs and records its own checks.
