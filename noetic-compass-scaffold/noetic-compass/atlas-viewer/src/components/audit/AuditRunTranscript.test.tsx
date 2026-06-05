import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { AuditRunTranscript } from './AuditRunTranscript';

const sessionWithLifecycle = {
  status: 'RUNNING',
  lifecycle: [
    {
      status: 'VALIDATING',
      message: 'Validating model access and runtime proof.',
      timestamp: '2026-06-04T12:04:00Z',
    },
    {
      status: 'RUNNING',
      message: 'Running CAS modules against the model output.',
      timestamp: '2026-06-04T12:05:00Z',
    },
  ],
};

describe('AuditRunTranscript', () => {
  it('renders each lifecycle entry as a plain-English sentence', () => {
    render(<AuditRunTranscript session={sessionWithLifecycle} />);

    const log = screen.getByLabelText('Audit run log');
    expect(
      within(log).getByText('Validating model access and runtime proof.'),
    ).toBeInTheDocument();
    expect(
      within(log).getByText('Running CAS modules against the model output.'),
    ).toBeInTheDocument();
  });

  it('marks the last lifecycle row active', () => {
    render(<AuditRunTranscript session={sessionWithLifecycle} />);
    const log = screen.getByLabelText('Audit run log');
    const rows = within(log).getAllByRole('listitem');
    expect(rows[rows.length - 1]).toHaveAttribute('data-state', 'active');
  });

  it('falls back to a status sentence when a lifecycle entry has no message', () => {
    render(
      <AuditRunTranscript
        session={{
          status: 'EVIDENCE_PENDING',
          lifecycle: [
            { status: 'EVIDENCE_PENDING', message: null, timestamp: null },
          ],
        }}
      />,
    );

    expect(
      screen.getByText('Building the evidence packet (audit trail and anchor)…'),
    ).toBeInTheDocument();
  });

  it('NEVER renders raw JSON — no entry text contains JSON.stringify braces', () => {
    const { container } = render(
      <AuditRunTranscript session={sessionWithLifecycle} />,
    );
    // The serialized DOM must not contain a JSON object dump of a lifecycle
    // entry (e.g. {"status":...}). This guards the no-JSON.stringify rule.
    expect(container.innerHTML).not.toContain('{&quot;');
    expect(container.innerHTML).not.toContain('"status":');
    expect(container.textContent ?? '').not.toContain('{"status"');
  });

  it('shows a calm empty state when there is no lifecycle yet', () => {
    render(<AuditRunTranscript session={null} />);
    expect(screen.queryByLabelText('Audit run log')).not.toBeInTheDocument();
    expect(
      screen.getByText(/No run activity yet/i),
    ).toBeInTheDocument();
  });
});
