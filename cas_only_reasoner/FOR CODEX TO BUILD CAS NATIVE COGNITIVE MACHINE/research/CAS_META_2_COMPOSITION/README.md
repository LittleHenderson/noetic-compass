# CAS-META-2: learned program composition

This is a separate experimental candidate, not a replacement for the accepted CAS-META-0 runtime or the completed CAS-META-1 pilot.

The next measured skill is to turn a bounded problem into a new nested CJT program with named intermediate values, then execute it through unchanged native CJT APIs. The candidate must emit operations, calls, and bindings, not just select a prepared whole program.

Current state: implementation in progress; no CAS-META-2 cloud execution or learning result has been established.

## Preserved evidence

- Accepted executor baseline: `0917267b1354e5d036263eaa6ba9a7197eafb776`.
- Completed learning pilot evidence: `6a4524d5f21f77194b35d0830d2b16da8530b17d`.
- The separate third-party receipt `../CAS_META_1_LEARNED_SELECTION/records/third_party_semantic_audit_glm2/audit_receipt.json` reports 72 references, 360 reverified executions, and matching verdicts: CAS trained 66/72, CAS untrained 8/72, generic trained 61/72, generic untrained 8/72, rule 72/72. It is a stored-evidence audit, not a new neural run. Its source file remains untouched.

## Boundaries

- All model construction, training, tensor computation, and neural evaluation must run on AWS CUDA. Laptop checks are pure parsing, hashes, control logic, and stored-evidence checks.
- No further T4 use. The amended AWS allowance is $400 total, including the $4 already reserved, the campaign, and later research. The new shared ledger preserves the old ledger and its history. A reservation is a conservative allowance, not an AWS invoice.
- Baseline source, native parameters, contracts, verifiers, and earlier raw evidence remain unchanged. No automatic merge.
- This candidate initially supports unary procedure inputs and a bounded acyclic call graph. Named intermediate values are real reference selections. This is not yet arbitrary multi-input composition, unbounded recursion, missing-skill acquisition, or complete Noetic semantics.
- Functional addresses identify a place in a program. Separate run and call identities identify an execution. Oscillatory phase is never the sole chain identity.
- A valid trace is necessary but not sufficient: correctness also requires the expected dependency graph, bindings, and actual native output bytes.

See `VISION_REQUIREMENTS.md` for the full endpoint and open requirements. A small successful experiment must not be relabeled as completion of that endpoint.

