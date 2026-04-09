import { useState, useMemo } from 'react';

const OPERATOR_NAMES = [
  'Identity', 'Reflection', 'Abstraction', 'Concretization',
  'Integration', 'Differentiation', 'Unification', 'Transformation',
  'Expansion', 'Contraction',
];
const DOMAIN_NAMES: Record<string, string> = { P: 'Principled', C: 'Cognitive', E: 'Evaluative', O: 'Operational' };
const DRIVE_NAMES = ['Unity', 'Wisdom', 'Vitality', 'Connection', 'Agency', 'Structure', 'Purpose'];

interface ParseResult {
  operators: number[];
  domains: string[];
  drives: number[];
  fractal: number[] | null;
  isRpm: boolean;
  valid: boolean;
  error: string;
  english: string;
}

function parseNotation(input: string): ParseResult {
  const result: ParseResult = {
    operators: [], domains: [], drives: [], fractal: null,
    isRpm: false, valid: true, error: '', english: '',
  };

  if (!input.trim()) {
    result.valid = false;
    result.english = 'Type CAS notation above...';
    return result;
  }

  const text = input.trim();

  // CO-N patterns
  for (const m of text.matchAll(/CO-(\d)/g)) {
    const idx = parseInt(m[1]);
    if (idx <= 9) result.operators.push(idx);
    else { result.valid = false; result.error = `Invalid operator CO-${idx}`; }
  }

  // Domain superscripts ^P ^C ^E ^O
  for (const m of text.matchAll(/\^([PCEO])/g)) {
    result.domains.push(m[1]);
  }

  // Cognitive states P3, C7, E0, O5
  for (const m of text.matchAll(/([PCEO])(\d)/g)) {
    // Only match if not preceded by CO-
    const domain = m[1];
    const opIdx = parseInt(m[2]);
    if (opIdx <= 9 && !result.operators.includes(opIdx)) {
      result.operators.push(opIdx);
    }
    if (!result.domains.includes(domain)) {
      result.domains.push(domain);
    }
  }

  // Drive F1-F7
  for (const m of text.matchAll(/F(\d)/g)) {
    const idx = parseInt(m[1]);
    if (idx >= 1 && idx <= 7) result.drives.push(idx - 1);
    else { result.valid = false; result.error = `Invalid drive F${idx}`; }
  }

  // RPM
  if (/RPM/i.test(text)) result.isRpm = true;

  // Fractal Phi<...> or Φ⟨...⟩
  const fracMatch = text.match(/(?:Phi|Φ)[⟨<]([\d:]+)[⟩>]/);
  if (fracMatch) {
    const indices = fracMatch[1].split(':').map(Number);
    if (indices.every(i => i >= 0 && i <= 9)) {
      result.fractal = indices;
    } else {
      result.valid = false;
      result.error = 'Fractal indices must be 0-9';
    }
  }

  // Check for unknown content
  if (result.operators.length === 0 && result.drives.length === 0 && !result.fractal && !result.isRpm) {
    result.valid = false;
    result.error = 'No recognized CAS notation found';
  }

  // Build English
  const parts: string[] = [];
  if (result.operators.length > 0) {
    const opNames = result.operators.map(i => `CO-${i} (${OPERATOR_NAMES[i] ?? '?'})`);
    parts.push(opNames.join(' and '));
  }
  if (result.domains.length > 0) {
    parts.push('in the ' + result.domains.map(d => `${DOMAIN_NAMES[d] ?? d} Domain`).join(' and '));
  }
  if (result.drives.length > 0) {
    parts.push('grounded in ' + result.drives.map(i => `F${i + 1} (${DRIVE_NAMES[i] ?? '?'})`).join(' and '));
  }
  if (result.isRpm) parts.push('(RPM prerequisite chain)');
  if (result.fractal) parts.push(`Cognitive Fractal [${result.fractal.join(':')}]`);

  result.english = parts.join(' ') || 'Empty notation';

  return result;
}

function generatePrompt(parsed: ParseResult): string {
  const parts: string[] = [];

  if (parsed.operators.length > 0) {
    const names = parsed.operators.map(i => OPERATOR_NAMES[i]).filter(Boolean);
    parts.push(`Write a response that demonstrates ${names.join(' and ').toLowerCase()}.`);
  }

  if (parsed.domains.length > 0) {
    const dNames = parsed.domains.map(d => DOMAIN_NAMES[d]).filter(Boolean);
    parts.push(`Frame your reasoning in the ${dNames.join(' and ').toLowerCase()} domain.`);
  }

  if (parsed.isRpm) {
    parts.push('Ensure your response follows a clear prerequisite chain: establish motivation before knowledge, and knowledge before action.');
  }

  if (parsed.fractal) {
    parts.push(`Apply cognitive operators in sequence: ${parsed.fractal.map(i => `CO-${i}`).join(' → ')}.`);
  }

  if (parts.length === 0) {
    return 'Explain your reasoning about a complex decision.';
  }

  return parts.join(' ');
}

interface NotationComposerProps {
  onGenerate: (prompt: string) => void;
}

export function NotationComposer({ onGenerate }: NotationComposerProps) {
  const [notation, setNotation] = useState('');
  const parsed = useMemo(() => parseNotation(notation), [notation]);

  const handleGenerate = () => {
    const prompt = generatePrompt(parsed);
    onGenerate(prompt);
  };

  return (
    <div className="space-y-3">
      {/* Notation input */}
      <div>
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
          CAS Notation
        </label>
        <input
          type="text"
          value={notation}
          onChange={(e) => setNotation(e.target.value)}
          placeholder="CO-3^E + CO-5^C   or   RPM(F5)   or   Phi<1:4:7>"
          className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-base sm:text-sm font-mono text-accent-teal placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none focus:ring-1 focus:ring-accent-teal/30"
        />
      </div>

      {/* Parse result */}
      {notation.trim() && (
        <div className={`rounded-lg border p-3 ${parsed.valid ? 'border-accent-teal/20 bg-accent-teal/[0.03]' : 'border-red-500/20 bg-red-500/[0.03]'}`}>
          {parsed.valid ? (
            <>
              <p className="text-[11px] text-slate-300 leading-relaxed">{parsed.english}</p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {parsed.operators.map(op => (
                  <span key={`op-${op}`} className="text-[9px] px-2 py-0.5 rounded-full bg-accent-teal/10 text-accent-teal font-mono">
                    CO-{op}
                  </span>
                ))}
                {parsed.domains.map(d => (
                  <span key={`d-${d}`} className="text-[9px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                    {DOMAIN_NAMES[d]}
                  </span>
                ))}
                {parsed.drives.map(i => (
                  <span key={`f-${i}`} className="text-[9px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400">
                    F{i + 1}
                  </span>
                ))}
                {parsed.isRpm && (
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400">RPM</span>
                )}
                {parsed.fractal && (
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-pink-500/10 text-pink-400 font-mono">
                    Φ⟨{parsed.fractal.join(':')}⟩
                  </span>
                )}
              </div>
            </>
          ) : (
            <p className="text-[11px] text-red-400">{parsed.error || parsed.english}</p>
          )}
        </div>
      )}

      {/* Quick reference */}
      <div className="text-[9px] text-slate-600 leading-relaxed">
        <span className="font-mono text-slate-500">CO-3^E</span> operator+domain
        {' · '}
        <span className="font-mono text-slate-500">CO-2 + CO-3</span> combination
        {' · '}
        <span className="font-mono text-slate-500">RPM(F5)</span> prerequisite chain
        {' · '}
        <span className="font-mono text-slate-500">Phi&lt;1:4:7&gt;</span> fractal
        {' · '}
        <span className="font-mono text-slate-500">P3</span> state
      </div>

      {/* Generate button */}
      {parsed.valid && notation.trim() && (
        <button
          onClick={handleGenerate}
          className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 sm:py-2 text-sm font-semibold text-dark-900 hover:opacity-90 transition-opacity min-h-[44px]"
        >
          Generate Targeted Scenario
        </button>
      )}
    </div>
  );
}
