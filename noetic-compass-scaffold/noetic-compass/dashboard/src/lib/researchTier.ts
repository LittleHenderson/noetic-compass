export function researchTierLabel(certification: string): string {
  return certification === 'Fail' ? 'Below Prototype Threshold' : `${certification} Research Tier`;
}

export function researchTierInline(certification: string): string {
  return certification === 'Fail' ? 'below the current prototype threshold' : `${certification.toLowerCase()} research tier`;
}
