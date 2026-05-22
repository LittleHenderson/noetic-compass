import { describe, expect, it } from 'vitest';

import { KNOB_TYPE_VALUES } from './testingMethods';
import {
  SPATIAL_EVIDENCE_MODULE,
  coordsNormToPx,
  loadSpatialEvidenceArtifact,
  parseVisualPrimitive,
  primitivesForStep,
  type SpatialEvidenceArtifact,
  type VisualPrimitive,
} from './visualPrimitives';

const POINT_FIXTURE: VisualPrimitive = {
  id: 'p1',
  kind: 'point',
  image_id: 'img-001',
  coords_norm: [0.5, 0.25],
  source: 'fixture',
};

const BOX_FIXTURE: VisualPrimitive = {
  id: 'p2',
  kind: 'box',
  image_id: 'img-001',
  coords_norm: [0.1, 0.2, 0.5, 0.6],
  source: 'human_annotation',
  cas_axis: 'Drive',
  cas_label: 'F3',
  confidence: 0.92,
};

const POLYLINE_FIXTURE: VisualPrimitive = {
  id: 'p3',
  kind: 'polyline',
  image_id: 'img-001',
  coords_norm: [0.1, 0.1, 0.5, 0.5, 0.9, 0.1],
  source: 'cas_trace',
  evidence_ref: { trace_id: 't-1', token_index: 4 },
};

function makeArtifact(): SpatialEvidenceArtifact {
  return {
    schema_version: 'spatial_evidence_v1',
    trace_id: 't-1',
    image_id: 'img-001',
    image_url: './fixtures/img-001.png',
    image_width: 1000,
    image_height: 800,
    primitives: [POINT_FIXTURE, BOX_FIXTURE, POLYLINE_FIXTURE],
    grounded_steps: [
      {
        trace_id: 't-1',
        step_id: 's1',
        token_index: 0,
        primitive_ids: ['p1', 'p2'],
      },
      {
        trace_id: 't-1',
        step_id: 's2',
        token_index: 4,
        primitive_ids: ['p3'],
      },
    ],
  };
}

describe('parseVisualPrimitive', () => {
  it('accepts each valid kind', () => {
    for (const fixture of [POINT_FIXTURE, BOX_FIXTURE, POLYLINE_FIXTURE]) {
      expect(parseVisualPrimitive(fixture)).toEqual(fixture);
    }
  });

  it('rejects an invalid kind enum value', () => {
    expect(() =>
      parseVisualPrimitive({
        id: 'x',
        kind: 'blob',
        image_id: 'img',
        coords_norm: [0.5, 0.5],
        source: 'fixture',
      }),
    ).toThrow(/kind/);
  });

  it('rejects an invalid source enum value', () => {
    expect(() =>
      parseVisualPrimitive({
        id: 'x',
        kind: 'point',
        image_id: 'img',
        coords_norm: [0.5, 0.5],
        source: 'guess',
      }),
    ).toThrow(/source/);
  });

  it('rejects coords_norm outside [0,1]', () => {
    expect(() =>
      parseVisualPrimitive({
        id: 'x',
        kind: 'point',
        image_id: 'img',
        coords_norm: [1.5, 0.5],
        source: 'fixture',
      }),
    ).toThrow(/coords_norm/);
  });

  it('rejects wrong coord arity for kind', () => {
    expect(() =>
      parseVisualPrimitive({
        id: 'x',
        kind: 'box',
        image_id: 'img',
        coords_norm: [0.1, 0.2, 0.3],
        source: 'fixture',
      }),
    ).toThrow(/coords_norm length/);
  });

  it('rejects confidence outside [0,1]', () => {
    expect(() =>
      parseVisualPrimitive({
        ...POINT_FIXTURE,
        confidence: 1.5,
      }),
    ).toThrow(/confidence/);
  });
});

describe('loadSpatialEvidenceArtifact', () => {
  it('loads a valid artifact round-trip', () => {
    const a = makeArtifact();
    const loaded = loadSpatialEvidenceArtifact(JSON.parse(JSON.stringify(a)));
    expect(loaded.schema_version).toBe('spatial_evidence_v1');
    expect(loaded.primitives).toHaveLength(3);
    expect(loaded.grounded_steps).toHaveLength(2);
  });

  it('catches schema mismatch on schema_version', () => {
    const a = makeArtifact();
    expect(() =>
      loadSpatialEvidenceArtifact({ ...a, schema_version: 'spatial_evidence_v0' }),
    ).toThrow(/schema_version/);
  });

  it('catches missing required fields', () => {
    expect(() =>
      loadSpatialEvidenceArtifact({
        schema_version: 'spatial_evidence_v1',
        trace_id: 't',
      }),
    ).toThrow();
  });

  it('rejects non-positive image dimensions', () => {
    const a = makeArtifact();
    expect(() => loadSpatialEvidenceArtifact({ ...a, image_width: 0 })).toThrow(
      /image_width/,
    );
  });

  it('rejects grounded steps referencing unknown primitive ids', () => {
    const a = makeArtifact();
    const bad = {
      ...a,
      grounded_steps: [
        { trace_id: 't-1', step_id: 's1', primitive_ids: ['unknown'] },
      ],
    };
    expect(() => loadSpatialEvidenceArtifact(bad)).toThrow(/unknown primitive_id/);
  });
});

describe('coordsNormToPx', () => {
  it('converts a point', () => {
    expect(coordsNormToPx(POINT_FIXTURE, 1000, 800)).toEqual([500, 200]);
  });

  it('converts a box', () => {
    expect(coordsNormToPx(BOX_FIXTURE, 1000, 800)).toEqual([100, 160, 500, 480]);
  });

  it('converts a polyline', () => {
    expect(coordsNormToPx(POLYLINE_FIXTURE, 1000, 800)).toEqual([
      100, 80, 500, 400, 900, 80,
    ]);
  });

  it('rejects non-positive image dimensions', () => {
    expect(() => coordsNormToPx(POINT_FIXTURE, 0, 800)).toThrow(/imageW/);
  });
});

describe('primitivesForStep', () => {
  it('returns the primitives linked to a step', () => {
    const a = makeArtifact();
    const list = primitivesForStep(a, 's1');
    expect(list.map((p) => p.id)).toEqual(['p1', 'p2']);
  });

  it('returns the single primitive for s2', () => {
    const a = makeArtifact();
    const list = primitivesForStep(a, 's2');
    expect(list.map((p) => p.id)).toEqual(['p3']);
  });

  it('returns an empty array for an unknown step', () => {
    const a = makeArtifact();
    expect(primitivesForStep(a, 'missing')).toEqual([]);
  });
});

describe('SPATIAL_EVIDENCE_MODULE', () => {
  it('matches the TestingMethod shape', () => {
    const m = SPATIAL_EVIDENCE_MODULE;
    expect(m.id).toBe('spatial_evidence_layer');
    expect(m.name).toBe('Spatial Evidence Layer');
    expect(m.orderIndex).toBe(9);
    expect(m.costEstimateGpuMinutes).toBe(0);
    expect(m.stageAnchor).toBe('Beta v0 (fixture-backed)');
    expect(m.validatedArchs).toEqual(['pythia']);
    expect(m.knobs.length).toBeGreaterThan(0);
    for (const knob of m.knobs) {
      expect(KNOB_TYPE_VALUES).toContain(knob.type);
    }
  });

  it('uses verbatim description and reveals text', () => {
    expect(SPATIAL_EVIDENCE_MODULE.description).toBe(
      'Links CAS trace steps to points, boxes, or regions in an image so the user can see exactly what visual evidence a reasoning move refers to.',
    );
    expect(SPATIAL_EVIDENCE_MODULE.reveals).toBe(
      'Grounded trace overlay + evidence-linked visual references on uploaded or fixture images.',
    );
    expect(SPATIAL_EVIDENCE_MODULE.outputShape).toBe(
      'Per-step visual primitive list with CAS labels + evidence refs',
    );
  });

  it('exposes source-filter, kind-filter, show-confidence knobs', () => {
    const m = SPATIAL_EVIDENCE_MODULE;
    const sourceFilter = m.knobs.find((k) => k.id === 'source_filter');
    expect(sourceFilter?.type).toBe('multiselect');
    expect(sourceFilter?.options).toEqual([
      'human_annotation',
      'fixture',
      'model_output',
      'cas_trace',
    ]);
    const kindFilter = m.knobs.find((k) => k.id === 'kind_filter');
    expect(kindFilter?.type).toBe('multiselect');
    expect(kindFilter?.options).toEqual(['point', 'box', 'polyline', 'region']);
    const showConfidence = m.knobs.find((k) => k.id === 'show_confidence');
    expect(showConfidence?.type).toBe('boolean');
    expect(showConfidence?.default).toBe(true);
  });
});
