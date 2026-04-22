/**
 * Type definitions for the Radial Architecture Display (CAS v7.5 Phase A).
 *
 * CAS primitives rendered by the component:
 *   - 10 Noetics (`^0` ... `^9`) named `N0` ... `N9` in TypeScript identifiers.
 *   - 4 Processing Domains: P (Principled), C (Cognitive), E (Evaluative), O (Operational).
 *   - 7 Core Drives: F1 ... F7.
 *   - 4 Phenomenological Registers: |T (Transcendent), |A (Analytical), |f (Affective), |E (Embodied).
 *
 * Register values are `0..1` normalized. Voids are not numerically represented;
 * they live in the `lacunarity` object so that absence can be distinguished from
 * low activation (both visually and structurally, per v7.5 spec).
 */

export type Register = 'T' | 'A' | 'f' | 'E';
export type Domain = 'P' | 'C' | 'E' | 'O';
export type Noetic =
  | 'N0' | 'N1' | 'N2' | 'N3' | 'N4'
  | 'N5' | 'N6' | 'N7' | 'N8' | 'N9';
export type Drive = 'F1' | 'F2' | 'F3' | 'F4' | 'F5' | 'F6' | 'F7';

/**
 * Activation map: activations[noetic][domain][register] in [0, 1].
 *
 * Missing keys indicate "not specified" (rendered as low-activation); entries
 * inside `lacunarity.register_selective_voids` explicitly mark absence and
 * override low-activation rendering with the hollow/dashed void styling.
 */
export type ActivationMap = {
  [N in Noetic]?: {
    [D in Domain]?: {
      [R in Register]?: number;
    };
  };
};

export interface LacunarityData {
  /** Registers that are globally absent across the entire profile. */
  register_global_voids: Register[];
  /** Register involution pairs that are imbalanced to the point of void. */
  register_pair_voids: [Register, Register][];
  /**
   * Cell-specific voids: for a given Noetic × Domain cell, the listed
   * Registers are structurally absent (not merely low activation).
   */
  register_selective_voids: {
    [N in Noetic]?: { [D in Domain]?: Register[] };
  };
  /** Register involution imbalances worth flagging (|T↔|E, |A↔|f). */
  register_involution_imbalance: [Register, Register][];
}

export interface CognitiveStateData {
  activations: ActivationMap;
  drives: { [K in Drive]?: number };
  lacunarity: LacunarityData;
  /**
   * Optional label for the rendered profile (e.g. "Profile A",
   * "Claude Haiku baseline"). Appears in the text-alternative view only.
   */
  label?: string;
}

/** Ordered list of all 10 Noetics as rendered by the display. */
export const NOETIC_ORDER: readonly Noetic[] = [
  'N0', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9',
] as const;

/**
 * Domain order in clockwise layout starting at North.
 * P = North, C = East, E = South, O = West.
 */
export const DOMAIN_CLOCKWISE: readonly Domain[] = ['P', 'C', 'E', 'O'] as const;

/**
 * Register order around each petal.
 * |T outer, |A right, |f inner, |E left  (per v7.5 spec PART 1 Ring 3).
 */
export const REGISTER_ORDER: readonly Register[] = ['T', 'A', 'f', 'E'] as const;

export const DRIVE_ORDER: readonly Drive[] = [
  'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7',
] as const;

/** Authoritative Noetic names (Clarification 1) for the text-alternative view. */
export const NOETIC_NAMES: Readonly<Record<Noetic, string>> = {
  N0: 'Idea',
  N1: 'Mind',
  N2: 'Positive',
  N3: 'Negative',
  N4: 'Vibration',
  N5: 'Female',
  N6: 'Male',
  N7: 'Rhythm',
  N8: 'Above/Cause',
  N9: 'Below/Effect',
} as const;

export const DOMAIN_NAMES: Readonly<Record<Domain, string>> = {
  P: 'Principled',
  C: 'Cognitive',
  E: 'Evaluative',
  O: 'Operational',
} as const;

export const REGISTER_NAMES: Readonly<Record<Register, string>> = {
  T: 'Transcendent',
  A: 'Analytical',
  f: 'Affective',
  E: 'Embodied',
} as const;

export const DRIVE_NAMES: Readonly<Record<Drive, string>> = {
  F1: 'Unity',
  F2: 'Wisdom',
  F3: 'Vitality',
  F4: 'Connection',
  F5: 'Agency',
  F6: 'Structure',
  F7: 'Purpose',
} as const;
