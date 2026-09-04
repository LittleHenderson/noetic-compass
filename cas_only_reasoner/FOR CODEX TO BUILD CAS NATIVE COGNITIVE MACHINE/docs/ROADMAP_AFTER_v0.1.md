# Roadmap After v0.1

> Historical kernel roadmap. The authoritative current delivery order is in
> `docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md`, which incorporates the complete
> 14,616-line source, CAS-Math, the neural cortex, retrieval, training,
> verifier-federation, Foundry A-F, causal-ablation, and integrated-v1 gates.

This roadmap preserves v0.1 as a frozen reference baseline. Work should proceed by versioned contracts and failing tests first. It must not silently assign meanings to `OPEN-SEMANTICS` items or expand runtime authority.

## Milestone 0 — Freeze and reproducibility

Goal: make the present demonstrator independently reproducible before adding capability.

- Pin a development/test environment separately from the dependency-free runtime.
- Add Draft 2020-12 metaschema validation using a pinned validator.
- Preserve all eight fixture outputs and `golden/manifest.json` receipts.
- Add a machine-readable build/test receipt with Python/platform/source revision and schema/golden digests.
- Exercise the suite on supported operating systems.

Exit: clean checkout commands reproduce exact goldens and current tests without undocumented setup.

## Milestone 1 — Close external-source trust blockers

Goal: authenticate the sources that are currently accepted as caller-supplied symbolic premises. v0.1 already prevents hypothetical-only chains from becoming authoritative support.

### 1.1 Conditional evidence semantics

- Preserve the v0.1 iterative authoritative-support graph as the unconditional baseline.
- Define a separate representation for conditional conclusions if they are wanted.
- Never weaken the current rule that hypothetical-only queries, constraints, and proof chains cannot commit.
- Add explicit conditional-query fixtures only after that representation is frozen.

### 1.2 Rule-source authority

- Define versioned rule packages and an authenticated admission policy.
- Keep structural proof reconstruction separate from source trust.
- Bind rule-package revision/digest into problem, run, trace, and evidence identity.
- Reject provenance strings that merely claim verification.

### 1.3 Episodic import authority

- Define a durable-record envelope, signature/MAC or trusted-store receipt, schema version, ontology/runtime bindings, and revocation policy.
- Define an explicit versioned restore API; keep current public nonempty injection rejected until that gate exists.
- Treat `verified=True` as an internal disposition, never as standalone authentication.
- Add tampered, cross-policy, stale, and revoked-record tests.

Exit: caller-invented provenance and unauthenticated durable episodes cannot become trusted external evidence; any future conditional result remains visibly conditional.

## Milestone 2 — Self-contained verification and replay

Goal: make retained receipts sufficient for independent deterministic checking.

- Define a versioned run bundle that includes or content-addresses the canonical problem and exact initial episodic snapshot.
- Bind memory snapshot digest and policy revision into summary/evidence.
- Extend verification to reconstruct proof, comparison, RPM, commitment, and learning semantics, not only hashes/bindings.
- Add streamed/large-receipt limits and fail-closed parsing.
- Preserve the existing compact bundle as a compatibility profile if useful.

Exit: a verifier with no hidden process state can replay a warm run exactly or report the missing content address.

## Milestone 3 — Complete bounded runtime behaviors

Goal: deepen the typed symbolic machine without widening ontology claims.

- Add property/fuzz tests for packets, intents, substitutions, chains, hashes, and budget edges.
- Cover every terminal status, rejection reason, intent type, and authorized issuer/capability pair.
- Specify and test nested RPM child scheduling, multi-level returns, failure propagation, and depth/cycle limits.
- Define exact semantics for `NEEDS_CAPABILITY`, `DEADLOCK`, and every currently reachable/unreachable halt path.
- Decide whether working memory should mirror committed branch propositions or remain input-only.
- Add maximum packet, trace, proof, and artifact-size contracts. Preserve the already enforced one-shot decomposition-state comparison, report, selection, commitment, per-run episode write, and duplicate-ID rules.

Exit: each closed enum path is either demonstrably reachable/tested or explicitly reserved and rejected.

## Milestone 4 — Native association and planning

Goal: implement a bounded `^8` candidate generator without granting it truth authority.

- Freeze allowed candidate templates and their provenance.
- Generate finite candidate specs under explicit branch/tick budgets.
- Keep generated facts hypothetical until admitted proof supports them.
- Add coverage/diversity criteria that do not become truth criteria.
- Prove deterministic ordering and single-path justification.

Exit: native candidates are reproducible, bounded, branch-isolated, and cannot bypass proof or commitment gates.

## Milestone 5 — Ontology work, separately governed

Goal: close charter ontology gaps only from separately approved canonical sources.

Do not begin executable lowering until versioned decisions exist for:

- seven Foundation meanings;
- 28 Sub-Foundation meanings;
- Foundation-to-Drive adapter;
- D/W/P definitions, evidence, sufficiency, and authority;
- Noetics `^0`-`^5` and `^7`;
- register-transfer semantics;
- substantive P/C/E/O evaluation.

Each decision needs namespace-safe schemas, operational semantics, counterexamples, authority rules, and positive/negative conformance fixtures. No default mapping from `TF1`-`TF7` to `F1`-`F7` is allowed.

Exit: every formerly open item is closed by a reviewed versioned ontology—not an implementation guess.

## Milestone 6 — Source compiler

Goal: compile one frozen symbolic source language to the typed packet boundary.

Current progress: the controlled-English conversation facade implements one deliberately small deterministic lowering path with fail-closed grammar, provenance, exact packet output, evidence verification, and exact same-packet second-execution parity. That parity does not validate the language interpretation. This milestone remains incomplete because it lacks an independent semantic oracle, authenticated rule packages, source maps, round-trip coverage, general symbolic syntax, or CCDL.

- Start with a small formal grammar, not raw English.
- Produce deterministic canonical packets and source maps.
- Reject open/unsupported constructs with typed diagnostics.
- Authenticate rule and ontology packages.
- Keep compiler acceptance separate from runtime intent authority.
- Add differential and round-trip fixtures.

Full CCDL should be a later compatibility project after a shared grammar/semantics version exists.

Exit: source-to-packet lowering is deterministic, traceable, and cannot expand runtime authority.

## Milestone 7 — Board ontology before web-workbench implementation

Goal: convert the appended CAS Foundry/Cognitive Board Studio/CADA concept into a reviewable contract before any application build.

- Freeze canonical Board, node, edge, port, capability, execution, layout, collaboration, registry, and publishing objects.
- Separate inert visual/editor metadata from any content that can lower into `cncm.problem/*`.
- Define permissions, tenancy, revision identity, conflict behavior, import/export, and provenance.
- Specify deterministic compiler/runtime boundaries and negative cases where a board must not gain proof or mutation authority.
- Build no canvas, editor, collaboration server, or registry until this versioned Board Ontology/Capability Specification is accepted.

Exit: a board document can be validated and its authority boundaries reviewed without relying on a web implementation.

## Milestone 8 — Freeze CRQS before qualification tooling

Goal: turn the CRQS qualification-bench appendix into an auditable standard without retroactively grading v0.1.

- Freeze versioned task-manifest and capability-report schemas.
- Define the nine difficulty axes, `D0`-`D10` banding, hard-floor precedence, missing-data behavior, and scorer calibration.
- Keep Design Ceiling, Peak Demonstration, Stable Demonstration, and Qualified Level distinct; topology alone cannot earn a capability grade.
- Define reproducible measurements and uncertainty for every Capability Vector dimension. Do not create a qualification level from one average score.
- Define cumulative `CAS-G` gates, critical-failure blocking, abstention, precision/coverage pairing, protected regression, held-out splits, contamination controls, and causal ablations.
- Define exact evidence prerequisites for each `E-Tier`, including evaluator and implementation independence where claimed.
- Keep `A-Level` under a separate authority policy. A qualification evaluator may report an existing grant but must not create, widen, or infer one from capability or evidence.
- Specify `RMB` only as a separate matched benchmark with identical task, representation, tools, budgets, memory, randomness, and scoring conditions.
- Freeze failure-localization and repair ontologies. A recommended board patch is advisory and cannot compile, mutate, promote, or act without the ordinary authority path.
- Keep protected fixtures, proof checker, trace verifier, authority tests, and promotion thresholds outside the mutation authority of the board being judged.
- Do not translate current v0.1 tests, fixtures, traces, evidence packets, or goldens into CRQS results. Re-evaluate the runtime only after a frozen CRQS suite explicitly admits it as a subject.

Exit: an independent evaluator can reproduce or reject a bounded versioned report without trusting topology, aggregate averages, or self-authored evidence. This exit creates evaluation mechanics only; no implementation earns a grade until it actually passes that frozen evaluation.

## Milestone 9 — Persistence and operational hardening

Goal: only after semantic/trust correctness, evaluate a service-grade host.

- Atomic durable episode store and migrations.
- Access control, key management, audit retention, backup/restore, and crash recovery.
- Resource quotas, input-size limits, denial-of-service tests, observability, and failure injection.
- Platform packaging, SBOM, dependency scanning, and reproducible builds.
- Independent threat model and security review.
- Performance and reliability targets with measured receipts.

Exit: readiness remains an evidence-based separate decision. Completing features does not itself establish production readiness.

## Not authorized by this roadmap

This roadmap does not itself authorize the proposed web workbench, CRQS qualification bench, repair engine, grading claim, external actions, autonomous long-term goals, online constitutional/procedural self-modification, recursive code rewriting, neural/LLM truth authority, CAS-Ohm authority, AGI claims, consciousness claims, or use of the protected sibling worktree. Any such change would require an explicit new authority contract and risk review, not an implementation shortcut.
