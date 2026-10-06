# HELM — the destination, the gap, and the question every task must answer

**Status:** canonical. Every HELM directive points here; this file never points at a directive for its intent.
**Owner:** Little Henderson. Edits to §1 are the owner's alone. §4 (current state) is updated by whoever lands evidence, with the commit that landed it.
**Created:** 2026-10-06, from the owner's statement of intent and the lasting-memory directive of the same date.

This document grants no authority. Merge, run, budget, credential and outreach authority live in each directive and nowhere else.

---

## 1. The destination

HELM is one machine, built from the CAS / CJT / PCBA principles in this repository, that:

1. **Reasons** — a reasoning system built from CAS/CJT/PCBA components, with memory, goals, and checks on its own decisions.
2. **Learns** — learning that produces useful new abilities and applies them to unfamiliar problems.
3. **Retains** — retention through restart and later learning, without destroying earlier abilities.
4. **Improves itself** — improvement of its own tools, harness and neural structure, including adding useful neurons.
5. **CASalesces** — CASalescence at the neural-architecture level, toward models working as a genuinely combined system.
6. **Organizes what it holds** — an RPA (Recursive Possibility Atlas) organizing retained knowledge and possibilities, while keeping facts, guesses and separate contexts distinct.
7. **Is built together** — Codex, DeepSeek and Claude contributing to one coherent project, reusing existing work.

The destination is firm. The implementation is open to evidence: any design choice may be challenged and replaced when evidence shows it fails the gate in §3, and the challenge is recorded in the directive's amendment log (as the Revision Streams contract does in its §12). What may not move is §1.

## 2. How this project tells preparation from progress

A small demonstration must never become the finish line by accident. Three rules keep that from happening.

**Preparation is not behavior.** Builds, reviews, clean runs, serialization checks and passing software tests establish *readiness* for an experiment. They are reported as preparation. Only an observed, pre-declared behavior on a frozen input counts as progress on an ability.

**Four outcome types, never conflated** (from the 2026-10-06 directive):

| outcome | what must be shown | what does not count |
|---|---|---|
| **Retention** | an accepted correction or lesson still changes a relevant answer after intervening sessions and a fresh-process restart, without being taught again | a saved file, a deserialized object, a same-process reload |
| **Reasoning and transfer** | a retained rule or recipe helps solve new supported cases or compositions, measured against an untaught control | exact-answer lookup |
| **Cooperation** | independently developed components exchange a correctly interpreted lesson or state and produce a behavior neither showed alone | a field-name match between schemas |
| **Neural growth** | a separate neural-state experiment with functional improvement and controls, with retrieval disabled as well as enabled | more files, branches, nodes or saved objects |

**Claims are bounded by the control that lacks the mechanism.** "Load-bearing" is said only as "relative to the solver that lacks it". "Necessary" and "superior" are not said. A single counterexample blocks the affected claim until it is fixed on development data and re-run on held-out data; failed examples are never edited out of a report. A measured zero is reported as zero.

## 3. The gate: the question every task answers before it starts

> **Which HELM ability does this advance, and what observable behavior will prove it?**

An acceptable answer has five parts and fits in a paragraph:

1. the ability by number from §1;
2. the observable behavior, as a before/after on a named input;
3. the control that lacks the mechanism, so the behavior can be attributed;
4. the pass criterion, frozen before the run, and the denominator it is counted over;
5. what the result will **not** show, in one sentence.

A task that cannot answer all five is preparation. Preparation is allowed and often necessary; it is labelled as such in its directive and its CHANGELOG entry, so it is never later mistaken for progress.

Worked answer for the earlier workspace experiment (PR #248, historical head `17dbe73`, base `4377a7d`; PR #248 is open and unmerged as of 2026-10-06): *Ability 1 and the ground of 3. The behavior: an organism that holds conclusions across questions agrees with recompute-from-scratch on every probe of a generated event stream in both world modes, and withdraws a held conclusion when its support is retracted or denied. Control: the two-set replayer `ctl_recompute`, correct by construction, and seven ablations each removing one workspace rule. Criterion: 100% agreement on verdict, contested keys and lacuna bounds over 89 probes per world, zero heartbeat faults; each ablation failing only inside its class. What it does not show: memory across items, survival of a process restart, or that truth maintenance is necessary — the replayer is also 100%.*

## 4. Where we are, ability by ability

Updated with each landed piece of evidence. Entries cite the commit or document that carries the evidence; anything not verified in this repository says so.

| # | ability | demonstrated (bounded) | required for the ability | the gap |
|---|---|---|---|---|
| 1 | Reasons | A processor built from CAS components reasons natively with no model in the loop: `^8` associates, `^6` decomposes at unity gain, `^9` lands; ten capabilities tested with the cord severed (PR #227). An organism over a living workspace holds, reuses and withdraws conclusions and converges with the recompute oracle on generated streams (PR #248). Motivation changes what is asked and never what is answered; the heartbeat audits standing beliefs. | Goals that choose problems, not only questions; checks on decisions that cover actions, not only verdicts; reasoning over open English rather than a five-production grammar. | Problems arrive already encoded; the encoder is five productions with total rejection. The initial workspace experiment was per item; the history layer now supports bounded multi-session replay (ability 3 row). No decision beyond a verdict is yet checked. |
| 2 | Learns | **Symbolic, development data (2026-10-06, contract §13, `docs/working/helm_lessons_evaluation_2026_10_06.md`):** a told, retractable rule ("relation r entails leads_to") that the organism could not apply before; after it is accepted the same ask answers YES, a never-seen instance taught two fresh processes later answers YES, the untaught twin stays GAP, retraction withdraws exactly what rested on it before and after restart. Hand-built end-to-end stream: oracle, control and organism agree in both worlds (9 tests); generator class L, seven variants, 42 tests; fault schedule with lessons on 10 development seeds 70/70. The first-look run on 20 unseen seeds is in progress at the time of writing and is reported in that note when complete. **Neural change: none** — the lesson is a row in the history document; no parameter exists to change. The directive's evidence register reports a bounded Codex correction (10→9) and reuse of a two-call solver in a fresh process, and DeepSeek guarded rule and math repair with grammar-lesson intake; those are recorded there, not verified in this session. LEARN in the processor writes one experience cell at low gain. | A taught lesson that helps solve a new supported case or composition, compared against an untaught control; for the neural form, the stages of the 2026-10-06 neural-learning directive. | The lesson is told, not induced; one lesson kind; no custodian. Neural learning: nothing in this repository; the R7/R8/R8B record (§7.4) shows a measured obstacle and a failed official R8, with the R8B outcome's custody unresolved. |
| 3 | Retains | Held beliefs survive across questions within one item and one process (PR #248). **Survival level (a), development data:** a taught fact changes a later answer, the accepted state is saved, a fresh operating-system process restores it and answers from the record without reteaching, a retraction or denial in the new process withdraws every dependent, and the same holds after a further restart; the restored stream agrees with the recompute control on every recorded ask (`scripts/cas_rpu/history.py`, `test_cas_rpu_memory.py`). **Multi-session first-look run (2026-10-06, `docs/working/helm_multi_session_evaluation_2026_10_06.md`):** 20 seeds the builder had not generated before × 5 successive fresh processes × 4 paths × 2 worlds (1200 process launches: 40 streams × 5 sessions × 3 subprocess paths × 2 worlds; the recompute control runs in process): 3280/3280 verdicts per path per world; 180/180 cross-session retention probes, 40 of them served from the held record with 0 stale hits; corrections and retractions withdrawn exactly (800/800) across restarts; the G-probe guess never promoted; 540/540 untaught twins GAP; T-compose answered by reasoning (0 record hits) while T-exact was served from the record (20/20). Fault schedule on 20 development seeds: every recovery ended exactly at the acknowledged prefix or one ahead with the retry recognised; history lost beyond retention is refused and named (E-MEM-046), never silently served. Still not the frozen result: no custodian, same builder, level (b) not demonstrated. | An accepted fact or correction that still changes a relevant answer after intervening sessions and a fresh operating-system process, without being retaught; dependents of a retraction change correctly before and after restart; no stale answer escapes through a faster path. | Level (b), survival of machine replacement: the mirror-and-restore mechanism is proven offline (three fresh processes, each machine's state destroyed, restore from the second location alone) and the S3 client is written and verified against AWS's published signing example; the live run against the dedicated location is blocked only by a valid key (the sandbox's was rejected, `InvalidAccessKeyId`). No frozen held-out run yet. `Workspace.snapshot` remains an inspection summary; the history document is the checkpoint. The CAS memory substrate design (`docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md`) is a proposal. The 2026-10-06 directive defines this gap and the order of work to close it: reuse audit, versioned contract, durability, guarded answer reuse, held-out multi-session evaluation. |
| 4 | Improves itself | Nothing. Every change to tools, harness and structure so far was made by a person or a delegated agent, not by the machine. | A measured improvement to its own tooling or structure, chosen and verified by the machine against a frozen criterion, with rollback. | Not started. Parked until 2 and 3 have demonstrated behavior, since self-improvement without retention is lost on restart. |
| 5 | CASalesces | Nothing at the neural-architecture level. The CAS-native model work (`cas-native/`) is training infrastructure with its own checkpoints; the processor and organism are symbolic. | Models working as a combined system with a measured functional gain over the parts, and a separation of retrieval assistance from parameter retention. | Not started. Requires the neural-growth protocol of §2 and a frozen baseline. |
| 6 | Organizes with RPA | An RPA model, recorded-run adapter and native adapter exist on branch `codex/helm-rpa-recorded-run-20260922` at `eb99855`, separating current state from inspection focus and hypothesis branches; the recorded adapter labels its view as an archived record, not live HELM. Not on `master`. **2026-10-06:** the organism's workspace projects into a valid atlas (`scripts/cas_memory/rpa_adapter.py`) and the atlas narrows record-first lookups; the loaded files are pinned by content to `eb99855` and CI mounts that commit so the RPA tests run rather than skip; the narrower is reconnected on restore and shown working after a restart. Measured on the multi-session first-look run: identical answers on every probe; 40 of 279 record hits sent to the walk (a held conclusion later restated as a given, which the atlas rates OBSERVED, not VERIFIED); restore time roughly doubled. No answer changed, no stale hit removed — the simpler dependency-checked path is the working path (owner decision), the RPA path the comparison. | RPA as a read-only index over the accepted event history that locates records and shows branches, rebuilt only after authoritative restore validation, never promoting a possibility to a fact, and shown to add value over an ordinary record index. | The reuse audit (task #10 of this session) is establishing what the existing RPA and recovery code already does and the exact gaps. RPA is not the persistence engine. |
| 7 | Built together | A frozen CNCM home-base entrypoint v0.1 is reported by the directive; Codex and DeepSeek demonstrations are recorded in its evidence register. The reconciliation documents it cites are not in this repository. | One coherent project: shared meanings (conformance fixtures for assertion, negation, unknown, conflict, correction, retraction, lesson, reload), an interchange envelope, single-writer ownership per stream, verified owners, an independent evaluation custodian. | Ownership is proposed, not accepted; no DeepSeek lead is verified; meanings differ (explicit polarity vs a negation predicate) and are unreconciled. |

## 5. Roadmap

Ordered by dependency, not by appeal. Each step states its gate answer in brief; the full answer is written in its directive before work starts.

1. **Reuse audit** (ability 3, 6, 7; preparation). Name, for every requirement in the lasting-memory directive, the existing module, what it does, the exact gap and the smallest compatible change. Output: `docs/working/helm_reuse_audit_2026_10_06.md`. In progress.
2. **Memory contract v1** (ability 3; preparation). A versioned extension of the Revision Streams contract — identity, events, beliefs and answers, snapshots, RPA entries, update and conflict behavior, durability boundary — written before any persistence code, with its amendment log.
3. **Retention, first result** (ability 3; behavior). *Done at level (a) on a first-look multi-session run, 2026-10-06 (`docs/working/helm_multi_session_evaluation_2026_10_06.md`); the frozen custodian run and level (b) remain.* Teach a fact, show it changes a later answer, save accepted state, terminate the process, restore, show the same behavior without reteaching; then correct or retract it and show every dependent answer changes before and after restart. Control: fresh recompute from the accepted event history. Criterion: exact agreement on every deterministic case; zero stale fast-path answers; every acknowledged update recovered within the declared failure model. Every claim names which survival it showed: after a clean process exit on the same machine, or after the machine was replaced (owner decision, directive amendment log item 1).
4. **Guarded answer reuse and the RPA comparison** (ability 3 and 6; behavior and cost). *All four paths ran on the multi-session first-look set, 2026-10-06: record-first with dependency invalidation agrees with the oracle on every probe with 0 stale hits and 279 record hits over 3280 probes per world; with RPA narrowing the answers are identical and 40 of those hits go to the walk instead — the atlas changed no answer and is kept as the comparison; the dependency-checked path is the working path.* Record-first behind a feature flag, whole-context invalidation first; four paths on identical work (fresh recompute, walk-first, record-first without RPA, record-first with RPA); common work units; a declared speed target with a paired confidence interval, reported as engineering choice not promise. If RPA adds no measured value, say so and keep the simpler path.
5. **Transfer** (ability 2; behavior). A frozen lesson contract; the same lesson asked through new instances or compositions; taught versus untaught controls.
6. **Cooperation** (ability 7; behavior). Conformance fixtures and an interchange envelope; one imported lesson producing a behavior neither path showed alone; verified owners and an independent custodian first.
7. **Self-improvement, bounded** (ability 4). After 3 and 5: the machine proposes one tooling change against a frozen criterion, with rollback.
8. **Neural growth and CASalescence** (ability 5). A separate neural-state experiment under the §2 protocol. Not before 3.

Parked, retained for comparison or fallback: broader English, recipe coefficients beyond the three shipped, Consequence computed by the processor, register-aware banks, the Rust `cas-engine` port.

## 6. Directives

Every directive is stored under `docs/directives/`, states which §1 abilities and §5 steps it serves, and carries its own authority and scope. Directives are amended in place with a dated log; they are not forked.

| date | directive | abilities | steps |
|---|---|---|---|
| 2026-10-06 | [HELM lasting memory and restart recovery](directives/2026_10_06_helm_lasting_memory_and_restart_recovery.md) | 3, 6, 7 | 1–4, 6 |
| 2026-10-06 | [HELM neural learning: a small useful skill that improves through teaching, survives a full restart, and works on new examples](directives/2026_10_06_helm_neural_learning.md) | 2, 3, 5 | 5, 8 |

Related binding documents: `docs/working/revision_streams_contract_2026_10_06.md` (the semantics the memory contract extends); `docs/working/cas_rpu_revision_streams_2026_10_06.md` (the evidence for ability 1 and the ground of 3); `docs/working/cas_rpu_reasoning_processor_2026_08_28.md` (the processor).


## 7. Consolidated source and neural-learning handoff — applied 2026-10-06

**Application note by the active writer (2026-10-06).** The owner delivered this section as a proposed amendment prepared from a read-only, byte-hashed inventory of the Codex, DeepSeek, September learner and October native-experiment records on the owner's machine and in the operator's records. It is applied here as delivered, with these qualifications: (1) §1 is unchanged; (2) nothing in §7 that lives outside this repository was re-verified from this cloud session, which cannot reach those locations — every path, hash, receipt and verdict in §7 is the source analysis's report, labelled as such; (3) the repository-internal items were checked here: the blobs listed in §7.5 match this branch at commit `c89f37a`; the seven "limitations and corrections for the active writer" in §7.5 were applied on 2026-10-06 — PR #248 is described as open and unmerged (§3), the process-launch denominator is 1200 (§4 and the multi-session note), the RPA diversion count is six per world and twelve in all, the harness header now reports twins *run* rather than generated, the session-generator suite is invoked in CI, the raw JSON reports are described as held only in the session scratchpad, and the live-storage gap wording names the owner's verification items; (4) this section authorizes nothing, as its own text says. The neural-learning directive that accompanies it is `docs/directives/2026_10_06_helm_neural_learning.md`; the decision package it asks for is `docs/working/helm_neural_learning_decision_package_2026_10_06.md`.

This section is the starting point for Claude and subsequent agents. It connects the existing roadmap to the preserved Codex, DeepSeek, September learner and October native experiment records. It does not authorize execution, alter private evaluation custody, select a winning codebase, or grant a new writer ownership.

**Evidence cut:** read-only gathering began 2026-10-06 09:38:43 PDT / 16:38:43 UTC. Sources below were read or byte-hashed, not imported or executed. Independent source reviewers inspected neural lineage, symbolic/RPA interfaces, and operator artifacts. The runtime identifies as GPT-6-based Codex; exact model variant and active reasoning effort were not exposed. Software checks and CI are preparation, not HELM achievements.

### 7.1 Where to start, and what each location owns

Use these exact roots; they are locators, not permission grants:

| alias | exact location |
|---|---|
| T | C:\Users\wakil\OneDrive\Desktop\tksCAS |
| C | T\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE |
| D | T\cas_only_reasoner\CAS_RRK_v0.1 — protected DeepSeek sibling |
| V | C\_worktrees\vision-next — separate Git repository, not a registered worktree of T |
| N | V\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE |
| B | C\research\HELM_NATIVE_MATCHED_TEACH128_20261005_R8B |
| R | C\_worktrees\codex-rpa-recorded-run\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE |
| P | C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation |
| G | https://github.com/LittleHenderson/noetic-compass/tree/c89f37a7dfde66b430521b3553e0709139993f90 |

**One entry point, preserved alternatives.** The repository roadmap is the overall HELM entry point. For local CNCM ownership and evidence, enter C\docs\CNCM_WORKSTREAM_RECONCILIATION_20261006.md, then its source-identities JSON and requirement ledger. C\README.md remains the frozen Codex CNCM v0.1 entry point; it does not identify October's neural learner. The existing C\docs\CNCM_JOINT_ARCHITECTURE_PROPOSAL_20261006.md maps reuse of graph, recovery, adapters, catalog/view and canonical encoding. It remains DESIGN_ONLY / NO_JOINT_AGREEMENT. Do not create a parallel memory framework, RPA build or roadmap because a schema needs a compatible extension.

Existing detail links: [canonical repository roadmap](https://github.com/LittleHenderson/noetic-compass/blob/c89f37a7dfde66b430521b3553e0709139993f90/docs/HELM_VISION_AND_ROADMAP.md), [CNCM reconciliation](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/docs/CNCM_WORKSTREAM_RECONCILIATION_20261006.md>), [joint reuse proposal](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/docs/CNCM_JOINT_ARCHITECTURE_PROPOSAL_20261006.md>), [R8B continuation/qualification plan](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/HELM_NATIVE_MATCHED_TEACH128_20261005_R8B/PLAN_AFTER_R8B.md>).

| stream | exact identity and current status | use and preserved boundary |
|---|---|---|
| Codex CNCM v0.1 in C | Outer T branch codex/casformer-v0.2-release; HEAD eb3c9b1eac98853b2065c98b08987918e8e7d936. Committed C subtree 661d2056ed46e61afb388dd632917063cde5300c. | Frozen symbolic reasoning foundation plus later opt-in research. The stable CLI does not automatically expose native/recovery experiments. Local additions need their own file identities. |
| DeepSeek D | Committed subtree f0f2cd7f012ebb862fc0b82d4d0a179ade062482 in the same outer repository. Protected owner files; current live lead unverified. | Independent symbolic implementation, guarded repairs and grammar promotion. Preserve its different semantics and same-process demonstrations. No integration consent or accepted joint ownership has been established. |
| September vision-next V/N | Branch research/helm-2.0-iterating-rounds; HEAD c58d4f42a733f496ebb07275d3897ba8f4e67932. N\BRAIN_LINEAGE.md and N\AUDIT_PACK.md retain historical authority. | Historical HELM 2.0 learner and correspondence/transfer experiments. Not October's execution owner or checkpoint authority. NO_TRANSFER_TO_NEW_WORLDS, retention regressions and failed certification remain part of its result. |
| October native B and earlier R7/R8 | Untracked research packages in T, not a dedicated committed version. BASE_ORIGIN.json plus source/archive hashes and operator receipts define actual execution identity. | New native route model importing selected prior weights. Existing matched128 driver, reader, acceptance seal and PLAN_AFTER_R8B are the continuation path. Ambient outer HEAD cannot prove shipped bytes. |
| CAS-RPU G / PR248 | Open, unmerged, refreshed head c89f37a7dfde66b430521b3553e0709139993f90; base 1574ce5eb1b7db9b1ec9f4ba6182b758bb963875; branch claude/cas-reasoning-processor-i47toc. | Current symbolic processor, organism, history replay and optional RPA narrowing. It is not a neural learner. Its active Claude writer owns repository changes. |
| RPA in R | Branch codex/helm-rpa-recorded-run-20260922; commit eb9985566bd11a89f485d627186ef0efa7177f02. | Reusable read-only atlas, recorded/native/compound adapters and recovery. PR248 imports two pinned files, not this entire branch or its ownership. |
| PCBA alternate | Branch codex/helm-pcba-adapter-20260921; HEAD 091f2bd2e4e9a41e8d80f6b310cc71c453c30f76. | pcba_component_adapter.py is a strict non-executing component reader; it does not train/load the neural model or demonstrate neural board gain. |
| Optional growth | C\research\HELM_GROWTH_RELOAD_v0_3, README.md / CAPABILITY_WITNESS.md / AWS_VALIDATION.md. SOURCE_IMPLEMENTED / NOT_RUN for the repaired version. | Retain as an incompatible experimental growth path, not a current R8B capability. Its 624 added A/B weights violate current teaching admission and geometry. |

These are **complementary implementations and different experiments with historical reuse**, rather than two interchangeable copies of one current machine. The Codex and DeepSeek symbolic implementations share the goal and repository ancestry but have different engines and assertion/negation interfaces. The October model inherits three operation matrices from a September checkpoint, not its complete learner. CAS-RPU independently develops symbolic state and replay. Preserve every stream; integrate only after meanings, state authority and observable behavior agree.

The PR248 interchange draft at docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md compares CAS-RPU with **Codex CNCM**, both using explicit polarity. It is not proof that the protected DeepSeek predicate-negation interface has been reconciled. Its older “no reload” snapshot is superseded for CAS-RPU by the current history.py. The earlier reuse audit at docs/working/helm_reuse_audit_2026_10_06.md is useful design history, but its early missing-replay rows are likewise superseded.

### 7.2 Actual checkpoint, model and state boundaries

The inherited checkpoint is present at both B\base\inputs\final.pt and B\base\evidence\op10\inputs\final.pt. Each is 4,025,999 bytes, byte-hashed to **5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341**. This matches BASE_ORIGIN.json. The files were not decoded in this analysis.

B\base\native_construct.py imports only left.weight (64×64), right.weight (64×64), and merge.weight (64×128). The October network has a new encoder, deterministic decoder, probe CJT and two reserve CJTs; prior pointer heads/encoders and other learned state are excluded. Registered training and inference execute the probe, so reserve units do not establish neural cooperation. The constructed root is pinned by historical_prefix.py:

| identity | digest |
|---|---|
| native root model | 6ea6c6b3118d7bdfd904933c9fee1ff2ed8d567216efb6e0ae0e8debca1ce161 |
| native root state | 6ed56d7b7ab033cb7cf16b331c09713bb02af6a112864b06e6b97d54a8da6822 |

The current **accepted learned checkpoint is not established by these input files**. Each R8B arm starts its own private copy from the original state. A private endpoint, a report-only extension, a qualification candidate and a durably accepted main state must be named separately. No 128-step endpoint locator or October 6 source/freeze/controller closeout was found in the accessible records. P\controller_claude_r8b_c06 and D:\tksCAS-archive\helm_r8b_matched128_c06_20261006 were absent at the source cut. This does not prove that a newer run did not happen. Request its exact existing receipt/archive/endpoint locations from the current operator; do not reconstruct them or reuse an old NOT_RUN header as current status.

R8 private endpoint custody has a metadata record, P\PRESERVATION_R8_PRIVATE_ENDPOINTS_20261005.json, pointing to D:\tksCAS-archive\helm_r8_matched_c05_20261005\preserved_private_endpoints. They are unpromoted and unqualified; payloads were not opened. An R8 report-only step-102 endpoint cannot stand in for a missing R8B 128-step endpoint.

The historical pointer-learning source is distinct again. The growth dossier pins pointer_learner.py to source c45f775f225dd06cc20cdf313f0a0398486e0d61 and SHA256 0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8. The currently read N pointer_learner.py has SHA256 21dabd21bb2909ff5990e2b11fd45b75558dce82992c34edfe12f8f556cd5084. Neither can silently substitute for the other. The real-parent growth migration driver at 31b7896f3db1be2152ec634b066cd36a9159719d remains unrecovered, so its full dependency closure is unverified.

### 7.3 Data, inference, learning and durable state flow

| stage | actual current source and authority |
|---|---|
| encode | B\base\native_task.py:95–104 encodes public graph identities, edges and proposed route into (1,8,64); gold is excluded. |
| inference | native_learning.py:45–83 creates the input cause and calls _prepare_inference without the expected answer or a memory write. Inference must leave state unchanged. |
| control | cas_cjt\control.py binds persisted Bias, checkpoint, input, routing, memory references and settings. RouteSettings defaults are explicit; two_route and constant_sum profiles are optional, not established active gains. |
| neural execution | cas_cjt\runtime.py:939–1021 → network.forward_node → cas_cjt\neural.py:358–402. CASformer's hard-gated telemetry effect feeds the operation; residual/FFN output is discarded. Construction uses standard linear weights. |
| answer | native_task.py:122–140 averages effect over batch/nodes; its first eight channels become eight logits. cas_cjt\semantic.py:97–128 applies the registered deterministic decoder. |
| private teaching | matched128\native_matched128.py → pinned R7 helpers and historical_prefix.py → isolated arm → _body_guarded. M uses pinned r8\matched\m_direction.py; it has current state and fixed original rows, no memory between steps. |
| endpoint/reload/seal | Pinned R7 save_endpoint / reload_endpoint; R8B reload_main / run_reload_child / write_acceptance_seal. Acceptance is sealed before report-only EXT_M. Source support is not evidence of actual continuation. |
| persistent native state | cas_cjt\persistence.py uses SQLite WAL/FULL and BEGIN IMMEDIATE. runtime.open:625–685 restores model, manifest, decoder, semantic lineage and teaching admission, then verifies coordinator recovery. |
| qualified native teaching commit | runtime.teaching_tick:1593–1753 opts into a Theta-only transition, independently replays qualification, durably commits isolated native state and then loads weights. It requests no memory, Effect or RPM commit; it does not establish global HELM promotion. |
| current parameter admission | teaching_learning.py:506–508 admits exactly the three operation matrices. New A/B growth weights are rejected by present geometry/scope. |
| symbolic bridge | cas_cjt\cncm_bridge.py explicitly grants INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM. It imports neither current cncm nor the DeepSeek kernel. |

A model checkpoint encodes the module state_dict (cas_cjt/checkpoint.py:56–71); it is not the complete continuation bundle. A resumable episode also needs bound configuration/topology/decoder/lineage, original constraint rows and controls, original parameter reference, accepted/refused-step cursor, cumulative/rounding/nominal path totals, and admission/schema identities. Record optimizer, schedule and RNG state when used; explicitly declare their absence otherwise. R8B load_start_state:763–797 takes all three path totals from ARM_M.json, while _body_guarded:834–842 retains the original parameter reference and cursor. Exact stop/save/continue is a different contract from loading weights and reproducing predictions. R7/R8 reload statements do not establish stop-at-32/64/102, restart, and identical continuation to 128. PLAN_AFTER_R8B §4.2 gives those cuts as examples to fix before execution; §4.3 explicitly says current qualification /3 cannot directly accept a saved endpoint. Resolve its interface and promotion authority before implementation.

CAS-RPU has a different, already implemented symbolic flow: Organism.consume is the history single writer; history.py records constructor and ordered events; restore replays and checks outcomes, state digests and audits before the first answer. The RPA callback must be attached before replay. record_dep works without RPA; record_rpa optionally narrows candidate records. Workspace.snapshot is an inspection summary, not the checkpoint. Missing acknowledged history yields E-MEM-046; incompatible state yields E-MEM-010. Replay code does not imply neural parameter retention.

Existing RPA models current state, focus and hypothesis branches, and projects only after authoritative restore. Its atlas is not the persistence engine. Existing native/compound journal schemas and their bounds are recorded in C\docs\CNCM_JOINT_ARCHITECTURE_SOURCE_IDENTITIES_20261006.json: 512 atlas nodes / 8 MiB; native 8 episodes / 32 MiB; compound 16 / 64 MiB; 1024 journal events. Extending these existing families requires a demonstrated gap and invariant-preserving ownership decision, not a new competing system.

### 7.4 R7 / R8 / R8B: real outcomes and preparation

| experiment | saved result and actual behavior | conclusion |
|---|---|---|
| R7 bracket | Job helm-claude-r7-bracket-20261004-c03. READING reports COMPLETE, H-OBSTACLE, R-B / REACHABLE_NOT_PROTECTED. Unguarded C/B correct target at 41/42; no clean protected step. H0 breaks anchor correctness at 15, projection refuses at 56. K12 remains 18/128 correct despite lower loss. | Target reachability and protection obstacle were measured; no durable protected learning achievement. TRAIN diagnostics are not independent qualification. |
| R8 matched64 | Job helm-claude-r8-matched-20261005-c05. COMPLETE; FAILURE / FAILURE_M_NO_T_AT_64. M retains guards at 64 but target stays wrong. Bg accepts two steps and refuses at three. | Registered experiment failed. Qualification NOT_PERFORMED_THIS_JOB_CANNOT_EMIT_A_PASS. |
| R8 report-only EXT_M | Target first correct at 102, 38 steps beyond acceptance budget. | Preserve as exploratory evidence of a longer trajectory; it cannot upgrade the R8 verdict or replace R8B. |
| R8B matched128 | Arms S sham, X5 replay-R5, M mechanism, Bg rehearsal, new Cg target-gradient baseline and B4 wrong-target. Frozen horizons: X5 retains 64 / 3.2M micro-unit path (historical refusal at 13); M/Bg/Cg/B4 allow at most 128 / 6.4M, or terminal refusal. S is sham. Guarded accepted states retain 18 anchors. EXT_M is report-only. | Current execution outcome unverified because latest result custody is missing. The best mechanism-specific verdict is EPISODE_CLEAN_QUALIFICATION_REQUIRED; a clean M episode can instead receive baseline credit or lack target specificity. No verdict is a general learning pass. |

The 128-step allowance was chosen after observing R8's step-102 correction; PREREGISTRATION_R8B:50–66 discloses this. It is not an outcome-blind comparison with R8. Do not cherry-pick M, omit Cg/Bg, or treat accepted steps as independent capabilities. Follow PLAN_AFTER_R8B's INVALID, FAILURE, CREDIT_TO_BASELINE, EPISODE_CLEAN_NOT_TARGET_SPECIFIC and clean-qualification branches, with no rescue run.

Each guarded accepted state keeps all 18 anchors correct with positive margin and each anchor's cross-entropy at most its own original value plus 0.005. The arm's PRIMARY loss strictly decreases (B4's PRIMARY case 85 differs from the real target), alongside parameter/path/reserve/direction checks. This per-anchor training threshold is distinct from qualification /3's mean-of-32 panel threshold.

Saved result custody is partial in B: R7 12/42 manifest members, R8 26/51, all present bytes matching recorded hashes/lengths. Missing members include endpoint binaries, reload receipts and prefix SQLite. Thus this analysis verifies saved reader statements and available artifacts, not full restart/replay closure. Operator raw/result locations are:

- P\controller_claude_r7_c03\retrieved\runs\helm-claude-r7-bracket-20261004-c03\results\r7_reading\out\READING.json
- P\controller_claude_r8_c05\retrieved\runs\helm-claude-r8-matched-20261005-c05\results\r8_reading\out\READING.json

R7 is source-recorded Fable5.1; **R8 is Opus5.5**, corrected in P\MODEL_PROVENANCE_R7_ASOM_R8_20261005.json. A hardcoded Fable5.1 R8 closeout label is stale. The R8 correction also acknowledges that the prereg-required hash-bound owner record was absent: operator-bound plan hashes are not owner-reviewed authority. “Stage consumed” does not establish compliant approval or teaching success.

B\base\cas_cjt\teaching.py supplies 128 TRAIN examples and the 32-case qualification panel. The fixed-seed panel (2026100107) is **EXPOSED**, not fresh held-out evidence. All 480 known fixtures must be excluded from a proposed fresh panel under PLAN_AFTER_R8B. Custodian identity, sealed seed/commitment, opening authority and final comparator/criterion are not yet assigned. No private panel contents were read or copied here; custody must be independent of the builder.

### 7.5 Symbolic results, controls and current reporting corrections

Keep the actual narrow gains from both CNCM streams. The existing reconciliation document reverified Codex's public retained correction 10→9 and two-call equation solver reused after restart, and nested prerequisite solving; these are bounded **symbolic** fixtures. DeepSeek's guarded rule/math repair and grammar intake remain its distinct saved capabilities; the grammar promotion is same-process. Neither demonstrates parameter retention, useful added neurons or neural-level cooperation.

PR248 now adds history-backed multi-session retention and symbolic lesson families. Pin current sources under G:

| source | Git blob or commit |
|---|---|
| docs/working/helm_multi_session_evaluation_2026_10_06.md | 837bc02b71c8058c902182d8e9a94d35b97d014a |
| scripts/cas_rpu/history.py | c327dd3ca27e188605214a97dc3cb7c58e415156 |
| scripts/cas_rpu/organism.py | d040c7ce5473bbcb80b97e2129a1bee8a7646a34 |
| scripts/cas_memory/rpa_adapter.py | b19a8dab1ff47961c9b0e3a11d1f3d6294395794 |
| new opt-in symbolic lesson-family change | commit cae1a5c6181d892292b8bd9b2e9972e778d1d1c2 |

The first-look report states 20 builder-generated seeds, five successive fresh processes, four paths and two worlds; each path/world has 3280/3280 correct verdicts and 180/180 cross-session probes. Dependency-checked record answers include 40 previously held conclusions with zero stale hits. Untaught twins give 540/540 GAP; T-compose gives 20/20 reasoning answers with zero record hits, versus T-exact's 20/20 record answers. In fault schedules, 1597/1640 asks are answered, all correctly; 43 explicitly refuse after corruption/schema faults; 9/9 recoveries and 162/162 recovery probes are reported. These are source-supported **same-host symbolic development/first-look behaviors**, not an independent custodian result, machine-replacement survival, neural learning or generalized lifelong retention.

RPA narrows 40 of 279 record hits into the walk, changes no answer and removes no stale hit; reported restore median increases about 43.7→82.2 ms. Dependency-checked record reuse remains the working baseline; RPA is the comparison. Only rpa_model.py and canonical.py are content-pinned to eb9985566bd11a89f485d627186ef0efa7177f02; loader HEAD is informational. This does not validate the full alternate checkout.

New lesson commit adds seven opt-in symbolic variants and untaught twins, explicitly **neural change: none**. Parent observed CAS CI run 37497122293 complete at 09:41 PDT after a workflow-formatting repair, with nine lesson tests invoked; source reports 42 generator tests, but the sessions-generator suite is absent from explicit CI invocations. No CI or test was run by this analysis, and these counts are preparation. The new variants' independent behavior result and custody remain to be established.

The 10:00 PDT refresh found commit c89f37a7dfde66b430521b3553e0709139993f90 changing only session_harness.py: completed stream stores are removed by default unless --keep-stores. Its commit message reports that the first lesson run stopped in its last path with E-MEM-051 (insufficient disk space). This is an author-reported incomplete experiment and harness custody change, not a new behavior result. No deletion was performed here. The roadmap, history, organism, RPA adapter and earlier multi-session report blobs listed above were independently checked unchanged at this refreshed head. Future evidence retention must explicitly account for --keep-stores and retained raw artifacts; this handoff does not authorize another run.

Limitations and corrections for the active writer:

1. The canonical source previously called PR248 merged and named an old head/base. Current PR is open and unmerged at the identity in §7.1; this proposed copy corrects that wording.
2. Report/canonical process-launch totals are inconsistent. The available harness implies 40 streams × 5 sessions × 3 subprocess paths × 2 worlds = **1200 normal process launches**; P0 is in process. Report's 400 per path/world and canonical's 2400 need the author's raw manifest. Do not substitute either unverified denominator as settled.
3. Fault header reports 20 twins while --no-twins renders generated rather than executed counts; do not claim twins ran there.
4. Older dry-run table's 39 versus 33 record hits per world implies six diversions per world / 12 total; prose saying six total / three per world conflicts.
5. Current context isolation is store isolation. K same-token context, W world-mode switch and A scoped-assumption classes were excluded. Their absence limits retention/cooperation claims.
6. Raw multi-session JSON (about 31 MB) and fault JSON (about 9.8 MB) were not retained in the repository. Author-declared hashes eb87140a2f0d4b1f74e12a8f7969a5c7d1286b9fd7464b48084edc40eca4e681 and 8f8b074f16df1b08678f731d9e8f209f0299bef59db0bc0e332cd74cfd19cd88 were not byte-verified here. Obtain existing artifact locations; do not rerun to fill a provenance gap.
7. The live-storage gap includes owner verification of location/purpose/access/deletion plus authorized operator access, not merely a key. No credentials should enter this record.

The September component-first study's reported relative advantage does not establish absolute improvement. Existing lineage/audit and reconciliation preserve that both schedules ended below initial performance and transfer/certification failed. Reuse the detailed historical record; it is not evidence that a current October combination is optimal.

### 7.6 Single writers, existing AWS path and undisturbed terminal work

| boundary | owner / dependency |
|---|---|
| overall intent and acceptance authority | Little Henderson; §1 unchanged. This handoff grants no run, merge, budget or promotion authority. |
| active PR248 roadmap/source writer | Current Claude session linked by PR248: https://claude.ai/code/session_013bBgKrpuApzAGiekqN7QHr. Declared route, not contacted or independently authenticated here. Apply this proposal through that existing writer. |
| Codex v0.1 homebase | Frozen code/navigation; protected by C\AGENTS.md and requirement ledger. Reconciliation documents map scope, not reassignment of ownership. |
| DeepSeek sibling | Protected D; current lead and consent unverified. Historical coordination records are not current owners. No messages, paid wake or code edits made. |
| R8B execution / accepted checkpoint | Current operator and artifact custodian must supply latest receipts and state identities. Do not elect a replacement based on old C06 plans. |
| fresh evaluation | Independent custodian and sealed commitment not yet assigned; builder must not see private panel contents. |
| terminal operator | Existing thread 01a0f984-b80f-7212-ac4c-d779134f50d8; builder 01a10a4f-811d-767b-9bbe-c7968b557003. Leave their source, leases, budget and responsibilities untouched. |

The existing AWS call path is the receipt-pinned P\controller_claude_r7_c03 or P\controller_claude_r8_c05: aws_control.py → worker.sh → runtime_preflight.py → that controller's shipped job_supervisor.py → tests, frozen driver, independent reader. bounded_s3.py provides bounded transport; independent_cleanup.py supplies cleanup. P\claude_jobkit is preparer/source material, not a substitute for shipped identity. Its make_r8b_config.py is the older R8B configuration preparer: owner-record validation, sealed archive/build review and allocation/lease admission precede preflight/launch. It does not prove that the same bytes were shipped in a newer job.

Historical R7/R8 envelopes: us-west-2, m6i.xlarge, one attempt, $1 cap, no retry; at least 2400 seconds must remain after bootstrap/dispatch in the same launch-derived 3000-second work window. New stages/processes do not renew that allowance. Work/force/host limits are 50/55/60 minutes. These belong to those receipts, not an automatic current PR248 envelope.

Nonsecret C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json was byte-read only. Revision helm-unified-20261005-owner7f636937-ceilinga1706fb3 records $97.59 provisional allocation against $250 ceiling, $152.41 unreserved and R8B/terminal $1 pending caps with $0 allocations. This is a historical control snapshot, not live billing, available credentials or launch permission.

P\controller_terminal_op14\READINESS_RESULT.json at 2026-10-06T06:58:01Z says SOURCE_READY_WAITING_EXISTING_ACCESS_AND_LIVE_ADMISSION. The last ProfileNotFound was before an AWS request; no paid run, allocation, upload or test occurred in that record. Existing 900-second host / 1200-second cleanup / $1 / one-attempt envelope remains separate. Do not change it or replay it here.

### 7.7 Reuse now, compatibility work, and next measurable experiment

**Reuse now as existing infrastructure:** pinned R8B matched128 driver/reader/acceptance plan, original input checkpoint, guarded episode and baseline definitions; SQLite checkpoint/recovery interfaces; existing RPA read-only adapters and canonical encoding; CAS-RPU's checked history and dependency invalidation; PCBA reader; detailed reconciliation manifests. Source inspection/navigation is authorized now. Running, promotion, schema implementation and private evaluation are outside this analysis.

**Require compatibility and behavior evidence:** saved endpoint → qualification /3 admission; complete optimizer/cursor/RNG continuation; symbolic lesson envelope/negation/correction/retraction conformance across engines; private context classes K/W/A; neural vs retrieval separation; growth checkpoint geometry; genuinely active multi-CJT or cross-model cooperation. Current symbolic proposal bridge and non-executing PCBA reader cannot fill those gaps.

Next action is conditional on the **existing R8B outcome**, not a new project:

1. Retrieve the latest R8B shipped-source freeze, owner record, controller receipt, closeout, acceptance seal, endpoint manifest and stored endpoint locators. Compare bytes with B. Establish private candidate vs accepted state, writer and promotion authority. Missing artifacts means UNKNOWN, not success, failure or permission to rerun.
2. Follow PLAN_AFTER_R8B's actual branch. Only the exact EPISODE_CLEAN_QUALIFICATION_REQUIRED verdict makes arm M eligible for step (a). INVALID, FAILURE, CREDIT_TO_BASELINE and EPISODE_CLEAN_NOT_TARGET_SPECIFIC do not. Preserve their verdicts; no rescue run or extra allowance is authorized.
3. Finalize existing step (a) in its prescribed order. Part 1 replays full M from ORIGINAL in a fresh process on the pinned AWS machine type, comparing all 129 states: state digest, observation, all 128 TRAIN rows and every update's path fields, then final endpoint bytes against the retained R8B receipt/endpoint. Any difference is INVALID; restart and qualification do not run. Part 2 then compares stop/save/fresh-process continuation at owner-fixed cuts (32/64/102 are plan examples) against the uninterrupted reference, preserving the continuation bundle in §7.3. Every later digest, row and final endpoint byte must agree. An independent forward-only loader re-predicts 128 TRAIN cases. This is reproducibility/retention preparation for abilities 2/3, not a novel learning achievement.
4. Fix the cuts and comparisons before execution. Preserve source, guards, decoder, path totals, step choices and private status. Missing state, altered admission or any divergent continuation fails Part 2 and blocks Part 3. Verify target correction at the retained private arm-M endpoint and after fresh-process restore without reteaching, with retrieval disabled. Acceptance of individual steps does not make that endpoint an authoritative HELM state. A clean result still concerns one TRAIN target; it cannot establish learning, new-world generalization, growth or cooperation.
5. Part 3 uses the existing EXPOSED 32-case qualification panel, after resolving a separately versioned saved-endpoint check and its naming/authority. Keep its four conditions unchanged: target loss improves by at least 1 micro-unit; mean panel loss rises by at most 5000 micro-units (0.005); the originally correct panel subset is nonempty and loses zero answers; target is correct. A refusal is final for that job. A clean check stays private: no native commit, transfer or global acceptance follows automatically. This gate can detect regression; it cannot certify novelty.
6. Step (b), separately proposed in the same PLAN, is the measurable test of broader learned ability: owner-frozen seeded selection of several wrong TRAIN targets covering at least two answer classes; fixed procedure/constants/guards/allowance; fresh sealed custodian panel of at least 64 cases in 32 world pairs excluding all 480 known fixtures. Include B0, lookup B1, Bg, Cg, B4, constant-answer and the plan's proposed mechanism ablations under matched constraints. An independent non-Claude reviewer must review design and raw outcomes. Before any new data, owner must adopt or reject proposed Rule A: world group is the counting unit; fixed exceeds broken; exact one-sided sign-test p≤0.01; fixed groups span at least two labels and worlds; zero retention-panel breaks; M beats every baseline on fixed minus broken. Keep every older necessary criterion too. These are proposed conditions, not authorized acceptance rules. Exposed /3 cannot substitute for this test; fresh step (b) cannot substitute for /3 when qualifying/promoting the retained step-128 candidate. PLAN also permits a new separately frozen and authorized step (b) after FAILURE, where step (a) does not apply; it cannot rescue or relabel that failed episode. Zero gain or baseline credit is reported directly.

A clean resume/reload establishes survival/reproducibility of the registered target correction within its private episode. The existing plan expressly says step (a) cannot establish learning, generalization or HELM advantage. Broader learned ability must pass separately authorized step (b); useful self-added neurons and neural cooperation require their own mechanism-disabled and equal-capacity controls. The current probe-only episode cannot demonstrate either.

Ranked alternatives are **testable hypotheses**, ordered by current evidence and smallest disturbance, not claimed optimal designs:

| priority | hypothesis and reason | comparison that could falsify it |
|---|---|---|
| 1 | Existing R8B candidate and current three-matrix route may support durable target correction; R8's 102-step observation motivates this, while its failed acceptance limits confidence. | First resolve actual R8B verdict/custody; matched continuation, Cg/Bg controls and fresh qualification could show no durable or target-specific gain. |
| 2 | Episode admission/constraint schedule, rather than capacity, may be the main obstacle; R7 reaches target unprotected, R8 preserves guards without target. | Existing guard/step/arm traces plus independently frozen admission comparison; no added budget or edited failure examples. |
| 3 | CAS-RPU history plus dependency checking may usefully organize symbolic retained lessons, with optional RPA as inspection. | Same cases with/without history, record reuse and RPA; preserve unknown/conflict/retraction and K/W/A contexts. Current RPA answer gain is zero. |
| 4 | Broader operation/decoder representation may be needed for unfamiliar worlds. | Frozen new-world tasks, untouched/full-parent comparisons where compatible, retrieval disabled; preserve September transfer failures. |
| 5 | Legacy 624-parameter growth or active multi-CJT cooperation might add useful capacity after state/admission compatibility is solved. | Real-parent source closure, equal-capacity/disabled controls, restart retention and part-vs-combination gain. Source-only growth repair and reserve units are insufficient. |

### 7.8 Compact evidence identities and remaining dependencies

SHA256 below identifies bytes; Git blobs identify repository content and are not interchangeable with SHA256. Full source inventories remain in the existing manifests instead of being copied into another project.

| locator | SHA256 |
|---|---|
| B\BASE_ORIGIN.json | 66e9db0fd0a43c6097786579ebcbff6230b557c52a4dfbe29a9caf4d1c96f667 |
| B\PREREGISTRATION_R8B.md | cfe30bcc07985530f65e822f7103fca00f6c8080e0061bb5e8198315d7d0954f |
| B\PLAN_AFTER_R8B.md | 4762364de86b00707728737d67b02dd78ce55dbb70a50cbc8e8566f82fe7b8a2 |
| B\TEST_ROSTER_R8B.json | 909c78d288b37fd3d880a1703d24aa95ea0f62baac50788065d315e849c57e09 |
| B\matched128\native_matched128.py | adb5e54d326232f26852d60f22903f0646f79beec91a0aff004d178893e7e2bb |
| B\matched128\matched128_reading.py | 45175faa3feedefe25ce871c6ecc1fe0e58a16434bd493d25a7833173bfa1e8a |
| B\r8\matched\m_direction.py | 6f3cdd5194c360c957b1828cbde0748985acc6237bac0786bfeb5161bcea3f5e |
| B\base\native_construct.py | b7286e6c11094a1a78d9f2705fb93040930f905cf35d7c991424edc7344b7126 |
| B\base\cas_cjt\runtime.py | db4f0face85847b7bb0940d72e1a121ff75a3859dfc3d536939ccf736a357c0d |
| B\base\cas_cjt\persistence.py | 2d80349b29b2397e15bd6e5872f8f7c751ade2c1c6f568476a4b252e5cf248d9 |
| B\base\cas_cjt\teaching_learning.py | c668d0b661bc28de9f7f6a3cdfca6a452617723caa4c43478b6e310a79175f88 |
| B\base\cas_cjt\cncm_bridge.py | fc25c9836f284abb6bf1378ba0d92021a9f3e03b4ee70df00bce2dcedf3ceb71 |
| B\r7_evidence\READING.json | 06adab1cbb3646fd9509c425aa513febc1ad90934fab1ac0684dee9143e9c900 |
| B\r7_evidence\MANIFEST.json | e772841810c3a1403835cb205d55e5183d820d3c775689694962e65e4913ba99 |
| B\r8_evidence\READING.json | 08929aaa736e8331509f8af215a6e25f8c5df0f865d34e3113eb1d8905fe85a2 |
| B\r8_evidence\MANIFEST.json | 18589ebcd22f57ec5f4e4f970ef1adcb005a415b5b02bdb034502735bfb857bd |
| B\r8_evidence\ACCEPTANCE_SEAL.json | 652128ee929bd61956310caed2191a67dc403c59da3b2bfc9eeec87392a78ca3 |
| N\BRAIN_LINEAGE.md | 30875cee7a0db50558acc7cdddfd1f5c412f782063272ff489c8e27abe964efb |
| N\AUDIT_PACK.md | 02320dd8afc09a22128098b24d54b2b927c07594b19d667c06860ae5f6afa4a8 |
| P\MODEL_PROVENANCE_R7_ASOM_R8_20261005.json | 234c533830bb2355dab18856659722994eb1d6f22868603a05041bf069db70e6 |
| P\PRESERVATION_R8_PRIVATE_ENDPOINTS_20261005.json | d18c64531db52276f2072dfc2b2aefed873b5dfee3e7d261b99c0c0e3afbd938 |
| P\claude_jobkit\make_r8b_config.py | c3e49b1cd823a82bc4e2b090ebdeb8b4a5523e960a12384e913d3d084f6dad77 |
| P\controller_terminal_op14\READINESS_RESULT.json | 2da217588f59340629080d02ba59dc57d4af864ef52ec448ed15e15586ea193a |
| AWS_COMBINED_ALLOCATION_CURRENT.json at stated absolute path | 9ffdb8d55e1a4f3797b25dff7a61e2e067fdeae3e99edf6370e7ad3f81e91fdb |
| C\docs\CNCM_WORKSTREAM_RECONCILIATION_20261006.md | e9fe025053c46d74b517eaae1dc41cb7f9ce0d4c312e939685416ba6b9f10cad |
| C\docs\CNCM_JOINT_ARCHITECTURE_PROPOSAL_20261006.md | ebd4421ff0b90f2e7b2de27e811a05e95280ecbe99a50fd463c1e1c16eb1abf3 |

Open dependencies: newest R8B shipped-source/receipt/result/endpoint custody and accepted-state owner; complete continuation-state contract; saved-endpoint qualification admission/authority; independent panel custodian and sealed opening conditions; protected DeepSeek current lead/consent and cross-engine fixtures; PR248 raw aggregate artifacts and reporting corrections; machine-replacement storage ownership/access; legacy growth real-parent driver closure. These are specific dependencies, not reasons to duplicate a build.

No project source, R8B/ASOM/terminal code, budgets, credentials or protected files were changed. No tests, benchmarks, imports, inference, training, paid APIs, AWS calls, pushes, merges or deployments were performed. This proposed document and its authorized Library delivery are the analysis outputs. Existing owner-reviewed navigation remains in place; active-writer application is NOT_APPLIED.


**Review record:** independent neural-source and operator/whole-document reviewers completed bounded read-only reviews. Corrections incorporated: private endpoint authority, model versus continuation bundle, exact eligible verdict, full replay before restart, exposed /3 versus fresh step (b), X5 horizon, per-anchor versus panel thresholds, launch-derived remaining window and shipped supervisor. Owner intent §1 is preserved. This is a source/evidence handoff, not model accomplishment.
