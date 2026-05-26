import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AuditConsolePage from './AuditConsolePage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/audit-console']}>
      <AuditConsolePage />
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

describe('AuditConsolePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('presents the CAS audit workflow without the old explanatory clutter', () => {
    renderPage();

    const heading = screen.getByRole('heading', {
      name: 'Connect a model. Run a CAS audit. Return a verdict with evidence.',
    });
    expect(heading).toHaveClass('cas-heading-wave');
    expect(heading).not.toHaveAttribute('title');
    expect(screen.getByText('TURN YOUR BLACK BOX INTO A GLASS HOUSE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit command center' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'CONNECT' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'RUN' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'VERDICT' })).toBeInTheDocument();
    expect(screen.getAllByText('Run CAS audit').length).toBeGreaterThan(0);
    expect(screen.getByText('Return verdict + evidence')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Proof chips' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Hover help' })).not.toBeInTheDocument();
    expect(screen.queryByText('License/API')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit mode')).not.toBeInTheDocument();
    expect(screen.queryByText('Inspect in Atlas')).not.toBeInTheDocument();
    expect(screen.queryByText('Evidence count')).not.toBeInTheDocument();
    expect(screen.queryByText('Verdict vocabulary')).not.toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Run audit' })).toBeDisabled();
    expect(screen.getByRole('heading', { name: 'Audit not started' })).toBeInTheDocument();
    expect(
      screen.getByRole('note', {
        name: 'Connect a supported target before running an audit.',
      }),
    ).toBeInTheDocument();
  });

  it('keeps explanatory wording on hover targets instead of visible paragraphs', () => {
    renderPage();

    expect(
      screen.queryByText(/the UI shows ACCEPT or SUPPRESS only when the/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Audit Console is the decision workflow/i)).not.toBeInTheDocument();
    const commandSubtitle = screen.getByText('Connect. Run. Decide.');
    expect(commandSubtitle).not.toHaveAttribute('title');
    fireEvent.mouseEnter(commandSubtitle);
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'connect the target, run CAS, then return a verdict',
    );
  });

  it('keeps the pending verdict compact', () => {
    renderPage();

    expect(screen.getByLabelText('Confidence not available')).toBeInTheDocument();
    expect(screen.queryByText(/No verdict yet\. Run a CAS audit/i)).not.toBeInTheDocument();
    expect(screen.queryByText('Not created')).not.toBeInTheDocument();
    expect(screen.queryByText('Not available')).not.toBeInTheDocument();
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
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();
    expect(screen.getByRole('note', { name: /reference target verified/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByText('cas-audit-test-session')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit complete' })).toBeInTheDocument();
    expect(screen.getByText('Confidence: 98%')).toBeInTheDocument();
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
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare target' }));
    expect(await screen.findByText('Target verified')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    expect(screen.getByText(/Accepted because the verifier explicitly allowed it/i)).toBeInTheDocument();
    expect(screen.getByText('Proof chips ready: 6/6')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 98%')).toBeInTheDocument();
    expect(
      screen.getByRole('note', { name: /Stage 19 accepted the row and Stage 20 readiness action is allow/i }),
    ).toBeInTheDocument();
  });
});
