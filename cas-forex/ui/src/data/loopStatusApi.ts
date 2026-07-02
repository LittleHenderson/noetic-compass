import { apiGet } from "./apiCore";
import { fetchWasteStageProbe } from "./wasteStageProbe";

export async function fetchDispatchLoopStatus(): Promise<Record<string, unknown> | null> {
  try {
    return await apiGet<Record<string, unknown>>("/dispatch-loop/status");
  } catch {
    return null;
  }
}

export async function fetchWasteLoopStatus(): Promise<Record<string, unknown> | null> {
  try {
    return await apiGet<Record<string, unknown>>("/waste-loop-control/status/fast");
  } catch {
    return null;
  }
}

export async function fetchWasteLoopStage(): Promise<Record<string, unknown> | null> {
  return await fetchWasteStageProbe({ timeoutMs: 6_000, maxAgeMs: 1_000 });
}
