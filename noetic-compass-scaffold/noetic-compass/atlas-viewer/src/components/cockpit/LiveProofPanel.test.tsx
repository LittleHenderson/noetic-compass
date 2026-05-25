import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import LiveProofPanel from './LiveProofPanel';

const verifiedProof = {
  verdict: 'REAL_PYTHIA_WEIGHTS_LOADED',
  httpStatus: 200,
  isRealModel: true,
  modelLoaded: true,
  fakeRuntimeEnv: false,
  manifestIsRealModel: true,
  loadError: null,
  checkedAt: '2026-05-25T08:30:12.000Z',
  workerVersion: 'atlas-live-worker-m2',
};

describe('LiveProofPanel', () => {
  it('shows a direct verified real-weights proof when every proof condition passes', () => {
    render(
      <LiveProofPanel
        connectionState="streaming"
        modelId="EleutherAI/pythia-160m"
        proof={verifiedProof}
        manifest={{ isRealModel: true, modelId: 'EleutherAI/pythia-160m' }}
        stream={{
          streamTokenIssued: true,
          tokenCount: 8,
          currentTokenIndex: 4,
          eventCount: 14,
          lastEventAt: '2026-05-25T08:31:00.000Z',
        }}
      />,
    );

    expect(screen.getByTestId('live-proof-panel')).toHaveAttribute(
      'data-verified',
      'true',
    );
    expect(screen.getByTestId('live-proof-status').textContent).toBe(
      'VERIFIED REAL WEIGHTS',
    );
    expect(screen.getByTestId('live-proof-topline').textContent).toBe(
      'Real Pythia weights verified.',
    );
    expect(screen.getByTestId('live-proof-actual-weights').textContent).toContain(
      'proven by /atlas/live/health/realmode',
    );
    expect(screen.getByTestId('live-proof-manifest-real').textContent).toBe(
      'Manifest realmanifest is_real_model: yes',
    );
    expect(screen.getByTestId('live-proof-stream-token').textContent).toBe(
      'Stream tokenissued',
    );
    expect(screen.getByTestId('live-proof-token-count').textContent).toContain(
      '5 / 8',
    );
    expect(screen.getByTestId('live-proof-model').textContent).toContain(
      'EleutherAI/pythia-160m',
    );
  });

  it('keeps loading/checking language separate from actual-weights claims', () => {
    const onRefreshProof = vi.fn();
    render(
      <LiveProofPanel
        connectionState="checking"
        modelId="EleutherAI/pythia-160m"
        proof={null}
        stream={{ streamTokenIssued: null, tokenCount: null }}
        onRefreshProof={onRefreshProof}
      />,
    );

    expect(screen.getByTestId('live-proof-panel')).toHaveAttribute(
      'data-verified',
      'false',
    );
    expect(screen.getByTestId('live-proof-status').textContent).toBe(
      'Checking real-weight proof',
    );
    expect(screen.getByTestId('live-proof-topline').textContent).toBe(
      'Real-weight proof is still running. Do not call this actual weights yet.',
    );
    expect(screen.getByTestId('live-proof-actual-weights').textContent).toContain(
      'not proven',
    );
    expect(screen.getByTestId('live-proof-boundary')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('live-proof-refresh'));
    expect(onRefreshProof).toHaveBeenCalledTimes(1);
  });

  it('shows unavailable as not proven with the failure reason surfaced', () => {
    render(
      <LiveProofPanel
        connectionState="unavailable"
        modelId="EleutherAI/pythia-160m"
        proof={{
          verdict: 'WORKER_UNAVAILABLE',
          httpStatus: 503,
          isRealModel: false,
          modelLoaded: false,
          fakeRuntimeEnv: false,
          manifestIsRealModel: null,
          loadError: null,
          checkedAt: '2026-05-25T08:32:00.000Z',
        }}
        stream={{ streamTokenIssued: false, eventCount: 0 }}
        failureReason="Atlas LIVE worker is unavailable."
      />,
    );

    expect(screen.getByTestId('live-proof-status').textContent).toBe(
      'LIVE worker unavailable',
    );
    expect(screen.getByTestId('live-proof-topline').textContent).toBe(
      'Live model is unavailable. Actual weights are not proven.',
    );
    expect(screen.getByTestId('live-proof-stream-token').textContent).toBe(
      'Stream tokennot issued',
    );
    expect(screen.getByTestId('live-proof-failure').textContent).toContain(
      'Atlas LIVE worker is unavailable.',
    );
    expect(screen.queryByTestId('live-proof-boundary')).toBeNull();
  });

  it('shows failed proof and load error without upgrading to verified', () => {
    render(
      <LiveProofPanel
        connectionState="failed"
        proof={{
          verdict: 'LOAD_ERROR',
          httpStatus: 503,
          isRealModel: false,
          modelLoaded: false,
          fakeRuntimeEnv: false,
          manifestIsRealModel: false,
          loadError: 'Pythia weights missing on worker',
          checkedAt: '2026-05-25T08:33:00.000Z',
        }}
        manifest={{ isRealModel: false, modelId: 'EleutherAI/pythia-160m' }}
        stream={{ streamTokenIssued: false, tokenCount: 0, eventCount: 0 }}
        failureReason="Real-weight proof failed."
      />,
    );

    expect(screen.getByTestId('live-proof-panel')).toHaveAttribute(
      'data-verified',
      'false',
    );
    expect(screen.getByTestId('live-proof-status').textContent).toBe(
      'LIVE proof failed',
    );
    expect(screen.getByTestId('live-proof-actual-weights').textContent).toContain(
      'not proven',
    );
    expect(screen.getByTestId('live-proof-load-error').textContent).toContain(
      'Pythia weights missing on worker',
    );
    expect(screen.getByTestId('live-proof-failure').textContent).toContain(
      'Real-weight proof failed.',
    );
  });
});
