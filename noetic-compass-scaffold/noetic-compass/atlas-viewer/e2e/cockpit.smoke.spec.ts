import { test, expect } from '@playwright/test';

// Atlas Viewer Wave 3 smoke spec.
// Selects via existing data-testids only; production component code is not
// modified. Notes on testid coverage:
// - ControlBar exposes `data-testid="control-bar"` (not `atlas-viewer-control-bar`).
//   The smoke spec uses the existing testid; renaming/aliasing is deferred.
// - NeuralNetScene wires WebGL pointer events directly; the production code
//   does not expose a click hook reachable from Playwright without simulating
//   a real WebGL hit. Test 3 documents this as a wave-4 follow-up.

test('cockpit page renders all five panels', async ({ page }) => {
  await page.goto('/cockpit');
  await expect(page.getByTestId('cockpit-page')).toBeVisible();
  // ControlBar — production testid is `control-bar`, not the spec's
  // `atlas-viewer-control-bar`. TODO(wave-4): add wrapper testid if a
  // shell-level selector is preferred.
  await expect(page.getByTestId('control-bar')).toBeVisible();
  await expect(page.getByTestId('atlas-viewer-center')).toBeVisible();
  await expect(page.getByTestId('atlas-viewer-right')).toBeVisible();
  await expect(page.getByTestId('mode7-timeline')).toBeVisible();
  await expect(page.getByTestId('atlas-viewer-left')).toBeVisible();
});

test('Spatial Evidence tab shows demo primitives at token 5', async ({ page }) => {
  await page.goto('/cockpit');
  const canvas = page.getByTestId('visual-primitive-canvas');
  await expect(canvas).toBeVisible();
  await expect(canvas.locator('img')).toBeVisible();

  // Scrub to token 5 via the per-cell testid emitted by Mode7Timeline.
  await page.getByTestId('mode7-timeline-cell-5').click();

  const primitives = canvas.locator('[data-primitive-id]');
  await expect(primitives.first()).toBeVisible({ timeout: 5_000 });

  await page.screenshot({
    path: 'test-results/cockpit-token5-spatial.png',
    fullPage: true,
  });
});

test('click neuron opens EvidenceDrawer', async ({ page }) => {
  // NeuralNetScene's production build does not expose a Playwright-reachable
  // click hook on individual neurons — picking goes through a Three.js
  // Raycaster against an InstancedMesh. The `__nn_simulate_click` test surface
  // is gated on `rendererFactory` being passed (unit-test path only). To click
  // a real neuron we'd need to (a) add a Playwright-visible click target on
  // the canvas wrapper or (b) ship a production-side debug hook.
  // TODO(wave-4): add a `data-testid="neuralnet-test-click"` button on the
  // shell (gated by ?e2e=1 query param) that dispatches a synthetic
  // NeuronCoord click for E2E coverage.
  test.skip(
    true,
    'NeuralNetScene click requires a production-side E2E hook (wave-4 follow-up).',
  );
  await page.goto('/cockpit');
  await expect(page.getByTestId('evidence-drawer')).toHaveAttribute(
    'data-open',
    'true',
  );
});
