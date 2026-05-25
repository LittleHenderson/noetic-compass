import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import BlindspotsPanel from './BlindspotsPanel';
import { DRIVE_TRANSLATIONS } from '../../lib/driveTranslations';

describe('BlindspotsPanel', () => {
  it('renders unscored possible-blindspot rows when only unavailable-band entries are present', () => {
    // Audit fix (PR #54): when covers exist but every member is in the
    // "unavailable" band (legacy/unscored trace), the 3D red overlay is still drawn — so an empty
    // textual panel would confuse the viewer. The panel now gives the
    // user the plain-English meaning while keeping confidence unavailable.
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: null, confidence_band: 'unavailable', evidence_sources: [] },
          ],
        }}
      />,
    );
    expect(screen.queryByTestId('blindspots-empty')).toBeNull();
    expect(screen.queryByTestId('blindspots-no-markers')).toBeNull();
    const pending = screen.getByTestId('blindspots-markers-pending');
    expect(pending.textContent).toMatch(/markers detected/i);
    expect(pending.textContent).toMatch(/confidence percentages are unavailable/i);
    const rows = screen.getAllByTestId('blindspot-interpretation');
    expect(rows).toHaveLength(1);
    expect(screen.getByTestId('blindspot-short-lead').textContent).toBe(
      'Possible blindspot: inclusion, protection, or connection.',
    );
    expect(screen.getByTestId('blindspot-confidence').textContent).toBe(
      'Confidence: not available (insufficient evidence)',
    );
  });

  it('renders the no-markers message when there are no cover overlaps at all', () => {
    render(<BlindspotsPanel perClassNeuronCovers={{}} />);
    expect(screen.queryByTestId('blindspot-interpretation')).toBeNull();
    expect(screen.queryByTestId('blindspots-markers-pending')).toBeNull();
    expect(screen.queryByTestId('blindspots-empty')).toBeNull();
    expect(screen.getByTestId('blindspots-no-markers')).toBeTruthy();
  });

  it('renders high + medium bands by default', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
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

  it('lets a user focus a blindspot row in the 3D neuron scene', () => {
    const onFocusClass = vi.fn();
    render(
      <BlindspotsPanel
        focusedClassKey="F1A"
        onFocusClass={onFocusClass}
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: 0.84, confidence_band: 'high', evidence_sources: ['probe'] },
            { label: 'L3N518', confidence: 0.82, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    const row = screen.getByTestId('blindspot-interpretation');
    expect(row.getAttribute('data-focused')).toBe('true');
    const button = screen.getByTestId('blindspot-focus-cover');
    expect(button.textContent).toBe('Showing neurons (2)');
    fireEvent.click(button);
    expect(onFocusClass).toHaveBeenCalledWith('F1A');
  });

  it('hides low-confidence entries by default and surfaces an expand affordance', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: 0.85, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
          F1f: [
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
          F1A: [
            { label: 'L3N142', confidence: 0.85, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
          F1f: [
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

  it('does not render unavailable entries when at least one scored row is visible', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: null, confidence_band: 'unavailable', evidence_sources: [] },
          ],
          F1T: [
            { label: 'L3N518', confidence: 0.86, confidence_band: 'high', evidence_sources: ['probe', 'ablation'] },
          ],
        }}
      />,
    );
    // Unavailable rows are a fallback for unscored traces. Once a scored
    // row exists, keep the panel focused on scored evidence.
    expect(screen.queryByTestId('blindspots-expand-low')).toBeNull();
    const rows = screen.getAllByTestId('blindspot-interpretation');
    expect(rows.length).toBe(1);
    expect(rows[0].getAttribute('data-drive')).toBe('F1');
  });

  it('renders the verbatim drive sentence for the rendered class', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: 0.72, confidence_band: 'medium', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    expect(screen.getByTestId('blindspot-headline').textContent).toBe(
      DRIVE_TRANSLATIONS.F1.sentence,
    );
  });

  it('passes register through into the CAS source line', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
            { label: 'L3N142', confidence: 0.72, confidence_band: 'medium', evidence_sources: ['probe'] },
          ],
        }}
      />,
    );
    expect(screen.getByTestId('blindspot-cas-source').textContent).toBe(
      'CAS source: F1 Unity · analytical register',
    );
  });

  it('aggregates multiple members of the same class into one row', () => {
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: [
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
    // Bare strings (legacy offline trace shape) normalise to
    // band=unavailable. Since they ARE present (markers exist in the
    // scene), the panel routes to unscored possible-blindspot rows rather
    // than the no-cover-overlap message.
    render(
      <BlindspotsPanel
        perClassNeuronCovers={{
          F1A: ['L3N142', 'L3N518'],
        }}
      />,
    );
    expect(screen.queryByTestId('blindspots-empty')).toBeNull();
    expect(screen.queryByTestId('blindspots-no-markers')).toBeNull();
    expect(screen.getByTestId('blindspots-markers-pending')).toBeTruthy();
    expect(screen.getAllByTestId('blindspot-interpretation')).toHaveLength(1);
    expect(screen.getByTestId('blindspot-confidence').textContent).toBe(
      'Confidence: not available (insufficient evidence)',
    );
  });
});
