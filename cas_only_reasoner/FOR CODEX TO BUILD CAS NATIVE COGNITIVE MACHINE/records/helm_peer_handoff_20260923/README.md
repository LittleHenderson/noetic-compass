# Peer evidence integrated; independent acceptance remains open

Recorded 2026-09-23. This is an additive handoff, not a new model result.
Codex remains the builder; Claude remains the independent checker and evaluation
designer. No other agent was assigned implementation or an experiment.
A bounded Codex read-only contract reviewer checked the acceptance interfaces.

## Exact sources and evidence checked

- Peer branch: research/helm-integration-20260923.
- Peer evidence commit: dfe15fa6462866a449ddff4d6b04006ae6f3c665.
- Peer evidence root: D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE.
- Codex branch: codex/helm-stage2-checker-20260923.
- Codex source and completed builder receipts: 7f85af1eb9eb0ed991d5a8c82fa7ec4db43e539d.
- Original Helm 2.0 source: 20208c923d41c24614504d4ecc2b289ecb66eda8.
- Analogy repair implementation: 60e382b042d54eab68394393b1d8fe4540a1ac06.
- Exact AWS-tested D-1 source: b87fcc150e5818a7b1a4efd11f56b764fa15c219.

VERIFICATION.json records full paths, byte sizes, raw/LF SHA-256 and Git blob IDs
for 22 selected peer files. All 22 match the committed bytes. The five runtime
source fingerprints in each of six model receipts match original Helm 2.0
(30 comparisons, zero mismatches). This checks listed files, not all dependencies.
Both remote branch heads were checked directly.

All nine probe rows are complete, each has 24 foci and the reported absence
verdict. All nine preservation rows contain 564 record digests and match the
saved summary. Six checkpoint hashes match the launch record; this is receipt
cross-checking, not a fresh load of those checkpoints.
The three self-test verdicts and summaries agree with their original receipts.

These measurements complement the source-level finding: historical Helm 2.0
does not compare the focus world with its candidate worlds. They do not establish
new-answer accuracy or independent acceptance of the repaired model.

## Acceptance boundaries

Claude's 4,096-pair frozen-checker comparison is ORACLE_SELFTEST_PASS.
It is not a comparison against checker_v2. Its class catalogue covers 3-5 nodes.
Five- and six-node v2 acceptance remains open.

Codex's separately completed AWS builder checks remain:
110 cases / 40 functions (68 new cases / 18 new functions; 42 existing cases /
22 existing functions), 564 answer-set and slot-plan comparisons, and 6,768
historical prediction decisions, with zero disagreements. These counts do not
include Claude's oracle pairs and do not constitute Claude's independent review.
Original sealed receipts and OUTPUT_MANIFEST.json are unchanged.

The A3 T4 rule is accepted as the required future preservation check:
in ONE job on a T4, compare repaired OFF against unchanged historical source
re-run on that machine, for all nine models. OFF must equal that control bit for
bit, and the control must equal the retained T4 references. A differing control
must produce REFERENCE_NOT_REPRODUCIBLE_ON_T4, not a preservation pass.
Also retain strict old-checkpoint loading, identical keys/shapes, 174,303
parameters, and the absence verdict with OFF.

Chronology correction: commit 60e382b0 records the repair at 01:50:27 PDT;
dfe15fa6 records A3 at 06:39:37 PDT. Therefore this is an amendment after
reference generation and before independent repair acceptance. The statement
"BEFORE any repair existed" is not supported by these commits. The evidence
files are preserved; this note does not rewrite the preregistration.

The measured cross-device inequality does not by itself isolate hardware as its
only cause. Three comparisons use a retained laptop reference file. Four laptop
values are printed literals in read_results.py rather than a full retained
reference receipt. Preserve this custody distinction.

Fresh ON effects do not satisfy trained ON acceptance. Each future trained
repaired checkpoint whose analogy numbers are examined must produce
PRESENT_GRAPH_AND_DOMAIN. Old weights cannot be silently loaded into the ON
architecture, which adds five tensors. No trained ON result is claimed here.

## Concrete builder and checker ownership

Codex's next bounded source fix is to make analogy_focus_comparison read-only.
The current pointer_learner.py stores a mutable public boolean (line 731 at
7f85af1e); the preregistration explicitly requires a read-only boolean.
The probe currently reads the value but does not detect mutation.
This is a recorded open interface issue, not a fix made or tested in this handoff.
The correction must retain the OFF tensor layout, RNG behavior and old scoring
path, then receive AWS verification with the source pinned before review.

Claude owns independent D-1 acceptance, rescorer review, model acceptance and
new evaluation cells. For D-1, include:

- Frozen-file hashes compared to original anchors, not merely reported hashes.
- All 564 answer sets, 6,768 correctness decisions, and 564 original slot plans.
- Independent five/six-node oracle cases, degree collisions, full mappings,
  same-domain exclusion, NO_MATCH, and both sides of the 64-answer limit.
- Actual schema/name checks, distinct new profile, larger-world admission,
  original bank-size refusal, and the benchmark's explicit bank size/device.

The current a2_compare_harness.py inserts the alternative package path after
importing the old package. Use a reviewed integrated checkout or select package
paths before imports. It currently omits slot-plan comparisons. Its profile
check only compares digests, and its protected-file step records hashes without
checking the anchors. These are acceptance-coverage gaps for Claude to resolve;
Codex is not replacing the independent harness.

Stage 1 cell bars/effective sizes and the final success-rule decision remain
Claude's next evaluation deliverable. No sealed final answers were accessed.
The historical rule remains unchanged: Helm 1.0 PASS/PASS/PASS; Helm 2.0
PASS/PASS/FAIL, with losses in two runs and no automatic zero-loss veto.
Q4 reconstruction remains a separate experiment.

## AWS state and cost limits

Read-only provider check at 2026-09-23T14:33:50.992836+00:00 confirms:

- Claude T4 i-07e0016d92bd6197b: terminated; no currently attached volumes.
- Codex CPU i-00787ea718c2631ea: terminated; no currently attached volumes.
- Codex disk vol-0d3077a69b01406c3: InvalidVolume.NotFound.

Thus the report that Codex is still testing on that instance is stale.
Our original AWS_CLEANUP.json also records the deleted temporary bucket.
The peer's historical disk ID is not in the inspected launch/watch receipts;
absence of a current attachment alone is not an independent deletion receipt.
Claude reports its deletion; this check does not recreate that missing identity.

The peer watch record estimates $0.4834 under its $3.00 ceiling, not a billing
receipt. Its disk-cost note says 20 GB while its launch record says 100 GB.
Preserve the discrepancy; the exact claimed total upper bound is not verified.
No peer S3 data, instances, volumes, policies or working files were changed.

No new tests, model execution, training, GPU jobs or cloud compute were started
during this reconciliation. Only lightweight local receipt inspection, hashing,
editing and read-only AWS API calls occurred. The AWS execution preference
continues to govern all future tests and sustained compute.

## Reproduce this receipt inspection

From the Codex CNCM root, with boto3 available and signed-in read-only AWS access:

```text
C:/Python314/python.exe -B records/helm_peer_handoff_20260923/inspect_saved_evidence.py --peer "D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE" --repo . --out peer_verification_fresh.json
```

This reads original files and current provider state. It does not rerun either
model or checker. A fresh output must not replace the preserved VERIFICATION.json.
