/**
 * Captures chart elements from a hidden DOM container as base64 images.
 * Uses html2canvas to render each chart section, loaded only when export runs.
 */

import type { ChartImages } from './reportData';

const CHART_KEYS: (keyof ChartImages)[] = [
  'gauge', 'subscores', 'radar', 'heatmap', 'drives', 'rpm', 'inversions',
];

export async function captureChartImages(
  containerRef: HTMLDivElement,
): Promise<ChartImages> {
  const { default: html2canvas } = await import('html2canvas');
  const images: ChartImages = {};

  for (const key of CHART_KEYS) {
    const el = containerRef.querySelector<HTMLElement>(`[data-chart="${key}"]`);
    if (!el) continue;

    try {
      const canvas = await html2canvas(el, {
        backgroundColor: '#0a0f1a',
        scale: 2,
        logging: false,
        useCORS: true,
      });
      images[key] = canvas.toDataURL('image/png');
    } catch {
      // Skip charts that fail to render
    }
  }

  return images;
}
