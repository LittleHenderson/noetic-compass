# Q1-Claude packet 2 return

Marker: HELM-Q1-P2-20260927-A. Author: Q1-Claude (new compiler lead). Session:
`session_01RqbKU6CiYqGb14Ktu14fZU`. ACK: `coordination/claude/P2_ACK.json`.

## Source identity

| Item | Value |
| --- | --- |
| Base (verified starting commit) | `35236511b2f56bddcb50f06bfc74e3c7e6d2de24` on `codex/helm-q1-offline-20260927` |
| Contribution branch | `claude/helm-q1-compiler-p2-20260927` (mirrored on the harness session branch `claude/sweet-darwin-ltjq0z`) |
| Transport | draft pull request https://github.com/LittleHenderson/noetic-compass/pull/246 from the contribution branch into `codex/helm-q1-offline-20260927`; the canonical branch and Codex's files were not written. Posting it does not mean Codex has read it; Codex's actual response will be recorded when it arrives |
| Compiler source digest | `77a3eb362ac4d00c3ca85ecedb21117a53602e55bfbbbb621772abc877261609` (`compiler_source_digest()` over `helm_quantum/compiler/*.py`) |
| Instruction semantics digest | `e687ad515ef05d8c9261d58031b0358ebbf594947f37712e9ed314eb3b6d5ef9` |
| Circuit digest, add2 target | `48d3d89e63035e5eab077188900d9a522a5fba8ee9999cab4b0090e367879210` |
| Circuit digest, parity target | `bf06aa452f927a06dfa1afd215aa4edc7fbfc518d06db56e5d302cd220d2b928` |
| Admitted source digest read from the problem | `e206253043a0bbe185ec5a08897fdf8d5132bc9c417d2805da0c4c764572356e` (unchanged by this work: admission excludes `compiler/`) |

`problem_digest` values are not listed because Codex's admission includes a per-process
deadline, so they differ per run; the binding records whichever problem was compiled.

## Code paths (all inside the Q1-Claude lease)

- `helm_quantum/compiler/ir.py` — abstract gate IR (X/Z/H with positive and negated controls), inverse, counts, ASAP depth bound, digest.
- `helm_quantum/compiler/sim.py` — standard-library dense statevector simulator (pinned index convention), sampling, and exact classical basis execution of permutation/phase circuits.
- `helm_quantum/compiler/reversible.py` — controlled reversible ID, INC, DEC, NOT2 on a two-qubit data register with explicit `lsb`/`msb` ordering and inverses.
- `helm_quantum/compiler/predicate.py` — `PredicateSpec`, `RegisterLayout`, `compile_predicate`: the length-L semantic predicate (conditional execution for all four public inputs, target checks, phase mark, full uncomputation). Precise `UnsupportedCapability` errors.
- `helm_quantum/compiler/search.py` — bounded BBHT amplitude amplification on the local simulator; `SearchOutcome`.
- `helm_quantum/compiler/resources.py` — `SimulationBudget`, `ResourceModel`, `admit_simulation` (fail-closed gate before any state is allocated).
- `helm_quantum/compiler/boundary.py` — `compile_problem(QuantumProblem) -> (CompiledPredicate, CompilerBinding)`; `compiler_source_digest()`.
- `tests/compiler/` — 50 test methods plus `reference.py`, an independent evaluator used only by tests.
- `semantics/` — instruction semantics, register layout, CAS/RPM/RPA mapping with the UNSUPPORTED list.

## Compiler interface and public input binding

```python
from helm_quantum.admission import admit_offline_fixture
from helm_quantum.compiler import compile_problem, SimulationBudget, bounded_search, estimate_resources

problem = admit_offline_fixture("add2").problem()      # Codex's admitted QuantumProblem
pred, binding = compile_problem(problem)               # reads public fields only; no mutation
model = estimate_resources(pred, SimulationBudget())   # finite model, no simulation
outcome = bounded_search(pred, SimulationBudget(seed=0))  # local ideal simulation, bounded
```

`compile_problem` reads `family`, `domain`, `instruction_library`, `program_length`,
`max_program_length`, `prerequisites`, `target_outputs`, `decoding_order`, and the digests.
It never reads the goal name, never imports `classical.py`, `verifier.py`, `vendor/` or any
receipt (tested in a fresh interpreter), and returns `execution_authority = "NONE"`.
Unsupported features fail with `UNSUPPORTED_INSTRUCTION_LIBRARY`, `UNSUPPORTED_DOMAIN`,
`UNSUPPORTED_PROGRAM_LENGTH`, `UNSUPPORTED_TARGET`, `UNSUPPORTED_DECODING_ORDER`,
`UNSUPPORTED_FAMILY`, `UNSUPPORTED_PREREQUISITES`, `UNSUPPORTED_VARIABLE_LENGTH`.
`SearchOutcome` is not a `QuantumProposal` or `QuantumRunReceipt`; Codex's contracts admit
neither a simulator origin nor a simulator execution kind today.

## Register allocation (compiler output, length 3)

| Register | Qubits | Count |
| --- | --- | --- |
| selection (slot k: qubit 2k opcode MSB, 2k+1 opcode LSB) | 0–5 | 6 |
| data (lsb 6, msb 7; x = lsb + 2·msb) | 6–7 | 2 |
| check flags (one per public input) | 8–11 | 4 |
| decomposition ancillas (abstract multi-controlled gates) | none | 0 |
| total | | 12 |

Decoding order `instruction-left-to-right;two-bit-op-msb-first` is pinned and tested;
program (1, 2, 3) is selection bitstring `011011`.

## Resource model (estimates labelled; measured values labelled)

| Quantity | Value | Kind |
| --- | --- | --- |
| State representation | dense statevector, Python complex in one list, qubit i = index bit i | design |
| Total qubits / amplitudes | 12 / 4096 | compiler output |
| State bytes | 163,840 (40 B per amplitude) | estimate |
| Peak process memory | 33.9 MB (32 MiB interpreter assumption + two states) | estimate |
| Peak RSS of the whole test process | 25.6 MiB | measured, this container |
| Oracle gates per application | 313 abstract gates: 200 C2X, 96 C3X, 1 C3Z, 16 X; max 3 controls | compiler output |
| Diffusion gates | 25 (6 H, 6 X, 1 C5Z, 6 X, 6 H) | compiler output |
| Gates per Grover iteration | 338 | compiler output |
| Oracle depth | 313 serial bound; 306 ASAP-layered bound (nearly serial: every gate touches the data register) | abstract bound |
| Toffoli estimate per oracle | 491 (Barenco 2k−3 per k-controlled gate, dirty ancillas) | estimate |
| SDK-native depth | NOT_MEASURED (no SDK installed or authorised) | — |
| Max oracle calls (default budget) | 64, equal to exhaustive classical evaluation of the same predicate | limit |
| Runtime ceiling | 43.3 s at the planning assumption of 2.0 ms per gate | estimate |
| Measured cost of one oracle application | 28.8 ms = 0.092 ms per gate (12 qubits) | measured, this container |
| Stop behaviour | stop before the first oracle application that would exceed the call budget; stop at the next round boundary after the wall-time budget; no retry; no limit raised | design |

## Search schedule for unknown solution count

BBHT: m starts at 1, each failed round multiplies m by 6/5 up to √N (=8), the iteration
count j is drawn uniformly from [0, ⌊m⌋), the sample is checked by classical execution of
the same compiled circuit (counted as one oracle call). Assumptions: ideal noiseless
simulation, N = 64. Bound: for 1 ≤ t ≤ 3N/4 the expected iterations are at most
4.5·√(N/t) (BBHT Theorem 3); with budget B, P(no candidate | t ≥ 1) ≤ 4.5·√(N/t)/B
(Markov, loose). Failure interpretation: `NO_CANDIDATE_WITHIN_BUDGET` is never
`UNSAT_PROVED`. The schedule constants are fixed in source and are not tuned from any
observed count; `bounded_search` takes no iteration or count argument.

Measured outcomes on this container (local ideal simulation, no authority):

| Target | Seed | Status | Program | Oracle calls | Rounds | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| add2 | 0 | CANDIDATE_SAMPLED | (0, 1, 1) | 13 | 9 | 253 ms |
| add2 | 1 | CANDIDATE_SAMPLED | (0, 2, 2) | 8 | 7 | 61 ms |
| add2 | 2 | CANDIDATE_SAMPLED | (2, 2, 0) | 1 | 1 | 3 ms |
| parity | 0 | NO_CANDIDATE_WITHIN_BUDGET | none | 60 | 20 | 1,610 ms |

Fixed-iteration check (test): with the test-side independent count t = 6, the simulated
success probability after k = 0, 1, 2 iterations equals sin²((2k+1)θ) to 1e-9.

## Tests

Command (from the Q1 root):

```sh
python -m unittest discover -s tests/compiler -p 'test_*.py' -v
```

| Suite | Collected | Executed | Pass | Fail | Error | Skip | NOT_RUN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tests/compiler (Q1-Claude), this container | 50 | 50 | 50 | 0 | 0 | 0 | 0 |
| tests/compiler (Q1-Claude), admitted AWS venue | 50 | 0 | — | — | — | — | 50 |
| tests/ (Q1-Codex) | 43 (collection only, unchanged by this work) | 0 | — | — | — | — | 43 |

Execution venue: the owner-opened Claude cloud session container, not MSI and not an
AWS runner; bounds enforced: one CPU (`taskset -c 0`), `ulimit -v 524288` (512 MiB
virtual), outer `timeout 180`; wall time about 1 s; zero incremental cloud spend, no
hardware, SDK, account or network calls. If the manager does not admit this venue, the
executed row is REPORTED_NONADMITTED_EXECUTION and the admitted-venue row stands.
Coverage: primitive controls/inverses/bit ordering, every basis program for three
targets, coherent superposition, relative phase, selection preservation, measurement/
decoding order, ancilla cleanup, involution, unsupported-capability errors, evaluator
import isolation, fixed-iteration theory match, bounded schedule, refusal before
allocation, wall-time stop, boundary bindings, non-mutation, expired admission, resource
model figures. A truth table alone is not relied on: superposition tests carry the
coherent claims.

## Defects and limits (open)

1. Depth is nearly serial (306 of 313) because one data register is reused per input; a
   four-data-register variant would trade 6 qubits for parallel depth. Not built.
2. Multi-controlled gates are abstract; the Toffoli figure is an estimate and no device
   lowering (IBM/Braket) exists. Provider documentation was not consulted; none was needed.
3. No noise model; ideal simulation only. No hardware speed claim is made or possible at
   N = 64, where the default oracle budget equals exhaustive evaluation.
4. `SearchOutcome` cannot become a `QuantumProposal`: `contracts.py` admits only
   `origin == "offline-classical"` and `execution_kind == "CLASSICAL_OFFLINE"` (Codex scope).
5. The search's in-loop sample check uses the compiled circuit's own semantics; it is not a
   verifier and grants nothing. Independent acceptance stays with `helm_quantum/verifier.py`.
6. `problem_digest` varies with the admission deadline, so a binding is per-process.
7. Q1-Codex's 43 tests were collected here for a count check only, not executed.

## CAS / RPM / RPA

See `semantics/cas_rpm_rpa_mapping.md`. Bound today: only `ReturnAddress` fields
(`parent_ref`, `snapshot_ref`, `snapshot_digest`, `branch_id`, `caller_id`,
`caller_frame`, `continuation`, `checkpoint_digest`) via `problem.binding`, carried
unchanged. Nested/shared prerequisites, checkpoint compatibility, RPA display and every
Noetic/Drive/Register mapping are UNSUPPORTED pending approved source exports from the
incumbent owner. The fixture is synthetic and is not called CAS-native anywhere.

## Next missing connection (one)

A Codex-owned proposal path for simulator-sourced candidates: an admitted `origin` for
`LOCAL_IDEAL_SIMULATION`, a receipt `execution_kind` for it, and the binding of
`SearchOutcome.program` into `propose`/`verify`. Then DeepSeek's distinct check of the
pinned compiler commit, and an admitted-venue run of both suites with a commit-bound receipt.

## Usage and limits

Monetary cost: NOT_EXPOSED (unknown is not zero). Active time: within the 30-minute bound
for this packet; five-minute updates were kept while active; no background monitoring is
promised. Children: 0. Cloud jobs, hardware calls, SDK/account probes, new dependencies,
paid resources: 0. Incumbent models, jobs, source and automation: untouched.
