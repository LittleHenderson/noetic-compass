# CNCM-RRK v0.1 Handoff

This directory contains a working, bounded CAS Native Cognitive Machine reference demonstrator. It executes strict typed symbolic problems deterministically, mediates all state changes through authorized intents, reconstructs proofs and control identities, retains a sealed hash-linked trace, and emits a self-checking evidence packet.

The bounded CNCM runtime is not complete CAS/TKS semantics, full CCDL, general-English understanding, a neural runtime, AGI, production software, or a CAS Reasoning Qualification Standard (CRQS) evaluator. This homebase also contains an isolated, untrained `research/CASFORMER_v0_1` neural reference package; the runtime does not import it and it has no CNCM authority.

## Owner playground

The bounded reference demonstrator is available through the private, owner-only [CNCM-RRK Playground](https://cncm-rrk-native-playground.wakil.chatgpt.site). It runs the exact Python package in a dedicated browser Web Worker through a content-checked, self-hosted Pyodide runtime. **Chat With This Mind** accepts a frozen controlled-English subset for facts, rules, questions, negative propositions, pronouns, and clarification. **Language Apprenticeship** executes the isolated proposal-only grammar laboratory for passive voice, role reversal, negation, local identity-separated qualification, retention receipts, and the teacher-commit authority attack. **Cognitive Faculty** executes the isolated CCB-T1 laboratory for exact reasoning/math instruction, a permission-aware tool procedure without external action, source-required changing knowledge, and protected-authority rejection. **Exact Math** exposes checked linear proofs, canonical rational results, deterministic bounded counterexamples, proof receipts, and semantic re-execution. Problem Lab retains editable JSON, all eight RRK kernel fixtures, receipt verification, exact replay, downloads, and same-session episodic memory.

The conversation mode is a deterministic language facade, not a general chatbot. It uses no Transformer or network model, admits no arbitrary prose, has no tool/action authority, and earns no `CONV`, language, CRQS, evidence-tier, or deployment-authority result. Unsupported input and unresolved references fail closed.

The language-apprenticeship laboratory is also bounded. Its local grammar store, provisional/durable labels, and rollback lineage are experimental artifacts only. It writes no CNCM `MachineState`, has no CAS-RRK promotion receipt, does not alter the conversation facade, and is not evidence of general English or kernel-authorized R1 learning.

The domain-neutral CCB-T1 laboratory has the same hard boundary. Teacher and faculty roles are typed local records, not live models. Its CAS-SDG expansion is a deterministic local analogue, not a connected CAS-SDG service. Its TeachingEpisodes, qualification/retention receipts, before/after CAS-Ohm-shaped observations, and local versions do not enter `MachineState`, CAS-GEM, procedural memory, constitutional memory, or CAS-RRK. Correct refusal is the required result for a changing fact without current source custody and for any protected-authority mutation.

## Protected boundary

All work for this implementation is contained in this directory. The sibling `../CAS_RRK_v0.1` is a no-touch boundary owned by another workstream and was not used as source, modified, or incorporated here. `cas_reasoner.txt` remains the source charter; this handoff narrows its broad capability request to the honestly implemented v0.1 subset.

## Requirements

- Python 3.11 or newer.
- The runtime package has no third-party dependencies.
- `pytest` is needed for the documented test command.
- The isolated CASformer research package additionally needs PyTorch.

## Verify first

Run these commands from this directory:

```powershell
python -m pytest -q
python tools/verify_goldens.py
python -m cncm demo --fixtures fixtures
```

Verify the isolated, non-authoritative CASformer research package separately:

```powershell
Push-Location research/CASFORMER_v0_1
python tools/validate_all.py
Pop-Location
```

That command regenerates its source manifest, runs its core engineering checks,
runs both its own and the existing CNCM pytest suites, runs one untrained
forward example, and writes a local completion receipt. It performs no neural
training, network call, GPU job, CNCM state write, or authority action.

The commands' current output is the receipt. Do not rely on a copied test count or manifest digest: both intentionally change when the frozen runtime, source charter, or retained artifacts change.

These commands are v0.1 engineering-conformance checks. The current tests and goldens are not CRQS qualification, protected or held-out capability tests, evidence-tier certification, authority assessment, or reference-model benchmarking. This implementation has earned no `D0`-`D10`, `CAS-G`, Capability Vector (`CV`), `E-Tier`, `A-Level`, or Reference Model Benchmark (`RMB`) result.

## Run one problem

```powershell
python -m cncm check --problem fixtures/deduction/problem.json
python -m cncm run `
  --problem fixtures/deduction/problem.json `
  --trace out/deduction.trace.json `
  --final-state out/deduction.state.json `
  --evidence out/deduction.evidence.json `
  --bundle out/deduction.bundle.json
python -m cncm verify --bundle out/deduction.bundle.json
python -m cncm replay --problem fixtures/deduction/problem.json --against out/deduction.bundle.json
```

CLI exit codes are 0 for success, 2 for parse/input/I/O errors, 3 only for a completed runtime `FAULT`, and 4 for replay or verification mismatch.

## Current fixture results

| Fixture | Cold-run terminal status |
|---|---|
| `branch_rollback` | `CONCLUDED` |
| `contradiction` | `CONFLICT_UNRESOLVED` |
| `deduction` | `CONCLUDED` |
| `memory_recall` | `NEEDS_INFORMATION` |
| `missing_information` | `NEEDS_INFORMATION` |
| `rpm_failure` | `NEEDS_INFORMATION` |
| `rpm_recursion` | `CONCLUDED` |
| `transitive_reasoning` | `CONCLUDED` |

`memory_recall` is intentionally cold in its standalone fixture. The warm path is: run `deduction` on one persistent `CognitiveMachine`, then run `memory_recall` on that same instance. The first committed episode enables exact recall in the second run.

## Python host API

```python
import json
from pathlib import Path

from cncm.api import replay, run, verify_evidence

problem = json.loads(Path("fixtures/deduction/problem.json").read_text(encoding="utf-8"))
result = run(problem)
assert verify_evidence(result.to_dict()).valid
assert replay(problem, result.trace).matches
```

For persistent episodic behavior, instantiate `CognitiveMachine` and reuse it across runs. `RunResult` retains the exact `initial_episodic_memory` used by the run; engine-level replay uses that snapshot and compares final state, trace, and evidence exactly.

Public nonempty episodic-memory injection is rejected by `CognitiveMachine`, `boot_state`, and the host API. The only admitted warm paths are records learned inside one persistent `CognitiveMachine` and the private snapshot used by engine-level `RunResult` replay. `_from_trusted_snapshot` and other underscore APIs are trusted same-process implementation boundaries, not security controls; they do not cryptographically prove snapshot ownership. There is no public durable restore/import path in v0.1, and `verified=True` is not an import credential.

## Controlled conversation API

```python
from cncm import ConversationalMind

mind = ConversationalMind()
mind.turn("Alice is human.")
mind.turn("Every human is mortal.")
answer = mind.turn("Is Alice mortal?")
assert answer.status.value == "ANSWERED"
assert answer.trace.execution_parity["matches"] is True
```

The accepted forms are `Name is property.`, `Name is not property.`, `Every property is [not] property.`, `Is Name|he|she|they|it [not] property?`, and the clarification reply `I mean Name.`. Dialogue facts and rules persist only inside one `ConversationalMind`; `reset()` clears them. They are explicit user assertions, not authenticated external truth.

## Exact CAS-Math API

```python
from cncm import (
    find_math_counterexample,
    solve_math,
    verify_counterexample_result,
    verify_math_result,
)

proof = solve_math("2*(x+3)=14", "x")
assert str(proof.solution) == "4"
assert all(step.receipt.accepted for step in proof.checked_steps)
assert verify_math_result(proof.to_dict()).valid

counterexample = find_math_counterexample(
    "x*x<5",
    [{"variable": "x", "lower": -3, "upper": 3}],
)
assert counterexample.status.value == "FOUND"
assert verify_counterexample_result(counterexample.to_dict()).valid
```

CAS-Math v0.1 is exact and bounded. It supports integers, rationals, explicit
arithmetic, equality, strict less-than, cited substitution, transitivity,
one-variable linear equations, checked proof steps, and bounded-integer
counterexamples. The bounded protected checker is a pure reconstruction
service with no state-write authority. Checked claims require content-bound,
semantically re-executable receipt chains; fixed theory/branch/checker IDs and
nonlinear fail-closed checks are enforced. Math receipts are not yet integrated
into RRK `MachineState`; mathematical strategy learning remains unimplemented.

## Verified language-apprenticeship API

```python
from cncm import run_language_qualification_demo

passive = run_language_qualification_demo("passive_voice")
assert passive["semantic_law"]["active_equals_passive"] is True
assert passive["semantic_law"]["role_reversal_remains_different"] is True
assert passive["authority_boundary"]["cncm_state_writes"] == 0

attack = run_language_qualification_demo("teacher_cannot_commit")
assert attack["active_count"] == 0
assert attack["active_digest_before"] == attack["active_digest_after_submission"]
```

The accepted cases are `passive_voice`, `negation`, and
`teacher_cannot_commit`. Each invocation starts from a fresh, isolated local
store and returns canonical JSON primitives. This is an executable CCB-L1-GRAM
laboratory, not the current CNCM conversation parser or an authority-bearing
kernel component.

## Cognitive-apprenticeship API

```python
from cncm import (
    cognitive_apprenticeship_demo_cases,
    run_cognitive_apprenticeship_demo,
)

assert cognitive_apprenticeship_demo_cases() == (
    "exact_reasoning_math",
    "tool_use_procedure",
    "source_grounded_changing_fact",
    "protected_authority_rejection",
)

lesson = run_cognitive_apprenticeship_demo("exact_reasoning_math")
assert lesson["authority_boundary"]["cncm_state_writes"] == 0
assert lesson["authority_boundary"]["cas_rrk_commits"] == 0

attack = run_cognitive_apprenticeship_demo("protected_authority_rejection")
assert attack["authority_boundary"]["cas_rrk_promotion_receipt"] is False
```

Every invocation starts from a fresh isolated CCB-T1 local store. The four
demonstrations exercise a domain-neutral lesson contract and honest stopping
behavior; they do not prove that the CNCM learned a general domain, retained a
kernel skill, used a live teacher, called the external CAS-SDG, or obtained R1
promotion.

The Cognitive Faculty interface includes an **AWS 20B** teacher-source control,
but it is intentionally `OFF / SETUP REQUIRED`. A live connection requires a
server-side AWS Bedrock adapter, region, exact model ID, credentials, budget,
and timeout policy. No AWS secret belongs in the browser, and any future AWS
model remains a proposal-only teacher under the same examination law.

## Artifact map

- `cncm/model.py`: immutable packet, state, branch, RPM, proof, intent, and trace types.
- `cncm/semantics.py`: unification, Horn inference, decomposition, contradiction, and RPM child proof reconstruction.
- `cncm/kernel.py`: authority matrix, boot state, sole writer, atomic transactions, commitment, learning, and trace chain.
- `cncm/engine.py`: deterministic episode driver, evidence generation, and exact replay.
- `cncm/language_apprenticeship.py`: immutable lesson/construction/frame records, bounded non-eval grammar compiler, independent local qualification and retention receipts, version lineage, quarantine, supersession, rollback, and browser-safe demonstrations.
- `cncm/cognitive_apprenticeship.py`: domain-neutral proposal-only teacher roles and transfer channels, prerequisite and local expansion evidence, bounded qualification/retention receipts, TeachingEpisodes, protected-category rejection, CAS-Ohm-shaped observations, local lineage/rollback, and four browser-safe demonstrations.
- `cncm/verification.py`: retained-bundle hash and binding verification.
- `cncm/api.py`: stable host-facing boot/run/step/replay/verify surface.
- `cncm/conversation.py`: controlled-English parser, immutable dialogue state, bounded reference clarification, packet compiler, verified renderer, and same-packet fresh-machine execution-parity check.
- `cncm/math_model.py`, `math_parser.py`, `math_normalize.py`: immutable exact CAS-Math IR, frozen notation grammar, exact evaluation, and canonical linear forms.
- `cncm/math_kernel.py`: bounded protected proof-step reconstruction, checked-claim issuance, receipt-chain validation, and no write authority.
- `cncm/math_engine.py`, `math_counterexample.py`, `math_api.py`: checked linear proof orchestration, deterministic counterexample search, host API, and semantic proof/search re-execution.
- `cncm/cli.py`: explicit filesystem host adapter.
- `schemas/`: strict Draft 2020-12 kernel, conversation, CAS-Math, CAS-Ohm, language-apprenticeship, and CCB-T1 wire contracts.
- `spec/`: reconciled semantic, IR, runtime, authority, conformance, conversation, language-board, dialogue-board, grammar-apprenticeship, cognitive-apprenticeship, and CAS-Ohm attention-integration contracts. The exact Phase 0 set now includes `CAS_CORE_ONTOLOGY_v0.1.md`, `FOUNDATION_DRIVE_ADAPTER_v0.1.md`, `COMPILER_RUNTIME_BOUNDARY_v0.1.md`, `CAS_KERNEL_IR_v0.1.md`, `NON_GOALS_v0.1.md`, and `CONFORMANCE_PLAN_v0.1.md` alongside the root manifest. The apprenticeship specifications have executable local companions but no kernel authority; `CAS_OHM_ATTENTION_INTEGRATION_PROTOCOL_v0.1.md` remains an adopted follow-on contract, not an implemented Phase 0 runtime feature.
- `research/CASFORMER_v0_1/`: isolated PyTorch reference code for positive CAS-Ohm routing, local relation-ID-selected operators, a CJT-inspired flow gate, a causal language-model shell, signed differential conductance, a passive graph solve, checksum-bound contract-checked non-authoritative traces, tests, source bindings, and an engineering receipt. The relation IDs are not canonical CAS-Sem types, breakdown deliberately fails closed instead of simulating destructive source behavior, and caller tick metadata is not provenance proof. It is untrained, not imported by `cncm`, and establishes no language, reasoning, CAS-advantage, authority, or production result.
- `fixtures/`, `golden/`, `tests/`: eight RRK and six CAS-Math retained fixture definitions, exact executable outputs where implemented, explicit contract-only status where absent, and executable checks.
- `tools/generate_goldens.py`: intentional golden regeneration.
- `tools/verify_goldens.py`: non-mutating golden/bundle verification.
- `playground/`: owner-only browser laboratory for the exact bounded runtime.
- `docs/`: gap analysis, code map, compiler boundary, and roadmap.

## Local external dependency inventory

- The current standalone CAS compiler is `C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\api\notation\compiler.py`; its CLI entry point is `python -B -m api.notation "<expression>" --mode run` from the `noetic-compass` directory. CNCM has not yet integrated this compiler.
- The current CAS Synthetic Data Generator is `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic`. Its datasets and generators remain external inputs; CNCM has no adapter, and any future imported expression must be independently recompiled and validated through the real compiler before admission.
- These systems were discovered and verified read-only. They are not copied into CNCM, and neither external directory is a CNCM write target.

## Frozen boundaries

- Problem schema is `cncm.problem/0.1`; evidence schema is `cncm.evidence/0.1`; runtime is `0.1.0`.
- CAS-Math result/evidence/checker versions are `cncm.math-result/0.1`, `cncm.math-evidence/0.1`, and `cncm.math-checker/0.1`; the only current theory is `cncm.q-linear/0.1`.
- SHA-256 values are plain 64-character lowercase hex strings.
- Canonical mappings require string keys recursively; floats, NaN, and Infinity are rejected from authoritative intents.
- Candidates and RPM resolvers are caller-declared; candidate generation is not implemented.
- Candidate ID `root` is reserved. Candidate IDs, branch IDs, resolver targets, resolver-local fact/rule IDs, and input intent IDs are uniqueness-checked.
- RPM is exact missing-premise resolution, not D/W/P semantics.
- Proof search is iterative and deterministic: at most one next proof per call, with a 4,096 antecedent-match expansion ceiling. RPM charges only the exact target-producing proof prefix; a truncated closure is budget exhaustion.
- Only asserted roots and verified recall/RPM/ordinary-proof chains with authoritative premises can support decomposition, classification, comparison, commitment, or a final conclusion. Hypothetical-only support is excluded.
- Comparison covers every declared reasoning branch from current decomposition/inference closure and is one-shot, as are selection, commitment, and episodic write. Root discard is admitted only for exact completed candidate expansion.
- Foundations/Sub-Foundations, Foundation-to-Drive mapping, D/W/P, `^0`-`^5`, and `^7` remain `OPEN-SEMANTICS`.
- All seven required Phase 0 artifact names exist, but that presence does not close Phase 0 while those semantic decisions, Prime Desire identity, complete conflict disposition, and final acceptance remain open.
- External actions and protected patching are typed but always rejected.
- Only working-state changes and a committed episodic write are admitted; semantic, procedural, architectural, kernel, and constitutional learning are prohibited.
- Standalone CAS-Math may create immutable checked receipts, but those receipts do not bypass RRK state authority and are not durable learning writes.
- The verified language-apprenticeship laboratory may create and activate versions only inside its isolated local store. Its receipts are not CNCM intents, it performs zero `MachineState` writes, and its promotion labels do not imply CAS-RRK authorization.
- The CCB-T1 cognitive-apprenticeship laboratory may create local TeachingEpisodes and versions only inside a fresh isolated store. Teacher-role labels, deterministic development expansion, qualification/retention receipts, and CAS-Ohm-shaped before/after observations are local evidence artifacts. They are not live teacher/CAS-SDG/CAS-Ohm integrations, CNCM intents, durable skill memory, or CAS-RRK authorization.
- `cncm.cas-ohm-stage/0.1` is a contract-only post-seal diagnostic sidecar. Runtime `0.1.0` neither reads nor emits it, and no CAS-Ohm scheduler, resource allocator, retrieval controller, or authority path is active. A future scheduler requires a separate pre-schedule `AttentionAllocationPlan`; it cannot consume this diagnostic record as a command.
- Component-requested `NEEDS_CAPABILITY`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, and `FAULT` are unavailable. `FAULT` is reserved for the kernel's final-tick fail-safe.
- The CRQS v0.1 qualification-bench appendix at source lines 10031-11171 is `PROPOSED-NOT-IMPLEMENTED` and `OPEN-SPECIFICATION`. None of its grading bands, gates, metrics, reports, benchmarks, or repair semantics is part of the runtime contract.
- The conversational-mind/chatbot material at source lines 11172-11834 is partially realized only by the frozen v0.1 conversation contracts, six schemas, eight fixture families, the bounded controlled-English facade, and **Chat With This Mind** playground. The complete-machine append at lines 11835-13786 adds a governed neural cortex, retrieval fabric, training pipeline, verifier federation, causal ablations, and phased qualification requirements; lines 13787-14616 add Verified Cognitive Apprenticeship and Learnable English. Those larger systems remain absent or partial as recorded in `docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md`.

## Important limitations

- Typed packet rules have provenance but no authenticated rule-source registry.
- Durable episodic import/restore is unavailable; a future authenticated adapter and policy remain open.
- The serialized bundle omits the initial episodic snapshot, so warm replay is not self-contained from the bundle alone.
- `verify_bundle` checks retained structural/hash/identity and evidence projections; it does not authenticate storage, packet truth, or the omitted warm-memory snapshot.
- No CNCM-integrated general-English or CCDL compiler, native `^8` candidate generator, substantive P/C/E/O evaluator, D/W/P model, external action layer, durable database, crash recovery, or production hardening exists. A separate local CAS compiler is available, but the typed bridge and admission tests are absent.
- CAS-Ohm attention allocation and CAS-GEM/CMB-R1 reconstructive episodic memory remain follow-on systems for runtime `0.1.0`. The isolated `research/CASFORMER_v0_1` package executes a non-authoritative neural routing reference, but there is no active CNCM attention scheduler, neural calibration corpus, trained cortex, reconstructive retrieval engine, memory capsule pipeline, or hot/warm/cold memory tier.
- The appended CAS Foundry/Cognitive Board Studio/CADA concept is not implemented: the playground is not a Foundry canvas, board editor, collaboration layer, registry, or publishing service. That follow-on must begin with a frozen Board Ontology/Capability Specification.
- The appended CRQS concept is also not implemented: there is no task-difficulty grader, CAS-G evaluator, Capability Vector scorer, evidence-tier evaluator, deployment-authority evaluator, reference-model benchmark, protected qualification suite, anti-gaming harness, repair engine, or qualification-bench UI. Capability, evidence maturity, and deployment authority remain separate concepts; this runtime does not infer one from another.
- The full conversational-mind concept is not implemented. The bounded facade resolves only its frozen pronoun forms, retains only explicit in-session dialogue facts/rules, and renders fixed trace-grounded responses. The separate grammar laboratory and untrained CASformer research package do not alter that path. There is no CNCM-integrated general English encoder/decoder, native lexical acquisition, full CCB-L1 or CCB-D1, trained hybrid Transformer peripheral, persistent correction learning, durable language memory, voice/tool dialogue, or conversational qualification suite.
- The broader cognitive-faculty concept is not implemented as a live learning system. The local CCB-T1 demonstrations do not provide autonomous world-knowledge acquisition, strategy installation, code execution, external tools, research, semantic/procedural consolidation, metacognitive policy learning, social learning, creativity, board construction, self-repair, neural distillation, or multimodal grounding. Each requires its own verifier, protected custody, native destination, and governed promotion path.

See `docs/CODEX_GAP_ANALYSIS.md` before extending claims or scope.
