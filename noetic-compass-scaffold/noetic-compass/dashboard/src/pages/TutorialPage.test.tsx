import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { TutorialPage } from './TutorialPage';

function renderTutorial() {
  return render(
    <BrowserRouter>
      <TutorialPage />
    </BrowserRouter>,
  );
}

describe('TutorialPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders the plain-language tutorial entry point', () => {
    renderTutorial();
    expect(screen.getByRole('heading', {
      name: /Learn Noetic Compass without starting in the math/i,
    })).toBeInTheDocument();
    expect(screen.getByText(/About five minutes/i)).toBeInTheDocument();
  });

  it('starts in simple mode and can reveal the technical layer', () => {
    renderTutorial();
    expect(screen.getByText(/structured map you can inspect/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /technical/i }));

    expect(screen.getByText(/Noetics, Domains, Registers, Drives/i)).toBeInTheDocument();
  });

  it('advances and returns between tutorial steps', () => {
    renderTutorial();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    expect(screen.getByRole('heading', { name: /First, look at the shape/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));

    expect(screen.getByRole('heading', { name: /CAS looks for structure/i })).toBeInTheDocument();
  });

  it('links each next-step card to the real app surface', () => {
    renderTutorial();
    expect(screen.getByRole('link', { name: /Visual \+ Audio/i })).toHaveAttribute('href', '/visualization');
    expect(screen.getByRole('link', { name: /Risk Forecast/i })).toHaveAttribute('href', '/forecast');
    expect(screen.getByRole('link', { name: /CAS Compiler/i })).toHaveAttribute('href', '/compiler');
    expect(screen.getByRole('link', { name: /Assessment/i })).toHaveAttribute('href', '/assessment');
  });

  it('stores completion locally and can show replay status', () => {
    renderTutorial();
    fireEvent.click(screen.getByRole('button', { name: 'Mark tutorial complete' }));

    expect(localStorage.getItem('nc_tutorial_complete_v1')).toBe('1');
    expect(screen.getByText(/Tutorial marked complete/i)).toBeInTheDocument();
  });
});
