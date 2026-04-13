import { useMemo } from 'react';

interface NotationDiffProps {
  expected: string;
  expectedEnglish?: string | null;
  computed: string;
  computedEnglish?: string;
  computedValid?: boolean;
}

const OPERATOR_RE = /CO-\d/g;
const DOMAIN_RE = /\^[PCEO]/g;
const DRIVE_RE = /F[1-7]/g;
const RPM_RE = /RPM\([^)]+\)/g;

function extractTokens(notation: string): Set<string> {
  const tokens = new Set<string>();
  for (const m of notation.matchAll(OPERATOR_RE)) tokens.add(m[0]);
  for (const m of notation.matchAll(DOMAIN_RE)) tokens.add(m[0]);
  for (const m of notation.matchAll(DRIVE_RE)) tokens.add(m[0]);
  for (const m of notation.matchAll(RPM_RE)) tokens.add(m[0]);
  return tokens;
}

function classifyToken(_token: string, inExpected: boolean, inComputed: boolean): 'match' | 'added' | 'removed' {
  if (inExpected && inComputed) return 'match';
  if (!inExpected && inComputed) return 'added';
  return 'removed';
}

const TOKEN_COLORS = {
  match: 'bg-slate-500/10 text-slate-300',
  added: 'bg-emerald-500/15 text-emerald-400',
  removed: 'bg-red-500/15 text-red-400',
};

const TOKEN_LABELS = {
  match: 'confirmed',
  added: 'new finding',
  removed: 'not observed',
};

export function NotationDiff({ expected, expectedEnglish, computed, computedEnglish, computedValid }: NotationDiffProps) {
  const diff = useMemo(() => {
    const expectedTokens = extractTokens(expected);
    const computedTokens = extractTokens(computed);
    const allTokens = new Set([...expectedTokens, ...computedTokens]);

    const classified: { token: string; status: 'match' | 'added' | 'removed' }[] = [];
    for (const token of allTokens) {
      classified.push({
        token,
        status: classifyToken(token, expectedTokens.has(token), computedTokens.has(token)),
      });
    }

    // Sort: operators first, then domains, then drives
    classified.sort((a, b) => {
      const order = (t: string) => t.startsWith('CO') ? 0 : t.startsWith('^') ? 1 : t.startsWith('RPM') ? 2 : 3;
      return order(a.token) - order(b.token) || a.token.localeCompare(b.token);
    });

    const matchCount = classified.filter(c => c.status === 'match').length;
    const addedCount = classified.filter(c => c.status === 'added').length;
    const removedCount = classified.filter(c => c.status === 'removed').length;
    const diverged = addedCount > 0 || removedCount > 0;

    return { classified, matchCount, addedCount, removedCount, diverged };
  }, [expected, computed]);

  return (
    <div className="space-y-4">
      {/* Side-by-side notation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Expected */}
        <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Expected</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">pre-assessment</span>
          </div>
          <p className="font-mono text-[12px] text-blue-300 leading-relaxed break-all">{expected}</p>
          {expectedEnglish && (
            <p className="text-[10px] text-slate-500 mt-1.5">{expectedEnglish}</p>
          )}
        </div>

        {/* Computed */}
        <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Computed</span>
            {computedValid ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">compiler-validated</span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">unvalidated</span>
            )}
          </div>
          <p className="font-mono text-[12px] text-accent-teal leading-relaxed break-all">{computed || '(no significant patterns)'}</p>
          {computedEnglish && (
            <p className="text-[10px] text-slate-500 mt-1.5">{computedEnglish}</p>
          )}
        </div>
      </div>

      {/* Divergence summary */}
      {diff.diverged ? (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.04] p-3">
          <p className="text-[11px] font-semibold text-amber-400 mb-2">
            Divergence Detected
          </p>
          <p className="text-[10px] text-slate-400 mb-3">
            The AI's actual cognitive profile differs from what the scenario was designed to test.
            {diff.addedCount > 0 && ` ${diff.addedCount} new dimension${diff.addedCount > 1 ? 's' : ''} emerged.`}
            {diff.removedCount > 0 && ` ${diff.removedCount} expected dimension${diff.removedCount > 1 ? 's' : ''} not observed.`}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {diff.classified.map(({ token, status }) => (
              <span
                key={`${status}-${token}`}
                className={`text-[9px] font-mono px-2 py-0.5 rounded-full ${TOKEN_COLORS[status]}`}
                title={TOKEN_LABELS[status]}
              >
                {status === 'added' && '+ '}
                {status === 'removed' && '- '}
                {token}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] p-3">
          <p className="text-[11px] font-semibold text-emerald-400">
            No Divergence
          </p>
          <p className="text-[10px] text-slate-400 mt-1">
            The AI's computed profile matches the scenario's expected dimensions. All {diff.matchCount} targeted components were confirmed.
          </p>
        </div>
      )}
    </div>
  );
}
