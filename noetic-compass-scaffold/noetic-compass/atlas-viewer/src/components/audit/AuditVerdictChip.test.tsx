import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuditVerdictChip } from './AuditVerdictChip';
import {
  buildDefaultProvenanceChips,
  isAuditResultCustomerSafe,
  type AuditSessionSummary,
} from '../../lib/casHarnessAudit';

const SCOPED_BAND = 'Scoped — not a customer-production ACCEPT';

// A summary that fails the customer-safe gate: an ACCEPT with not-all-usable
// proof chips (mirrors the Stage 9 40E scoped-validation case).
const scopedAcceptSummary: AuditSessionSummary = {
  request: { mode: 'live', prompt: '' },
  verdict: 'ACCEPT',
  confidence: 0.7,
  confidenceLabel: '70%',
  provenanceChips: buildDefaultProvenanceChips({
    modelProof: true,
    casReadout: true,
    causalProof: { status: 'unavailable' },
    controlProof: { status: 'missing' },
    outputProof: true,
    packetProof: { status: 'missing' },
  }),
  runtimeProof: {
    is_real_model: true,
    model_loaded: true,
    load_error: null,
    fake_runtime_env: false,
    manifest_is_real_model: true,
  },
};

const safeAcceptSummary: AuditSessionSummary = {
  request: { mode: 'live', prompt: '' },
  verdict: 'ACCEPT',
  confidence: 0.84,
  confidenceLabel: '84%',
  provenanceChips: buildDefaultProvenanceChips({
    modelProof: true,
    casReadout: true,
    causalProof: true,
    controlProof: true,
    outputProof: true,
    packetProof: true,
  }),
  runtimeProof: {
    is_real_model: true,
    model_loaded: true,
    load_error: null,
    fake_runtime_env: false,
    manifest_is_real_model: true,
  },
};

describe('AuditVerdictChip honesty gate', () => {
  it('shows the amber scoped band for an ACCEPT that is NOT customer-safe', () => {
    // Guard the premise: this summary really does fail the gate.
    expect(isAuditResultCustomerSafe(scopedAcceptSummary)).toBe(false);

    render(<AuditVerdictChip verdict="ACCEPT" confidence={0.7} customerSafe={false} />);

    expect(screen.getByText('ACCEPT')).toBeInTheDocument();
    expect(screen.getByText(SCOPED_BAND)).toBeInTheDocument();
  });

  it('derives the scoped band from a non-customer-safe summary', () => {
    render(
      <AuditVerdictChip verdict="ACCEPT" confidence={0.7} summary={scopedAcceptSummary} />,
    );
    expect(screen.getByText(SCOPED_BAND)).toBeInTheDocument();
  });

  it('renders a clean ACCEPT with NO scoped band when customer-safe', () => {
    expect(isAuditResultCustomerSafe(safeAcceptSummary)).toBe(true);

    render(<AuditVerdictChip verdict="ACCEPT" confidence={0.84} customerSafe />);

    expect(screen.getByText('ACCEPT')).toBeInTheDocument();
    expect(screen.queryByText(SCOPED_BAND)).not.toBeInTheDocument();
  });

  it('uses the verbatim FLAG label and a human-review eyebrow', () => {
    render(<AuditVerdictChip verdict="FLAG_FOR_HUMAN_REVIEW" confidence={0.5} />);

    expect(screen.getByText('FLAG FOR HUMAN REVIEW')).toBeInTheDocument();
    expect(screen.getByText('Human review required')).toBeInTheDocument();
    // FLAG is not an ACCEPT, so no scoped-ACCEPT band.
    expect(screen.queryByText(SCOPED_BAND)).not.toBeInTheDocument();
  });

  it('falls back to NO VERDICT YET before a verdict exists', () => {
    render(<AuditVerdictChip verdict={null} confidence={null} />);
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();
  });
});
