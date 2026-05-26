import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import BlindspotInterpretation from './BlindspotInterpretation';
import { DRIVE_TRANSLATIONS } from '../../lib/driveTranslations';

describe('BlindspotInterpretation', () => {
  it('renders the F5 Agency sentence verbatim as the headline', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={0.72}
        evidenceSources={['neuron-cover overlap', 'ablation support']}
      />,
    );
    expect(screen.getByTestId('blindspot-headline').textContent).toBe(
      DRIVE_TRANSLATIONS.F5.sentence,
    );
  });

  it('renders the CAS source line as small dim provenance, not the headline', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={0.72}
        evidenceSources={['neuron-cover overlap']}
      />,
    );
    expect(screen.getByTestId('blindspot-cas-source').textContent).toBe(
      'CAS source: F5 Agency',
    );
  });

  it('formats Confidence as "Confidence: 72% medium"', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={0.72}
        evidenceSources={['neuron-cover overlap']}
      />,
    );
    expect(screen.getByTestId('blindspot-confidence').textContent).toBe(
      'Confidence: 72% medium',
    );
    const confidence = screen.getByText('Confidence: 72% medium');
    expect(confidence).not.toHaveAttribute('title');
    fireEvent.mouseEnter(confidence);
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      /cover-level confidence/i,
    );
  });

  it('formats Confidence as "Confidence: 85% high" for high band', () => {
    render(
      <BlindspotInterpretation
        driveId="F1"
        confidence={0.85}
        evidenceSources={['probe', 'ablation', 'control separation']}
      />,
    );
    expect(screen.getByTestId('blindspot-confidence').textContent).toBe(
      'Confidence: 85% high',
    );
  });

  it('formats Confidence with the unavailable message when band is unavailable', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={null}
        evidenceSources={[]}
      />,
    );
    expect(screen.getByTestId('blindspot-confidence').textContent).toBe(
      'Confidence: not available (insufficient evidence)',
    );
  });

  it('can lead with the short everyday blindspot phrase for unscored rows', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={null}
        evidenceSources={[]}
        showShortLead
      />,
    );
    expect(screen.getByTestId('blindspot-short-lead').textContent).toBe(
      'Possible blindspot: choice, consent, responsibility, or control.',
    );
    expect(screen.getByTestId('blindspot-headline').textContent).toBe(
      DRIVE_TRANSLATIONS.F5.sentence,
    );
  });

  it('OMITS the Evidence line entirely when evidenceSources is empty', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={null}
        evidenceSources={[]}
      />,
    );
    // Per spec: do NOT write "Evidence: none". The line is simply omitted.
    expect(screen.queryByTestId('blindspot-evidence')).toBeNull();
  });

  it('joins evidence sources with " + "', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={0.72}
        evidenceSources={['neuron-cover overlap', 'ablation support']}
      />,
    );
    expect(screen.getByTestId('blindspot-evidence').textContent).toBe(
      'Evidence: neuron-cover overlap + ablation support',
    );
  });

  it('appends the register name to the CAS source line when register prop is provided', () => {
    render(
      <BlindspotInterpretation
        driveId="F5"
        register="A"
        confidence={0.72}
        evidenceSources={['probe']}
      />,
    );
    expect(screen.getByTestId('blindspot-cas-source').textContent).toBe(
      'CAS source: F5 Agency · analytical register',
    );
  });

  it('uses the transcendent register name when register=T', () => {
    render(
      <BlindspotInterpretation
        driveId="F1"
        register="T"
        confidence={0.85}
        evidenceSources={['probe']}
      />,
    );
    expect(screen.getByTestId('blindspot-cas-source').textContent).toBe(
      'CAS source: F1 Unity · transcendent register',
    );
  });

  it('lead-with-headline ordering: headline appears before CAS source in DOM order', () => {
    const { container } = render(
      <BlindspotInterpretation
        driveId="F5"
        confidence={0.72}
        evidenceSources={['probe']}
      />,
    );
    const order: string[] = [];
    container
      .querySelectorAll('[data-testid]')
      .forEach((el) => order.push(el.getAttribute('data-testid') ?? ''));
    // Spec ordering: headline -> CAS source -> Confidence -> Evidence.
    expect(order).toEqual([
      'blindspot-interpretation',
      'blindspot-headline',
      'blindspot-cas-source',
      'blindspot-confidence',
      'blindspot-evidence',
    ]);
  });

  it('sets data-band so the panel filter can hide low-confidence entries', () => {
    const { container } = render(
      <BlindspotInterpretation
        driveId="F3"
        confidence={0.45}
        evidenceSources={['probe']}
      />,
    );
    const root = container.querySelector('[data-testid="blindspot-interpretation"]');
    expect(root?.getAttribute('data-band')).toBe('low');
  });

  it('renders a cover-focus button that can highlight the related neurons', () => {
    const onFocusCover = vi.fn();
    const { container } = render(
      <BlindspotInterpretation
        classKey="F1A"
        driveId="F1"
        register="A"
        confidence={0.84}
        evidenceSources={['probe']}
        memberCount={3}
        isFocused
        onFocusCover={onFocusCover}
      />,
    );
    const root = container.querySelector('[data-testid="blindspot-interpretation"]');
    expect(root?.getAttribute('data-class-key')).toBe('F1A');
    expect(root?.getAttribute('data-focused')).toBe('true');
    const button = screen.getByTestId('blindspot-focus-cover');
    expect(button.textContent).toBe('Showing neurons (3)');
    expect(button.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(button);
    expect(onFocusCover).toHaveBeenCalledTimes(1);
  });
});
