const PROVIDER_LABELS: Record<string, string> = {
  mock: 'Mock Ai',
};

export function formatProviderLabel(provider: string | null | undefined): string {
  if (!provider) return 'Unknown provider';
  return PROVIDER_LABELS[provider] ?? provider;
}
