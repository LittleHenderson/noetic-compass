# Known-example fit succeeded; unfamiliar composition remains unproven

Job: `cas-meta2-20260906054131-feae01a9`.
Source: `6a71e01c3689a1debe56eed842f101dfa4990556`.
Source archive SHA-256: `17cdaaf25a9d07439598bf24ab9105193da1a15614fe9b41a2ba037a49849d4b`.
Result archive SHA-256: `7e29dfa32f89159c3a1f476614fab5d9c80b9778e7a724cc2f967c72a158b34f`.
Result archive: 11,614,881 bytes, return code zero, no omitted full files.

The fresh CAS and matched generic candidates each completed 600 optimizer steps
over 200 epochs. Training/measurement worker time was 139.627063307 seconds.
Both freely generated all 24 correct program-and-input-binding targets at the
final epoch, improving from zero. All 24 were known training examples, not held-out
tasks. Neither model used the accepted checkpoint; accepted weights are unchanged.

| Epoch | CAS depth 1 /8 | CAS depth 2 /8 | CAS depth 3 /8 | Generic total /24 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 0 |
| 60 | 3 | 0 | 0 | 2 |
| 100 | 8 | 6 | 5 | 14 |
| 130 | 8 | 7 | 8 | 23 |
| 140 | 8 | 8 | 8 | 24 |
| 200 | 8 | 8 | 8 | 24 |

Both first reached 24/24 at the recorded epoch 140 and remained there at every
later recorded measurement. This is not a best-checkpoint selection: the initial
and final states were saved under the fixed rule. Every recorded measurement is
retained; the table does not replace the full curve.

Final CAS checkpoint SHA-256:
`78bb23c0445a115f72ec1c0ef0c2594c21e4140b511966935fe8dfc1c11e92d6`.
Final generic checkpoint SHA-256:
`013d72412c6f9cd1377f0847a3bd8c4d417bd23d79b80af0ea65350b68195f7b`.
Both files are in the packet under cloud_job/campaign/fit/ and in the verified
extraction records/aws_fit_v5_001_review_extracted/cloud_job/campaign/fit/.

The offline review in records/fit_packet_review_v5_001/ returned
`RECORDED_FIT_RECOUNT_PASSED`. It checked 508 source/input files, the complete
archive and payload inventories, protected source/wheel identities, all 22
measurement files, all four checkpoint byte hashes, and repeated the frozen
generation-score calculations. GPU XML records show 4 native, 27 policy, and
2 fit contract tests passing on the registered Blackwell environment.
This was not independent neural replay, native task scoring, or independent
recount of the teacher-forced logits. No checkpoint was loaded locally.

## What this changes

The current CAS architecture, decoder, and training path can fit this small set
of nested examples. An absolute inability to represent these particular programs
is no longer a good explanation of the earlier failure. It does not prove that
longer training alone solves the larger curriculum: this run also reduced the
training set substantially and restarted from fresh candidates.

The earlier exposed composition result remains CAS **0/72**, generic **12/72**,
rule **72/72**. No CAS-specific advantage, new held-out skill, qualified memory,
or complete cognitive-machine capability is claimed or promoted.

Next learning work should target input binding and child selection, verify fit
on a structurally varied curriculum, and reserve new tasks for unchanged native
evaluation. Keep the earlier test exposed; do not reuse it as fresh validation.

## Budget and resource state

This run reserved $7. Shared reservations total $60 of the $400 cap, leaving
$340 unreserved. Reservations are not an invoice and are not automatically
refunded. Source and result archives are preserved locally.

The launcher finished with termination_confirmed=true, no cleanup errors, and
no remaining job volumes. A separate provider check at
2026-09-06T05:54:49.890396+00:00 passed all seven cleanup checks: the instance
terminated and disks, security group, worker profile, both roles, and shutdown
schedule were absent. The S3 evidence objects retain their seven-day expiry.
The launcher estimated compute/disk/IPv4 charges at
$0.5216805109999999999999999999; this excludes S3, transfer, taxes, and other
charges and is not an AWS invoice. No reservation refund was applied.
