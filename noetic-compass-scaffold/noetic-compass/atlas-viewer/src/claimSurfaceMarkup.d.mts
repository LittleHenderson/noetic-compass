export interface ClaimSurfaceMarkupContent {
  eyebrow: string;
  heading: string;
  summary: string;
  statements: readonly string[];
  loadingLabel: string;
}

export function escapeClaimSurfaceHtml(value: unknown): string;
export function renderClaimSurfaceChildren(
  kind: string,
  surface: ClaimSurfaceMarkupContent,
): string;
