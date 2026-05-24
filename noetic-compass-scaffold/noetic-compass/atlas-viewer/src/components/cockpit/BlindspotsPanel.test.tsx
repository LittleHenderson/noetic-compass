import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import BlindspotsPanel from './BlindspotsPanel';
import { DRIVE_TRANSLATIONS } from '../../lib/driveTranslations';

describe('BlindspotsPanel', () => {
  it('renders nothing visible when only unavailable-band entries are present', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: null, confidence_band: 'unavailable', evidence_sources: [] },
          ],
        }}
      />,
    );
    expect(screen.queryByTestId('blindspot-interpretation')).toBeNull();
    expect(screen.getByTestId('blindspots-empty')).toBeTruthy();
  });

  it('renders high + medium bands by default', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F5A: [
            { label: 'L3N142', confidence: 0.84, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
          F1T: [
            { label: 'L4N336', confidence: 0.72, confidence_band: 'medium', evidence_sources: ['probe', 'ablation'] },
          ],
        }}
      />,
    );
    const rows = screen.getAllByTestId('blindspot-interpretation');
    expect(rows.length).toBe(2);
    // High first, then medium (stronger band first).
    expect(rows[0].getAttribute('data-band')).toBe('high');
    expect(rows[1].getAttribute('data-band')).toBe('medium');
  });

  it('hides low-confidence entries by default and surfaces an expand affordance', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F5A: [
            { label: 'L3N142', confidence: 0.85, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
          F3f: [
            { label: 'L5N91', confidence: 0.45, confidence_band: 'low', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    const rowsBefore = screen.getAllByTestId('blindspot-interpretation');
    expect(rowsBefore.length).toBe(1);
    expect(rowsBefore[0].getAttribute('data-band')).toBe('high');

    const expand = screen.getByTestId('blindspots-expand-low');
    expect(expand.textContent).toBe('Show low-confidence (1 hidden)');
  });

  it('expanding reveals low-confidence rows', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F5A: [
            { label: 'L3N142', confidence: 0.85, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
          F3f: [
            { label: 'L5N91', confidence: 0.45, confidence_band: 'low', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    fireEvent.click(screen.getByTestId('blindspots-expand-low'));
    const rowsAfter = screen.getAllByTestId('blindspot-interpretation');
    expect(rowsAfter.length).toBe(2);
    expect(rowsAfter.map((r) => r.getAttribute('data-band'))).toEqual([
      'high',
      'low',
    ]);
  });

  it('never includes unavailable entries even when expanded', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: null, confidence_band: 'unavailable', evidence_sources: [] },
          ],
          F5A: [
            { label: 'L3N518', confidence: 0.86, confidence_band: 'high', evidence_sources: ['probe', 'ablation'] },
          ],
        }}
      />,
    );
    // Even without expanding, expand button should NOT be rendered for
    // unavailable entries (only low-band hidden ones get the affordance).
    expect(screen.queryByTestId('blindspots-expand-low')).toBeNull();
    const rows = screen.getAllByTestId('blindspot-interpretation');
    expect(rows.length).toBe(1);
    expect(rows[0].getAttribute('data-drive')).toBe('F5');
  });

  it('renders the verbatim drive sentence for the rendered class', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F5A: [
            { label: 'L3N142', confidence: 0.72, confidence_band: 'medium', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    expect(screen.getByTestId('blindspot-headline').textContent).toBe(
      DRIVE_TRANSLATIONS.F5.sentence,
    );
  });

  it('passes register through into the CAS source line', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F5A: [
            { label: 'L3N142', confidence: 0.72, confidence_band: 'medium', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    expect(screen.getByTestId('blindspot-cas-source').textContent).toBe(
      'CAS source: F5 Agency · analytical register',
    );
  });

  it('aggregates multiple members of the same class into one row', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F5A: [
            { label: 'L3N142', confidence: 0.65, confidence_band: 'medium', evidence_sources: ['probe'] },
            { label: 'L3N518', confidence: 0.84, confidence_band: 'high', evidence_sources: ['probe', 'ablation'] },
            { label: 'L5N91', confidence: 0.50, confidence_band: 'low', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    const rows = screen.getAllByTestId('blindspot-interpretation');
    expect(rows.length).toBe(1);
    // Best band wins: high (because at least one member is high).
    expect(rows[0].getAttribute('data-band')).toBe('high');
    // Evidence union: probe + ablation (probe duplicates merge).
    expect(screen.getByTestId('blindspot-evidence').textContent).toBe(
      'Evidence: probe + ablation',
    );
  });

  it('renders bare-string covers (legacy offline traces) as placeholder/unavailable rows', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: ['L3N142', 'L3N518'],
        }}
      />,
    );
    // Bare strings normalise to band=unavailable, which never shows.
    expect(screen.queryByTestId('blindspot-interpretation')).toBeNull();
    expect(screen.getByTestId('blindspots-empty')).toBeTruthy();
  });
});
