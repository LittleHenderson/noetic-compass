import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

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

  it('shows the public-guide-only honesty line', () => {
    render(<GuideChatWidget />);
    openPanel();
    const honesty = screen.getAllByText(GUIDE_HONESTY_LINE);
    expect(honesty.length).toBeGreaterThanOrEqual(1);
    expect(honesty[0]).toHaveTextContent(/only from the public cas harness guide/i);
  });

  it('sends a question and renders the answer with source chips', async () => {
    askExplainerMock.mockResolvedValue({
      answer: 'Start by choosing a model target, then run the audit.',
      sources: ['docs/explainer/cas_harness_public_guide.md'],
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

    expect(screen.getByText('How do I run an audit?')).toBeInTheDocument();
    expect(
      await screen.findByText(/start by choosing a model target/i),
    ).toBeInTheDocument();

    const chip = await screen.findByTestId('guide-chat-source');
    expect(chip).toHaveTextContent(
      'Source: docs/explainer/cas_harness_public_guide.md',
    );
  });

  it('sends on Enter and keeps Shift+Enter as a newline', async () => {
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
    await user.type(input, 'line one{Shift>}{Enter}{/Shift}line two');
    expect(askExplainerMock).not.toHaveBeenCalled();
    expect(input.value).toContain('\n');

    await user.type(input, '{Enter}');
    await waitFor(() => {
      expect(askExplainerMock).toHaveBeenCalledTimes(1);
    });
  });

  it('renders an error bubble when askExplainer rejects', async () => {
    askExplainerMock.mockRejectedValue(new Error('Explainer request failed (503)'));

    const user = userEvent.setup();
    render(<GuideChatWidget />);
    openPanel();

    await user.type(screen.getByTestId('guide-chat-input'), 'anything');
    await user.click(screen.getByTestId('guide-chat-send'));

    expect(
      await screen.findByText(/the guide is unavailable right now/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/explainer request failed \(503\)/i)).toBeInTheDocument();
    expect(screen.getByTestId('guide-chat-panel')).toBeInTheDocument();
  });

  it('closes the panel by button and Escape', async () => {
    render(<GuideChatWidget />);
    openPanel();
    expect(screen.getByTestId('guide-chat-panel')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('guide-chat-close'));
    await waitFor(() => {
      expect(screen.queryByTestId('guide-chat-panel')).not.toBeInTheDocument();
    });

    openPanel();
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByTestId('guide-chat-panel')).not.toBeInTheDocument();
    });
  });
});
