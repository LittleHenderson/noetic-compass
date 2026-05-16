import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { EvidencePacket } from './EvidencePacket';
import {
  type EvidencePacket as EvidencePacketData,
  type EvidenceClaimLevel,
  type EvidenceClaimSupport,
} from '../../lib/evidence_packet';
import { setToken, clearToken } from '../../api/auth';

function makeJwt(payload: Record<string, unknown>): string {
  const encoded = btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
  return `header.${encoded}.sig`;
}

function freshToken(): string {
  return makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
}

function fixturePacket(overrides: Partial<EvidencePacketData> = {}): EvidencePacketData {
  return {
    schema_version: 'evidence_packet.v1',
    trace_id: 'trace-test-1',
    generated_at: '2026-05-15T12:00:00Z',
    input: { text: 'why is the sky blue?', user_id: 'u-1', session_id: 's-1' },
    cas_expression: {
      text: '^2^C × ^5^C',
      compiler_valid: true,
      grammar_category: 'compound',
    },
    output: { text: 'a thoughtful reply', n_tokens: 14, max_new_tokens: 96 },
    copy_slot_trace: [
      {
        role: 'noetic',
        name: '^2',
        copied: true,
        source_token_index: 3,
        target_token_index: 12,
        claim_level: 'source_copy_evidence',
      },
      {
        role: 'identifier',
        name: 'foo',
        copied: false,
        claim_level: 'derived_trace',
      },
    ],
    provenance: {
      model_checkpoint_id: 'ckpt_test_42',
      checkpoint_label: 'v1-step42',
      code_commit_sha: 'abc12345' + 'f'.repeat(32),
      code_commit_summary: 'feat: add evidence packet',
      run_command: 'python train.py --foo bar',
      config_snapshot: { lr: 0.001, batch_size: 128 },
    },
    hashes: {
      weights_sha: 'b'.repeat(64),
      tokenizer_hash: 'c'.repeat(64),
      english_bpe_hash: 'd'.repeat(64),
      corpus_sha256: 'e'.repeat(64),
      on_disk_paths: {
        weights_path: '/srv/ckpts/v1_step42.pt',
        tokenizer_path: '/srv/tok/v1c.json',
        corpus_path: '/srv/data/corpus.jsonl',
      },
    },
    claim_levels: [
      {
        claim: 'CAS expression compiles cleanly',
        level: 'cas_hard_trace',
        support_status: 'supported',
        support_rationale: 'The compiler accepted the expression.',
        rationale: 'Direct call to api/notation/compiler.py.',
      },
      {
        claim: 'Identifier "foo" copied input → output',
        level: 'source_copy_evidence',
        rationale: 'Pointer evidence at tokens 3 → 12.',
      },
      {
        claim: 'Domain marginal derived from Δ°₃₉ readout',
        level: 'derived_trace',
        rationale: 'Marginalization over noetic axis.',
      },
      {
        claim: 'Attention head 4 attends to user_id',
        level: 'neural_attribution_estimate',
        rationale: 'Probe over RandomBatch sample (estimate).',
      },
    ],
    caveats: ['Mode 7 attribution is an estimate, not a proof.'],
    ...overrides,
  };
}

// ── MSW for the loading/error/retry tests ───────────────────────────────────

const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  clearToken();
});
afterAll(() => server.close());

// ── Mount-with-initialPacket tests ──────────────────────────────────────────

describe('EvidencePacket — mount with initialPacket', () => {
  it('renders nothing when open=false', () => {
    const { container } = render(
      <EvidencePacket
        traceId="t1"
        open={false}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders all 7 section headers when open=true', () => {
    render(
      <EvidencePacket
        traceId="t1"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(
      screen.getByRole('heading', { name: 'Input', level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'CAS expression', level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Output', level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Copy / slot trace', level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Provenance', level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Hashes', level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Evidence type & claim support', level: 3 }),
    ).toBeInTheDocument();
  });

  it('renders headline blockquote prominently', () => {
    render(
      <EvidencePacket
        traceId="t1"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    const bq = screen.getByText(/CAS does not just show an answer/i);
    expect(bq.tagName.toLowerCase()).toBe('blockquote');
    expect(bq.textContent).toContain('inspectable object');
  });

  it('renders trace ID', () => {
    render(
      <EvidencePacket
        traceId="trace-test-1"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(
      screen.getByLabelText('Copy trace id'),
    ).toHaveTextContent('trace-test-1');
  });
});

// ── Close interactions ──────────────────────────────────────────────────────

describe('EvidencePacket — close interactions', () => {
  it('calls onClose when the Close buttons are clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t1"
        open={true}
        onClose={onClose}
        initialPacket={fixturePacket()}
      />,
    );
    // There are two close affordances: the header X (aria-label="Close")
    // and the footer "Close" text button. Both should call onClose.
    const closes = screen.getAllByRole('button', { name: 'Close' });
    expect(closes.length).toBeGreaterThanOrEqual(2);
    await user.click(closes[0]);
    expect(onClose).toHaveBeenCalled();
    onClose.mockClear();
    await user.click(closes[1]);
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape key', () => {
    const onClose = vi.fn();
    render(
      <EvidencePacket
        traceId="t1"
        open={true}
        onClose={onClose}
        initialPacket={fixturePacket()}
      />,
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when the backdrop is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t1"
        open={true}
        onClose={onClose}
        initialPacket={fixturePacket()}
      />,
    );
    await user.click(screen.getByTestId('evidence-packet-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });

  it('does NOT call onClose when the drawer body is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t1"
        open={true}
        onClose={onClose}
        initialPacket={fixturePacket()}
      />,
    );
    await user.click(screen.getByRole('heading', { name: 'Input' }));
    expect(onClose).not.toHaveBeenCalled();
  });
});

// ── Export JSON ─────────────────────────────────────────────────────────────

describe('EvidencePacket — export JSON', () => {
  let originalCreateObjectURL: typeof URL.createObjectURL;
  let originalRevokeObjectURL: typeof URL.revokeObjectURL;

  beforeEach(() => {
    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    // jsdom doesn't implement these by default.
    URL.createObjectURL = vi.fn(() => 'blob:mock-url') as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn() as typeof URL.revokeObjectURL;
  });
  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it('triggers a download when Export JSON is clicked', async () => {
    const user = userEvent.setup();
    const packet = fixturePacket();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    render(
      <EvidencePacket
        traceId={packet.trace_id}
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Export JSON' }));
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});

// ── Claim-level badges ──────────────────────────────────────────────────────

describe('EvidencePacket — claim-level badges', () => {
  it.each<EvidenceClaimLevel>([
    'cas_hard_trace',
    'source_copy_evidence',
    'derived_trace',
    'neural_attribution_estimate',
  ])('renders %s badge with label and color class', (level) => {
    const packet = fixturePacket();
    render(
      <EvidencePacket
        traceId={packet.trace_id}
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    const badges = screen.getAllByTestId(`claim-badge-${level}`);
    expect(badges.length).toBeGreaterThan(0);
    const expectedLabel = {
      cas_hard_trace: 'CAS hard trace',
      source_copy_evidence: 'Source copy evidence',
      derived_trace: 'Derived trace',
      neural_attribution_estimate: 'Neural attribution (estimate)',
    }[level];
    expect(badges[0].textContent).toContain(expectedLabel);
    const colorMap: Record<EvidenceClaimLevel, string> = {
      cas_hard_trace: 'emerald-400/30',
      source_copy_evidence: 'emerald-400/25',
      derived_trace: 'sky-400/30',
      neural_attribution_estimate: 'amber-400/30',
    };
    expect(badges[0].className).toContain(colorMap[level]);
  });
});

// ── Compiler valid / invalid states ─────────────────────────────────────────

describe('EvidencePacket — CAS expression states', () => {
  it('shows green "Compiler valid" when compiler_valid=true', () => {
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(screen.getByTestId('cas-compiler-valid')).toBeInTheDocument();
    expect(screen.queryByTestId('cas-compiler-invalid')).toBeNull();
  });

  it('shows red error badge when compiler_valid=false', () => {
    const packet = fixturePacket({
      cas_expression: {
        text: '^99^?',
        compiler_valid: false,
        compiler_error: 'unknown noetic',
      },
    });
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    const errBadge = screen.getByTestId('cas-compiler-invalid');
    expect(errBadge).toBeInTheDocument();
    expect(errBadge.textContent).toContain('unknown noetic');
    expect(screen.queryByTestId('cas-compiler-valid')).toBeNull();
  });

  it('shows empty-state copy when cas_expression is absent', () => {
    const packet = fixturePacket({ cas_expression: undefined });
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    expect(
      screen.getByText(/did not produce a CAS expression/i),
    ).toBeInTheDocument();
  });
});

// ── Empty states + caveats ──────────────────────────────────────────────────

describe('EvidencePacket — empty states + caveats', () => {
  it('shows empty-state when copy_slot_trace is missing', () => {
    const packet = fixturePacket({ copy_slot_trace: undefined });
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    expect(
      screen.getByText(/No copy slot trace recorded/i),
    ).toBeInTheDocument();
  });

  it('renders caveats panel when caveats are present', () => {
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    const caveats = screen.getByTestId('evidence-packet-caveats');
    expect(caveats).toBeInTheDocument();
    expect(caveats.textContent).toContain('estimate, not a proof');
  });

  it('does not render caveats panel when caveats are absent', () => {
    const packet = fixturePacket({ caveats: undefined });
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    expect(screen.queryByTestId('evidence-packet-caveats')).toBeNull();
  });
});

// ── Reviewer playbook toggle ────────────────────────────────────────────────

describe('EvidencePacket — reviewer playbook', () => {
  it('reviewer playbook is hidden by default and toggles open', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(screen.queryByTestId('evidence-packet-playbook')).toBeNull();
    await user.click(screen.getByRole('button', { name: /how to audit this/i }));
    expect(screen.getByTestId('evidence-packet-playbook')).toBeInTheDocument();
    expect(
      screen.getByTestId('evidence-packet-playbook').textContent,
    ).toMatch(/Copy the trace ID/i);
  });
});

// ── Verify Hashes flow ──────────────────────────────────────────────────────

describe('EvidencePacket — verify hashes', () => {
  it('renders a success banner when verify returns all_match', async () => {
    setToken(freshToken());
    server.use(
      http.post('/api/evidence/t/verify', () =>
        HttpResponse.json({
          trace_id: 't',
          verified_at: '2026-05-15T12:05:00Z',
          checks: [
            {
              artifact: 'Weights',
              expected: 'b'.repeat(64),
              actual: 'b'.repeat(64),
              match: true,
            },
            {
              artifact: 'Tokenizer',
              expected: 'c'.repeat(64),
              actual: 'c'.repeat(64),
              match: true,
            },
          ],
          overall: 'all_match',
        }),
      ),
    );
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket({ trace_id: 't' })}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Verify Hashes' }));
    const banner = await screen.findByTestId('evidence-packet-verify-banner');
    expect(banner.textContent).toContain('All artifact hashes verified.');
  });

  it('renders a mismatch banner when verify returns partial_mismatch', async () => {
    setToken(freshToken());
    server.use(
      http.post('/api/evidence/t/verify', () =>
        HttpResponse.json({
          trace_id: 't',
          verified_at: '2026-05-15T12:05:00Z',
          checks: [
            {
              artifact: 'Weights',
              expected: 'b'.repeat(64),
              actual: 'z'.repeat(64),
              match: false,
              notes: 'changed since this trace',
            },
            {
              artifact: 'Tokenizer',
              expected: 'c'.repeat(64),
              actual: 'c'.repeat(64),
              match: true,
            },
          ],
          overall: 'partial_mismatch',
        }),
      ),
    );
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket({ trace_id: 't' })}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Verify Hashes' }));
    const banner = await screen.findByTestId('evidence-packet-verify-banner');
    expect(banner.textContent).toContain('Mismatch detected');
    expect(banner.textContent).toContain('1 of 2');
  });
});

// ── Fetch-on-mount path ────────────────────────────────────────────────────

describe('EvidencePacket — fetch on mount when no initialPacket', () => {
  it('fetches the packet from the API and renders it', async () => {
    setToken(freshToken());
    const packet = fixturePacket({ trace_id: 'fetched-1' });
    server.use(
      http.get('/api/evidence/fetched-1', () => HttpResponse.json(packet)),
    );
    render(
      <EvidencePacket traceId="fetched-1" open={true} onClose={() => {}} />,
    );
    // Output text should appear after the fetch resolves.
    expect(
      await screen.findByText('a thoughtful reply'),
    ).toBeInTheDocument();
  });

  it('renders an error panel + Retry when the API returns 404', async () => {
    setToken(freshToken());
    server.use(
      http.get('/api/evidence/missing', () =>
        HttpResponse.json({ detail: 'No such trace' }, { status: 404 }),
      ),
    );
    render(
      <EvidencePacket traceId="missing" open={true} onClose={() => {}} />,
    );
    const errPanel = await screen.findByTestId('evidence-packet-error');
    expect(errPanel.textContent).toContain('No such trace');
    expect(
      screen.getByRole('button', { name: 'Retry' }),
    ).toBeInTheDocument();
  });

  it('Retry button refetches the packet', async () => {
    setToken(freshToken());
    let calls = 0;
    server.use(
      http.get('/api/evidence/retry-me', () => {
        calls += 1;
        if (calls === 1) {
          return HttpResponse.json(
            { detail: 'transient' },
            { status: 500 },
          );
        }
        return HttpResponse.json(fixturePacket({ trace_id: 'retry-me' }));
      }),
    );
    const user = userEvent.setup();
    render(
      <EvidencePacket traceId="retry-me" open={true} onClose={() => {}} />,
    );
    await screen.findByTestId('evidence-packet-error');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('a thoughtful reply')).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});

// ── Provenance config snapshot toggle ───────────────────────────────────────

describe('EvidencePacket — provenance config snapshot', () => {
  it('config snapshot is collapsed by default and toggles open', async () => {
    const user = userEvent.setup();
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(screen.queryByText('"lr": 0.001')).toBeNull();
    await user.click(screen.getByRole('button', { name: /Config snapshot/i }));
    expect(screen.getByText(/"lr": 0.001/)).toBeInTheDocument();
  });
});

// Silence "act" warning noise from a couple of state updates that happen
// outside test interactions in some flows.
beforeAll(() => {
  const origError = console.error;
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === 'string' && args[0].includes('not wrapped in act')) return;
    origError(...args);
  };
});

// Keep act import alive for tooling that complains otherwise.
void act;

describe('EvidencePacket - claim support separation', () => {
  it.each<[EvidenceClaimSupport, string]>([
    ['supported', 'Support: yes'],
    ['partially_supported', 'Support: partial'],
    ['unsupported', 'Support: no'],
    ['contradicted', 'Contradicted'],
    ['not_applicable', 'Support: not applicable'],
    ['unknown', 'Support: unknown'],
  ])('renders %s as a separate support badge', (status, expectedLabel) => {
    const packet = fixturePacket({
      claim_levels: [
        {
          claim: `support status ${status}`,
          level: 'derived_trace',
          support_status: status,
          support_rationale: 'Support status test row.',
          rationale: 'Evidence type test row.',
        },
      ],
    });
    render(
      <EvidencePacket
        traceId={packet.trace_id}
        open={true}
        onClose={() => {}}
        initialPacket={packet}
      />,
    );
    expect(screen.getByTestId(`claim-support-${status}`)).toHaveTextContent(
      expectedLabel,
    );
  });

  it('explains that trace evidence and claim support are separate', () => {
    render(
      <EvidencePacket
        traceId="t"
        open={true}
        onClose={() => {}}
        initialPacket={fixturePacket()}
      />,
    );
    expect(
      screen.getByTestId('evidence-confidence-separation-note'),
    ).toHaveTextContent(/CAS may clearly track that a claim was made/i);
    expect(screen.getByText('Evidence type')).toBeInTheDocument();
  });
});
