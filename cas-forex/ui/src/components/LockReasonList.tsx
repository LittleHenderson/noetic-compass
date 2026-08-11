/* ── CAS Forex — Lock Reason List ── */

import { StatusChip } from "./StatusChip";

interface LockReasonListProps {
  title: string;
  items: string[];
  variant?: "danger" | "warning";
}

export function LockReasonList({
  title,
  items,
  variant = "danger",
}: LockReasonListProps) {
  if (!items.length) return null;

  return (
    <div className="lock-reason-list">
      <div
        className="lock-reason-header"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 8,
        }}
      >
        <StatusChip
          label={variant === "danger" ? "BLOCKED" : "PENDING"}
          variant={variant}
          size="sm"
        />
        <span
          style={{
            fontSize: "0.875rem",
            fontWeight: 600,
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          {title}
        </span>
      </div>
      <ul className="lock-reason-items">
        {items.map((item, i) => (
          <li key={i} className="lock-reason-item">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
