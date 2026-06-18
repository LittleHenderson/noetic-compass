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
    expect(screen.getByTestId('fleet-readiness-summary')).toHaveTextContent(/large-model eval readiness/i);
    expect(screen.getByTestId('fleet-readiness-actions')).toHaveTextContent(/register workers/i);
  });

  it('renders backend readiness blockers and next actions directly', () => {
    render(
      <FleetExecutorPanel
        registeredWorkers={1}
        leasedJobs={0}
        staleWorkers={0}
        completedFragments={0}
        totalJobs={25}
        mergedPacketStatus="not_created"
        verifierGateStatus="waiting_for_workers"
        readiness={{
          status: 'waiting',
          headline: 'Large-model eval is waiting on workers or fragment receipts.',
          blockers: ['24 assigned worker job(s) still need a registered, compatible, fresh-heartbeat worker.'],
          next_actions: ['Register or heartbeat every assigned Probe Worker.'],
          verifier_owned: true,
        }}
      />,
    );

    expect(screen.getByTestId('fleet-readiness-summary')).toHaveTextContent(
      /waiting on workers or fragment receipts/i,
    );
    expect(screen.getByTestId('fleet-readiness-blockers')).toHaveTextContent(
      /24 assigned worker job/i,
    );
    expect(screen.getByText(/cannot emit ACCEPT by themselves/i)).toBeInTheDocument();
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

  it('renders structural monitoring as a shadow-only review lane', () => {
    render(
      <FleetExecutorPanel
        registeredWorkers={25}
        leasedJobs={25}
        staleWorkers={0}
        completedFragments={25}
        totalJobs={25}
        mergedPacketStatus="ready"
        verifierGateStatus="ready_for_verifier"
        structuralMonitoring={{
          status: 'FLAG_FOR_HUMAN_REVIEW',
          verdict_effect: 'none_shadow_only',
          route: 'FLAG_FOR_HUMAN_REVIEW',
          basis: 'measured',
          summary: {
            signal_count: 1,
            measured_signal_count: 1,
            missing_signal_count: 0,
            drifted_signal_count: 1,
            max_drift_score: 0.42,
          },
          review_reasons: ['structural drift_score exceeded drift_threshold'],
          claim_ceiling:
            'Structural/fleet monitoring is shadow-only evidence review and cannot mint ACCEPT/SUPPRESS.',
        }}
      />,
    );

    expect(screen.getByTestId('fleet-structural-monitoring')).toHaveTextContent(/shadow structural signal/i);
    expect(screen.getByTestId('fleet-structural-monitoring')).toHaveTextContent(/FLAG_FOR_HUMAN_REVIEW/);
    expect(screen.getByTestId('fleet-structural-monitoring-reasons')).toHaveTextContent(/drift_score exceeded/i);
    expect(screen.getByTestId('fleet-structural-monitoring-claim')).toHaveTextContent(/cannot mint ACCEPT\/SUPPRESS/i);
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
    expect(screen.getByTestId('fleet-readiness-summary')).toHaveTextContent(/verifier review is unblocked/i);
    expect(screen.queryByTestId('fleet-executor-block')).not.toBeInTheDocument();
  });
});
