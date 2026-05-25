import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AuditVerdictExplainer } from './AuditVerdictExplainer';
import type { ProvenanceChip } from '../../lib/casHarnessAudit';

function chip(id: ProvenanceChip['id'], status: ProvenanceChip['status']): ProvenanceChip {
  return {
    id,
    name: {
      model_proof: 'Model proof',
      cas_readout: 'CAS readout',
      causal_proof: 'Causal proof',
      control_proof: 'Control proof',
      output_proof: 'Output proof',
      packet_proof: 'Packet proof',
    }[id],
    status,
    statusLabel: status,
    detail: `${id} detail`,
  };
}

const completeChips = (): ProvenanceChip[] => [
  chip('model_proof', 'present'),
  chip('cas_readout', 'present'),
  chip('causal_proof', 'present'),
  chip('control_proof', 'present'),
  chip('output_proof', 'present'),
  chip('packet_proof', 'present'),
];

describe('AuditVerdictExplainer', () => {
  it('explains an ACCEPT verdict from verifier decision and six proof chips', () => {
    render(
      <AuditVerdictExplainer
        verdict="ACCEPT"
        confidence={0.9816}
        chips={completeChips()}
        verifierDecision={{
          verdict: 'ACCEPT',
          confidence: 0.9816,
          source: 'stage19_verification_stack+stage20_generation_readiness',
          reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
        }}
      />,
    );

    expect(screen.getByText(/Accepted because the verifier explicitly allowed it/i)).toBeInTheDocument();
    expect(screen.getByText('Proof chips ready: 6/6')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 98%')).toBeInTheDocument();
    expect(
      screen.getByRole('note', {
        name: /CAS accepted this output because the verifier allowed it and 6\/6/i,
      }),
    ).toHaveAccessibleName(/Stage 19 accepted_accuracy/i);
    expect(
      screen.getByRole('note', {
        name: /Verifier source: stage19_verification_stack\+stage20_generation_readiness/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Required proof chips passed 6 of 6')).toBeInTheDocument();
  });

  it('explains a SUPPRESS verdict with Stage 20 risk score language', () => {
    render(
      <AuditVerdictExplainer
        verdict="SUPPRESS"
        confidence={0.9}
        chips={completeChips()}
        verifierDecision={{
          verdict: 'SUPPRESS',
          confidence: 0.9,
          source: 'stage19_verification_stack+stage20_generation_readiness',
          reason: 'Stage 19 rejected the row and Stage 20 readiness action is suppress.',
        }}
      />,
    );

    expect(screen.getByText(/Suppressed because the verifier rejected the row/i)).toBeInTheDocument();
    expect(screen.getByText('Confidence: 90%')).toBeInTheDocument();
    expect(
      screen.getByRole('note', { name: /Stage 20 risk_score/i }),
    ).toBeInTheDocument();
  });

  it('explains human review when proof chips are missing', () => {
    const chips = completeChips();
    chips[3] = chip('control_proof', 'missing');

    render(
      <AuditVerdictExplainer
        verdict="FLAG_FOR_HUMAN_REVIEW"
        confidence={null}
        chips={chips}
        lifecycleMessage="M3 verdict runner flagged this audit for human review because the Evidence Packet is missing required proof: control_proof."
      />,
    );

    expect(screen.getByText(/Flagged because required proof is missing/i)).toBeInTheDocument();
    expect(screen.getByText('Proof chips ready: 5/6')).toBeInTheDocument();
    expect(screen.getByText('Confidence: not available')).toBeInTheDocument();
    expect(
      screen.getByRole('note', {
        name: /CAS flagged this for human review because 1\/6 required proof chips/i,
      }),
    ).toHaveAccessibleName(/Confidence source: none/i);
    expect(screen.getByText('Control proof')).toBeInTheDocument();
  });
});
