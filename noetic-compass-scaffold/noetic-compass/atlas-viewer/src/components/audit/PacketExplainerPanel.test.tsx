import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';

// Mock the explainer client so the panel never makes a real network/auth call.
vi.mock('../../lib/explainerApi', () => ({
  askExplainerForPacket: vi.fn(),
}));

import { askExplainerForPacket, type ExplainPacketResponse } from '../../lib/explainerApi';
import {
  PacketExplainerPanel,
  PACKET_EXPLAINER_DISCLAIMER,
} from './PacketExplainerPanel';
import { EvidenceRail } from '../shell/EvidenceRail';
import { buildDefaultProvenanceChips } from '../../lib/casHarnessAudit';

const askPacketMock = vi.mocked(askExplainerForPacket);

const TRACE_ID = 'stage9-40e-original-baseline-readout-20260527';

// A FLAG packet so we can assert the AI never softens it.
const flagChips = buildDefaultProvenanceChips({
  modelProof: 'verified',
  casReadout: 'present',
  causalProof: { status: 'failed', detail: 'Ablation did not confirm.' },
  controlProof: 'present',
  outputProof: 'present',
  packetProof: 'present',
});

// A well-formed response whose verdict_echo MATCHES the EP verdict, with one
// cited segment, one EMPTY-refs segment (must be hidden), and one investigate
// item.
const goodResponse: ExplainPacketResponse = {
  trace_id: TRACE_ID,
  verdict_echo: 'FLAG_FOR_HUMAN_REVIEW',
  segments: [
    {
      text: 'Your audit returned FLAG_FOR_HUMAN_REVIEW — not a pass; a person must review.',
      refs: ['verdict'],
    },
    {
      // Zero refs -> must NOT render (spec §6 no uncited claims).
      text: 'This uncited sentence must never appear.',
      refs: [],
    },
    {
      text: 'The Causal check came back failed.',
      refs: ['proof_chips.causal_proof.status'],
    },
  ],
  investigate_next: [
    {
      text: 'Reproduce the flagged input and confirm whether the stated reason drove the behavior.',
      refs: ['proof_chips.causal_proof.status'],
    },
  ],
  used_gemini: true,
  model: 'gemini-3.1-pro-preview',
  safety_mode: 'packet_projection_only',
  disclaimer: PACKET_EXPLAINER_DISCLAIMER,
};

// Render the EP view (with the button) AND the floating panel together, exactly
// as AuditAppFrame mounts them, so the window-event open path is exercised.
function renderRailAndPanel(verdict: 'FLAG_FOR_HUMAN_REVIEW' | 'ACCEPT' = 'FLAG_FOR_HUMAN_REVIEW') {
  return render(
    <>
      <EvidenceRail
        verdict={verdict}
        confidence={0.42}
        customerSafe={false}
        chips={flagChips}
        evidencePacketTraceId={TRACE_ID}
      />
      <PacketExplainerPanel />
    </>,
  );
}

describe('PacketExplainerPanel + Explain-this-packet button', () => {
  beforeEach(() => {
    askPacketMock.mockReset();
    window.localStorage.clear();
    // jsdom has no scrollIntoView; ref-chip clicks call it. Stub to a no-op.
    Element.prototype.scrollIntoView = vi.fn();
    // Pre-acknowledge the G4 disclaimer for the default-path tests; the
    // first-use modal has its own dedicated test below.
    window.localStorage.setItem('casPacketExplainerDisclaimerAck', 'true');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the "Explain this packet (plain English)" button on the EP view', () => {
    renderRailAndPanel();
    const button = screen.getByTestId('explain-packet-button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent(/explain this packet \(plain english\)/i);
  });

  it('opens the panel and renders cited segments + investigate-next when clicked', async () => {
    askPacketMock.mockResolvedValue(goodResponse);
    renderRailAndPanel();

    expect(screen.queryByTestId('packet-explainer-panel')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('explain-packet-button'));

    // The panel opens and the client is called with the trace id.
    expect(await screen.findByTestId('packet-explainer-panel')).toBeInTheDocument();
    await waitFor(() => {
      expect(askPacketMock).toHaveBeenCalledWith(TRACE_ID);
    });

    // The cited verdict segment renders.
    expect(
      await screen.findByText(/your audit returned flag_for_human_review/i),
    ).toBeInTheDocument();
    // The investigate-next item renders under its label.
    expect(screen.getByText(/what & why to investigate next/i)).toBeInTheDocument();
    expect(
      screen.getByText(/reproduce the flagged input/i),
    ).toBeInTheDocument();
  });

  it('renders a clickable reference-chip that scrolls to the EP field', async () => {
    askPacketMock.mockResolvedValue(goodResponse);
    renderRailAndPanel();
    fireEvent.click(screen.getByTestId('explain-packet-button'));

    await screen.findByTestId('packet-explainer-panel');

    const chips = await screen.findAllByTestId('packet-explainer-ref-chip');
    // verdict chip + 2x causal_proof.status chips = at least the verdict one.
    const verdictChip = chips.find((c) => c.getAttribute('data-ref') === 'verdict');
    expect(verdictChip).toBeDefined();
    expect(verdictChip).toHaveTextContent('verdict');

    // Clicking the chip resolves the EP-field anchor and scrolls to it.
    fireEvent.click(verdictChip as HTMLElement);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('does NOT render a segment that has empty refs (no uncited claims)', async () => {
    askPacketMock.mockResolvedValue(goodResponse);
    renderRailAndPanel();
    fireEvent.click(screen.getByTestId('explain-packet-button'));

    await screen.findByText(/your audit returned flag_for_human_review/i);
    // The empty-refs sentence must be absent.
    expect(
      screen.queryByText(/this uncited sentence must never appear/i),
    ).not.toBeInTheDocument();

    // Exactly two body segments render (verdict + causal), not three.
    const segments = screen.getAllByTestId('packet-explainer-segment');
    expect(segments).toHaveLength(2);
  });

  it('fails closed when verdict_echo does not match the EP verdict', async () => {
    // The model echoes ACCEPT for a FLAG packet — an inflated reading.
    askPacketMock.mockResolvedValue({
      ...goodResponse,
      verdict_echo: 'ACCEPT',
    });
    renderRailAndPanel('FLAG_FOR_HUMAN_REVIEW');
    fireEvent.click(screen.getByTestId('explain-packet-button'));

    // Fail-closed fallback renders; the AI segments do NOT.
    expect(await screen.findByTestId('packet-explainer-mismatch')).toBeInTheDocument();
    expect(screen.getByText(/ai summary unavailable for this packet/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/your audit returned flag_for_human_review/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('packet-explainer-segment')).not.toBeInTheDocument();
  });

  it('shows the G4 disclaimer in the panel footer', async () => {
    askPacketMock.mockResolvedValue(goodResponse);
    renderRailAndPanel();
    fireEvent.click(screen.getByTestId('explain-packet-button'));

    const footer = await screen.findByTestId('packet-explainer-footer-disclaimer');
    expect(footer).toHaveTextContent(PACKET_EXPLAINER_DISCLAIMER);
    expect(footer).toHaveTextContent(/authoritative record/i);
    expect(footer).toHaveTextContent(/responsible for reading it yourself/i);
  });

  it('blocks behind the first-use disclaimer modal until acknowledged, then loads', async () => {
    // No prior ack for this test.
    window.localStorage.clear();
    askPacketMock.mockResolvedValue(goodResponse);
    renderRailAndPanel();

    fireEvent.click(screen.getByTestId('explain-packet-button'));

    // First-use modal appears; the panel + the API call are gated.
    const modal = await screen.findByTestId('packet-explainer-disclaimer-modal');
    expect(within(modal).getByText(/authoritative record/i)).toBeInTheDocument();
    expect(within(modal).getByText(/go\/no-go decision/i)).toBeInTheDocument();
    expect(askPacketMock).not.toHaveBeenCalled();
    expect(screen.queryByTestId('packet-explainer-panel')).not.toBeInTheDocument();

    // Acknowledge -> modal closes, ack persists, the deferred load runs.
    fireEvent.click(screen.getByTestId('packet-explainer-disclaimer-accept'));
    expect(await screen.findByTestId('packet-explainer-panel')).toBeInTheDocument();
    await waitFor(() => {
      expect(askPacketMock).toHaveBeenCalledWith(TRACE_ID);
    });
    expect(window.localStorage.getItem('casPacketExplainerDisclaimerAck')).toBe('true');
  });
});
