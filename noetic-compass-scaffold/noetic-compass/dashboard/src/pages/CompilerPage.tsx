import { useState, useRef, useEffect, useCallback } from 'react';
import { apiFetch } from '../api/client';

// ── Constants ──

// ASCII lines split so the dot formation can be inlined after the S
const ASCII_LINES = [
  ' ██████╗ █████╗ ███████╗',
  '██╔════╝██╔══██╗██╔════╝',
  '██║     ███████║███████╗',
  '██║     ██╔══██║╚════██║',
  '╚██████╗██║  ██║███████║',
  ' ╚═════╝╚═╝  ╚═╝╚══════╝',
  'Cognitive Architecture',
  'Compiler v1.0',
  'Patent Pending',
];

const HELP_TEXT = `Commands:
  :help      Show this message
  :grammar   Print the BNF grammar
  :examples  Show sample expressions
  :clear     Clear output
  :history   Show command history

Type any CAS expression to compile it.`;

const EXAMPLES = [
  { expr: 'CO-3^P_{F2} * CO-8^P_{F6}', label: 'Operator Composition' },
  { expr: 'CO-5^P -> CO-5^C', label: 'Domain Descent' },
  { expr: 'CO-2^P / CO-3^P', label: 'Involution Division' },
  { expr: 'CO-5^E + CO-2^E', label: 'Co-Presence' },
  { expr: 'CO-3^P - CO-8^P', label: 'Subtraction' },
  { expr: 'RPM(F5)', label: 'Prerequisite Chain' },
  { expr: 'Phi<3:8:5:2>', label: 'Fractal Analysis' },
  { expr: '(CO-3^P_{F2} * CO-8^P_{F6}) -> (CO-5^E_{F4} + CO-2^E_{F1})', label: 'Full Expression' },
];

const OPERATOR_NAMES = [
  'Generative Potential', 'Directed Attention', 'Attraction/Affinity', 'Aversion/Critical Eval',
  'Encoding Intensity', 'Receptive Integration', 'Projective Assertion', 'Pattern Entrainment',
  'Causal Initiation', 'Consequential Grounding',
];
const DOMAIN_NAMES: Record<string, string> = { P: 'Principled', C: 'Cognitive', E: 'Evaluative', O: 'Operational' };
const DRIVE_NAMES = ['Unity', 'Wisdom', 'Vitality', 'Connection', 'Agency', 'Structure', 'Purpose'];

// ── Types ──

interface CompileResult {
  source: string;
  valid: boolean;
  error?: string | null;
  engine?: string;
  warnings?: string[];
  tokens?: { kind: string; value: string; position: number }[];
  ast?: Record<string, unknown> | null;
  type?: { kind: string; domains: string[]; singular: boolean } | null;
  bytecode?: unknown[];
  result?: Record<string, unknown> | null;
}

interface HistoryEntry {
  input: string;
  result: CompileResult | null;
  isCommand: boolean;
  commandOutput?: string;
  timestamp: number;
}

// ── Syntax highlighting ──

function highlightSyntax(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let i = 0;
  const s = text;

  while (i < s.length) {
    // CO-N operator
    const coMatch = s.slice(i).match(/^CO-\d+/);
    if (coMatch) {
      parts.push(<span key={i} className="text-cyan-400">{coMatch[0]}</span>);
      i += coMatch[0].length;
      continue;
    }
    // ^Domain
    if (s[i] === '^' && 'PCEO'.includes(s[i + 1] ?? '')) {
      parts.push(<span key={i} className="text-emerald-400">^{s[i + 1]}</span>);
      i += 2;
      continue;
    }
    // _{Fn} drive subscript
    const driveMatch = s.slice(i).match(/^_\{F\d+\}/);
    if (driveMatch) {
      parts.push(<span key={i} className="text-amber-400">{driveMatch[0]}</span>);
      i += driveMatch[0].length;
      continue;
    }
    // Fn drive ref
    const fnMatch = s.slice(i).match(/^F[1-7]\b/);
    if (fnMatch && (i === 0 || !/[{a-zA-Z]/.test(s[i - 1] ?? ''))) {
      parts.push(<span key={i} className="text-amber-400">{fnMatch[0]}</span>);
      i += fnMatch[0].length;
      continue;
    }
    // RPM
    if (s.slice(i, i + 3) === 'RPM') {
      parts.push(<span key={i} className="text-purple-400">RPM</span>);
      i += 3;
      continue;
    }
    // Phi / Φ
    if (s.slice(i, i + 3) === 'Phi' || s[i] === 'Φ') {
      const len = s[i] === 'Φ' ? 1 : 3;
      parts.push(<span key={i} className="text-pink-400">{s.slice(i, i + len)}</span>);
      i += len;
      continue;
    }
    // Operations
    if ('*×/÷∘'.includes(s[i])) {
      parts.push(<span key={i} className="text-white font-bold">{s[i]}</span>);
      i += 1;
      continue;
    }
    if (s.slice(i, i + 2) === '->') {
      parts.push(<span key={i} className="text-white font-bold">→</span>);
      i += 2;
      continue;
    }
    if (s[i] === '→' || s[i] === '←' || s[i] === '↔') {
      parts.push(<span key={i} className="text-white font-bold">{s[i]}</span>);
      i += 1;
      continue;
    }
    if (s[i] === '+' || s[i] === '-') {
      parts.push(<span key={i} className="text-slate-300 font-bold">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Parens / angle brackets
    if ('(){}⟨⟩<>'.includes(s[i])) {
      parts.push(<span key={i} className="text-slate-500">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Default
    parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
    i += 1;
  }
  return parts;
}

// ── Result rendering ──

function describeResult(r: CompileResult): string {
  if (!r.result) return '';
  const res = r.result as Record<string, unknown>;
  const kind = res.kind as string | undefined;

  if (kind === 'state') {
    const dom = (res.dominant_domain as string) || '?';
    const op = (res.dominant_operator as string) || '?';
    const opIdx = parseInt(op.replace('CO-', ''));
    const opName = OPERATOR_NAMES[opIdx] ?? op;
    const domName = DOMAIN_NAMES[dom] ?? dom;
    return `${opName} in the ${domName} Domain`;
  }
  if (kind === 'fractal') {
    const seq = (res.sequence as number[]) || [];
    const composed = res.composed_operator as string || '?';
    return `Fractal sequence [${seq.join(':')}] → composed ${composed}`;
  }
  if (kind === 'rpm') {
    const drive = res.drive as string || '?';
    const completeness = res.completeness as number ?? 0;
    return `${drive} prerequisite chain (completeness: ${(completeness * 100).toFixed(0)}%)`;
  }
  if (kind === 'program') {
    const final = res.final_result as Record<string, unknown> | null;
    if (final?.kind === 'state') {
      const dom = (final.dominant_domain as string) || '?';
      const op = (final.dominant_operator as string) || '?';
      const opIdx = parseInt(op.replace('CO-', ''));
      return `Program → ${OPERATOR_NAMES[opIdx] ?? op} in ${DOMAIN_NAMES[dom] ?? dom} Domain`;
    }
    return 'Multi-statement program';
  }
  return JSON.stringify(res).slice(0, 120);
}

function ResultCard({ entry }: { entry: HistoryEntry }) {
  if (entry.isCommand) {
    return (
      <div className="animate-[fadeSlideIn_0.2s_ease-out]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-accent-teal font-mono text-sm">cas&gt;</span>
          <span className="text-slate-300 font-mono text-sm">{entry.input}</span>
        </div>
        <pre className="text-slate-400 text-xs font-mono whitespace-pre-wrap pl-6">{entry.commandOutput}</pre>
      </div>
    );
  }

  const r = entry.result;
  if (!r) return null;

  return (
    <div className={`animate-[fadeSlideIn_0.3s_ease-out] rounded-lg border p-4 font-mono text-xs ${
      r.valid
        ? 'border-emerald-500/20 bg-emerald-500/[0.03]'
        : 'border-red-500/20 bg-red-500/[0.03]'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-accent-teal">cas&gt;</span>
        <span className="text-sm">{highlightSyntax(r.source)}</span>
      </div>
      <div className="flex items-center gap-2 mt-2 text-[10px]">
        {r.valid ? (
          <span className="text-emerald-400">✅ Valid</span>
        ) : (
          <span className="text-red-400">❌ Invalid</span>
        )}
        {r.engine && <span className="text-slate-600">engine: {r.engine}</span>}
        {r.tokens && <span className="text-slate-600">tokens: {r.tokens.length}</span>}
        {r.bytecode && r.bytecode.length > 0 && <span className="text-slate-600">bytecode: {r.bytecode.length}</span>}
      </div>

      {/* Error */}
      {r.error && (
        <div className="mt-3 rounded border border-red-500/20 bg-red-500/[0.05] p-3">
          <p className="text-red-400 text-[11px]">{r.error}</p>
          {r.tokens && r.tokens.length > 0 && (
            <div className="mt-2 text-slate-500 text-[10px]">
              <p className="text-slate-400 mb-1">Tokens parsed before failure:</p>
              <div className="flex flex-wrap gap-1">
                {r.tokens.map((t, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-400">
                    {t.kind}={t.value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* AST */}
      {r.ast && (
        <div className="mt-3 rounded border border-white/[0.06] bg-white/[0.02] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">AST</p>
          <pre className="text-[10px] text-slate-400 whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(r.ast, null, 2).slice(0, 500)}
          </pre>
        </div>
      )}

      {/* Type */}
      {r.type && (
        <div className="mt-2 flex items-center gap-2 text-[10px]">
          <span className="text-slate-500">Type:</span>
          <span className="text-blue-400">{r.type.kind}</span>
          {r.type.domains.length > 0 && (
            <span className="text-emerald-400">[{r.type.domains.join(', ')}]</span>
          )}
          {r.type.singular && <span className="text-amber-400">singular</span>}
        </div>
      )}

      {/* Result */}
      {r.result && (
        <div className="mt-3 rounded border border-accent-teal/20 bg-accent-teal/[0.03] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Result</p>
          <p className="text-accent-teal text-[12px]">{describeResult(r)}</p>
        </div>
      )}

      {r.warnings && r.warnings.length > 0 && (
        <div className="mt-2">
          {r.warnings.map((w, i) => (
            <p key={i} className="text-[10px] text-amber-400">⚠ {w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Page ──

export function CompilerPage() {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [showRef, setShowRef] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight, behavior: 'smooth' });
  }, [history]);

  const addEntry = useCallback((entry: HistoryEntry) => {
    setHistory((prev) => [...prev, entry]);
  }, []);

  async function handleSubmit() {
    const trimmed = input.trim();
    if (!trimmed) return;

    setCmdHistory((prev) => [trimmed, ...prev].slice(0, 50));
    setHistoryIdx(-1);
    setInput('');

    const ts = Date.now();

    // Special commands
    if (trimmed === ':help') {
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: HELP_TEXT, timestamp: ts });
      return;
    }
    if (trimmed === ':clear') {
      setHistory([]);
      return;
    }
    if (trimmed === ':examples') {
      const text = EXAMPLES.map((e) => `  ${e.expr}\n    → ${e.label}`).join('\n');
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: text, timestamp: ts });
      return;
    }
    if (trimmed === ':history') {
      const text = cmdHistory.slice(0, 20).map((c, i) => `  ${i + 1}. ${c}`).join('\n');
      addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: text || '  (empty)', timestamp: ts });
      return;
    }
    if (trimmed === ':grammar') {
      try {
        const data = await apiFetch<{ grammar: string }>('/notation/grammar');
        addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: data.grammar, timestamp: ts });
      } catch {
        addEntry({ input: trimmed, result: null, isCommand: true, commandOutput: 'Failed to fetch grammar', timestamp: ts });
      }
      return;
    }

    // Compile expression
    setLoading(true);
    try {
      const result = await apiFetch<CompileResult>('/notation/compile', {
        method: 'POST',
        body: JSON.stringify({ expression: trimmed }),
      });
      addEntry({ input: trimmed, result, isCommand: false, timestamp: ts });
    } catch (err) {
      // If compile returns 422, the error detail has the compilation error
      const detail = err instanceof Error ? err.message : String(err);
      // Try to get the full artifact even on error
      try {
        const raw = await fetch(`${import.meta.env.PROD ? '/api' : (import.meta.env.VITE_API_URL ?? '/api')}/notation/compile`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ expression: trimmed }),
        });
        if (raw.status === 422) {
          const body = await raw.json();
          addEntry({
            input: trimmed,
            result: { source: trimmed, valid: false, error: body.detail ?? detail, engine: 'rust+python' },
            isCommand: false,
            timestamp: ts,
          });
        } else {
          addEntry({
            input: trimmed,
            result: { source: trimmed, valid: false, error: detail },
            isCommand: false,
            timestamp: ts,
          });
        }
      } catch {
        addEntry({
          input: trimmed,
          result: { source: trimmed, valid: false, error: detail },
          isCommand: false,
          timestamp: ts,
        });
      }
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const next = Math.min(historyIdx + 1, cmdHistory.length - 1);
      setHistoryIdx(next);
      if (cmdHistory[next]) setInput(cmdHistory[next]);
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = historyIdx - 1;
      if (next < 0) {
        setHistoryIdx(-1);
        setInput('');
      } else {
        setHistoryIdx(next);
        if (cmdHistory[next]) setInput(cmdHistory[next]);
      }
    }
  }

  return (
    <div className="flex h-full max-h-[calc(100vh-5rem)]">
      {/* Main terminal */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Output area */}
        <div
          ref={outputRef}
          className="flex-1 overflow-y-auto p-4 space-y-4 font-mono"
          style={{ backgroundColor: '#0d1117' }}
          onClick={() => inputRef.current?.focus()}
        >
          {/* Logo: ASCII CAS with 10-dot formation fused to the end of the S */}
          {history.length === 0 && (
            <div className="space-y-3">
              <div className="select-none flex items-start gap-4">
                <pre className="text-accent-teal text-[10px] leading-tight whitespace-pre m-0 shrink-0">{ASCII_LINES.join('\n')}</pre>
                {/* TKS 10-dot formation — exact original proportions from SVG viewBox 0 0 800 1100, 3x dot size */}
                <svg viewBox="0 0 800 1100" className="shrink-0" style={{ height: '140px', width: '100px' }}>
                  <circle cx="400" cy="55"   r="90" fill="#FFC107" stroke="#FFA000" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 0s infinite alternate' }} />
                  <circle cx="110" cy="190"  r="90" fill="#E53935" stroke="#C62828" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.25s infinite alternate' }} />
                  <circle cx="690" cy="190"  r="90" fill="#7B1FA2" stroke="#6A1B9A" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.5s infinite alternate' }} />
                  <circle cx="400" cy="400"  r="90" fill="#FFC107" stroke="#FFA000" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.75s infinite alternate' }} />
                  <circle cx="110" cy="545"  r="90" fill="#E53935" stroke="#C62828" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.0s infinite alternate' }} />
                  <circle cx="690" cy="545"  r="90" fill="#7B1FA2" stroke="#6A1B9A" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.25s infinite alternate' }} />
                  <circle cx="400" cy="690"  r="90" fill="#FFC107" stroke="#FFA000" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.5s infinite alternate' }} />
                  <circle cx="110" cy="870"  r="90" fill="#E53935" stroke="#C62828" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.75s infinite alternate' }} />
                  <circle cx="690" cy="870"  r="90" fill="#7B1FA2" stroke="#6A1B9A" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 2.0s infinite alternate' }} />
                  <circle cx="400" cy="1020" r="90" fill="#FFC107" stroke="#FFA000" strokeWidth="10" style={{ animation: 'tks-breathe 2.5s ease-in-out 2.25s infinite alternate' }} />
                </svg>
              </div>
              <p className="text-slate-500 text-xs">
                Type <span className="text-slate-300">:help</span> for commands,{' '}
                <span className="text-slate-300">:grammar</span> for the BNF,{' '}
                <span className="text-slate-300">:examples</span> for sample expressions
              </p>
            </div>
          )}

          {/* History */}
          {history.map((entry, i) => (
            <ResultCard key={i} entry={entry} />
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-slate-500 text-xs font-mono animate-pulse">
              <span className="text-accent-teal">cas&gt;</span>
              <span>Compiling...</span>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-white/[0.06] p-3 flex items-center gap-2" style={{ backgroundColor: '#0d1117' }}>
          <span className="text-accent-teal font-mono text-sm font-bold shrink-0">cas&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="CO-3^P_{F2} * CO-8^P_{F6}"
            className="flex-1 bg-transparent border-none outline-none text-sm font-mono text-slate-200 placeholder-slate-700 caret-accent-teal min-h-[44px]"
            autoComplete="off"
            spellCheck={false}
          />
          <button
            onClick={() => setShowRef(!showRef)}
            className="shrink-0 px-2 py-1 rounded text-[10px] font-mono text-slate-500 hover:text-slate-300 border border-white/[0.06] hover:border-white/[0.12] transition-colors min-h-[36px]"
          >
            {showRef ? 'Hide Ref' : 'Ref'}
          </button>
        </div>
      </div>

      {/* Side panel */}
      {showRef && (
        <div className="w-72 border-l border-white/[0.06] overflow-y-auto p-4 space-y-5 shrink-0 hidden sm:block" style={{ backgroundColor: '#0d1117' }}>
          {/* Examples */}
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Examples</p>
            <div className="space-y-1">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex.expr}
                  onClick={() => { setInput(ex.expr); inputRef.current?.focus(); }}
                  className="w-full text-left rounded px-2 py-1.5 text-[10px] font-mono text-slate-400 hover:text-accent-teal hover:bg-white/[0.04] transition-colors"
                >
                  <span className="text-slate-500 block text-[9px]">{ex.label}</span>
                  {ex.expr}
                </button>
              ))}
            </div>
          </div>

          {/* Operators */}
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Operators</p>
            <div className="space-y-0.5">
              {OPERATOR_NAMES.map((name, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span className="text-cyan-400 font-mono w-8">CO-{i}</span>
                  <span className="text-slate-500">{name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Domains */}
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Domains</p>
            {Object.entries(DOMAIN_NAMES).map(([code, name]) => (
              <div key={code} className="flex items-center gap-2 text-[10px]">
                <span className="text-emerald-400 font-mono w-4">{code}</span>
                <span className="text-slate-500">{name}</span>
              </div>
            ))}
          </div>

          {/* Drives */}
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Drives</p>
            {DRIVE_NAMES.map((name, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="text-amber-400 font-mono w-6">F{i + 1}</span>
                <span className="text-slate-500">{name}</span>
              </div>
            ))}
          </div>

          {/* Operations */}
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Operations</p>
            <div className="space-y-0.5 text-[10px]">
              <div><span className="text-orange-400 font-mono">×</span> <span className="text-slate-500">Composition (algebraic)</span></div>
              <div><span className="text-orange-400 font-mono">÷</span> <span className="text-slate-500">Division (algebraic)</span></div>
              <div><span className="text-orange-400 font-mono">∘</span> <span className="text-slate-500">Fractal (algebraic)</span></div>
              <div><span className="text-slate-300 font-mono">+</span> <span className="text-slate-500">Co-presence (syntactic)</span></div>
              <div><span className="text-slate-300 font-mono">-</span> <span className="text-slate-500">Removal (syntactic)</span></div>
              <div><span className="text-white font-mono">→</span> <span className="text-slate-500">Dependency (relation)</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
