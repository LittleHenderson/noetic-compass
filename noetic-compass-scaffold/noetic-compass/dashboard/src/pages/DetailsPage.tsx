import { useParams, useNavigate } from 'react-router-dom';
import { useState, lazy, Suspense } from 'react';
import { useHistoryStore } from '../stores/historyStore';
import { Card } from '../components/shared/Card';
import { CertBadge } from '../components/shared/CertBadge';
import { ExportButton } from '../components/shared/ExportButton';
import { AiBriefing } from '../components/shared/AiBriefing';
import { AiResponsePanel } from '../components/shared/AiResponsePanel';
import { TraceViewer } from '../components/shared/TraceViewer';
import { InterpretButton } from '../components/shared/InterpretButton';
import { ResearchPrototypeNotice } from '../components/shared/ResearchPrototypeNotice';
import { PIPELINE_STAGES } from '../lib/constants';
import { interpretNccs, interpretSubScores, interpretOperators, interpretHeatmap, interpretDrives, interpretRpm, interpretInversions, interpretPipeline, interpretTrace } from '../lib/cardInterpretations';

const LazyNccsGauge = lazy(() => import('../components/charts/NccsGauge').then((m) => ({ default: m.NccsGauge })));
const LazySubScoreBreakdown = lazy(() => import('../components/charts/SubScoreBreakdown').then((m) => ({ default: m.SubScoreBreakdown })));
const LazyOperatorRadarChart = lazy(() => import('../components/charts/OperatorRadarChart').then((m) => ({ default: m.OperatorRadarChart })));
const LazyStateHeatmap = lazy(() => import('../components/charts/StateHeatmap').then((m) => ({ default: m.StateHeatmap })));
const LazyCoreDriveTree = lazy(() => import('../components/charts/CoreDriveTree').then((m) => ({ default: m.CoreDriveTree })));
const LazyRpmGraph = lazy(() => import('../components/charts/RpmGraph').then((m) => ({ default: m.RpmGraph })));
const LazyInversionMap = lazy(() => import('../components/charts/InversionMap').then((m) => ({ default: m.InversionMap })));

export function DetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const record = useHistoryStore((s) => s.getById(id ?? ''));
  const [showRaw, setShowRaw] = useState(false);
  const [viewMode, setViewMode] = useState<'summary' | 'technical'>('summary');

  if (!record) {
    return (
      <div className="p-8 text-center text-slate-500">
        Assessment not found. <button onClick={() => navigate('/history')} className="text-accent-teal underline">Back to history</button>
      </div>
    );
  }

  const { result } = record;
  const operatorScores = result.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
  // CAS v7.5 Register data flow (Clarification 8). Top-level
  // `score_registers` is canonical; fall back to the operator_scoring
  // stage data for defense-in-depth. Null/undefined = register-neutral
  // (v7.4-compatible rendering).
  const scoreRegisters =
    result.score_registers ??
    (result.stages.find(s => s.stage === 'operator_scoring')?.data?.score_registers as
      | (import('../api/types').PhenomenologicalRegister | null)[]
      | undefined) ??
    null;
  const domainAverages = result.stages.find(s => s.stage === 'domain_coherence')?.data?.domain_averages as number[] | undefined;
  const driveScores = result.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
  const a0Score = result.stages.find(s => s.stage === 'rpm_gate')?.data?.a0_score as number | undefined;
  const rpmCompleteness = result.stages.find(s => s.stage === 'rpm_gate')?.data?.rpm_completeness as number | undefined;
  const axisScores = result.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
  const stealthResistance = result.stages.find(s => s.stage === 'inversion_scan')?.data?.stealth_resistance as number | undefined;
  const chartFallback = (
    <div className="flex min-h-[220px] items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-xs text-slate-500">
      Loading visualization...
    </div>
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold text-slate-100">Assessment Details</h2>
        <div className="flex flex-wrap gap-2">
          <ExportButton
            result={record.result}
            text={record.text}
            timestamp={new Date(record.timestamp).toLocaleString()}
          />
          <button
            onClick={() => navigate('/assessment', { state: { prefill: record.text } })}
            className="rounded-lg border border-accent-teal/30 bg-accent-teal/10 px-3 py-2 text-xs font-medium text-accent-teal hover:bg-accent-teal/20 transition-colors min-h-[44px]"
          >
            Re-run
          </button>
          <button
            onClick={() => navigate('/history')}
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
          >
            Back
          </button>
        </div>
      </div>

      <ResearchPrototypeNotice compact />

      <Card title="Input Text">
        <p className="text-sm text-slate-300 whitespace-pre-wrap">{record.text}</p>
        <p className="mt-2 text-xs text-slate-600">{new Date(record.timestamp).toLocaleString()}</p>
      </Card>

      {/* Show the actual AI response that was assessed. Collapsed by default. */}
      <AiResponsePanel llmResponse={result.llm_response} />

      {result.interpretation && (
        <div className="flex justify-end">
          <button
            onClick={() => setViewMode(viewMode === 'summary' ? 'technical' : 'summary')}
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
          >
            {viewMode === 'summary' ? 'Show Technical View' : 'Show Summary View'}
          </button>
        </div>
      )}

      {viewMode === 'summary' && result.interpretation && (
        <AiBriefing
          interpretation={result.interpretation}
          modelName={result.llm_response?.model ?? null}
        />
      )}

      {(viewMode === 'technical' || !result.interpretation) && (
        <>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Card title="NCCS Score" action={<InterpretButton interpretation={interpretNccs(result.nccs)} />}>
              <div className="flex flex-col items-center gap-4">
                <Suspense fallback={chartFallback}>
                  <LazyNccsGauge composite={result.nccs.composite} certification={result.nccs.certification} nccs={result.nccs} />
                </Suspense>
                <CertBadge certification={result.nccs.certification} composite={result.nccs.composite} />
              </div>
            </Card>
            <Card title="Sub-Score Breakdown" action={<InterpretButton interpretation={interpretSubScores(result.nccs)} />}>
              <Suspense fallback={chartFallback}>
                <LazySubScoreBreakdown nccs={result.nccs} />
              </Suspense>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {operatorScores && (
              <Card title="Operator Radar" action={<InterpretButton interpretation={interpretOperators(operatorScores)} />}>
                <Suspense fallback={chartFallback}>
                  <LazyOperatorRadarChart scores={operatorScores} registers={scoreRegisters} />
                </Suspense>
              </Card>
            )}
            {operatorScores && domainAverages && (
              <Card title="40-State Heatmap" action={<InterpretButton interpretation={interpretHeatmap(operatorScores, domainAverages)} />}>
                <Suspense fallback={chartFallback}>
                  <LazyStateHeatmap operatorScores={operatorScores} domainAverages={domainAverages} />
                </Suspense>
              </Card>
            )}
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            {driveScores && driveScores.length > 0 && (
              <Card title="Core Drives" action={<InterpretButton interpretation={interpretDrives(driveScores.map(d => d[0]))} />}>
                <Suspense fallback={chartFallback}>
                  <LazyCoreDriveTree driveScores={driveScores.map(d => d[0])} />
                </Suspense>
              </Card>
            )}
            {driveScores && a0Score !== undefined && rpmCompleteness !== undefined && (
              <Card title="RPM Graph" action={<InterpretButton interpretation={interpretRpm(driveScores, a0Score, rpmCompleteness)} />}>
                <Suspense fallback={chartFallback}>
                  <LazyRpmGraph a0Score={a0Score} driveScores={driveScores} rpmCompleteness={rpmCompleteness} />
                </Suspense>
              </Card>
            )}
            {axisScores && stealthResistance !== undefined && (
              <Card title="Inversion Map" action={<InterpretButton interpretation={interpretInversions(axisScores, stealthResistance)} />}>
                <Suspense fallback={chartFallback}>
                  <LazyInversionMap axisScores={axisScores} stealthResistance={stealthResistance} />
                </Suspense>
              </Card>
            )}
          </div>

          <Card title="Pipeline Stages" action={<InterpretButton interpretation={interpretPipeline(result.stages)} />}>
            <div className="space-y-2">
              {result.stages.map((s, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="relative flex items-center justify-center w-5 h-5">
                    {s.success ? (
                      <>
                        <div className="absolute inset-0 rounded-full bg-emerald-400/20" />
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                          <path d="M2.5 6L5 8.5L9.5 3.5" stroke="#34d399" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </>
                    ) : (
                      <>
                        <div className="absolute inset-0 rounded-full bg-red-400/20" />
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                          <path d="M2.5 2.5L7.5 7.5M7.5 2.5L2.5 7.5" stroke="#f87171" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                      </>
                    )}
                  </div>
                  <span className="text-xs font-medium text-slate-300 w-32">{PIPELINE_STAGES[i]}</span>
                  {s.error && <span className="text-[10px] text-red-400">{s.error}</span>}
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      <Card title="Evaluation Trace" action={<InterpretButton interpretation={interpretTrace(result.stages)} />}>
        <TraceViewer stages={result.stages} />
      </Card>

      <Card>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-xs font-medium text-accent-teal hover:text-accent-cyan transition-colors"
        >
          {showRaw ? 'Hide' : 'Show'} Raw JSON
        </button>
        {showRaw && (
          <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-dark-800 border border-white/[0.06] p-4 text-xs text-slate-400">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
