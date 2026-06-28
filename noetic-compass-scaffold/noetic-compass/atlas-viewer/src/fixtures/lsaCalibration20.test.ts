import { describe, expect, it } from 'vitest';
import { lsaCalibration20 } from './lsaCalibration20';

describe('lsaCalibration20', () => {
  it('ships only the 20 rater-facing calibration items', () => {
    expect(lsaCalibration20.items).toHaveLength(20);
    expect(lsaCalibration20.items.filter((item) => item.axis === '40e')).toHaveLength(10);
    expect(lsaCalibration20.items.filter((item) => item.axis === 'f28')).toHaveLength(10);
  });

  it('does not expose hidden answer keys in the web fixture', () => {
    const serialized = JSON.stringify(lsaCalibration20).toLowerCase();

    expect(serialized).not.toContain('expected_label');
    expect(serialized).not.toContain('gold_label');
    expect(serialized).not.toContain('answer_key');
    expect(serialized).not.toContain('original_text');
  });

  it('provides all label choices for both calibration axes', () => {
    expect(lsaCalibration20.definitions['40e']).toHaveLength(40);
    expect(lsaCalibration20.definitions.f28).toHaveLength(28);
  });
});
