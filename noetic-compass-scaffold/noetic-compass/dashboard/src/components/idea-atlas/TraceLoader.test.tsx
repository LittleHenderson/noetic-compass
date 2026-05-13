/**
 * Tests for TraceLoader — file/drop/URL/demo paths for loading a
 * traceability_v0 trace. Asserts the contract documented in the
 * atlas-v0 Agent B brief:
 *   - Demo button loads valid trace → onTraceLoaded
 *   - File picker with invalid JSON → onError
 *   - File picker with valid schema → onTraceLoaded
 *   - File picker missing required keys → onError
 *   - URL ?trace= parses correctly
 *   - File picker with wrong schema_version → onError
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { TraceLoader, DEMO_TRACE } from './TraceLoader';
import type { AtlasTrace } from '../../lib/trace';

// ── Helpers ─────────────────────────────────────────────────────

function makeValidTraceJson(): string {
  return JSON.stringify(DEMO_TRACE);
}

/**
 * Drive the hidden <input type="file"> by attaching a File to it and
 * firing a synthetic `change` event. RTL's userEvent.upload also works
 * but this is the most portable form across vitest/jsdom versions.
 */
async function selectFile(input: HTMLInputElement, file: File) {
  Object.defineProperty(input, 'files', {
    value: [file],
    configurable: true,
  });
  await act(async () => {
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

beforeEach(() => {
  // Reset URL search params before every test — the URL effect runs on
  // mount, so we need a clean slate.
  window.history.replaceState({}, '', '/');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Demo button ─────────────────────────────────────────────────

describe('TraceLoader — demo button', () => {
  it('fires onTraceLoaded with a valid trace when clicked', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const btn = screen.getByRole('button', { name: /load demo trace/i });
    await act(async () => {
      btn.click();
    });
    expect(onTraceLoaded).toHaveBeenCalledTimes(1);
    const trace = onTraceLoaded.mock.calls[0][0] as AtlasTrace;
    expect(trace.schema_version).toBe('traceability_v0');
    expect(onError).not.toHaveBeenCalled();
  });
});

// ── File picker ─────────────────────────────────────────────────

describe('TraceLoader — file picker', () => {
  it('fires onTraceLoaded for a valid schema', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    const file = new File([makeValidTraceJson()], 'trace.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onTraceLoaded).toHaveBeenCalledTimes(1));
    expect(onError).not.toHaveBeenCalled();
  });

  it('fires onError when the JSON is invalid', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    const file = new File(['{ not valid json'], 'broken.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    const msg = onError.mock.calls[0][0] as string;
    expect(msg.toLowerCase()).toMatch(/parse|json/);
    expect(onTraceLoaded).not.toHaveBeenCalled();
  });

  it('fires onError when required keys are missing', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    // Drop `thought_tree`
    const trimmed: Record<string, unknown> = {
      ...(DEMO_TRACE as unknown as Record<string, unknown>),
    };
    delete trimmed.thought_tree;
    const file = new File([JSON.stringify(trimmed)], 'missing-key.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onError.mock.calls[0][0]).toContain('thought_tree');
    expect(onTraceLoaded).not.toHaveBeenCalled();
  });

  it('fires onError when schema_version is wrong', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    const input = screen.getByTestId('trace-file-input') as HTMLInputElement;
    const bad = { ...DEMO_TRACE, schema_version: 'trace_v0' };
    const file = new File([JSON.stringify(bad)], 'bad-version.json', {
      type: 'application/json',
    });
    await selectFile(input, file);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onError.mock.calls[0][0].toLowerCase()).toContain('schema_version');
    expect(onTraceLoaded).not.toHaveBeenCalled();
  });
});

// ── URL ?trace= param ───────────────────────────────────────────

describe('TraceLoader — URL ?trace= param', () => {
  it('parses a trace from the URL on mount', async () => {
    const encoded = encodeURIComponent(makeValidTraceJson());
    window.history.replaceState({}, '', `/?trace=${encoded}`);
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    await waitFor(() => expect(onTraceLoaded).toHaveBeenCalledTimes(1));
    const trace = onTraceLoaded.mock.calls[0][0] as AtlasTrace;
    expect(trace.schema_version).toBe('traceability_v0');
    expect(onError).not.toHaveBeenCalled();
  });

  it('does nothing when no trace param is set', async () => {
    const onTraceLoaded = vi.fn();
    const onError = vi.fn();
    render(
      <TraceLoader onTraceLoaded={onTraceLoaded} onError={onError} />,
    );
    // Wait a microtask tick — nothing should fire
    await Promise.resolve();
    expect(onTraceLoaded).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
