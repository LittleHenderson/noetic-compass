/**
 * Vitest coverage for the CAS v7.5 Register axis rendering in the
 * operator radar chart (Clarification 8, rollout track (j)).
 *
 * Register annotations appear only inside the ExplainPanel — the
 * details panel opened by clicking the chart — so tests click through
 * to the expanded view and assert the register badge is present/absent
 * depending on the input shape.
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OperatorRadarChart } from '../../components/charts/OperatorRadarChart';
import type { PhenomenologicalRegister } from '../../api/types';

const TEN_SCORES: number[] = [0.7, 0.8, 0.6, 0.55, 0.7, 0.68, 0.77, 0.6, 0.58, 0.66];

describe('OperatorRadarChart — CAS v7.5 Register rendering', () => {
  it('renders without a register badge when no registers are provided (v7.4 shape)', () => {
    const { container } = render(<OperatorRadarChart scores={TEN_SCORES} />);
    // Click anywhere on the wrapper to open the details panel.
    const wrapper = container.querySelector('.chart-interactive') as HTMLElement;
    fireEvent.click(wrapper);
    // Register badges use data-testid="register-badge-<index>"; none should exist.
    expect(container.querySelector('[data-testid^="register-badge-"]')).toBeNull();
  });

  it('renders without a register badge when registers is all-null', () => {
    const allNull: (PhenomenologicalRegister | null)[] = Array(10).fill(null);
    const { container } = render(
      <OperatorRadarChart scores={TEN_SCORES} registers={allNull} />,
    );
    const wrapper = container.querySelector('.chart-interactive') as HTMLElement;
    fireEvent.click(wrapper);
    expect(container.querySelector('[data-testid^="register-badge-"]')).toBeNull();
  });

  it('renders register badges only for annotated positions when registers are mixed', () => {
    const mixed: (PhenomenologicalRegister | null)[] = [
      'T', 'A', 'f', 'E', null, null, null, null, null, null,
    ];
    const { container } = render(
      <OperatorRadarChart scores={TEN_SCORES} registers={mixed} />,
    );
    const wrapper = container.querySelector('.chart-interactive') as HTMLElement;
    fireEvent.click(wrapper);

    // First four operators carry registers T, A, f, E.
    expect(screen.getByTestId('register-badge-0').textContent).toContain('T');
    expect(screen.getByTestId('register-badge-1').textContent).toContain('A');
    expect(screen.getByTestId('register-badge-2').textContent).toContain('f');
    expect(screen.getByTestId('register-badge-3').textContent).toContain('E');
    // Remaining positions have no register badge.
    for (let i = 4; i < 10; i += 1) {
      expect(screen.queryByTestId(`register-badge-${i}`)).toBeNull();
    }
  });

  it('shows human-readable register name in the badge tooltip', () => {
    const registers: (PhenomenologicalRegister | null)[] = [
      'f', null, null, null, null, null, null, null, null, null,
    ];
    const { container } = render(
      <OperatorRadarChart scores={TEN_SCORES} registers={registers} />,
    );
    const wrapper = container.querySelector('.chart-interactive') as HTMLElement;
    fireEvent.click(wrapper);
    const badge = screen.getByTestId('register-badge-0');
    // `|f` visible; tooltip surfaces the authoritative CAS v7.5 name.
    expect(badge.textContent).toContain('|f');
    expect(badge.getAttribute('title')).toContain('Affective');
  });
});
