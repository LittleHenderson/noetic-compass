// Bundled day-1 evidence fixtures. These are faithful snapshots of the real
// CAS Forex evidence_runs/index_tsmom_126_paper_proof/*.json files (2026-06-22),
// so the read-only cockpit displays TRUTHFUL state with no live backend wired.
//
// When a real /api/forex/* backend exists, forexApi prefers it and these become
// the offline fallback only.

import paperProofRaw from './paperProofStatus.json';
import uiReadinessRaw from './uiReadinessStatus.json';
import dailyScheduleRaw from './dailyScheduleStatus.json';
import paperDecisionRaw from './paperDecisionStatus.json';
import paperRiskRaw from './paperRiskStatus.json';
import dailyBundleRaw from './dailyBundleStatus.json';
import adaptiveCockpitRaw from './adaptiveCockpit.json';

import type {
  PaperProofStatus,
  UiReadinessStatus,
  DailyScheduleStatus,
  PaperDecisionStatus,
  PaperRiskStatus,
  DailyBundleStatus,
  AdaptiveCockpitPayload,
} from '../types';

export const paperProofFixture = paperProofRaw as unknown as PaperProofStatus;
export const uiReadinessFixture = uiReadinessRaw as unknown as UiReadinessStatus;
export const dailyScheduleFixture = dailyScheduleRaw as unknown as DailyScheduleStatus;
export const paperDecisionFixture = paperDecisionRaw as unknown as PaperDecisionStatus;
export const paperRiskFixture = paperRiskRaw as unknown as PaperRiskStatus;
export const dailyBundleFixture = dailyBundleRaw as unknown as DailyBundleStatus;
export const adaptiveCockpitFixture = adaptiveCockpitRaw as unknown as AdaptiveCockpitPayload;
