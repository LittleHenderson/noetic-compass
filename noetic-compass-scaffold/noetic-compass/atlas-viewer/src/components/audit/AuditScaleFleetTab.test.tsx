import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { AuditScaleFleetTab, type AuditScaleFleetTabProps } from './AuditScaleFleetTab';
import { DEFAULT_ENTERPRISE_SCALE_PLAN } from '../../lib/enterpriseScalePlan';

function baseProps(): AuditScaleFleetTabProps {
  return {
    enterprisePlan: DEFAULT_ENTERPRISE_SCALE_PLAN,
    enterprisePlanSize: '100B',
    isEnterprisePlanLoading: false,
    enterprisePlanError: null,
    onSelectSize: vi.fn(),
    distributedAudit: null,
    isDistributedAuditLoading: false,
    distributedAuditError: null,
    onCreateDistributedRun: vi.fn(),
    onDispatchDistributedRun: vi.fn(),
    onMergeDistributedRun: vi.fn(),
    fleetRegisteredWorkers: 0,
    fleetLeasedJobs: 0,
    fleetStaleWorkers: 0,
    fleetCompletedFragments: 0,
    fleetTotalJobs: 0,
    fleetMergedPacketStatus: 'not_created',
    fleetVerifierGateStatus: 'not_prepared',
    fleetReadiness: null,
    fleetAuthToken: '',
    onFleetAuthTokenChange: vi.fn(),
    isFleetExecutorLoading: false,
    fleetExecutorError: null,
    fleetRun: null,
    fleetVerifierDecision: null,
    canPrepareFleet: false,
    canRegisterFleetWorker: false,
    canLeaseFleetJob: false,
    canSubmitFleetReceipt: false,
    canMergeFleet: false,
    canRunFleetVerifier: false,
    onPrepareFleet: vi.fn(),
    onRegisterFleetWorker: vi.fn(),
    onLeaseFleetJob: vi.fn(),
    onSubmitFleetReceipt: vi.fn(),
    onMergeFleet: vi.fn(),
    onRunFleetVerifier: vi.fn(),
  };
}

describe('AuditScaleFleetTab', () => {
  it('relocates the enterprise plan, distributed run, and fleet controls into one tab', () => {
    render(<AuditScaleFleetTab {...baseProps()} />);

    expect(screen.getByLabelText('Scale and fleet (advanced)')).toBeInTheDocument();
    // The three moved panels + the fleet button row are all present here.
    expect(screen.getByRole('button', { name: 'Create run' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Fleet executor controls' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Prepare fleet' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Register demo worker' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run fleet verifier' })).toBeInTheDocument();
    expect(screen.getByLabelText('Protected API token')).toBeInTheDocument();
  });

  it('wires the fleet auth token field', () => {
    const props = baseProps();
    render(<AuditScaleFleetTab {...props} />);

    fireEvent.change(screen.getByLabelText('Protected API token'), {
      target: { value: 'fleet-jwt' },
    });
    expect(props.onFleetAuthTokenChange).toHaveBeenCalledWith('fleet-jwt');
  });

  it('renders the fleet verifier decision verbatim (always human review)', () => {
    render(
      <AuditScaleFleetTab
        {...baseProps()}
        fleetVerifierDecision={{
          audit_id: 'a1',
          merged_packet_trace_id: 'merged-1',
          verdict: 'FLAG_FOR_HUMAN_REVIEW',
          confidence: null,
          source: 'fleet_packet_verifier',
          reason: 'Needs an explicit verifier decision.',
          decision_scope: 'distributed_fleet_merged_packet',
          coverage: {
            basis: 'fleet_worker_fragments',
            total_jobs: 1,
            completed_fragments: 1,
            failed_jobs: 0,
            missing_output_jobs: 0,
            distributed_merge_status: 'complete',
          },
          proof_chip_gate: 'blocked',
          blockers: [],
          next_actions: [],
          created_at: '2026-06-05T00:00:00Z',
        }}
      />,
    );

    expect(screen.getByTestId('fleet-verifier-decision')).toHaveTextContent(
      /Fleet verifier decision: FLAG FOR HUMAN REVIEW/i,
    );
  });
});
