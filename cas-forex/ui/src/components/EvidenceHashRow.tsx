/* ── CAS Forex — Evidence Hash Row ── */

import type { ReactNode } from "react";

interface EvidenceHashRowProps {
  label: string;
  value: string;
  verified: boolean;
  icon?: ReactNode;
}

export function EvidenceHashRow({
  label,
  value,
  verified,
  icon,
}: EvidenceHashRowProps) {
  return (
    <div className="hash-row">
      <div className="hash-row-left">
        {icon && <span className="hash-row-icon">{icon}</span>}
        <span className="hash-row-label">{label}</span>
      </div>
      <div className="hash-row-right">
        <code className="hash-row-value">{value}</code>
        <span
          className="hash-row-badge"
          style={{
            color: verified ? "var(--success)" : "var(--danger)",
            fontSize: "0.7rem",
            fontWeight: 600,
          }}
        >
          {verified ? "✓" : "✗"}
        </span>
      </div>
    </div>
  );
}
