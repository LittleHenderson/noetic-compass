/* ── CAS Forex — Quick Start Item ── */

export type QuickStartStatus = "pending" | "running" | "done" | "error";

interface QuickStartItemProps {
  index: number;
  title: string;
  status: QuickStartStatus;
  detail: string;
  expanded: boolean;
  onToggle: () => void;
}

function statusLabel(status: QuickStartStatus): string {
  if (status === "done") return "DONE";
  if (status === "running") return "CHECKING";
  if (status === "error") return "NEEDS ACTION";
  return "PENDING";
}

export function QuickStartItem({
  index,
  title,
  status,
  detail,
  expanded,
  onToggle,
}: QuickStartItemProps) {
  return (
    <div
      className={`quick-start-item quick-start-item-${status} ${
        expanded ? "quick-start-item-expanded" : ""
      }`}
    >
      <button
        type="button"
        className="quick-start-item-header"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <span className="quick-start-item-index">{index}</span>
        <span className="quick-start-item-title">{title}</span>
        <span
          className={`quick-start-status-chip quick-start-status-${status}`}
        >
          {statusLabel(status)}
        </span>
        <span className="quick-start-item-caret" aria-hidden>
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {expanded && (
        <div className="quick-start-detail">
          <p>{detail}</p>
        </div>
      )}
    </div>
  );
}
