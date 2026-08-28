# cas-rr — CAS Reasoning Runtime v0.1

A native CAS reasoning machine. Not a harness around a model — a
deterministic symbolic interpreter in which the reasoning states are CAS
states, the transformations are CJT transitions, memory is a CMB, plans
are RPM recursion, comparison is CDAB, and the final conclusion is
produced by an internal CAS trace. No LLM is anywhere in the loop; there
is no randomness; there are no runtime dependencies beyond the standard
library.

## What it contains

- CJTs with typed biases and all four operating regions (cutoff, active,
  saturation, breakdown) — cas_rr/cjt.py
- The 7 Foundation goal engines and 28 sub-foundation channels with the
  Foundation-to-Drive adapter — cas_rr/foundations.py, ontology.py
- CMB memory: 40 cells, three leakage layers, structural query, typed
  lacunae (KNOWLEDGE_MISSING / EXPERIENCE_MISSING) — cas_rr/memory.py
- The ^8 / ^6 / ^9 reasoning spine: association generates candidates,
  unity-gain decomposition and inference land proven conclusions with
  full originating paths — cas_rr/candidates.py, reasoning.py
- CDAB comparison under shared bias and matched gain, with a tournament
  tree — cas_rr/compare.py
- RPM D -> W -> P recursion stack with typed subgoals and re-measurement
  (section-retraction, no assumed reversibility) — cas_rr/rpm.py
- Schmitt commitment with five typed gates and seven typed halt states —
  cas_rr/commit.py
- P -> C -> E -> O domain descent, O-last boot, diode-enforced direction
  — cas_rr/domains.py
- Low-gain filtered learning; procedural and constitutional layers
  disabled in v0.1 — cas_rr/learning.py
- Append-only trace and the Reasoning Provenance Packet — cas_rr/trace.py
- The machine loop: 12 phases, deterministic scheduler, budget and tick
  stop gates — cas_rr/runtime.py

## Quickstart

    cd cas-rr
    python -m pytest

Expected: 25 passed. The suite covers the six-task native-reasoning
battery, negative variants exercising all seven halt states, and the five
load-bearing laws.

## One reasoning episode

    from cas_rr.runtime import CASRuntime, default_constitution
    from tasks.battery import task_transitive

    packet = CASRuntime(default_constitution(), task_transitive()).run()
    print(packet["terminal_status"])   # CONCLUDED
    print(packet["output"]["conclusion"])  # precedes(a,c)

The packet carries the whole trace: memory retrievals with lacunae,
candidate amplifications, decomposition probes, inference proof paths,
comparison reports, RPM scans, commitment gates, and learning
dispositions.

## Claims boundary

This is a testable reasoning architecture, and nothing more: it executes
its own rules deterministically over CAS-encoded inputs. It does not
claim consciousness, empirical general intelligence, or that CAS-Ohm is
a physical law. CAS-Ohm quantities appear only as authored design
quantities inside the attention budget. The three source documents'
boundaries are honored in code and in the spec.

## Specifications

- docs/cas_rr/CAS_RR_V0_1_SPEC.md — operational semantics, 18 chapters
- docs/cas_rr/CCB_R1_BOARD_SPEC.md — the motherboard architecture
- docs/cas_rr/SOURCE_GROUNDING_NOTES.md — verbatim citations for every
  load-bearing claim
