import type { ReplayTrace } from './replayController';
import {
  loadSpatialEvidenceArtifact,
  type SpatialEvidenceArtifact,
} from './visualPrimitives';

// @ts-expect-error JSON fixture lives in atlas-viewer/test-fixtures/, outside
// the tsconfig "include" glob ("src"). Vite/Vitest resolve the import at
// runtime via resolveJsonModule + the bundler's native JSON loader.
import pythiaTraceJson from '../../test-fixtures/pythia_160m_reference_trace.json';
import visualGroundingJson from '../fixtures/visualGroundingDemo.json';

export async function loadPythiaTrace(): Promise<ReplayTrace> {
  return pythiaTraceJson as unknown as ReplayTrace;
}

export async function loadSpatialEvidenceDemo(): Promise<SpatialEvidenceArtifact> {
  return loadSpatialEvidenceArtifact(visualGroundingJson);
}
