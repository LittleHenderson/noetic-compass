import { useState } from 'react';
import { useWrap } from '../hooks/useWrap';
import { useTranslation } from '../hooks/useTranslation';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { CertBadge } from '../components/shared/CertBadge';
import { ExportButton } from '../components/shared/ExportButton';
import { ExplainPanel } from '../components/shared/ExplainPanel';
import { ExecutiveSummary } from '../components/shared/ExecutiveSummary';
import { AiBriefing } from '../components/shared/AiBriefing';
import { NccsGauge } from '../components/charts/NccsGauge';
import { SubScoreBreakdown } from '../components/charts/SubScoreBreakdown';
import { OperatorRadarChart } from '../components/charts/OperatorRadarChart';
import { DomainCoherenceRadar } from '../components/charts/DomainCoherenceRadar';
import { StateHeatmap } from '../components/charts/StateHeatmap';
import { CoreDriveTree } from '../components/charts/CoreDriveTree';
import { RpmGraph } from '../components/charts/RpmGraph';
import { InversionMap } from '../components/charts/InversionMap';
import { InversionAlert } from '../components/shared/InversionAlert';
import { PIPELINE_STAGES } from '../lib/constants';
import { interpretStage } from '../lib/interpretations';
import type { WrapResult } from '../api/types';

const PROVIDERS = ['mock', 'openai', 'anthropic', 'google', 'meta', 'xai', 'deepseek', 'qwen'];

function StageTimeline({ stages }: { stages: WrapResult['stages'] }) {
  const [selected, setSelected] = useState<number | null>(null);

  const insight = selected !== null ? interpretStage(stages[selected], selected) : null;

  return (
    <div className="space-y-2">
      {stages.map((s, i) => (
        <div
          key={i}
          className="flex items-center gap-3 animate-chart-in cursor-pointer rounded px-1 py-0.5 hover:bg-white/[0.02] transition-colors"
          style={{ animationDelay: `${i * 60}ms` }}
          onClick={() => setSelected(selected === i ? null : i)}
        >
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
          <span className={`text-xs font-medium w-32 ${selected === i ? 'text-slate-100' : 'text-slate-300'}`}>
            {PIPELINE_STAGES[i]}
          </span>
          <div className="flex-1 h-1 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${s.success ? 'bg-emerald-400/40' : 'bg-red-400/40'}`}
              style={{ width: '100%', animationDelay: `${i * 80}ms` }}
            />
          </div>
          {s.error && <span className="text-[10px] text-red-400">{s.error}</span>}
        </div>
      ))}

      {insight && (
        <ExplainPanel visible={true} onClose={() => setSelected(null)}>
          <p className="font-medium text-slate-200">{insight.name}</p>
          <p>{insight.description}</p>
          <p className={insight.success ? 'text-emerald-400' : 'text-red-400'}>{insight.status}</p>
        </ExplainPanel>
      )}
    </div>
  );
}

export function AssessmentPage() {
  const [text, setText] = useState('');
  const [provider, setProvider] = useState('mock');
  const [viewMode, setViewMode] = useState<'summary' | 'technical'>('summary');
  const wrap = useWrap();

  function handleSubmit() {
    if (!text.trim()) return;
    wrap.mutate({ text, provider, mock: provider === 'mock' });
  }

  const result = wrap.data;
  const translated = useTranslation(result);

  const operatorScores = result?.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
  const domainAverages = result?.stages.find(s => s.stage === 'domain_coherence')?.data?.domain_averages as number[] | undefined;
  const driveScores = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
  const a0Score = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.a0_score as number | undefined;
  const rpmCompleteness = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.rpm_completeness as number | undefined;
  const axisScores = result?.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
  const stealthResistance = result?.stages.find(s => s.stage === 'inversion_scan')?.data?.stealth_resistance as number | undefined;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <h2 className="text-xl font-bold text-slate-100">Assessment</h2>

      <Card>
        <div className="space-y-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to assess..."
            rows={4}
            className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-base sm:text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none focus:ring-1 focus:ring-accent-teal/30 resize-none"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p} className="bg-dark-800">{p}</option>
              ))}
            </select>
            {provider !== 'mock' && (
              <span className="text-[10px] text-amber-400/80 flex items-center gap-1">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Live API — requires key in .env
              </span>
            )}
            <button
              onClick={handleSubmit}
              disabled={wrap.isPending || !text.trim()}
              className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-3 sm:py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity min-h-[44px]"
            >
              {wrap.isPending ? 'Assessing...' : 'Assess'}
            </button>
          </div>
        </div>
      </Card>

      {wrap.isPending && <LoadingSpinner />}
      <ErrorBanner error={wrap.error as Error | null} />

      {result && (
        <div className="space-y-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end sm:gap-3">
            {result.interpretation && (
              <button
                onClick={() => setViewMode(viewMode === 'summary' ? 'technical' : 'summary')}
                className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
              >
                {viewMode === 'summary' ? 'Show Technical View' : 'Show Summary View'}
              </button>
            )}
            <ExportButton result={result} text={text} timestamp={new Date().toLocaleString()} />
          </div>

          {viewMode === 'summary' && result.interpretation && (
            <AiBriefing interpretation={result.interpretation} />
          )}

          {(viewMode === 'technical' || !result.interpretation) && (
            <>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <Card title="NCCS Score">
                  <div className="flex flex-col items-center gap-4">
                    <NccsGauge composite={result.nccs.composite} certification={result.nccs.certification} nccs={result.nccs} />
                    <CertBadge certification={result.nccs.certification} composite={result.nccs.composite} />
                  </div>
                </Card>
                <Card title="Sub-Score Breakdown">
                  <SubScoreBreakdown nccs={result.nccs} />
                </Card>
              </div>

              {/* Executive Summary (translated) */}
              {translated && (
                <Card title="Executive Summary">
                  <ExecutiveSummary data={translated} />
                </Card>
              )}

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {operatorScores && (
                  <Card title="Thinking Patterns">
                    <OperatorRadarChart scores={operatorScores} />
                  </Card>
                )}
                <Card title="Processing Balance">
                  <DomainCoherenceRadar result={result} />
                </Card>
              </div>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {operatorScores && domainAverages && (
                  <Card title="40-State Heatmap">
                    <StateHeatmap operatorScores={operatorScores} domainAverages={domainAverages} />
                  </Card>
                )}
                {/* Inversion Alert (Task 2) */}
                {axisScores && stealthResistance !== undefined && (
                  <Card title="Stability Alerts">
                    <InversionAlert result={result} />
                  </Card>
                )}
              </div>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                {driveScores && driveScores.length > 0 && (
                  <Card title="Core Drives">
                    <CoreDriveTree driveScores={driveScores.map(d => d[0])} />
                  </Card>
                )}
                {driveScores && a0Score !== undefined && rpmCompleteness !== undefined && (
                  <Card title="RPM Graph">
                    <RpmGraph
                      a0Score={a0Score}
                      driveScores={driveScores}
                      rpmCompleteness={rpmCompleteness}
                    />
                  </Card>
                )}
                {axisScores && stealthResistance !== undefined && (
                  <Card title="Inversion Map">
                    <InversionMap axisScores={axisScores} stealthResistance={stealthResistance} />
                  </Card>
                )}
              </div>

              <Card title="Pipeline Stages">
                <StageTimeline stages={result.stages} />
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
