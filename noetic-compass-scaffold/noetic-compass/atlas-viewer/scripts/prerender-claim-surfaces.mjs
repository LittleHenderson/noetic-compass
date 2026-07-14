#!/usr/bin/env node

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  escapeClaimSurfaceHtml as escapeHtml,
  renderClaimSurfaceChildren,
} from '../src/claimSurfaceMarkup.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DEFAULT_DIST_DIR = resolve(HERE, '..', 'dist');
const DEFAULT_CONTENT_PATH = resolve(HERE, '..', 'src', 'claimSurfaces.json');
const ROOT_MOUNT = '<div id="root"></div>';
const EXPECTED_SURFACES = Object.freeze([
  Object.freeze({ kind: 'product_app', route: '/', output: 'index.html' }),
  Object.freeze({
    kind: 'audit_console',
    route: '/audit-console',
    output: 'audit-console/index.html',
  }),
]);
const SURFACE_FIELDS = Object.freeze([
  'route',
  'documentTitle',
  'description',
  'eyebrow',
  'heading',
  'summary',
  'statements',
  'loadingLabel',
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertExactKeys(value, expected, context) {
  assert(
    value !== null && typeof value === 'object' && !Array.isArray(value),
    context + ' must be an object',
  );
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  assert(
    JSON.stringify(actual) === JSON.stringify(wanted),
    context + ' keys must match the fixed contract',
  );
}

function loadAndValidateContent(raw) {
  const document = JSON.parse(raw);
  assertExactKeys(
    document,
    ['schemaVersion', 'surfaces'],
    'claim-surface document',
  );
  assert(
    document.schemaVersion === 'cas_claim_surface.v1',
    'claim-surface schema version must be cas_claim_surface.v1',
  );
  assertExactKeys(
    document.surfaces,
    EXPECTED_SURFACES.map(({ kind }) => kind),
    'claim-surface map',
  );

  for (const expected of EXPECTED_SURFACES) {
    const surface = document.surfaces[expected.kind];
    assertExactKeys(surface, SURFACE_FIELDS, 'surface ' + expected.kind);
    assert(
      surface.route === expected.route,
      'surface ' + expected.kind + ' must use its exact pinned route',
    );
    for (const field of SURFACE_FIELDS.filter((field) => field !== 'statements')) {
      assert(
        typeof surface[field] === 'string' && surface[field].trim().length > 0,
        expected.kind + '.' + field + ' must be a non-empty string',
      );
    }
    assert(
      Array.isArray(surface.statements) && surface.statements.length >= 4,
      expected.kind + '.statements must contain at least four boundaries',
    );
    assert(
      surface.statements.every(
        (statement) =>
          typeof statement === 'string' && statement.trim().length > 0,
      ),
      expected.kind + '.statements must contain only non-empty strings',
    );
    assert(
      surface.heading !== 'Log in to Noetic Compass',
      expected.kind + ' cannot use the generic login heading',
    );
  }
  return document;
}

function renderApplicationMount(kind, schemaVersion, surface) {
  return [
    '<div id="root" data-cas-prerendered-route="' +
      escapeHtml(surface.route) +
      '"',
    ' data-cas-prerender-schema="' + escapeHtml(schemaVersion) + '"',
    ' data-cas-prerender-kind="' + escapeHtml(kind) + '">',
    '<div data-cas-hydration-container="' + escapeHtml(kind) + '">',
    renderClaimSurfaceChildren(kind, surface),
    '</div>',
    '</div>',
  ].join('');
}

function replaceExactlyOnce(source, pattern, replacement, context) {
  const matches = source.match(pattern);
  assert(matches !== null && matches.length === 1, context + ' must occur exactly once');
  return source.replace(pattern, replacement);
}

function renderDocument(baseHtml, kind, schemaVersion, surface) {
  let rendered = replaceExactlyOnce(
    baseHtml,
    /<title>[\s\S]*?<\/title>/gi,
    '<title>' + escapeHtml(surface.documentTitle) + '</title>',
    'document title',
  );
  rendered = replaceExactlyOnce(
    rendered,
    /<meta\s+name=["']description["']\s+content=["'][^"']*["']\s*\/?\s*>/gi,
    '<meta name="description" content="' +
      escapeHtml(surface.description) +
      '" />',
    'description metadata',
  );
  const mountCount = rendered.split(ROOT_MOUNT).length - 1;
  assert(mountCount === 1, 'empty application mount must occur exactly once');
  return rendered.replace(
    ROOT_MOUNT,
    renderApplicationMount(kind, schemaVersion, surface),
  );
}

function validateRenderedDocument(html, expected, schemaVersion, surface) {
  assert(
    html.includes('data-cas-prerendered-route="' + expected.route + '"'),
    expected.kind + ' output must bind its exact route',
  );
  assert(
    html.includes('data-cas-prerender-schema="' + schemaVersion + '"'),
    expected.kind + ' output must bind its schema',
  );
  assert(
    html.includes('data-cas-prerender-kind="' + expected.kind + '"'),
    expected.kind + ' output must bind its kind',
  );
  assert(
    html.includes('<h1 id="cas-claim-heading-' + expected.kind + '"'),
    expected.kind + ' output must contain its route heading',
  );
  assert(
    html.includes('>' + escapeHtml(surface.heading) + '</h1>'),
    expected.kind + ' output must contain the exact heading text',
  );
  assert(
    !/<noscript\b/i.test(html),
    expected.kind + ' output cannot rely on noscript text',
  );
  assert(
    !/data-cas-static-claim-surface=["'][^"']+["'][^>]*\shidden(?:\s|=|>)/i.test(
      html,
    ),
    expected.kind + ' output cannot hide the claim surface',
  );
  assert(
    !/data-cas-static-claim-surface=["'][^"']+["'][^>]*aria-hidden=["']true["']/i.test(
      html,
    ),
    expected.kind + ' output cannot aria-hide the claim surface',
  );
  assert(
    !/data-cas-static-claim-surface=["'][^"']+["'][^>]*style=["'][^"']*(?:display\s*:\s*none|visibility\s*:\s*hidden)/i.test(
      html,
    ),
    expected.kind + ' output cannot style-hide the claim surface',
  );
}

export async function prerenderClaimSurfaces({
  distDir = DEFAULT_DIST_DIR,
  contentPath = DEFAULT_CONTENT_PATH,
} = {}) {
  const [baseHtml, contentRaw] = await Promise.all([
    readFile(resolve(distDir, 'index.html'), 'utf8'),
    readFile(contentPath, 'utf8'),
  ]);
  assert(
    baseHtml.includes(ROOT_MOUNT),
    'Vite output must contain the empty #root mount',
  );
  assert(
    !baseHtml.includes('data-cas-prerendered-route='),
    'Vite base output must not already be prerendered',
  );
  const content = loadAndValidateContent(contentRaw);

  // Render's catch-all rewrite must use this neutral shell. It prevents the
  // product-app summary from becoming static fallback content on other paths.
  await writeFile(resolve(distDir, 'spa.html'), baseHtml, 'utf8');

  const outputs = [];
  for (const expected of EXPECTED_SURFACES) {
    const surface = content.surfaces[expected.kind];
    const html = renderDocument(
      baseHtml,
      expected.kind,
      content.schemaVersion,
      surface,
    );
    validateRenderedDocument(html, expected, content.schemaVersion, surface);
    const outputPath = resolve(distDir, expected.output);
    await mkdir(dirname(outputPath), { recursive: true });
    await writeFile(outputPath, html, 'utf8');
    outputs.push({ ...expected, outputPath, html });
  }
  return { schemaVersion: content.schemaVersion, outputs };
}

function parseArgs(argv) {
  const parsed = {
    distDir: DEFAULT_DIST_DIR,
    contentPath: DEFAULT_CONTENT_PATH,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--dist') {
      parsed.distDir = resolve(argv[++index] ?? '');
    } else if (argument === '--content') {
      parsed.contentPath = resolve(argv[++index] ?? '');
    } else {
      throw new Error('unsupported argument: ' + argument);
    }
  }
  return parsed;
}

const isMain =
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href;
if (isMain) {
  try {
    const result = await prerenderClaimSurfaces(
      parseArgs(process.argv.slice(2)),
    );
    process.stdout.write(
      'Prerendered ' +
        result.outputs.length +
        ' exact claim surfaces (' +
        result.schemaVersion +
        ').\n',
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'unknown prerender failure';
    process.stderr.write('Claim-surface prerender failed: ' + message + '\n');
    process.exitCode = 1;
  }
}
