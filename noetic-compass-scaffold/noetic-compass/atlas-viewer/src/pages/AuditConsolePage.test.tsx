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

describe('AuditConsolePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('presents the CAS audit workflow and verdict vocabulary', () => {
    renderPage();

    expect(
      screen.getByRole('heading', {
        name: 'Connect a model. Run a CAS audit. Return a verdict with evidence.',
      }),
    ).toHaveClass('cas-heading-wave');
    expect(screen.getByText('TURN YOUR BLACK BOX INTO A GLASS HOUSE')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit command center' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'CONNECT' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'RUN' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'VERDICT' })).toBeInTheDocument();
    expect(screen.getAllByText('Run CAS audit').length).toBeGreaterThan(0);
    expect(screen.getByText('Return verdict + evidence')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Proof chips' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Hover help' })).toBeInTheDocument();
    expect(screen.getByText('License/API')).toBeInTheDocument();
    expect(screen.getByText('Audit mode')).toBeInTheDocument();
    expect(screen.getAllByText('Inspect in Atlas').length).toBeGreaterThan(0);

    expect(screen.getByText('ACCEPT')).toBeInTheDocument();
    expect(screen.getByText('SUPPRESS')).toBeInTheDocument();
    expect(screen.getByText('FLAG FOR HUMAN REVIEW')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeDisabled();
    expect(screen.getByRole('heading', { name: 'Audit not started' })).toBeInTheDocument();
    expect(
      screen.getByText('Connect a supported target before running an audit.'),
    ).toBeInTheDocument();
    expect(screen.getByText('baseline')).toHaveAttribute(
      'title',
      expect.stringContaining('comparison opponent'),
    );
  });

  it('frames Atlas as deep inspection and avoids fake verdict claims', () => {
    renderPage();

    expect(
      screen.getByText(/the UI shows ACCEPT or SUPPRESS only when the/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Audit Console is the decision workflow/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Confidence not available')).toBeInTheDocument();
  });

  it('creates a backend session and keeps the verdict pending until computed', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sessionResponse(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          sessionResponse({
            status: 'SCAFFOLD_PENDING_RUNNER',
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
                status: 'SCAFFOLD_PENDING_RUNNER',
                message: 'Stopped before verdict.',
                timestamp: '2026-05-25T11:01:00Z',
              },
            ],
          }),
      });
    vi.stubGlobal('fetch', fetchMock);

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Prepare reference session' }));
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeEnabled();
    expect(screen.getByText(/Target ready/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByText('cas-audit-test-session')).toBeInTheDocument();
    expect(
      screen.getByText('Session created. Verdict blocked until an Evidence Packet is attached.'),
    ).toBeInTheDocument();
    expect(screen.getAllByText('Runner pending').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'NO VERDICT YET' })).toBeInTheDocument();
    expect(screen.getByLabelText('Confidence not available')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/cas-harness/audit/session',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/cas-harness/audit/session/cas-audit-test-session/run',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('explains a backend ACCEPT verdict with verifier reason and proof chips', async () => {
    const allPresentChips = [
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
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sessionResponse({
          evidence_packet_trace_id: 'stage21-allow-001',
          provenance_chips: allPresentChips,
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
            provenance_chips: allPresentChips,
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

    fireEvent.click(screen.getByRole('button', { name: 'Prepare reference session' }));
    fireEvent.click(screen.getByRole('button', { name: 'Run audit' }));

    expect(await screen.findByRole('heading', { name: 'ACCEPT' })).toBeInTheDocument();
    expect(screen.getByText(/Accepted because the verifier explicitly allowed it/i)).toBeInTheDocument();
    expect(screen.getByText(/CAS accepted this output because the verifier allowed it and 6\/6/i)).toBeInTheDocument();
    expect(screen.getByText(/Stage 19 accepted_accuracy/i)).toBeInTheDocument();
    expect(screen.getByText(/Verifier source: stage19_verification_stack\+stage20_generation_readiness/i)).toBeInTheDocument();
  });

  it('keeps navigation links available', () => {
    renderPage();

    expect(screen.getByRole('link', { name: 'Open Atlas cockpit' })).toHaveAttribute(
      'href',
      '/cockpit',
    );
  });
});
