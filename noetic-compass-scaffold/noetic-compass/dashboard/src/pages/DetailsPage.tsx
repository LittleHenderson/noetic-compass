import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useHistoryStore } from '../stores/historyStore';
import { Card } from '../components/shared/Card';
import { CertBadge } from '../components/shared/CertBadge';
import { ExportButton } from '../components/shared/ExportButton';
import { NccsGauge } from '../components/charts/NccsGauge';
import { SubScoreBreakdown } from '../components/charts/SubScoreBreakdown';
import { OperatorRadarChart } from '../components/charts/OperatorRadarChart';
import { StateHeatmap } from '../components/charts/StateHeatmap';
import { CoreDriveTree } from '../components/charts/CoreDriveTree';
import { RpmGraph } from '../components/charts/RpmGraph';
import { InversionMap } from '../components/charts/InversionMap';
import { PIPELINE_STAGES } from '../lib/constants';

export function DetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const record = useHistoryStore((s) => s.getById(id ?? ''));
  const [showRaw, setShowRaw] = useState(false);

  if (!record) {
    return (
      <div className="p-8 text-center text-slate-500">
        Assessment not found. <button onClick={() => navigate('/history')} className="text-accent-teal underline">Back to history</button>
      </div>
    );
  }

  const { result } = record;
  const operatorScores = result.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
  const domainAverages = result.stages.find(s => s.stage === 'domain_coherence')?.data?.domain_averages as number[] | undefined;
  const driveScores = result.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
  const a0Score = result.stages.find(s => s.stage === 'rpm_gate')?.data?.a0_score as number | undefined;
  const rpmCompleteness = result.stages.find(s => s.stage === 'rpm_gate')?.data?.rpm_completeness as number | undefined;
  const axisScores = result.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
  const stealthResistance = result.stages.find(s => s.stage === 'inversion_scan')?.data?.stealth_resistance as number | undefined;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100">Assessment Details</h2>
        <div className="flex gap-2">
          <ExportButton
            result={record.result}
            text={record.text}
            timestamp={new Date(record.timestamp).toLocaleString()}
          />
          <button
            onClick={() => navigate('/', { state: { prefill: record.text } })}
            className="rounded-lg border border-accent-teal/30 bg-accent-teal/10 px-3 py-1.5 text-xs font-medium text-accent-teal hover:bg-accent-teal/20 transition-colors"
          >
            Re-run
          </button>
          <button
            onClick={() => navigate('/history')}
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors"
          >
            Back
          </button>
        </div>
      </div>

      <Card title="Input Text">
        <p className="text-sm text-slate-300 whitespace-pre-wrap">{record.text}</p>
        <p className="mt-2 text-xs text-slate-600">{new Date(record.timestamp).toLocaleString()}</p>
      </Card>

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

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
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

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {driveScores && driveScores.length > 0 && (
          <Card title="Core Drives">
            <CoreDriveTree driveScores={driveScores.map(d => d[0])} />
          </Card>
        )}
        {driveScores && a0Score !== undefined && rpmCompleteness !== undefined && (
          <Card title="RPM Graph">
            <RpmGraph a0Score={a0Score} driveScores={driveScores} rpmCompleteness={rpmCompleteness} />
          </Card>
        )}
        {axisScores && stealthResistance !== undefined && (
          <Card title="Inversion Map">
            <InversionMap axisScores={axisScores} stealthResistance={stealthResistance} />
          </Card>
        )}
      </div>

      <Card title="Pipeline Stages">
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
