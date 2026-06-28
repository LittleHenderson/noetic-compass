/**
 * Stub data for testing the IdeaAtlas UI without a real backend.
 *
 * The atlas + diagram below are *coordinated* — same generation_id, same
 * cas_expression — so the toggle's correspondence logic can be exercised
 * end-to-end. The atlas mirrors the verbatim Python output of
 * `prediction_to_atlas` for the v77 prediction:
 *
 *   {noetic: 3, domain: "E", drive: "F2", register: "A"}  →  ^3^E_{F2}|A
 *
 * Source: `cas-native/atlas/prediction_to_atlas.py`. Keep this in sync
 * when the Python derivation changes.
 */

import type {
  CasDiagram,
  GenerationTrace,
  IdeaAtlas,
} from './types';

export const STUB_GENERATION_ID = 'b2f4a1e9c0d34d6c9e2f8a7b1d6e3f04';

export const STUB_ATLAS: IdeaAtlas = {
  generation_id: STUB_GENERATION_ID,
  cas_expression: '^3^E_{F2}|A',
  nodes: [
    {
      id: '^3^E_{F2}|A',
      label: '^3 Negative ^E _{F2} |A',
      noetic: '^3',
      domain: 'E',
      drive: 'F2',
      register: 'A',
      intensity: 1.0,
      is_positive_space: true,
      metadata: {
        register_mode: 'single',
        domain_descent_position: 2,
        noetic_name: 'Negative',
        expression_family: 'register_state',
        turn_type: 'ANSWER',
        authority: 'admitted',
        drive_inversion_partner: 'F6',
      },
    },
    {
      id: '^2^E_{F2}|A:negspace',
      label: '(absent) ^2 Positive ^E _{F2} |A',
      noetic: '^2',
      domain: 'E',
      drive: 'F2',
      register: 'A',
      intensity: 0.18,
      is_positive_space: false,
      metadata: {
        shadow_of: '^3^E_{F2}|A',
        noetic_name: 'Positive',
        involution_kind: 'noetic',
      },
    },
  ],
  edges: [
    {
      source_id: '^3^E_{F2}|A',
      target_id: '^2^E_{F2}|A:negspace',
      edge_kind: 'involution_pair',
      label: '^3↔^2',
      metadata: { involution_kind: 'noetic' },
    },
  ],
  metadata: {
    schema_version: 'idea_atlas_v0.1',
  },
};

export const STUB_DIAGRAM: CasDiagram = {
  generation_id: STUB_GENERATION_ID,
  layout_hint: 'radial',
  nodes: [
    {
      id: 'compiler_state_0',
      label: '^3^E_{F2}|A',
      noetic: '^3',
      domain: 'E',
      drive: 'F2',
      register: 'A',
      kind: 'state',
    },
  ],
  edges: [],
  containers: [],
};

export const STUB_TRACE: GenerationTrace = {
  generation_id: STUB_GENERATION_ID,
  timestamp_ms: 1759593600000,
  user_input: "I can't stand it when people interrupt me",
  cas_expression: '^3^E_{F2}|A',
  prediction: {
    turn_type: 'ANSWER',
    expression_family: 'register_state',
    transition_kind: 'state',
    noetic: 3,
    domain: 'E',
    drive: 'F2',
    register_mode: 'single',
    registers: ['A'],
    authority: 'admitted',
    has_omega: false,
    has_meta_logic: false,
    meta_relations: [],
  },
  atlas_node_ids: ['^3^E_{F2}|A', '^2^E_{F2}|A:negspace'],
  diagram_node_ids: ['compiler_state_0'],
  metadata: {
    source: 'stub',
  },
};

/**
 * Atlas-id → Diagram-id[] correspondence map for the stub.
 * Mirrors `correspond_atlas_to_diagram` Python helper.
 */
export const STUB_CORRESPONDENCE: Record<string, string[]> = {
  '^3^E_{F2}|A': ['compiler_state_0'],
  '^2^E_{F2}|A:negspace': [],
};
