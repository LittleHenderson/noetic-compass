import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AuditConsolePage from './AuditConsolePage';
import { AccountAuthProvider } from '../components/auth/AccountAuthProvider';
import { buildCasHarnessFleetEvidenceFragmentRef } from '../lib/casHarnessAuditApi';

const LIVE_WORKER_HEALTH_PATH = '/api/cas-harness/live-worker/health';
const SESSION_LIST_PATH = '/api/cas-harness/audit/sessions';

function liveWorkerHealthResponse(overrides: Record<string, unknown> = {}) {
  return {
    configured: false,
    reachable: false,
    real_weights: false,
    model_id: null,
    worker_version: null,
    label: 'Live worker not configured',
    ...overrides,
  };
}

function isLiveWorkerHealthCall(input: unknown): boolean {
  return typeof input === 'string' && input.endsWith(LIVE_WORKER_HEALTH_PATH);
}

// The left rail's Recent Runs probe (GET /sessions) fires on every mount. Like
// the live-worker health probe, it must be answered out-of-band so the ordered
// flow mocks keep their call indices.
function isSessionListCall(input: unknown): boolean {
  return typeof input === 'string' && input.endsWith(SESSION_LIST_PATH);
}

/**
 * Install a global fetch that answers the Audit Console's mount-time
 * live-worker health probe AND the left-rail Recent Runs probe separately,
 * then delegates every other request to `orderedMock`. Tests keep asserting
 * against `orderedMock`, so its call indices and counts stay unaffected by
 * the two mount-time probes.
 */
function stubFetchWithLiveWorker(
  orderedMock: ReturnType<typeof vi.fn>,
  healthOverrides: Record<string, unknown> = {},
) {
  const router = vi.fn((input: unknown, init?: unknown) => {
    if (isLiveWorkerHealthCall(input)) {
      return Promise.resolve({
        ok: true,
        json: async () => liveWorkerHealthResponse(healthOverrides),
      });
    }
    if (isSessionListCall(input)) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ sessions: [] }),
      });
    }
    return orderedMock(input, init);
  });
  vi.stubGlobal('fetch', router);
  return router;
}

const S7_F28_TRACE_ID = 's7-f28-balanced-bridge-gpt-neox-20b-20260526';
const STAGE9_40E_TRACE_ID = 'stage9-40e-original-baseline-readout-20260527';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/audit-console']}>
      <AccountAuthProvider>
        <AuditConsolePage />
      </AccountAuthProvider>
    </MemoryRouter>
  );
}

function sessionResponse(overrides: Record<string, unknown> = {}) {
  return {
    audit_id: 'cas-audit-test-session',
    status: 'DRAFT',
    model_status: 'NOT_CONNECTED_MOCK',
    model_id: 'EleutherAI/pythia-160m',
    endpoint_url: null,
    audit_mode: 'BALANCED',
    prompt_summary: null,
    scenario_summary:
      'Reference audit smoke scenario: validate the CAS Harness audit contract without fabricating a verdict.',
    selected_modules: [
      'model_proof',
      'cas_readout',
      'causal_proof',
      'control_proof',
      'output_proof',
      'packet_proof',
    ],
    created_at: '2026-05-25T11:00:00Z',
    updated_at: '2026-05-25T11:00:00Z',
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    atlas_deep_link: null,
    verifier_decision: null,
    provenance_chips: [
      {
        id: 'model_proof',
        name: 'Model proof',
        status: 'missing',
        detail: 'No model proof has been verified for this audit session yet.',
      },
      {
        id: 'cas_readout',
        name: 'CAS readout',
        status: 'unavailable',
        detail: 'No CAS readout exists until an Evidence Packet is attached.',
      },
      {
        id: 'causal_proof',
        name: 'Causal proof',
        status: 'unavailable',
        detail: 'No causal proof exists yet.',
      },
      {
        id: 'control_proof',
        name: 'Control proof',
        status: 'unavailable',
        detail: 'No matched control proof exists yet.',
      },
      {
        id: 'output_proof',
        name: 'Output proof',
        status: 'unavailable',
        detail: 'No output proof exists yet.',
      },
      {
        id: 'packet_proof',
        name: 'Packet proof',
        status: 'missing',
        detail: 'No Evidence Packet has been attached.',
      },
    ],
    lifecycle: [
      {
        status: 'DRAFT',
        message: 'Audit session created.',
        timestamp: '2026-05-25T11:00:00Z',
      },
    ],
    ...overrides,
  };
}

function targetVerification(overrides: Record<string, unknown> = {}) {
  return {
    connection_id: 'cas-target-demo',
    connection_state: 'CONNECTED',
    model_status: 'CONNECTED',
    can_run_audit: true,
    target: {
      kind: 'demo_reference',
      provider: 'cas_harness_reference',
      model_id: 'EleutherAI/pythia-160m',
      endpoint_url: null,
      credential_mode: 'none',
      timeout_ms: 10000,
    },
    detail:
      'CAS Harness reference target verified locally. No external model call, credential, Evidence Packet, or audit verdict was created.',
    checked_at: '2026-05-26T10:00:00Z',
    provenance_chip: {
      id: 'model_proof',
      name: 'Model proof',
      status: 'verified',
      detail: 'Reference target verified for non-secret Audit Console demos.',
    },
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    reference_evidence_packet_trace_id: 'cas_harness_reference_accept_001',
    atlas_deep_link: null,
    ...overrides,
  };
}

function allPresentChips() {
  return [
    'model_proof',
    'cas_readout',
    'causal_proof',
    'control_proof',
    'output_proof',
    'packet_proof',
  ].map((id) => ({
    id,
    name: id === 'cas_readout'
      ? 'CAS readout'
      : `${id.replace('_', ' ')}`
          .replace(/\b\w/g, (letter) => letter.toUpperCase()),
    status: 'present',
    detail: `${id} present`,
  }));
}

function stage940EChips() {
  return [
    { id: 'model_proof', name: 'Model proof', status: 'present', detail: 'Model identity/hash evidence is recorded in the packet.' },
    { id: 'cas_readout', name: 'CAS readout', status: 'verified', detail: 'Corrected Stage 9 40E hidden-state readout beats text and shuffled controls.' },
    { id: 'causal_proof', name: 'Causal proof', status: 'verified', detail: 'Subspace ablation/control evidence is recorded for the Stage 9 40E readout.' },
    { id: 'control_proof', name: 'Control proof', status: 'verified', detail: 'Candidate cover/control evidence is recorded for the Stage 9 40E run.' },
    { id: 'output_proof', name: 'Output proof', status: 'verified', detail: 'Eta-to-epsilon readable bridge output evidence is recorded.' },
    { id: 'packet_proof', name: 'Packet proof', status: 'present', detail: 'Evidence Packet schema, trace ID, and source artifact hashes are recorded.' },
  ];
}

function scalePlan() {
  return {
    model_id: 'customer/open-weight-100b',
    weight_access: 'open_weight',
    parameter_count_b: 100,
    num_layers: 120,
    scale_tier: 'enterprise_distributed_open_weight',
    recommended_worker_count: 12,
    orchestration_pattern: 'CAS Orchestrator + distributed Probe Workers.',
    worker_assignments: [
      {
        worker_id: 'probe-worker-01',
        layer_start: 0,
        layer_end: 9,
        shard_id: 'layers-000-009',
        assigned_methods: ['foundation_probe'],
        expected_outputs: ['layer_activation_summary'],
      },
    ],
    memory_estimate: {
      precision: 'bf16',
      total_weight_memory_gb: 200,
      activation_overhead_gb: 36,
      estimated_total_runtime_gb: 236,
      estimated_memory_per_worker_gb: 19.67,
    },
    expected_capability: ['single orchestrated Evidence Packet across all workers'],
    evidence_requirements: ['open model weights or customer-hosted activation hooks'],
    limitations: ['does not support black-box/API-only model audits in this product lane'],
  };
}

function distributedAudit(overrides: Record<string, unknown> = {}) {
  return {
    audit_id: 'cas-dist-unit',
    plan_id: 'cas-plan-unit',
    status: 'PLANNED',
    merge_status: 'pending',
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    merge_reason: 'Distributed audit planned; no worker evidence has been merged yet.',
    created_at: '2026-05-26T10:00:00Z',
    updated_at: '2026-05-26T10:00:00Z',
    plan: scalePlan(),
    worker_evidence: [
      {
        worker_id: 'probe-worker-01',
        layer_start: 0,
        layer_end: 9,
        shard_id: 'layers-000-009',
        assigned_methods: ['foundation_probe'],
        expected_outputs: ['layer_activation_summary'],
        worker_status: 'queued',
        produced_outputs: [],
        missing_outputs: [],
        evidence_packet_ref: null,
        error_message: null,
        updated_at: '2026-05-26T10:00:00Z',
      },
    ],
    ready_workers: 0,
    failed_workers: 0,
    total_workers: 1,
    missing_outputs: [],
    ...overrides,
  };
}

function fleetWorker(overrides: Record<string, unknown> = {}) {
  return {
    worker_id: 'probe-worker-01',
    model_id: 'customer/open-weight-100b',
    worker_url: 'local://probe-worker-01',
    gpu_type: 'H100-80GB',
    capacity: 1,
    supported_methods: [
      'foundation_probe',
      'rpm_gate_check',
      'inversion_scan',
      'blindspot_detection',
      'verification_stack',
      'evidence_packet',
    ],
    registered_at: '2026-05-26T10:00:00Z',
    last_heartbeat_at: '2026-05-26T10:00:01Z',
    status: 'active',
    ...overrides,
  };
}

function fleetJob(overrides: Record<string, unknown> = {}) {
  return {
    job_id: 'fleet-job-001',
    audit_id: 'cas-dist-unit',
    assigned_worker_id: 'probe-worker-01',
    layer_start: 0,
    layer_end: 9,
    shard_id: 'layers-000-009',
    assigned_methods: ['foundation_probe'],
    expected_outputs: ['layer_activation_summary'],
    status: 'queued',
    lease_token: null,
    lease_expires_at: null,
    evidence_packet_fragment_ref: null,
    produced_outputs: [],
    missing_outputs: [],
    error_message: null,
    updated_at: '2026-05-26T10:00:00Z',
    ...overrides,
  };
}

function fleetRun(overrides: Record<string, unknown> = {}) {
  return {
    audit_id: 'cas-dist-unit',
    status: 'PREPARED',
    verifier_gate_status: 'waiting_for_workers',
    merged_packet_trace_id: null,
    merge_reason: 'Fleet jobs prepared; waiting for registered workers.',
    created_at: '2026-05-26T10:00:00Z',
    updated_at: '2026-05-26T10:00:00Z',
    total_jobs: 1,
    leased_jobs: 0,
    completed_fragments: 0,
    failed_jobs: 0,
    registered_workers: 0,
    stale_workers: [],
    readiness: {
      status: 'waiting',
      headline: 'Large-model eval is waiting on workers or fragment receipts.',
      blockers: ['1 assigned worker job(s) still need a registered, compatible, fresh-heartbeat worker.'],
      next_actions: ['Register or heartbeat every assigned Probe Worker.'],
      verifier_owned: true,
    },
    jobs: [fleetJob()],
    ...overrides,
  };
}

function fleetVerifierDecision(overrides: Record<string, unknown> = {}) {
  return {
    audit_id: 'cas-dist-unit',
    merged_packet_trace_id: 'cas-dist-unit-merged-packet',
    verdict: 'FLAG_FOR_HUMAN_REVIEW',
    confidence: null,
    source: 'fleet_packet_verifier',
    reason:
      'Fleet receipts are merged, but ACCEPT/SUPPRESS requires an explicit verifier decision over the merged Evidence Packet.',
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
    blockers: [
      'Merged distributed packet has worker receipts but no explicit proof-chip verifier decision.',
    ],
    next_actions: [
      'Attach Stage 19/20/21 verifier output or packet-level explicit_verifier_decision.',
      'Keep the public verdict at FLAG FOR HUMAN REVIEW until proof chips pass.',
    ],
    created_at: '2026-05-26T10:05:00Z',
    ...overrides,
  };
}

async function fleetFragmentRef(
  overrides: Partial<Parameters<typeof buildCasHarnessFleetEvidenceFragmentRef>[0]> = {},
) {
  return buildCasHarnessFleetEvidenceFragmentRef({
    audit_id: 'cas-dist-unit',
    job_id: 'fleet-job-001',
    worker_id: 'probe-worker-01',
    model_id: 'customer/open-weight-100b',
    layer_start: 0,
    layer_end: 9,
    shard_id: 'layers-000-009',
    expected_outputs: ['layer_activation_summary'],
    produced_outputs: ['layer_activation_summary'],
    missing_outputs: [],
    ...overrides,
  });
}

describe('AuditConsolePage', () => {
  beforeEach(() => {
    // Default global fetch answers only the mount-time live-worker health
    // probe so render-only tests have a deterministic, non-throwing stub.
    // Flow tests override this via stubFetchWithLiveWorker(...) before acting.
    vi.stubGlobal(
      'fetch',
      vi.fn((input: unknown) => {
        if (isLiveWorkerHealthCall(input)) {
          return Promise.resolve({
            ok: true,
            json: async () => liveWorkerHealthResponse(),
          });
        }
        if (isSessionListCall(input)) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ sessions: [] }),
          });
        }
        return Promise.reject(new Error(`unexpected fetch: ${String(input)}`));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('presents the consolidated composer center without the old command-center clutter', () => {
    renderPage();

    // The calm run header replaces the giant animated marketing H1.
    expect(
      screen.queryByText(
        'Connect a model. Run a CAS audit. Return a verdict with evidence.',
      ),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('TURN YOUR BLACK BOX INTO A GLASS HOUSE')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Audit command center' })).not.toBeInTheDocument();
    expect(screen.queryByText(/Worker evidence, not planner theater/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'CONNECT' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'RUN' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'VERDICT' })).not.toBeInTheDocument();

    // The new composer surface is present.
    expect(screen.getByRole('heading', { name: 'Set up an audit' })).toBeInTheDocument();
    expect(screen.getByLabelText('Audit run header')).toBeInTheDocument();
    expect(screen.getByText('Start an audit')).toBeInTheDocument();

    // The pending verdict chip lives in the right rail.
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();

    // The ModelConnectionCard "Run audit" button is disabled before a target is
    // connected; the composer primary action invites connecting the target.
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Prepare target' })).toBeEnabled();
  });

  it('hides the enterprise / distributed / fleet machinery behind the advanced disclosure', () => {
    renderPage();

    // None of the scale/fleet controls render on the default audit view.
    expect(screen.queryByRole('button', { name: 'Create run' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Prepare fleet' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Run fleet verifier' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Fleet executor controls' })).not.toBeInTheDocument();

    // They live behind the "Scale & fleet (advanced)" disclosure.
    const disclosure = screen.getByRole('button', { name: /Scale & fleet \(advanced\)/i });
    expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(disclosure);
    expect(screen.getByRole('button', { name: 'Create run' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Prepare fleet' })).toBeInTheDocument();
  });

  it('opens the "Why this verdict" methodology drawer only after a verdict exists', async () => {
    renderPage();

    // No verdict yet -> no "Why this verdict" affordance, and the Stage-19/20/21
    // methodology vocabulary is NOT on the default surface.
    expect(
      screen.queryByRole('button', { name: /Why this verdict/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Stage 19 accepted_accuracy/i)).not.toBeInTheDocument();
    // The left-rail Help button opens the same drawer.
    fireEvent.click(screen.getByRole('button', { name: '? Help' }));
    expect(await screen.findByTestId('methodology-drawer')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Why this verdict' })).toBeInTheDocument();
    // The internal scoring vocabulary lives inside the drawer.
    expect(screen.getByText(/Stage 19 \/ accepted_accuracy/i)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('methodology-drawer-close'));
  });

  it('keeps the pending verdict compact', () => {
    renderPage();

    expect(screen.getByLabelText('Confidence not available')).toBeInTheDocument();
    expect(screen.queryByText(/No verdict yet\. Run a CAS audit/i)).not.toBeInTheDocument();
  });

  it('creates a reference-backed backend session and shows the evidence-gated verdict', async () => {
    const chips = allPresentChips();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => targetVerification(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            evidence_packet_trace_id: 'cas_harness_reference_accept_001',
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'ACCEPT',
              confidence: 0.9816,
              source: 'stage19_verification_stack+stage20_generation_readiness',
              reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
            },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            verdict: 'ACCEPT',
            confidence: 0.9816,
            evidence_packet_trace_id: 'cas_harness_reference_accept_001',
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'ACCEPT',
              confidence: 0.9816,
              source: 'stage19_verification_stack+stage20_generation_readiness',
              reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
            },
            updated_at: '2026-05-25T11:01:00Z',
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created.',
                timestamp: '2026-05-25T11:00:00Z',
              },
              {
                status: 'VALIDATING',
                message: 'Input contract validated.',
                timestamp: '2026-05-25T11:00:30Z',
              },
              {
                status: 'RUNNING',
                message: 'Run requested.',
                timestamp: '2026-05-25T11:00:45Z',
              },
              {
                status: 'COMPLETE',
                message: 'M3 verdict runner returned the explicit verifier decision from the attached evidence contract.',
                timestamp: '2026-05-25T11:01:00Z',
              },
            ],
          }),
      });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();
    expect(screen.getByRole('note', { name: /reference target verified/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByText(/Audit cas-audit-test-session/)).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit complete' })).toBeInTheDocument();
    // Confidence detail lives in the methodology drawer now.
    fireEvent.click(screen.getByRole('button', { name: /Why this verdict/i }));
    expect(await screen.findByText('Confidence: 98%')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/cas-harness/audit/target/verify',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toEqual({
      target: { kind: 'demo_reference' },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/cas-harness/audit/session',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body))).toMatchObject({
      evidence_packet_trace_id: 'cas_harness_reference_accept_001',
      model_id: 'EleutherAI/pythia-160m',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/cas-harness/audit/session/cas-audit-test-session/run',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('sends a customer BYOK key in the run body and surfaces the honest audit scope label', async () => {
    const chips = allPresentChips();
    const scope = {
      kind: 'output_only_api_harvest',
      label: 'Output-only harvest · no internal activation access · verdict held for review',
      internal_activation_access: false,
      verdict_disposition: 'held_for_human_review',
      detail: 'Closed API target. No weights or activations were accessible.',
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => targetVerification() })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            evidence_packet_trace_id: 'cas_harness_byok_001',
            provenance_chips: chips,
            audit_scope: scope,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'EVIDENCE_PENDING',
            evidence_packet_trace_id: 'cas_harness_byok_001',
            provenance_chips: chips,
            audit_scope: scope,
            updated_at: '2026-05-25T11:01:00Z',
          }),
      });
    // Route the mount-time live-worker health probe away from the ordered mock
    // so the BYOK call sequence (verify -> session -> run) keeps its indices.
    stubFetchWithLiveWorker(fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();

    fireEvent.change(
      screen.getByLabelText('Bring your own provider API key (optional)'),
      { target: { value: 'sk-customer-secret' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    // The honest scope label is now surfaced as a persistent "Scope: …" chip
    // (left rail) and ScopeRibbon (right rail), replacing the old inline banner.
    expect(
      (
        await screen.findAllByText(
          'Scope: Output-only harvest · no internal activation access · verdict held for review',
        )
      ).length,
    ).toBeGreaterThan(0);

    const runCall = fetchMock.mock.calls[2];
    expect(runCall[0]).toBe('/api/cas-harness/audit/session/cas-audit-test-session/run');
    expect(JSON.parse(String((runCall[1] as RequestInit).body))).toEqual({
      api_key: 'sk-customer-secret',
    });
  });

  it('loads the S7-F28 20B evidence packet into the audit lifecycle', async () => {
    const chips = allPresentChips();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            model_id: 'EleutherAI/gpt-neox-20b',
            scenario_summary:
              'Stage 7 Foundation-28 GPT-NeoX-20B evidence packet review using the S7-F28 Balanced Bridge Method.',
            evidence_packet_trace_id: S7_F28_TRACE_ID,
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'FLAG_FOR_HUMAN_REVIEW',
              confidence: 0.803571,
              source: 'S7-F28-BALANCED-BRIDGE',
              reason:
                'S7-F28 packet is strong evidence but routes to human review until the final verifier merge layer closes.',
            },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            model_id: 'EleutherAI/gpt-neox-20b',
            verdict: 'FLAG_FOR_HUMAN_REVIEW',
            confidence: 0.803571,
            scenario_summary:
              'Stage 7 Foundation-28 GPT-NeoX-20B evidence packet review using the S7-F28 Balanced Bridge Method.',
            evidence_packet_trace_id: S7_F28_TRACE_ID,
            atlas_deep_link: `/cockpit?trace_id=${S7_F28_TRACE_ID}`,
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'FLAG_FOR_HUMAN_REVIEW',
              confidence: 0.803571,
              source: 'S7-F28-BALANCED-BRIDGE',
              reason:
                'S7-F28 packet is strong evidence but routes to human review until the final verifier merge layer closes.',
            },
            updated_at: '2026-05-26T22:06:00Z',
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created with S7-F28 Evidence Packet.',
                timestamp: '2026-05-26T22:05:00Z',
              },
              {
                status: 'COMPLETE',
                message:
                  'S7-F28 Balanced Bridge packet returned a conservative human-review verdict.',
                timestamp: '2026-05-26T22:06:00Z',
              },
            ],
          }),
      });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Load 20B review packet' }));

    expect(screen.getAllByText('EleutherAI/gpt-neox-20b').length).toBeGreaterThan(0);
    expect(screen.getByText('S7-F28 Balanced Bridge Method')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(
      await screen.findByRole('heading', { name: 'FLAG FOR HUMAN REVIEW' }),
    ).toBeInTheDocument();
    // Confidence detail lives in the methodology drawer now.
    fireEvent.click(screen.getByRole('button', { name: /Why this verdict/i }));
    expect(await screen.findByText('Confidence: 80%')).toBeInTheDocument();
    expect(screen.getAllByText(S7_F28_TRACE_ID).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/cas-harness/audit/session',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toMatchObject({
      evidence_packet_trace_id: S7_F28_TRACE_ID,
      model_id: 'EleutherAI/gpt-neox-20b',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/cas-harness/audit/session/cas-audit-test-session/run',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('loads the Stage 9 40E 20B validation packet and shows the WORM gate', async () => {
    const chips = stage940EChips();
    const verifierDecision = {
      verdict: 'ACCEPT',
      confidence: 0.95625,
      source: 'stage9_40e_packet_verifier',
      reason: 'all_stage9_40e_validation_gates_passed',
      decision_scope: 'stage9_40e_validation_packet',
      coverage: {
        basis: 'stage9_40e_validation_cases',
        case_count: 80,
        class_count: 40,
      },
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            model_id: 'EleutherAI/gpt-neox-20b',
            scenario_summary:
              'Stage 9 original 40-Element GPT-NeoX-20B validation packet. It carries a verifier ACCEPT decision, but routes to review unless WORM packet proof is attached.',
            evidence_packet_trace_id: STAGE9_40E_TRACE_ID,
            provenance_chips: chips,
            verifier_decision: verifierDecision,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            model_id: 'EleutherAI/gpt-neox-20b',
            verdict: 'FLAG_FOR_HUMAN_REVIEW',
            confidence: null,
            scenario_summary:
              'Stage 9 original 40-Element GPT-NeoX-20B validation packet. It carries a verifier ACCEPT decision, but routes to review unless WORM packet proof is attached.',
            evidence_packet_trace_id: STAGE9_40E_TRACE_ID,
            atlas_deep_link: `/cockpit?trace_id=${STAGE9_40E_TRACE_ID}`,
            provenance_chips: chips,
            verifier_decision: verifierDecision,
            updated_at: '2026-05-28T07:31:00Z',
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created with Stage 9 40E Evidence Packet.',
                timestamp: '2026-05-28T07:30:00Z',
              },
              {
                status: 'COMPLETE',
                message:
                  'M3 verdict runner blocked the explicit verifier decision because final ACCEPT/SUPPRESS requires an Evidence Packet with active Object Lock retention. Packet proof must be S3 re-read verified with active Object Lock retention.',
                timestamp: '2026-05-28T07:31:00Z',
              },
            ],
          }),
      });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Load 20B validation packet' }));

    expect(screen.getAllByText('EleutherAI/gpt-neox-20b').length).toBeGreaterThan(0);
    expect(screen.getByText('Stage 9 original 40E validation packet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByRole('heading', { name: 'FLAG FOR HUMAN REVIEW' })).toBeInTheDocument();
    // The scope label is on the persistent right-rail ScopeRibbon (no drawer needed).
    expect(
      screen.getAllByText('Scope: Stage 9 40E validation packet').length,
    ).toBeGreaterThan(0);
    // Confidence basis, coverage, and the WORM-gate prose live in the drawer.
    fireEvent.click(screen.getByRole('button', { name: /Why this verdict/i }));
    expect(await screen.findByText('Confidence: not available')).toBeInTheDocument();
    expect(screen.getByText('Coverage: 80 cases / 40 classes')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Flagged because the Evidence Packet does not have active Object Lock retention yet.',
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText(STAGE9_40E_TRACE_ID).length).toBeGreaterThan(0);
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toMatchObject({
      evidence_packet_trace_id: STAGE9_40E_TRACE_ID,
      model_id: 'EleutherAI/gpt-neox-20b',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/cas-harness/audit/session/cas-audit-test-session/run',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('creates and dispatches a distributed audit run from the enterprise plan panel', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => distributedAudit(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => distributedAudit({ status: 'DISPATCHED' }),
      });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Scale & fleet \(advanced\)/i }));

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    expect(await screen.findByText('cas-dist-unit')).toBeInTheDocument();
    expect(screen.getByText('0/1 ready')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));
    expect(await screen.findByText('DISPATCHED')).toBeInTheDocument();
    expect(screen.getByTestId('distributed-merge-gate')).toHaveTextContent(/worker receipt is still pending/i);
    expect(screen.getByRole('button', { name: 'Merge distributed receipts' })).toBeDisabled();

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/session',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/dispatch',
    ]);
  });

  it('wires fleet executor controls to prepare, register, lease, receipt, and merge APIs', async () => {
    const fragmentRef = await fleetFragmentRef();
    const leasedJob = fleetJob({
      status: 'leased',
      lease_token: 'lease-token-001',
      lease_expires_at: '2026-05-26T10:05:00Z',
      updated_at: '2026-05-26T10:01:00Z',
    });
    const completedJob = fleetJob({
      status: 'completed',
      evidence_packet_fragment_ref: fragmentRef,
      produced_outputs: ['layer_activation_summary'],
      updated_at: '2026-05-26T10:02:00Z',
    });
    const readyRun = fleetRun({
      status: 'MERGE_PENDING',
      verifier_gate_status: 'ready_for_verifier',
      merge_reason: 'All worker Evidence Packet fragments returned; verifier gate is ready.',
      registered_workers: 1,
      completed_fragments: 1,
      readiness: {
        status: 'ready',
        headline: 'Large-model worker receipts are complete; verifier review is unblocked.',
        blockers: [],
        next_actions: [
          'Merge fleet evidence into one distributed Evidence Packet.',
          'Then run the verifier decision layer; fleet merge alone cannot ACCEPT.',
        ],
        verifier_owned: true,
      },
      jobs: [completedJob],
    });
    const mergedRun = fleetRun({
      status: 'COMPLETE',
      verifier_gate_status: 'ready_for_verifier',
      merged_packet_trace_id: 'cas-dist-unit-merged-packet',
      merge_reason:
        'Merged packet ready for verifier decision. Final ACCEPT/SUPPRESS still requires verifier decision layer.',
      registered_workers: 1,
      completed_fragments: 1,
      readiness: {
        status: 'ready',
        headline: 'Large-model worker receipts are complete; verifier review is unblocked.',
        blockers: [],
        next_actions: ['Run the verifier decision layer over the merged Evidence Packet.'],
        verifier_owned: true,
      },
      jobs: [completedJob],
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => distributedAudit(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          distributedAudit({
            status: 'DISPATCHED',
            worker_evidence: [
              {
                ...distributedAudit().worker_evidence[0],
                worker_status: 'assigned',
              },
            ],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => fleetRun(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => fleetWorker(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => leasedJob,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => readyRun,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mergedRun,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => fleetVerifierDecision(),
      });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Scale & fleet \(advanced\)/i }));

    expect(screen.getByRole('button', { name: 'Prepare fleet' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Run fleet verifier' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Protected API token'), {
      target: { value: 'fleet-jwt' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    expect(await screen.findByText('cas-dist-unit')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));
    expect(await screen.findByText('DISPATCHED')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare fleet' }));
    expect(await screen.findByTestId('fleet-executor-gate')).toHaveTextContent(
      /waiting for registered/i,
    );
    expect(screen.getByTestId('fleet-readiness-summary')).toHaveTextContent(
      /waiting on workers or fragment receipts/i,
    );
    expect(screen.getByRole('button', { name: 'Lease one job' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Register demo worker' }));
    expect(await screen.findByText('1/1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Lease one job' }));
    expect(await screen.findByText('1/1')).toBeInTheDocument();
    expect(screen.getByTestId('fleet-executor-gate')).toHaveTextContent(/receipts are still missing/i);
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();
    expect(screen.queryByText('lease-token-001')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Submit one receipt' }));
    expect(await screen.findByText('ready for verifier')).toBeInTheDocument();
    expect(screen.getByTestId('fleet-readiness-summary')).toHaveTextContent(
      /verifier review is unblocked/i,
    );
    expect(screen.getByTestId('fleet-readiness-actions')).toHaveTextContent(
      /fleet merge alone cannot ACCEPT/i,
    );
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Merge fleet' }));
    expect(await screen.findByText(/cas-dist-unit-merged-packet/)).toBeInTheDocument();
    expect(screen.getByText(/Final ACCEPT\/SUPPRESS still requires verifier decision layer/i)).toBeInTheDocument();
    expect(screen.getByTestId('fleet-readiness-actions')).toHaveTextContent(
      /Run the verifier decision layer over the merged Evidence Packet/i,
    );
    expect(screen.getByRole('button', { name: 'Run fleet verifier' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Run fleet verifier' }));
    expect(await screen.findByTestId('fleet-verifier-decision')).toHaveTextContent(
      /Fleet verifier decision: FLAG FOR HUMAN REVIEW/i,
    );
    expect(screen.getByTestId('fleet-verifier-decision')).toHaveTextContent(
      /no explicit proof-chip verifier decision/i,
    );

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/cas-harness/audit/distributed/session',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/dispatch',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/prepare',
      '/api/cas-harness/audit/distributed/fleet/worker/register',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/job/lease',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/job/fleet-job-001/receipt',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/merge',
      '/api/cas-harness/audit/distributed/session/cas-dist-unit/fleet/verifier',
    ]);
    expect(JSON.parse(String((fetchMock.mock.calls[3][1] as RequestInit).body))).toMatchObject({
      worker_id: 'probe-worker-01',
      gpu_type: 'H100-80GB',
    });
    expect(JSON.parse(String((fetchMock.mock.calls[5][1] as RequestInit).body))).toMatchObject({
      worker_id: 'probe-worker-01',
      lease_token: 'lease-token-001',
      evidence_packet_fragment_ref: fragmentRef,
      job_status: 'completed',
    });
    for (const call of fetchMock.mock.calls) {
      expect((call[1] as RequestInit).headers).toMatchObject({
        Authorization: 'Bearer fleet-jwt',
      });
    }
  }, 15000);

  it('keeps fleet merge disabled when the backend verifier gate is blocked', async () => {
    const blockedFragmentRef = await fleetFragmentRef({
      produced_outputs: [],
      missing_outputs: ['layer_activation_summary'],
    });
    const leasedJob = fleetJob({
      status: 'leased',
      lease_token: 'lease-token-001',
      lease_expires_at: '2026-05-26T10:05:00Z',
      updated_at: '2026-05-26T10:01:00Z',
    });
    const blockedJob = fleetJob({
      status: 'completed',
      evidence_packet_fragment_ref: blockedFragmentRef,
      produced_outputs: [],
      missing_outputs: ['layer_activation_summary'],
      updated_at: '2026-05-26T10:02:00Z',
    });
    const blockedRun = fleetRun({
      status: 'MERGE_PENDING',
      verifier_gate_status: 'blocked_missing_outputs',
      merge_reason: 'At least one worker receipt is missing required outputs; cannot ACCEPT.',
      registered_workers: 1,
      completed_fragments: 1,
      readiness: {
        status: 'blocked',
        headline: 'Large-model eval is blocked; the run cannot support ACCEPT.',
        blockers: ['1 completed receipt(s) are missing required outputs.'],
        next_actions: ['Rerun incomplete jobs with all expected outputs or route to human review.'],
        verifier_owned: true,
      },
      jobs: [blockedJob],
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => distributedAudit() })
      .mockResolvedValueOnce({ ok: true, json: async () => distributedAudit({ status: 'DISPATCHED' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => fleetRun() })
      .mockResolvedValueOnce({ ok: true, json: async () => fleetWorker() })
      .mockResolvedValueOnce({ ok: true, json: async () => leasedJob })
      .mockResolvedValueOnce({ ok: true, json: async () => blockedRun });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Scale & fleet \(advanced\)/i }));

    fireEvent.click(screen.getByRole('button', { name: 'Create run' }));
    expect(await screen.findByText('cas-dist-unit')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Dispatch workers' }));
    expect(await screen.findByText('DISPATCHED')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Prepare fleet' }));
    expect(await screen.findByTestId('fleet-executor-gate')).toHaveTextContent(/waiting for registered/i);
    fireEvent.click(screen.getByRole('button', { name: 'Register demo worker' }));
    expect(await screen.findByText('1/1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Lease one job' }));
    expect(await screen.findByText('waiting for receipts')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Submit one receipt' }));

    expect(await screen.findByTestId('fleet-executor-gate')).toHaveTextContent(/missing required outputs/i);
    expect(screen.getByRole('button', { name: 'Merge fleet' })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(6);
  });

  it('explains a backend ACCEPT verdict with verifier reason and proof chips', async () => {
    const chips = allPresentChips();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => targetVerification(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sessionResponse({
          evidence_packet_trace_id: 'stage21-allow-001',
          provenance_chips: chips,
          verifier_decision: {
            verdict: 'ACCEPT',
            confidence: 0.9816,
            source: 'stage19_verification_stack+stage20_generation_readiness',
            reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'COMPLETE',
            verdict: 'ACCEPT',
            confidence: 0.9816,
            evidence_packet_trace_id: 'stage21-allow-001',
            provenance_chips: chips,
            verifier_decision: {
              verdict: 'ACCEPT',
              confidence: 0.9816,
              source: 'stage19_verification_stack+stage20_generation_readiness',
              reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
            },
            lifecycle: [
              {
                status: 'DRAFT',
                message: 'Audit session created.',
                timestamp: '2026-05-25T11:00:00Z',
              },
              {
                status: 'COMPLETE',
                message: 'M3 verdict runner returned the explicit verifier decision from the attached evidence contract.',
                timestamp: '2026-05-25T11:01:00Z',
              },
            ],
          }),
      });
    stubFetchWithLiveWorker(fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    // The verifier reason + proof prose live behind the "Why this verdict" drawer.
    fireEvent.click(screen.getByRole('button', { name: /Why this verdict/i }));
    expect(
      await screen.findByText(/Accepted because the verifier explicitly allowed it/i),
    ).toBeInTheDocument();
    expect(screen.getByText('Proof chips ready: 6/6')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 98%')).toBeInTheDocument();
    expect(
      screen.getByRole('note', { name: /Stage 19 accepted the row and Stage 20 readiness action is allow/i }),
    ).toBeInTheDocument();
  });

  describe('live-worker status chip', () => {
    function renderWithLiveWorkerHealth(
      overrides: Record<string, unknown>,
    ) {
      stubFetchWithLiveWorker(vi.fn(), overrides);
      renderPage();
    }

    function findLiveWorkerChip() {
      return screen.findByRole('status', { name: /Live trace status:/i });
    }

    it('shows a teal "real Pythia weights" chip only when real weights are confirmed', async () => {
      renderWithLiveWorkerHealth({
        configured: true,
        reachable: true,
        real_weights: true,
        model_id: 'EleutherAI/pythia-160m',
        worker_version: 'm2-real-pythia',
        label: 'Live worker connected · real Pythia weights',
      });

      const chip = await findLiveWorkerChip();
      expect(chip).toHaveTextContent('Live worker connected · real Pythia weights');
      // ACCENT_TEAL = #2dd4bf -> rgb(45, 212, 191)
      expect(chip).toHaveStyle({ color: 'rgb(45, 212, 191)' });
    });

    it('shows an amber chip for a reachable-but-demo worker (no real weights)', async () => {
      renderWithLiveWorkerHealth({
        configured: true,
        reachable: true,
        real_weights: false,
        model_id: 'EleutherAI/pythia-160m',
        worker_version: 'm2-real-pythia',
        label: 'Live worker reachable · demo mode (not real weights)',
      });

      const chip = await findLiveWorkerChip();
      expect(chip).toHaveTextContent('Live worker reachable · demo mode (not real weights)');
      // ACCENT_AMBER = #fbbf24 -> rgb(251, 191, 36)
      expect(chip).toHaveStyle({ color: 'rgb(251, 191, 36)' });
    });

    it('shows an amber chip when the worker is configured but unreachable', async () => {
      renderWithLiveWorkerHealth({
        configured: true,
        reachable: false,
        real_weights: false,
        model_id: null,
        worker_version: null,
        label: 'Live worker unavailable · no live audit will run',
      });

      const chip = await findLiveWorkerChip();
      expect(chip).toHaveTextContent('Live worker unavailable · no live audit will run');
      expect(chip).toHaveStyle({ color: 'rgb(251, 191, 36)' });
    });

    it('shows a muted chip when the live worker is not configured', async () => {
      renderWithLiveWorkerHealth({
        configured: false,
        reachable: false,
        real_weights: false,
        model_id: null,
        worker_version: null,
        label: 'Live worker not configured',
      });

      const chip = await findLiveWorkerChip();
      expect(chip).toHaveTextContent('Live worker not configured');
      // COLORS.textMuted = #64748b -> rgb(100, 116, 139)
      expect(chip).toHaveStyle({ color: 'rgb(100, 116, 139)' });
    });

    it('renders a calm "checking" chip before the health probe resolves and never blocks the page', () => {
      // A health probe that never settles leaves the chip in its unknown state.
      vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));

      renderPage();

      const chip = screen.getByRole('status', { name: /Live trace status:/i });
      expect(chip).toHaveTextContent('Checking live worker…');
      expect(chip).toHaveStyle({ color: 'rgb(100, 116, 139)' });
      // Page still renders its core controls.
      expect(screen.getByRole('button', { name: 'Run audit' })).toBeInTheDocument();
    });
  });
});
