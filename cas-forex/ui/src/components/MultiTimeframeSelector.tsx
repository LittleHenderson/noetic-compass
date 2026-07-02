/* ── CAS Forex — Multi-Timeframe Selector ──
 *
 * UI face of the MultiTimeframeRuntime. Lets the operator toggle which
 * timeframes are concurrently active for a given symbol; each toggle
 * round-trips through /api/forex/timeframes so the bot, monitor loop,
 * and risk gates see the same state.
 *
 * Optimistic UI: toggling a chip updates local state immediately while
 * the POST/DELETE is in flight; on failure the local state reverts and
 * the user sees a small error. This keeps the selector responsive even
 * when the API is sluggish.
 */

import { useEffect, useState, useCallback } from "react";
import { GlassPanel } from "./GlassPanel";
import {
  activateTimeframe,
  deactivateTimeframe,
  fetchCanonicalTimeframes,
  fetchSymbolTimeframes,
} from "../data/api";
import "./SelectorChips.css";
import "./MultiTimeframeSelector.css";

interface MultiTimeframeSelectorProps {
  symbol: string;
}

export function MultiTimeframeSelector({ symbol }: MultiTimeframeSelectorProps) {
  const [canonical, setCanonical] = useState<string[] | null>(null);
  const [active, setActive] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Set<string>>(new Set());

  // Load the canonical vocabulary once.
  useEffect(() => {
    let cancelled = false;
    let retryId: number | undefined;

    async function loadCanonical() {
      const result = await fetchCanonicalTimeframes();
      if (cancelled) return;
      if (result) {
        setCanonical(result.canonical_timeframes);
      } else {
        setError("Could not load canonical timeframe vocabulary");
        retryId = window.setTimeout(() => void loadCanonical(), 5_000);
      }
    }

    void loadCanonical();
    return () => {
      cancelled = true;
      if (retryId !== undefined) window.clearTimeout(retryId);
    };
  }, []);

  // Re-sync active set whenever the symbol changes.
  const reloadActive = useCallback(async (): Promise<boolean> => {
    const result = await fetchSymbolTimeframes(symbol);
    if (result) {
      setActive(new Set(result.active_timeframes));
      setError(null);
      return true;
    }
    setError(`Could not load active timeframes for ${symbol}`);
    return false;
  }, [symbol]);

  useEffect(() => {
    let cancelled = false;
    let retryId: number | undefined;

    async function loadActive() {
      const ok = await reloadActive();
      if (!cancelled) {
        retryId = window.setTimeout(() => void loadActive(), ok ? 15_000 : 5_000);
      }
    }

    void loadActive();
    return () => {
      cancelled = true;
      if (retryId !== undefined) window.clearTimeout(retryId);
    };
  }, [reloadActive]);

  const toggle = useCallback(
    async (tf: string) => {
      const wasActive = active.has(tf);

      // Optimistic update.
      const next = new Set(active);
      if (wasActive) {
        next.delete(tf);
      } else {
        next.add(tf);
      }
      setActive(next);
      setPending((p) => new Set(p).add(tf));

      const result = wasActive
        ? await deactivateTimeframe(symbol, tf)
        : await activateTimeframe(symbol, tf);

      setPending((p) => {
        const copy = new Set(p);
        copy.delete(tf);
        return copy;
      });

      if (result) {
        // Trust the server's view, in case another writer changed state.
        setActive(new Set(result.active_timeframes));
        setError(null);
      } else {
        // Revert optimistic change.
        setActive(active);
        setError(`Could not ${wasActive ? "deactivate" : "activate"} ${tf} for ${symbol}`);
      }
    },
    [active, symbol],
  );

  return (
    <GlassPanel
      title="Active timeframes"
      subtitle={`Concurrent timeframes for ${symbol} — risk and signals aggregate across the ones you turn on`}
    >
      <div className="mtf-selector">
        {canonical === null ? (
          <span className="mtf-loading">Loading…</span>
        ) : (
          <div className="mtf-chips">
            {canonical.map((tf) => {
              const isActive = active.has(tf);
              const isPending = pending.has(tf);
              return (
                <button
                  key={tf}
                  className={`selector-chip ${isActive ? "active" : ""}`}
                  onClick={() => void toggle(tf)}
                  disabled={isPending}
                  aria-pressed={isActive}
                  title={
                    isActive
                      ? `${tf} is active — click to deactivate`
                      : `${tf} is off — click to activate`
                  }
                >
                  {tf}
                  {isPending ? "…" : ""}
                </button>
              );
            })}
          </div>
        )}
        {error && <div className="mtf-error">{error}</div>}
        <div className="mtf-summary">
          {active.size === 0
            ? "No timeframes active. Risk gate will not aggregate."
            : `${active.size} active: ${[...active].sort().join(", ")}`}
        </div>
      </div>
    </GlassPanel>
  );
}
