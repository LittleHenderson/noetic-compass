/* ── CAS Forex — Trading Windows (2×2 live chart cockpit) ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { TradingWindow, type WindowRole } from "../components/TradingWindow";
import { fetchChartSymbols } from "../data/api";
import type { DashboardState } from "../types/evidence";

interface WindowsPageProps {
  state: DashboardState;
}

const FALLBACK_SYMBOLS = ["EUR/USD", "XAU/USD", "GBP/USD", "USD/JPY"];
const FALLBACK_TIMEFRAMES = ["M1", "M5", "M15", "H1", "D1"];

export function WindowsPage({ state }: WindowsPageProps) {
  const [symbols, setSymbols] = useState<string[]>(FALLBACK_SYMBOLS);
  const [timeframes, setTimeframes] = useState<string[]>(FALLBACK_TIMEFRAMES);

  useEffect(() => {
    void fetchChartSymbols().then((s) => {
      if (s && s.symbols.length) setSymbols(s.symbols);
      if (s && s.timeframes.length) setTimeframes(s.timeframes);
    });
  }, []);

  // Strategy windows default to the top strategy leads / Fury replay candidates,
  // falling back to sensible majors when those aren't available.
  const leadSymbols = (state.strategyLeads ?? [])
    .flatMap((l) => l.symbols_promoted_for_next_tests ?? [])
    .filter((s) => symbols.includes(s));
  const furySymbols = (state.forexFuryReplayCandidates?.candidates ?? [])
    .filter((c) => c.symbol_supported)
    .map((c) => c.cas_symbol)
    .filter((s) => symbols.includes(s));
  const stratA = leadSymbols[0] ?? furySymbols[0] ?? "GBP/USD";
  const stratB = leadSymbols[1] ?? furySymbols[1] ?? "USD/JPY";

  const panes: { role: WindowRole; symbol: string; brokerFeedConnected: boolean }[] = [
    { role: "Live", symbol: "EUR/USD", brokerFeedConnected: false },
    { role: "Demo", symbol: "XAU/USD", brokerFeedConnected: false },
    { role: "Strategy A", symbol: stratA, brokerFeedConnected: false },
    { role: "Strategy B", symbol: stratB, brokerFeedConnected: false },
  ];

  return (
    <div className="windows-page">
      <GlassPanel
        title="Trading Windows"
        subtitle="Four live-ish chart panes — watch what the CAS agents are tracking; optional manual controls"
      >
        <div className="windows-intro">
          Near-real-time market data (delayed retail feed, not a pro tick stream). “Live”
          needs a connected broker feed — none is running yet, so it shows market data and is
          labelled accordingly. Buy/Sell route a 0.01-lot order through the <strong>gated</strong> dispatch,
          so they are <strong>paper-safe by default</strong> and can only reach a live broker once the owner
          authorizes live trading. Pause stops that pane’s polling.
        </div>
      </GlassPanel>

      <div className="windows-grid">
        {panes.map((p) => (
          <TradingWindow
            key={p.role}
            role={p.role}
            defaultSymbol={p.symbol}
            symbols={symbols}
            timeframes={timeframes}
            brokerFeedConnected={p.brokerFeedConnected}
          />
        ))}
      </div>
    </div>
  );
}
