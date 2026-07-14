export function escapeClaimSurfaceHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}


export function renderClaimSurfaceChildren(kind, surface) {
  const headingId = `cas-claim-heading-${kind}`;
  const statements = surface.statements
    .map((statement) => `<li>${escapeClaimSurfaceHtml(statement)}</li>`)
    .join('');
  return [
    `<main class="cas-claim-surface" data-cas-static-claim-surface="${escapeClaimSurfaceHtml(kind)}">`,
    `<section class="cas-claim-card" aria-labelledby="${headingId}">`,
    `<p class="cas-claim-eyebrow">${escapeClaimSurfaceHtml(surface.eyebrow)}</p>`,
    `<h1 id="${headingId}" class="cas-claim-heading">${escapeClaimSurfaceHtml(surface.heading)}</h1>`,
    `<p class="cas-claim-summary">${escapeClaimSurfaceHtml(surface.summary)}</p>`,
    `<ul class="cas-claim-statements">${statements}</ul>`,
    `<p class="cas-claim-loading" aria-live="polite">${escapeClaimSurfaceHtml(surface.loadingLabel)}</p>`,
    '</section>',
    '</main>',
  ].join('');
}
