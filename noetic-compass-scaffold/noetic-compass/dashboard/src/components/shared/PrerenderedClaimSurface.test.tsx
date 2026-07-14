import { act } from 'react';
import { hydrateRoot } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';

import claimSurfaceContent from '../../claimSurfaces.json';
import {
  escapeClaimSurfaceHtml,
  renderClaimSurfaceChildren,
} from '../../claimSurfaceMarkup.mjs';
import {
  PrerenderedClaimSurface,
} from './PrerenderedClaimSurface';
import {
  claimSurfaceRoute,
  isClaimSurfaceKind,
} from '../../lib/claimSurfaceContract';


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
        `<div data-cas-hydration-container="${surfaceKind}">`,
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
      expect(mount.querySelector('[data-cas-static-claim-surface]')).toBeVisible();
      expect(mount.querySelector('noscript')).toBeNull();

      await act(async () => root.unmount());
    },
  );

  it('keeps the surface registry exact and route-specific', () => {
    expect(isClaimSurfaceKind('product_app')).toBe(true);
    expect(isClaimSurfaceKind('audit_console')).toBe(true);
    expect(isClaimSurfaceKind('generic')).toBe(false);
    expect(claimSurfaceRoute('product_app')).toBe('/');
    expect(claimSurfaceRoute('audit_console')).toBe('/audit-console');
  });

  it('escapes checked-in content before inserting static HTML', () => {
    expect(escapeClaimSurfaceHtml('<script>alert("x")</script>')).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;',
    );
  });
});
