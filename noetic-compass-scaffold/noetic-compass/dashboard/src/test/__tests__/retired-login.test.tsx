import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../../App';

afterEach(() => { localStorage.clear(); vi.unstubAllGlobals(); });
it.each(['/login', '/scenarios', '/assessment'])('retired route %s cannot mint or restore a legacy session', async (route) => {
  const fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  localStorage.setItem('nc_jwt_token', 'synthetic-old-token');
  render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>);
  expect(await screen.findByRole('status')).toHaveTextContent('Legacy dashboard sign-in is retired.');
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'How it works' })).toHaveAttribute('href', '/how-it-works');
  expect(screen.getByRole('link', { name: 'FAQ' })).toHaveAttribute('href', '/faq');
  expect(localStorage.getItem('nc_jwt_token')).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});
