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
  paper: { bg: "#3b1f6e", fg: "var(--paper)" },
};

export function StatusChip({ label, variant, size = "md" }: StatusChipProps) {
  const colors = COLOR_MAP[variant];
  const padding = size === "sm" ? "1px 6px" : "2px 10px";
  const fontSize = size === "sm" ? "0.7rem" : "0.75rem";

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
