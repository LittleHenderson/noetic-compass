import type { ReplayTrace } from './replayController';
import {
  loadSpatialEvidenceArtifact,
  type SpatialEvidenceArtifact,
} from './visualPrimitives';
import { bandForConfidence, type ConfidenceBand } from './confidenceBands';
import pythiaTraceJson from '../../test-fixtures/pythia_160m_reference_trace.json';
import visualGroundingJson from '../fixtures/visualGroundingDemo.json';
import visualGroundingImageUrl from '../fixtures/visualGroundingDemoImage.svg?url';
import visualGroundingCrosswalkJson from '../fixtures/visualGroundingCrosswalk.json';
import visualGroundingCrosswalkUrl from '../fixtures/visualGroundingCrosswalk.svg?url';
import visualGroundingClinicJson from '../fixtures/visualGroundingClinic.json';
import visualGroundingClinicUrl from '../fixtures/visualGroundingClinic.svg?url';

interface CalibratedCoverMember {
  label: string;
  confidence: number | null;
  confidence_band: ConfidenceBand;
  evidence_sources: string[];
}

interface BestCoverReport {
  labels: string[];
  confidence: number;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function calibratedReplayTrace(raw: unknown): ReplayTrace {
  const trace = JSON.parse(JSON.stringify(raw)) as Record<string, unknown>;
  const neuronCovers = asRecord(trace.neuron_covers);
  if (!neuronCovers) return trace as unknown as ReplayTrace;

  const rowReports = Array.isArray(neuronCovers.row_reports)
    ? neuronCovers.row_reports
    : [];
  const bestByTarget = new Map<string, BestCoverReport>();

  for (const rowUnknown of rowReports) {
    const row = asRecord(rowUnknown);
    if (!row || typeof row.target !== 'string') continue;
    const cleanMargin = typeof row.clean_margin === 'number' ? row.clean_margin : null;
    const targetedDrop = typeof row.targeted_drop === 'number' ? row.targeted_drop : null;
    const labels = stringArray(row.neuron_cover);
    if (!cleanMargin || cleanMargin <= 0 || targetedDrop === null || labels.length === 0) {
      continue;
    }
    const confidence = Math.round((targetedDrop / cleanMargin) * 1000) / 1000;
    const existing = bestByTarget.get(row.target);
    if (!existing || confidence > existing.confidence) {
      bestByTarget.set(row.target, { labels, confidence });
    }
  }

  const legacyCovers = asRecord(neuronCovers.per_class_neuron_covers) ?? {};
  const classKeys = new Set([...Object.keys(legacyCovers), ...bestByTarget.keys()]);
  const calibrated: Record<string, CalibratedCoverMember[]> = {};

  for (const classKey of classKeys) {
    const best = bestByTarget.get(classKey);
    const labels = best?.labels ?? stringArray(legacyCovers[classKey]);
    calibrated[classKey] = labels.map((label) => ({
      label,
      confidence: best?.confidence ?? null,
      confidence_band: bandForConfidence(best?.confidence ?? null),
      evidence_sources: best
        ? ['Stage27F cover', 'clean_margin', 'targeted_drop']
        : [],
    }));
  }

  neuronCovers.per_class_neuron_covers = calibrated;
  return trace as unknown as ReplayTrace;
}

export async function loadPythiaTrace(): Promise<ReplayTrace> {
  return calibratedReplayTrace(pythiaTraceJson);
}

export async function loadSpatialEvidenceDemo(): Promise<SpatialEvidenceArtifact> {
  // Override the fixture's relative path with the Vite-resolved bundled URL so
  // the <img> renders correctly regardless of the page route the cockpit is mounted at.
  const withResolvedImage = {
    ...(visualGroundingJson as Record<string, unknown>),
    image_url: visualGroundingImageUrl,
  };
  return loadSpatialEvidenceArtifact(withResolvedImage);
}

export async function loadSpatialEvidenceDemos(): Promise<SpatialEvidenceArtifact[]> {
  return [
    loadSpatialEvidenceArtifact({
      ...(visualGroundingJson as Record<string, unknown>),
      image_url: visualGroundingImageUrl,
    }),
    loadSpatialEvidenceArtifact({
      ...(visualGroundingCrosswalkJson as Record<string, unknown>),
      image_url: visualGroundingCrosswalkUrl,
    }),
    loadSpatialEvidenceArtifact({
      ...(visualGroundingClinicJson as Record<string, unknown>),
      image_url: visualGroundingClinicUrl,
    }),
  ];
}
