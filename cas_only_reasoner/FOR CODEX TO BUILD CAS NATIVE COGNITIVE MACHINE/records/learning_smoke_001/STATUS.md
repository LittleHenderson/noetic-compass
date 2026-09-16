# Ordered ingestion teaching/reload smoke

Status: MECHANICAL_SMOKE_AND_RELOAD_OBSERVED / MATCHED_LEARNING_UNPROVEN.

One actual AWS CUDA run completed 64 optimizer updates through the ordered,
source-bound input path. Initial and final checkpoints reconstructed exact model,
optimizer, projection and cache values within the same worker. Their six public
predictions matched the corresponding original prediction files byte for byte.
The worker counted 178 model forward calls: 136 original, 21 initial reload and
21 final reload. Smoke orchestration took 9.951 seconds, the worker 12.083 seconds,
and the complete provider lifecycle, including setup and shutdown, 597.293 seconds.

This establishes the implemented teaching/reload connection. It does not establish
a fresh-process restart, resumed optimizer-step equivalence, improved learning
speed, delayed retention, unseen transfer, a CAS advantage or full-machine
completion. No local tensor/model execution or checkpoint decoding occurred.

The six already-exposed questions scored 2/6 before and 4/6 after teaching.
The three taught questions changed from 0/3 to 3/3; the other three exposed
questions changed from 2/3 to 1/3. This tiny mixed set has no matched baseline and
is not a held-out learning experiment. The earlier three-seed recurrence result
remains NOT_MET, 0/3 positive.

## Exact run and evidence

- Job: cas-meta2-ingestionsmoke-20260916183635-6ef614bf
- Source commit: 6ef614bfb448abb586a6f8c0c92058e57de9238b
- Archive SHA-256: 3015a8e0b29184624ae8e8aa06ec90a4fcd95e6fd31509a14841ea11575eb614
- Instance: i-0df9728e05ae06711; g7.2xlarge, us-west-2.
- Runtime: torch 2.11.0+cu128, CUDA 12.8, NVIDIA RTX PRO 4500 Blackwell Server Edition.
- Lifecycle: receipt_cas-meta2-ingestionsmoke-20260916183635-6ef614bf/result.json
- Lifecycle SHA-256: a99859a9bd93af0e502798399737e15a35bb8b2c9de17fad039b8fb860eb92cb
- Independent verification: delivery_verification_001/receipt.json
- Verification SHA-256: dfd7a897b4d93a5233be47d3c544502b2117b347ded2730592eabbbb9a0cdc4e

The receiver verified all 16 required evidence objects and retained all 28
inventory entries. The independent verifier checked the caller-held launch,
source archive, input inventory, installed source bytes, three checkpoint files
without decoding them, four prediction seals, target/operation consistency and
the exact training-question subset. Its result is
RECORDED_MECHANICAL_EVIDENCE_VERIFIED. This is evidence checking, not a second
numerical run or authenticated-world-fact claim.

The 211-member committed package passed package_rehearsal_002 before launch.
The guest shutdown timer was observed active in runtime_observation_003. The
provider lifecycle reports complete cleanup; direct root observation confirmed
termination in cleanup_supervision_001 without requesting forced termination.
Independent AWS readback in provider_closure_001/closure_scope.json confirmed
current-job cleanup complete. Older security/access resources remain elsewhere
in the account and were left untouched; that broader observation is separate
from this run. The retained bucket has public access blocked and encryption, but
no versioning/Object Lock status or independently verified backup is claimed.
Evidence remains in the private S3 job bucket. Separate backup verification was
not performed; the inherited archive status remains RETAINED_PENDING_COLLECTION
despite complete receiver collection, so it is not relabelled as backup success.

Exactly one $7 reservation was added to the canonical meta1 ledger, with no job
retry or refund. Revision 75 has $438 reserved and $4,562 unreserved under the
$5,000 cap. These are conservative reservations, not invoiced charges. The
publication copy and all 76 history states were verified in budget_publication_001.

## Repairs and retained limits

The earlier 169-test preparation remains recorded. Subsequent targeted checks
passed 74 launcher tests and 94 smoke/worker tests. These overlapping suites are
not added together as independent checks. The package helper passed 14 regression
checks, launch preparation passed seven local Git checks, and the delivery helper
passed 33 pure selfchecks before reading the real result.

Retained failures explain the scoped repairs: explicit committed CNCM package
reads; learner-subprocess timeout checking separate from publisher joins;
guest-side shutdown plus truthful pending/unknown cleanup; an actual positive
price quote before reservation; staged-source refusal; and common source context
separate from ordered per-question identities. The failed probes and original
source copies remain in their development directories. Shared historical
launchers and the accepted ingestion adapter/cycle remain unchanged.

All 607 accepted source files, nine prior evidence receipts and five previously
recorded runtime profiles remain unchanged. The next gate is a fresh matched
multi-seed learning experiment with equal lessons and compute, development-only
selection, saved public predictions and separate final scoring. See
NEXT_STUDY_REVIEW.md and docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md. The full goal
and wider charter remain open. This goal turn is PROGRESS.
