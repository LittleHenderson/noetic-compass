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
    expect(screen.getByText('Reference')).toBeInTheDocument();
    expect(screen.getAllByText(/Hosted real-weight worker operation remains OPEN/i).length).toBeGreaterThan(0);
    expect(screen.queryByText('Live')).not.toBeInTheDocument();
    expect(screen.queryByText(/wired end-to-end/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Choose model for CAS audit' }));

    expect(screen.getByTestId('location')).toHaveTextContent(
      '/audit-console?model=pythia-160m',
    );
  });
});
