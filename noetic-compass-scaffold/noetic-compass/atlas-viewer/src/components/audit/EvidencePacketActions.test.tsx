import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { EvidencePacketActions } from './EvidencePacketActions';

describe('EvidencePacketActions', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('keeps packet actions disabled until a trace_id exists', () => {
    render(<EvidencePacketActions traceId={null} authToken="test-token" />);

    expect(
      screen.getByRole('button', { name: 'Download Evidence Packet' }),
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Copy Evidence Packet review link' }),
    ).toBeDisabled();
  });

  it('keeps authenticated download disabled when no Bearer token is available', () => {
    render(<EvidencePacketActions traceId="trace-123" />);

    expect(
      screen.getByRole('button', { name: 'Download Evidence Packet' }),
    ).toBeDisabled();
    expect(screen.getByRole('note')).toHaveTextContent('protected API token');
    expect(
      screen.getByRole('button', { name: 'Copy Evidence Packet review link' }),
    ).toBeEnabled();
  });

  it('fetches with the current Bearer token and starts exactly one authenticated download', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ trace_id: 'trace with spaces' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const createObjectURL = vi.fn().mockReturnValue('blob:packet-123');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    const open = vi.spyOn(window, 'open');
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    render(
      <EvidencePacketActions
        traceId="trace with spaces"
        authToken="current-token"
        fetchImpl={fetchImpl}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Download Evidence Packet' }));

    expect(await screen.findByRole('status')).toHaveTextContent('download started');
    expect(fetchImpl).toHaveBeenCalledWith('/api/evidence/trace%20with%20spaces', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        Authorization: 'Bearer current-token',
      },
    });
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(open).not.toHaveBeenCalled();
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).not.toHaveBeenCalled();
  });

  it('copies a real Audit Console review deep link, never the POST-only API URL', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    render(<EvidencePacketActions traceId="trace with spaces" />);

    fireEvent.click(screen.getByRole('button', { name: 'Copy Evidence Packet review link' }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        'http://localhost:3000/audit-console?trace=trace%20with%20spaces#evidence-packet-verification',
      );
    });
    expect(writeText.mock.calls[0][0]).not.toContain('/api/evidence/');
    expect(screen.getByRole('status')).toHaveTextContent('review link copied');
  });

  it('resets action status when the trace changes', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    const { rerender } = render(<EvidencePacketActions traceId="trace-1" />);

    fireEvent.click(screen.getByRole('button', { name: 'Copy Evidence Packet review link' }));
    expect(await screen.findByRole('status')).toHaveTextContent('review link copied');

    rerender(<EvidencePacketActions traceId="trace-2" />);
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
  });

  it('reports clipboard unavailability without claiming the link was copied', async () => {
    vi.stubGlobal('navigator', {});
    render(<EvidencePacketActions traceId="trace-123" />);

    fireEvent.click(screen.getByRole('button', { name: 'Copy Evidence Packet review link' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'review link could not be copied',
    );
  });

  it('announces copy success even after a completed download', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ trace_id: 'trace-123' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('URL', { createObjectURL: vi.fn().mockReturnValue('blob:packet-123'), revokeObjectURL: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    render(<EvidencePacketActions traceId="trace-123" authToken="token" fetchImpl={fetchImpl} />);

    fireEvent.click(screen.getByRole('button', { name: 'Download Evidence Packet' }));
    expect(await screen.findByText('Evidence Packet download started.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Copy Evidence Packet review link' }));

    expect(await screen.findByText('Evidence Packet review link copied.')).toBeInTheDocument();
    expect(screen.getByText('Evidence Packet download started.')).toBeInTheDocument();
  });
});
