import type { ReplayTrace } from './replayController';
import {
  loadSpatialEvidenceArtifact,
  type SpatialEvidenceArtifact,
} from './visualPrimitives';
import pythiaTraceJson from '../../test-fixtures/pythia_160m_reference_trace.json';
import visualGroundingJson from '../fixtures/visualGroundingDemo.json';
import visualGroundingImageUrl from '../fixtures/visualGroundingDemoImage.svg?url';
import visualGroundingCrosswalkJson from '../fixtures/visualGroundingCrosswalk.json';
import visualGroundingCrosswalkUrl from '../fixtures/visualGroundingCrosswalk.svg?url';
import visualGroundingClinicJson from '../fixtures/visualGroundingClinic.json';
import visualGroundingClinicUrl from '../fixtures/visualGroundingClinic.svg?url';

export async function loadPythiaTrace(): Promise<ReplayTrace> {
  return pythiaTraceJson as unknown as ReplayTrace;
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
