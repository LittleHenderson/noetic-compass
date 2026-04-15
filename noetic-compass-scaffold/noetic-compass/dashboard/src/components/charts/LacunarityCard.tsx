const OP_NAMES = [
  'Generative Potential', 'Directed Attention', 'Attraction', 'Critical Evaluation',
  'Encoding Intensity', 'Receptive Integration', 'Projective Assertion',
  'Pattern Entrainment', 'Causal Reasoning', 'Consequential Grounding',
];
const DRIVE_NAMES = ['Unity', 'Wisdom', 'Vitality', 'Connection', 'Agency', 'Structure', 'Purpose'];

interface GapMap {
  absent_operators: number[];
  absent_domains: string[];
  absent_drives: number[];
  strongest_cluster: number[];
  largest_void: string;
}

interface LacunarityProfile {
  state: number;
  fractal: number;
  domain: number;
  drive: number;
  rpm_resolution: number;
  composite: number;
  classification: string;
  gap_map: GapMap;
}

function barColor(value: number): string {
  if (value < 0.5) return 'bg-emerald-500/60';
  if (value < 1.5) return 'bg-amber-500/60';
  if (value < 3.0) return 'bg-orange-500/60';
  return 'bg-red-500/60';
}

function classColor(cls: string): string {
  if (cls === 'Uniform') return 'text-emerald-400';
  if (cls === 'Moderate') return 'text-amber-400';
  if (cls === 'Concentrated') return 'text-orange-400';
  return 'text-red-400';
}

function LacBar({ label, value, maxVal = 3.0 }: { label: string; value: number; maxVal?: number }) {
  const pct = Math.min(100, (value / maxVal) * 100);
  return (
    <div className="flex items-center gap-2 text-[10px]">
      <span className="w-20 text-slate-400 shrink-0">{label}</span>
      <div className="flex-1 h-2.5 rounded-full bg-white/[0.04] overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor(value)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right text-slate-500 font-mono">{value.toFixed(2)}</span>
    </div>
  );
}

export function LacunarityCard({ profile }: { profile: LacunarityProfile }) {
  const gm = profile.gap_map;

  return (
    <div className="space-y-4">
      {/* Composite */}
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Composite</span>
        <span className={`text-lg font-bold ${classColor(profile.classification)}`}>
          {profile.composite.toFixed(2)}
        </span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full ${
          profile.classification === 'Uniform' ? 'bg-emerald-500/10 text-emerald-400' :
          profile.classification === 'Moderate' ? 'bg-amber-500/10 text-amber-400' :
          profile.classification === 'Concentrated' ? 'bg-orange-500/10 text-orange-400' :
          'bg-red-500/10 text-red-400'
        }`}>
          {profile.classification}
        </span>
      </div>

      {/* Dimension bars */}
      <div className="space-y-1.5">
        <LacBar label="Operator" value={profile.state} />
        <LacBar label="Fractal" value={profile.fractal} maxVal={1.0} />
        <LacBar label="Domain" value={profile.domain} maxVal={1.0} />
        <LacBar label="Drive" value={profile.drive} maxVal={1.0} />
        <LacBar label="RPM Resol." value={profile.rpm_resolution} maxVal={1.0} />
      </div>

      {/* Gap Map */}
      <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 space-y-2">
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Gap Map</p>

        {/* 10-dot operator X-ray */}
        <div className="flex justify-center gap-1.5 py-1">
          {Array.from({ length: 10 }, (_, i) => {
            const present = !gm.absent_operators.includes(i);
            const strong = gm.strongest_cluster.includes(i);
            return (
              <div
                key={i}
                className={`w-4 h-4 rounded-full border transition-all ${
                  strong ? 'bg-accent-teal/60 border-accent-teal/80 shadow-[0_0_6px_rgba(45,212,191,0.3)]' :
                  present ? 'bg-slate-500/30 border-slate-500/40' :
                  'bg-transparent border-slate-700/30'
                }`}
                title={`CO-${i}: ${OP_NAMES[i]}${strong ? ' (concentrated)' : present ? '' : ' (absent)'}`}
              />
            );
          })}
        </div>

        {gm.absent_operators.length > 0 && (
          <p className="text-[10px] text-slate-400">
            <span className="text-red-400/70">Absent operators:</span>{' '}
            {gm.absent_operators.map(i => `CO-${i}`).join(', ')}
          </p>
        )}
        {gm.absent_domains.length > 0 && (
          <p className="text-[10px] text-slate-400">
            <span className="text-red-400/70">Absent domains:</span>{' '}
            {gm.absent_domains.join(', ')}
          </p>
        )}
        {gm.absent_drives.length > 0 && (
          <p className="text-[10px] text-slate-400">
            <span className="text-red-400/70">Absent drives:</span>{' '}
            {gm.absent_drives.map(i => `F${i} ${DRIVE_NAMES[i - 1] ?? ''}`).join(', ')}
          </p>
        )}
        {gm.strongest_cluster.length > 0 && (
          <p className="text-[10px] text-slate-400">
            <span className="text-accent-teal">Concentration:</span>{' '}
            {gm.strongest_cluster.map(i => `CO-${i} ${OP_NAMES[i]}`).join(', ')}
          </p>
        )}
        <p className="text-[10px] text-slate-500 italic">{gm.largest_void}</p>
      </div>
    </div>
  );
}
