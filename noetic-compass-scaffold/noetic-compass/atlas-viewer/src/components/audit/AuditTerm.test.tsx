import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AuditTerm } from './AuditTerm';

describe('AuditTerm', () => {
  it('renders a hoverable plain-English definition', () => {
    render(<AuditTerm term="matchedControl">matched control</AuditTerm>);

    const term = screen.getByRole('note', { name: /matched control/i });
    expect(term).not.toHaveAttribute('title');
    fireEvent.mouseEnter(term);
    expect(screen.getByRole('tooltip')).toHaveTextContent('fair comparison');
  });
});
