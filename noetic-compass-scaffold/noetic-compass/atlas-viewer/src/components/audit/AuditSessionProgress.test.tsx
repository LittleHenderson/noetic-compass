import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { AuditSessionProgress } from './AuditSessionProgress';

describe('AuditSessionProgress', () => {
  it('renders the running lifecycle in plain English', () => {
    render(<AuditSessionProgress status="running" />);

    expect(screen.getByRole('heading', { name: 'Running CAS audit' })).toBeInTheDocument();
    expect(
      screen.getByText('The selected CAS modules are evaluating the model output.'),
    ).toBeInTheDocument();
    const steps = screen.getByLabelText('Audit lifecycle steps');
    expect(within(steps).getByText('Validating model')).toBeInTheDocument();
    expect(within(steps).getByText('Running CAS audit')).toBeInTheDocument();
    expect(within(steps).getByText('Runner pending')).toBeInTheDocument();
    expect(within(steps).getByText('Building evidence packet')).toBeInTheDocument();
  });

  it('renders runner pending as a no-verdict state', () => {
    render(<AuditSessionProgress status="runner_pending" />);

    expect(screen.getByRole('heading', { name: 'Runner pending' })).toBeInTheDocument();
    expect(
      screen.getByText('The backend accepted the session, but no final CAS verdict was computed.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Audit complete' })).not.toBeInTheDocument();
  });

  it('renders evidence pending as a packet-building state, not a verdict', () => {
    render(<AuditSessionProgress status="evidence_pending" />);

    expect(screen.getByRole('heading', { name: 'Evidence packet pending' })).toBeInTheDocument();
    expect(
      screen.getByText('The run has produced audit data and is assembling the packet.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Audit complete' })).not.toBeInTheDocument();
  });

  it('renders failed state with an explicit no-trust warning and error message', () => {
    render(
      <AuditSessionProgress
        status="failed"
        errorMessage="Worker returned atlas_live_worker_auth_failed."
      />,
    );

    expect(screen.getByRole('heading', { name: 'Audit failed' })).toBeInTheDocument();
    expect(screen.getByText('Do not use a verdict from this failed run.')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Worker returned atlas_live_worker_auth_failed.',
    );
  });
});
