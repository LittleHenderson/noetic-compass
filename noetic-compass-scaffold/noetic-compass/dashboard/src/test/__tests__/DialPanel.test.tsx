import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DialPanel } from '../../components/config/DialPanel';

describe('DialPanel', () => {
  it('renders all 10 sliders', () => {
    render(<DialPanel onSave={vi.fn()} saving={false} />);
    const sliders = screen.getAllByRole('slider');
    expect(sliders).toHaveLength(10);
  });

  it('save button is enabled with valid defaults', () => {
    render(<DialPanel onSave={vi.fn()} saving={false} />);
    const saveBtn = screen.getByRole('button', { name: /save/i });
    expect(saveBtn).not.toBeDisabled();
  });

  it('calls onSave with current values', async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<DialPanel initialValues={[6, 6, 6, 6, 6, 6, 6, 6, 6, 6]} onSave={onSave} saving={false} />);
    await user.click(screen.getByRole('button', { name: /save/i }));
    expect(onSave).toHaveBeenCalledWith([6, 6, 6, 6, 6, 6, 6, 6, 6, 6]);
  });

  it('resets to default', async () => {
    const user = userEvent.setup();
    render(<DialPanel initialValues={[3, 9, 3, 9, 3, 9, 3, 9, 3, 9]} onSave={vi.fn()} saving={false} />);
    await user.click(screen.getByRole('button', { name: /reset/i }));
    const sliders = screen.getAllByRole('slider');
    sliders.forEach((s) => expect(s).toHaveValue('6'));
  });

  it('disables save button while saving', () => {
    render(<DialPanel onSave={vi.fn()} saving={true} />);
    const saveBtn = screen.getByRole('button', { name: /saving/i });
    expect(saveBtn).toBeDisabled();
  });
});
