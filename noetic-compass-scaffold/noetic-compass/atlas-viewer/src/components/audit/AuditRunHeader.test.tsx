import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuditRunHeader } from './AuditRunHeader';

describe('AuditRunHeader', () => {
  it('shows audit_id, model, mode, and a status word for an active run', () => {
    render(
      <AuditRunHeader
        auditId="cas-audit-xyz"
        modelTarget="EleutherAI/pythia-160m"
        mode="BALANCED"
        status="running"
      />,
    );

    const header = screen.getByLabelText('Audit run header');
    expect(header).toHaveTextContent('Audit cas-audit-xyz');
    expect(header).toHaveTextContent('EleutherAI/pythia-160m');
    expect(header).toHaveTextContent('BALANCED');
    // Status word is always present (color is never the only signal).
    expect(screen.getByRole('status', { name: 'Run status: Running' })).toHaveTextContent(
      'Running',
    );
  });

  it('reads as a calm "New audit / No active run" header before a session exists', () => {
    render(<AuditRunHeader status="draft" />);

    const header = screen.getByLabelText('Audit run header');
    expect(header).toHaveTextContent('New audit');
    expect(screen.getByRole('status', { name: 'Run status: No active run' })).toBeInTheDocument();
    expect(header).toHaveTextContent('Connect a model below to begin.');
  });

  it('uses the Complete status word for a finished run', () => {
    render(<AuditRunHeader auditId="a1" status="complete" />);
    expect(screen.getByRole('status', { name: 'Run status: Complete' })).toBeInTheDocument();
  });
});
