# Explicitly bound retrospective packet inspection

`tools/inspect_ablation_packet_v5.py` accepts an explicit job, full source
commit, source archive and its external SHA-256, result packet and its external
SHA-256. It does not infer those identities from the packet being audited.
The old v4 inspector remains unchanged and pinned to the first failed job.

The caller-bound source archive must match its hash and commit. Before loading
the unchanged archive-safety helper, the checker compares its archived bytes
against the source manifest, local file and committed Git object. It checks
the original checkpoint-input archive hash without loading any weights.

The remaining byte, collection-index, extraction and complete-run receipt checks
retain the v4 logic, with explicit identity arguments instead of fixed globals.
The output schema is `cas-meta2-retrospective-inspection/0.2`.

The added synthetic tests cover failure-packet extraction, unsafe paths,
wrong result hash, wrong source-archive hash, wrong source commit, and wrong job.
The guarded suite passed 1,220 test functions and 178 subtests with no failures
and eight GPU modules skipped. See `records/local_ablation_inspector_v5_001`.
All captured source and 316 protected files stayed unchanged during validation.

The checker also re-inspected the actual first failed packet using that old
job's explicit source identity. It matched the original inspector's result:
90 member files, no issues, the same complete inventory hash, and no learning
or semantic-audit acceptance. The receipt is under
`records/aws_ablation_v5_failure_crosscheck_001`.

Receipt consistency is not a stored semantic audit, neural re-execution, new
training, fresh held-out performance or learning acceptance. The checker keeps
those claims false. Complete-run checks must still be exercised on a real
completed comparison and followed by inspection of the actual stored outcomes.

For the current corrected run, the source identity is
`9f562c761c7cb84c767673b2fab735cdd031b499`, source archive SHA-256
`3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd`,
and job `cas-meta2-20260906032109-361b34a0`.
The downloaded result hash must come from that run's verified download receipt;
do not substitute the first failed run's result hash.
