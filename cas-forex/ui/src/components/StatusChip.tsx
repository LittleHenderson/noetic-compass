/* ── CAS Forex — Status Chip ── */

interface StatusChipProps {
  label: string;
  variant: "success" | "warning" | "danger" | "info" | "muted" | "paper";
  size?: "sm" | "md";
}

const COLOR_MAP = {
  success: { bg: "var(--success-dim)", fg: "var(--success)" },
  warning: { bg: "var(--warning-dim)", fg: "var(--warning)" },
  danger: { bg: "var(--danger-dim)", fg: "var(--danger)" },
  info: { bg: "var(--accent-teal-dim)", fg: "var(--accent-teal)" },
  muted: { bg: "var(--border-subtle)", fg: "var(--text-muted)" },
  paper: { bg: "var(--paper-dim)", fg: "var(--paper)" },
};

export function StatusChip({ label, variant, size = "md" }: StatusChipProps) {
  const colors = COLOR_MAP[variant];
  const padding = size === "sm" ? "2px 8px" : "3px 10px";
  // On the type scale rather than the old 0.7/0.75rem pair, which rendered at
  // 11.2px/12px. This chip is used in 46 files and was the single largest
  // remaining source of sub-12px text after the global rescale.
  const fontSize = size === "sm" ? "var(--fs-xs)" : "var(--fs-sm)";

  return (
    <span
      className="status-chip"
      style={{
        background: colors.bg,
        color: colors.fg,
        padding,
        fontSize,
        borderRadius: "var(--radius-sm)",
        fontWeight: 600,
        letterSpacing: "0.03em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
      }}
    >
      {label}
    </span>
  );
}
