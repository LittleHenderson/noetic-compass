# CAS 14-Capability Integrated-Path Status — 2026-08-20

## Decision

No capability is both integrated into the current product path and verified by the current real-model experiment.

| Strict class | Count | Capability IDs |
| --- | ---: | --- |
| `IMPLEMENTED_AND_REAL_MODEL_VERIFIED` | 0 | none |
| `ENGINEERED_NOT_RUN` | 2 | C06, C14 |
| `PARTIAL` | 12 | C01–C05, C07–C13 |
| `STUB` | 0 | none |
| `ABSENT` | 0 | none |
| **Total** | **14** | C01–C14 |

The real A40 experiment is `NOT RUN`. There is therefore no scientific PASS or FAIL. Pod `vernmyfb3ck9po` was stopped before source transfer, model load, forward pass, intervention, or capture; later same-ID starts failed for capacity. The current preregistration still says `FROZEN_DESIGN_ONLY_NO_EXECUTION_AUTHORITY`, `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`, and `NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE` (`docs/working/OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json:3,139-152`).

## Scope and classification rule

This review uses the strict **integrated-path** rule, not a repository-wide “some code or historical artifact exists” rule.

- Baseline commit: `11a43bb653bf2345200027b86ee83d3f9ca62461`.
- The cited core engine, adapter, public route, probe evaluator, ablation diagnostic, and text-filter files were unchanged from that commit at inspection time.
- Separate uncommitted RunPod receipt/guardian work was in progress. It is outside this capability classification and grants no execution authority.
- `IMPLEMENTED_AND_REAL_MODEL_VERIFIED` requires working mechanics in the current integrated path plus evidence from the current byte-attested real-model run.
- `ENGINEERED_NOT_RUN` means the named mechanical output is implemented, but the current real-model path has not executed it.
- `PARTIAL` means useful mechanics or historical evidence exist, but a required integration, scientific control, detector, or current-path run is missing.
- `STUB` means the capability is named and its requirements are represented, but no operational method was found.

The adapter itself preserves this boundary: every capability row has `evidence_status="NOT_RUN"` and serialized plans reject any other value (`noetic-compass-scaffold/noetic-compass/api/services/cas_harness_interpretability_adapter.py:343-361,699-739`).

## The integration break

There are currently two different paths:

1. The **CLI/canary path** dynamically loads `load_open_weight_runtime` and `capture_greedy_trajectory` in `scripts/run_open_weight_trajectory_canary_v2.py::_load_runtime_api`. Its preregistered two-token, nine-capture experiment is inert and has not run.
2. The **public live-worker path** imports `stream_fake_trace`, not the real engine (`live-trace-worker/app/routes/live_trace.py:21,57-63,84-92`). `model_loader.py:1-4` and `pythia_runner.py:1-8,30-44` explicitly remain milestone-1 stubs, while `event_stream.py:1-7,216-265` emits fake schema-valid data.

Consequently, the real engine is not the implementation behind `/sessions`, `/sessions/{id}/events`, or `/sessions/dump`.

## Per-capability status

| ID | Capability | Strict status | Current evidence and remaining gap |
| --- | --- | --- | --- |
| C01 | Hidden-state analysis | `PARTIAL` | The real engine registers every-layer residual and MLP hooks and stores full-width arrays (`engine.py:460-484,526-581,606-613`). The receipt contract states exactly what is captured (`engine.py:652-657`). The current canary never ran, and this engine is not behind the live route. |
| C02 | Layer sweeps | `PARTIAL` | The engine captures every registered decoder layer. The separate 40E evaluator implements group-disjoint train/validation/test splits, validation-only layer selection, and selection-aware shuffled-label control (`scripts/evaluate_40_element_probe.py:437-645`). That evaluator is not fed by a current byte-attested integrated dataset/run. |
| C03 | Probing | `PARTIAL` | Linear-probe evaluation, leakage-resistant grouping, registered splits, and shuffled-label controls are engineered (`evaluate_40_element_probe.py:404-645,708-826`). Historical activation artifacts do not promote this status: the evaluator explicitly records an unbound registered artifact as `NOT_PACKET_ELIGIBLE` and requires a new pre-capture receipt (`evaluate_40_element_probe.py:337-402`). |
| C04 | Pre-output trajectories | `PARTIAL` | Manual greedy generation saves a residual vector, MLP vector, and full pre-selection logits at each generation step before argmax selection (`engine.py:547-613`). The only current plan is two tokens (`OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json:60-70`), it has not run, and no W0/W1/Wk event semantics or matched temporal labels are integrated. |
| C05 | Pre-speech interception | `PARTIAL` | A step- and layer-targeted output-replacement hook exists (`engine.py:488-524`), but there is no integrated pre-speech detector, preregistered intercept rule, or real-path intervention result. Historical Qwen pre-speech detection/steering work remains separate and includes a clean control failure (`docs/working/steering_causal_result_20260611.md:1-25`). |
| C06 | Architecture discovery | `ENGINEERED_NOT_RUN` | Registered model-family profiles exist (`cas_harness_interpretability_adapter.py:59-127`). `discover_loaded_architecture` verifies the loaded config, decoder-layer count, hook APIs, and residual/attention/MLP paths, then emits `STRUCTURE_VERIFIED` (`:416-484`). This is fully engineered structure inspection, but the current A40 model path did not execute it. |
| C07 | Semantic circuit discovery | `PARTIAL` | Adapter discovery can locate attention/MLP modules, and candidate neuron-cover discovery exists, but that code labels its output candidate-only pending matched ablation (`scripts/discover_stage9_40e_neuron_covers.py:23-31,357-545`). The current engine explicitly records attention as `NOT_CAPTURED_IN_V1` (`engine.py:652-657`). No current integrated circuit has passed held-out semantic and matched-component controls. |
| C08 | Ablation | `PARTIAL` | The engine implements exact zero and vector patch replacement in-model (`engine.py:499-524`). The current zero/no-op canary is unexecuted. The Stage-9 “subspace ablation” is a separate feature-space projection/retrain diagnostic and explicitly does not emit a packet decision (`scripts/run_stage9_40e_subspace_ablation.py:2-14,337-465`). No current in-model matched-random plus patch-back causal result exists. |
| C09 | Matched controls | `PARTIAL` | The frozen design specifies baseline/no-op/zero × three repeats (`OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json:75-83`), and the runner has exact-schedule and same-input/runtime/seed checks in `expected_schedule` and `_evaluate_captures`. Those controls have not run and are not yet a reusable control bundle for probing, circuits, ablation, steering, and detectors. |
| C10 | Bounded causal steering | `PARTIAL` | `InterventionSpec` supports step/layer targeting and norm-bounded additive or patch vectors (`engine.py:60-132`), with the hook applying the vector at the chosen residual state (`:499-524`). The current canary exercises only planned zero/no-op mechanics, not additive steering. Dose schedules, same-norm random controls, stop rules, and collateral-harm rules remain external requirements (`cas_harness_interpretability_adapter.py:315-320`). |
| C11 | Prompt-injection detection | `PARTIAL` | A deterministic **text-surface** filter checks raw, zero-width-stripped, HTML, URL-decoded, and base64-decoded text (`cas-forex/cas_forex/pcba_prompt_injection.py:58-90`). This is not hidden-state detection or the open-weight engine. The production prevention claim remains `NOT_LICENSED` (`cas-forex/cas_forex/pcba_readiness.py:172-179`), and no current integrated hidden-state detector exists. |
| C12 | Hallucination detection | `PARTIAL` | The engine supplies residual/logit mechanics needed for a detector but implements no hallucination classifier. Historical leakage-safe KWIK work is real research evidence, not current-path evidence: its best larger-data floor reached `0.7553`, while residual `0.692` and held-out `0.7392` missed their gates; status remains `OPEN / NOT LICENSED` (`docs/working/hallucination_kwik_ceiling_findings_20260619.md:78-91,123-124`). |
| C13 | Reasoning-break detection | `PARTIAL` | Commit `bf0ec2eaafda5a45b579572f3e3b36281f06345e` adds an operational offline evaluator with independent labels, group-disjoint splits, W0/W1/Wk features, validation-only selection/calibration, abstention, surface and shuffled-label controls, preregistered gates, and deterministic provenance verification (`scripts/run_reasoning_break_detector_c13.py`; focused tests `21/21`). It remains synthetic/offline and has not consumed registered real-model captures or produced a scientific detector result. |
| C14 | Harness adapter generation | `ENGINEERED_NOT_RUN` | Commit `fd90d88e0eb99ee0339fa58830f66b920305786f` upgrades the deterministic 14-row manifest into hash-bound executable Python adapter artifacts with strict profile/config/path/class/API drift checks, side-effect-free capture/intervention attachment points, source reconstruction verification, and hostile-input defenses (`48/48` focused tests; hostile `P0/P1=0/0`). Loaded model bytes remain declared references rather than real-model-byte verified, and the current A40 path has not executed the adapter. |

## Claim boundary

Allowed claims:

- A local real-model capture/intervention engine is engineered.
- Architecture discovery and deterministic adapter-manifest generation are engineered but not run in the current A40 experiment.
- Twelve other capabilities have useful mechanics or bounded historical research evidence.
- The public live-worker route is still a fake/stub route.

Disallowed claims:

- No capability is `IMPLEMENTED_AND_REAL_MODEL_VERIFIED` in the current integrated path.
- The real A40 experiment did not pass or fail; it is `NOT RUN`.
- No current detector, semantic circuit, causal safety property, Evidence Packet, product license, or production-readiness claim follows from the engine, adapter plan, synthetic tests, or historical artifacts.
- Even a future canary PASS would prove only the exact frozen capture/no-op/zero engineering mechanics. The canary source says such a PASS remains `NOT_PACKET_ELIGIBLE` and `NOT_SCIENTIFIC_RESULT` (`run_open_weight_trajectory_canary_v2.py:1-17,87-95,125-136`).

## Prioritized post-canary roadmap

1. **Close the mechanical foundation only.** Obtain one successful, byte-attested, externally guarded canary and preserve its narrow engineering-only claim boundary.
2. **Build one provenance-correct shared probe dataset.** Feed the same full-width, all-layer captures into C01/C02/C03, with group-disjoint splits, frozen labels, surface controls, and reusable C09 metadata.
3. **Build one reusable causal-control bundle.** For C07–C10, require baseline/no-op, matched random same-rank or same-norm, wrong-layer/component, patch-back, dose response, stop rules, and collateral-effect measures.
4. **Extend temporal semantics.** Replace the two-token mechanical horizon with preregistered W0/W1/Wk windows, matched events, and interception timing for C04/C05.
5. **Validate detectors separately.** Treat hallucination (C12), prompt injection (C11), and reasoning break (C13) as three different studies, each with independent labels, leakage/surface controls, held-out groups, abstention policy, and prospective gates.
6. **Integrate the live worker last.** Replace `stream_fake_trace` and the stub loader/runner only after the real engine, provenance, controls, and detector-specific gates are stable. Keep the route private/default-dark until then.

## Uncertainties and audit limits

- This was a read-only static integration review. It did not execute tests, load a model, contact RunPod, or rerun historical experiments.
- Historical artifacts can demonstrate real earlier research within their own boundaries, but their provenance and schemas are not automatically admissible into the current byte-attested path.
- C13 now has an operational offline evaluator, but its classification remains only `PARTIAL` until registered real-model captures and independent labels drive a prospective run.
- Line numbers reflect the inspected 2026-08-20 worktree. Ongoing launch-transaction hardening may move lines in the preregistration or canary runner; symbol names and the baseline commit are the durable references.
