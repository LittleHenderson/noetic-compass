/**
 * Off-screen chart renderer for export capture.
 * Renders all 7 chart components at fixed dimensions in a hidden container.
 * Mounted only during export, removed after capture.
 */

import { forwardRef } from 'react';
import { NccsGauge } from '../charts/NccsGauge';
import { SubScoreBreakdown } from '../charts/SubScoreBreakdown';
import { OperatorRadarChart } from '../charts/OperatorRadarChart';
import { StateHeatmap } from '../charts/StateHeatmap';
import { CoreDriveTree } from '../charts/CoreDriveTree';
import { RpmGraph } from '../charts/RpmGraph';
import { InversionMap } from '../charts/InversionMap';
import type { NccsResult } from '../../api/types';

interface HiddenReportChartsProps {
  nccs: NccsResult;
  operatorScores?: number[];
  domainAverages?: number[];
  driveScores?: number[][];
  a0Score?: number;
  rpmCompleteness?: number;
  axisScores?: number[];
  stealthResistance?: number;
}

export const HiddenReportCharts = forwardRef<HTMLDivElement, HiddenReportChartsProps>(
  function HiddenReportCharts(props, ref) {
    const {
      nccs, operatorScores, domainAverages, driveScores,
      a0Score, rpmCompleteness, axisScores, stealthResistance,
    } = props;

    const flatDrives = driveScores?.map(d => d[0]) ?? [];

    return (
      <div
        ref={ref}
        style={{
          position: 'absolute',
          left: '-9999px',
          top: 0,
          width: '600px',
          background: '#0a0f1a',
          color: '#e2e8f0',
        }}
      >
        <div data-chart="gauge" style={{ width: 600, height: 200, padding: 16 }}>
          <NccsGauge composite={nccs.composite} certification={nccs.certification} nccs={nccs} />
        </div>

        <div data-chart="subscores" style={{ width: 600, height: 280, padding: 16 }}>
          <SubScoreBreakdown nccs={nccs} />
        </div>

        {operatorScores && (
          <div data-chart="radar" style={{ width: 600, height: 340, padding: 16 }}>
            <OperatorRadarChart scores={operatorScores} />
          </div>
        )}

        {operatorScores && domainAverages && (
          <div data-chart="heatmap" style={{ width: 600, height: 340, padding: 16 }}>
            <StateHeatmap operatorScores={operatorScores} domainAverages={domainAverages} />
          </div>
        )}

        {flatDrives.length > 0 && (
          <div data-chart="drives" style={{ width: 600, height: 340, padding: 16 }}>
            <CoreDriveTree driveScores={flatDrives} />
          </div>
        )}

        {driveScores && a0Score !== undefined && rpmCompleteness !== undefined && (
          <div data-chart="rpm" style={{ width: 600, height: 340, padding: 16 }}>
            <RpmGraph a0Score={a0Score} driveScores={driveScores} rpmCompleteness={rpmCompleteness} />
          </div>
        )}

        {axisScores && stealthResistance !== undefined && (
          <div data-chart="inversions" style={{ width: 600, height: 320, padding: 16 }}>
            <InversionMap axisScores={axisScores} stealthResistance={stealthResistance} />
          </div>
        )}
      </div>
    );
  },
);
