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

Worked answer for the work merged so far (PR #248, head `17dbe73`, base `4377a7d`): *Ability 1 and the ground of 3. The behavior: an organism that holds conclusions across questions agrees with recompute-from-scratch on every probe of a generated event stream in both world modes, and withdraws a held conclusion when its support is retracted or denied. Control: the two-set replayer `ctl_recompute`, correct by construction, and seven ablations each removing one workspace rule. Criterion: 100% agreement on verdict, contested keys and lacuna bounds over 89 probes per world, zero heartbeat faults; each ablation failing only inside its class. What it does not show: memory across items, survival of a process restart, or that truth maintenance is necessary — the replayer is also 100%.*

## 4. Where we are, ability by ability

Updated with each landed piece of evidence. Entries cite the commit or document that carries the evidence; anything not verified in this repository says so.

| # | ability | demonstrated (bounded) | required for the ability | the gap |
|---|---|---|---|---|
| 1 | Reasons | A processor built from CAS components reasons natively with no model in the loop: `^8` associates, `^6` decomposes at unity gain, `^9` lands; ten capabilities tested with the cord severed (PR #227). An organism over a living workspace holds, reuses and withdraws conclusions and converges with the recompute oracle on generated streams (PR #248). Motivation changes what is asked and never what is answered; the heartbeat audits standing beliefs. | Goals that choose problems, not only questions; checks on decisions that cover actions, not only verdicts; reasoning over open English rather than a five-production grammar. | Problems arrive already encoded; the encoder is five productions with total rejection. Memory is one workspace per item. No decision beyond a verdict is yet checked. |
| 2 | Learns | Nothing demonstrated under the §2 definition in this repository. The directive's evidence register reports a bounded Codex correction (10→9) and reuse of a two-call solver in a fresh process, and DeepSeek guarded rule and math repair with grammar-lesson intake; those are recorded there, not verified in this session. LEARN in the processor writes one experience cell at low gain. | A taught lesson that helps solve a new supported case or composition, compared against an untaught control. | No lesson contract, no transfer test, no untaught control exists yet. |
| 3 | Retains | Held beliefs survive across questions within one item and one process (PR #248). | An accepted fact or correction that still changes a relevant answer after intervening sessions and a fresh operating-system process, without being retaught; dependents of a retraction change correctly before and after restart; no stale answer escapes through a faster path. | Nothing is persisted. `Workspace.snapshot` is an inspection summary. The CAS memory substrate design (`docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md`) is a proposal. The 2026-10-06 directive defines this gap and the order of work to close it: reuse audit, versioned contract, durability, guarded answer reuse, held-out multi-session evaluation. |
| 4 | Improves itself | Nothing. Every change to tools, harness and structure so far was made by a person or a delegated agent, not by the machine. | A measured improvement to its own tooling or structure, chosen and verified by the machine against a frozen criterion, with rollback. | Not started. Parked until 2 and 3 have demonstrated behavior, since self-improvement without retention is lost on restart. |
| 5 | CASalesces | Nothing at the neural-architecture level. The CAS-native model work (`cas-native/`) is training infrastructure with its own checkpoints; the processor and organism are symbolic. | Models working as a combined system with a measured functional gain over the parts, and a separation of retrieval assistance from parameter retention. | Not started. Requires the neural-growth protocol of §2 and a frozen baseline. |
| 6 | Organizes with RPA | An RPA model, recorded-run adapter and native adapter exist on branch `codex/helm-rpa-recorded-run-20260922` at `eb99855`, separating current state from inspection focus and hypothesis branches; the recorded adapter labels its view as an archived record, not live HELM. Not on `master`. | RPA as a read-only index over the accepted event history that locates records and shows branches, rebuilt only after authoritative restore validation, never promoting a possibility to a fact, and shown to add value over an ordinary record index. | The reuse audit (task #10 of this session) is establishing what the existing RPA and recovery code already does and the exact gaps. RPA is not the persistence engine. |
| 7 | Built together | A frozen CNCM home-base entrypoint v0.1 is reported by the directive; Codex and DeepSeek demonstrations are recorded in its evidence register. The reconciliation documents it cites are not in this repository. | One coherent project: shared meanings (conformance fixtures for assertion, negation, unknown, conflict, correction, retraction, lesson, reload), an interchange envelope, single-writer ownership per stream, verified owners, an independent evaluation custodian. | Ownership is proposed, not accepted; no DeepSeek lead is verified; meanings differ (explicit polarity vs a negation predicate) and are unreconciled. |

## 5. Roadmap

Ordered by dependency, not by appeal. Each step states its gate answer in brief; the full answer is written in its directive before work starts.

1. **Reuse audit** (ability 3, 6, 7; preparation). Name, for every requirement in the lasting-memory directive, the existing module, what it does, the exact gap and the smallest compatible change. Output: `docs/working/helm_reuse_audit_2026_10_06.md`. In progress.
2. **Memory contract v1** (ability 3; preparation). A versioned extension of the Revision Streams contract — identity, events, beliefs and answers, snapshots, RPA entries, update and conflict behavior, durability boundary — written before any persistence code, with its amendment log.
3. **Retention, first result** (ability 3; behavior). Teach a fact, show it changes a later answer, save accepted state, terminate the process, restore, show the same behavior without reteaching; then correct or retract it and show every dependent answer changes before and after restart. Control: fresh recompute from the accepted event history. Criterion: exact agreement on every deterministic case; zero stale fast-path answers; every acknowledged update recovered within the declared failure model. Every claim names which survival it showed: after a clean process exit on the same machine, or after the machine was replaced (owner decision, directive amendment log item 1).
4. **Guarded answer reuse and the RPA comparison** (ability 3 and 6; behavior and cost). Record-first behind a feature flag, whole-context invalidation first; four paths on identical work (fresh recompute, walk-first, record-first without RPA, record-first with RPA); common work units; a declared speed target with a paired confidence interval, reported as engineering choice not promise. If RPA adds no measured value, say so and keep the simpler path.
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

Related binding documents: `docs/working/revision_streams_contract_2026_10_06.md` (the semantics the memory contract extends); `docs/working/cas_rpu_revision_streams_2026_10_06.md` (the evidence for ability 1 and the ground of 3); `docs/working/cas_rpu_reasoning_processor_2026_08_28.md` (the processor).
