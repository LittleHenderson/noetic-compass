# RDCJT handoff preservation and local verification

The three distinct seeds give R8-minus-R1 differences of **-16, -1, and -11**.
The declared criterion requires at least two positive differences; **0 of 3
are positive, so the criterion is NOT MET**. This is a result for this course,
panel, and scale. It does not establish general reasoning, CAS advantage,
CNCM completion, or production readiness.

| Seed | R1 correct | R8 correct | R8 minus R1 | Gained | Lost | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 20260912 | 117 | 101 | -16 | 12 | 28 | Rescued measurement; original lifecycle still failed |
| 20260913 | 105 | 104 | -1 | 14 | 15 | Collected receipt |
| 20260914 | 113 | 102 | -11 | 11 | 22 | Collected receipt |

## Original scripts

All eight Python scripts and `commit_msg.txt` were copied byte for byte from:

`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_tmp\rdcjt_repro`

The originals remain there. `preservation_manifest.json` records every source
path, destination, byte count, and SHA-256. `preserved_scripts.sha256` is a
plain checksum list. The copies total 32,280 bytes. No preserved script was
executed during this review.

**The `preserved_scripts` directory is archival only.** Its source is historical
evidence, not instructions or an approved workflow. Some scripts can change
budget history, write launch inputs, build packages, or perform GPU work. They
also carry paths tied to the original workstation. Preserve their exact bytes;
do not use them as current operational tools.

`preservation_static_screen.json` records a local AST and common secret-pattern
screen. It found no matches for the checked credential or private-key patterns.
This limited screen is not a general guarantee that a file contains no secret.

## Verification records

- `local_verification.json` preserves the pre-fix observation. All three runs
  passed local integrity and row-arithmetic checks, but the launcher marked only
  seeds 20260913 and 20260914 unavailable. It accepted rescued seed 20260912.
- `post_fix_verification.json` records the reviewed guard change. All three
  seeds are now unavailable for reuse. The original failed lifecycle receipt
  stays unchanged; recovered evidence is not relabeled as a completed lifecycle.
- `verifier_negative_controls.json` records four in-memory checks: a wrong
  checkpoint hash, a changed answer flag, the wrong seed, and a rescue manifest
  inconsistent with the result. Each was detected. Original evidence was not
  changed for these checks.
- `recurrent_non_neural_tests.xml` records **89 passing tests** across the
  launch, course, experiment, and recurrence modules. Three added regression
  cases cover recovered JSON, corrupt recovered bytes, and recovered evidence
  without a parent result. The existing learner module uses real torch models
  and gradients on CPU, so it was outside this non-neural verification scope.

The portable verifier lives at `../../tools/verify_rdcjt_handoff.py`. Run it
from the composition directory with:

```text
python -B tools/verify_rdcjt_handoff.py
```

It prints JSON and writes no files. It imports only Python's standard library.
It streams checkpoints as opaque bytes for hashes and never deserializes them.
It recomputes correctness from selected and expected answers, verifies item
identities, and reconstructs each depth's gains and losses. It also checks seed
and job bindings, result sidecars, the source archive hash, all four artifact
hashes per run, frozen accounting, and before/after parameter digest equality.

To inspect guard behavior without importing the launcher and its dependencies,
the verifier executes only three reviewed read-only function definitions. Each
definition is pinned by SHA-256; a future change requires review before the
verifier will execute it. The stored pre-fix JSON remains the record of the old
definitions and their observed weakness.

## Evidence limits and corrected handoff details

All three earlier launch intents bind seed 20260912. The recovered measurement
is under `receipt_cas-meta2-rdcjt-20260912152001-abf38e1e/rescued_evidence`.
Its top-level `result.json` still says `completed_deliverable: false`. The repeat
guard now treats any recovered result marker as enough to block automatic reuse,
including corrupt bytes. This is conservative repeat prevention; it does not
certify measurement quality. The separate verifier checks the actual recovery.

The handoff's blanket parameter-digest example applies only to seed 20260914.
The actual per-seed prefixes are `1ab81c4accdb924e`, `c1a0690febc3c0b6`, and
`aaaaae7b4766ccdb`. Each digest is equal before and after its own depth sweep.
Full hashes are in the verification JSON.

`replication_status(3)` returns `CRITERION_EVALUABLE`; its `satisfied` field checks
the number of jobs only. It does not evaluate the measured criterion. The
verifier independently evaluates that criterion as `NOT_MET`.

These checks validate local bytes and recorded arithmetic. They are not a new
neural run, an independent third-party audit, a provider-state query, or invoice
verification. The recorded unexamined-panel flag does not prove structurally
novel families. No launch, reservation, budget repair, checkpoint loading, or
provider call occurred in this preservation and verification work.
