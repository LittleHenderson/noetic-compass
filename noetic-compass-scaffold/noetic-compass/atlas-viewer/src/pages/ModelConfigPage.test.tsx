import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import ModelConfigPage from './ModelConfigPage';

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location">{`${location.pathname}${location.search}`}</p>;
}

describe('ModelConfigPage', () => {
  it('hands the supported model to the CAS Harness Audit Console query', () => {
    render(
      <MemoryRouter initialEntries={['/model-config']}>
        <Routes>
          <Route path="/model-config" element={<ModelConfigPage />} />
          <Route path="/audit-console" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('radio', { name: /Pythia/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByText('Live')).toBeInTheDocument();
    expect(screen.getAllByText(/hosted live worker/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/connect step verifies/i).length).toBeGreaterThan(0);
    expect(screen.queryByText('Reference')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Choose model for CAS audit' }));

    expect(screen.getByTestId('location')).toHaveTextContent(
      '/audit-console?model=pythia-160m',
    );
  });
});
