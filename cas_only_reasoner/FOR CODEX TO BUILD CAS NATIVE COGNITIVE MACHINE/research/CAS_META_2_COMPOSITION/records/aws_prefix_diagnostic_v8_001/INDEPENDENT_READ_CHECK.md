# Internal read-only verification

A second agent independently inspected the completed files without calling AWS,
loading tensors, or changing source. This is an internal review, not a new
external auditor acceptance.

- Approval, job, $4 cap, source commits, source/development archives, worker plan,
  reservation and checkpoint identities agree.
- 480/480 diagnostic row hashes and 510/510 collected file hashes match.
- 615/615 source files and 15/15 development bundle files match their manifests.
- All 144 summary groups reproduce from the saved rows, including counts,
  correct choices and mean losses.
- All seven remote subprocess receipts report exit 0, with matching raw output hashes.
- All 480 generated actions equal their previously saved development actions.
- All 480 grammar/site comparisons were independently replayed with the frozen
  pure source; results are saved in first_errors_001.

The frozen worker checks model-state equality and checkpoint hashes before and
after diagnosis. Successful completion means those checks passed. The internal
review independently checked checkpoint file bytes but did not deserialize tensors.

CAS-selected has 1,064/2,272 comparable self-generated decision sites; 875 have
changed context and 333 are missing. Generic-selected has 1,173/2,272 comparable
sites, 867 changed and 232 missing. Across every checkpoint, zero scored
self-generated sites followed an earlier prefix difference. No recovery after
an error is demonstrated by these matched-site scores.

The final launch receipt reports confirmed termination, zero tagged disks,
and no cleanup errors. Three result objects remain under the seven-day expiry
rule. A later direct read is saved in execution_001/post_run_provider_read.json.

These checks establish saved-byte consistency and the stated diagnostic result.
They do not establish new learning, native task correctness, held-out generalization,
or a CAS-specific advantage.
