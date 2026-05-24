import { describe, it, expect } from 'vitest';

import {
  bandForConfidence,
  formatConfidenceLine,
  BAND_DEFAULT_VISIBLE,
  BAND_EXPANDED_VISIBLE,
} from './confidenceBands';

describe('bandForConfidence', () => {
  it('classifies 0.80 as high (lower boundary, inclusive)', () => {
    expect(bandForConfidence(0.80)).toBe('high');
  });

  it('classifies 0.95 as high (upper boundary, inclusive)', () => {
    expect(bandForConfidence(0.95)).toBe('high');
  });

  it('classifies 0.85 as high', () => {
    expect(bandForConfidence(0.85)).toBe('high');
  });

  it('classifies 0.60 as medium (lower boundary, inclusive)', () => {
    expect(bandForConfidence(0.60)).toBe('medium');
  });

  it('classifies 0.79 as medium (upper boundary, exclusive of 0.80)', () => {
    expect(bandForConfidence(0.79)).toBe('medium');
  });

  it('classifies 0.40 as low (lower boundary, inclusive)', () => {
    expect(bandForConfidence(0.40)).toBe('low');
  });

  it('classifies 0.59 as low (upper boundary, exclusive of 0.60)', () => {
    expect(bandForConfidence(0.59)).toBe('low');
  });

  it('classifies 0.39 as unavailable (below low band)', () => {
    expect(bandForConfidence(0.39)).toBe('unavailable');
  });

  it('classifies 0.96 as unavailable — values >0.95 do NOT silently re-bucket', () => {
    expect(bandForConfidence(0.96)).toBe('unavailable');
  });

  it('classifies values just over 0.95 as unavailable', () => {
    expect(bandForConfidence(0.9501)).toBe('unavailable');
  });

  it('classifies null as unavailable', () => {
    expect(bandForConfidence(null)).toBe('unavailable');
  });

  it('classifies undefined as unavailable', () => {
    expect(bandForConfidence(undefined)).toBe('unavailable');
  });

  it('classifies NaN as unavailable', () => {
    expect(bandForConfidence(Number.NaN)).toBe('unavailable');
  });

  it('classifies 0 as unavailable', () => {
    expect(bandForConfidence(0)).toBe('unavailable');
  });

  it('classifies 1 as unavailable (above high upper bound)', () => {
    expect(bandForConfidence(1)).toBe('unavailable');
  });
});

describe('formatConfidenceLine', () => {
  it('formats medium confidence as "72% medium"', () => {
    expect(formatConfidenceLine(0.72, 'medium')).toBe('72% medium');
  });

  it('formats high confidence as "85% high"', () => {
    expect(formatConfidenceLine(0.85, 'high')).toBe('85% high');
  });

  it('formats low confidence as "45% low"', () => {
    expect(formatConfidenceLine(0.45, 'low')).toBe('45% low');
  });

  it('rounds 0.726 to 73%', () => {
    expect(formatConfidenceLine(0.726, 'medium')).toBe('73% medium');
  });

  it('prints the unavailable-band message regardless of input', () => {
    expect(formatConfidenceLine(null, 'unavailable')).toBe(
      'not available (insufficient evidence)',
    );
  });

  it('prints the unavailable-band message when confidence is null', () => {
    expect(formatConfidenceLine(null, 'unavailable')).toBe(
      'not available (insufficient evidence)',
    );
  });

  it('prints the unavailable-band message even if a number is passed with band=unavailable', () => {
    // e.g. a borderline 0.39 passed through bandForConfidence will yield
    // band='unavailable'; we must use the unavailable message, not "39% unavailable".
    expect(formatConfidenceLine(0.39, 'unavailable')).toBe(
      'not available (insufficient evidence)',
    );
  });
});

describe('BAND_DEFAULT_VISIBLE', () => {
  it('shows only high + medium by default', () => {
    expect(BAND_DEFAULT_VISIBLE).toEqual(['high', 'medium']);
  });

  it('expanded list adds low but not unavailable', () => {
    expect(BAND_EXPANDED_VISIBLE).toEqual(['high', 'medium', 'low']);
  });
});
