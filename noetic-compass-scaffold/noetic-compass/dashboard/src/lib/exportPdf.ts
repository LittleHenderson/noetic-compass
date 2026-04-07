/**
 * Generates a branded A4 PDF report with embedded chart images and tables.
 * Uses jsPDF for layout — no DOM rendering at export time.
 */

import { jsPDF } from 'jspdf';
import type { ReportData, ChartImages } from './reportData';

// ── Constants ──

const PAGE_W = 210; // A4 mm
const PAGE_H = 297;
const MARGIN = 15;
const CONTENT_W = PAGE_W - MARGIN * 2;
const TEAL: [number, number, number] = [45, 212, 191]; // #2dd4bf
const DARK: [number, number, number] = [10, 15, 26];
const WHITE: [number, number, number] = [226, 232, 240];
const GRAY: [number, number, number] = [148, 163, 184];
const RED: [number, number, number] = [248, 113, 113];

// ── Helpers ──

function addFooter(doc: jsPDF, page: number, totalPages: number) {
  doc.setFontSize(7);
  doc.setTextColor(...GRAY);
  doc.text('Noetic Compass | CAS v7.4 | Confidential', MARGIN, PAGE_H - 8);
  doc.text(`Page ${page} of ${totalPages}`, PAGE_W - MARGIN, PAGE_H - 8, { align: 'right' });
}

function sectionHeader(doc: jsPDF, y: number, title: string): number {
  doc.setFontSize(13);
  doc.setTextColor(...TEAL);
  doc.text(title, MARGIN, y);
  y += 2;
  doc.setDrawColor(...TEAL);
  doc.setLineWidth(0.3);
  doc.line(MARGIN, y, MARGIN + CONTENT_W, y);
  return y + 6;
}

function checkPage(doc: jsPDF, y: number, needed: number, pageCount: { n: number }): number {
  if (y + needed > PAGE_H - 20) {
    doc.addPage();
    pageCount.n++;
    return 20;
  }
  return y;
}

function addImage(doc: jsPDF, dataUrl: string | undefined, y: number, pageCount: { n: number }): number {
  if (!dataUrl) return y;
  const imgW = CONTENT_W;
  const imgH = imgW * 0.55; // roughly 600x330 aspect
  y = checkPage(doc, y, imgH + 5, pageCount);
  try {
    doc.addImage(dataUrl, 'PNG', MARGIN, y, imgW, imgH);
  } catch {
    // Skip image if it fails
  }
  return y + imgH + 5;
}

function tableHeader(
  doc: jsPDF, y: number, cols: { label: string; x: number; w: number }[],
): number {
  doc.setFillColor(21, 29, 51); // dark-700
  doc.rect(MARGIN, y - 4, CONTENT_W, 6, 'F');
  doc.setFontSize(8);
  doc.setTextColor(...TEAL);
  cols.forEach(c => doc.text(c.label, c.x, y));
  return y + 7;
}

function tableRow(
  doc: jsPDF, y: number, cols: { text: string; x: number }[],
  alt: boolean,
): number {
  if (alt) {
    doc.setFillColor(15, 22, 41); // dark-800
    doc.rect(MARGIN, y - 3.5, CONTENT_W, 5.5, 'F');
  }
  doc.setFontSize(8);
  doc.setTextColor(...WHITE);
  cols.forEach(c => doc.text(c.text, c.x, y));
  return y + 5.5;
}

// ── Main Export ──

export function exportPdf(data: ReportData, images: ChartImages): void {
  const doc = new jsPDF('p', 'mm', 'a4');
  const pageCount = { n: 1 };
  let y = 20;

  // ── Page 1: Header ──
  doc.setFillColor(...DARK);
  doc.rect(0, 0, PAGE_W, PAGE_H, 'F');

  // Title block
  doc.setFontSize(9);
  doc.setTextColor(...TEAL);
  doc.text('NOETIC COMPASS', MARGIN, y);
  y += 7;
  doc.setFontSize(18);
  doc.setTextColor(...WHITE);
  doc.text(data.title, MARGIN, y);
  y += 9;
  doc.setFontSize(9);
  doc.setTextColor(...GRAY);
  doc.text(`Date: ${data.date}  |  Model: ${data.model}  |  ID: ${data.assessmentId}`, MARGIN, y);
  y += 4;
  doc.text('Framework: CAS v7.4 — Corrected Edition  |  Confidential', MARGIN, y);
  y += 10;

  // ── Executive Summary ──
  y = sectionHeader(doc, y, 'Executive Summary');

  // NCCS score highlight
  doc.setFontSize(28);
  doc.setTextColor(...TEAL);
  doc.text(data.nccs.composite.toFixed(1), MARGIN, y + 2);
  doc.setFontSize(10);
  doc.setTextColor(...GRAY);
  doc.text('/ 100', MARGIN + 28, y + 2);

  doc.setFontSize(14);
  const certCol = certToColor(data.certLevel);
  doc.setTextColor(...certCol);
  doc.text(data.certLevel, MARGIN + 50, y + 2);
  y += 12;

  // Deployment recommendation
  doc.setFontSize(9);
  doc.setTextColor(...WHITE);
  const verdictLines = doc.splitTextToSize(data.verdict, CONTENT_W);
  doc.text(verdictLines, MARGIN, y);
  y += verdictLines.length * 4.5 + 3;

  doc.setFontSize(8);
  doc.setTextColor(...TEAL);
  doc.text(data.deploymentRecommendation, MARGIN, y);
  y += 8;

  // Strengths / Vulnerabilities side by side
  doc.setFontSize(9);
  doc.setTextColor(...WHITE);
  doc.text('Top Strengths:', MARGIN, y);
  doc.text('Top Vulnerabilities:', MARGIN + CONTENT_W / 2, y);
  y += 5;
  doc.setFontSize(8);
  doc.setTextColor(...GRAY);
  for (let i = 0; i < 3; i++) {
    if (data.topStrengths[i]) doc.text(`• ${data.topStrengths[i]}`, MARGIN + 2, y);
    if (data.topVulnerabilities[i]) doc.text(`• ${data.topVulnerabilities[i]}`, MARGIN + CONTENT_W / 2 + 2, y);
    y += 4.5;
  }
  y += 5;

  // Gauge + subscores images
  y = addImage(doc, images.gauge, y, pageCount);
  y = addImage(doc, images.subscores, y, pageCount);

  // ── Section 1: Operator Profile ──
  y = checkPage(doc, y, 80, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }
  y = sectionHeader(doc, y, '1. Cognitive Operator Profile');

  y = addImage(doc, images.radar, y, pageCount);
  if (y < 25) fillPageBg(doc);

  // Operator table
  y = checkPage(doc, y, 70, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }

  const opCols = [
    { label: 'Operator', x: MARGIN + 2, w: 60 },
    { label: 'Score', x: MARGIN + 90, w: 30 },
  ];
  y = tableHeader(doc, y, opCols);
  data.operators.forEach((op, i) => {
    y = checkPage(doc, y, 6, pageCount);
    if (y < 25) { fillPageBg(doc); y = 20; }
    y = tableRow(doc, y, [
      { text: op.label, x: opCols[0].x },
      { text: `${(op.score * 100).toFixed(1)}%`, x: opCols[1].x },
    ], i % 2 === 0);
  });
  y += 5;

  // Involution pairs
  doc.setFontSize(9);
  doc.setTextColor(...WHITE);
  doc.text('Involution Pair Balance:', MARGIN, y);
  y += 5;
  const pairCols = [
    { label: 'Pair', x: MARGIN + 2, w: 30 },
    { label: 'Score A', x: MARGIN + 35, w: 20 },
    { label: 'Score B', x: MARGIN + 60, w: 20 },
    { label: 'Gap', x: MARGIN + 85, w: 20 },
    { label: 'Status', x: MARGIN + 110, w: 20 },
  ];
  y = tableHeader(doc, y, pairCols);
  data.involutionPairs.forEach((p, i) => {
    y = checkPage(doc, y, 6, pageCount);
    if (y < 25) { fillPageBg(doc); y = 20; }
    doc.setTextColor(WHITE[0], WHITE[1], WHITE[2]);
    y = tableRow(doc, y, [
      { text: `${p.a} / ${p.b}`, x: pairCols[0].x },
      { text: `${(p.scoreA * 100).toFixed(1)}%`, x: pairCols[1].x },
      { text: `${(p.scoreB * 100).toFixed(1)}%`, x: pairCols[2].x },
      { text: `${(p.gap * 100).toFixed(0)}%`, x: pairCols[3].x },
      { text: p.flagged ? 'FLAGGED' : 'OK', x: pairCols[4].x },
    ], i % 2 === 0);
    // Color the status text after row
    if (p.flagged) {
      doc.setTextColor(RED[0], RED[1], RED[2]);
      doc.text('FLAGGED', pairCols[4].x, y - 5.5);
    }
  });
  y += 8;

  // ── Section 2: Domain Coherence ──
  y = checkPage(doc, y, 60, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }
  y = sectionHeader(doc, y, '2. Domain Coherence');

  y = addImage(doc, images.heatmap, y, pageCount);
  if (y < 25) fillPageBg(doc);

  y = checkPage(doc, y, 40, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }

  const domCols = [
    { label: 'Domain', x: MARGIN + 2, w: 40 },
    { label: 'Average', x: MARGIN + 60, w: 30 },
  ];
  y = tableHeader(doc, y, domCols);
  data.domains.forEach((d, i) => {
    y = tableRow(doc, y, [
      { text: d.label + (d.label === data.weakestDomain ? ' (weakest)' : ''), x: domCols[0].x },
      { text: `${(d.average * 100).toFixed(1)}%`, x: domCols[1].x },
    ], i % 2 === 0);
  });
  y += 3;
  doc.setFontSize(8);
  doc.setTextColor(...GRAY);
  doc.text(`DCI: ${(data.dci * 100).toFixed(1)}%  |  Weakest: ${data.weakestDomain}`, MARGIN, y);
  y += 8;

  // ── Section 3: Core Drive Integrity ──
  y = checkPage(doc, y, 70, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }
  y = sectionHeader(doc, y, '3. Core Drive Integrity');

  y = addImage(doc, images.drives, y, pageCount);
  if (y < 25) fillPageBg(doc);

  y = checkPage(doc, y, 55, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }

  const drvCols = [
    { label: 'Drive', x: MARGIN + 2, w: 50 },
    { label: 'Score', x: MARGIN + 60, w: 25 },
    { label: 'Status', x: MARGIN + 100, w: 25 },
  ];
  y = tableHeader(doc, y, drvCols);
  data.drives.forEach((d, i) => {
    y = tableRow(doc, y, [
      { text: d.label, x: drvCols[0].x },
      { text: `${(d.score * 100).toFixed(1)}%`, x: drvCols[1].x },
      { text: d.flagged ? 'CONCERN' : 'OK', x: drvCols[2].x },
    ], i % 2 === 0);
  });
  y += 8;

  // ── Section 4: RPM Analysis ──
  y = checkPage(doc, y, 50, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }
  y = sectionHeader(doc, y, '4. RPM Analysis');

  y = addImage(doc, images.rpm, y, pageCount);
  if (y < 25) fillPageBg(doc);

  y = checkPage(doc, y, 20, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }

  doc.setFontSize(9);
  doc.setTextColor(...WHITE);
  doc.text(`RPM Completeness: ${(data.rpmCompleteness * 100).toFixed(1)}%`, MARGIN, y);
  y += 5;
  if (data.brokenChains.length > 0) {
    doc.setFontSize(8);
    doc.setTextColor(...RED);
    doc.text(`Broken Chains: ${data.brokenChains.join(', ')}`, MARGIN, y);
    y += 5;
  }
  y += 5;

  // ── Section 5: Inversion Analysis ──
  y = checkPage(doc, y, 70, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }
  y = sectionHeader(doc, y, '5. Inversion Analysis');

  y = addImage(doc, images.inversions, y, pageCount);
  if (y < 25) fillPageBg(doc);

  y = checkPage(doc, y, 60, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }

  const invCols = [
    { label: 'Axis', x: MARGIN + 2, w: 50 },
    { label: 'Score', x: MARGIN + 70, w: 25 },
  ];
  y = tableHeader(doc, y, invCols);
  data.inversions.forEach((inv, i) => {
    y = tableRow(doc, y, [
      { text: inv.label, x: invCols[0].x },
      { text: `${(inv.score * 100).toFixed(1)}%`, x: invCols[1].x },
    ], i % 2 === 0);
  });
  y += 3;
  doc.setFontSize(8);
  doc.setTextColor(...GRAY);
  doc.text(`Stealth Resistance: ${(data.stealthResistance * 100).toFixed(1)}%`, MARGIN, y);
  y += 8;

  // ── Section 6: Pipeline Trace ──
  y = checkPage(doc, y, 60, pageCount);
  if (y < 25) { fillPageBg(doc); y = 20; }
  y = sectionHeader(doc, y, '6. Pipeline Trace');

  const stgCols = [
    { label: 'Stage', x: MARGIN + 2, w: 50 },
    { label: 'Status', x: MARGIN + 80, w: 25 },
  ];
  y = tableHeader(doc, y, stgCols);
  data.stages.forEach((s, i) => {
    const statusLabel = s.status === 'pass' ? 'PASS' : s.status === 'flag' ? 'FLAG' : 'BLOCK';
    y = tableRow(doc, y, [
      { text: s.name, x: stgCols[0].x },
      { text: statusLabel, x: stgCols[1].x },
    ], i % 2 === 0);
  });

  // ── Add dark backgrounds to all pages and footers ──
  const total = pageCount.n;
  for (let p = 1; p <= total; p++) {
    doc.setPage(p);
    addFooter(doc, p, total);
  }

  // Save
  const filename = `noetic-assessment-${data.date.replace(/[/:, ]/g, '-')}.pdf`;
  doc.save(filename);
}

function fillPageBg(doc: jsPDF) {
  doc.setFillColor(...DARK);
  doc.rect(0, 0, PAGE_W, PAGE_H, 'F');
}

function certToColor(cert: string): [number, number, number] {
  switch (cert) {
    case 'Platinum': return [34, 211, 238];
    case 'Gold': return [251, 191, 36];
    case 'Silver': return [148, 163, 184];
    case 'Bronze': return [251, 146, 60];
    default: return [239, 68, 68];
  }
}
