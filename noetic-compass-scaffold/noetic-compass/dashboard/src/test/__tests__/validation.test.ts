import { describe, it, expect } from 'vitest';
import { validateDials } from '../../lib/validation';

describe('validateDials', () => {
  it('accepts valid default dials', () => {
    expect(validateDials([6, 6, 6, 6, 6, 6, 6, 6, 6, 6])).toEqual([]);
  });

  it('accepts edge values 3 and 9', () => {
    expect(validateDials([3, 9, 3, 7, 3, 9, 5, 3, 3, 7])).toEqual([]);
  });

  it('rejects value below 3', () => {
    const errors = validateDials([2, 6, 6, 6, 6, 6, 6, 6, 6, 6]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain('CO-0');
    expect(errors[0]).toContain('out of range');
  });

  it('rejects value above 9', () => {
    const errors = validateDials([6, 6, 6, 6, 6, 6, 6, 6, 6, 10]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain('CO-9');
  });

  it('rejects involution divergence > 4 for CO-2/CO-3', () => {
    const errors = validateDials([6, 6, 3, 8, 6, 6, 6, 6, 6, 6]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain('CO-2/CO-3');
    expect(errors[0]).toContain('divergence');
  });

  it('allows involution divergence exactly 4', () => {
    expect(validateDials([6, 6, 3, 7, 6, 6, 6, 6, 6, 6])).toEqual([]);
  });

  it('rejects wrong array length', () => {
    const errors = validateDials([6, 6, 6]);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0]).toContain('Expected 10');
  });

  it('catches multiple errors simultaneously', () => {
    const errors = validateDials([2, 6, 3, 9, 6, 10, 6, 6, 6, 6]);
    expect(errors.length).toBeGreaterThanOrEqual(2);
  });
});
