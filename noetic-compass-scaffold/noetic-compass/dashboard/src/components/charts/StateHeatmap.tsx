import { Fragment, useMemo, useRef, useState } from 'react';
import { DOMAIN_SHORT, OPERATOR_SHORT } from '../../lib/constants';
import { ExplainPanel } from '../shared/ExplainPanel';
import { interpretState } from '../../lib/interpretations';

/* ── Thermal color mapping ─────────────────────────────────────────── */

interface HeatStyle {
  bg: string;
  glow: string;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpColor(c1: [number, number, number], c2: [number, number, number], t: number): string {
  return `rgb(${Math.round(lerp(c1[0], c2[0], t))},${Math.round(lerp(c1[1], c2[1], t))},${Math.round(lerp(c1[2], c2[2], t))})`;
}

const STOPS: { at: number; rgb: [number, number, number]; glow: string }[] = [
  { at: 0.0,  rgb: [15, 23, 42],    glow: 'none' },                                        // near-black navy
  { at: 0.2,  rgb: [30, 58, 95],    glow: 'none' },                                        // dark blue
  { at: 0.4,  rgb: [26, 82, 118],   glow: 'none' },                                        // deep teal
  { at: 0.55, rgb: [30, 122, 138],  glow: '0 0 6px rgba(45,212,191,0.2)' },                // teal
  { at: 0.7,  rgb: [45, 212, 191],  glow: '0 0 8px rgba(45,212,191,0.35)' },               // cyan
  { at: 0.8,  rgb: [251, 191, 36],  glow: '0 0 10px rgba(251,191,36,0.35)' },              // amber
  { at: 0.9,  rgb: [245, 158, 11],  glow: '0 0 14px rgba(245,158,11,0.45)' },              // bright amber
  { at: 1.0,  rgb: [254, 243, 199], glow: '0 0 18px rgba(254,243,199,0.5), 0 0 6px rgba(251,191,36,0.3)' }, // hot white-gold
];

function heatColor(intensity: number): HeatStyle {
  const v = Math.max(0, Math.min(1, intensity));
  for (let i = 1; i < STOPS.length; i++) {
    if (v <= STOPS[i].at) {
      const t = (v - STOPS[i - 1].at) / (STOPS[i].at - STOPS[i - 1].at);
      return {
        bg: lerpColor(STOPS[i - 1].rgb, STOPS[i].rgb, t),
        glow: t > 0.5 ? STOPS[i].glow : STOPS[i - 1].glow,
      };
    }
  }
  const last = STOPS[STOPS.length - 1];
  return { bg: lerpColor(last.rgb, last.rgb, 1), glow: last.glow };
}

/* ── Component ─────────────────────────────────────────────────────── */

export function StateHeatmap({
  operatorScores,
  domainAverages,
}: {
  operatorScores: number[];
  domainAverages: number[];
}) {
  const [selected, setSelected] = useState<{ d: number; o: number } | null>(null);
  const [hovered, setHovered] = useState<{ d: number; o: number } | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  /* Compute all 40 intensities, normalize to [0,1], then rank */
  const { cellGrid, top5, bottom5, rowAvgs, colAvgs, strongestRow, weakestRow, strongestCol, weakestCol } =
    useMemo(() => {
      /* 1. Raw intensities */
      const raw: number[][] = []; // raw[d][o]
      let minI = Infinity, maxI = -Infinity;
      for (let d = 0; d < 4; d++) {
        raw[d] = [];
        for (let o = 0; o < 10; o++) {
          const v = domainAverages[d] * operatorScores[o];
          raw[d][o] = v;
          if (v < minI) minI = v;
          if (v > maxI) maxI = v;
        }
      }

      /* 2. Normalize to [0,1] so full thermal spectrum is used.
         Raw values are tiny (domainAverages sum to 1 → each ~0.25) so without
         this every cell lands in the same dark-blue band. */
      const range = maxI - minI || 1;
      const cellGrid: number[][] = [];
      for (let d = 0; d < 4; d++) {
        cellGrid[d] = [];
        for (let o = 0; o < 10; o++) {
          cellGrid[d][o] = (raw[d][o] - minI) / range;
        }
      }

      /* 3. Row/col averages from normalized values so bars match cell colors */
      const rowAvgs = cellGrid.map((row) => row.reduce((s, v) => s + v, 0) / 10);
      const colAvgs = Array.from({ length: 10 }, (_, o) =>
        cellGrid.reduce((s, row) => s + row[o], 0) / 4,
      );

      /* 4. Rank all 40 cells for top5/bottom5 */
      const flat = cellGrid.flatMap((row, d) => row.map((intensity, o) => ({ d, o, intensity })));
      flat.sort((a, b) => b.intensity - a.intensity);
      const top5 = new Set(flat.slice(0, 5).map((c) => `${c.d}-${c.o}`));
      const bottom5 = new Set(flat.slice(-5).map((c) => `${c.d}-${c.o}`));

      /* 5. Strongest/weakest row & col */
      let strongestRow = 0, weakestRow = 0;
      let strongestCol = 0, weakestCol = 0;
      for (let i = 1; i < 4; i++) {
        if (rowAvgs[i] > rowAvgs[strongestRow]) strongestRow = i;
        if (rowAvgs[i] < rowAvgs[weakestRow]) weakestRow = i;
      }
      for (let i = 1; i < 10; i++) {
        if (colAvgs[i] > colAvgs[strongestCol]) strongestCol = i;
        if (colAvgs[i] < colAvgs[weakestCol]) weakestCol = i;
      }

      return { cellGrid, top5, bottom5, rowAvgs, colAvgs, strongestRow, weakestRow, strongestCol, weakestCol };
    }, [operatorScores, domainAverages]);

  const insight = selected
    ? interpretState(selected.d, selected.o, domainAverages[selected.d], operatorScores[selected.o])
    : null;

  return (
    <div className="chart-interactive">
      <div className="overflow-x-auto animate-chart-in" ref={gridRef}>
        {/* ── Main grid: label + 10 cells + row summary ── */}
        <div
          className="inline-grid gap-1 relative"
          style={{ gridTemplateColumns: 'auto repeat(10, 40px) 80px' }}
        >
          {/* Header row: empty + operator labels + "Avg" */}
          <div />
          {OPERATOR_SHORT.map((op) => (
            <div key={op} className="px-0.5 py-0.5 text-center text-[10px] text-slate-500 font-medium truncate">
              {op}
            </div>
          ))}
          <div className="px-1 py-0.5 text-center text-[10px] text-slate-500 font-medium">Avg</div>

          {/* 4 domain rows */}
          {DOMAIN_SHORT.map((domain, di) => (
            <Fragment key={domain}>
              {/* Row label */}
              <div className="px-2 py-1 text-xs font-medium text-slate-400 flex items-center">
                {domain}
              </div>

              {/* 10 cells */}
              {operatorScores.map((_opScore, oi) => {
                const normalized = cellGrid[di][oi]; // 0-1 for color mapping
                const rawScore = domainAverages[di] * operatorScores[oi]; // original for display
                const score10 = (rawScore * 10).toFixed(1);
                const key = `${di}-${oi}`;
                const isTop5 = top5.has(key);
                const isBottom5 = bottom5.has(key);
                const isSelected = selected?.d === di && selected?.o === oi;
                const heat = heatColor(normalized);

                return (
                  <div
                    key={key}
                    className={`w-10 h-10 rounded-md cursor-pointer transition-all duration-200
                      hover:scale-110 hover:brightness-125 hover:z-10 relative
                      ${isTop5 ? 'animate-heat-pulse' : ''}
                      ${isBottom5 ? 'animate-frost-pulse' : ''}`}
                    style={{
                      backgroundColor: heat.bg,
                      boxShadow: isSelected
                        ? `0 0 16px ${heat.bg}, inset 0 0 0 2px white`
                        : heat.glow,
                      '--heat-glow': `0 0 8px ${heat.bg}`,
                      '--heat-glow-bright': `0 0 16px ${heat.bg}, 0 0 24px rgba(251,191,36,0.2)`,
                    } as React.CSSProperties}
                    title={`${domain}${oi}: ${score10}/10`}
                    onMouseEnter={() => setHovered({ d: di, o: oi })}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => setSelected(isSelected ? null : { d: di, o: oi })}
                  >
                    {/* Score overlay for hot cells */}
                    {normalized >= 0.7 && (
                      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-dark-900/70 pointer-events-none">
                        {score10}
                      </span>
                    )}
                  </div>
                );
              })}

              {/* Row summary: mini bar + percentage */}
              <div className="flex items-center gap-1 px-1">
                <div className="w-10 h-2 rounded-full overflow-hidden bg-dark-700">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(100, rowAvgs[di] * 100)}%`,
                      backgroundColor: heatColor(rowAvgs[di]).bg,
                    }}
                  />
                </div>
                <span
                  className="text-[10px] font-mono font-medium"
                  style={{ color: di === strongestRow ? '#fbbf24' : di === weakestRow ? '#f87171' : '#94a3b8' }}
                >
                  {(rowAvgs[di] * 100).toFixed(0)}%
                </span>
              </div>
            </Fragment>
          ))}
        </div>

        {/* ── Column summaries ── */}
        <div
          className="inline-grid gap-1 mt-1"
          style={{ gridTemplateColumns: 'auto repeat(10, 40px) 80px' }}
        >
          <div className="px-2 text-[10px] text-slate-600">Avg</div>
          {colAvgs.map((avg: number, oi: number) => (
            <div key={oi} className="flex flex-col items-center gap-0.5">
              <div className="w-2 h-5 rounded-full overflow-hidden bg-dark-700">
                <div
                  className="w-full rounded-full transition-all duration-300"
                  style={{
                    height: `${Math.min(100, avg * 100)}%`,
                    backgroundColor: heatColor(avg).bg,
                    marginTop: `${100 - Math.min(100, avg * 100)}%`,
                  }}
                />
              </div>
              <span
                className="text-[9px] font-mono"
                style={{ color: oi === strongestCol ? '#fbbf24' : oi === weakestCol ? '#f87171' : '#64748b' }}
              >
                {(avg * 100).toFixed(0)}
              </span>
            </div>
          ))}
          <div />
        </div>

        {/* ── Legend bar ── */}
        <div className="mt-3 px-1">
          <div
            className="h-2 rounded-full"
            style={{
              background: 'linear-gradient(to right, #0f172a, #1e3a5f, #1a5276, #2dd4bf, #fbbf24, #f59e0b, #fef3c7)',
            }}
          />
          <div className="flex justify-between mt-0.5">
            <span className="text-[9px] text-blue-400/60">Cold</span>
            <span className="text-[9px] text-slate-500">Moderate</span>
            <span className="text-[9px] text-amber-400/80">Hot</span>
          </div>
        </div>

        {/* ── Hover tooltip ── */}
        {hovered && (
          <div
            className="absolute z-20 px-2 py-1 rounded-md text-[11px] font-mono pointer-events-none
              border border-white/10 bg-[#0f1629]/95 backdrop-blur text-slate-200 shadow-lg"
            style={{
              /* Position relative to grid — sits above the hovered cell */
              left: `calc(${hovered.o * 44 + 44}px)`,
              top: `calc(${hovered.d * 44 + 12}px)`,
            }}
          >
            {DOMAIN_SHORT[hovered.d]}{hovered.o} ={' '}
            <span className="text-amber-300 font-bold">
              {(domainAverages[hovered.d] * operatorScores[hovered.o] * 10).toFixed(1)}
            </span>
            /10
          </div>
        )}

        {/* ── Hint text ── */}
        <div className="chart-hint mt-1 text-center text-[10px] text-slate-600 opacity-0 transition-opacity">
          Click a cell for details
        </div>
      </div>

      {/* ── Explain panel ── */}
      {insight && (
        <ExplainPanel visible={true} onClose={() => setSelected(null)}>
          <p className="font-medium text-slate-200">
            State {insight.state}: {insight.operator} / {insight.domain}
          </p>
          <p>
            Intensity:{' '}
            <span className="font-mono font-bold text-slate-200">
              {(insight.intensity * 100).toFixed(1)}%
            </span>
          </p>
          <p>{insight.description}</p>
        </ExplainPanel>
      )}
    </div>
  );
}
