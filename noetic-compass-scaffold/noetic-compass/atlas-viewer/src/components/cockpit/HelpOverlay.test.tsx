import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import HelpOverlay from './HelpOverlay';

describe('HelpOverlay', () => {
  it('shows the CAS Harness method as a step-by-step FAQ entry', () => {
    render(<HelpOverlay open onClose={vi.fn()} />);

    const faq = screen.getByTestId('cas-harness-method-faq');
    expect(faq).toHaveTextContent('FAQ: S7-F28 Balanced Bridge Method');
    expect(faq).toHaveTextContent('S7-F28-BALANCED-BRIDGE');
    expect(faq).toHaveTextContent('Use the original source-defined taxonomy.');
    expect(faq).toHaveTextContent('Capture real hidden states from the open-weight model.');
    expect(faq).toHaveTextContent('LogisticRegression(C=0.1, class_weight="balanced")');
    expect(faq).toHaveTextContent('86.8622% heldout Foundation accuracy');
    expect(faq).toHaveTextContent('+0.596413 with 90/112 positive rows');
    expect(faq).toHaveTextContent('lacunarity was 0.006715');
    expect(faq).toHaveTextContent('not yet the final verdict layer');
  });

  it('explains the TKS40 text-baseline guard without promoting the claim', () => {
    render(<HelpOverlay open onClose={vi.fn()} />);

    const faq = screen.getByTestId('tks40-text-baseline-faq');
    expect(faq).toHaveTextContent('FAQ: TKS40 Text Baseline Guard');
    expect(faq).toHaveTextContent('hidden states read the compact-gloss TKS40 axis at 97.50%');
    expect(faq).toHaveTextContent('text-only classifier also reached 100.00%');
    expect(faq).toHaveTextContent('original Stage 9 40E fixture');
    expect(faq).toHaveTextContent('49.24%');
    expect(faq).toHaveTextContent('pre-registered text-baseline ceiling of 60% or lower');
  });

  it('keeps the FAQ behind the help overlay and closes cleanly', () => {
    const closed = render(<HelpOverlay open={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId('cas-harness-method-faq')).not.toBeInTheDocument();
    closed.unmount();

    const onClose = vi.fn();
    render(<HelpOverlay open onClose={onClose} />);
    fireEvent.click(screen.getByTestId('help-overlay-close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
