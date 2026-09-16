# Input-v0.2 cloud teaching/reload check

Status: RECORDED_INPUT_V02_MECHANICAL_EVIDENCE_VERIFIED.

The new input-v0.2 path completed on AWS. It rebuilt a training-only tokenizer
from three examples, created a fresh model origin, made 64 optimizer updates
and 178 actual forward calls, and reconstructed the initial and final checkpoints
with matching values and public predictions in the same worker.

| Exposed questions | Before | After | Gains | Losses |
|---|---:|---:|---:|---:|
| Three taught questions | 0/3 | 3/3 | 3 | 0 |
| Three other questions | 1/3 | 2/3 | 2 | 1 |
| Total | 1/6 | 5/6 | 5 | 1 |

The lost answer was REACHED_VIA Bicycle to Frame. The two other-question gains
were LIST_PARTS Cart and FIND_SHARED_PART Bicycle/Frame. These are already-exposed
engineering questions, not untouched transfer tests. The aggregate increase
does not erase the lost answer.

## Exact execution and evidence

- Tested source: bedc06d52211491b7de4ef955227822801faa4a1.
- Job: cas-meta2-ingestionsmoke-20260916195214-bedc06d5.
- Instance: i-07c15e04e29d558bf, g7.2xlarge, us-west-2.
- Runtime: torch 2.11.0+cu128, CUDA 12.8, NVIDIA RTX PRO 4500 Blackwell Server Edition.
- Worker elapsed: 12.73912628 seconds; smoke: 10.64245666 seconds.
  Lifecycle including collection/cleanup: 561.9404458 seconds.
- Lifecycle result SHA-256:
  66aee7d84a2a5397d1f863c454fc6d44381dbb747b2d97a605f50c0e50623f08.
- Delivery verifier receipt SHA-256:
  2e599b677018e3904de4af68f7f00add84c4b81dd4f4df0c078c9d9f8dcd4eff.
- Smoke receipt SHA-256:
  7e8b1f4190a4a5331482108d4e9a361e49c9e10a7efe0317848d73b6bd1ed338.

The separate v0.2 verifier passed 24 pure controls and independent source review.
It preserves the v0.1 checker and changes only its version guard through a
checked transformation, adding exact caller/source/disclosure checks.
Independent review confirms 245 file pins, 215 archive members, 16 required
objects and 13 artifacts. Checkpoints were hashed without decoding or rerunning
a model. Predictions were sealed before private scoring. The exact reload result
is same-worker reconstruction, not a fresh-process restart or resumed-optimizer
step equivalence claim.

## Closure and cost boundary

Fresh AWS observations at 2026-09-16 20:05:55–20:05:58 UTC confirm this instance
terminated and its security group, worker role/profile, timer role and schedule
absent. No active CAS-tagged instance, volume or network interface remained.
The raw broader scan remains PARTIAL_OR_OPEN because resources named for the
older cas-meta2-teaching-20260908134143-ebd84f71 job remain untouched.
provider_closure_001/closure_scope.json separates that older job from this run;
its SHA-256 is 91581c2c8d8f99d9579d979963e1204bf39a819aecddada79a3a6a73647a86d7.

The private evidence bucket remains present, with public access blocked and
AES256 encryption. Its results prefix contains 24 objects (718,225 bytes).
HEAD sizes match the checked local marker, manifest and three checkpoints.
This presence/configuration readback is not a second content download, WORM,
independent backup or final invoice. The inherited lifecycle archive status
remains RETAINED_PENDING_COLLECTION; collection itself is COMPLETE_VERIFIED,
and backup verification is NOT_ATTEMPTED.

Exactly one $7 reservation was added; there was no retry or automatic refund.
Canonical budget revision 76 records $445 reserved and $4,555 unreserved under
the $5,000 cap. The vision-next ledger is an exact publication copy, not a second
spending ledger. The observed compute quote was $2.52/hour; it is not the bill.

## What this establishes

The corrected complete-inventory input can reach and update the learner and
survive the recorded reload checks. This run does not execute the full six-face
course or new scoped encoder. It does not establish better learning than a
matched control, delayed retention, untouched transfer or a CAS-specific gain.
Fresh tokenizer/model bindings also prevent a causal v0.1-versus-v0.2 claim.

The full-course preparation was separately published with 129 pure checks.
Target-conditioned choices, the course-aware worker, numeric scoped acceptance
and a distinct frozen comparison remain open. The complete project goal remains
active. Earlier viewer, v0.1 smoke and negative three-seed evidence are preserved.
