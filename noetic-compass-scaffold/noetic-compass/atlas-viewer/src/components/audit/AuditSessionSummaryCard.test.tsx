import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuditSessionSummaryCard } from './AuditSessionSummaryCard';

describe('AuditSessionSummaryCard', () => {
  it('renders a no-session summary without fake verdict or confidence', () => {
    render(<AuditSessionSummaryCard />);

    expect(screen.getByText('No audit session yet')).toBeInTheDocument();
    expect(screen.getByText('No verdict yet')).toBeInTheDocument();
    expect(screen.getByText('Not computed')).toBeInTheDocument();
    expect(screen.getAllByText('Not created')).toHaveLength(2);
    expect(screen.queryByText('87%')).not.toBeInTheDocument();
  });

  it('renders audit id, model target, mode, modules, verdict, and confidence', () => {
    render(
      <AuditSessionSummaryCard
        auditId="audit_123"
        modelTarget="EleutherAI/pythia-160m"
        mode="BALANCED"
        selectedModulesCount={6}
        status="complete"
        verdict="FLAG_FOR_HUMAN_REVIEW"
        confidence={0.72}
        evidencePacketId="packet_123"
        updatedAt="2026-05-25T11:30:00Z"
      />,
    );

    expect(screen.getByText('Audit audit_123')).toBeInTheDocument();
    expect(screen.getByText('EleutherAI/pythia-160m')).toBeInTheDocument();
    expect(screen.getByText('BALANCED')).toBeInTheDocument();
    expect(screen.getByText('6 modules selected')).toBeInTheDocument();
    expect(screen.getByText('FLAG FOR HUMAN REVIEW')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('packet_123')).toBeInTheDocument();
  });

  it('uses a singular module label for one selected module', () => {
    render(<AuditSessionSummaryCard selectedModulesCount={1} />);

    expect(screen.getByText('1 module selected')).toBeInTheDocument();
  });
});
