/**
 * EvidencePacketDrawer tests — Stage 21B Atlas reviewer drawer.
 *
 * Coverage (per the spec brief):
 *   1. Drawer renders all 7 tabs in the correct order.
 *   2. Loading state shows while fetch is pending.
 *   3. "evidence packet not found" shows on 404.
 *   4. Each tab renders the correct slice of a sample packet.
 *   5. Download JSON triggers a Blob download with the correct filename.
 *   6. Download Markdown fetches the /markdown endpoint.
 *   7. VerificationPanel "View full Evidence Packet" button only renders
 *      when a trace_id is present.
 *   8. Backward compatibility: nodes without verification don't crash
 *      and don't show the button.
 *
 * Fixtures are derived from
 * `research/cas_probe/evidence_packets/stage21a_*.json`.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EvidencePacketDrawer } from './EvidencePacketDrawer';
import { VerificationPanel } from './VerificationPanel';
import {
  type EvidencePacket,
  EVIDENCE_PACKET_SCHEMA_VERSION,
} from '../../lib/evidencePacket';

// ── Fixtures: condensed Stage 21A packets ──────────────────────────────────

function allowPacket(): EvidencePacket {
  return {
    schema_version: EVIDENCE_PACKET_SCHEMA_VERSION,
    trace_id: 'stage21a_allow_qwen15b_000',
    created_at: '2026-05-19',
    boundary:
      'This packet shows a bounded CAS Harness readout and readiness decision for one locked example.',
    export_label: 'allow: clean accepted Qwen readout',
    claim_badges: [
      'provenance',
      'readout',
      'verification_stack',
      'generation_readiness',
      'harness_conditioning',
    ],
    caveats: [
      'EvidencePacket v1 is an export artifact over locked Stage 19/20B reports.',
      'Readiness policy is generated from Verification Stack status in this export.',
    ],
    rejected_claims: [
      'exact_causal_neurons',
      'weights_firing',
      'raw_cas_symbol_understanding',
    ],
    model: {
      family: 'Qwen',
      model_key: 'qwen15b',
      name: 'Qwen/Qwen2.5-1.5B',
      revision: '8faed761d45a263340a0528343f099c05c9a4323',
    },
    readout: {
      axis: 'foundation',
      label: 'F1T',
      layer: 11,
      position: 'focus_token',
      confidence: null,
      confidence_source: 'verification_stack_tier',
      stable_agree: ['focus_token', 'final_token', 'mean_over_seq_len'],
      votes: {
        final_token: 'F1T',
        focus_token: 'F1T',
        mean_over_seq_len: 'F1T',
      },
    },
    controls: {
      random_ablation: 'random null controls are reported in the source claims matrices',
      text_baseline: null,
      metadata_baseline: null,
      raw_symbol_delta: -0.0002,
    },
    diagnostics: {
      lacunarity: null,
      blindspot_flags: [],
      note: 'Per-example LacunarityHead values are not present in Stage 19 reports.',
    },
    conditioning: {
      p_value: '2.92e-12',
      partner_margin: 1.6253,
      positive_cases: '83/112',
      probe_readable_delta: 0.796,
    },
    generation_readiness: {
      generation_readiness: 'allow',
      mode: 'BALANCED',
      recommended_mode: 'BALANCED',
      policy_version: 'stage20_generation_readiness_gate_v1',
      reasons: ['all_readiness_signals_within_mode_thresholds'],
      risk_score: 0.0,
      evidence: {
        inversion_flag_count: 0,
        max_gap_probability: 0.0,
        max_lacunarity: 0.0,
        mean_gap_probability: 0.0,
        min_domain_confidence: 1.0,
        mode: 'BALANCED',
        rpm_satisfaction: 1.0,
        verification_accepted: true,
      },
    },
    provenance: {
      activation_file: 'stage16_qwen15b_activations_20260519.npz',
      activation_sha256: 'ccb79afe5a3215f0f6aac828c574a0d14cf8115ab769489ea4269c70ce43fe8e',
      code_commit: '2c72e37a60efe0e9ad42e1093cabe05342472207',
      fixture_sha256:
        '3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250',
      source_reports: [
        'stage19b_cross_arch_foundation_verification_stack_20260519.json',
        'stage20b_generation_readiness_packets_20260519.json',
      ],
      source_stage: 'Stage 16',
    },
    verification: {
      accepted: true,
      confidence_tier: 'high',
      mode: 'BALANCED',
      mode_profile: {},
      suppression_reasons: [],
    },
  };
}

function suppressPacket(): EvidencePacket {
  const base = allowPacket();
  return {
    ...base,
    trace_id: 'stage21a_suppress_olmo1b_054',
    export_label: 'suppress: factor-conflicted OLMo row in BALANCED',
    diagnostics: {
      ...base.diagnostics,
      blindspot_flags: ['factor_conflicted'],
    },
    generation_readiness: {
      ...base.generation_readiness,
      generation_readiness: 'suppress',
      recommended_mode: 'HIGH_PRECISION',
      reasons: ['verification_stack_rejected', 'verification:factor_conflicted'],
      risk_score: 0.9,
      evidence: {
        ...base.generation_readiness.evidence,
        verification_accepted: false,
      },
    },
  };
}

// ── Fetch mocking helpers ──────────────────────────────────────────────────

function mockJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockTextResponse(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: { 'Content-Type': 'text/markdown' },
  });
}

/** Build a fetch mock that resolves the packet URL with a deferrable promise.  */
function deferredFetch(): {
  fetchImpl: ReturnType<typeof vi.fn>;
  resolve: (response: Response) => void;
  reject: (error: unknown) => void;
} {
  let resolve!: (response: Response) => void;
  let reject!: (error: unknown) => void;
  const pending = new Promise<Response>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  const fetchImpl = vi.fn(async () => pending);
  return { fetchImpl, resolve, reject };
}

// ── URL.createObjectURL / anchor.click shim for jsdom ──────────────────────

let originalCreateObjectURL: typeof URL.createObjectURL;
let originalRevokeObjectURL: typeof URL.revokeObjectURL;

beforeEach(() => {
  originalCreateObjectURL = URL.createObjectURL;
  originalRevokeObjectURL = URL.revokeObjectURL;
  URL.createObjectURL = vi.fn(() => 'blob:mock-url') as typeof URL.createObjectURL;
  URL.revokeObjectURL = vi.fn() as typeof URL.revokeObjectURL;
});

afterEach(() => {
  URL.createObjectURL = originalCreateObjectURL;
  URL.revokeObjectURL = originalRevokeObjectURL;
  vi.restoreAllMocks();
});

// ── 1. Renders all 7 tabs in correct order ─────────────────────────────────

describe('EvidencePacketDrawer — tab layout', () => {
  it('renders all 7 tab buttons in the canonical order', () => {
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={allowPacket()}
      />,
    );
    const tabs = screen.getAllByRole('tab');
    const labels = tabs.map((t) => t.textContent);
    expect(labels).toEqual([
      'Readout',
      'Diagnostics',
      'Controls',
      'Generation Readiness',
      'Provenance',
      'Caveats',
      'Rejected Claims',
    ]);
  });

  it('returns null when traceId is null (drawer closed)', () => {
    const { container } = render(
      <EvidencePacketDrawer traceId={null} onClose={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

// ── 2. Loading state ───────────────────────────────────────────────────────

describe('EvidencePacketDrawer — loading state', () => {
  it('shows a loading indicator while the fetch is pending', async () => {
    const { fetchImpl, resolve } = deferredFetch();
    render(
      <EvidencePacketDrawer
        traceId="pending-1"
        onClose={() => {}}
        fetchImpl={fetchImpl as unknown as typeof fetch}
      />,
    );
    expect(
      screen.getByTestId('evidence-packet-drawer-loading'),
    ).toBeInTheDocument();
    // Resolve so the test cleans up tidily.
    await act(async () => {
      resolve(mockJsonResponse(allowPacket()));
    });
  });
});

// ── 3. 404 → not-found state ───────────────────────────────────────────────

describe('EvidencePacketDrawer — error states', () => {
  it('renders "evidence packet not found" when the API returns 404', async () => {
    const fetchImpl = vi.fn(async () =>
      mockJsonResponse({ detail: 'No such packet' }, 404),
    );
    render(
      <EvidencePacketDrawer
        traceId="missing-1"
        onClose={() => {}}
        fetchImpl={fetchImpl as unknown as typeof fetch}
      />,
    );
    const notFound = await screen.findByTestId(
      'evidence-packet-drawer-not-found',
    );
    expect(notFound.textContent).toBe('evidence packet not found');
  });

  it('renders an error panel on non-404 HTTP failures', async () => {
    const fetchImpl = vi.fn(async () =>
      mockJsonResponse({ detail: 'boom' }, 500),
    );
    render(
      <EvidencePacketDrawer
        traceId="boom-1"
        onClose={() => {}}
        fetchImpl={fetchImpl as unknown as typeof fetch}
      />,
    );
    const err = await screen.findByTestId('evidence-packet-drawer-error');
    expect(err.textContent).toContain('500');
  });
});

// ── 4. Per-tab slice rendering ─────────────────────────────────────────────

describe('EvidencePacketDrawer — per-tab rendering', () => {
  it('Readout tab surfaces axis / label / stable_agree / votes', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={allowPacket()}
      />,
    );
    // Readout is the default tab.
    const body = screen.getByTestId('evidence-packet-tab-readout');
    expect(body).toBeInTheDocument();
    expect(body.textContent).toContain('foundation');
    expect(body.textContent).toContain('F1T');
    // Votes & stable-agree lists
    expect(
      screen.getByTestId('evidence-packet-readout-stable-agree').textContent,
    ).toContain('focus_token');
    expect(
      screen.getByTestId('evidence-packet-readout-votes').textContent,
    ).toContain('final_token');

    // Sanity: switching tabs unmounts the readout body (lazy render).
    await user.click(screen.getByTestId('evidence-packet-tab-button-diagnostics'));
    expect(
      screen.queryByTestId('evidence-packet-tab-readout'),
    ).not.toBeInTheDocument();
  });

  it('Diagnostics tab surfaces blindspot flags + RPM satisfaction', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={suppressPacket()}
      />,
    );
    await user.click(
      screen.getByTestId('evidence-packet-tab-button-diagnostics'),
    );
    const body = screen.getByTestId('evidence-packet-tab-diagnostics');
    expect(body.textContent).toContain('factor conflicted');
    expect(body.textContent).toContain('1.000'); // rpm_satisfaction
  });

  it('Controls tab surfaces random null + raw symbol delta', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={allowPacket()}
      />,
    );
    await user.click(screen.getByTestId('evidence-packet-tab-button-controls'));
    const body = screen.getByTestId('evidence-packet-tab-controls');
    expect(body.textContent).toContain('random null controls');
    expect(body.textContent).toContain('-0.0002');
  });

  it('Generation Readiness tab renders the action badge and reasons', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={suppressPacket()}
      />,
    );
    await user.click(
      screen.getByTestId('evidence-packet-tab-button-readiness'),
    );
    const badge = screen.getByTestId('evidence-packet-readiness-badge');
    expect(badge.textContent).toBe('Suppress');
    expect(badge.className).toContain('rose');
    const reasons = screen.getByTestId('evidence-packet-readiness-reasons');
    expect(reasons.textContent).toContain('verification_stack_rejected');
    // VerificationPanel reused for the badge/colors.
    expect(screen.getByTestId('verification-panel')).toBeInTheDocument();
  });

  it('Provenance tab surfaces trace_id, created_at, commit and source reports', async () => {
    const user = userEvent.setup();
    const packet = allowPacket();
    render(
      <EvidencePacketDrawer
        traceId={packet.trace_id}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    await user.click(
      screen.getByTestId('evidence-packet-tab-button-provenance'),
    );
    const body = screen.getByTestId('evidence-packet-tab-provenance');
    expect(body.textContent).toContain(packet.trace_id);
    expect(body.textContent).toContain(packet.created_at);
    expect(body.textContent).toContain(packet.provenance.code_commit);
    const reports = screen.getByTestId(
      'evidence-packet-provenance-source-reports',
    );
    expect(reports.textContent).toContain('stage19b_cross_arch_foundation');
  });

  it('Caveats tab renders the bounded-claim language as a bullet list', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={allowPacket()}
      />,
    );
    await user.click(screen.getByTestId('evidence-packet-tab-button-caveats'));
    const list = screen.getByTestId('evidence-packet-caveats-list');
    expect(list.tagName.toLowerCase()).toBe('ul');
    const items = list.querySelectorAll('li');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('export artifact');
  });

  it('Rejected Claims tab renders the no-license list with warning styling', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={() => {}}
        initialPacket={allowPacket()}
      />,
    );
    await user.click(
      screen.getByTestId('evidence-packet-tab-button-rejected_claims'),
    );
    const list = screen.getByTestId('evidence-packet-rejected-claims-list');
    expect(list.tagName.toLowerCase()).toBe('ul');
    const items = list.querySelectorAll('li');
    expect(items.length).toBe(3);
    // Warning palette = rose
    expect(items[0].className).toContain('rose');
  });
});

// ── 5. Export JSON ─────────────────────────────────────────────────────────

describe('EvidencePacketDrawer — export JSON', () => {
  it('downloads the packet with the trace-id-derived filename', async () => {
    const user = userEvent.setup();
    const packet = allowPacket();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    render(
      <EvidencePacketDrawer
        traceId={packet.trace_id}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    await user.click(screen.getByTestId('evidence-packet-drawer-export-json'));
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    // The created anchor's download attribute is set just before click;
    // capture the most-recent anchor's `download` value.
    const anchor = clickSpy.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.download).toBe(`evidence_packet_${packet.trace_id}.json`);
    clickSpy.mockRestore();
  });

  it('export buttons are disabled while the packet is loading', async () => {
    const { fetchImpl, resolve } = deferredFetch();
    render(
      <EvidencePacketDrawer
        traceId="pending-1"
        onClose={() => {}}
        fetchImpl={fetchImpl as unknown as typeof fetch}
      />,
    );
    expect(
      screen.getByTestId('evidence-packet-drawer-export-json'),
    ).toBeDisabled();
    expect(
      screen.getByTestId('evidence-packet-drawer-export-markdown'),
    ).toBeDisabled();
    await act(async () => {
      resolve(mockJsonResponse(allowPacket()));
    });
  });
});

// ── 6. Export Markdown ─────────────────────────────────────────────────────

describe('EvidencePacketDrawer — export Markdown', () => {
  it('hits the /markdown endpoint and downloads the .md file', async () => {
    const user = userEvent.setup();
    const packet = allowPacket();
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.endsWith('/markdown')) {
        return mockTextResponse('# evidence packet\n');
      }
      return mockJsonResponse(packet);
    });
    render(
      <EvidencePacketDrawer
        traceId={packet.trace_id}
        onClose={() => {}}
        initialPacket={packet}
        fetchImpl={fetchImpl as unknown as typeof fetch}
      />,
    );
    await user.click(
      screen.getByTestId('evidence-packet-drawer-export-markdown'),
    );
    expect(fetchImpl).toHaveBeenCalledWith(
      `/api/harness/evidence/${packet.trace_id}/markdown`,
    );
    const anchor = clickSpy.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.download).toBe(`evidence_packet_${packet.trace_id}.md`);
    clickSpy.mockRestore();
  });
});

// ── 7. VerificationPanel "View full Evidence Packet" button ────────────────

describe('VerificationPanel — Stage 21B hook', () => {
  it('renders the View button when verification carries a trace_id', () => {
    const onOpen = vi.fn();
    render(
      <VerificationPanel
        verification={{
          decision: 'ACCEPT',
          decision_tier: 'high',
          evidence_packet_trace_id: 'stage21a_allow_qwen15b_000',
        }}
        onOpenEvidencePacket={onOpen}
      />,
    );
    expect(
      screen.getByTestId('verification-open-evidence-packet'),
    ).toBeInTheDocument();
  });

  it('clicking the View button fires the onOpenEvidencePacket callback', async () => {
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(
      <VerificationPanel
        verification={{
          decision: 'ACCEPT',
          decision_tier: 'high',
          evidence_packet_trace_id: 'stage21a_allow_qwen15b_000',
        }}
        onOpenEvidencePacket={onOpen}
      />,
    );
    await user.click(screen.getByTestId('verification-open-evidence-packet'));
    expect(onOpen).toHaveBeenCalledWith('stage21a_allow_qwen15b_000');
  });

  it('does NOT render the View button when verification has no trace_id', () => {
    render(
      <VerificationPanel
        verification={{
          decision: 'ACCEPT',
          decision_tier: 'high',
        }}
        onOpenEvidencePacket={() => {}}
      />,
    );
    expect(
      screen.queryByTestId('verification-open-evidence-packet'),
    ).toBeNull();
  });

  it('does NOT render the View button when onOpenEvidencePacket is omitted', () => {
    render(
      <VerificationPanel
        verification={{
          decision: 'ACCEPT',
          decision_tier: 'high',
          evidence_packet_trace_id: 'stage21a_allow_qwen15b_000',
        }}
      />,
    );
    expect(
      screen.queryByTestId('verification-open-evidence-packet'),
    ).toBeNull();
  });
});

// ── 8. Backward compatibility ──────────────────────────────────────────────

describe('VerificationPanel — backward compatibility', () => {
  it('renders nothing when verification is null/undefined', () => {
    const { container } = render(<VerificationPanel verification={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('does not crash when an existing trace fixture has no verification field', () => {
    // Render twice to make sure the absence of the field never throws —
    // mirrors the existing "node without verification" path in the Atlas.
    expect(() => {
      render(<VerificationPanel verification={undefined} />);
      render(<VerificationPanel verification={null} />);
    }).not.toThrow();
  });
});

// ── 9. Close interactions ──────────────────────────────────────────────────

describe('EvidencePacketDrawer — close interactions', () => {
  it('fires onClose when the close button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={onClose}
        initialPacket={allowPacket()}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('fires onClose when the backdrop is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={onClose}
        initialPacket={allowPacket()}
      />,
    );
    await user.click(screen.getByTestId('evidence-packet-drawer-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });

  it('fires onClose on Escape key', () => {
    const onClose = vi.fn();
    render(
      <EvidencePacketDrawer
        traceId="t1"
        onClose={onClose}
        initialPacket={allowPacket()}
      />,
    );
    const event = new KeyboardEvent('keydown', { key: 'Escape' });
    window.dispatchEvent(event);
    expect(onClose).toHaveBeenCalled();
  });
});
