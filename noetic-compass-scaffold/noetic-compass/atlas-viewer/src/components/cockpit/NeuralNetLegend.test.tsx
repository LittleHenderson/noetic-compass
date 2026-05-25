import { render, screen } from '@testing-library/react';
import NeuralNetLegend from './NeuralNetLegend';

describe('NeuralNetLegend', () => {
  it('stays on the left side away from the mini stack dock', () => {
    render(<NeuralNetLegend />);

    const legend = screen.getByTestId('neural-net-legend');
    expect(legend).toHaveStyle({
      left: '12px',
      top: '12px',
    });
    expect(legend).not.toHaveStyle({
      right: '12px',
    });
  });
});
