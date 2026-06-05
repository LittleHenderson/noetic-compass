import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock the explainer client so the widget never makes a real network/auth call.
vi.mock('../../lib/explainerApi', () => ({
  askExplainer: vi.fn(),
}));

import { askExplainer } from '../../lib/explainerApi';
import { GuideChatWidget, GUIDE_HONESTY_LINE } from './GuideChatWidget';

const askExplainerMock = vi.mocked(askExplainer);

function openPanel() {
  fireEvent.click(screen.getByTestId('guide-chat-launcher'));
}

describe('GuideChatWidget', () => {
  beforeEach(() => {
    askExplainerMock.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the floating launcher and is closed by default', () => {
    render(<GuideChatWidget />);
    expect(screen.getByTestId('guide-chat-launcher')).toBeInTheDocument();
    expect(screen.queryByTestId('guide-chat-panel')).not.toBeInTheDocument();
  });

  it('opens the panel when the launcher is clicked', () => {
    render(<GuideChatWidget />);
    openPanel();
    expect(screen.getByTestId('guide-chat-panel')).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: /cas harness guide/i })).toBeInTheDocument();
  });

  it('shows the honesty line that answers come only from the public guide', () => {
    render(<GuideChatWidget />);
    openPanel();
    // Present in both the header subline and the footer — both must carry it.
    const honesty = screen.getAllByText(GUIDE_HONESTY_LINE);
    expect(honesty.length).toBeGreaterThanOrEqual(1);
    expect(honesty[0]).toHaveTextContent(/only from the public cas harness guide/i);
  });

  it('sends a question, calls askExplainer, and renders the answer and a sources chip', async () => {
    askExplainerMock.mockResolvedValue({
      answer: 'Start by choosing a model target, then run the audit.',
      sources: ['docs/explainer/getting_started.md'],
      used_gemini: true,
      model: 'gemini-2.5-flash',
      safety_mode: 'public_kb_only',
    });

    const user = userEvent.setup();
    render(<GuideChatWidget />);
    openPanel();

    await user.type(screen.getByTestId('guide-chat-input'), 'How do I run an audit?');
    await user.click(screen.getByTestId('guide-chat-send'));

    await waitFor(() => {
      expect(askExplainerMock).toHaveBeenCalledTimes(1);
    });
    expect(askExplainerMock).toHaveBeenCalledWith('How do I run an audit?');

    // The user message and the assistant answer both render.
    expect(screen.getByText('How do I run an audit?')).toBeInTheDocument();
    expect(
      await screen.findByText(/start by choosing a model target/i),
    ).toBeInTheDocument();

    // The returned source renders as a labelled chip (honesty: show provenance).
    const chip = await screen.findByTestId('guide-chat-source');
    expect(chip).toHaveTextContent('Source: docs/explainer/getting_started.md');
  });

  it('sends on Enter and inserts a newline on Shift+Enter', async () => {
    askExplainerMock.mockResolvedValue({
      answer: 'Answer body.',
      sources: [],
      used_gemini: true,
      model: 'gemini-2.5-flash',
      safety_mode: 'public_kb_only',
    });

    const user = userEvent.setup();
    render(<GuideChatWidget />);
    openPanel();

    const input = screen.getByTestId('guide-chat-input') as HTMLTextAreaElement;
    // Shift+Enter must NOT submit.
    await user.type(input, 'line one{Shift>}{Enter}{/Shift}line two');
    expect(askExplainerMock).not.toHaveBeenCalled();
    expect(input.value).toContain('\n');

    // A bare Enter submits.
    await user.type(input, '{Enter}');
    await waitFor(() => {
      expect(askExplainerMock).toHaveBeenCalledTimes(1);
    });
  });

  it('renders a calm error bubble when askExplainer rejects, without throwing', async () => {
    askExplainerMock.mockRejectedValue(new Error('Explainer request failed (503)'));

    const user = userEvent.setup();
    render(<GuideChatWidget />);
    openPanel();

    await user.type(screen.getByTestId('guide-chat-input'), 'anything');
    await user.click(screen.getByTestId('guide-chat-send'));

    expect(
      await screen.findByText(/the guide is unavailable right now — try again/i),
    ).toBeInTheDocument();
    // The underlying error detail is surfaced (small), not swallowed.
    expect(screen.getByText(/explainer request failed \(503\)/i)).toBeInTheDocument();
    // Panel is still mounted — no crash.
    expect(screen.getByTestId('guide-chat-panel')).toBeInTheDocument();
  });

  it('closes the panel when the ✕ button is clicked', () => {
    render(<GuideChatWidget />);
    openPanel();
    expect(screen.getByTestId('guide-chat-panel')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('guide-chat-close'));
    return waitFor(() => {
      expect(screen.queryByTestId('guide-chat-panel')).not.toBeInTheDocument();
    });
  });

  it('closes the panel when Escape is pressed', () => {
    render(<GuideChatWidget />);
    openPanel();
    expect(screen.getByTestId('guide-chat-panel')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    return waitFor(() => {
      expect(screen.queryByTestId('guide-chat-panel')).not.toBeInTheDocument();
    });
  });
});
