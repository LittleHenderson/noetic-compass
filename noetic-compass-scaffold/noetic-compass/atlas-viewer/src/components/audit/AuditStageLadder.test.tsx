import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { AuditStageLadder } from './AuditStageLadder';

describe('AuditStageLadder', () => {
  it('renders the six public nodes for a draft run with Queued active', () => {
    render(<AuditStageLadder status="draft" />);

    const ladder = screen.getByLabelText('Audit stage ladder');
    ['Queued', 'Validating', 'Running', 'Verifying', 'Anchoring', 'Completed'].forEach(
      (label) => {
        expect(within(ladder).getByText(label)).toBeInTheDocument();
      },
    );
    // Queued (draft) is the active step.
    const queued = within(ladder).getByText('Queued').closest('li');
    expect(queued).toHaveAttribute('data-state', 'active');
  });

  it('marks the running node active and earlier nodes done', () => {
    render(<AuditStageLadder status="running" />);
    const ladder = screen.getByLabelText('Audit stage ladder');

    expect(within(ladder).getByText('Running').closest('li')).toHaveAttribute(
      'data-state',
      'active',
    );
    expect(within(ladder).getByText('Validating').closest('li')).toHaveAttribute(
      'data-state',
      'done',
    );
  });

  it('pins an amber "Runner not connected" interrupt on Running for runner_pending', () => {
    render(<AuditStageLadder status="runner_pending" />);
    const ladder = screen.getByLabelText('Audit stage ladder');

    const running = within(ladder).getByText('Running').closest('li');
    expect(running).toHaveAttribute('data-state', 'review');
    expect(screen.getByText('Runner not connected')).toBeInTheDocument();
    // The final node must NOT read as a calm completed teal terminal.
    expect(within(ladder).getByText('Completed').closest('li')).toHaveAttribute(
      'data-state',
      'pending',
    );
  });

  it('shows the "Needs human review" terminal (amber) for a FLAG verdict', () => {
    render(<AuditStageLadder status="complete" verdict="FLAG_FOR_HUMAN_REVIEW" />);
    const ladder = screen.getByLabelText('Audit stage ladder');

    expect(within(ladder).getByText('Needs human review')).toBeInTheDocument();
    expect(within(ladder).queryByText('Completed')).not.toBeInTheDocument();
    expect(
      within(ladder).getByText('Needs human review').closest('li'),
    ).toHaveAttribute('data-state', 'review');
  });

  it('renders a clean teal Completed terminal only when complete AND a verdict is present', () => {
    render(<AuditStageLadder status="complete" verdict="ACCEPT" />);
    const ladder = screen.getByLabelText('Audit stage ladder');

    expect(within(ladder).getByText('Completed').closest('li')).toHaveAttribute(
      'data-state',
      'done',
    );
  });

  it('does not show a teal Completed when complete but no verdict is attached', () => {
    render(<AuditStageLadder status="complete" verdict={null} />);
    const ladder = screen.getByLabelText('Audit stage ladder');

    expect(within(ladder).getByText('Completed').closest('li')).toHaveAttribute(
      'data-state',
      'pending',
    );
  });

  it('turns the reached node rose and stops on a failed run', () => {
    render(<AuditStageLadder status="failed" />);
    const ladder = screen.getByLabelText('Audit stage ladder');

    expect(within(ladder).getByText('Running').closest('li')).toHaveAttribute(
      'data-state',
      'failed',
    );
    expect(within(ladder).getByText('Verifying').closest('li')).toHaveAttribute(
      'data-state',
      'pending',
    );
  });
});
