# CAS-META-2: learned program composition

This is a separate experimental candidate, not a replacement for the accepted CAS-META-0 runtime or the completed CAS-META-1 pilot.

The next measured skill is to turn a bounded problem into a new nested CJT program with named intermediate values, then execute it through unchanged native CJT APIs. The candidate must emit operations, calls, and bindings, not just select a prepared whole program.

Current state: the first AWS Blackwell preflight ran from source `2a3ec1132770b121881a49effee2aa5d4e0494fb`. The four preserved native GPU contract tests passed. Three of four new policy GPU tests passed; the active-gradient check failed, so the job stopped before composition smoke execution or training. Raw failure evidence is retained under `records/aws_smoke_001`. No CAS-META-2 learning result has been established.

The next candidate keeps Drive and summed absolute current unchanged, and sets initial gate saturation to twice the configured maximum input length. All gate parameters remain trainable. Its revised GPU preflight checks the real default training geometry, finite nonzero gradients, operating-region measurements and a resistance intervention. These revised neural checks still require AWS execution. Local record/control checks report 367 passed tests and 52 passed subtests; the GPU-only module was skipped, and all 316 protected files remained unchanged (`records/local_candidate_004/receipt.json`).

## Preserved evidence

- Accepted executor baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.
- Completed learning pilot evidence: `6a4524d5f21f77194b35d0830d2b16da8530b17d`.
- The separate third-party receipt `../CAS_META_1_LEARNED_SELECTION/records/third_party_semantic_audit_glm2/audit_receipt.json` reports 72 references, 360 reverified executions, and matching verdicts: CAS trained 66/72, CAS untrained 8/72, generic trained 61/72, generic untrained 8/72, rule 72/72. It is a stored-evidence audit, not a new neural run. Its source file remains untouched.

## Boundaries

- All model construction, training, tensor computation, and neural evaluation must run on AWS CUDA. Laptop checks are pure parsing, hashes, control logic, and stored-evidence checks.
- No further T4 use. The amended AWS allowance is $400 total across the earlier pilot, this campaign and later research. The shared `records/budget/campaign_ledger.json` preserves all earlier reservations and records the current unreserved allowance. A reservation is a conservative allowance, not an AWS invoice.
- Baseline source, native parameters, contracts, verifiers, and earlier raw evidence remain unchanged. No automatic merge.
- This candidate initially supports unary procedure inputs and a bounded acyclic call graph. Named intermediate values are real reference selections. This is not yet arbitrary multi-input composition, unbounded recursion, missing-skill acquisition, or complete Noetic semantics.
- The first curriculum uses controlled wording that describes the required operations and dependencies. The model translates that wording into executable program structure; it is not yet discovering an algorithm from an outcome-only request. Held-out program JSON and answers are withheld during prediction, but the public instructions deliberately contain procedural information.
- Functional addresses identify a place in a program. Separate run and call identities identify an execution. Oscillatory phase is never the sole chain identity.
- A valid trace is necessary but not sufficient: correctness also requires the expected dependency graph, bindings, and actual native output bytes.

See `VISION_REQUIREMENTS.md` for the full endpoint and open requirements. A small successful experiment must not be relabeled as completion of that endpoint.
