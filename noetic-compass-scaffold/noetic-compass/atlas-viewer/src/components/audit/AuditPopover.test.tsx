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
});
