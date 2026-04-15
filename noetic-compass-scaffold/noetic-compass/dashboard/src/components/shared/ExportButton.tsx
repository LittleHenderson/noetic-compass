/**
 * Export Results button with dropdown for PDF, DOCX, Markdown formats.
 * Heavy libraries (jspdf, docx, html2canvas) are loaded dynamically
 * on first export — not bundled with the main app.
 */

import { useState, useRef, useEffect, useCallback, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import type { WrapResult } from '../../api/types';
import { extractReportData } from '../../lib/reportData';
import type { HiddenReportChartsProps } from './HiddenReportCharts';

type ExportFormat = 'pdf' | 'docx' | 'md';

interface ExportButtonProps {
  result: WrapResult;
  text: string;
  timestamp: string;
}

const FORMAT_OPTIONS: { key: ExportFormat; label: string; icon: string }[] = [
  { key: 'pdf', label: 'PDF Report', icon: 'PDF' },
  { key: 'docx', label: 'Word Document', icon: 'DOC' },
  { key: 'md', label: 'Markdown', icon: 'MD' },
];

export function ExportButton({ result, text, timestamp }: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCharts, setShowCharts] = useState(false);
  const [HiddenReportChartsComponent, setHiddenReportChartsComponent] =
    useState<ForwardRefExoticComponent<HiddenReportChartsProps & RefAttributes<HTMLDivElement>> | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Extract stage data for chart rendering
  const operatorScores = result.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
  const domainAverages = result.stages.find(s => s.stage === 'domain_coherence')?.data?.domain_averages as number[] | undefined;
  const driveScores = result.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
  const a0Score = result.stages.find(s => s.stage === 'rpm_gate')?.data?.a0_score as number | undefined;
  const rpmCompleteness = result.stages.find(s => s.stage === 'rpm_gate')?.data?.rpm_completeness as number | undefined;
  const axisScores = result.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
  const stealthResistance = result.stages.find(s => s.stage === 'inversion_scan')?.data?.stealth_resistance as number | undefined;

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const handleExport = useCallback(async (format: ExportFormat) => {
    setOpen(false);
    setLoading(true);

    try {
      const data = extractReportData(result, text, timestamp);

      if (format === 'md') {
        const { exportMarkdown } = await import('../../lib/exportMarkdown');
        exportMarkdown(data);
        setLoading(false);
        return;
      }

      // For PDF/DOCX, mount hidden charts, capture images, then generate
      if (!HiddenReportChartsComponent) {
        const chartsModule = await import('./HiddenReportCharts');
        setHiddenReportChartsComponent(() => chartsModule.HiddenReportCharts);
      }

      setShowCharts(true);

      // Wait for charts to render
      await new Promise(resolve => setTimeout(resolve, 500));

      let images = {};
      if (chartRef.current) {
        const { captureChartImages } = await import('../../lib/chartCapture');
        images = await captureChartImages(chartRef.current);
      }

      setShowCharts(false);

      if (format === 'pdf') {
        const { exportPdf } = await import('../../lib/exportPdf');
        await exportPdf(data, images);
      } else {
        const { exportDocx } = await import('../../lib/exportDocx');
        await exportDocx(data, images);
      }
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setLoading(false);
      setShowCharts(false);
    }
  }, [HiddenReportChartsComponent, result, text, timestamp]);

  const HiddenCharts = HiddenReportChartsComponent;

  return (
    <>
      <div ref={dropdownRef} className="relative inline-block">
        <button
          onClick={() => setOpen(!open)}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-300 hover:text-slate-100 hover:bg-white/[0.08] hover:border-accent-teal/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all min-h-[44px]"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Generating...
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path d="M2.5 4L5 6.5L7.5 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </>
          )}
        </button>

        {open && (
          <div className="absolute right-0 top-full mt-1 z-50 min-w-[160px] rounded-lg border border-white/[0.08] bg-dark-800/95 backdrop-blur-sm shadow-xl overflow-hidden animate-chart-in">
            {FORMAT_OPTIONS.map(opt => (
              <button
                key={opt.key}
                onClick={() => handleExport(opt.key)}
                className="flex items-center gap-3 w-full px-3 py-3 text-left text-xs text-slate-300 hover:text-slate-100 hover:bg-white/[0.06] transition-colors min-h-[44px]"
              >
                <span className="inline-flex items-center justify-center w-7 h-5 rounded bg-white/[0.06] text-[9px] font-bold tracking-wider text-accent-teal">
                  {opt.icon}
                </span>
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {showCharts && HiddenCharts && (
        <HiddenCharts
          ref={chartRef}
          nccs={result.nccs}
          operatorScores={operatorScores}
          domainAverages={domainAverages}
          driveScores={driveScores}
          a0Score={a0Score}
          rpmCompleteness={rpmCompleteness}
          axisScores={axisScores}
          stealthResistance={stealthResistance}
        />
      )}
    </>
  );
}
