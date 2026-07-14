import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { prerenderClaimSurfaces } from './prerender-claim-surfaces.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const CONTENT_PATH = resolve(HERE, '..', 'src', 'claimSurfaces.json');
const RENDER_ROUTES_PATH = resolve(HERE, '..', 'render-route-rules.json');
const BASE_HTML = [
  '<!doctype html><html lang="en"><head><meta charset="UTF-8" />',
  '<title>Atlas Viewer - Alpha</title>',
  '<meta name="description" content="Private alpha preview." />',
  '</head><body><div id="root"></div>',
  '<script type="module" crossorigin src="/assets/index-abc123.js"></script>',
  '</body></html>',
].join('');

async function fixture() {
  const directory = await mkdtemp(resolve(tmpdir(), 'atlas-claim-prerender-'));
  await writeFile(resolve(directory, 'index.html'), BASE_HTML, 'utf8');
  return directory;
}

test('writes deterministic exact-route documents and a neutral SPA fallback', async (context) => {
  const firstDir = await fixture();
  const secondDir = await fixture();
  context.after(() =>
    Promise.all([
      rm(firstDir, { recursive: true, force: true }),
      rm(secondDir, { recursive: true, force: true }),
    ]),
  );

  const [first, second] = await Promise.all([
    prerenderClaimSurfaces({ distDir: firstDir, contentPath: CONTENT_PATH }),
    prerenderClaimSurfaces({ distDir: secondDir, contentPath: CONTENT_PATH }),
  ]);
  assert.equal(first.schemaVersion, 'cas_claim_surface.v1');
  assert.deepEqual(
    first.outputs.map(({ kind, route, output }) => ({ kind, route, output })),
    [
      { kind: 'product_app', route: '/', output: 'index.html' },
      {
        kind: 'audit_console',
        route: '/audit-console',
        output: 'audit-console/index.html',
      },
    ],
  );

  const [product, audit, spa, productAgain, auditAgain] = await Promise.all([
    readFile(resolve(firstDir, 'index.html'), 'utf8'),
    readFile(resolve(firstDir, 'audit-console', 'index.html'), 'utf8'),
    readFile(resolve(firstDir, 'spa.html'), 'utf8'),
    readFile(resolve(secondDir, 'index.html'), 'utf8'),
    readFile(resolve(secondDir, 'audit-console', 'index.html'), 'utf8'),
  ]);

  assert.equal(product, productAgain);
  assert.equal(audit, auditAgain);
  assert.match(product, /data-cas-prerendered-route="\/"/);
  assert.match(product, /data-cas-prerender-kind="product_app"/);
  assert.match(product, /<h1[^>]*>Atlas Model Audit<\/h1>/);
  assert.match(product, /Customer-production status: OPEN\./);
  assert.match(audit, /data-cas-prerendered-route="\/audit-console"/);
  assert.match(audit, /data-cas-prerender-kind="audit_console"/);
  assert.match(audit, /<h1[^>]*>Audit Console<\/h1>/);
  assert.match(audit, /FLAG_FOR_HUMAN_REVIEW/);

  for (const html of [product, audit]) {
    assert.match(html, /data-cas-prerender-schema="cas_claim_surface\.v1"/);
    assert.match(
      html,
      /<script type="module" crossorigin src="\/assets\/index-abc123\.js"><\/script>/,
    );
    assert.doesNotMatch(html, /<noscript\b/i);
    assert.doesNotMatch(
      html,
      /data-cas-static-claim-surface[^>]*\shidden(?:\s|=|>)/i,
    );
    assert.doesNotMatch(
      html,
      /data-cas-static-claim-surface[^>]*aria-hidden="true"/i,
    );
  }
  assert.notEqual(product, audit);
  assert.equal(spa, BASE_HTML);
  assert.match(spa, /<div id="root"><\/div>/);
  assert.doesNotMatch(spa, /data-cas-prerendered-route/);
  assert.doesNotMatch(spa, /data-cas-static-claim-surface/);

  assert.deepEqual(
    first.outputs.map(({ html }) => html),
    second.outputs.map(({ html }) => html),
  );
});

test('fails closed when content attempts to move a pinned route', async (context) => {
  const distDir = await fixture();
  context.after(() => rm(distDir, { recursive: true, force: true }));
  const content = JSON.parse(await readFile(CONTENT_PATH, 'utf8'));
  content.surfaces.audit_console.route = '/generic-fallback';
  const invalidContentPath = resolve(distDir, 'invalid-content.json');
  await writeFile(invalidContentPath, JSON.stringify(content), 'utf8');

  await assert.rejects(
    prerenderClaimSurfaces({ distDir, contentPath: invalidContentPath }),
    /must use its exact pinned route/,
  );
});

test('fails closed when a pinned route uses the generic login heading', async (context) => {
  const distDir = await fixture();
  context.after(() => rm(distDir, { recursive: true, force: true }));
  const content = JSON.parse(await readFile(CONTENT_PATH, 'utf8'));
  content.surfaces.product_app.heading = 'Log in to Noetic Compass';
  const invalidContentPath = resolve(distDir, 'invalid-heading.json');
  await writeFile(invalidContentPath, JSON.stringify(content), 'utf8');

  await assert.rejects(
    prerenderClaimSurfaces({ distDir, contentPath: invalidContentPath }),
    /cannot use the generic login heading/,
  );
});

test('fails closed when the Vite application mount is missing or duplicated', async (context) => {
  const distDir = await fixture();
  context.after(() => rm(distDir, { recursive: true, force: true }));
  await writeFile(
    resolve(distDir, 'index.html'),
    BASE_HTML.replace('</body>', '<div id="root"></div></body>'),
    'utf8',
  );

  await assert.rejects(
    prerenderClaimSurfaces({ distDir, contentPath: CONTENT_PATH }),
    /empty application mount must occur exactly once/,
  );
});

test('pins the fail-closed full Render route replacement', async () => {
  const contract = JSON.parse(await readFile(RENDER_ROUTES_PATH, 'utf8'));
  assert.deepEqual(contract, {
    schemaVersion: 'atlas_render_static_routes.v1',
    dashboardManaged: true,
    requiredApiBaseUrl: 'https://noetic-compass-api.onrender.com/atlas',
    expectedCurrentRoutes: [
      {
        type: 'rewrite',
        source: '/*',
        destination: '/index.html',
      },
    ],
    applyOnlyAfterLiveResources: [
      '/spa.html',
      '/audit-console/index.html',
    ],
    replacementRoutes: [
      {
        type: 'rewrite',
        source: '/audit-console',
        destination: '/audit-console/index.html',
      },
      {
        type: 'rewrite',
        source: '/audit-console/',
        destination: '/audit-console/index.html',
      },
      {
        type: 'rewrite',
        source: '/*',
        destination: '/spa.html',
      },
    ],
    smokePathsAfterReplacement: ['/', '/audit-console', '/model-config'],
    rollbackRoutes: [
      {
        type: 'rewrite',
        source: '/*',
        destination: '/index.html',
      },
    ],
  });
});
