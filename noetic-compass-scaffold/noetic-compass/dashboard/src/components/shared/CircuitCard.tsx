import type { ReactNode } from 'react';

interface CircuitNode {
  label: string;
  sublabel?: string;
  color?: string;
}

interface CircuitCardProps {
  title: string;
  operators: string;
  nodes: CircuitNode[];
  /** Optional feedback arrow from last node back to a node index */
  feedbackTo?: number;
  description: string;
  callout: string;
  calloutOperator: string;
  children?: ReactNode;
}

function NodeBox({ node, index }: { node: CircuitNode; index: number }) {
  const color = node.color ?? '#2dd4bf';
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="w-16 h-14 sm:w-20 sm:h-14 rounded-lg border flex flex-col items-center justify-center px-1"
        style={{ borderColor: `${color}40`, background: `${color}08` }}
      >
        <span className="text-[10px] font-bold" style={{ color }}>{node.label}</span>
        {node.sublabel && (
          <span className="text-[8px] text-slate-400 text-center leading-tight mt-0.5">{node.sublabel}</span>
        )}
      </div>
      <span className="text-[8px] text-slate-600">({index + 1})</span>
    </div>
  );
}

function Arrow() {
  return (
    <svg width="20" height="12" className="text-accent-teal/50 shrink-0 mx-0.5" viewBox="0 0 20 12">
      <path d="M0 6h14m-4-4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function CircuitCard({
  title,
  operators,
  nodes,
  feedbackTo,
  description,
  callout,
  calloutOperator,
}: CircuitCardProps) {
  return (
    <div className="glass-card p-5 space-y-4">
      {/* Header */}
      <div>
        <h4 className="text-sm font-semibold text-slate-100">{title}</h4>
        <p className="text-[10px] text-accent-teal/70 font-mono mt-0.5">{operators}</p>
      </div>

      {/* Circuit diagram */}
      <div className="relative">
        <div className="flex items-center justify-center gap-0.5 flex-wrap py-2">
          {nodes.map((node, i) => (
            <div key={i} className="flex items-center gap-0.5">
              <NodeBox node={node} index={i} />
              {i < nodes.length - 1 && <Arrow />}
            </div>
          ))}
        </div>

        {/* Feedback loop arrow */}
        {feedbackTo !== undefined && (
          <div className="flex justify-center mt-1">
            <div className="flex items-center gap-1.5 text-[9px] text-amber-400/70">
              <svg width="16" height="14" viewBox="0 0 16 14">
                <path d="M12 2C6 2 3 6 3 11m0 0l2.5-2.5M3 11l-2.5-2.5" fill="none" stroke="currentColor" strokeWidth="1" />
              </svg>
              feedback loop to ({feedbackTo + 1})
            </div>
          </div>
        )}
      </div>

      {/* Description */}
      <p className="text-[12px] text-slate-400 leading-relaxed">{description}</p>

      {/* Assessment callout */}
      <div className="rounded-lg border border-accent-teal/15 bg-accent-teal/[0.04] px-4 py-3">
        <p className="text-[11px] text-slate-300 leading-relaxed">
          <span className="font-semibold text-accent-teal">{calloutOperator} in assessment:</span>{' '}
          {callout}
        </p>
      </div>
    </div>
  );
}
