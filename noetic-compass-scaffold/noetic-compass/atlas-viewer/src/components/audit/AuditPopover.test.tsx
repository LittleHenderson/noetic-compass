import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AuditPopover } from './AuditPopover';

describe('AuditPopover', () => {
  it('shows a modern briefing immediately on hover and hides on leave', async () => {
    render(
      <AuditPopover briefing="Connect the target, then run the audit.">
        <button type="button">Connect</button>
      </AuditPopover>,
    );

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    fireEvent.mouseEnter(screen.getByText('Connect'));

    expect(screen.getByRole('tooltip')).toHaveTextContent('Briefing');
    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Connect the target, then run the audit.',
    );

    fireEvent.mouseLeave(screen.getByText('Connect'));

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('also opens on keyboard focus for reviewers who tab through the UI', () => {
    render(
      <AuditPopover briefing="Verdicts come from the backend, not the UI.">
        <span>Verdict</span>
      </AuditPopover>,
    );

    const trigger = screen.getByText('Verdict').parentElement;
    expect(trigger).not.toBeNull();
    fireEvent.focus(trigger as HTMLElement);

    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Verdicts come from the backend, not the UI.',
    );
  });

  it('portals the briefing onto document.body so a panel can never obscure or clip it', () => {
    // Regression: the briefing used to render position:absolute INSIDE the trigger,
    // so it lived in the trigger's stacking context and was clipped by any
    // overflow:hidden/auto ancestor (the scrollable rails/cards) — it popped up
    // BEHIND the next panel and couldn't be read. The fix renders it through a
    // portal on document.body with position:fixed + a high z-index, escaping every
    // ancestor stacking context and overflow clip.
    render(
      <AuditPopover briefing="Portaled out of any clipping ancestor.">
        <button type="button">Why?</button>
      </AuditPopover>,
    );

    const trigger = screen.getByText('Why?').parentElement as HTMLElement;
    fireEvent.mouseEnter(screen.getByText('Why?'));

    const tip = screen.getByRole('tooltip');
    // The popover is NOT nested inside the trigger (it was portaled out)...
    expect(trigger.contains(tip)).toBe(false);
    // ...it is a descendant of document.body instead...
    expect(document.body.contains(tip)).toBe(true);
    // ...and it is fixed-positioned above every in-app panel (drawer overlay = 70).
    expect(tip.style.position).toBe('fixed');
    expect(tip.style.zIndex).toBe('1000');
  });

  it('flips a right-placed briefing to the other side when there is no room on the right', () => {
    // Regression (Model-connection "?"): a right-placed popover whose trigger sits in a
    // right-side card has no room to its right, so it used to be clamped clear across
    // the screen and read as "far away." It must instead FLIP to the left of the
    // trigger — anchored by its right edge — so it stays adjacent.
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 1024,
    });
    render(
      <AuditPopover briefing="Pinned near the right edge." placement="right">
        <span>?</span>
      </AuditPopover>,
    );

    const trigger = screen.getByText('?').parentElement as HTMLElement;
    // Trigger pinned against the right edge: a 300px popover cannot fit to its right.
    trigger.getBoundingClientRect = () =>
      ({
        left: 1000,
        right: 1016,
        top: 120,
        bottom: 136,
        width: 16,
        height: 16,
        x: 1000,
        y: 120,
        toJSON: () => ({}),
      }) as DOMRect;

    fireEvent.mouseEnter(trigger);

    const tip = screen.getByRole('tooltip');
    // Flipped: anchored by the right edge (sits to the LEFT of the "?"), never the left.
    expect(tip.style.right).not.toBe('');
    expect(tip.style.left).toBe('');
  });

  it('keeps an inline trigger hugging its content so the popover anchors to the glyph', () => {
    // Regression (Model-connection "?"): in a grid/flex parent the inline trigger was
    // stretched to the full cell width (a 22px "?" inside a 768px wrapper), so a
    // right-placed popover anchored off the wrapper's far edge, ~750px from the glyph.
    // The trigger must shrink-wrap (fit-content + start self-alignment) so its box — and
    // thus the popover anchor — stays tight around the visible glyph.
    const { rerender } = render(
      <AuditPopover briefing="x">
        <span>?</span>
      </AuditPopover>,
    );
    const inlineTrigger = screen.getByText('?').parentElement as HTMLElement;
    expect(inlineTrigger.style.width).toBe('fit-content');
    expect(inlineTrigger.style.alignSelf).toBe('flex-start');
    expect(inlineTrigger.style.justifySelf).toBe('start');

    // A block trigger (detail tiles) still fills its row as intended.
    rerender(
      <AuditPopover briefing="x" block>
        <span>block child</span>
      </AuditPopover>,
    );
    const blockTrigger = screen.getByText('block child').parentElement as HTMLElement;
    expect(blockTrigger.style.width).toBe('100%');
  });
});
