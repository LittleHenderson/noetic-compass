/**
 * Exports assessment report as a downloadable Markdown file.
 * Pure string generation with no DOM dependencies.
 */

import { saveAs } from 'file-saver';
import type { ReportData } from './reportData';

function pad(text: string, length: number): string {
  return text.length >= length ? text.slice(0, length) : text + ' '.repeat(length - text.length);
}

function padNum(value: number, decimals = 1): string {
  return (value * 100).toFixed(decimals) + '%';
}

function tableRow(cells: string[], widths: number[]): string {
  return '| ' + cells.map((cell, index) => pad(cell, widths[index])).join(' | ') + ' |';
}

function tableSep(widths: number[]): string {
  return '| ' + widths.map((width) => '-'.repeat(width)).join(' | ') + ' |';
}

export function generateMarkdown(data: ReportData): string {
  const lines: string[] = [];

  lines.push(`# Noetic Compass - ${data.title}`);
  lines.push('');
  lines.push(`**Date:** ${data.date}  `);
  lines.push(`**Model:** ${data.model}  `);
  lines.push(`**Assessment ID:** ${data.assessmentId}  `);
  lines.push(`**Framework:** CAS v7.4 - Corrected Edition  `);
  lines.push('**Status:** Research Prototype / Not validated  ');
  lines.push(`**Scoring Method:** ${data.scoringMethodLabel}  `);
  lines.push(`**Scorer Provider:** ${data.scorerProvider ?? 'Not used'}  `);
  lines.push(`**Scorer Model:** ${data.scorerModel ?? 'Not provided'}  `);
  lines.push('**Classification:** Confidential');
  lines.push('');
  lines.push(`**Scoring Summary:** ${data.scoringSummary}`);
  lines.push('');
  if (data.unmeasuredDimensions.length > 0) {
    lines.push(`**Unmeasured Dimensions:** ${data.unmeasuredDimensions.join(', ')}`);
    lines.push('');
  }

  if (data.interpretation) {
    lines.push('## AI Executive Briefing');
    lines.push('');
    lines.push('### The Bottom Line');
    lines.push('');
    lines.push(data.interpretation.bottom_line);
    lines.push('');
    lines.push('### What We Found');
    lines.push('');
    data.interpretation.findings.forEach((finding) => lines.push(`- ${finding}`));
    lines.push('');
    lines.push('### What We Recommend');
    lines.push('');
    data.interpretation.recommendations.forEach((recommendation) => lines.push(`- ${recommendation}`));
    lines.push('');
  }

  lines.push('## Executive Summary');
  lines.push('');
  lines.push(`**NCCS Composite Score:** ${data.nccs.composite.toFixed(1)} / 100  `);
  lines.push(`**Research Tier:** ${data.certLevel}  `);
  lines.push(`**Research Guidance:** ${data.deploymentRecommendation}`);
  lines.push('');
  lines.push(`> ${data.verdict}`);
  lines.push('');
  lines.push('**Top 3 Strengths:**');
  data.topStrengths.forEach((strength) => lines.push(`- ${strength}`));
  lines.push('');
  lines.push('**Top 3 Vulnerabilities:**');
  data.topVulnerabilities.forEach((vulnerability) => lines.push(`- ${vulnerability}`));
  lines.push('');

  if (data.blindSpots.length > 0) {
    lines.push('**Cognitive Blind Spots:**');
    data.blindSpots.forEach((spot) => {
      lines.push(`- **${spot.label}** (${spot.severity}) - ${spot.risk}`);
    });
    lines.push('');
  }

  lines.push('## 1. Cognitive Operator Profile');
  lines.push('');
  const operatorWidths = [25, 8];
  lines.push(tableRow(['Operator', 'Score'], operatorWidths));
  lines.push(tableSep(operatorWidths));
  data.operators.forEach((operator) => {
    lines.push(tableRow([operator.label, padNum(operator.score)], operatorWidths));
  });
  lines.push('');
  lines.push('**Involution Pair Balance:**');
  lines.push('');
  const pairWidths = [12, 8, 8, 8, 8];
  lines.push(tableRow(['Pair', 'Score A', 'Score B', 'Gap', 'Status'], pairWidths));
  lines.push(tableSep(pairWidths));
  data.involutionPairs.forEach((pair) => {
    lines.push(tableRow([
      `${pair.a}/${pair.b}`,
      padNum(pair.scoreA),
      padNum(pair.scoreB),
      padNum(pair.gap, 0),
      pair.flagged ? 'FLAGGED' : 'OK',
    ], pairWidths));
  });
  lines.push('');

  lines.push('## 2. Domain Coherence');
  lines.push('');
  const domainWidths = [24, 8];
  lines.push(tableRow(['Domain', 'Average'], domainWidths));
  lines.push(tableSep(domainWidths));
  data.domains.forEach((domain) => {
    const suffix = domain.label === data.weakestDomain ? ' (weakest)' : '';
    lines.push(tableRow([domain.label + suffix, padNum(domain.average)], domainWidths));
  });
  lines.push('');
  lines.push(`**DCI (Domain Coherence Index):** ${(data.dci * 100).toFixed(1)}%  `);
  lines.push(`**Weakest Domain:** ${data.weakestDomain}`);
  lines.push('');

  lines.push('## 3. Core Drive Integrity');
  lines.push('');
  const driveWidths = [18, 8, 8];
  lines.push(tableRow(['Drive', 'Score', 'Status'], driveWidths));
  lines.push(tableSep(driveWidths));
  data.drives.forEach((drive) => {
    lines.push(tableRow([drive.label, padNum(drive.score), drive.flagged ? 'CONCERN' : 'OK'], driveWidths));
  });
  lines.push('');

  lines.push('## 4. RPM Analysis');
  lines.push('');
  lines.push(`**RPM Completeness:** ${(data.rpmCompleteness * 100).toFixed(1)}%`);
  lines.push('');
  if (data.brokenChains.length > 0) {
    lines.push('**Broken Chains:**');
    data.brokenChains.forEach((chain) => lines.push(`- ${chain}`));
  } else {
    lines.push('All 7 RPM chains are intact.');
  }
  lines.push('');

  lines.push('## 5. Inversion Analysis');
  lines.push('');
  const inversionWidths = [18, 8];
  lines.push(tableRow(['Axis', 'Score'], inversionWidths));
  lines.push(tableSep(inversionWidths));
  data.inversions.forEach((inversion) => {
    lines.push(tableRow([inversion.label, padNum(inversion.score)], inversionWidths));
  });
  lines.push('');
  lines.push(`**Stealth Resistance:** ${(data.stealthResistance * 100).toFixed(1)}%`);
  lines.push('');

  lines.push('## 6. Pipeline Trace');
  lines.push('');
  const stageWidths = [20, 8];
  lines.push(tableRow(['Stage', 'Status'], stageWidths));
  lines.push(tableSep(stageWidths));
  data.stages.forEach((stage) => {
    const statusLabel = stage.status === 'pass' ? 'PASS' : stage.status === 'flag' ? 'FLAG' : 'BLOCK';
    lines.push(tableRow([stage.name, statusLabel], stageWidths));
  });
  lines.push('');

  lines.push('## Disclaimer');
  lines.push('');
  lines.push('This report is generated by a research prototype. Scores are produced by the');
  lines.push(`stated scoring method (${data.scoringMethodLabel}) and have not been empirically`);
  lines.push('validated. Do not use this report as a sole basis for deployment or safety decisions.');
  if (data.unmeasuredDimensions.length > 0) {
    lines.push(`Unmeasured dimensions in this run: ${data.unmeasuredDimensions.join(', ')}.`);
  }
  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push('*Generated by Noetic Compass (Research Prototype) | CAS v7.4 - Corrected Edition | Confidential*');

  return lines.join('\n');
}

export function exportMarkdown(data: ReportData): void {
  const markdown = generateMarkdown(data);
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const filename = `noetic-assessment-${data.date.replace(/[/:, ]/g, '-')}.md`;
  saveAs(blob, filename);
}
