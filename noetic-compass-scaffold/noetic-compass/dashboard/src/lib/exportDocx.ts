/**
 * Generates a branded DOCX report with headings, tables, and embedded chart images.
 * Uses the `docx` package for programmatic Word document generation.
 */

import {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, HeadingLevel, AlignmentType, BorderStyle, ImageRun,
  ShadingType, Footer, PageNumber, NumberFormat,
} from 'docx';
import { saveAs } from 'file-saver';
import type { ReportData, ChartImages } from './reportData';

// ── Constants ──

const TEAL = '2DD4BF';
const DARK = '0A0F1A';
const GRAY = '94A3B8';
const WHITE_TEXT = 'E2E8F0';
const RED = 'F87171';

// ── Helpers ──

function pct(n: number, decimals = 1): string {
  return `${(n * 100).toFixed(decimals)}%`;
}

function heading(text: string, level: typeof HeadingLevel[keyof typeof HeadingLevel]) {
  return new Paragraph({
    heading: level,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, color: TEAL, bold: true })],
  });
}

function textPara(text: string, opts?: { bold?: boolean; color?: string; size?: number }) {
  return new Paragraph({
    spacing: { after: 80 },
    children: [new TextRun({
      text,
      color: opts?.color ?? WHITE_TEXT,
      bold: opts?.bold,
      size: opts?.size ?? 20,
    })],
  });
}

function bulletPara(text: string) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 40 },
    children: [new TextRun({ text, color: WHITE_TEXT, size: 20 })],
  });
}

function makeCell(text: string, opts?: { bold?: boolean; color?: string; shading?: string; width?: number }) {
  return new TableCell({
    width: opts?.width ? { size: opts.width, type: WidthType.DXA } : undefined,
    shading: opts?.shading ? { type: ShadingType.SOLID, color: opts.shading } : undefined,
    children: [new Paragraph({
      children: [new TextRun({ text, color: opts?.color ?? WHITE_TEXT, bold: opts?.bold, size: 18 })],
    })],
  });
}

function headerRow(labels: string[]) {
  return new TableRow({
    children: labels.map(l => makeCell(l, { bold: true, color: TEAL, shading: '151D33' })),
  });
}

function dataRow(cells: string[], alt: boolean, flagIdx?: number) {
  return new TableRow({
    children: cells.map((text, i) => makeCell(text, {
      shading: alt ? '0F1629' : undefined,
      color: i === flagIdx && text !== 'OK' ? RED : WHITE_TEXT,
    })),
  });
}

function simpleTable(headers: string[], rows: string[][]) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 1, color: '1B2540' },
      bottom: { style: BorderStyle.SINGLE, size: 1, color: '1B2540' },
      left: { style: BorderStyle.SINGLE, size: 1, color: '1B2540' },
      right: { style: BorderStyle.SINGLE, size: 1, color: '1B2540' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: '1B2540' },
      insideVertical: { style: BorderStyle.SINGLE, size: 1, color: '1B2540' },
    },
    rows: [
      headerRow(headers),
      ...rows.map((r, i) => dataRow(r, i % 2 === 0)),
    ],
  });
}

function base64ToUint8Array(dataUrl: string): Uint8Array {
  const base64 = dataUrl.split(',')[1];
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function chartImage(dataUrl: string | undefined): Paragraph | null {
  if (!dataUrl) return null;
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    alignment: AlignmentType.CENTER,
    children: [new ImageRun({
      data: base64ToUint8Array(dataUrl),
      transformation: { width: 540, height: 297 },
      type: 'png',
    })],
  });
}

// ── Main Export ──

export async function exportDocx(data: ReportData, images: ChartImages): Promise<void> {
  const children: (Paragraph | Table)[] = [];

  // Title
  children.push(new Paragraph({
    spacing: { after: 40 },
    children: [new TextRun({ text: 'NOETIC COMPASS — RESEARCH PROTOTYPE', color: TEAL, bold: true, size: 18 })],
  }));
  children.push(heading(data.title, HeadingLevel.TITLE));
  children.push(textPara(
    `Date: ${data.date}  |  Model: ${data.model}  |  ID: ${data.assessmentId}`,
    { color: GRAY, size: 18 },
  ));
  children.push(textPara('Framework: CAS v7.4 — Corrected Edition  |  Confidential', { color: GRAY, size: 18 }));
  children.push(textPara('Status: Research Prototype / Not validated', { color: RED, size: 18, bold: true }));
  children.push(textPara(
    `Scoring: ${data.scoringMethodLabel}  |  Scorer: ${data.scorerProvider ?? 'Not used'}  |  Model: ${data.scorerModel ?? 'Not provided'}`,
    { color: GRAY, size: 18 },
  ));
  children.push(textPara(`Scoring Summary: ${data.scoringSummary}`, { color: GRAY, size: 18 }));
  if (data.unmeasuredDimensions.length > 0) {
    children.push(textPara(
      `Unmeasured dimensions: ${data.unmeasuredDimensions.join(', ')}`,
      { color: GRAY, size: 18 },
    ));
  }

  // AI Executive Briefing
  if (data.interpretation) {
    children.push(heading('AI Executive Briefing', HeadingLevel.HEADING_1));
    children.push(textPara('THE BOTTOM LINE', { bold: true, color: TEAL }));
    children.push(textPara(data.interpretation.bottom_line));
    children.push(textPara('WHAT WE FOUND', { bold: true, color: TEAL }));
    data.interpretation.findings.forEach(f => children.push(textPara(f, { color: GRAY })));
    children.push(textPara('WHAT WE RECOMMEND', { bold: true, color: TEAL }));
    data.interpretation.recommendations.forEach(r => children.push(bulletPara(r)));
  }

  // Executive Summary
  children.push(heading('Executive Summary', HeadingLevel.HEADING_1));
  children.push(textPara(
    `NCCS Composite Score: ${data.nccs.composite.toFixed(1)} / 100  —  ${data.certLevel}`,
    { bold: true, color: TEAL, size: 28 },
  ));
  children.push(textPara(data.verdict));
  children.push(textPara(data.deploymentRecommendation, { bold: true, color: TEAL }));
  children.push(textPara('Top Strengths:', { bold: true }));
  data.topStrengths.forEach(s => children.push(bulletPara(s)));
  children.push(textPara('Top Vulnerabilities:', { bold: true }));
  data.topVulnerabilities.forEach(v => children.push(bulletPara(v)));

  const gaugeImg = chartImage(images.gauge);
  if (gaugeImg) children.push(gaugeImg);
  const subImg = chartImage(images.subscores);
  if (subImg) children.push(subImg);

  // 1. Operator Profile
  children.push(heading('1. Cognitive Operator Profile', HeadingLevel.HEADING_1));
  const radarImg = chartImage(images.radar);
  if (radarImg) children.push(radarImg);

  children.push(simpleTable(
    ['Operator', 'Score'],
    data.operators.map(op => [op.label, pct(op.score)]),
  ));

  children.push(textPara('Involution Pair Balance:', { bold: true }));
  children.push(simpleTable(
    ['Pair', 'Score A', 'Score B', 'Gap', 'Status'],
    data.involutionPairs.map(p => [
      `${p.a} / ${p.b}`, pct(p.scoreA), pct(p.scoreB), pct(p.gap, 0), p.flagged ? 'FLAGGED' : 'OK',
    ]),
  ));

  // 2. Domain Coherence
  children.push(heading('2. Domain Coherence', HeadingLevel.HEADING_1));
  const heatImg = chartImage(images.heatmap);
  if (heatImg) children.push(heatImg);

  children.push(simpleTable(
    ['Domain', 'Average'],
    data.domains.map(d => [
      d.label + (d.label === data.weakestDomain ? ' (weakest)' : ''),
      pct(d.average),
    ]),
  ));
  children.push(textPara(`DCI: ${pct(data.dci)}  |  Weakest: ${data.weakestDomain}`, { color: GRAY }));

  // 3. Core Drives
  children.push(heading('3. Core Drive Integrity', HeadingLevel.HEADING_1));
  const drvImg = chartImage(images.drives);
  if (drvImg) children.push(drvImg);

  children.push(simpleTable(
    ['Drive', 'Score', 'Status'],
    data.drives.map(d => [d.label, pct(d.score), d.flagged ? 'CONCERN' : 'OK']),
  ));

  // 4. RPM
  children.push(heading('4. RPM Analysis', HeadingLevel.HEADING_1));
  const rpmImg = chartImage(images.rpm);
  if (rpmImg) children.push(rpmImg);

  children.push(textPara(`RPM Completeness: ${pct(data.rpmCompleteness)}`));
  if (data.brokenChains.length > 0) {
    children.push(textPara('Broken Chains:', { color: RED }));
    data.brokenChains.forEach(c => children.push(bulletPara(c)));
  } else {
    children.push(textPara('All 7 RPM chains are intact.'));
  }

  // 5. Inversions
  children.push(heading('5. Inversion Analysis', HeadingLevel.HEADING_1));
  const invImg = chartImage(images.inversions);
  if (invImg) children.push(invImg);

  children.push(simpleTable(
    ['Axis', 'Score'],
    data.inversions.map(inv => [inv.label, pct(inv.score)]),
  ));
  children.push(textPara(`Stealth Resistance: ${pct(data.stealthResistance)}`, { color: GRAY }));

  // 6. Pipeline Trace
  children.push(heading('6. Pipeline Trace', HeadingLevel.HEADING_1));
  children.push(simpleTable(
    ['Stage', 'Status'],
    data.stages.map(s => {
      const label = s.status === 'pass' ? 'PASS' : s.status === 'flag' ? 'FLAG' : 'BLOCK';
      return [s.name, label];
    }),
  ));

  // Build document
  const doc = new Document({
    background: { color: DARK },
    sections: [{
      properties: {
        page: {
          pageNumbers: { start: 1 },
        },
      },
      headers: {},
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: 'Noetic Compass (Research Prototype) | CAS v7.4 | Research-stage scoring — empirical validation pending  —  Page ', color: GRAY, size: 14 }),
              new TextRun({ children: [PageNumber.CURRENT], color: GRAY, size: 14 }),
              new TextRun({ text: ' of ', color: GRAY, size: 14 }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], color: GRAY, size: 14 }),
            ],
          })],
        }),
      },
      children,
    }],
    numbering: {
      config: [{
        reference: 'bullet-list',
        levels: [{
          level: 0,
          format: NumberFormat.BULLET,
          text: '\u2022',
          alignment: AlignmentType.LEFT,
        }],
      }],
    },
  });

  const blob = await Packer.toBlob(doc);
  const filename = `noetic-assessment-${data.date.replace(/[/:, ]/g, '-')}.docx`;
  saveAs(blob, filename);
}
