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
});
