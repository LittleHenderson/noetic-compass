'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  CircleDot,
  Database,
  GitBranch,
  Info,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  StepForward,
  TriangleAlert,
  Zap,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import {
  ATTENTION_TOUR,
  BOARD_BY_ID,
  CAS_OHM_BOARDS,
  CAS_OHM_EDGES,
  CAS_OHM_SCENARIOS,
  SCENARIO_BY_ID,
  boardStateById,
  getTourPoint,
  resolveScenario,
  type BoardId,
  type CasOhmBoard,
  type CasOhmEdge,
  type OperatingRegion,
  type ResolvedBoardState,
  type SemanticOutcome,
} from '@/lib/cas-ohm-graph-model';
import { cn } from '@/lib/utils';

interface CasOhmPanelProps {
  active: boolean;
}

const SPEEDS = [
  { label: '0.5×', value: 1500 },
  { label: '1×', value: 900 },
  { label: '2×', value: 450 },
] as const;

function flowTone(region: OperatingRegion) {
  if (region === 'ACTIVE') return 'text-emerald-300';
  if (region === 'CUTOFF') return 'text-amber-300';
  if (region === 'SATURATION' || region === 'UNSTABLE') return 'text-rose-300';
  return 'text-muted-foreground';
}

function semanticTone(outcome: SemanticOutcome) {
  if (outcome === 'INTENDED') return 'text-emerald-300';
  if (outcome === 'OPPOSITE') return 'text-rose-300';
  if (outcome === 'OFF_AXIS') return 'text-amber-300';
  return 'text-muted-foreground';
}

function svgFlowColor(region: OperatingRegion) {
  if (region === 'ACTIVE') return 'oklch(0.79 0.135 204)';
  if (region === 'CUTOFF') return 'oklch(0.75 0.14 72)';
  return 'oklch(0.67 0.2 28)';
}

function svgSemanticColor(outcome: SemanticOutcome) {
  if (outcome === 'INTENDED') return 'oklch(0.77 0.15 155)';
  if (outcome === 'OPPOSITE') return 'oklch(0.67 0.2 28)';
  if (outcome === 'OFF_AXIS') return 'oklch(0.75 0.14 72)';
  return 'var(--muted-foreground)';
}

function cjtCoordinate(board: CasOhmBoard, cjtIndex: number) {
  const count = board.cjts.length;
  const width = 176;
  const start = board.x - width / 2;
  const step = count > 1 ? width / (count - 1) : 0;
  return { x: start + step * cjtIndex, y: board.y + 46 };
}

function shortenedPath(from: CasOhmBoard, to: CasOhmBoard) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.max(Math.hypot(dx, dy), 1);
  const trimX = (dx / distance) * 132;
  const trimY = (dy / distance) * 82;
  return [
    'M',
    (from.x + trimX).toFixed(1),
    (from.y + trimY).toFixed(1),
    'L',
    (to.x - trimX).toFixed(1),
    (to.y - trimY).toFixed(1),
  ].join(' ');
}

function curvedPath(from: CasOhmBoard, to: CasOhmBoard, bend: number) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.max(Math.hypot(dx, dy), 1);
  const normalX = (-dy / distance) * bend;
  const normalY = (dx / distance) * bend;
  const midX = (from.x + to.x) / 2 + normalX;
  const midY = (from.y + to.y) / 2 + normalY;
  return [
    'M',
    from.x.toFixed(1),
    from.y.toFixed(1),
    'Q',
    midX.toFixed(1),
    midY.toFixed(1),
    to.x.toFixed(1),
    to.y.toFixed(1),
  ].join(' ');
}

function edgePath(edge: CasOhmEdge) {
  const from = BOARD_BY_ID.get(edge.from);
  const to = BOARD_BY_ID.get(edge.to);
  if (!from || !to) return '';
  if (edge.from === 'timing' && edge.to === 'power') {
    return [
      'M',
      from.x,
      from.y + 82,
      'C',
      from.x,
      752,
      54,
      752,
      54,
      from.y,
      'L',
      54,
      92,
      'C',
      54,
      70,
      to.x,
      70,
      to.x,
      to.y - 82,
    ].join(' ');
  }
  if (edge.kind === 'RPM_LOOP') {
    return curvedPath(from, to, edge.from === 'goal' ? -125 : 125);
  }
  if (edge.kind === 'CAS_GEM_LOOP') {
    return curvedPath(from, to, 78);
  }
  if (edge.kind === 'CONTROL_RETURN') {
    return curvedPath(from, to, -190);
  }
  return shortenedPath(from, to);
}

function isAuxiliaryScenario(scenarioId: string, kind: CasOhmEdge['kind']) {
  if (
    (scenarioId === 'ambiguous-reference' || scenarioId === 'rpm-failure') &&
    kind === 'RPM_LOOP'
  ) {
    return true;
  }
  if (
    (scenarioId === 'memory-contention' || scenarioId === 'anchor-conflict') &&
    kind === 'CAS_GEM_LOOP'
  ) {
    return true;
  }
  return false;
}

function Metric({
  label,
  value,
  detail,
  className,
}: {
  label: string;
  value: string;
  detail: string;
  className?: string;
}) {
  return (
    <div className="bg-card/95 px-3 py-3">
      <p className="eyebrow">{label}</p>
      <p className={cn('mt-1 font-mono text-sm text-primary', className)}>{value}</p>
      <p className="mt-1 text-[10px] leading-4 text-muted-foreground">{detail}</p>
    </div>
  );
}

function BoardGraph({
  states,
  selectedBoardId,
  activeBoardId,
  activeCjtId,
  scenarioId,
  playing,
  reducedMotion,
  speedMs,
  onSelect,
}: {
  states: readonly ResolvedBoardState[];
  selectedBoardId: BoardId;
  activeBoardId: BoardId;
  activeCjtId: string;
  scenarioId: string;
  playing: boolean;
  reducedMotion: boolean;
  speedMs: number;
  onSelect: (boardId: BoardId) => void;
}) {
  const activeBoard = BOARD_BY_ID.get(activeBoardId) ?? CAS_OHM_BOARDS[0];
  const activeCjtIndex = Math.max(
    activeBoard.cjts.findIndex((cjt) => cjt.id === activeCjtId),
    0,
  );
  const bead = cjtCoordinate(activeBoard, activeCjtIndex);
  const activeBoardIndex = CAS_OHM_BOARDS.findIndex(
    (board) => board.id === activeBoardId,
  );
  const previousBoardId =
    CAS_OHM_BOARDS[
      (activeBoardIndex - 1 + CAS_OHM_BOARDS.length) % CAS_OHM_BOARDS.length
    ].id;

  return (
    <div className="border border-border bg-[#071014]/90">
      <div className="hidden overflow-hidden xl:block">
        <svg
          viewBox="0 0 1540 790"
          className="h-auto w-full"
          aria-labelledby="cas-ohm-map-title cas-ohm-map-description"
        >
          <title id="cas-ohm-map-title">Whole-machine CAS-Ohm attention map</title>
          <desc id="cas-ohm-map-description">
            Animated design simulation of attention moving through fourteen declared
            board-family stations and every conceptual CJT test point. Flow and
            semantic outcome are shown independently. The values are not live
            CNCM telemetry.
          </desc>
          <defs>
            <marker
              id="cas-ohm-arrow"
              markerWidth="8"
              markerHeight="8"
              refX="6"
              refY="3"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L0,6 L6,3 z" fill="var(--muted-foreground)" />
            </marker>
            <filter id="cas-ohm-glow" x="-80%" y="-80%" width="260%" height="260%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <pattern
              id="cas-ohm-grid"
              width="28"
              height="28"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 28 0 L 0 0 0 28"
                fill="none"
                stroke="var(--border)"
                strokeWidth="0.6"
                opacity="0.45"
              />
            </pattern>
          </defs>

          <rect width="1540" height="790" fill="url(#cas-ohm-grid)" />
          <path
            d="M54 96 H1486 M54 342 H1486 M54 582 H1486"
            fill="none"
            stroke="var(--border)"
            strokeWidth="1"
            opacity="0.45"
          />
          <text x="66" y="110" fill="var(--muted-foreground)" fontSize="10" fontFamily="var(--font-plex-mono)">
            DRIVE / INPUT PLANE
          </text>
          <text x="66" y="356" fill="var(--muted-foreground)" fontSize="10" fontFamily="var(--font-plex-mono)">
            TRANSFORM / VERIFY PLANE
          </text>
          <text x="66" y="596" fill="var(--muted-foreground)" fontSize="10" fontFamily="var(--font-plex-mono)">
            COMMIT / EVIDENCE / FEEDBACK PLANE
          </text>

          <g aria-hidden="true">
            {CAS_OHM_EDGES.map((edge) => {
              const fromState = boardStateById(states, edge.from);
              const isIncomingPrimary =
                edge.kind === 'PRIMARY' &&
                edge.from === previousBoardId &&
                edge.to === activeBoardId;
              const isAuxiliary = isAuxiliaryScenario(scenarioId, edge.kind);
              const highlighted = isIncomingPrimary || isAuxiliary;
              return (
                <path
                  key={edge.id}
                  id={edge.id}
                  d={edgePath(edge)}
                  fill="none"
                  stroke={
                    highlighted
                      ? edge.kind === 'RPM_LOOP'
                        ? 'var(--accent)'
                        : 'var(--primary)'
                      : 'var(--muted-foreground)'
                  }
                  strokeWidth={
                    highlighted
                      ? 2.4 + Math.min(fromState.overloadRatio, 1.5)
                      : 1 + Math.min(fromState.overloadRatio, 1.2)
                  }
                  strokeDasharray={
                    edge.kind === 'PRIMARY' ? (highlighted ? '9 8' : undefined) : '5 8'
                  }
                  opacity={highlighted ? 0.95 : edge.kind === 'PRIMARY' ? 0.38 : 0.24}
                  markerEnd="url(#cas-ohm-arrow)"
                  className={cn(highlighted && playing && 'cas-ohm-flow-line')}
                />
              );
            })}
          </g>

          {CAS_OHM_EDGES.filter((edge) =>
            isAuxiliaryScenario(scenarioId, edge.kind),
          ).map((edge) =>
            playing && !reducedMotion ? (
              <circle
                key={'pulse.' + edge.id}
                r="5"
                fill={edge.kind === 'RPM_LOOP' ? 'var(--accent)' : 'var(--primary)'}
                filter="url(#cas-ohm-glow)"
                aria-hidden="true"
              >
                <animateMotion
                  dur={String(Math.max(speedMs * 5, 1800)) + 'ms'}
                  repeatCount="indefinite"
                  path={edgePath(edge)}
                />
              </circle>
            ) : null,
          )}

          {states.map((board) => {
            const isActive = board.id === activeBoardId;
            const isSelected = board.id === selectedBoardId;
            const stroke = isActive
              ? svgFlowColor(board.operatingRegion)
              : isSelected
                ? 'var(--foreground)'
                : 'var(--border)';
            return (
              <g
                key={board.id}
                onClick={() => onSelect(board.id)}
                className="cursor-pointer"
              >
                <rect
                  x={board.x - 122}
                  y={board.y - 72}
                  width="244"
                  height="144"
                  rx="5"
                  fill={
                    isActive
                      ? 'color-mix(in oklch, var(--primary) 10%, var(--card))'
                      : 'var(--card)'
                  }
                  stroke={stroke}
                  strokeWidth={isActive ? 2.4 : isSelected ? 1.8 : 1}
                  filter={isActive ? 'url(#cas-ohm-glow)' : undefined}
                />
                <rect
                  x={board.x - 122}
                  y={board.y - 72}
                  width="5"
                  height="144"
                  fill={svgFlowColor(board.operatingRegion)}
                  opacity={isActive ? 1 : 0.55}
                />
                <rect
                  x={board.x + 107}
                  y={board.y - 57}
                  width="7"
                  height="7"
                  fill={svgSemanticColor(board.semanticOutcome)}
                />
                <text
                  x={board.x - 103}
                  y={board.y - 48}
                  fill="var(--muted-foreground)"
                  fontSize="9"
                  fontFamily="var(--font-plex-mono)"
                  letterSpacing="1.1"
                >
                  FAMILY {String(board.family).padStart(2, '0')} · {board.code}
                </text>
                <text
                  x={board.x - 103}
                  y={board.y - 25}
                  fill="var(--foreground)"
                  fontSize="14"
                  fontWeight="600"
                  fontFamily="var(--font-manrope)"
                >
                  {board.shortName}
                </text>
                <text
                  x={board.x - 103}
                  y={board.y - 6}
                  fill="var(--muted-foreground)"
                  fontSize="9"
                  fontFamily="var(--font-plex-mono)"
                >
                  I {board.observedFlow.toFixed(2)} · R {board.resistance.toFixed(2)} · β {board.beta.toFixed(2)}
                </text>
                <text
                  x={board.x - 103}
                  y={board.y + 13}
                  fill={svgFlowColor(board.operatingRegion)}
                  fontSize="9"
                  fontFamily="var(--font-plex-mono)"
                >
                  {board.operatingRegion}
                </text>
                <text
                  x={board.x + 2}
                  y={board.y + 13}
                  fill={svgSemanticColor(board.semanticOutcome)}
                  fontSize="9"
                  fontFamily="var(--font-plex-mono)"
                >
                  SEM {board.semanticOutcome}
                </text>
                <line
                  x1={board.x - 88}
                  y1={board.y + 46}
                  x2={board.x + 88}
                  y2={board.y + 46}
                  stroke="var(--border)"
                  strokeWidth="1"
                />
                {board.cjts.map((cjt, index) => {
                  const coordinate = cjtCoordinate(board, index);
                  const cjtActive = cjt.id === activeCjtId;
                  return (
                    <g key={cjt.id}>
                      <circle
                        cx={coordinate.x}
                        cy={coordinate.y}
                        r={cjtActive ? 7 : 4.2}
                        fill={cjtActive ? 'var(--primary)' : 'var(--background)'}
                        stroke={cjtActive ? 'var(--primary)' : 'var(--muted-foreground)'}
                        strokeWidth={cjtActive ? 2 : 1}
                        className={cn(
                          cjtActive && playing && 'cas-ohm-cjt-pulse',
                        )}
                      />
                    </g>
                  );
                })}
                <text
                  x={board.x - 103}
                  y={board.y + 65}
                  fill={isActive ? 'var(--primary)' : 'var(--muted-foreground)'}
                  fontSize="8"
                  fontFamily="var(--font-plex-mono)"
                >
                  {board.cjts.length} CJT / TEST POINTS · {board.binding}
                </text>
              </g>
            );
          })}

          <g
            aria-hidden="true"
            style={{
              transform: 'translate(' + bead.x + 'px, ' + bead.y + 'px)',
              transitionDuration: reducedMotion ? '0ms' : String(speedMs * 0.72) + 'ms',
            }}
            className="cas-ohm-attention-bead"
          >
            <circle
              cx="0"
              cy="0"
              r="13"
              fill="none"
              stroke="var(--primary)"
              strokeWidth="1.5"
              opacity="0.75"
              className={cn(playing && 'cas-ohm-cjt-pulse')}
            />
            <circle
              cx="0"
              cy="0"
              r="5"
              fill="var(--primary)"
              filter="url(#cas-ohm-glow)"
            />
          </g>
        </svg>
      </div>

      <div className="grid gap-px bg-border xl:hidden sm:grid-cols-2 lg:grid-cols-3">
        {states.map((board) => {
          const activeNode = board.id === activeBoardId;
          const selected = board.id === selectedBoardId;
          const activeCjt = board.cjts.find((cjt) => cjt.id === activeCjtId);
          return (
            <button
              key={board.id}
              type="button"
              onClick={() => onSelect(board.id)}
              aria-pressed={selected}
              className={cn(
                'min-h-36 bg-card p-3 text-left transition-colors',
                activeNode && 'bg-primary/10 ring-1 ring-inset ring-primary/60',
                selected && !activeNode && 'bg-muted/45 ring-1 ring-inset ring-foreground/30',
              )}
            >
              <span className="flex items-start justify-between gap-3">
                <span>
                  <span className="eyebrow">FAMILY {board.family} · {board.code}</span>
                  <span className="mt-1 block text-xs font-semibold">{board.name}</span>
                </span>
                <span
                  className={cn(
                    'mt-1 size-2 shrink-0',
                    board.semanticOutcome === 'INTENDED'
                      ? 'bg-emerald-300'
                      : board.semanticOutcome === 'UNKNOWN'
                        ? 'bg-muted-foreground'
                        : board.semanticOutcome === 'OPPOSITE'
                          ? 'bg-rose-300'
                          : 'bg-amber-300',
                  )}
                  aria-hidden="true"
                />
              </span>
              <span className="mt-3 flex items-center gap-2">
                {board.cjts.map((cjt) => (
                  <span
                    key={cjt.id}
                    className={cn(
                      'size-2 rounded-full border border-muted-foreground/70',
                      cjt.id === activeCjtId &&
                        'border-primary bg-primary shadow-[0_0_12px_var(--primary)]',
                    )}
                    aria-hidden="true"
                  />
                ))}
              </span>
              <span className="mt-3 block font-mono text-[9px] text-muted-foreground">
                I {board.observedFlow.toFixed(2)} · R {board.resistance.toFixed(2)} ·{' '}
                <span className={flowTone(board.operatingRegion)}>
                  {board.operatingRegion}
                </span>
              </span>
              <span className="mt-1 block truncate font-mono text-[9px] text-primary">
                {activeCjt?.label ?? board.cjts.length + ' conceptual CJTs'}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function CasOhmPanel({ active }: CasOhmPanelProps) {
  const [scenarioId, setScenarioId] = useState('healthy');
  const [tourIndex, setTourIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speedMs, setSpeedMs] = useState<number>(900);
  const [selectedBoardId, setSelectedBoardId] = useState<BoardId>('power');
  const [reducedMotion, setReducedMotion] = useState(false);

  const scenario = SCENARIO_BY_ID.get(scenarioId) ?? CAS_OHM_SCENARIOS[0];
  const states = useMemo(() => resolveScenario(scenarioId), [scenarioId]);
  const activePoint = getTourPoint(tourIndex);
  const activeBoard = boardStateById(states, activePoint.boardId);
  const activeCjt =
    activeBoard.cjts.find((cjt) => cjt.id === activePoint.cjtId) ??
    activeBoard.cjts[0];
  const selectedBoard = boardStateById(states, selectedBoardId);
  const totalCjts = ATTENTION_TOUR.length;
  const allFlowReady = states.every((board) => board.flowReady);
  const semanticFaultCount = states.filter(
    (board) => board.semanticOutcome !== 'INTENDED',
  ).length;

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => {
      setReducedMotion(query.matches);
      if (query.matches) setPlaying(false);
    };
    sync();
    query.addEventListener('change', sync);
    return () => query.removeEventListener('change', sync);
  }, []);

  useEffect(() => {
    if (!active || !playing) return;
    const interval = window.setInterval(
      () => setTourIndex((current) => (current + 1) % ATTENTION_TOUR.length),
      speedMs,
    );
    return () => window.clearInterval(interval);
  }, [active, playing, speedMs]);

  const changeScenario = (nextScenarioId: string) => {
    const nextScenario =
      SCENARIO_BY_ID.get(nextScenarioId) ?? CAS_OHM_SCENARIOS[0];
    const firstPoint = ATTENTION_TOUR.findIndex(
      (candidate) => candidate.boardId === nextScenario.focusBoard,
    );
    setScenarioId(nextScenario.id);
    setSelectedBoardId(nextScenario.focusBoard);
    setTourIndex(Math.max(firstPoint, 0));
    if (!reducedMotion) setPlaying(true);
  };

  const reset = () => {
    setScenarioId('healthy');
    setTourIndex(0);
    setSelectedBoardId('power');
    setSpeedMs(900);
    setPlaying(!reducedMotion);
  };

  return (
    <section className="space-y-4" aria-labelledby="cas-ohm-heading">
      <div className="border border-primary/35 bg-primary/6 px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                className="rounded-sm border-primary/40 bg-primary/10 font-mono text-[9px] text-primary"
              >
                DESIGN / SIMULATION
              </Badge>
              <Badge
                variant="outline"
                className="rounded-sm border-amber-400/40 bg-amber-400/8 font-mono text-[9px] text-amber-200"
              >
                NOT LIVE CNCM TELEMETRY
              </Badge>
            </div>
            <h2 id="cas-ohm-heading" className="mt-3 text-xl font-semibold tracking-tight">
              Whole-Mind CAS-Ohm Attention Map
            </h2>
            <p className="mt-2 max-w-3xl text-xs leading-6 text-muted-foreground">
              Watch modeled attention move through all 14 declared board families
              and all {totalCjts} conceptual CJT/test points. The five canonical
              boards, language/dialogue, CAS-Sem, RPM, exact math, verifier,
              commitment, CAS-GEM, evidence, and learning paths are all represented.
            </p>
          </div>
          <div className="grid min-w-[240px] gap-2 font-mono text-[9px] text-muted-foreground">
            <span className="flex items-center gap-2">
              <CircleDot className="size-3.5 text-primary" /> 14 / 14 board families
            </span>
            <span className="flex items-center gap-2">
              <Activity className="size-3.5 text-primary" /> {totalCjts} / {totalCjts} test points
            </span>
            <span className="flex items-center gap-2">
              <ShieldCheck className="size-3.5 text-amber-300" /> observer-only claim boundary
            </span>
          </div>
        </div>
      </div>

      <div className="border border-border bg-card/75 p-3">
        <div className="grid gap-3 xl:grid-cols-[minmax(260px,1.4fr)_auto_minmax(160px,0.65fr)_minmax(210px,0.8fr)] xl:items-end">
          <label className="grid gap-1.5">
            <span className="eyebrow">Scenario</span>
            <NativeSelect
              value={scenarioId}
              onChange={(event) => changeScenario(event.target.value)}
              className="w-full"
              aria-label="CAS-Ohm scenario"
            >
              {CAS_OHM_SCENARIOS.map((item) => (
                <NativeSelectOption key={item.id} value={item.id}>
                  {item.label}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </label>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={playing ? 'outline' : 'default'}
              size="sm"
              className="rounded-none"
              onClick={() => setPlaying((current) => !current)}
              aria-pressed={playing}
            >
              {playing ? <Pause data-icon="inline-start" /> : <Play data-icon="inline-start" />}
              {playing ? 'Pause' : 'Play'}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-none"
              onClick={() =>
                setTourIndex((current) => (current + 1) % ATTENTION_TOUR.length)
              }
            >
              <StepForward data-icon="inline-start" /> Step
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-none"
              onClick={reset}
            >
              <RotateCcw data-icon="inline-start" /> Reset
            </Button>
          </div>

          <label className="grid gap-1.5">
            <span className="eyebrow">Motion speed</span>
            <NativeSelect
              value={String(speedMs)}
              onChange={(event) => setSpeedMs(Number(event.target.value))}
              className="w-full"
              aria-label="Attention animation speed"
            >
              {SPEEDS.map((speed) => (
                <NativeSelectOption key={speed.value} value={String(speed.value)}>
                  {speed.label}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </label>

          <label className="grid gap-1.5">
            <span className="eyebrow">Inspect board</span>
            <NativeSelect
              value={selectedBoardId}
              onChange={(event) => setSelectedBoardId(event.target.value as BoardId)}
              className="w-full"
              aria-label="Board inspector"
            >
              {CAS_OHM_BOARDS.map((board) => (
                <NativeSelectOption key={board.id} value={board.id}>
                  {board.shortName} · F{board.family}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </label>
        </div>

        <output
          className="mt-3 flex items-start gap-2 border-t border-border/70 pt-3 text-[11px] leading-5 text-muted-foreground"
          aria-live="polite"
        >
          <GitBranch className="mt-0.5 size-3.5 shrink-0 text-primary" />
          <span>
            <strong className="font-medium text-foreground">{scenario.routeLabel}:</strong>{' '}
            {scenario.description}
          </span>
        </output>
      </div>

      <div className="grid gap-px border border-border bg-border sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Attention position"
          value={activeBoard.shortName}
          detail={activeBoard.code}
        />
        <Metric
          label={'CJT / test point ' + (tourIndex + 1) + ' of ' + totalCjts}
          value={activeCjt.label}
          detail={activeCjt.effect}
        />
        <Metric
          label="Local native model"
          value={'I ' + activeBoard.observedFlow.toFixed(2)}
          detail={
            'V ' +
            activeBoard.drive.toFixed(2) +
            ' / R ' +
            activeBoard.resistance.toFixed(2) +
            ' · β ' +
            activeBoard.beta.toFixed(2)
          }
          className={flowTone(activeBoard.operatingRegion)}
        />
        <Metric
          label="Independent axes"
          value={
            'FLOW ' +
            activeBoard.operatingRegion +
            ' · SEM ' +
            activeBoard.semanticOutcome
          }
          detail="Semantic outcome is borrowed from CAS-Sem / verifier."
          className={semanticTone(activeBoard.semanticOutcome)}
        />
      </div>

      <BoardGraph
        states={states}
        selectedBoardId={selectedBoardId}
        activeBoardId={activePoint.boardId}
        activeCjtId={activePoint.cjtId}
        scenarioId={scenarioId}
        playing={playing}
        reducedMotion={reducedMotion}
        speedMs={speedMs}
        onSelect={setSelectedBoardId}
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr_1fr]">
        <section className="border border-border bg-card/75">
          <div className="border-b border-border px-4 py-3">
            <p className="eyebrow">Selected board</p>
            <h3 className="mt-1 text-sm font-semibold">{selectedBoard.name}</h3>
            <p className="mt-1 font-mono text-[9px] text-primary">
              FAMILY {selectedBoard.family} · {selectedBoard.code}
            </p>
          </div>
          <div className="p-4">
            <p className="text-[11px] leading-5 text-muted-foreground">
              {selectedBoard.role}
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-px border border-border bg-border font-mono text-[9px]">
              {[
                ['V_drive', selectedBoard.drive.toFixed(2)],
                ['R_total', selectedBoard.resistance.toFixed(2)],
                ['I_pred', selectedBoard.predictedFlow.toFixed(2)],
                ['I_obs', selectedBoard.observedFlow.toFixed(2)],
                ['delta_i', selectedBoard.residual.toFixed(2)],
                ['beta_gain', selectedBoard.beta.toFixed(2)],
                ['fairness share', (selectedBoard.allocationShare * 100).toFixed(2) + '%'],
                ['overload ratio', selectedBoard.overloadRatio.toFixed(2)],
                ['critical floor', selectedBoard.criticalFloor.toFixed(2)],
                ['ceiling', selectedBoard.ceiling.toFixed(2)],
              ].map(([label, value]) => (
                <div key={label} className="bg-card px-3 py-2.5">
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="mt-1 text-cyan-100">{value}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge
                variant="outline"
                className={cn(
                  'rounded-sm font-mono text-[9px]',
                  flowTone(selectedBoard.operatingRegion),
                )}
              >
                FLOW {selectedBoard.operatingRegion}
              </Badge>
              <Badge
                variant="outline"
                className={cn(
                  'rounded-sm font-mono text-[9px]',
                  semanticTone(selectedBoard.semanticOutcome),
                )}
              >
                SEM {selectedBoard.semanticOutcome}
              </Badge>
              <Badge
                variant="outline"
                className="rounded-sm font-mono text-[9px] text-muted-foreground"
              >
                {selectedBoard.binding}
              </Badge>
            </div>
          </div>
        </section>

        <section className="border border-border bg-card/75">
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
            <div>
              <p className="eyebrow">Preserved child test points</p>
              <h3 className="mt-1 text-sm font-semibold">All conceptual CJTs</h3>
            </div>
            <Badge variant="outline" className="rounded-sm font-mono text-[9px]">
              {selectedBoard.cjts.length} POINTS
            </Badge>
          </div>
          <ol className="divide-y divide-border/70">
            {selectedBoard.cjts.map((cjt, index) => {
              const current = cjt.id === activePoint.cjtId;
              return (
                <li
                  key={cjt.id}
                  className={cn(
                    'grid grid-cols-[26px_1fr] gap-3 px-4 py-3',
                    current && 'bg-primary/8',
                  )}
                >
                  <span
                    className={cn(
                      'grid size-6 place-items-center border border-border font-mono text-[9px] text-muted-foreground',
                      current && 'border-primary bg-primary/10 text-primary',
                    )}
                  >
                    {index + 1}
                  </span>
                  <span>
                    <span className="block text-[11px] font-medium">{cjt.label}</span>
                    <span className="mt-1 block text-[10px] leading-4 text-muted-foreground">
                      {cjt.effect}
                    </span>
                    <code className="mt-1 block text-[8px] text-primary/80">{cjt.id}</code>
                  </span>
                </li>
              );
            })}
          </ol>
        </section>

        <section className="space-y-3">
          <div className="border border-border bg-card/75 p-4">
            <p className="eyebrow">Scenario diagnosis</p>
            <div className="mt-3 flex items-start gap-2">
              {scenario.semanticGate === 'ADVISORY_PASS' ? (
                <Activity className="mt-0.5 size-4 shrink-0 text-primary" />
              ) : (
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-300" />
              )}
              <div>
                <p className="text-[11px] leading-5 text-foreground">
                  {scenario.diagnostic}
                </p>
                <p className="mt-2 text-[10px] leading-5 text-muted-foreground">
                  Next probe: {scenario.probe}
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-px border border-border bg-border">
            <div className="bg-card p-3">
              <div className="flex items-center gap-2">
                <Zap className="size-3.5 text-primary" />
                <p className="eyebrow">Flow plane</p>
              </div>
              <p className="mt-2 text-[10px] leading-5 text-muted-foreground">
                CAS-Ohm may model allocation, flow, residuals, and probe priority.
                Whole-cascade flow is {allFlowReady ? 'locally active' : 'not locally ready'}.
              </p>
            </div>
            <div className="bg-card p-3">
              <div className="flex items-center gap-2">
                <Database className="size-3.5 text-emerald-300" />
                <p className="eyebrow">Meaning plane</p>
              </div>
              <p className="mt-2 text-[10px] leading-5 text-muted-foreground">
                CAS-Sem and the verifier supply semantic results. {semanticFaultCount}{' '}
                board{semanticFaultCount === 1 ? '' : 's'} currently carry a
                non-intended result.
              </p>
            </div>
            <div className="bg-card p-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-3.5 text-amber-300" />
                <p className="eyebrow">Commitment & authority</p>
              </div>
              <p className="mt-2 text-[10px] leading-5 text-muted-foreground">
                {scenario.semanticGate === 'ADVISORY_PASS'
                  ? 'This display is advisory. The separate commitment controller still owns the decision.'
                  : 'The separate semantic / commitment authority remains blocked in this scenario.'}
              </p>
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-3 border border-amber-400/30 bg-amber-400/5 p-4 lg:grid-cols-[auto_1fr]">
        <Info className="size-5 text-amber-300" aria-hidden="true" />
        <div>
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-200">
            Attention is not truth · Flow ≠ meaning · Work allocation ≠ probability
          </p>
          <p className="mt-2 text-[10px] leading-5 text-muted-foreground">
            Residual rank does not identify a cause. This deterministic visual does
            not mutate CNCM state. Runtime 0.1.0 does not read or emit CAS-Ohm
            records, and no point shown here claims a compiled CJT identity.
          </p>
        </div>
      </div>
    </section>
  );
}
