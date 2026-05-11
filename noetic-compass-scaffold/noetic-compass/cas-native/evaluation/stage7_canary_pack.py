"""Stage 7 v7.1 canary pack — fixed non-training records for sample reads.

Per user 2026-05-11. The canary pack is a small, hand-curated set of records
spanning the v1c grammar categories. It is NOT used for training; it is
fed to the model at sample checkpoints (steps 250/500/750/1000 + post-
training) for damage detection.

The point of the pack is to detect Phase-C-shape damage signatures (phrase
loops, truncation, stage variable corruption, notation leaks, generic
prose collapse, ABeing-style token boundary corruption) early, before
scalar metrics finish smoothing them away. Per user 2026-05-11:

  "scalar loss can look fine while samples show truncation, repetition,
   or identifier damage"
  "Stage 7 is architecture feasibility, not product quality. The sample
   question is: is it learning without developing Phase-C-shaped damage?"

Categories per user spec:
  - rpm_chain (long stage vars)
  - fractal k=7/8
  - recipe
  - meta-logic
  - state / binary / CRO controls
  - invalid_to_explanation controls

Records below are taken from real v1c training data but flagged as canary;
the trainer's stratified-sample loader does NOT need to exclude these
specifically (they're a small fraction of ~7000 records) — random sampling
will hit them at rate < 0.2%, statistically negligible.
"""
from __future__ import annotations

from typing import Any


CANARY_RECORDS: list[dict[str, Any]] = [
    # 1-2: rpm_chain with long stage var identifiers — Phase C's nemesis.
    {
        "id": "canary_rpm_chain_001",
        "trace_id": "canary_trace_rpm_chain_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain this rpm chain expression.",
        "reply_text": (
            "Let stageA0_5_0296 name a foundational thought, "
            "stageD5_5_0296 name practiced rhythm with agency."
        ),
        "cas_expression": "let stageA0_5_0296 = ^0^P; let stageD5_5_0296 = ^7^P_{F5}",
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
    },
    {
        "id": "canary_rpm_chain_002",
        "trace_id": "canary_trace_rpm_chain_002",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain this rpm chain expression.",
        "reply_text": (
            "Let stageA0_4_0049 name a foundational thought, "
            "stageD4_4_0049 name what triggered an evaluative judgment."
        ),
        "cas_expression": "let stageA0_4_0049 = ^0^P; let stageD4_4_0049 = ^8^P_{F4}",
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
    },
    # 3-4: fractal with k=7 and k=8 lengths — exercises the structure the
    # decoder needs to preserve without re-ordering or truncating.
    {
        "id": "canary_fractal_k7_001",
        "trace_id": "canary_trace_fractal_k7_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Describe this fractal sequence.",
        "reply_text": (
            "A seven-step fractal sequence starting from the universal idea, "
            "progressing through awareness, attraction, and resonance."
        ),
        "cas_expression": "Phi⟨0:1:2:4:5:6:7⟩",
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "fractal_sequence",
    },
    {
        "id": "canary_fractal_k8_001",
        "trace_id": "canary_trace_fractal_k8_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Describe this fractal sequence.",
        "reply_text": (
            "An eight-step fractal sequence beginning with idea, "
            "passing through mind, positive, negative, vibration, and rhythm."
        ),
        "cas_expression": "Phi⟨0:1:2:3:4:5:7:8⟩",
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "fractal_sequence",
    },
    # 5: recipe with Ω target + coefficients + drives.
    {
        "id": "canary_recipe_001",
        "trace_id": "canary_trace_recipe_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Describe this recipe.",
        "reply_text": (
            "To produce the outcome called grounding, combine two of "
            "principled attraction with one of operational thought."
        ),
        "cas_expression": "Θ(Ω_grounding) = 2*^2^P + 1*^0^O → Ω_grounding",
        "register": "T",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "recipe",
    },
    # 6: meta-logic — set-constructor expression.
    {
        "id": "canary_meta_logic_001",
        "trace_id": "canary_trace_meta_logic_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain this set-theoretic expression.",
        "reply_text": (
            "A partition expression claims that two groups together account "
            "for everything in a larger collection of cognitive operators."
        ),
        "cas_expression": "PartitionOf(NoeticCluster{^4, ^5, ^6, ^9}, NoeticCluster{^4}, NoeticCluster{^5, ^6, ^9})",
        "register": "A",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "meta_logic",
    },
    # 7: state_literal — simple compound state.
    {
        "id": "canary_state_literal_001",
        "trace_id": "canary_trace_state_literal_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Describe this cognitive state.",
        "reply_text": (
            "A thought in cognitive thinking, driven by a need for connection."
        ),
        "cas_expression": "^0^C_{F4}",
        "register": "T",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "state_literal",
    },
    # 8: binary_composition — operator composition.
    {
        "id": "canary_binary_001",
        "trace_id": "canary_trace_binary_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Describe this composition.",
        "reply_text": (
            "A sense of self in the cognitive arena integrated with "
            "a thought in the same arena."
        ),
        "cas_expression": "^5^C × ^0^C",
        "register": "T",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "binary_composition",
    },
    # 9: cross_register_omega — register product producing Ω target.
    {
        "id": "canary_cro_001",
        "trace_id": "canary_trace_cro_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Describe this cross-register composition.",
        "reply_text": (
            "Practice combined with felt resonance fuses into a unified "
            "state of presence."
        ),
        "cas_expression": "(^7|E × ^7|f) = ^7|Ω_presence",
        "register": "T",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "cross_register_omega",
    },
    # 10-11: invalid_to_explanation controls — model should EXPLAIN
    # the invalidity, not silently emit garbage.
    {
        "id": "canary_invalid_001",
        "trace_id": "canary_trace_invalid_001",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain why this expression is invalid.",
        "reply_text": (
            "The expression has empty angle brackets where a sequence "
            "of values should be — the fractal cannot be empty."
        ),
        "cas_expression": "Phi⟨⟩",
        "register": "A",
        "v1mix_task_type": "invalid_to_explanation",
        "v1mix_grammar_category_or_error_class": "fractal",
    },
    {
        "id": "canary_invalid_002",
        "trace_id": "canary_trace_invalid_002",
        "schema_version": "native_nl.v1",
        "tier": "tier3",
        "prompt_text": "Explain why this expression is invalid.",
        "reply_text": (
            "The expression contains a negative value in the fractal "
            "list, but the system does not allow negative numbers there."
        ),
        "cas_expression": "Phi⟨1:5:2:7:-1:9:9⟩",
        "register": "A",
        "v1mix_task_type": "invalid_to_explanation",
        "v1mix_grammar_category_or_error_class": "fractal",
    },
]


def canary_pack() -> list[dict[str, Any]]:
    """Return the fixed Stage 7 canary pack."""
    return [dict(r) for r in CANARY_RECORDS]
