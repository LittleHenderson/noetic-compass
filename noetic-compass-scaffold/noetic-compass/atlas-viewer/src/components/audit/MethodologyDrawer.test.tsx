import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MethodologyDrawer } from './MethodologyDrawer';
import { buildDefaultProvenanceChips } from '../../lib/casHarnessAudit';

const chips = buildDefaultProvenanceChips({
  modelProof: { status: 'verified', detail: 'model verified' },
  casReadout: { status: 'verified', detail: 'readout present' },
  causalProof: { status: 'verified', detail: 'ablation present' },
  controlProof: { status: 'verified', detail: 'control present' },
  outputProof: { status: 'verified', detail: 'output present' },
  packetProof: { status: 'present', detail: 'packet present' },
});

describe('MethodologyDrawer', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <MethodologyDrawer open={false} onClose={() => {}} chips={chips} />,
    );
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId('methodology-drawer')).not.toBeInTheDocument();
  });

  it('opens with the verdict explainer, the relabel legend, and the Stage vocabulary', () => {
    render(
      <MethodologyDrawer
        open
        onClose={() => {}}
        verdict="ACCEPT"
        confidence={0.98}
        chips={chips}
        verifierDecision={{
          verdict: 'ACCEPT',
          confidence: 0.98,
          source: 'stage19_verification_stack',
          reason: 'Stage 19 accepted the row.',
        }}
      />,
    );

    expect(screen.getByTestId('methodology-drawer')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Why this verdict' })).toBeInTheDocument();
    // Absorbs the verdict-explainer prose.
    expect(
      screen.getByText(/Accepted because the verifier explicitly allowed it/i),
    ).toBeInTheDocument();
    // The plain-language relabel legend is here, mapping to internal terms.
    expect(screen.getByText('CAS readout (model-internal signal)')).toBeInTheDocument();
    expect(screen.getByText('Matched control')).toBeInTheDocument();
    // The internal scoring vocabulary lives ONLY in the drawer.
    expect(screen.getByText(/Stage 19 \/ accepted_accuracy/i)).toBeInTheDocument();
    expect(screen.getByText(/Stage 20 \/ Generation Readiness/i)).toBeInTheDocument();
    // Absorbs the Evidence Packet flight-recorder FAQ.
    expect(
      screen.getByRole('heading', { name: 'Evidence Packet = AI flight recorder' }),
    ).toBeInTheDocument();
  });

  it('closes via the close button', () => {
    const onClose = vi.fn();
    render(<MethodologyDrawer open onClose={onClose} chips={chips} />);

    fireEvent.click(screen.getByTestId('methodology-drawer-close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes on backdrop click', () => {
    const onClose = vi.fn();
    render(<MethodologyDrawer open onClose={onClose} chips={chips} />);

    fireEvent.click(screen.getByTestId('methodology-drawer-backdrop'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
