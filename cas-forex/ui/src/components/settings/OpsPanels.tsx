/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 2). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { BrokerSymbolDiagnostics, EconomicCalendarFeedReport, RuntimeTopologyStatus, fetchEconomicCalendarFeed, fetchMt5SymbolDiagnostics, fetchRuntimeTopology, getApiBase, resetApiBase, setApiBase } from "../../data/api";
import { formatContractValue } from "./formatters";
import { useEffect, useState } from "react";

type BrokerSymbolRow = NonNullable<BrokerSymbolDiagnostics["symbols"]>[number];

export function EconomicCalendarPanel() {
  const [report, setReport] = useState<EconomicCalendarFeedReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchEconomicCalendarFeed();
    if (next) {
      setReport(next);
    } else {
      setStatus("Economic calendar status unavailable - is the API reachable?");
    }
  }

  const configured = report?.configured === true;
  const loaded = report?.status === "LOADED" || report?.status === "CACHE_FRESH" || report?.status === "CACHE_FRESH_AFTER_REFRESH_ERROR";
  const attention = configured && !loaded;
  const events = report?.events ?? [];

  return (
    <GlassPanel title="Economic Calendar Feed" subtitle="External macro-event source for dispatch blackout checks">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={loaded ? "success" : attention ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={configured ? "FEED CONFIGURED" : "STATIC FALLBACK"}
          variant={configured ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`${report?.event_count ?? 0} EVENTS`}
          variant={(report?.event_count ?? 0) ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.fail_closed_on_error ? "FAIL CLOSED" : "NO FAIL-CLOSED"}
          variant={report?.fail_closed_on_error ? "success" : "muted"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Source" value={report?.source || "Not configured"} mono danger={!configured} description={report?.detail ?? "Economic calendar feed status is loading."} />
        <ControlField label="Cache" value={report?.cache_path || "runtime/economic_calendar"} mono danger={report?.cache_stale === true} description={typeof report?.cache_age_seconds === "number" ? `${Math.round(report.cache_age_seconds)}s old, ttl ${report.cache_ttl_seconds ?? 0}s` : "No cache age loaded."} />
        <ControlField label="Unusable Rows" value={`${report?.unusable_event_count ?? 0}`} mono danger={Boolean(report?.unusable_event_count)} description={`${report?.raw_event_count ?? 0} raw event row(s) inspected.`} />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Impact</th>
              <th>Currency</th>
              <th>Scheduled</th>
            </tr>
          </thead>
          <tbody>
            {events.slice(0, 6).map((event, index) => (
              <tr key={`${String(event.event_id ?? "event")}-${index}`}>
                <td>{String(event.name ?? event.event_type ?? "macro event")}</td>
                <td>{String(event.impact ?? "HIGH")}</td>
                <td>{String(event.currency ?? "USD")}</td>
                <td className="mono">{String(event.scheduled_at_utc ?? "")}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={4}>No configured external events loaded; dispatch will label fallback/static calendar evidence.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh calendar status</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Economic calendar feed status is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}


export function RuntimeTopologyPanel() {
  const [report, setReport] = useState<RuntimeTopologyStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      const next = await fetchRuntimeTopology();
      if (!cancelled && next) setReport(next);
    }
    void refresh();
    const intervalId = window.setInterval(() => void refresh(), 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const accepted = report?.claim_status === "ACCEPT";
  return (
    <GlassPanel
      title="Runtime Process Topology"
      subtitle="Single ownership for Operator, dispatch, proof loops, and process-local state"
      variant={accepted ? "default" : "warning"}
    >
      <div className="dashboard-grid-3col">
        <ControlField label="Topology" value={report?.status ?? "WARMING"} danger={Boolean(report && !accepted)} mono />
        <ControlField label="API Workers" value={`${report?.api_worker_count ?? 0} / ${report?.supported_api_worker_count ?? 1}`} danger={Boolean(report && report.api_worker_count !== 1)} mono />
        <ControlField label="Runtime Owner" value={report?.runtime_owner ? `PID ${report.runtime_owner_pid}` : "NOT OWNED"} danger={Boolean(report && !report.runtime_owner)} mono />
        <ControlField label="Control Plane" value={report?.stateful_control_plane_enabled ? "ENABLED" : "BLOCKED"} danger={Boolean(report && !report.stateful_control_plane_enabled)} />
        <ControlField label="LAN / Phone" value={report?.lan_phone_supported ? "SUPPORTED" : "BLOCKED"} danger={Boolean(report && !report.lan_phone_supported)} />
        <ControlField label="Multi-worker" value={report?.multi_worker_supported ? "SUPPORTED" : "REFUSED"} danger={false} />
      </div>
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        Process-local components: {(report?.process_local_components ?? []).join(", ") || "status warming"}.
      </div>
      <div className="control-field-desc" style={{ marginTop: 4 }}>
        {report?.claim_boundary ?? "Runtime topology status is warming."}
      </div>
    </GlassPanel>
  );
}



export function MobileApiPanel() {
  const [apiBase, setApiBaseInput] = useState(() => getApiBase());
  const [saved, setSaved] = useState(false);

  const save = () => {
    setApiBase(apiBase);
    setSaved(true);
  };

  const reset = () => {
    resetApiBase();
    setApiBaseInput(getApiBase());
    setSaved(true);
  };

  return (
    <GlassPanel title="Phone / APK Connection" subtitle="Point this app at the CAS Forex API reachable from your phone">
      <div className="mobile-api-row">
        <input
          className="mobile-api-input"
          value={apiBase}
          onChange={(e) => {
            setApiBaseInput(e.target.value);
            setSaved(false);
          }}
          placeholder="http://192.168.1.50:8765/api/forex"
          spellCheck={false}
        />
        <button className="mobile-api-button" type="button" onClick={save}>Save</button>
        <button className="mobile-api-button ghost" type="button" onClick={reset}>Reset</button>
      </div>
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        For a phone, use your computer's LAN/VPN/tunnel address, e.g. <code>http://192.168.x.x:8765/api/forex</code>.
        <strong> Do not use 127.0.0.1 on the phone</strong> unless the API is running on the phone itself.
        {saved && <span style={{ color: "var(--success)", marginLeft: 8 }}>Saved. Refresh or reopen the app to reload live evidence.</span>}
      </div>
    </GlassPanel>
  );
}


export function BrokerSymbolDiagnosticsPanel() {
  const [symbolsText, setSymbolsText] = useState("EUR/USD,XAU/USD,US30,NAS100");
  const [report, setReport] = useState<BrokerSymbolDiagnostics | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  function requestedSymbols(): string[] {
    return symbolsText
      .split(/[\s,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function refresh() {
    setStatus("");
    const next = await fetchMt5SymbolDiagnostics(requestedSymbols());
    if (next) {
      setReport(next);
    } else {
      setStatus("Broker symbol diagnostics unavailable - is the API reachable and MT5 open?");
    }
  }

  const rows = report?.symbols ?? [];
  const unresolved = report?.unresolved_symbols ?? [];

  return (
    <GlassPanel title="Broker Symbol Diagnostics" subtitle="MT5 symbol mapping and contract constraints">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.mt5_connected ? "MT5 CONNECTED" : "MT5 NOT CONNECTED"}
          variant={report?.mt5_connected ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`${unresolved.length} UNRESOLVED`}
          variant={unresolved.length ? "warning" : "success"}
          size="sm"
        />
      </div>
      <div className="mobile-api-row" style={{ marginBottom: 10 }}>
        <input
          className="mobile-api-input"
          value={symbolsText}
          onChange={(event) => setSymbolsText(event.target.value)}
          placeholder="EUR/USD,XAU/USD,US30,NAS100"
          spellCheck={false}
        />
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh symbols</button>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>CAS Symbol</th>
              <th>Broker Symbol</th>
              <th>Status</th>
              <th>Lot Rules</th>
              <th>Stops</th>
              <th>Tick</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: BrokerSymbolRow) => {
              const constraints = row.broker_contract_constraints ?? {};
              return (
                <tr key={`${row.canonical_symbol ?? "symbol"}-${row.selected_symbol ?? "unresolved"}`}>
                  <td className="mono">{row.canonical_symbol ?? "unknown"}</td>
                  <td>
                    <div className="ai-dial-name mono">{row.selected_symbol ?? "unresolved"}</div>
                    <div className="ai-dial-key">{row.resolution_source ?? "no source"}</div>
                  </td>
                  <td>
                    <StatusChip
                      label={row.diagnostic_status ?? row.status ?? "UNKNOWN"}
                      variant={row.status === "RESOLVED" ? "success" : "warning"}
                      size="sm"
                    />
                  </td>
                  <td className="mono">
                    {formatContractValue(constraints.min_lot)} / {formatContractValue(constraints.max_lot)}
                    {" step "}
                    {formatContractValue(constraints.lot_step)}
                  </td>
                  <td className="mono">
                    stop {formatContractValue(constraints.stop_level_points)}
                    {" / freeze "}
                    {formatContractValue(constraints.freeze_level_points)}
                  </td>
                  <td className="mono">
                    size {formatContractValue(constraints.tick_size)}
                    {" / value "}
                    {formatContractValue(constraints.tick_value)}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>No broker symbol diagnostics loaded.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {unresolved.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          Unresolved: {unresolved.join(", ")}. Configure broker symbol overrides or keep MT5 open so discovery can run.
        </div>
      )}
      {status && <div className="control-field-desc" style={{ marginTop: 8, color: "var(--danger)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {report?.claim_boundary ?? "Symbol diagnostics are read-only and do not place orders or change trading authority."}
      </div>
    </GlassPanel>
  );
}

