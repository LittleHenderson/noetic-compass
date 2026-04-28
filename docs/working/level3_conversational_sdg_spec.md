# Level 3 Conversational SDG Specification

## Purpose

Level 3 is the conversational training layer built on top of the Level 2 CAS synthetic dataset. Each record is a single supervised assistant turn: a user prompt, a conversational assistant response, a retained CAS expression target, soft operator/domain targets, and provenance linking the item back to the Level 2 source that supplied the structural CAS signal.

Level 3 is separate from Level 2 because it optimizes a different behavior. Level 2 teaches compiler-valid CAS notation and structural labels from sentence-pair examples. Level 3 teaches how to use those labels in dialogue: answering plainly, preserving uncertainty, asking a useful follow-up, and avoiding clinical, diagnostic, or predictive overclaiming. Keeping the layers separate prevents conversational style and safety constraints from contaminating the Level 2 structural dataset, while preserving traceability from every Level 3 example to a Level 2 source expression.

## Record Shape

Schema file: `cas-synthetic/schemas/level3_conversation.schema.json`

Required fields:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable Level 3 record identifier. Recommended prefix: `l3conv_`. |
| `source_level2_id` | string | Stable pointer to the Level 2 example, row, hash, or derived ID used as the structural source. |
| `bucket` | string | Source Level 2 bucket: `v74_baseline`, `v75_register`, `v77_rule_four`, `v77_omega`, `v76_production`, or `meta_logic`. |
| `cas_expression` | string | Compiler-valid CAS expression retained as the structural target. |
| `user_prompt` | string | User-facing conversational input for the assistant turn. |
| `natural_language_mapping` | string | Annotation explaining why the prompt maps to the CAS expression and soft targets. This is training metadata, not necessarily user-visible output. |
| `assistant_response` | string | Conversational answer the model should learn to produce. It may mention the CAS expression, but should not become a formula dump. |
| `follow_up_question` | string | A short open-ended question that continues the dialogue without forcing a diagnosis or conclusion. |
| `soft_operator_targets` | array[10] number | Distribution over Noetics `^0` through `^9`, ordered by index. Values are floats in `[0, 1]` and should sum to approximately `1.0`. |
| `soft_domain_targets` | object or array[4] number | Distribution over Domains P/C/E/O. Object form uses keys `P`, `C`, `E`, `O`; vector form is ordered `[P, C, E, O]`. Values should sum to approximately `1.0`. |
| `tags` | array[string] | Search and filtering labels. |
| `provenance` | object | Traceability metadata, including spec version, source dataset, generation method, and any reviewer notes. |

Recommended `provenance` subfields:

| Field | Meaning |
|---|---|
| `level3_spec_version` | Spec version used to produce the row, e.g. `0.1.0`. |
| `generation_method` | `manual`, `template`, `llm_assisted`, `human_reviewed`, or a composed value such as `template_plus_review`. |
| `level2_dataset` | Source Level 2 dataset name or file stem. |
| `level2_commit` | Commit or release ID for the source Level 2 dataset when available. |
| `level2_row_index` | Original JSONL row index when available. |
| `level2_hash` | Hash of the source Level 2 row or source expression when no stable row ID exists. |
| `conversation_id` | Optional grouping ID if multiple Level 3 turns belong to one synthetic dialogue. |
| `turn_index` | Optional zero-based turn index inside a grouped dialogue. |
| `notes` | Short traceability or review notes. |

## Target Semantics

`soft_operator_targets` and `soft_domain_targets` are soft distributions, not necessarily one-hot labels. Level 3 prompts often contain conversational ambiguity, mixed evidence, hedging, or multiple plausible readings. The distribution should encode the intended supervised emphasis for this turn.

Operator vector order:

| Index | Noetic |
|---|---|
| 0 | Idea |
| 1 | Mind |
| 2 | Positive |
| 3 | Negative |
| 4 | Vibration |
| 5 | Female |
| 6 | Male |
| 7 | Rhythm |
| 8 | Above/Cause |
| 9 | Below/Effect |

Domain vector order:

| Index | Domain |
|---|---|
| 0 | P, Principled |
| 1 | C, Cognitive |
| 2 | E, Evaluative |
| 3 | O, Operational |

## Quality Gates

Blocking gates:

- `cas_expression` must compile through the CAS compiler. Level 3 should not wrap deliberate Level 2 invalid examples unless a separate negative-conversation schema is introduced.
- `soft_operator_targets` must contain exactly 10 finite numbers in `[0, 1]`, and `abs(sum - 1.0) <= 0.001`.
- `soft_domain_targets` must contain exactly P/C/E/O as either a four-key object or a length-4 vector, with finite values in `[0, 1]`, and `abs(sum - 1.0) <= 0.001`.
- `assistant_response` must not claim diagnosis, mental-health status, intent, future behavior, risk certainty, or prediction. Acceptable phrasing: "CAS would frame this as...", "This suggests...", "One possible reading is...". Avoid: "You are...", "This proves...", "This predicts...".
- `assistant_response` must be conversational rather than math-heavy. Default target: 1-4 short paragraphs, plain-language first, at most one CAS expression unless the prompt explicitly asks for notation.
- `follow_up_question` must be open-ended, relevant to the mapping, and not leading the user toward a fixed conclusion.

Review gates:

- `natural_language_mapping` should identify the main prompt evidence for the dominant Noetic and Domain.
- `assistant_response` should preserve the same meaning as `natural_language_mapping` while being suitable for an end user.
- `tags` should include `level3`, `conversational`, the source bucket, and at least one semantic label.
- `source_level2_id` must resolve to an auditable Level 2 row, row hash, or generation artifact.

## Example Records

```json
{
  "id": "l3conv_v1_000001",
  "source_level2_id": "level2_full_10k:row_000123",
  "bucket": "v74_baseline",
  "cas_expression": "^2^C_{F3}",
  "user_prompt": "I'm excited by the proposal, but I want to think it through before acting. How would CAS frame that?",
  "natural_language_mapping": "The prompt centers on attraction toward an idea in the cognitive domain, with secondary evidence for reflection and action-readiness.",
  "assistant_response": "CAS would frame this as being drawn toward an idea while still keeping it in the thinking lane. A compact representation is `^2^C_{F3}`: affinity in the cognitive domain with some movement toward engagement. That is a reading of the moment, not a diagnosis or prediction.",
  "follow_up_question": "What part of the proposal feels most compelling: the idea itself, the values behind it, or the practical next step?",
  "soft_operator_targets": [0.0, 0.0, 0.74, 0.0, 0.0, 0.06, 0.08, 0.0, 0.07, 0.05],
  "soft_domain_targets": {"P": 0.06, "C": 0.78, "E": 0.08, "O": 0.08},
  "tags": ["level3", "conversational", "v74_baseline", "attraction", "cognitive-domain"],
  "provenance": {
    "level3_spec_version": "0.1.0",
    "generation_method": "manual_spec_example",
    "level2_dataset": "level2_full_10k",
    "level2_row_index": 123,
    "notes": "Illustrative example."
  }
}
```

```json
{
  "id": "l3conv_v1_000002",
  "source_level2_id": "level2_full_10k:row_001047",
  "bucket": "v75_register",
  "cas_expression": "^3^E_{F2}|f",
  "user_prompt": "I have a gut-level no about this policy, even though I have not fully argued it out yet.",
  "natural_language_mapping": "The user describes felt aversion rather than analytical critique, so the dominant target is Negative in the Evaluative domain with affective register.",
  "assistant_response": "CAS would treat that as a felt evaluative refusal rather than a completed argument. The notation `^3^E_{F2}|f` marks aversion in the evaluative domain, carried in the affective register. It does not mean the policy is wrong; it means the response you described is a felt negative signal that may deserve examination.",
  "follow_up_question": "What evidence would help you tell whether the gut-level no is tracking a real concern or just an initial reaction?",
  "soft_operator_targets": [0.0, 0.06, 0.0, 0.82, 0.08, 0.0, 0.04, 0.0, 0.0, 0.0],
  "soft_domain_targets": [0.08, 0.08, 0.76, 0.08],
  "tags": ["level3", "conversational", "v75_register", "felt-aversion", "evaluative-domain", "affective-register"],
  "provenance": {
    "level3_spec_version": "0.1.0",
    "generation_method": "manual_spec_example",
    "level2_dataset": "level2_full_10k",
    "level2_row_index": 1047,
    "notes": "Uses vector-form domain targets ordered P/C/E/O."
  }
}
```

```json
{
  "id": "l3conv_v1_000003",
  "source_level2_id": "level2_full_10k:row_004812",
  "bucket": "v77_omega",
  "cas_expression": "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_refusal",
  "user_prompt": "Part of me can explain why this crosses a line, part of me just feels the no, and part of me sees it as a values issue.",
  "natural_language_mapping": "The prompt describes same-Noetic principled refusal across analytical, affective, and transcendent registers, requiring a named emergent rather than bare cross-register multiplication.",
  "assistant_response": "CAS would not reduce that to a single simple objection. It reads like several registers converging around a principled boundary: an argument, a felt no, and a values-level orientation. The named-emergent form captures that convergence, while still leaving room to check facts before deciding what action follows.",
  "follow_up_question": "Which register feels strongest right now: the argument, the felt boundary, or the values-level concern?",
  "soft_operator_targets": [0.0, 0.05, 0.0, 0.8, 0.05, 0.0, 0.05, 0.0, 0.05, 0.0],
  "soft_domain_targets": {"P": 0.7, "C": 0.1, "E": 0.15, "O": 0.05},
  "tags": ["level3", "conversational", "v77_omega", "rule-four", "refusal", "principled-domain"],
  "provenance": {
    "level3_spec_version": "0.1.0",
    "generation_method": "manual_spec_example",
    "level2_dataset": "level2_full_10k",
    "level2_row_index": 4812,
    "notes": "Illustrates named emergent requirement for same-Noetic cross-register integration."
  }
}
```

```json
{
  "id": "l3conv_v1_000004",
  "source_level2_id": "level2_full_10k:row_008390",
  "bucket": "meta_logic",
  "cas_expression": "NoeticCluster{^2, ^7} ⊆ Noetics",
  "user_prompt": "Can CAS talk about attraction and repetition together without saying they are the same thing?",
  "natural_language_mapping": "The user asks for a set-level relation over two Noetics, so the correct response should preserve distinction while grouping both under the Noetics carrier.",
  "assistant_response": "Yes. CAS can group Positive and Rhythm as members of a Noetic cluster without collapsing them into one operation. In plain terms, attraction and repetition can be discussed together as related ingredients while remaining distinct dynamics.",
  "follow_up_question": "Are you trying to compare the two dynamics, or describe how they work together in one situation?",
  "soft_operator_targets": [0.0, 0.05, 0.45, 0.0, 0.0, 0.0, 0.05, 0.45, 0.0, 0.0],
  "soft_domain_targets": {"P": 0.25, "C": 0.25, "E": 0.25, "O": 0.25},
  "tags": ["level3", "conversational", "meta_logic", "noetic-cluster", "set-relation"],
  "provenance": {
    "level3_spec_version": "0.1.0",
    "generation_method": "manual_spec_example",
    "level2_dataset": "level2_full_10k",
    "level2_row_index": 8390,
    "notes": "Meta-logic example uses uniform domain distribution because the expression is carrier-level, not domain-anchored."
  }
}
```

## Implementation Notes

- This specification defines dataset shape only. It does not require changes to the Level 2 generator, existing validators, or tests.
- JSON Schema validates field shape and scalar ranges. A Level 3 validator should add compiler checks and distribution-sum checks.
- If the Level 2 source lacks explicit `id` values, compute `source_level2_id` from `{dataset_name}:row_{zero_padded_index}` and include a source-row hash in `provenance.level2_hash` when possible.
