const OPERATOR_LABELS = [
  'CO-0 Identity', 'CO-1 Attention', 'CO-2 Affinity', 'CO-3 Aversion',
  'CO-4 Intensity', 'CO-5 Integration', 'CO-6 Assertion', 'CO-7 Pattern',
  'CO-8 Initiation', 'CO-9 Consequence',
];

const DOMAIN_LABELS = ['P Principled', 'C Cognitive', 'E Evaluative', 'O Operational'];

const DRIVE_LABELS = [
  'F1 Unity', 'F2 Wisdom', 'F3 Vitality', 'F4 Connection',
  'F5 Agency', 'F6 Structure', 'F7 Purpose',
];

function heatColor(value: number, max: number): string {
  const ratio = Math.min(1, value / max);
  if (ratio < 0.01) return 'bg-white/[0.02]';
  if (ratio < 0.2) return 'bg-accent-teal/10';
  if (ratio < 0.4) return 'bg-accent-teal/20';
  if (ratio < 0.6) return 'bg-accent-teal/30';
  if (ratio < 0.8) return 'bg-accent-teal/50';
  return 'bg-accent-teal/70';
}

function textColor(value: number, max: number): string {
  const ratio = Math.min(1, value / max);
  if (ratio < 0.01) return 'text-slate-700';
  if (ratio < 0.4) return 'text-slate-400';
  return 'text-slate-100';
}

interface HeatRowProps {
  label: string;
  value: number;
  max: number;
}

function HeatCell({ label, value, max }: HeatRowProps) {
  const bg = heatColor(value, max);
  const fg = textColor(value, max);
  const shortLabel = label.split(' ').slice(0, 1)[0];
  return (
    <div
      className={`rounded px-1.5 py-1 text-center ${bg} transition-colors duration-200`}
      title={`${label}: ${value.toFixed(1)}`}
    >
      <span className={`block text-[8px] font-mono ${fg} leading-none`}>{shortLabel}</span>
      <span className={`block text-[10px] font-semibold ${fg} mt-0.5`}>
        {value > 0 ? value.toFixed(1) : ''}
      </span>
    </div>
  );
}

interface SignalHeatmapProps {
  operatorScores: number[];
  domainScores: number[];
  driveScores: number[];
  rpmSignal: number;
}

export function SignalHeatmap({ operatorScores, domainScores, driveScores, rpmSignal }: SignalHeatmapProps) {
  const hasAnySignal = [...operatorScores, ...domainScores, ...driveScores, rpmSignal].some(v => v > 0);

  if (!hasAnySignal) return null;

  return (
    <div className="space-y-2">
      <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-600">Signal Breakdown</p>

      {/* Operators (0-10 scale) */}
      <div>
        <p className="text-[8px] uppercase tracking-wider text-slate-600 mb-1">Operators</p>
        <div className="grid grid-cols-10 gap-0.5">
          {operatorScores.map((score, i) => (
            <HeatCell key={`op-${i}`} label={OPERATOR_LABELS[i]} value={score} max={10} />
          ))}
        </div>
      </div>

      {/* Domains (0-1 scale) + Drives (0-1 scale) side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[8px] uppercase tracking-wider text-slate-600 mb-1">Domains</p>
          <div className="grid grid-cols-4 gap-0.5">
            {domainScores.map((score, i) => (
              <HeatCell key={`dom-${i}`} label={DOMAIN_LABELS[i]} value={score} max={1} />
            ))}
          </div>
        </div>
        <div>
          <p className="text-[8px] uppercase tracking-wider text-slate-600 mb-1">Drives</p>
          <div className="grid grid-cols-7 gap-0.5">
            {driveScores.map((score, i) => (
              <HeatCell key={`drv-${i}`} label={DRIVE_LABELS[i]} value={score} max={1} />
            ))}
          </div>
        </div>
      </div>

      {/* RPM signal */}
      {rpmSignal > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-[8px] uppercase tracking-wider text-slate-600">RPM</span>
          <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full bg-amber-500/60 transition-all duration-300"
              style={{ width: `${Math.min(100, rpmSignal * 100)}%` }}
            />
          </div>
          <span className="text-[9px] font-mono text-slate-500">{rpmSignal.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}
