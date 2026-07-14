import claimSurfaceContent from '../claimSurfaces.json';

export type ClaimSurfaceKind = keyof typeof claimSurfaceContent.surfaces;
export const CLAIM_SURFACE_SCHEMA_VERSION = claimSurfaceContent.schemaVersion;

export function isClaimSurfaceKind(value: string): value is ClaimSurfaceKind {
  return Object.prototype.hasOwnProperty.call(claimSurfaceContent.surfaces, value);
}

export function claimSurfaceRoute(surfaceKind: ClaimSurfaceKind): string {
  return claimSurfaceContent.surfaces[surfaceKind].route;
}

export function claimSurface(surfaceKind: ClaimSurfaceKind) {
  return claimSurfaceContent.surfaces[surfaceKind];
}

export function prerenderedClaimSurfaceKind(
  rootElement: HTMLElement,
  pathname: string,
): ClaimSurfaceKind | null {
  const prerenderKind = rootElement.dataset.casPrerenderKind ?? '';
  const prerenderRoute = rootElement.dataset.casPrerenderedRoute ?? '';
  const prerenderSchema = rootElement.dataset.casPrerenderSchema ?? '';
  if (
    isClaimSurfaceKind(prerenderKind) &&
    prerenderSchema === CLAIM_SURFACE_SCHEMA_VERSION &&
    prerenderRoute === claimSurfaceRoute(prerenderKind) &&
    pathname === prerenderRoute
  ) {
    return prerenderKind;
  }
  return null;
}
