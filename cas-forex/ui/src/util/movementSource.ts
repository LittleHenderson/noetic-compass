import type {
  MarketMovementQuote,
  MovementSourceTruthSnapshot,
  PositionMovement,
  LiveReadinessCheck,
} from "../types/evidence";

export type MovementSourceTone = "success" | "warning" | "danger" | "info" | "muted" | "paper";

export interface MovementSourceSummary {
  rawStatus: string;
  statusLabel: string;
  statusTone: MovementSourceTone;
  providerBackedCount: number;
  staticFallbackCount: number;
  mt5FallbackCount: number;
  providerLabel: string;
  hasStaticFallback: boolean;
  statusSummary: string;
  panelTitle: string;
  panelSubtitle: string;
  warningText: string | null;
}

export interface PositionFeedTruth {
  title: string;
  countLabel: string;
  label: string;
  detail: string;
  isLiveBroker: boolean;
}

export interface ReconciliationMovementTruthLike {
  movement_source_truth?: MovementSourceTruthSnapshot | null;
  movement_price_source_status?: string | null;
  movement_position_feed_label?: string | null;
  movement_position_feed_detail?: string | null;
}

export interface ReconciliationMovementTruthSummary {
  hasTruth: boolean;
  statusLabel: string;
  statusTone: MovementSourceTone;
  feedLabel: string;
  feedTone: MovementSourceTone;
  detail: string | null;
}

export interface MovementSourceLike {
  price_source_status?: string | null;
  price_source_label?: string | null;
  price_source_summary?: string | null;
  price_source_warning?: string | null;
  static_simulation_active?: boolean;
  position_feed_title?: string | null;
  position_feed_count_label?: string | null;
  position_feed_label?: string | null;
  position_feed_detail?: string | null;
  broker_ticket_position_count?: number;
  static_position_count?: number;
  static_quote_count?: number;
  provider_usable_symbols?: string[];
  static_fallback_symbols?: string[];
  mt5_fallback_symbols?: string[];
  provider_stale_symbols?: string[];
  provider_freshness_max_age_seconds?: number;
  snapshot_age_seconds_by_symbol?: Record<string, number | null>;
  market_data_provider_requested?: boolean;
  market_data_provider?: string | null;
  configured_market_data_provider?: string | null;
  provider_errors?: Record<string, string>;
  quotes?: Array<MarketMovementQuote | null | undefined>;
  positions?: Array<PositionMovement | null | undefined>;
}

const STATIC_SIMULATION_WARNING =
  "Static simulator rows are not being moved by usable provider/MT5 quotes right now; prices and floating P/L can remain unchanged at entry.";

function prettifyStatus(value: string): string {
  return value.replace(/_/g, " ");
}

function friendlyProviderName(value: string | null | undefined): string {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) return "provider";
  if (text === "YFinanceConnector") return "Yahoo";
  if (text === "OANDARestConnector") return "OANDA";
  if (text === "MT5TerminalMarketDataConnector") return "MT5 terminal";
  return text;
}

function positionFeedTone(label: string | undefined): MovementSourceTone {
  const upper = typeof label === "string" ? label.trim().toUpperCase() : "";
  if (upper === "LIVE MT5" || upper === "MT5 LIVE" || upper === "MT5 DEMO") return "success";
  if (upper === "SIM PROOF") return "warning";
  if (upper === "NONE" || upper === "UNKNOWN" || upper === "WARMING" || !upper) return "muted";
  return "info";
}

export function formatMovementSourceStatus(
  value: string | null | undefined,
  fallback = "UNKNOWN",
): string {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) return fallback;
  if (text === "STATIC_SIMULATION_FALLBACK") return "STATIC SIM";
  if (text === "MIXED_PROVIDER_AND_STATIC_FALLBACK") return "MIXED";
  if (text === "PROVIDER_ACTIVE") return "PROVIDER";
  if (text === "LEDGER_ONLY") return "LEDGER ONLY";
  if (text === "CACHE_WARMING") return "WARMING";
  return prettifyStatus(text);
}

export function movementSourceStatusTone(
  value: string | null | undefined,
  hasStaticFallback = false,
): MovementSourceTone {
  const text = typeof value === "string" ? value : "";
  if (hasStaticFallback || text.includes("STATIC")) return "warning";
  if (text === "PROVIDER_ACTIVE") return "success";
  return "muted";
}

export function formatMovementPositionSourceLabel(
  label: string | undefined,
  brokerTicket: string | null,
  priceSource: string | undefined,
): string {
  const source = priceSource ?? "";
  if (
    label === "MT5_LIVE_BROKER"
    || label === "MT5_DEMO_BROKER"
    || source === "mt5_terminal_api_verifier"
    || source === "mt5_live_account_snapshot"
    || source === "mt5_demo_account_snapshot"
  ) return label === "MT5_DEMO_BROKER" || source === "mt5_demo_account_snapshot" ? "MT5 DEMO" : "MT5 LIVE";
  const brokerBackedProofRow = Boolean(
    (typeof label === "string" && label.startsWith("PAPER_SIM_BROKER_TICKET"))
    || (brokerTicket && source !== "mt5_terminal_api_verifier"),
  );
  if (
    label === "PAPER_SIM_BROKER_TICKET_MT5_PRICED"
    || (brokerBackedProofRow && source.startsWith("provider_snapshot:MT5TerminalMarketDataConnector"))
  ) {
    return "SIM TICKET+MT5";
  }
  if (
    label === "PAPER_SIM_BROKER_TICKET_PROVIDER_PRICED"
    || (brokerBackedProofRow && source.startsWith("provider_snapshot:"))
  ) {
    return "SIM TICKET+QUOTE";
  }
  if (
    label === "PAPER_SIM_BROKER_TICKET_STATIC"
    || (brokerBackedProofRow && source.startsWith("paper_route_snapshot"))
  ) {
    return "SIM TICKET STATIC";
  }
  if (brokerBackedProofRow) return "SIM TICKET";
  if (source.startsWith("provider_snapshot:MT5TerminalMarketDataConnector") || label === "PAPER_SIM_MT5_PRICED") {
    return "SIM+MT5";
  }
  if (source.startsWith("provider_snapshot:")) return "SIM+QUOTE";
  if (label === "PAPER_SIM_STATIC") return "SIM STATIC";
  if (label === "PAPER_SIM_PROVIDER_PRICED") return "SIM+QUOTE";
  return "SIM";
}

export function isStaticMovementPosition(
  position: {
    price_source?: string | null;
    price_stale?: boolean | null;
    position_source_label?: string | null;
  } | null | undefined,
): boolean {
  const source = position?.price_source ?? "";
  return Boolean(
    position?.price_stale
    || source.startsWith("paper_route_snapshot")
    || position?.position_source_label === "PAPER_SIM_STATIC",
  );
}

export function isStaticMovementQuote(
  quote: MarketMovementQuote | null | undefined,
  position?: PositionMovement | null | undefined,
): boolean {
  if (quote?.stale) return true;
  return isStaticMovementPosition(position);
}

export function formatMovementPositionAge(
  position: Pick<PositionMovement, "age_days" | "age_seconds"> | null | undefined,
): string {
  const ageDays = position?.age_days;
  if (typeof ageDays !== "number" || Number.isNaN(ageDays)) return "n/a";
  if (ageDays >= 1) return `${ageDays.toFixed(ageDays >= 10 ? 0 : 1)}d`;
  const seconds = position?.age_seconds ?? 0;
  const hours = seconds / 3600;
  if (hours >= 1) return `${hours.toFixed(hours >= 10 ? 0 : 1)}h`;
  const minutes = Math.max(0, Math.round(seconds / 60));
  return `${minutes}m`;
}

export function summarizeMovementSource(
  movement: MovementSourceLike | null | undefined,
): MovementSourceSummary {
  const rawStatus = movement?.price_source_status ?? "UNKNOWN";
  const backendStatusLabel = typeof movement?.price_source_label === "string"
    ? movement.price_source_label.trim()
    : "";
  const backendStatusSummary = typeof movement?.price_source_summary === "string"
    ? movement.price_source_summary.trim()
    : "";
  const backendWarning = typeof movement?.price_source_warning === "string"
    ? movement.price_source_warning.trim()
    : "";
  const providerBackedCount = movement?.provider_usable_symbols?.length ?? 0;
  const staticFallbackCount = movement?.static_fallback_symbols?.length ?? 0;
  const mt5FallbackCount = movement?.mt5_fallback_symbols?.length ?? 0;
  const providerStaleSymbols = movement?.provider_stale_symbols ?? [];
  const providerStaleCount = providerStaleSymbols.length;
  const freshnessMax = movement?.provider_freshness_max_age_seconds;
  const staticPositionCount = movement?.static_position_count ?? 0;
  const staticQuoteCount = movement?.static_quote_count ?? 0;
  const hasStaticFallback = Boolean(movement?.static_simulation_active)
    || staticFallbackCount > 0
    || staticQuoteCount > 0
    || staticPositionCount > 0
    || Boolean(movement?.quotes?.some((quote) => Boolean(quote?.stale)))
    || Boolean(movement?.positions?.some((position) => isStaticMovementPosition(position)));
  const configuredProvider = movement?.configured_market_data_provider ?? movement?.market_data_provider;
  const providerLabelBase = friendlyProviderName(configuredProvider);
  const providerLabel = movement?.market_data_provider_requested
    ? mt5FallbackCount > 0 && providerLabelBase !== "MT5 terminal"
      ? `${providerLabelBase} + MT5 fallback`
      : providerLabelBase
    : "not requested";
  const derivedSummary = hasStaticFallback
    ? "paper/demo ledger with static simulator fallback; provider or MT5 prices are not moving every row"
    : mt5FallbackCount > 0
      ? "paper/demo ledger with provider-backed movement; MT5 terminal fallback is repricing some rows"
      : "paper/demo ledger with provider-backed movement where available";
  const staleSuffix = providerStaleCount > 0
    ? ` stale provider/MT5 snapshots rejected for ${providerStaleSymbols.join(", ")}${typeof freshnessMax === "number" ? `; max age ${freshnessMax}s` : ""}`
    : "";
  const derivedWarning = hasStaticFallback
    ? `${STATIC_SIMULATION_WARNING}${staleSuffix ? ` ${staleSuffix}.` : ""}`
    : staleSuffix
      ? `${staleSuffix}.`
      : null;

  return {
    rawStatus,
    statusLabel: backendStatusLabel || formatMovementSourceStatus(rawStatus),
    statusTone: movementSourceStatusTone(rawStatus, hasStaticFallback),
    providerBackedCount,
    staticFallbackCount,
    mt5FallbackCount,
    providerLabel,
    hasStaticFallback,
    statusSummary: backendStatusSummary || `${derivedSummary}${staleSuffix ? `;${staleSuffix}` : ""}`,
    panelTitle: hasStaticFallback ? "Movement Source: Static Simulation" : "Movement Source",
    panelSubtitle: backendStatusSummary || `${derivedSummary}${staleSuffix ? `;${staleSuffix}` : ""}`,
    warningText: backendWarning || derivedWarning,
  };
}

export function describeMovementPositionFeed(
  movement: MovementSourceLike | null | undefined,
  accountSource?: string | null,
): PositionFeedTruth {
  const summary = summarizeMovementSource(movement);
  const backendTitle = typeof movement?.position_feed_title === "string"
    ? movement.position_feed_title.trim()
    : "";
  const backendCountLabel = typeof movement?.position_feed_count_label === "string"
    ? movement.position_feed_count_label.trim()
    : "";
  const backendLabel = typeof movement?.position_feed_label === "string"
    ? movement.position_feed_label.trim()
    : "";
  const backendDetail = typeof movement?.position_feed_detail === "string"
    ? movement.position_feed_detail.trim()
    : "";
  if ((accountSource ?? "") === "mt5_live" || (accountSource ?? "") === "mt5_demo") {
    const demo = accountSource === "mt5_demo";
    return {
      title: backendTitle || "MT5 Open Positions",
      countLabel: backendCountLabel || "Open positions",
      label: backendLabel || (demo ? "MT5 DEMO" : "MT5 LIVE"),
      detail: backendDetail || `Rows in this table are mirrored from the connected MT5 ${demo ? "demo" : "live"} account and represent live MT5 broker positions.`,
      isLiveBroker: true,
    };
  }
  if (backendLabel || backendDetail || backendTitle || backendCountLabel) {
    return {
      title: backendTitle || "Simulator Proof Rows",
      countLabel: backendCountLabel || "Simulator rows",
      label: backendLabel || "paper/demo simulator proof rows",
      detail: backendDetail || "Rows in this table are simulator proof rows, not live MT5 terminal positions.",
      isLiveBroker: ["LIVE MT5", "MT5 LIVE", "MT5 DEMO"].includes(backendLabel.toUpperCase()),
    };
  }
  if (summary.hasStaticFallback) {
    return {
      title: "Simulator Proof Rows",
      countLabel: "Simulator rows",
      label: "paper/demo simulator proof rows with static stale pricing",
      detail: `Rows in this table are simulator proof rows, not live MT5 terminal positions. ${summary.warningText ?? STATIC_SIMULATION_WARNING}`,
      isLiveBroker: false,
    };
  }
  if (summary.mt5FallbackCount > 0) {
    return {
      title: "Simulator Proof Rows",
      countLabel: "Simulator rows",
      label: "paper/demo simulator proof rows with provider quotes and MT5 repricing fallback",
      detail: "Rows in this table are simulator proof rows, not live MT5 terminal positions. Quotes/P&L move only when usable provider prices or MT5 terminal fallback quotes are available.",
      isLiveBroker: false,
    };
  }
  if (summary.providerBackedCount > 0) {
    return {
      title: "Simulator Proof Rows",
      countLabel: "Simulator rows",
      label: "paper/demo simulator proof rows with provider-backed pricing where available",
      detail: "Rows in this table are simulator proof rows, not live MT5 terminal positions. Quotes/P&L move only when usable provider prices are available.",
      isLiveBroker: false,
    };
  }
  return {
    title: "Simulator Proof Rows",
    countLabel: "Simulator rows",
    label: "paper/demo simulator proof rows",
    detail: "Rows in this table are simulator proof rows, not live MT5 terminal positions.",
    isLiveBroker: false,
  };
}

export function describeReconciliationMovementTruth(
  reconciliation: ReconciliationMovementTruthLike | null | undefined,
): ReconciliationMovementTruthSummary {
  const truth = reconciliation?.movement_source_truth;
  const rawStatus = typeof truth?.price_source_status === "string"
    ? truth.price_source_status.trim()
    : typeof reconciliation?.movement_price_source_status === "string"
      ? reconciliation.movement_price_source_status.trim()
      : "";
  const backendLabel = typeof truth?.price_source_label === "string"
    ? truth.price_source_label.trim()
    : "";
  const feedLabel = typeof truth?.position_feed_label === "string"
    ? truth.position_feed_label.trim()
    : typeof reconciliation?.movement_position_feed_label === "string"
      ? reconciliation.movement_position_feed_label.trim()
      : "";
  const detail = typeof truth?.position_feed_detail === "string"
    ? truth.position_feed_detail.trim()
    : typeof truth?.detail === "string"
      ? truth.detail.trim()
      : typeof reconciliation?.movement_position_feed_detail === "string"
        ? reconciliation.movement_position_feed_detail.trim()
        : "";
  const hasStaticFallback = Boolean(truth?.static_simulation_active)
    || rawStatus.includes("STATIC")
    || /static/i.test(detail);

  return {
    hasTruth: Boolean(rawStatus || feedLabel || detail),
    statusLabel: backendLabel || formatMovementSourceStatus(rawStatus || undefined, "SOURCE WARMING"),
    statusTone: movementSourceStatusTone(rawStatus || undefined, hasStaticFallback),
    feedLabel: feedLabel || "WARMING",
    feedTone: positionFeedTone(feedLabel || undefined),
    detail: detail || null,
  };
}

export function detailEvidenceForLiveReadinessCheck(
  check: LiveReadinessCheck | null | undefined,
): string {
  if (!check || check.gate_id !== "movement_price_source_truth") return "";
  const evidence = Array.isArray(check.evidence) ? check.evidence : [];
  return (
    evidence.find((value) => {
      if (typeof value !== "string") return false;
      const trimmed = value.trim();
      if (!trimmed) return false;
      return !trimmed.startsWith("price_source_status=") && !trimmed.startsWith("position_feed_label=");
    }) ?? ""
  );
}
