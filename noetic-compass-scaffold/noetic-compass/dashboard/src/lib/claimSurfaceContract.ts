import claimSurfaceContent from '../claimSurfaces.json';

export type ClaimSurfaceKind = keyof typeof claimSurfaceContent.surfaces;
export const CLAIM_SURFACE_SCHEMA_VERSION = claimSurfaceContent.schemaVersion;

export function isClaimSurfaceKind(value: string): value is ClaimSurfaceKind {
  return Object.hasOwn(claimSurfaceContent.surfaces, value);
}

export function claimSurfaceRoute(surfaceKind: ClaimSurfaceKind): string {
  return claimSurfaceContent.surfaces[surfaceKind].route;
}

export function claimSurface(surfaceKind: ClaimSurfaceKind) {
  return claimSurfaceContent.surfaces[surfaceKind];
}
