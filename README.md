# HELM-Q1 offline packet 1

Implemented source: strict fixture-bound records, an independent verifier,
exhaustive and pruned classical search, bounded uniform sampling, and an offline
backend that refuses submission. Tests are authored but NOT_RUN. Q0, independent
acceptance, simulation, hardware, CAS integration and retained reuse remain open.

The repository root maps to the directive's research/helm_quantum/. The importable
Python package is helm_quantum/. Python 3.10+ and its standard library suffice;
no dependency installation, SDK, credentials or live HELM checkout is needed.

## Ownership and source

Read coordination/FILE_LEASES.md before writing. Q1-Codex accepts its lease.
DeepSeek and manager local ACKs were read; Claude ACK and receiver Git access
remain unconfirmed. The complete starter
package is preserved byte-for-byte in input_package/. SOURCE_INVENTORY.json pins
the admitted inputs. The original helper is vendored unchanged, with its SHA256.
No protected upstream history, checkpoints or runtime files were imported.

## Commands on an authorized AWS runner

From this repository root, the actual first command is:

```sh
python -m helm_quantum inventory --read-only
python -m helm_quantum baseline --mode disabled
python -m helm_quantum baseline --target parity --method structured
python -m helm_quantum baseline --method uniform --samples 16 --seed 19
python -m helm_quantum validate --fixture q1-mod4
python -m helm_quantum compare --fixture q1-mod4 --offline
python -m helm_quantum verify-program --program 1 1 0
python -m unittest discover -s input_package/original_package/tests -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

These commands are supplied, not execution receipts. Do not run them on MSI under
the current AWS-only testing instruction. No authorized Q1 runner was identified.
The package's historical receipt reports 22 helper tests passed elsewhere; this
session has rerun none. See evidence/TEST_STATUS.json for current counts.

The following are deliberate refusal boundaries, not implemented quantum features:

```sh
python -m helm_quantum compile --fixture q1-mod4 --backend local
python -m helm_quantum submit --request missing.json --authorization fake
```

Both should return exit 2. Submission refuses before reading grant/request files.
Poll, cancel and decode also refuse. No provider job, cancellation, circuit,
qubit count or live quote is fabricated. Job reconciliation and retained replay
commands are not implemented in this packet.

## Contract boundary

admit_offline_fixture() creates an immutable, in-process synthetic admission with
a 60-second deadline. QuantumProblem, QuantumProposal, QuantumRunReceipt and
QuantumVerification validate direct constructors, dataclasses.replace(),
from_dict() and from_json(). Unknown/missing fields, duplicate JSON keys, expired
admission, foreign return addresses, changed semantics/scorers and fabricated
grants are refused. Every result binds the complete problem digest, mode and exact
parent/snapshot/branch/caller/frame/continuation. That digest binds source,
operations, limits and independent verifier identity.
Candidate-producing receipts also bind the complete proposal digest and require
the matching validated proposal during construction/deserialization. These are
offline records, not provider attestations or a persisted job ledger.

JSON schemas are transport documentation, not authority. The Python boundary
requires the existing admitted object. An exported request cannot establish fresh
host state in a new process; persisted host admission/replay belongs to a later
adapter. This design protects against untrusted records, not arbitrary malicious
Python code already executing in the same process. Do not use pickle as a wire
format. No fixture identity is presented as an actual HELM identity.

Verification recomputes all four outputs independently of the vendored evaluator.
Constructing/deserializing a verification record repeats that check; a returned
valid flag is never accepted on its own. No record can retain or promote anything.
Disabled records are offline checks; shadow records are comparisons; research
records are unretained candidates awaiting an authorized host retention bridge.

## Search and compiler boundary

All instruction sequences have exact length three over ID/INC/DEC/NOT2. Exhaustive
search evaluates all 64 encodings. Structured search retains one prefix witness
per complete four-input transformation at each depth; identical transformations
have identical possible suffixes. A completed search can prove no solution on
this finite domain. The parity target also fails because these operations are
bijections. Uniform sampling uses a fixed seed and finite sample count; failure
means NO_CANDIDATE_WITHIN_BUDGET, even on the negative fixture.

Limits are 64 candidate evaluations, 1024 primitive/input transitions, 1000 ms of
search time, a requested 64 MiB working-memory envelope, zero shots, zero tasks
and zero provider dollars. The finite search storage is small; Python does not
enforce an OS RSS cap. The authorized runner must supply a process memory limit
and outer timeout before execution. Search time is checked between bounded work
units, not a hard real-time interrupt. No benchmark measurement has been made.

Q1-Claude consumes fixtures/public/q1-mod4.json and the admitted contract. No
classical result lists/counts may construct the predicate or determine iteration
counts. Compiler files and compiler tests are Claude-owned; independent review
probes are DeepSeek-owned. These fixtures are not yet CAS-native operations.

## Next deliverable

Obtain a source-bound test receipt for this exact commit from an already-authorized
AWS runner and Q1-DeepSeek's independent probes. In parallel, Q1-Claude can deliver
its reversible primitives/predicate in its leased paths, with complete qubit,
workspace, gate and memory bounds, before any simulation is admitted. The next
Codex code packet integrates that reviewed compiler without enabling submission.
