# Retained curriculum contrast diagnosis — 2026-09-16

The six retained learners reproduce all saved practice scores, then fail many
questions when node names or relationships change. Merely reordering the written
connections leaves every selected answer correct. All model weights remain
unchanged; zero optimizer updates were taken.

| Contrast | Correct / attempted |
|---|---:|
| Original correctly answered practice cases | 109 / 109 |
| Consistent node renaming | 47 / 109 |
| Reordered nodes/connections | 109 / 109 |
| Changed containment connection | 3 / 32 |

Renaming changes 62 answers after mapping labels back to their original names.
Reordering changes none. Rewiring changes only 9 of 32 answers even though the
correct relationship answer changes. These are conditional, retrospective
readings on each learner's originally correct practice cases, not an untouched
transfer score or an unbiased comparison of the two curricula.
The 109 evaluations reuse the same 30-question practice set across learners;
they are not 109 independent questions or independent statistical samples.

All 192 option-order permutations of the 32 eligible LIST_PARTS cases remain
correct. Each answer slot is chosen 64 times. The shortest option is chosen zero
times and a longest option 78 times, but these are observations on different
semantic options, not a causal test of option length. These readings do not
establish a length bias or identify the shortcut responsible for the historical
5/90 LIST_PARTS result. The historical negative result remains unchanged.

## Execution and evidence

- Job: `cas-meta2-graph6contrast-20260916052513-7bf38e64`.
- Frozen implementation: `fb4bb4a297d6c5a9268bd96d98eb983d934ef4f5`.
- Source archive SHA-256: `8226f34037f518d2c44569620abd39f5ee63e08fb455487dfe75e46bb09240cc`.
- AWS instance: `i-0c4022a6e99e5ceef`, `g7.2xlarge`, `us-west-2`.
- Original source job: `cas-meta2-graph6curr-20260910133000-aecb5d07`.
- Conditions: control/varied; paired seeds 20260913, 20260914, 20260915;
  retained step-256 checkpoints. None selected by a new score.
- Practice correct counts reproduced exactly: 23, 12, 23, 14, 23, 14 of 30.
- Inference elapsed: 6.066 seconds; setup, collection and teardown are separate.
- Reservation: $7.00; this is not the actual billed amount.
- No neural computation ran on the local machine. Local checks were pure
  orchestration/input tests and source-package rehearsal.
- `RECOUNT.json` independently recounts raw contrast rows and verifies retained
  input identities, output hashes, and all six before/after parameter digests.
- The receiver reports `COMPLETE_VERIFIED` for all five required evidence files.
  The final lifecycle receipt reports `AWS_CANDIDATE_FINISHED`,
  `completed_deliverable: true`, and compute cleanup `COMPLETE`.
  AWS independently reports the instance terminated. Evidence remains retained.
- Ledger revision 73: $424.00 reserved and $4,576.00 unreserved under the
  existing $5,000.00 cap. The actual invoice was not queried.

The package's inherited resource plan includes historical training metadata.
The job's separately frozen `execution_design`, worker configuration, strict
1,200-second inner timeout, and output record all bind this diagnosis to zero
optimizer updates. The original 4,210,428-byte result is transported as a
360,086-byte deterministic gzip copy and checked against its original SHA-256
after decompression; the original receipt is never edited.

## Next experiment boundary

These findings support testing stronger teaching of relation-preserving views
and changed relationships. They do not prove that a successor works. The
complementary and perspective directives remain build-only here. Their data,
fairness, numerical and runtime gates must succeed before an empirical claim.
The completed recurrent-depth criterion remains NOT_MET, 0 of 3 positive; no
additional recurrent-depth seed is justified by this diagnosis.
