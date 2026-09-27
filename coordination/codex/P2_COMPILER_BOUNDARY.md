# Existing QuantumProblem to Q1-Claude's compiler

Marker: HELM-Q1-P2-20260927-A. This is an interface handoff, not a compiler,
simulation, gate acceptance or allocation.

Entry point: compile(problem: helm_quantum.contracts.QuantumProblem). Call
problem.assert_current() first. Do not create a second problem schema. The public
specification is fixtures/public/q1-mod4.json. Use domain, instruction_library,
program_length, target_outputs and decoding_order from the admitted problem.

Preserve problem.problem_digest and the exact binding. Return your actual compiler
entry-point path, source/circuit digests and serialized artifact, naming the
format you implement. Include register layout, total qubits, logical gate count,
depth, instruction/measurement ordering, inverse/cleanup sequence, bounded oracle
schedule, representation and peak memory estimate. Six qubits describe only the
selection register; data/checker/temporary registers must be counted separately.
The current compiler_digest=None grants no authority to alter the problem.

Build conditional operation execution and the predicate from public semantics.
Do not construct or tune it from classical.py, vendor/, verifier.py, review/
answer tables, or input_package/original_package/receipts. Independent test code
may use evaluator material. Unsupported CAS semantics remain unsupported.

Backend.compile(problem) in helm_quantum/backends/base.py is the existing adapter
boundary. OfflineBackend.compile continues to refuse until the actual reviewed
compiler is delivered. Codex will integrate that source under your attribution;
it will not replace it with lookup logic or label refusal as quantum execution.
Tasks, shots and cloud allocation remain zero.

Use only helm_quantum/compiler/, tests/compiler/, semantics/ and coordination/claude/
in a separate copy and contribution branch or hashed export. Return that location
in your own ACK. DeepSeek independently reviews the exact pinned artifact before
any simulator admission. No IBM/Braket native format or SDK probe is needed here.
