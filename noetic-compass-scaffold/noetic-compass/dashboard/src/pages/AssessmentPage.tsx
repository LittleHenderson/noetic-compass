import { useState } from 'react';
import { useWrap } from '../hooks/useWrap';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { CertBadge } from '../components/shared/CertBadge';
import { NccsGauge } from '../components/charts/NccsGauge';
import { SubScoreBreakdown } from '../components/charts/SubScoreBreakdown';
import { OperatorRadarChart } from '../components/charts/OperatorRadarChart';
import { StateHeatmap } from '../components/charts/StateHeatmap';
import { CoreDriveTree } from '../components/charts/CoreDriveTree';
import { RpmGraph } from '../components/charts/RpmGraph';
import { InversionMap } from '../components/charts/InversionMap';
import { PIPELINE_STAGES } from '../lib/constants';
import type { WrapResult } from '../api/types';

const PROVIDERS = ['mock', 'openai', 'anthropic', 'google', 'meta'];

function StageTimeline({ stages }: { stages: WrapResult['stages'] }) {
  return (
    <div className="space-y-1">
      {stages.map((s, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className={`h-2 w-2 rounded-full ${s.success ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="w-28 font-medium text-gray-600">{PIPELINE_STAGES[i]}</span>
          {s.error && <span className="text-red-500">{s.error}</span>}
        </div>
      ))}
    </div>
  );
}

export function AssessmentPage() {
  const [text, setText] = useState('');
  const [provider, setProvider] = useState('mock');
  const wrap = useWrap();

  function handleSubmit() {
    if (!text.trim()) return;
    wrap.mutate({ text, provider });
  }

  const result = wrap.data;

  // Extract chart data from stage results
  const operatorScores = result?.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
  const domainAverages = result?.stages.find(s => s.stage === 'domain_coherence')?.data?.domain_averages as number[] | undefined;
  const driveScores = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
  const a0Score = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.a0_score as number | undefined;
  const rpmCompleteness = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.rpm_completeness as number | undefined;
  const axisScores = result?.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
  const stealthResistance = result?.stages.find(s => s.stage === 'inversion_scan')?.data?.stealth_resistance as number | undefined;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Assessment</h2>

      {/* Input form */}
      <Card>
        <div className="space-y-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to assess..."
            rows={5}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <div className="flex items-center gap-3">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <button
              onClick={handleSubmit}
              disabled={wrap.isPending || !text.trim()}
              className="rounded-md bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {wrap.isPending ? 'Assessing...' : 'Assess'}
            </button>
          </div>
        </div>
      </Card>

      {wrap.isPending && <LoadingSpinner />}
      <ErrorBanner error={wrap.error as Error | null} />

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Top row: Gauge + Badge + Sub-scores */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="NCCS Score">
              <div className="flex flex-col items-center gap-3">
                <NccsGauge composite={result.nccs.composite} certification={result.nccs.certification} />
                <CertBadge certification={result.nccs.certification} composite={result.nccs.composite} />
              </div>
            </Card>
            <Card title="Sub-Score Breakdown">
              <SubScoreBreakdown nccs={result.nccs} />
            </Card>
          </div>

          {/* Operator + State charts */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {operatorScores && (
              <Card title="Operator Radar">
                <OperatorRadarChart scores={operatorScores} />
              </Card>
            )}
            {operatorScores && domainAverages && (
              <Card title="40-State Heatmap">
                <StateHeatmap operatorScores={operatorScores} domainAverages={domainAverages} />
              </Card>
            )}
          </div>

          {/* Drive + RPM + Inversion */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
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

          {/* Pipeline Timeline */}
          <Card title="Pipeline Stages">
            <StageTimeline stages={result.stages} />
          </Card>
        </div>
      )}
    </div>
  );
}
