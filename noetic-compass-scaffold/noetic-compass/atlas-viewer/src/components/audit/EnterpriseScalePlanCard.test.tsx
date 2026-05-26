import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { vi } from 'vitest';
import EnterpriseScalePlanCard from './EnterpriseScalePlanCard';
import { getEnterpriseScalePlan } from '../../lib/enterpriseScalePlan';

const hundredBPlan = getEnterpriseScalePlan('100B');

describe('EnterpriseScalePlanCard', () => {
  it('renders the 100B plan text and scaling model', () => {
    render(<EnterpriseScalePlanCard plan={hundredBPlan} />);

    const card = screen.getByTestId('enterprise-scale-plan-card');
    expect(within(card).getByText('100B open-weight plan')).toBeInTheDocument();
    expect(screen.getByTestId('enterprise-plan-worker-count')).toHaveTextContent(
      '16 Probe Workers',
    );
    expect(card).toHaveTextContent('Orchestrator + Probe Workers');
    expect(card).toHaveTextContent('not one harness per 1B params');
    expect(card).toHaveTextContent('Real proof coverage is measured');
  });

  it('renders worker assignments by layer and shard range', () => {
    render(<EnterpriseScalePlanCard plan={hundredBPlan} />);

    const assignment = screen.getByTestId(
      'enterprise-worker-assignment-PW-100-09',
    );
    expect(assignment).toHaveTextContent('PW-100-09');
    expect(assignment).toHaveTextContent('Layers 40-44');
    expect(assignment).toHaveTextContent('Shards S16-S17');
    expect(assignment).toHaveTextContent('Late residual stream localization');
  });

  it('keeps audit claims bounded', () => {
    render(<EnterpriseScalePlanCard plan={hundredBPlan} />);

    const copy = document.body.textContent ?? '';
    expect(copy).not.toMatch(/instant full audit any model/i);
    expect(copy).not.toMatch(/full audit any model/i);
    expect(copy).toMatch(/not a guarantee that every parameter/i);
  });

  it('lets the console choose a different planning size when wired', () => {
    const onSelectSize = vi.fn();
    render(
      <EnterpriseScalePlanCard
        plan={hundredBPlan}
        selectedSize="100B"
        onSelectSize={onSelectSize}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '300B' }));

    expect(onSelectSize).toHaveBeenCalledWith('300B');
  });
});
