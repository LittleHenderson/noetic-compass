import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useHistoryStore } from '../stores/historyStore';
import { Card } from '../components/shared/Card';
import { CertBadge } from '../components/shared/CertBadge';
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
      <div className="p-8 text-center text-gray-500">
        Assessment not found. <button onClick={() => navigate('/history')} className="text-indigo-600 underline">Back to history</button>
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">Assessment Details</h2>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/', { state: { prefill: record.text } })}
            className="rounded-md bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
          >
            Re-run
          </button>
          <button
            onClick={() => navigate('/history')}
            className="rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200"
          >
            Back
          </button>
        </div>
      </div>

      {/* Full text */}
      <Card title="Input Text">
        <p className="text-sm text-gray-700 whitespace-pre-wrap">{record.text}</p>
        <p className="mt-2 text-xs text-gray-400">{new Date(record.timestamp).toLocaleString()}</p>
      </Card>

      {/* Score overview */}
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

      {/* Charts */}
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
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

      {/* Pipeline */}
      <Card title="Pipeline Stages">
        <div className="space-y-1">
          {result.stages.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${s.success ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="w-28 font-medium text-gray-600">{PIPELINE_STAGES[i]}</span>
              {s.error && <span className="text-red-500">{s.error}</span>}
            </div>
          ))}
        </div>
      </Card>

      {/* Raw JSON toggle */}
      <Card>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-xs font-medium text-indigo-600 hover:underline"
        >
          {showRaw ? 'Hide' : 'Show'} Raw JSON
        </button>
        {showRaw && (
          <pre className="mt-2 max-h-96 overflow-auto rounded bg-gray-100 p-3 text-xs">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
