import { act } from 'react';
import { hydrateRoot } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';

import claimSurfaceContent from '../../claimSurfaces.json';
import {
  escapeClaimSurfaceHtml,
  renderClaimSurfaceChildren,
} from '../../claimSurfaceMarkup.mjs';
import {
  claimSurfaceRoute,
  isClaimSurfaceKind,
  prerenderedClaimSurfaceKind,
} from '../../lib/claimSurfaceContract';
import { PrerenderedClaimSurface } from './PrerenderedClaimSurface';

afterEach(() => {
  document.body.replaceChildren();
});

describe('PrerenderedClaimSurface', () => {
  it.each(['product_app', 'audit_console'] as const)(
    'hydrates the exact static %s markup without recovery',
    async (surfaceKind) => {
      const surface = claimSurfaceContent.surfaces[surfaceKind];
      const mount = document.createElement('div');
      mount.innerHTML = [
        '<div data-cas-hydration-container="' + surfaceKind + '">',
        renderClaimSurfaceChildren(surfaceKind, surface),
        '</div>',
      ].join('');
      document.body.append(mount);
      const recoverableErrors: unknown[] = [];

      const root = hydrateRoot(
        mount,
        <PrerenderedClaimSurface surfaceKind={surfaceKind} />,
        {
          onRecoverableError(error) {
            recoverableErrors.push(error);
          },
        },
      );
      await act(async () => undefined);

      expect(recoverableErrors).toEqual([]);
      expect(mount.querySelector('h1')).toHaveTextContent(surface.heading);
      expect(
        mount.querySelector('[data-cas-static-claim-surface]'),
      ).toBeVisible();
      expect(mount.querySelector('noscript')).toBeNull();

      await act(async () => root.unmount());
    },
  );

  it('keeps the registry exact and route-specific', () => {
    expect(isClaimSurfaceKind('product_app')).toBe(true);
    expect(isClaimSurfaceKind('audit_console')).toBe(true);
    expect(isClaimSurfaceKind('generic')).toBe(false);
    expect(claimSurfaceRoute('product_app')).toBe('/');
    expect(claimSurfaceRoute('audit_console')).toBe('/audit-console');
  });

  it('accepts only a schema, kind, route, and browser path that all agree', () => {
    const root = document.createElement('div');
    root.dataset.casPrerenderKind = 'audit_console';
    root.dataset.casPrerenderSchema = 'cas_claim_surface.v1';
    root.dataset.casPrerenderedRoute = '/audit-console';

    expect(prerenderedClaimSurfaceKind(root, '/audit-console')).toBe(
      'audit_console',
    );
    expect(prerenderedClaimSurfaceKind(root, '/unrelated')).toBeNull();
    root.dataset.casPrerenderSchema = 'untrusted.v1';
    expect(prerenderedClaimSurfaceKind(root, '/audit-console')).toBeNull();
  });

  it('escapes checked-in content before inserting static HTML', () => {
    expect(escapeClaimSurfaceHtml('<script>alert("x")</script>')).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;',
    );
  });
});
