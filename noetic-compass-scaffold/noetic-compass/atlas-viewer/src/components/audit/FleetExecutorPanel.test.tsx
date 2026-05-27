import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FleetExecutorPanel from './FleetExecutorPanel';

describe('FleetExecutorPanel', () => {
  it('states that a scale plan alone cannot move a 100B or 300B run forward', () => {
    render(
      <FleetExecutorPanel
        registeredWorkers={0}
        leasedJobs={0}
        staleWorkers={0}
        completedFragments={0}
        totalJobs={25}
        mergedPacketStatus="not_created"
        verifierGateStatus="waiting_for_workers"
      />,
    );

    expect(screen.getByText(/cannot move forward from a scale plan alone/i)).toBeInTheDocument();
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(/waiting for registered/i);
    expect(screen.getByTestId('fleet-executor-block')).toHaveTextContent(/assigned workers and returned receipts/i);
  });

  it('shows lease, heartbeat, fragment, packet, and verifier readiness metrics', () => {
    render(
      <FleetExecutorPanel
        registeredWorkers={24}
        leasedJobs={20}
        staleWorkers={1}
        completedFragments={18}
        totalJobs={25}
        mergedPacketStatus="partial"
        verifierGateStatus="waiting_for_receipts"
      />,
    );

    expect(screen.getByText('24/25')).toBeInTheDocument();
    expect(screen.getByText('20/25')).toBeInTheDocument();
    expect(screen.getByText('18/25')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('partial')).toBeInTheDocument();
    expect(screen.getByText('waiting for receipts')).toBeInTheDocument();
  });

  it('warns when worker failure blocks ACCEPT', () => {
    render(
      <FleetExecutorPanel
        registeredWorkers={25}
        leasedJobs={25}
        staleWorkers={0}
        completedFragments={24}
        totalJobs={25}
        mergedPacketStatus="partial"
        verifierGateStatus="blocked_failed_worker"
      />,
    );

    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(/worker failed/i);
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(/cannot become ACCEPT/i);
  });

  it('does not show the blocked notice once every fragment is ready for verifier review', () => {
    render(
      <FleetExecutorPanel
        registeredWorkers={25}
        leasedJobs={25}
        staleWorkers={0}
        completedFragments={25}
        totalJobs={25}
        mergedPacketStatus="ready"
        verifierGateStatus="ready_for_verifier"
      />,
    );

    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(/merge can assemble/i);
    expect(screen.queryByTestId('fleet-executor-block')).not.toBeInTheDocument();
  });
});
