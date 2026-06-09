import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import LegalPage from './LegalPage';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <LegalPage />
    </MemoryRouter>,
  );
}

describe('LegalPage', () => {
  it('renders beta-safe legal status language', () => {
    renderAt('/legal');

    expect(screen.getByRole('heading', { name: 'Legal' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'FLAG_FOR_HUMAN_REVIEW' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'OPEN' })).toBeInTheDocument();
    expect(screen.getByText(/not legal advice, safety certification, or regulatory approval/i)).toBeInTheDocument();
  });

  it('routes privacy and terms copy from the current path', () => {
    const { unmount } = renderAt('/privacy');

    expect(screen.getByRole('heading', { name: 'Privacy' })).toBeInTheDocument();
    expect(screen.getByText(/Data-rights operations and residency enforcement are OPEN/i)).toBeInTheDocument();

    unmount();
    renderAt('/terms');

    expect(screen.getByRole('heading', { name: 'Terms' })).toBeInTheDocument();
    expect(screen.getByText(/Do not call it COMPLIANCE unless the receipt says COMPLIANCE/i)).toBeInTheDocument();
  });

  it('surfaces the CAS Compass early-access contact without changing claim status boundaries', () => {
    renderAt('/terms');

    expect(screen.getByText(/CAS Compass is the public early-access surface/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'hello@cascompass.ai' })).toHaveAttribute(
      'href',
      'mailto:hello@cascompass.ai',
    );
    expect(screen.getByRole('link', { name: 'cascompass.ai' })).toHaveAttribute(
      'href',
      'https://cascompass.ai/',
    );
    expect(screen.getByRole('button', { name: 'FLAG_FOR_HUMAN_REVIEW' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'OPEN' })).toBeInTheDocument();
  });

  it('turns every claim status into an explained interactive boundary', () => {
    renderAt('/legal');

    expect(screen.getByRole('button', { name: 'present' })).toHaveAttribute(
      'title',
      expect.stringContaining('observed in this packet or run'),
    );
    expect(screen.getByRole('button', { name: 'unavailable' })).toHaveAttribute(
      'title',
      expect.stringContaining('not returned or could not be checked'),
    );

    const reviewStatus = screen.getByRole('button', { name: 'FLAG_FOR_HUMAN_REVIEW' });
    fireEvent.mouseEnter(reviewStatus);

    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'human reviewer must decide before it becomes ACCEPT',
    );

    fireEvent.click(reviewStatus);

    expect(reviewStatus).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('note')).toHaveTextContent(
      'The system found enough signal to preserve and escalate',
    );
    expect(screen.getByRole('note')).toHaveTextContent('must decide before it becomes ACCEPT');
  });
});
