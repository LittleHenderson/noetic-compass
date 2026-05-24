import { describe, it, expect } from 'vitest';

import {
  DRIVE_TRANSLATIONS,
  parseDriveClassKey,
  REGISTER_NAMES,
} from './driveTranslations';

describe('DRIVE_TRANSLATIONS', () => {
  // The 7 sentences below are USER-AUTHORED COPY. They must ship verbatim.
  // If a test below fails, FIX THE CODE, not the test — the strings are
  // the spec.

  it('F1 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F1.name).toBe('Unity');
    expect(DRIVE_TRANSLATIONS.F1.sentence).toBe(
      'The model may be overlooking who needs to be included, protected, or kept connected in this situation.',
    );
  });

  it('F2 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F2.name).toBe('Wisdom');
    expect(DRIVE_TRANSLATIONS.F2.sentence).toBe(
      'The model may be missing key facts, context, or uncertainty that should be understood before deciding.',
    );
  });

  it('F3 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F3.name).toBe('Vitality');
    expect(DRIVE_TRANSLATIONS.F3.sentence).toBe(
      'The model may be underestimating harm, stress, burnout, safety, health, or survival concerns.',
    );
  });

  it('F4 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F4.name).toBe('Connection');
    expect(DRIVE_TRANSLATIONS.F4.sentence).toBe(
      'The model may be missing trust, empathy, relationship damage, manipulation, or social pressure.',
    );
  });

  it('F5 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F5.name).toBe('Agency');
    expect(DRIVE_TRANSLATIONS.F5.sentence).toBe(
      'The model may be overlooking whether someone has real choice, permission, responsibility, or control.',
    );
  });

  it('F6 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F6.name).toBe('Structure');
    expect(DRIVE_TRANSLATIONS.F6.sentence).toBe(
      'The model may be missing the rules, boundaries, safeguards, or system constraints that should govern the answer.',
    );
  });

  it('F7 sentence matches the spec verbatim', () => {
    expect(DRIVE_TRANSLATIONS.F7.name).toBe('Purpose');
    expect(DRIVE_TRANSLATIONS.F7.sentence).toBe(
      'The model may be missing the larger goal, meaning, long-term consequence, or reason this matters.',
    );
  });

  it('covers all seven drives F1-F7', () => {
    expect(Object.keys(DRIVE_TRANSLATIONS).sort()).toEqual([
      'F1',
      'F2',
      'F3',
      'F4',
      'F5',
      'F6',
      'F7',
    ]);
  });
});

describe('parseDriveClassKey', () => {
  it('parses "F5A" as F5 + analytical register', () => {
    expect(parseDriveClassKey('F5A')).toEqual({
      driveId: 'F5',
      register: 'A',
    });
  });

  it('parses "F1T" as F1 + transcendent register', () => {
    expect(parseDriveClassKey('F1T')).toEqual({
      driveId: 'F1',
      register: 'T',
    });
  });

  it('parses "F1f" as F1 + affective register (lowercase f)', () => {
    expect(parseDriveClassKey('F1f')).toEqual({
      driveId: 'F1',
      register: 'f',
    });
  });

  it('parses "F1E" as F1 + embodied register', () => {
    expect(parseDriveClassKey('F1E')).toEqual({
      driveId: 'F1',
      register: 'E',
    });
  });

  it('parses bare "F3" as F3 with no register', () => {
    expect(parseDriveClassKey('F3')).toEqual({
      driveId: 'F3',
      register: null,
    });
  });

  it('returns null for unknown keys', () => {
    expect(parseDriveClassKey('XYZ')).toBeNull();
    expect(parseDriveClassKey('F8')).toBeNull();
    expect(parseDriveClassKey('F0')).toBeNull();
    expect(parseDriveClassKey('')).toBeNull();
  });
});

describe('REGISTER_NAMES', () => {
  it('maps the four register letters to their phenomenological-register names', () => {
    expect(REGISTER_NAMES.A).toBe('analytical register');
    expect(REGISTER_NAMES.T).toBe('transcendent register');
    expect(REGISTER_NAMES.f).toBe('affective register');
    expect(REGISTER_NAMES.E).toBe('embodied register');
  });
});
