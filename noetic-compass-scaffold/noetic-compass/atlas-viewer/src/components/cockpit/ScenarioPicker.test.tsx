import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ScenarioPicker from './ScenarioPicker';
import type { AlphaScenario } from '../../lib/alphaScenarios';

const SCENARIOS: AlphaScenario[] = [
  {
    id: 'alpha_safe_f1',
    sourcePath: 'fixture#1',
    prompt: 'How do you keep everyone included in a tense team decision?',
    sentence: 'How do you keep everyone included in a tense team decision?',
    purpose: 'Tests inclusion and team voice.',
    expectedCasAxes: { domain: 'O', noetic: '^5', drive: 'F1', register: 'E' },
    difficulty: 'easy',
    demoSafe: true,
    demoSafetySource: 'explicit',
    honestyFlag: null,
  },
  {
    id: 'alpha_safe_f5',
    sourcePath: 'fixture#2',
    prompt: 'What does real consent require when pressure is present?',
    sentence: 'What does real consent require when pressure is present?',
    purpose: 'Tests choice and control.',
    expectedCasAxes: { domain: 'P', noetic: '^3', drive: 'F5', register: 'A' },
    difficulty: 'hard',
    demoSafe: true,
    demoSafetySource: 'explicit',
    honestyFlag: null,
  },
  {
    id: 'alpha_unsafe_f1',
    sourcePath: 'fixture#3',
    prompt: 'Unsafe scenario excluded by the default demo-safe filter.',
    sentence: 'Unsafe scenario excluded by the default demo-safe filter.',
    purpose: 'Tests demo safety filtering.',
    expectedCasAxes: { domain: 'E', noetic: '^2', drive: 'F1', register: 'f' },
    difficulty: 'medium',
    demoSafe: false,
    demoSafetySource: 'explicit',
    honestyFlag: 'Unsafe fixture.',
  },
];

describe('ScenarioPicker', () => {
  it('renders demo-safe scenarios by default', () => {
    render(<ScenarioPicker scenarios={SCENARIOS} />);

    expect(screen.getByTestId('scenario-count')).toHaveTextContent('2 scenarios');
    expect(screen.getByTestId('scenario-option-alpha_safe_f1')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-option-alpha_safe_f5')).toBeInTheDocument();
    expect(screen.queryByTestId('scenario-option-alpha_unsafe_f1')).not.toBeInTheDocument();
  });

  it('filters by drive and difficulty', () => {
    render(<ScenarioPicker scenarios={SCENARIOS} />);

    fireEvent.change(screen.getByTestId('scenario-filter-drive'), {
      target: { value: 'F5' },
    });
    expect(screen.getByTestId('scenario-count')).toHaveTextContent('1 scenarios');
    expect(screen.getByTestId('scenario-option-alpha_safe_f5')).toHaveTextContent(
      'What does real consent require when pressure is present?',
    );

    fireEvent.change(screen.getByTestId('scenario-filter-difficulty'), {
      target: { value: 'easy' },
    });
    expect(screen.getByTestId('scenario-count')).toHaveTextContent('0 scenarios');
  });

  it('can show all scenarios when demo-safe filtering is disabled', () => {
    render(<ScenarioPicker scenarios={SCENARIOS} />);

    fireEvent.change(screen.getByTestId('scenario-filter-demo-safe'), {
      target: { value: 'all' },
    });
    expect(screen.getByTestId('scenario-count')).toHaveTextContent('3 scenarios');
    expect(screen.getByTestId('scenario-option-alpha_unsafe_f1')).toBeInTheDocument();
  });

  it('calls onSelect with the selected scenario', () => {
    const onSelect = vi.fn();
    render(<ScenarioPicker scenarios={SCENARIOS} onSelect={onSelect} />);

    fireEvent.click(screen.getByTestId('scenario-option-alpha_safe_f1'));
    expect(onSelect).toHaveBeenCalledWith(SCENARIOS[0]);
  });

  it('marks the selected scenario visually for host shells', () => {
    render(<ScenarioPicker scenarios={SCENARIOS} selectedId="alpha_safe_f5" />);

    expect(screen.getByTestId('scenario-option-alpha_safe_f5')).toHaveStyle({
      cursor: 'pointer',
    });
    expect(screen.getByTestId('scenario-option-alpha_safe_f5').getAttribute('style')).toContain(
      '56, 189, 248',
    );
  });
});
