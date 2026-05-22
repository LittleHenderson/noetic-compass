import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import SpatialEvidencePanel from './SpatialEvidencePanel';
import type { EvidenceRef, VisualPrimitive } from '../../lib/visualPrimitives';

const basePoint: VisualPrimitive = {
  id: 'p1',
  kind: 'point',
  image_id: 'img1',
  coords_norm: [0.1, 0.2],
  source: 'human_annotation',
  label: 'Left hand',
  cas_label: '^2^P',
  cas_axis: 'Noetic',
  confidence: 0.92,
  evidence_ref: { trace_id: 't1', row_id: 'r1' },
};

const baseBox: VisualPrimitive = {
  id: 'p2',
  kind: 'box',
  image_id: 'img1',
  coords_norm: [0.0, 0.0, 0.5, 0.5],
  source: 'fixture',
  label: 'Frame',
  cas_label: '^3^C',
  cas_axis: 'Domain',
  confidence: 0.62,
};

const baseRegion: VisualPrimitive = {
  id: 'p3',
  kind: 'region',
  image_id: 'img1',
  coords_norm: [0.1, 0.1, 0.2, 0.1, 0.2, 0.2, 0.1, 0.2],
  source: 'model_output',
  cas_label: '^8',
  cas_axis: 'Drive',
  confidence: 0.4,
  explanation: 'Model attended to this region while emitting ^8.',
};

describe('SpatialEvidencePanel', () => {
  it('renders empty state when no primitives', () => {
    render(<SpatialEvidencePanel primitives={[]} />);
    expect(screen.getByTestId('spatial-evidence-empty')).toHaveTextContent(
      'No spatial evidence for this step',
    );
  });

  it('renders custom empty state label', () => {
    render(<SpatialEvidencePanel primitives={[]} emptyStateLabel="nothing here" />);
    expect(screen.getByTestId('spatial-evidence-empty')).toHaveTextContent('nothing here');
  });

  it('renders one card per primitive', () => {
    render(<SpatialEvidencePanel primitives={[basePoint, baseBox, baseRegion]} />);
    expect(screen.getByTestId('spatial-evidence-card-p1')).toBeInTheDocument();
    expect(screen.getByTestId('spatial-evidence-card-p2')).toBeInTheDocument();
    expect(screen.getByTestId('spatial-evidence-card-p3')).toBeInTheDocument();
  });

  it('uses label or falls back to "Unnamed primitive"', () => {
    render(<SpatialEvidencePanel primitives={[basePoint, baseRegion]} />);
    expect(screen.getByTestId('spatial-evidence-card-p1')).toHaveTextContent('Left hand');
    expect(screen.getByTestId('spatial-evidence-card-p3')).toHaveTextContent(
      'Unnamed primitive',
    );
  });

  it('renders cas_label and English (explanation or toEnglish fallback)', () => {
    render(<SpatialEvidencePanel primitives={[basePoint, baseRegion]} />);
    expect(screen.getByTestId('spatial-evidence-cas-p1')).toHaveTextContent('^2^P');
    expect(screen.getByTestId('spatial-evidence-en-p1')).toHaveTextContent(
      'Drawn to it like a moth to a flame.',
    );
    expect(screen.getByTestId('spatial-evidence-en-p3')).toHaveTextContent(
      'Model attended to this region while emitting ^8.',
    );
  });

  it('selectedPrimitiveId highlights the correct card via aria-selected', () => {
    render(
      <SpatialEvidencePanel
        primitives={[basePoint, baseBox]}
        selectedPrimitiveId="p2"
      />,
    );
    expect(screen.getByTestId('spatial-evidence-card-p2')).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByTestId('spatial-evidence-card-p1')).toHaveAttribute(
      'aria-selected',
      'false',
    );
  });

  it('clicking a card triggers onPrimitiveSelect with that primitive', () => {
    const onPrimitiveSelect = vi.fn();
    render(
      <SpatialEvidencePanel
        primitives={[basePoint, baseBox]}
        onPrimitiveSelect={onPrimitiveSelect}
      />,
    );
    fireEvent.click(screen.getByTestId('spatial-evidence-card-p2'));
    expect(onPrimitiveSelect).toHaveBeenCalledTimes(1);
    expect(onPrimitiveSelect).toHaveBeenCalledWith(baseBox);
  });

  it('evidence button only renders when evidence_ref present', () => {
    render(<SpatialEvidencePanel primitives={[basePoint, baseBox]} />);
    expect(screen.getByTestId('spatial-evidence-open-p1')).toBeInTheDocument();
    expect(screen.queryByTestId('spatial-evidence-open-p2')).toBeNull();
  });

  it('evidence button click triggers onOpenEvidence with the ref and does not also select', () => {
    const onOpenEvidence = vi.fn<(ref: EvidenceRef) => void>();
    const onPrimitiveSelect = vi.fn();
    render(
      <SpatialEvidencePanel
        primitives={[basePoint]}
        onOpenEvidence={onOpenEvidence}
        onPrimitiveSelect={onPrimitiveSelect}
      />,
    );
    fireEvent.click(screen.getByTestId('spatial-evidence-open-p1'));
    expect(onOpenEvidence).toHaveBeenCalledTimes(1);
    expect(onOpenEvidence).toHaveBeenCalledWith(basePoint.evidence_ref);
    expect(onPrimitiveSelect).not.toHaveBeenCalled();
  });

  it('confidence badge renders when confidence defined', () => {
    render(<SpatialEvidencePanel primitives={[basePoint, baseRegion]} />);
    expect(screen.getByTestId('spatial-evidence-confidence-p1')).toHaveTextContent(
      'conf 0.92',
    );
    expect(screen.getByTestId('spatial-evidence-confidence-p3')).toHaveTextContent(
      'conf 0.40',
    );
  });

  it('arrow-key navigation moves selection down then up', () => {
    const onPrimitiveSelect = vi.fn();
    render(
      <SpatialEvidencePanel
        primitives={[basePoint, baseBox, baseRegion]}
        selectedPrimitiveId="p1"
        onPrimitiveSelect={onPrimitiveSelect}
      />,
    );
    const first = screen.getByTestId('spatial-evidence-card-p1');
    first.focus();
    fireEvent.keyDown(first, { key: 'ArrowDown' });
    expect(onPrimitiveSelect).toHaveBeenLastCalledWith(baseBox);
    const second = screen.getByTestId('spatial-evidence-card-p2');
    fireEvent.keyDown(second, { key: 'ArrowDown' });
    expect(onPrimitiveSelect).toHaveBeenLastCalledWith(baseRegion);
    const third = screen.getByTestId('spatial-evidence-card-p3');
    fireEvent.keyDown(third, { key: 'ArrowUp' });
    expect(onPrimitiveSelect).toHaveBeenLastCalledWith(baseBox);
  });

  it('Enter on focused card with evidence_ref triggers onOpenEvidence', () => {
    const onOpenEvidence = vi.fn<(ref: EvidenceRef) => void>();
    render(
      <SpatialEvidencePanel
        primitives={[basePoint]}
        selectedPrimitiveId="p1"
        onOpenEvidence={onOpenEvidence}
      />,
    );
    const card = screen.getByTestId('spatial-evidence-card-p1');
    card.focus();
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onOpenEvidence).toHaveBeenCalledWith(basePoint.evidence_ref);
  });

  it('exposes list / listitem roles for ARIA', () => {
    render(<SpatialEvidencePanel primitives={[basePoint, baseBox]} />);
    const list = screen.getByRole('list');
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
  });
});
