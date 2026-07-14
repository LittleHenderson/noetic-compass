import { renderClaimSurfaceChildren } from '../../claimSurfaceMarkup.mjs';
import { claimSurface, type ClaimSurfaceKind } from '../../lib/claimSurfaceContract';

export function PrerenderedClaimSurface({
  surfaceKind,
}: {
  surfaceKind: ClaimSurfaceKind;
}) {
  const surface = claimSurface(surfaceKind);
  return (
    <div
      data-cas-hydration-container={surfaceKind}
      dangerouslySetInnerHTML={{
        __html: renderClaimSurfaceChildren(surfaceKind, surface),
      }}
    />
  );
}
