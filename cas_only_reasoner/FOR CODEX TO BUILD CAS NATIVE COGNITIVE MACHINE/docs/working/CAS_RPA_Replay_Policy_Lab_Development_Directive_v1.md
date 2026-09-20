# CAS-RPA Replay Policy Lab
## Multi-agent development directive v1.0

**Project:** CAS-RPA / CNCM, with CAS PCBA and optional TypeSafe Jev extensions  
**Prepared for:** Little Henderson and the implementing AI-agent team  
**Date:** 19 September 2026  
**Status:** Implementation directive and proposed acceptance contract. Not an implemented system, a completed audit, or a performance result.

> **Mission:** Build the software that turns recorded investigations into restricted replay environments, tests better exploration policies, validates them on fresh work, and makes the entire process navigable through CAS-RPA. Preserve the existing machine. Deliver an operational vertical slice, not just another design document.

> **Adaptive execution mandate:** This plan is a starting design, not a claim of complete foresight. You are expected to discover missing requirements, identify mistaken assumptions, invent solutions, and improvise when real code, data, mathematics, or experiments require it. Preserve the objective and evidence standards; change the mechanism when justified. Do not manufacture success by weakening the test.

### Start here

The coordinator reads this directive, `WORK_ITEMS.json`, and `agent_prompts/A0_COORDINATOR.md`. Establish the actual source baseline before assigning implementation ownership. Execute the core work through a reproducible local demonstration and independent acceptance. Do not stop after inventory unless a concrete blocker prevents all authorized work. Treat optional provider access and paid compute as separate permissions, not assumed prerequisites.

The proposed product is an **engineering workbench with Explore, Replay, and Learn modes**. The first release is a local research product. It is not a production autonomous service and not a claim of broad self-improvement.

## 1. Source basis and interpretation

The supplied Dream-RSI paper describes online exploration, construction of replay worlds from recorded discovery trees, and policy improvement using those worlds. Its discovery model, evaluator, and execution interfaces stay fixed while exploration-policy code changes. [S1, §3, pp. 4–6]

The supplied CAS-RPA project-fit report describes a bounded read-only view of semantically replayed native evidence. It distinguishes parts, refinements, transitions, present state, inspection focus, and hypotheses. It does not establish a policy-learning system. [S2]

The CAS-RPA mathematical review preserves the distinctions among profile coordinates, state identity, reachability, common-intersection evidence, and authority. It does not validate measured CAS profile assignment or improved search. [S3]

The earlier TypeSafe/CAS PCBA integration report proposes an optional probabilistic judgment service and diagnostic channels. It is a recovered design synthesis, not an implementation baseline or a substitute for primary CAS component specifications. Its proposed use of uppercase “JEV” is not adopted as an established user protocol here: **Jev** names the provider model; the new local records are called the **evidence ledger**. [S4]

The official Dream-RSI repository currently lists its full codebase and reproduction scripts as being prepared. Recheck availability and licensing during inventory, but do not block this project waiting for upstream code. Implement a clearly attributed adaptation of the published ideas when reuse is unavailable. Do not describe that adaptation as an exact reproduction. [S5]

**Interpretation rule:** Statements labeled “source basis” report the supplied materials. Requirements, phases, identifiers, APIs, metrics, and numerical defaults below are proposed engineering decisions for this build. They are not attributed to the paper as existing features.

### Historical checkpoints, not current HEAD

`83322e8f` identifies the previously discussed RPA checkpoint. `9597840c` identifies the previously discussed compound-procedure checkpoint. They are useful historical anchors only. No current repository inspection was performed to author this directive. Agents must discover the actual checkout, branch, runtime, source contracts, and existing successors before adding code. The older 420-candidate arithmetic construction is a fixture opportunity, not the definition of current machine capability. [S2; S4]

## 2. Product outcome and scope

### Required user journey

A user opens a task, inspects its actual state and evidence, enters a subproblem or procedure, and sees its constituent records. The user opens Replay Lab, compares two policies against the same supported recorded world, and sees which decisions used which observations. The system evaluates a candidate policy on fresh isolated work, retains the evaluation, and either qualifies it for a later authorized episode or keeps the incumbent.

The user can answer: **What happened? What was known then? What did the policy choose? What did it cost? What could not be replayed? Did the candidate help on new work?**

### Core release

Build native journal adapters, immutable world records, a prefix-only simulator, policy interfaces, at least three baselines, bounded policy improvement, independent evaluation, fresh local execution, recovery, controlled policy activation/rollback, and a genuinely recursive atlas interface.

### Extension releases

Add source-supported CAS PCBA diagnostics, optional Jev ranking, learned-composite reuse, and broader task families as separately measured extensions. Their absence must not prevent the core replay lab from functioning.

### Explicit exclusions from this first program

Do not replace CNCM with CAS Harness. Do not rewrite the protected kernel, verifier, authority constitution, or historical evidence to make this integration easier. Do not introduce world-fact claims from model confidence. Do not claim infinite enumeration, quantum behavior, a full sheaf, or measured cognitive geometry. Do not deploy externally, purchase services, launch cloud/GPU jobs, or enable real-world actuation merely because this document authorizes local development.

## 3. Agent team and collaboration contract

Use these roles even if the platform provides fewer agents. A smaller team may perform roles sequentially, but independent review and test custody must remain separate from policy development.

| Agent | Owns | Must not own |
|---|---|---|
| **A0 Coordinator / integrator** | Baseline discovery, scope, contracts, dependency order, integration, decisions | Unilateral relaxation of protected acceptance requirements |
| **A1 Native adapter / evidence engineer** | Runtime adapters, source binding, world materialization, lineage | Search-policy optimization or hidden-test tuning |
| **A2 Replay / isolation engineer** | Simulator, legal frontier, observations, budget enforcement, policy isolation | Native semantic writes or test-outcome disclosure |
| **A3 Exploration-policy engineer** | Baselines, policy candidates, bounded improvement search, development analysis | Sealed tests, evaluators, source journals, promotion approval |
| **A4 Evaluation custodian** | Dataset split, independent oracle, preregistration, sealed evaluation, statistics | Editing candidate policies or giving hidden examples to A3 |
| **A5 Atlas product engineer** | Recursive navigation, Explore/Replay/Learn views, accessible inspection | Direct kernel writes or using UI geometry as policy evidence |
| **A6 CAS integration researcher** | PCBA diagnostic adapter; optional Jev; component-reuse experiments | Inventing CAS mappings or promoting provider judgments to proof |
| **A7 Adversarial QA / release auditor** | Leakage tests, fault injection, independent acceptance, release integrity | Self-approving implementation changes without review |

### Working rules

Each work item has one owner, named reviewer, declared write paths, entry conditions, exit tests, and evidence outputs. Use isolated worktrees or equivalent workspace isolation. A0 is the integration writer for shared schemas and common APIs. Parallel edits to those files require an explicit ownership transfer.

At each handoff, record the base revision, changed files, source/profile identifiers, commands, actual exit codes, failed cases, remaining assumptions, and next dependency. Store these in `HANDOFF` records rather than relying on conversation memory. Never call work “done” because a collaborator said tests passed.

A4 must hold sealed test records in a separate filesystem/process boundary inaccessible to A3. Agent-role names in a shared prompt are not access control. If the platform cannot maintain isolation, report `CUSTODY_LIMITED` and do not make protected held-out claims.

Use a bounded shared run ledger and explicit leases for file ownership. Do not run many redundant suites concurrently or create unbounded agent recursion. The coordinator resolves code conflicts before integration; agents do not overwrite one another’s evidence.

## 4. Wave 0: discover and preserve the real project

**Owner:** A0 with A1 and A7. **Gate G0:** Source and permission baseline accepted.

Inspect repository guidance, `AGENTS.md`, applicable `GOAL` files, manifests, test runners, dependency locks, current experiments, and canonical requirement ledgers. Run read-only status checks such as `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git diff --stat`, and `git worktree list` where Git is the actual source-control system.

Locate the active CNCM homebase. Keep new native work inside `FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE` unless the current authoritative layout directs otherwise. Treat `CAS_RRK_v0.1`, protected sibling implementations, production Harness services, and prior acceptance packets as protected. If guidance conflicts, preserve all affected work, document the conflict, and continue independent safe work while the conflict is resolved.

Resolve the actual semantic writer. If the installed architecture identifies `NetworkAtomicCoordinator` as the sole writer, bind to it. If another version names a different coordinator, record the verified mapping. Do not assume a class exists because it appears in an old discussion.

Create `SOURCE_BASELINE.json`, `CURRENT_CAPABILITY_MAP.md`, `PROTECTED_PATHS.json`, `PERMISSION_BUDGET.json`, and `ASSUMPTIONS.md`. Record branch, commit, dirty-file inventory, runtime entry points, legacy adapter versions, schemas, deterministic replay contracts, supported task families, evaluation entry points, and current source hashes. Preserve user edits. Do not reset, clean, force-push, overwrite an existing run directory, or rewrite history.

Run the existing required baseline suite once under the discovered test policy. Keep exact counts and failures. A pre-existing failure may be recorded and isolated only with independent review; it is not permission to ignore a related regression. Do not compare current counts against historical counts as though test counts were capability scores.

**Permission default:** Use the already authorized development environment for bounded symbolic execution and local tests. New external-model usage, paid services, credentials, public publication, or cloud resources require their actual permissions and caps. Missing optional credentials do not block offline development.

## 5. Non-negotiable architecture contracts

### Authority and state

Keep four distinct concepts:

1. **Actual state:** the authoritative retained/live runtime state.
2. **Inspection focus:** the record or local scope the user is viewing.
3. **Replay state:** the observations and budget of one simulated policy run.
4. **Hypothesis:** a proposed action, interpretation, or outcome not yet observed and accepted.

Changing focus changes no native state. Replay reveals recorded observations into a separate replay ledger, not into native memory. A policy recommends legal actions; only the existing authorized executor/coordinator can produce native changes. A policy activation is an explicit, versioned event at an episode boundary, never a side effect of opening a visualization.

### Two replay modes

**Integrity replay** reconstructs the actual accepted history using the runtime’s trusted source inputs. **Exploration replay** evaluates a different investigation strategy over supported recorded opportunities. Exploration replay cannot create an integrity receipt for a history that did not occur.

### Typed structure

Keep `contains_part`, `refines_state`, and `reachable_via` distinct. Add separate, versioned relations for execution prerequisites, derivation context, policy decisions, evaluations, and artifact reuse where needed. A procedure’s composition is not automatically a schedule. A visually shared petal is not an overlap certificate. Genuine containment remains acyclic; feedback and references receive their own link types. [S2; S3]

### Learning and evidence

Freeze the discovery executor, correctness checker, task contract, and permitted skill library within each matched policy comparison. A3 may change policy artifacts, not the task solver or evaluator under test. Describe external-agent-authored candidates as model-assisted policy improvement. Do not claim native CNCM learned to author policies until that mechanism is independently demonstrated. [S1, p. 4]

A hash establishes byte identity under its stated assumptions, not author identity or factual truth. Preserve source labels and conditional arithmetic. Keep policy evidence, runtime proof, source attestation, and physical instrument evidence separate.

## 6. Source-to-build differences that must be explicit

The main paper selects the root or a revealed leaf, with the root opening the earliest unrevealed recorded branch. Appendix B describes a broader interface with identifiable unopened roots, branch metadata, and grid planning. These must not become one undocumented action model. [S1, pp. 5–6, 20–23]

Implement a small **`paper_tree_v1` conformance mode** following the main-text rule, then a separately versioned **`cas_catalog_v1` mode** only when candidate identities and features are genuinely available before execution. Declare the supported graph model in every world.

The main paper’s best-quality minus work plus parallelism score differs from Appendix B’s attainment-curve objective. Choose a local objective below and version it. An optional paper-score calculator must be labeled as such and never silently substituted into local promotion. [S1, p. 6 and p. 19]

The main-text revision indexing also warrants an explicit local convention: **M means the total number of evaluated policies including the incumbent**; there are M−1 proposed revisions. Bound the outer loop separately. Do not inherit an off-by-one policy-evaluation budget.

The paper’s prompt-level historical guidance ablation reports worse results on its ConvDiv experiment. Do not turn that into a universal rule, but include “history summary only” as an optional control rather than assuming more narrative guidance always helps. [S1, §5.1, p. 11]

## 7. Domain records and interface contract

All names in this section are **proposed interfaces to implement or map**, not claims about existing APIs. Favor adapters to existing immutable models over parallel replacements. Pin schema versions and canonicalization rules. Reject non-finite values, ambiguous duplicate keys, invalid IDs, and out-of-range counts at ingress. Preserve exact arithmetic values using the project’s approved rational representation.

| Record | Minimum information |
|---|---|
| **WorldManifest** | Schema; runtime/source hashes; graph mode; task family; evaluator; initial skill-library and memory/source versions; producer policy; budget model; context policy; split assignment; artifact references; completeness/support declaration |
| **AttemptRecord** | Attempt ID; primary workspace parent; all prerequisite/context references; candidate/program hash; pre-state and input identities; raw evaluation reference; normalized result; status; represented cost; actual telemetry; information-availability metadata |
| **PrefixSnapshot** | Prefix-safe task description; revealed observations; legal actions; explicit known budget; worker cap; allowed features; public policy-state version; observation sequence |
| **DecisionRecord** | Policy artifact/config; prefix digest held by the trusted recorder; selected batch or stop; reason codes; referenced visible evidence; resource reservation; rejection/acceptance result |
| **PolicyArtifact** | Code or restricted-policy representation; parent version; parameters; source of proposal; development-world versions; interface contract; tests; content digest |
| **ReplayReceipt** | World; policy; seed where applicable; decisions; revealed sequence; represented cost; replay CPU/wall cost; support events; termination reason; ledger digest |
| **PromotionRecord** | Candidate/incumbent identities; compatibility contract; engineering gates; validation and fresh-run evidence; uncertainty; actual authorization; activation boundary; rollback target |
| **ExternalJudgment** | Optional provider/model IDs; exact projected request; raw response hash; normalized typed output; time/version; purpose; expiry; admission result; separate usage accounting |

The private world identifier, full archive digest, hidden artifact paths, and final-source hashes should remain in the trusted recorder, not automatically in the policy’s observation. Otherwise an ostensibly prefix-only policy can memorize a world fingerprint. Use opaque episode-local action handles and record their private mapping outside policy custody.

### Minimal policy API

```text
policy.reset(public_episode_config)
policy.decide(prefix_snapshot) -> Decision

Decision = ProbeBatch(action_handles, reason_codes, visible_refs)
         | Stop(reason_code, visible_refs)
```

The controller validates the returned decision against the same pre-batch snapshot and reserves work before dispatch. The simulator, not the policy, reveals the results. No interface hands the candidate policy a native machine handle, hidden test directory, evaluator object, or complete world record.

## 8. World construction and support semantics

**Owner:** A1. **Gate G1:** Contract tests and source-bound materialization pass.

Materialize worlds only after the relevant native integrity replay succeeds. Preserve original records and append derived views. Bind each world to its exact task, inputs, runtime, programs, source chronology, environment, evaluator, producer context, and candidate-generation conditions. Include rejected and incomplete attempts with their real status and charges.

### Do not turn one chain into a fictional search tree

Many native traces record a sequence of necessary transactions, not independent research alternatives. Classify each imported edge. Separate administrative events from actual exploration opportunities. The existing arithmetic candidate catalog may provide a small search fixture, but one fixed template cannot establish broad search-policy transfer. If a trace does not contain supported alternative opportunities, deliver an integrity-only world and collect appropriate exploration records instead.

### Parent ancestry is not enough

Record three kinds of dependency: workspace ancestry, computational prerequisites, and information used to generate a candidate. Sibling reports, model prompts, remembered facts, and global history can matter even when a node has one workspace parent.

Each attempt receives one declared context class:

- **PARENT_LOCAL:** generation depends only on its declared parent-local information and pinned environment.
- **DECLARED_DEPENDENCIES:** additional revealed observations are required before that outcome is usable.
- **HISTORICAL_ONLY:** context dependence is not sufficiently known for alternate-order use.

Alternate-order replay may use the first two only when their conditions hold. A changed sibling history, memory correction, program version, or external environment can invalidate support. Return `OUT_OF_SUPPORT` rather than relabeling an unsupported outcome as a valid counterfactual. Historical-only records remain inspectable.

The paper reuses realized outcomes and explicitly generates no outcomes outside the recorded tree. Its online prompt also consumes available historical proposals. Therefore this context audit is an additional CAS fidelity requirement, not an asserted theorem from Dream-RSI. [S1, pp. 5–6, 18–19]

### No hidden completeness assumptions

Distinguish `RECORDED_END`, `OUT_OF_SUPPORT`, `NOT_YET_EXPLORED`, `BUDGET_EXHAUSTED`, `SOURCE_INVALID`, and `PROVED_UNSAT` where an actual proof exists. No recorded continuation is not proof of impossibility. Deferred UI pages are not search failures. A sampled world is not an exhaustive world.

## 9. Prefix-only replay and isolation

**Owner:** A2. **Gate G2:** Reference equivalence, information isolation, and legal-action tests pass.

Start a replay with only its permitted root observation and ex ante metadata. Reveal information only after the corresponding supported probe completes. Define availability per field; do not pass final status, future descendants, future scores, result-bearing filenames, or outcome-derived tags as “structural metadata.” Known candidate syntax may be available in catalog mode; it must have existed before execution and be supplied to all matched policies.

For `paper_tree_v1`, opening the root reveals the next recorded branch in creation order. Continuing a revealed leaf reveals its unique recorded continuation or an explicit recorded-end result. Do not expose how many future children are hidden unless the declared information contract makes that an ex ante known limit.

For `cas_catalog_v1`, legal actions are drawn from an actual available candidate catalog and all declared prerequisites must be satisfied. Maintain original identity privately while rekeying handles for tests. Do not flatten shared structures into disconnected trees or turn a containment edge into an execution edge.

A batch contains distinct actions legal before the batch begins. No parent/child or unresolved prerequisite pair may execute in the same batch. Reject conflicting write sets or other task-declared interference. Isolated worker results return to a deterministic coordinator order; a completed worker cannot independently commit native state.

### Enforce isolation, do not merely request it

Run policies in a process or equivalent enforced boundary with no network, credentials, hidden world mounts, native writer, repository evaluator sources, or unrelated filesystem access. Use bounded CPU/time/memory and a strict serialized protocol. Arbitrary Python in the simulator’s own process is not an acceptable hidden-data boundary. A constrained policy representation is preferable if the installed environment cannot safely isolate generated code.

### Essential noninterference test

Construct paired worlds whose permitted prefixes are byte-equivalent but whose hidden suffixes, winning IDs, outcomes, or archive layouts differ. Under the same permitted seed/configuration, the policy must return the same decision until an allowed distinguishing observation is revealed. Hold public metadata constant; test covert leakage through IDs, error messages, metadata, and paths. A7 independently implements these tests.

## 10. Resource model, concurrency, and recovery

Maintain separate ledgers for **represented discovery work**, **actual native execution work**, **policy-development and replay compute**, and **external-provider usage**. A replay probe can represent an expensive experiment while physically performing only a lookup. Both facts must be visible. Do not report a reduction in represented work as measured end-to-end latency or monetary savings. [S1, p. 6; S2]

Use finite configured limits for episodes, decisions, workers, probes, policy revisions, improvement cycles, wall time, memory, and artifact storage. When actual cost is unknown before a native call, reserve a declared bound and reconcile it using the task contract. Preserve started-work charges after failure or cancellation. No return from RPM or rollback refunds completed work by implication.

For offline timing simulation, use recorded durations only within a declared resource/contention model. Mark simulated makespan as simulated. Actual fresh-run timings remain separate. In matched tests, all arms receive the same worker cap and initial budgets.

### Transaction boundary

Use durable phases such as `DECISION_RECORDED`, `WORK_RESERVED`, `DISPATCH_RECORDED`, `RESULT_DURABLE`, `RESULT_CHECKED`, and `COMMIT_OR_REJECT`. Fit these to the installed runtime rather than adding an unauthorized second writer. Each operation has a stable idempotency identity. Recovery reconstructs accepted outcomes and remaining budgets from durable records; it must not blindly rerun an unknown-delivery operation.

Simulated replay recovery resumes the recorded reveal sequence without repeating policy side effects. Live recovery follows the existing runtime’s semantics. External calls, when authorized later, require attempt-level records: a re-query is a new event, not integrity replay. Exactly-once external execution is not assumed.

A7 must inject a process stop at every new durable transition boundary and selected in-flight worker conditions. Require a distinct recovery process. Test successful runs, expected refusals, partially completed batches, corrupted records, duplicated deliveries, and activation/rollback boundaries. Seal unresolved work explicitly; do not invent an outcome to complete the demo.

## 11. Policies, improvement, and experiment discipline

**Owner:** A3. **Independent evaluation:** A4. **Gate G3:** A real bounded improvement loop executes.

Implement these starting policies over the same API:

- **B0 Fixed:** the discovered native/reference ordering and a declared stop rule.
- **B1 History-aware heuristic:** a transparent hand-authored policy using permitted trajectory signals.
- **B2 Seeded shuffle:** a reproducible randomized control for catalog mode, only where actions are interchangeable and legal.
- **C Replay-improved:** a policy selected from bounded candidate revisions using development replay.

B2 is an explicit experimental extension, not the deterministic controller prescribed by the paper’s appendix. All policy state resets per replay. Record any permitted seed and do not allow hidden cross-world memory. Freeze parameters within an episode. The paper’s beta sweep may inspire a configurable exploration setting, but beta is not a required universal CAS quantity. [S1, pp. 20–23]

A3 can improve allocation among widening, deepening, repair, deferred branches, parallel batches, and stopping. Preserve earlier successful anchors after a failed refinement. Classify failure using evidence: missing prerequisite, repairable implementation issue, resource/domain refusal, insufficient information, or repeated valid lack of improvement. Soft deprioritization is not a permanent impossibility claim.

Begin with bounded changes to a small interpretable policy representation or parameterized controller. Expand to generated policy code only after isolation tests pass. No policy variant may edit scoring, reveal permissions, test data, resource meters, or promotion rules.

**Improvement-loop default:** incumbent plus at most seven revisions per cycle; at most three cycles in the initial development run. These are engineering budget defaults, not research results. A0 may revise them before the run in the resource manifest. A3 cannot enlarge them mid-run because a candidate is losing.

An external agent proposing better policies counts as external-agent-assisted improvement. Native procedure construction and native policy learning require their own artifacts and causal tests. Adding a better external model must never silently become the claimed benefit of CAS.

## 12. Evaluation contract and meaningful success

**Owner:** A4. **Gate G4:** Independent evaluation is complete and its outcome is reported honestly.

### Separate three questions

**Engineering correctness:** Does the implementation obey its contracts?  
**Replay screening:** Does a candidate perform better on supported stored worlds?  
**Fresh benefit:** Does it help on new actual work under matched conditions?

A candidate can pass the first two and fail the third. Preserve that result.

### Data and custody

Split by task family, structural template, context lineage, and related candidate programs, not just by random rows. Group descendants and near-duplicate worlds into one split. A3 sees development data and bounded development feedback. A4 uses validation to select one frozen finalist under a preregistered protocol, without disclosing hidden examples. Sealed final-test outcomes are read once for that protocol. Retuning after exposure requires a new test set and an explicit new experiment version.

Use at least 12 small synthetic worlds for unit coverage. A proposed pilot uses 30 development, 20 validation, and 100 test episodes only if genuinely distinct, eligible data can be collected affordably. These numbers are planning defaults, not an automatic adequacy claim. A4 must justify statistical power using pilot variance and clustered structure before the final test. If support is insufficient, mark `INCONCLUSIVE` or `DATA_LIMITED`; do not invent independence by cloning arithmetic coefficients.

Include cold-start and later-cycle conditions. No policy begins with secret successful history or a richer primitive library than its control. An optional “summary-only historical guidance” arm measures whether replay adds value over textual lessons alone. [S1, §5.1]

### Objective chosen for this build

For the first task family, **correctness is a gate, not a score bonus**. Predeclare a useful checked outcome and a fixed work budget B. Compare checked-success rate at B. Measure censored work-to-first-checked-success as actual represented work when success occurs and B otherwise. Show success rate alongside this censored measure so failure cannot look efficient through early stopping. Invalid or unexecuted outputs never earn quality credit.

A candidate is not promoted simply because it probes fewer nodes. For optimization tasks, introduce a separate, versioned quality-at-budget or attainment-curve objective with direction and normalization fixed from development information or an externally specified task contract. Hidden world maxima must not enter policy observations or stop rules.

Report represented probes, native instructions/checker calls, policy-development model calls, replay compute, actual fresh-run wall time, storage, provider usage, and failure counts separately. For multi-resource constraints, use explicit caps rather than an undocumented sum of incompatible units. Charge internal work when a composite procedure is called.

### Proposed promotion margin

Before sealed evaluation, A4 freezes one of two contracts: a useful success/quality improvement under the same budgets, or a work reduction with no material success degradation. Suggested pilot targets are a 10% work reduction and a 2-percentage-point noninferiority margin on success. They require appropriate uncertainty bounds and domain justification; they are not mandatory universal constants or guaranteed gains. Use paired, task-cluster-aware intervals. A7 verifies that the acceptance rule was frozen before the test.

### Do not overlook replay fidelity

Test supported identical-context execution against the recorded outcome. Classify order-sensitive or stochastic history as screening-only when exact alternate-order validity cannot be established. New online/local real executions are required before a fresh-benefit claim. A simulator score cannot supply outcomes for new branches.

## 13. Native deployment, policy registry, and rollback

**Owner:** A1 and A0; **review:** A7. **Gate G5:** Authorized fresh execution and registry lifecycle pass.

First deploy candidates in isolated shadow evaluation with no production authority. A qualifying policy may be activated for later local research episodes only through the approved registry/coordinator path. Freeze policy identity, runtime contract, skill library, evaluator, and permitted external inputs for each episode.

Activation checks all declared compatibility identities and the expected incumbent. Use an atomic compare-and-swap or the project’s existing equivalent. An in-flight episode retains its starting policy; new episodes may use the newly activated policy. Preserve the full decision and evaluation lineage.

Rollback changes the active policy head, not the historical record. It must leave failed candidates inspectable, prevent stale activation, and retain previous observations and charges. Test dependency revocation, mismatched skill-library versions, duplicated activation requests, replay after restart, and concurrent episode completion. A policy cannot self-promote or claim a larger budget.

If no candidate qualifies, ship the workbench with the incumbent and a visible `NO_BENEFIT_DETECTED` or `INCONCLUSIVE` result. This is a completed experiment, not a reason to fabricate a better policy.

## 14. Recursive atlas product requirements

**Owner:** A5. **Gate G6:** Functional recursive navigation and evidence parity pass.

### Explore mode

Show the actual state banner, task, caller, prerequisites, retained procedures, source versions, budget, and evidence. Entering a flower reveals its declared parts or refinements. Use breadcrumbs, a return-to-present control, expandable local neighborhoods, and shared canonical identity across context-specific views. Visual enlargement alone does not satisfy this requirement.

### Replay mode

Show policy versions A and B on the same world with step controls, observed prefix, chosen batch, rejected actions, represented cost, actual replay cost, and support status. Keep simulated state visibly distinct from the actual machine. A comparison should explain differences from logged visible evidence, not manufacture a free-form rationale afterward.

### Learn mode

Show incumbent, candidate lineage, development results, compatibility contract, validation/fresh-test outcomes, qualification status, and later deployment history. The viewer displays registry events but does not create authority merely by selecting a candidate. Any authorized activation control is a separate host action with an explicit action contract, not the legacy offline viewer acquiring silent write access.

### Interior objects

A world contains attempts and contexts. A policy contains source/configuration and evaluation records. A procedure contains call steps and bindings. A board view contains source-supported component probes. Keep time transitions, composition, shared identity, and evidence support visually distinct. Collapsed nodes retain child-failure counts and unresolved/deferred counts.

Both Graph and Flower views consume the same canonical projected records, filters, and display budgets. Count the root in the node budget. Label records omitted for paging. In policy-evaluation mode, the UI must not reveal hidden outcomes through previews, tooltips, searches, exports, or counts. Forensic full-history inspection runs separately and is unavailable to the policy agent.

Test keyboard navigation, readable labels, small-screen layout, focus persistence, duplicate shared views, stale cursors, large reports, and malicious text. Local research mode and standalone read-only exports have distinct network/content-security policies. Do not remove an old export’s restrictions to avoid implementing a proper new host boundary.

## 15. CAS PCBA and Jev extension contract

**Owner:** A6. These extensions are not on the core critical path.

For PCBA, locate the actual ratified component and board specifications first. Map supported CJT stages, prerequisite diagnostics, bias/gain observations, memory records, and fault reports using explicit units and scope. A1/A4 must establish whether each signal was available before the policy decision. Preserve child anomalies even if an aggregate looks nominal. No mapping is established merely because two concepts have similar names. [S2; S4]

Keep separate fields for CAS profile descriptors, diagnostic measurements, external probabilities, native work, and provider usage. Leave `profile40` unassigned until a measured assignment contract exists. Do not infer CAS-Ohm Drive, resistance, attention, or Foundation mappings from a ranking score. Typed atlas relationships are useful without activating unvalidated geometry. [S3; S4]

For Jev, use an optional advisor interface with an offline deterministic test double. Before real calls, recheck provider contracts, limits, model identity/pinning, privacy, storage, publication/training permissions, account authorization, and budgets. This directive makes no new claim about current provider limits. Jev ranks or classifies permitted candidates; it does not write policies, replace the correctness checker, or authorize a native action.

Use bounded prefix-safe projections. Archive raw responses separately from normalized outputs. Bind responses to request, source state, model, and purpose; reject stale or mismatched use. Re-querying a provider is not replay. Timeouts and outages preserve native behavior or an explicit unavailable status. Do not prune a candidate permanently solely on provider confidence.

Evaluate generic replay, replay plus PCBA diagnostics, replay plus Jev, and combined variants separately. Provide equal raw facts and account for extra computation. Where PCBA features are deterministic functions of available facts, supply a matched generic-feature control to distinguish a useful feature from a CAS-label effect. Provider-assisted gains are not evidence of native learning in its absence.

## 16. Development waves and executable deliverables

The following command names are **target CLI commands the team must implement**, not commands available in this handoff. Prefer a discovered existing runner when it provides the same contract, and record the mapping in `COMMAND_MAP.md`.

| Wave | Work and ownership | Required exit |
|---|---|---|
| **W0 / G0** | A0/A1/A7: baseline, permissions, source conflicts, path ownership | Source baseline and reproducible pre-change status |
| **W1 / G1** | A1/A2/A4: schemas, trust boundary, tiny worlds, independent reference semantics | Contract fixtures and information policy locked |
| **W2 / G2** | A1/A2/A5/A7: one native world, two policies, recursive view, recovery | End-to-end offline vertical slice with actual records |
| **W3 / G3** | A3/A4/A6: baselines, bounded revisions, split-aware evaluation, optional diagnostic stub | At least one complete improvement cycle with receipts |
| **W4 / G4–G5** | A0/A1/A4/A7: held-out evaluation, fresh local runs, activation/rollback | Engineering result and benefit result separately reported |
| **W5 / G6–G7** | A5/A7/A0: UX hardening, independent reproduction, release | Reproducible package, receipts, limitations, runbook |
| **W6 / extension** | A6/A3/A4: PCBA/Jev/compound reuse and broader tasks | Separate extension gates and comparisons |

### Target commands

```text
rpa-lab inspect --config project.json
rpa-lab import-world --source source.json --output NEW_DIRECTORY
rpa-lab validate-world --world WORLD_ID
rpa-lab replay --world WORLD_ID --policy POLICY_ID --budget-profile BUDGET_ID
rpa-lab improve --development MANIFEST_ID --config SEARCH_ID
rpa-lab evaluate --protocol PROTOCOL_ID --candidate POLICY_ID
rpa-lab run-fresh --protocol PROTOCOL_ID --candidate POLICY_ID
rpa-lab verify-recovery --run RUN_ID
rpa-lab export --run RUN_ID --format html
rpa-lab verify-release --manifest MANIFEST_PATH
```

Return structured output and nonzero exit codes for contract failures. A successful tool exit only means its declared operation succeeded. It does not imply a performance benefit. Do not create no-op commands that emit expected status strings without doing the work.

### Suggested new module boundaries

```text
<resolved CNCM homebase>/
  <approved successor area>/replay_lab/
    contracts/      adapters/       worlds/
    observation/    simulator/      policies/
    evaluation/     registry/       cli/
  docs/replay_lab/
  tests/replay_lab/
  records/replay_lab/<immutable_run_id>/
```

Paths are suggestions, to be reconciled with actual repository conventions. `evaluation` must not be importable by untrusted policy code. Keep sealed datasets out of the shared checkout even when evaluation code is public.

## 17. Acceptance vectors and stop conditions

`TEST_VECTORS.json` contains the test registry. Implement every core vector with an independent expected result. At minimum cover prefix noninterference, context mismatch, unsupported outcomes, wrong source/version, duplicate actions, batch dependency violation, budget overrun, failure charging, corrupted receipts, replay recovery, registry rollback, UI/source separation, and baseline parity.

Separate **construction tests** from **method-benefit tests**. A working simulator and passing schemas do not demonstrate a better exploration strategy. A favorable policy score does not demonstrate an uncompromised simulator.

Fail the relevant release gate on hidden-data leakage, unauthorized writes, incorrect result accepted as checked, source-history rewriting, secret exposure, or budget bypass. Repair and rerun the affected adversarial family. Do not suppress the test or rename the failure.

For flaky timing, isolate deterministic correctness from noisy performance measurement. Retain the first failure and any reruns. For sparse evidence, deliver the engineering result and a collection plan rather than forcing a statistical claim.

For a candidate policy with no gain, retain the incumbent. After a bounded set of unsuccessful approaches, record why they failed and change the hypothesis or mechanism. Do not keep spending on the same failed variant by merely increasing depth. A failed approach is not a mandate to abandon the goal.

## 18. X-factor protocol: authorized innovation and improvisation

Agents are explicitly expected to adapt. Use three change lanes:

**Lane A: local reversible change.** The work-item owner may adapt file layout, data plumbing, visualization technique, or a bounded algorithm behind a frozen interface. Record the assumption, proposed change, relevant tests, and reviewer. Continue without interrupting the owner for routine choices.

**Lane B: contract-affecting change.** A0 plus the independent reviewer approve a versioned change to action semantics, schemas, context eligibility, scoring, resource units, or experiment structure. Add migration/compatibility tests. Make objective or dataset changes before sealed evaluation. Do not rewrite historical receipts to match the new version.

**Lane C: permission or protected-core change.** Obtain explicit owner authorization for new paid/model/cloud usage outside existing caps, credentials, real-world side effects, external publication, destructive operations, or changes to protected authority/verifier contracts. Continue other authorized work in parallel.

### Required adaptation record

Use `templates/ADAPTATION_RECORD.md`. State: observed obstacle; evidence; which assumption failed; candidate alternatives; selected experiment; resource cap; expected result and falsifier; affected interfaces; change lane; reviewer/authorization; before/after identities; actual result; effect on claims and roadmap.

| X factor | Required response |
|---|---|
| Current code has a newer adapter or learner | Reuse/extend it after comparison; avoid duplicate architecture; update source map |
| Paper and appendix disagree | Implement a named contract; add conformance fixtures; disclose divergence |
| Upstream code unavailable or licensing unclear | Write an original local adaptation; preserve attribution; do not copy unlicensed code or wait indefinitely |
| Traces contain hidden sibling context | Add declared dependencies or historical-only eligibility; collect fresh parent-local records |
| Traces contain no alternative search choices | Deliver integrity view; add a real exploration recorder instead of fabricating branches |
| Single arithmetic template trivializes the test | Add structurally distinct supported tasks; retain simple template as a smoke fixture |
| Policy exploits IDs, source hashes, UI, or tags | Fix the information boundary; rekey; invalidate contaminated evaluations |
| New policy improves replay but loses online | Keep incumbent; investigate support mismatch; report the negative result |
| Novel algorithm beats the proposed heuristic | Retain it if independent tests support it; the plan does not require the original mechanism to win |
| PCBA signal cannot be sourced | Leave it absent; label any new diagnostic as experimental, not an established CAS quantity |
| Jev inaccessible, expensive, or unhelpful | Keep adapter optional and use native baseline; no provider dependency on core acceptance |
| Shared-parent DAG conflicts with tree rules | Preserve DAG in atlas; use a versioned action model and explicit dependencies for replay |
| Agent context window or coordination breaks down | Handoff from durable records; re-resolve ownership; never infer missing test outcomes |
| Existing tests fail before changes | Preserve baseline failure; scope independently; do not conceal newly introduced regressions |
| Insufficient independent data | Mark benefit inconclusive; ship functional workbench and bounded evidence honestly |

**The central rule:** You may invent a better implementation. You may not invent the evidence that it worked.

## 19. Definition of done and release contents

**Engineering acceptance** requires a source-bound end-to-end loop, enforced prefix isolation, legal and budgeted decisions, actual native checks on fresh work, recovery and rollback, recursive navigation, regression preservation, and independent reproduction.

**Benefit acceptance** additionally requires the preregistered held-out/fresh improvement criterion. Release these as separate status fields: `engineering_status` and `benefit_status`. Allowed benefit outcomes include `PASS`, `NO_BENEFIT_DETECTED`, `INCONCLUSIVE`, and `NOT_EVALUATED`. Broad cross-domain learning is not a permitted inference from a bounded pass.

Deliver source changes and exact revision references; install/run instructions; `COMMAND_MAP.md`; schemas; immutable world manifests; policy lineage; decision ledgers; development/validation/test split manifests with custody documentation; budget and cost reports; fault-injection results; raw test logs and machine-readable reports; UI exports/screenshots; adaptation and assumption records; outstanding issues; and a release manifest binding all retained artifacts by digest.

A7 reproduces the accepted path from a clean permitted workspace using the release instructions. Keep the incumbent and failed experiments. State explicitly which tests were independently rerun, which results came from stored receipts, which examples are synthetic, and which modules are still design-only.

Do not publish a commit, deploy a service, or upload private evidence externally unless that action is covered by the project’s actual authorization. The development directive authorizes planning and local implementation work, not blanket external distribution.

## 20. Coordinator kickoff order

Give the coordinator this instruction with the full package:

> Execute the CAS-RPA Replay Policy Lab directive. First discover and preserve the actual CNCM checkout, guidance, contracts, evidence, and resource permissions. Assign isolated work items with independent evaluation custody. Build the core native vertical slice before optional provider integrations. Implement integrity replay and exploration replay as separate mechanisms, enforce prefix-only observations, and deliver real recursive atlas navigation. Run bounded policy-improvement experiments and fresh native evaluation without changing the protected verifier or grading rules. Use the X-factor protocol to innovate when assumptions fail; do not stall on routine design choices or mistake this plan for a complete specification of reality. Continue through a reproducible engineering release and an honest benefit result. Report working artifacts, exact tests, failures, deviations, and unresolved dependencies. Do not claim the whole vision is complete because one fixture passes.

## 21. Sources and traceability

**S1.** Zheng et al., *Dream-RSI: Recursive Self-Improvement through Evolving Worlds*, supplied `2609.14858v1.pdf`, 36 pages, v1 dated 14 September 2026. Use §3 pp. 4–6 for the main replay loop; §5.1 p. 11 for the reported semantic-guidance ablation; Appendix B pp. 18–23 for agent prompts, prefix interface, failure handling, batches, beta, grid planning, and between-round feedback. Local source hash is in `SOURCE_REGISTER.json`. Paper: https://arxiv.org/abs/2609.14858

**S2.** Supplied `CAS_RPA_PROJECT_FIT(6).md`, “CAS-RPA: project fit and first prototype.” Basis for typed links, present/focus separation, native replay provenance, bounded expansion, and prototype limitations.

**S3.** Supplied `CAS_RPA_MATHEMATICAL_REVIEW(6).md`, review dated 16 September 2026. Basis for simplex/ALR distinctions, common-intersection obligations, compatibility limits, unknown/deferred semantics, and scale/authority separation.

**S4.** Supplied `CAS_RPA_TypeSafe_Jev_CAS_PCBA_Deep_Dive.md`, recovered research report. Secondary design input for optional external-judgment, diagnostic, learning, and interface experiments. Recovery explicitly did not re-audit its research; verify original technical/legal sources before relying on them for implementation or publication. Its own use of “current” is historical, not this directive’s claim about HEAD.

**S5.** Official Dream-RSI repository, reviewed 19 September 2026: https://github.com/zhengkid/Dream-RSI . Release-plan availability is a point-in-time statement, not a dependency guarantee.

**S6.** Direct user instruction in this conversation: prepare an executable team development directive and authorize innovation/improvisation for unforeseen factors. All newly specified roles, gates, metrics, interfaces, thresholds, and adaptation lanes are engineering proposals responsive to that instruction.

### Source-to-requirement map

| Source | Requirements informed |
|---|---|
| S1 §3 | World pool, policy/executor separation, prefix replay, fixed-policy episode, bounded offline revisions |
| S1 Appendix B | Trajectory-aware decisions, repair handling, legal batches, information limits, separate grid planning |
| S1 §5.1 | Optional summary-only guidance comparison, not an assumption that all semantic structure is harmful |
| S2 | Native replay before atlas, typed structure, exact identity, current/focus/hypothesis distinction |
| S3 | Coordinates not authority, common witnesses, no invented profiles, explicit unknown and finite support |
| S4 | Optional PCBA/Jev adapters, separate quantities, composite-reuse tests, evidence preservation |
| S6 | Action orientation, independent agent execution, X-factor adaptation mandate |

