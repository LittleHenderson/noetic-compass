import { ApiError } from '../../api/client';

const STATUS_LABELS: Record<number, string> = {
  0: 'Network error',
  401: 'Unauthorized - check your JWT token',
  403: 'Forbidden',
  404: 'Not found',
  429: 'Rate limited - try again later',
  500: 'Server error',
  502: 'LLM provider error',
};

/**
 * CAS-specific error patterns that should be rendered with
 * domain terminology instead of generic HTTP error language.
 */
const CAS_VIOLATION_PATTERNS: { pattern: RegExp; label: string; icon: string }[] = [
  {
    pattern: /domain.?ascent|ascending.*domain/i,
    label: 'Domain Descent Violation',
    icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  },
  {
    pattern: /cross.?domain.*division/i,
    label: 'Cross-Domain Division Error',
    icon: 'M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636',
  },
  {
    pattern: /admissib/i,
    label: 'Admissibility Violation',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  },
  {
    pattern: /degenerate.*state/i,
    label: 'Degenerate State',
    icon: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    pattern: /boundary.*violation|non.?positive/i,
    label: 'Simplex Boundary Violation',
    icon: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    pattern: /involution.*diverge|dial.*out.*range|involution.*pair/i,
    label: 'Dial Safety Constraint',
    icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  },
];

function detectCasViolation(detail: string): { label: string; icon: string } | null {
  for (const v of CAS_VIOLATION_PATTERNS) {
    if (v.pattern.test(detail)) {
      return { label: v.label, icon: v.icon };
    }
  }
  return null;
}

export function ErrorBanner({ error }: { error: Error | null }) {
  if (!error) return null;

  const detail = error instanceof ApiError ? error.detail : error.message;
  const status = error instanceof ApiError ? error.status : 0;
  const violation = detectCasViolation(detail);

  if (violation) {
    return (
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-4">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d={violation.icon} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-amber-300">{violation.label}</p>
            <p className="text-[12px] text-slate-400 leading-relaxed">{detail}</p>
          </div>
        </div>
      </div>
    );
  }

  const label = STATUS_LABELS[status];
  const message = label ? `${label}: ${detail}` : status ? `Error ${status}: ${detail}` : detail;

  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
      {message}
    </div>
  );
}
