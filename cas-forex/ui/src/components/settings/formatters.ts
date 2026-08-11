/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 2). */


export function formatIsoForDisplay(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}


export function formatUnknownValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  if (typeof value === "boolean") return value ? "YES" : "NO";
  if (value == null) return "UNSET";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}


export function formatYesNo(value: unknown): string {
  return value ? "YES" : "NO";
}


export function formatUsd(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "n/a";
  return `$${numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}


export function recordOrNull(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}


export function formatContractValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "NA";
  return formatUnknownValue(value);
}

// Grouped layout for the live-enable toggles. Keys map to the backend flags.


export function formatBrokerTruthReasonLabel(value: string): string {
  const labels: Record<string, string> = {
    terminal_position_reconciliation: "Terminal Reconciliation",
    live_open_positions_crosscheck: "Open Position Crosscheck",
    live_position_stop_loss_protection: "Stop-Loss Protection",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}


export function formatBrokerTruthReasonList(values: unknown): string {
  if (!Array.isArray(values) || values.length === 0) return "NONE";
  const labels = values
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .map((value) => formatBrokerTruthReasonLabel(value));
  return labels.length > 0 ? labels.join(", ") : "NONE";
}


export function formatDialBound(value: unknown): string {
  if (!value || typeof value !== "object") return "UNBOUNDED";
  const record = value as Record<string, unknown>;
  if (Array.isArray(record.allowed)) return record.allowed.join(", ");
  if ("min" in record || "max" in record) {
    const min = formatUnknownValue(record.min);
    const max = record.max === null || record.max === undefined ? "UNBOUNDED" : formatUnknownValue(record.max);
    return `${min} to ${max}`;
  }
  return JSON.stringify(value);
}

