import { useEffect, type Dispatch, type SetStateAction } from "react";
import type { DashboardState } from "../types/evidence";

interface DashboardStateHydratorProps {
  fastFetchDeferMs?: number;
  initialState: DashboardState;
  onError: Dispatch<SetStateAction<string | null>>;
  onState: Dispatch<SetStateAction<DashboardState | null>>;
}

export function DashboardStateHydrator({
  fastFetchDeferMs,
  initialState,
  onError,
  onState,
}: DashboardStateHydratorProps) {
  useEffect(() => {
    let cancelled = false;
    onError(null);

    void import("../data/dashboardApi")
      .then(({ loadDashboardState }) => {
        if (cancelled) return undefined;
        return loadDashboardState(initialState, {
          setState: onState,
          setError: onError,
          isCancelled: () => cancelled,
        }, { fastFetchDeferMs });
      })
      .catch(() => {
        if (cancelled) return;
        onState(initialState);
        onError("Live API shell/fast dashboard unavailable - using local startup state");
      });

    return () => {
      cancelled = true;
    };
  }, [fastFetchDeferMs, initialState, onError, onState]);

  return null;
}
