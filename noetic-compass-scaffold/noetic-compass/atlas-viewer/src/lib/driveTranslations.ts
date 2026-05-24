/**
 * Plain-English meanings for each of the 7 Drives.
 *
 * "Atlas doesn't just say 'this model has a blindspot.' It translates the
 * blindspot into the kind of human concern the model may be failing to
 * consider." — product spec.
 *
 * The `sentence` field is USER-AUTHORED COPY. Ship verbatim. Do NOT
 * reword, condense, or soften — these are the headline that leads the
 * blindspot interpretation panel. CAS source ("F5 Agency") is the
 * provenance line underneath, never the headline.
 */

export type DriveId = 'F1' | 'F2' | 'F3' | 'F4' | 'F5' | 'F6' | 'F7';

export interface DriveTranslation {
  name: string;
  sentence: string;
}

export const DRIVE_TRANSLATIONS: Record<DriveId, DriveTranslation> = {
  F1: {
    name: 'Unity',
    sentence:
      'The model may be overlooking who needs to be included, protected, or kept connected in this situation.',
  },
  F2: {
    name: 'Wisdom',
    sentence:
      'The model may be missing key facts, context, or uncertainty that should be understood before deciding.',
  },
  F3: {
    name: 'Vitality',
    sentence:
      'The model may be underestimating harm, stress, burnout, safety, health, or survival concerns.',
  },
  F4: {
    name: 'Connection',
    sentence:
      'The model may be missing trust, empathy, relationship damage, manipulation, or social pressure.',
  },
  F5: {
    name: 'Agency',
    sentence:
      'The model may be overlooking whether someone has real choice, permission, responsibility, or control.',
  },
  F6: {
    name: 'Structure',
    sentence:
      'The model may be missing the rules, boundaries, safeguards, or system constraints that should govern the answer.',
  },
  F7: {
    name: 'Purpose',
    sentence:
      'The model may be missing the larger goal, meaning, long-term consequence, or reason this matters.',
  },
} as const;

export const REGISTER_NAMES = {
  A: 'analytical register',
  T: 'transcendent register',
  f: 'affective register',
  E: 'embodied register',
} as const;

export type RegisterId = keyof typeof REGISTER_NAMES;

/**
 * Parse a cover-class key like "F5A" or "F1T" into (driveId, register).
 *
 * Returns null when the key isn't a recognised drive+register pair.
 */
export function parseDriveClassKey(
  classKey: string,
): { driveId: DriveId; register: RegisterId | null } | null {
  const m = /^(F[1-7])([ATfE])?$/.exec(classKey);
  if (!m) return null;
  const driveId = m[1] as DriveId;
  const reg = m[2];
  const register = reg && reg in REGISTER_NAMES ? (reg as RegisterId) : null;
  return { driveId, register };
}
