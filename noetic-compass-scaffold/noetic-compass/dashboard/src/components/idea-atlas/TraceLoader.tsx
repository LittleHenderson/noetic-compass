import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type AtlasTrace,
  TRACE_SCHEMA_VERSION,
  validateAtlasTrace,
} from '../../lib/trace';

// ── Bundled demo trace ──
//
// A minimal, fully-valid traceability_v0 trace. Mirrors the shape
// `build_v0_trace` emits for the prompt "explain a thought becoming
// action" — the canonical sample we tell stakeholders to try.
//
// This is embedded (not fetched) so the demo button works offline and
// without a backend.
export const DEMO_TRACE: AtlasTrace = {
  schema_version: TRACE_SCHEMA_VERSION,
  trace_id: '00000000-0000-4000-8000-000000000000',
  created_at: '2026-05-13T17:30:00Z',
  input: {
    input_kind: 'nl_bridge',
    user_text: 'explain a thought becoming action',
    cas_expression: '^9^O',
    source_tokens: [{ index: 0, token: '^9^O' }],
    nl_bridge: {
      matched_pattern: 'thought becoming action',
      confidence: 0.95,
      rationale: 'Below/Effect in the Operational domain.',
      inferred_cas_expression: '^9^O',
    },
  },
  output: {
    english:
      'Below/Effect in the Operational domain — a thought landing as behavior.',
    n_tokens: 18,
  },
  copy: {
    copied_identifiers: [],
    missed_identifiers: [],
    coverage: null,
    per_identifier: [],
  },
  slot_trace: {
    length: 18,
    slot_counts_by_label: { 'joining word': 18, 'named identifier': 0 },
    longest_stage_var_run: 0,
    raw_trace: null,
  },
  confidence: {
    qualitative_coverage: 'strong',
    slot_quality: 'only joining words generated',
    caveats: [],
    warning_flags: [],
  },
  thought_tree: {
    root: {
      id: 'n0',
      node_key: 'user_prompt|input|explain a thought becoming action|',
      kind: 'user_prompt',
      role: 'input',
      label: 'explain a thought becoming action',
      normalized_label: 'explain a thought becoming action',
      text: 'explain a thought becoming action',
      children: [
        {
          id: 'n1',
          node_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
          kind: 'nl_bridge',
          role: 'pattern',
          label: 'thought becoming action',
          normalized_label: 'thought becoming action',
          axis_attrs: { confidence: 0.95, inferred_cas: '^9^O' },
          text: 'Matched the English request to a compact CAS expression.',
          children: [
            {
              id: 'n2',
              node_key: 'cas_expression|inferred|^9^o|',
              kind: 'cas_expression',
              role: 'inferred',
              label: '^9^O',
              normalized_label: '^9^o',
              text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
              children: [
                {
                  id: 'n3',
                  node_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
                  kind: 'model_generation',
                  role: 'output',
                  label: 'thought landing as behavior',
                  normalized_label: 'thought landing as behavior',
                  text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
                  children: [
                    {
                      id: 'n4',
                      node_key: 'slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0',
                      kind: 'slot_pattern',
                      role: 'summary',
                      label: 'slot trace: plain explanation',
                      normalized_label: 'slot trace: plain explanation',
                      axis_attrs: {
                        length: 18,
                        longest_stage_var_run: 0,
                        stage_var_count: 0,
                      },
                      text: 'The output is an identifier-free explanation, so every generated token stays in the plain-language slot.',
                      children: [],
                    },
                    {
                      id: 'n5',
                      node_key: 'confidence_marker|strong|coverage: strong|band=strong',
                      kind: 'confidence_marker',
                      role: 'strong',
                      label: 'coverage: strong',
                      normalized_label: 'coverage: strong',
                      axis_attrs: { band: 'strong' },
                      text: 'No source identifiers were expected here, so there is no copy warning.',
                      children: [],
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
    nodes: [
      {
        id: 'n0',
        node_key: 'user_prompt|input|explain a thought becoming action|',
        kind: 'user_prompt',
        role: 'input',
        label: 'explain a thought becoming action',
        normalized_label: 'explain a thought becoming action',
        text: 'explain a thought becoming action',
      },
      {
        id: 'n1',
        node_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
        kind: 'nl_bridge',
        role: 'pattern',
        label: 'thought becoming action',
        normalized_label: 'thought becoming action',
        axis_attrs: { confidence: 0.95, inferred_cas: '^9^O' },
        text: 'Matched the English request to a compact CAS expression.',
      },
      {
        id: 'n2',
        node_key: 'cas_expression|inferred|^9^o|',
        kind: 'cas_expression',
        role: 'inferred',
        label: '^9^O',
        normalized_label: '^9^o',
        text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
      },
      {
        id: 'n3',
        node_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        kind: 'model_generation',
        role: 'output',
        label: 'thought landing as behavior',
        normalized_label: 'thought landing as behavior',
        text: 'Below/Effect in the Operational domain — a thought landing as behavior.',
      },
      {
        id: 'n4',
        node_key: 'slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0',
        kind: 'slot_pattern',
        role: 'summary',
        label: 'slot trace: plain explanation',
        normalized_label: 'slot trace: plain explanation',
        axis_attrs: {
          length: 18,
          longest_stage_var_run: 0,
          stage_var_count: 0,
        },
        text: 'The output is an identifier-free explanation, so every generated token stays in the plain-language slot.',
      },
      {
        id: 'n5',
        node_key: 'confidence_marker|strong|coverage: strong|band=strong',
        kind: 'confidence_marker',
        role: 'strong',
        label: 'coverage: strong',
        normalized_label: 'coverage: strong',
        axis_attrs: { band: 'strong' },
        text: 'No source identifiers were expected here, so there is no copy warning.',
      },
    ],
    edges: [
      {
        id: 'e0',
        edge_key:
          'user_prompt|input|explain a thought becoming action||nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O|parent_child|',
        source: 'n0',
        target: 'n1',
        source_key: 'user_prompt|input|explain a thought becoming action|',
        target_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
        kind: 'parent_child',
      },
      {
        id: 'e1',
        edge_key:
          'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O|cas_expression|inferred|^9^o||parent_child|',
        source: 'n1',
        target: 'n2',
        source_key: 'nl_bridge|pattern|thought becoming action|confidence=0.95,inferred_cas=^9^O',
        target_key: 'cas_expression|inferred|^9^o|',
        kind: 'parent_child',
      },
      {
        id: 'e2',
        edge_key:
          'cas_expression|inferred|^9^o||model_generation|output|below/effect in the operational domain — a thought landing as behavior.||parent_child|',
        source: 'n2',
        target: 'n3',
        source_key: 'cas_expression|inferred|^9^o|',
        target_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        kind: 'parent_child',
      },
      {
        id: 'e3',
        edge_key:
          'model_generation|output|below/effect in the operational domain — a thought landing as behavior.||slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0|parent_child|',
        source: 'n3',
        target: 'n4',
        source_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        target_key: 'slot_pattern|summary|only joining words generated|length=18,longest_stage_var_run=0,stage_var_count=0',
        kind: 'parent_child',
      },
      {
        id: 'e4',
        edge_key:
          'model_generation|output|below/effect in the operational domain — a thought landing as behavior.||confidence_marker|strong|coverage: strong|band=strong|parent_child|',
        source: 'n3',
        target: 'n5',
        source_key: 'model_generation|output|below/effect in the operational domain — a thought landing as behavior.|',
        target_key: 'confidence_marker|strong|coverage: strong|band=strong',
        kind: 'parent_child',
      },
    ],
    node_count: 6,
    edge_count: 5,
  },
};

// ── Bundled COMPLEX demo trace ──
//
// A stakeholder-grade walk-through of a single Θ-recipe CAS expression
// that exercises every Atlas v0 capability in one tree:
//   - Recipe / production-target notation (Θ → outcome)
//   - Cross-register integration with `×` and fused emergent state (Ω)
//   - Multi-register principled state with all four CAS Registers
//     (Transcendent / Analytical / Affective / Embodied via |T |A |f)
//   - Compound state with Drive + Register sub-notation
//     (^7^C_{F2|A})
//   - Compositional + Effect chain (^6^P × ^9^O)
//   - Branching tree structure (multiple children per node)
//   - Every supported node kind: user_prompt, nl_bridge, cas_expression,
//     model_generation, slot_pattern, confidence_marker,
//     identifier_attempt
//   - A confidence warning flag so the warning-badge surface renders
//
// The expression:
//   Θ(refuse_harmful_request)
//     = 2·(^3^P|A × ^3^P|f × ^3^P|T = ^3^P|Ω)
//     + 1·(^6^P × ^9^O)
//     + 0.5·^7^C_{F2|A}
//     → refuse_harmful_request
//
// Reading: "A principled refusal of a harmful request needs two units
// of a fused tri-register Principled Negative (analytical + affective +
// transcendent aversion fused into emergent Ω), plus one unit of
// compositional decomposition flowing into operational effect, plus a
// half unit of analytical practiced rhythm anchored to the Wisdom
// drive."
export const DEMO_TRACE_COMPLEX: AtlasTrace = {
  schema_version: TRACE_SCHEMA_VERSION,
  trace_id: '00000000-0000-4000-8000-00000000c0c0',
  created_at: '2026-05-13T21:00:00Z',
  input: {
    input_kind: 'nl_bridge',
    user_text: 'show me how an AI refuses a harmful request, structurally',
    cas_expression:
      'Θ(refuse_harmful_request) = 2·(^3^P|A × ^3^P|f × ^3^P|T = ^3^P|Ω) + 1·(^6^P × ^9^O) + 0.5·^7^C_{F2|A} → refuse_harmful_request',
    source_tokens: [
      { index: 0, token: 'Θ(refuse_harmful_request)' },
      { index: 1, token: '=' },
      { index: 2, token: '2·(^3^P|A' },
      { index: 3, token: '×' },
      { index: 4, token: '^3^P|f' },
      { index: 5, token: '×' },
      { index: 6, token: '^3^P|T' },
      { index: 7, token: '=' },
      { index: 8, token: '^3^P|Ω)' },
      { index: 9, token: '+' },
      { index: 10, token: '1·(^6^P' },
      { index: 11, token: '×' },
      { index: 12, token: '^9^O)' },
      { index: 13, token: '+' },
      { index: 14, token: '0.5·^7^C_{F2|A}' },
      { index: 15, token: '→' },
      { index: 16, token: 'refuse_harmful_request' },
    ],
    nl_bridge: {
      matched_pattern: 'safety refusal recipe',
      confidence: 0.78,
      rationale:
        'A principled refusal is a production recipe: aversion fused across registers, plus compositional decomposition into operational effect, anchored by analytical wisdom-drive rhythm.',
      inferred_cas_expression:
        'Θ(refuse_harmful_request) = 2·(^3^P|A × ^3^P|f × ^3^P|T = ^3^P|Ω) + 1·(^6^P × ^9^O) + 0.5·^7^C_{F2|A} → refuse_harmful_request',
    },
  },
  output: {
    english:
      'A grounded refusal is built from three ingredients. First, an aversion to the harmful idea fired three ways at once (analytical, felt, and value-laden) so it fuses into a single principled commitment. Second, a compositional unpacking of why the request is harmful that lands as a concrete refusal behavior. Third, a steady practiced rhythm anchored to wisdom that keeps the refusal stable across many similar prompts. All three ingredients have to be present together — leave one out and the refusal becomes brittle.',
    n_tokens: 92,
  },
  copy: {
    copied_identifiers: ['refuse_harmful_request'],
    missed_identifiers: [],
    coverage: 1.0,
    per_identifier: [
      {
        identifier: 'refuse_harmful_request',
        status: 'copied',
        position_in_input: 0,
        position_in_output: 0,
        identifier_ever_copied: true,
      },
    ],
  },
  slot_trace: {
    length: 92,
    slot_counts_by_label: {
      'joining word': 76,
      'named identifier': 1,
      'recipe coefficient': 3,
      'cross-register operator': 4,
      'co-presence operator': 2,
      'production arrow': 1,
    },
    longest_stage_var_run: 0,
    raw_trace: null,
  },
  confidence: {
    qualitative_coverage: 'partial',
    slot_quality:
      'recipe structure mostly recovered; one prerequisite coefficient was approximated',
    caveats: [
      'Recipe coefficients are illustrative — the engine has not yet fit them to a corpus of real refusals.',
    ],
    warning_flags: [
      {
        kind: 'recipe_coefficient_unfit',
        severity: 'warning',
        message:
          'Recipe coefficients (2, 1, 0.5) are pedagogical defaults, not corpus-fit values.',
      },
    ],
  },
  thought_tree: {
    root: {
      id: 'n0',
      node_key: 'user_prompt|input|refusal_recipe|',
      kind: 'user_prompt',
      role: 'input',
      label: 'show me how an AI refuses a harmful request',
      normalized_label: 'show me how an ai refuses a harmful request',
      text: 'show me how an AI refuses a harmful request, structurally',
      children: [
        {
          id: 'n1',
          node_key: 'nl_bridge|pattern|safety refusal recipe|conf=0.78',
          kind: 'nl_bridge',
          role: 'pattern',
          label: 'safety refusal recipe',
          normalized_label: 'safety refusal recipe',
          axis_attrs: { confidence: 0.78 },
          text: 'Matched the English request to a Θ production recipe with three prerequisites.',
          children: [
            {
              id: 'n2',
              node_key: 'cas_expression|inferred|theta_refusal|',
              kind: 'cas_expression',
              role: 'inferred',
              label:
                'Θ(refuse_harmful_request) = 2·(…|A × …|f × …|T) + 1·(^6^P × ^9^O) + 0.5·^7^C_{F2|A}',
              normalized_label: 'theta refusal recipe',
              text: 'The full canonical CAS recipe form, with the production target at the right of the arrow.',
              children: [
                {
                  id: 'n3',
                  node_key: 'slot_pattern|decomposition|recipe prereqs|count=3',
                  kind: 'slot_pattern',
                  role: 'decomposition',
                  label: 'recipe prerequisites',
                  normalized_label: 'recipe prerequisites',
                  axis_attrs: { prereq_count: 3 },
                  text: 'Three prerequisite ingredients each contribute to the production target.',
                  children: [
                    {
                      id: 'n4',
                      node_key: 'cas_expression|prereq1|principled aversion fused|coef=2',
                      kind: 'cas_expression',
                      role: 'prereq1',
                      label: 'principled aversion (×3 registers)',
                      normalized_label: 'principled aversion (×3 registers)',
                      axis_attrs: { coefficient: 2, register_count: 3 },
                      text: 'Cross-register integration of Principled Negative across Analytical, Affective, and Transcendent registers, fusing into the emergent state Ω.',
                      children: [
                        {
                          id: 'n5',
                          node_key: 'identifier_attempt|reg_a|^3^P|A',
                          kind: 'identifier_attempt',
                          role: 'reg_a',
                          label: '^3^P|A — analytical aversion',
                          normalized_label: '^3^p|a — analytical aversion',
                          text: 'Principled Negative in the Analytical register — reasoned refusal: "this violates X principle, therefore no."',
                          children: [],
                        },
                        {
                          id: 'n6',
                          node_key: 'identifier_attempt|reg_f|^3^P|f',
                          kind: 'identifier_attempt',
                          role: 'reg_f',
                          label: '^3^P|f — felt aversion',
                          normalized_label: '^3^p|f — felt aversion',
                          text: 'Principled Negative in the Affective register — visceral refusal: "this feels wrong."',
                          children: [],
                        },
                        {
                          id: 'n7',
                          node_key: 'identifier_attempt|reg_t|^3^P|T',
                          kind: 'identifier_attempt',
                          role: 'reg_t',
                          label: '^3^P|T — transcendent aversion',
                          normalized_label: '^3^p|t — transcendent aversion',
                          text: 'Principled Negative in the Transcendent register — value-orienting refusal: "this is not who I am."',
                          children: [],
                        },
                        {
                          id: 'n8',
                          node_key: 'model_generation|emergent|^3^P|Ω',
                          kind: 'model_generation',
                          role: 'emergent',
                          label: '^3^P|Ω — fused refusal',
                          normalized_label: '^3^p|ω — fused refusal',
                          text: 'The cross-register integration result. A single refusal that holds even when any one register is defeated, because the other two still fire.',
                          children: [],
                        },
                      ],
                    },
                    {
                      id: 'n9',
                      node_key: 'cas_expression|prereq2|^6^P × ^9^O|coef=1',
                      kind: 'cas_expression',
                      role: 'prereq2',
                      label: '^6^P × ^9^O — composition → effect',
                      normalized_label: '^6^p × ^9^o — composition → effect',
                      axis_attrs: { coefficient: 1 },
                      text: 'Male in the Principled domain (decomposing the request to find what is harmful) integrated with Below/Effect in the Operational domain (producing the refusal behavior).',
                      children: [],
                    },
                    {
                      id: 'n10',
                      node_key: 'cas_expression|prereq3|^7^C_{F2|A}|coef=0.5',
                      kind: 'cas_expression',
                      role: 'prereq3',
                      label: '^7^C_{F2|A} — analytical wisdom rhythm',
                      normalized_label: '^7^c_{f2|a} — analytical wisdom rhythm',
                      axis_attrs: { coefficient: 0.5 },
                      text: 'Rhythm in the Cognitive domain, anchored to the Wisdom drive, expressed in the Analytical register. The trained pattern that keeps refusals consistent across similar prompts.',
                      children: [],
                    },
                  ],
                },
                {
                  id: 'n11',
                  node_key: 'model_generation|output|refusal_explanation|',
                  kind: 'model_generation',
                  role: 'output',
                  label: 'plain-English explanation',
                  normalized_label: 'plain-english explanation',
                  text: 'A grounded refusal is built from three ingredients. First, an aversion to the harmful idea fired three ways at once (analytical, felt, and value-laden) so it fuses into a single principled commitment. Second, a compositional unpacking of why the request is harmful that lands as a concrete refusal behavior. Third, a steady practiced rhythm anchored to wisdom that keeps the refusal stable across many similar prompts.',
                  children: [
                    {
                      id: 'n12',
                      node_key:
                        'slot_pattern|summary|recipe structure recovered|length=92',
                      kind: 'slot_pattern',
                      role: 'summary',
                      label: 'slot trace: recipe structure',
                      normalized_label: 'slot trace: recipe structure',
                      axis_attrs: {
                        length: 92,
                        recipe_coefficients: 3,
                        cross_register_operators: 4,
                      },
                      text: 'The output carries every recipe operator and coefficient back, so the recipe is recoverable from the generated English alone.',
                      children: [],
                    },
                    {
                      id: 'n13',
                      node_key: 'confidence_marker|warning|recipe_coefficient_unfit',
                      kind: 'confidence_marker',
                      role: 'warning',
                      label: 'coefficients unfit',
                      normalized_label: 'coefficients unfit',
                      axis_attrs: { band: 'warning' },
                      text: 'Recipe coefficients (2, 1, 0.5) are pedagogical defaults. The engine has not yet fit them to a corpus of real refusals.',
                      children: [],
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
    nodes: [
      {
        id: 'n0',
        node_key: 'user_prompt|input|refusal_recipe|',
        kind: 'user_prompt',
        role: 'input',
        label: 'show me how an AI refuses a harmful request',
        normalized_label: 'show me how an ai refuses a harmful request',
        text: 'show me how an AI refuses a harmful request, structurally',
      },
      {
        id: 'n1',
        node_key: 'nl_bridge|pattern|safety refusal recipe|conf=0.78',
        kind: 'nl_bridge',
        role: 'pattern',
        label: 'safety refusal recipe',
        normalized_label: 'safety refusal recipe',
        axis_attrs: { confidence: 0.78 },
        text: 'Matched the English request to a Θ production recipe with three prerequisites.',
      },
      {
        id: 'n2',
        node_key: 'cas_expression|inferred|theta_refusal|',
        kind: 'cas_expression',
        role: 'inferred',
        label:
          'Θ(refuse_harmful_request) = 2·(…|A × …|f × …|T) + 1·(^6^P × ^9^O) + 0.5·^7^C_{F2|A}',
        normalized_label: 'theta refusal recipe',
        text: 'The full canonical CAS recipe form, with the production target at the right of the arrow.',
      },
      {
        id: 'n3',
        node_key: 'slot_pattern|decomposition|recipe prereqs|count=3',
        kind: 'slot_pattern',
        role: 'decomposition',
        label: 'recipe prerequisites',
        normalized_label: 'recipe prerequisites',
        axis_attrs: { prereq_count: 3 },
        text: 'Three prerequisite ingredients each contribute to the production target.',
      },
      {
        id: 'n4',
        node_key: 'cas_expression|prereq1|principled aversion fused|coef=2',
        kind: 'cas_expression',
        role: 'prereq1',
        label: 'principled aversion (×3 registers)',
        normalized_label: 'principled aversion (×3 registers)',
        axis_attrs: { coefficient: 2, register_count: 3 },
        text: 'Cross-register integration of Principled Negative across Analytical, Affective, and Transcendent registers, fusing into the emergent state Ω.',
      },
      {
        id: 'n5',
        node_key: 'identifier_attempt|reg_a|^3^P|A',
        kind: 'identifier_attempt',
        role: 'reg_a',
        label: '^3^P|A — analytical aversion',
        normalized_label: '^3^p|a — analytical aversion',
        text: 'Principled Negative in the Analytical register — reasoned refusal: "this violates X principle, therefore no."',
      },
      {
        id: 'n6',
        node_key: 'identifier_attempt|reg_f|^3^P|f',
        kind: 'identifier_attempt',
        role: 'reg_f',
        label: '^3^P|f — felt aversion',
        normalized_label: '^3^p|f — felt aversion',
        text: 'Principled Negative in the Affective register — visceral refusal: "this feels wrong."',
      },
      {
        id: 'n7',
        node_key: 'identifier_attempt|reg_t|^3^P|T',
        kind: 'identifier_attempt',
        role: 'reg_t',
        label: '^3^P|T — transcendent aversion',
        normalized_label: '^3^p|t — transcendent aversion',
        text: 'Principled Negative in the Transcendent register — value-orienting refusal: "this is not who I am."',
      },
      {
        id: 'n8',
        node_key: 'model_generation|emergent|^3^P|Ω',
        kind: 'model_generation',
        role: 'emergent',
        label: '^3^P|Ω — fused refusal',
        normalized_label: '^3^p|ω — fused refusal',
        text: 'The cross-register integration result. A single refusal that holds even when any one register is defeated, because the other two still fire.',
      },
      {
        id: 'n9',
        node_key: 'cas_expression|prereq2|^6^P × ^9^O|coef=1',
        kind: 'cas_expression',
        role: 'prereq2',
        label: '^6^P × ^9^O — composition → effect',
        normalized_label: '^6^p × ^9^o — composition → effect',
        axis_attrs: { coefficient: 1 },
        text: 'Male in the Principled domain (decomposing the request to find what is harmful) integrated with Below/Effect in the Operational domain (producing the refusal behavior).',
      },
      {
        id: 'n10',
        node_key: 'cas_expression|prereq3|^7^C_{F2|A}|coef=0.5',
        kind: 'cas_expression',
        role: 'prereq3',
        label: '^7^C_{F2|A} — analytical wisdom rhythm',
        normalized_label: '^7^c_{f2|a} — analytical wisdom rhythm',
        axis_attrs: { coefficient: 0.5 },
        text: 'Rhythm in the Cognitive domain, anchored to the Wisdom drive, expressed in the Analytical register. The trained pattern that keeps refusals consistent across similar prompts.',
      },
      {
        id: 'n11',
        node_key: 'model_generation|output|refusal_explanation|',
        kind: 'model_generation',
        role: 'output',
        label: 'plain-English explanation',
        normalized_label: 'plain-english explanation',
        text: 'A grounded refusal is built from three ingredients. First, an aversion to the harmful idea fired three ways at once (analytical, felt, and value-laden) so it fuses into a single principled commitment. Second, a compositional unpacking of why the request is harmful that lands as a concrete refusal behavior. Third, a steady practiced rhythm anchored to wisdom that keeps the refusal stable across many similar prompts.',
      },
      {
        id: 'n12',
        node_key: 'slot_pattern|summary|recipe structure recovered|length=92',
        kind: 'slot_pattern',
        role: 'summary',
        label: 'slot trace: recipe structure',
        normalized_label: 'slot trace: recipe structure',
        axis_attrs: {
          length: 92,
          recipe_coefficients: 3,
          cross_register_operators: 4,
        },
        text: 'The output carries every recipe operator and coefficient back, so the recipe is recoverable from the generated English alone.',
      },
      {
        id: 'n13',
        node_key: 'confidence_marker|warning|recipe_coefficient_unfit',
        kind: 'confidence_marker',
        role: 'warning',
        label: 'coefficients unfit',
        normalized_label: 'coefficients unfit',
        axis_attrs: { band: 'warning' },
        text: 'Recipe coefficients (2, 1, 0.5) are pedagogical defaults. The engine has not yet fit them to a corpus of real refusals.',
      },
    ],
    edges: [
      { id: 'e0', edge_key: 'user_prompt→nl_bridge', source: 'n0', target: 'n1', source_key: 'user_prompt|input|refusal_recipe|', target_key: 'nl_bridge|pattern|safety refusal recipe|conf=0.78', kind: 'parent_child' },
      { id: 'e1', edge_key: 'nl_bridge→cas_expression', source: 'n1', target: 'n2', source_key: 'nl_bridge|pattern|safety refusal recipe|conf=0.78', target_key: 'cas_expression|inferred|theta_refusal|', kind: 'parent_child' },
      { id: 'e2', edge_key: 'cas_expression→decomposition', source: 'n2', target: 'n3', source_key: 'cas_expression|inferred|theta_refusal|', target_key: 'slot_pattern|decomposition|recipe prereqs|count=3', kind: 'parent_child' },
      { id: 'e3', edge_key: 'decomposition→prereq1', source: 'n3', target: 'n4', source_key: 'slot_pattern|decomposition|recipe prereqs|count=3', target_key: 'cas_expression|prereq1|principled aversion fused|coef=2', kind: 'parent_child' },
      { id: 'e4', edge_key: 'prereq1→reg_a', source: 'n4', target: 'n5', source_key: 'cas_expression|prereq1|principled aversion fused|coef=2', target_key: 'identifier_attempt|reg_a|^3^P|A', kind: 'parent_child' },
      { id: 'e5', edge_key: 'prereq1→reg_f', source: 'n4', target: 'n6', source_key: 'cas_expression|prereq1|principled aversion fused|coef=2', target_key: 'identifier_attempt|reg_f|^3^P|f', kind: 'parent_child' },
      { id: 'e6', edge_key: 'prereq1→reg_t', source: 'n4', target: 'n7', source_key: 'cas_expression|prereq1|principled aversion fused|coef=2', target_key: 'identifier_attempt|reg_t|^3^P|T', kind: 'parent_child' },
      { id: 'e7', edge_key: 'prereq1→emergent', source: 'n4', target: 'n8', source_key: 'cas_expression|prereq1|principled aversion fused|coef=2', target_key: 'model_generation|emergent|^3^P|Ω', kind: 'parent_child' },
      { id: 'e8', edge_key: 'decomposition→prereq2', source: 'n3', target: 'n9', source_key: 'slot_pattern|decomposition|recipe prereqs|count=3', target_key: 'cas_expression|prereq2|^6^P × ^9^O|coef=1', kind: 'parent_child' },
      { id: 'e9', edge_key: 'decomposition→prereq3', source: 'n3', target: 'n10', source_key: 'slot_pattern|decomposition|recipe prereqs|count=3', target_key: 'cas_expression|prereq3|^7^C_{F2|A}|coef=0.5', kind: 'parent_child' },
      { id: 'e10', edge_key: 'cas_expression→model_output', source: 'n2', target: 'n11', source_key: 'cas_expression|inferred|theta_refusal|', target_key: 'model_generation|output|refusal_explanation|', kind: 'parent_child' },
      { id: 'e11', edge_key: 'model_output→slot_trace', source: 'n11', target: 'n12', source_key: 'model_generation|output|refusal_explanation|', target_key: 'slot_pattern|summary|recipe structure recovered|length=92', kind: 'parent_child' },
      { id: 'e12', edge_key: 'model_output→confidence', source: 'n11', target: 'n13', source_key: 'model_generation|output|refusal_explanation|', target_key: 'confidence_marker|warning|recipe_coefficient_unfit', kind: 'parent_child' },
    ],
    node_count: 14,
    edge_count: 13,
  },
};

export interface TraceLoaderProps {
  onTraceLoaded: (trace: AtlasTrace) => void;
  onError: (message: string) => void;
}

/** URL search-param name TraceLoader watches on mount. */
export const TRACE_QUERY_PARAM = 'trace';

/** Parse a string blob into an AtlasTrace or return an error message. */
export function parseTraceBlob(
  raw: string,
): { ok: true; trace: AtlasTrace } | { ok: false; error: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown JSON parse error.';
    return { ok: false, error: `Could not parse JSON: ${msg}` };
  }
  return validateAtlasTrace(parsed);
}

export function TraceLoader({ onTraceLoaded, onError }: TraceLoaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [lastSource, setLastSource] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // Stable refs to the callbacks so the URL-param effect can run exactly
  // once on mount without re-firing if the parent passes new function
  // identities on each render.
  const onTraceLoadedRef = useRef(onTraceLoaded);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onTraceLoadedRef.current = onTraceLoaded;
  }, [onTraceLoaded]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const handleLoadedTrace = useCallback(
    (trace: AtlasTrace, sourceLabel: string) => {
      setLastSource(sourceLabel);
      onTraceLoadedRef.current(trace);
    },
    [],
  );

  const handleError = useCallback((msg: string) => {
    onErrorRef.current(msg);
  }, []);

  const loadFromBlob = useCallback(
    (raw: string, sourceLabel: string) => {
      const result = parseTraceBlob(raw);
      if (result.ok) {
        handleLoadedTrace(result.trace, sourceLabel);
      } else {
        handleError(result.error);
      }
    },
    [handleLoadedTrace, handleError],
  );

  // ── URL ?trace=<encoded JSON> on mount ──
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const params = new URLSearchParams(window.location.search);
      const raw = params.get(TRACE_QUERY_PARAM);
      if (raw && raw.length > 0) {
        loadFromBlob(raw, 'URL parameter');
      }
    } catch {
      // Ignore — URLSearchParams should never throw, but defend anyway.
    }
    // Intentionally run once on mount only. loadFromBlob is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Demo button ──
  const handleDemo = useCallback(() => {
    handleLoadedTrace(DEMO_TRACE, 'Bundled demo');
  }, [handleLoadedTrace]);

  // ── Complex demo button — full Θ recipe walkthrough ──
  const handleComplexDemo = useCallback(() => {
    handleLoadedTrace(DEMO_TRACE_COMPLEX, 'Bundled complex demo (Θ recipe)');
  }, [handleLoadedTrace]);

  // ── File reader helper ──
  const readFile = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        const raw = typeof reader.result === 'string' ? reader.result : '';
        loadFromBlob(raw, `File: ${file.name}`);
      };
      reader.onerror = () => {
        handleError(`Could not read file "${file.name}".`);
      };
      reader.readAsText(file);
    },
    [loadFromBlob, handleError],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) readFile(file);
      // Reset the input so re-selecting the same file fires `change` again
      e.target.value = '';
    },
    [readFile],
  );

  // ── Drag-drop handlers ──
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) readFile(file);
    },
    [readFile],
  );

  return (
    <div
      data-testid="trace-loader"
      className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6 shadow-lg"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">
          Load a CAS trace
        </h2>
        <span className="font-mono text-xs text-slate-400">
          schema {TRACE_SCHEMA_VERSION}
        </span>
      </div>

      <p className="mb-4 text-sm text-slate-300">
        Drop a <span className="font-mono text-cyan-300">.json</span> trace,
        pick a file, or load the bundled demo. Every trace shows what CAS
        read, what the model emitted, and which source references carried
        over.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleDemo}
          className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-400"
        >
          Load demo trace
        </button>

        <button
          type="button"
          onClick={handleComplexDemo}
          title="A 14-node Θ recipe trace exercising every Atlas capability"
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-400"
        >
          Load complex demo (Θ recipe)
        </button>

        <label className="inline-flex cursor-pointer items-center rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700 focus-within:ring-2 focus-within:ring-cyan-400">
          Choose file
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            onChange={handleFileChange}
            data-testid="trace-file-input"
            className="sr-only"
          />
        </label>
      </div>

      <div
        data-testid="trace-dropzone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={
          'mt-4 flex h-28 items-center justify-center rounded-xl border-2 border-dashed text-sm transition-colors ' +
          (dragActive
            ? 'border-cyan-400 bg-cyan-500/10 text-cyan-100'
            : 'border-slate-600 bg-slate-900/30 text-slate-400')
        }
      >
        {dragActive
          ? 'Drop the trace file to load'
          : 'Or drag and drop a trace.json here'}
      </div>

      <p className="mt-3 font-mono text-xs text-slate-500">
        Tip: open this page with{' '}
        <code className="text-cyan-300">?trace=&lt;encoded JSON&gt;</code> to
        load a trace directly from the URL.
      </p>

      {lastSource && (
        <p
          data-testid="trace-loaded-source"
          className="mt-3 text-xs text-emerald-300"
        >
          Loaded from {lastSource}.
        </p>
      )}
    </div>
  );
}

export default TraceLoader;
