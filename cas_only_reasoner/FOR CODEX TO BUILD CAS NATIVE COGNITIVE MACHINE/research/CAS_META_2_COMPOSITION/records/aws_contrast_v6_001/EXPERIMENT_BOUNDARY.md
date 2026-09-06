# Separated-curriculum run: registered scope

Frozen source: `acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0`.
Job: `cas-meta2-20260906064703-c0d74ffa`.
The registered counts below must be confirmed against the actual cloud dataset
manifest before they are reported as completed data assembly.

| Partition | Registered tasks | Depth distribution | Purpose |
| --- | ---: | --- | --- |
| Training | 640 | 128 depth 1; 256 depth 2; 256 depth 3 | 128 flat tasks and 256 contrasting pairs (512 tasks) |
| Validation | 96 | 32 at each of depths 1, 2, and 3 | Checkpoint selection only; separate graphs, observations, and wording combinations |
| Test | 72 | 48 depth 3; 24 depth 4 | 24 matched triplets, evaluated only after prediction sealing and training exit |

Each test triplet contains:

- `same_depth`: a new depth-3 program graph and new observations, with familiar
  wording combinations;
- `wording_shift`: the same program and observations, with held-out wording;
- `deeper_calls`: a matched depth-4 program with the same symbolic work and
  observations as the depth-3 task, but deeper calls.

These are not 72 independent structures. Graph signatures ignore mere naming
changes. The test excludes known exposed graph signatures. It tests new
program combinations together with fresh observations; it does not isolate
fresh observations on previously trained composition programs as a separate
test condition. The controlled procedural language is not unrestricted English.

The original 256 prototype tasks remain development evidence and are excluded
from the current training, validation, and test partitions. The broader builder
uses their contrast construction approach; it does not literally append those
256 old task records. The later user request to include those exact records is
therefore not implemented in this already-frozen run. The running experiment
will not be changed mid-run or described as if it had included them.

Both neural families start from fresh candidate copies. The accepted executor,
verifier, permissions, and baseline weights remain unchanged. The registered
training is 200 epochs, 8,000 optimizer steps per family, with validation-only
checkpoint selection and four neural arms plus the rule baseline at test time.
Actual completion, checkpoint identities, and outcomes remain subject to the
collected result package and audits. No automatic candidate promotion follows.

Budget reservation: $7 for this job under the existing $400 total authorization.
Canonical ledger revision 9 records $67 reserved and $333 unreserved. These are
conservative reservations, not a spending target or an AWS invoice. No second
job was started in response to the latest instruction.
