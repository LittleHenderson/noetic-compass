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

Editing:
  Enter        Submit the expression
  Shift+Enter  Insert a newline (write multi-statement programs)
  ↑ / ↓        Recall command history (only when textbox is empty)

Type any CAS expression to compile it.`;

interface Example {
  expr: string;
  label: string;
  category: string;
}

const EXAMPLES: Example[] = [
  // CAS v7.4 — Foundational notation
  { expr: '^2^P_{F2} × ^8^P_{F6}', label: 'Operator Composition (×)', category: 'Foundational' },
  { expr: '^5^P -> ^5^C', label: 'Domain Descent (P → C)', category: 'Foundational' },
  { expr: '^2^P / ^3^P', label: 'Involution Division', category: 'Foundational' },
  { expr: '^5^E + ^2^E', label: 'Co-Presence (+)', category: 'Foundational' },
  { expr: 'RPM(F5)', label: 'Prerequisite Chain', category: 'Foundational' },
  { expr: 'Phi<3:8:5:2>', label: 'Fractal Analysis', category: 'Foundational' },

  // CAS v7.5 — Phenomenological Registers
  { expr: '^3^P|A', label: 'Analytical-register Negative', category: 'v7.5 Registers' },
  { expr: '^3^P|f', label: 'Affective-register Negative', category: 'v7.5 Registers' },
  { expr: '^2^C_{F2}|T', label: 'Compound state, Transcendent', category: 'v7.5 Registers' },

  // CAS v7.6 — Production Semantics
  { expr: 'Θ(Ω_focus) = 0.6·^1^C + 0.4·^7^O → Ω_focus', label: 'Recipe definition', category: 'v7.6 Production' },
  { expr: 'Y_T(Ω_focus)', label: 'Theoretical yield query', category: 'v7.6 Production' },
  { expr: 'Θ(Ω_book) | κ_deadline = 0.5·^7^P + 0.5·^6^C → Ω_book', label: 'Recipe with catalyst', category: 'v7.6 Production' },

  // CAS v7.7 — Register Multiplicity & Operator Discipline
  { expr: '^3^P|⟨A,f,T⟩', label: 'Register-set specification', category: 'v7.7 Operator Discipline' },
  { expr: '^3^P|A + ^3^P|f + ^3^P|T', label: 'Register co-presence (defeasible)', category: 'v7.7 Operator Discipline' },
  { expr: '(^3^P|A × ^3^P|f × ^3^P|T) = Ω_refusal', label: 'Cross-register integration → emergent', category: 'v7.7 Operator Discipline' },

  // Meta-logic — Set theory / discrete math layer
  { expr: '^2 ∈ Noetics', label: 'Membership (^N ∈ Noetics)', category: 'Set Theory' },
  { expr: '^2^P ∈ States', label: 'Compound state ∈ 40-state space', category: 'Set Theory' },
  { expr: 'F2 ∈ Drives', label: 'Drive membership', category: 'Set Theory' },
  { expr: 'Foundation_1 ⊂ SubFoundations', label: 'Proper subset (28 sub-foundations)', category: 'Set Theory' },
  { expr: '∅ ⊆ Noetics', label: 'Empty set is subset of every set', category: 'Set Theory' },
  { expr: '|Noetics|', label: 'Cardinality of Noetics (= 10)', category: 'Set Theory' },
  { expr: '|States|', label: 'Cardinality of state space (= 40)', category: 'Set Theory' },
];

const OPERATOR_NAMES = [
  'Idea', 'Mind', 'Positive', 'Negative',
  'Vibration', 'Female', 'Male', 'Rhythm',
  'Above/Cause', 'Below/Effect',
];

// Quick-insert palette: every Unicode symbol that's hard to type on a US keyboard
const SYMBOL_PALETTE: { sym: string; title: string }[] = [
  // Production semantics (v7.6)
  { sym: 'Θ', title: 'Recipe Θ' },
  { sym: 'Ω_', title: 'Production target Ω_name' },
  { sym: 'Λ_', title: 'Leakage Λ_name' },
  { sym: 'κ_', title: 'Catalyst κ_name' },
  { sym: 'ι_', title: 'Inhibitor ι_name' },
  { sym: 'η', title: 'Efficiency η' },
  { sym: 'Φ', title: 'Fractal Φ' },
  // Operations
  { sym: '×', title: 'Compose / multiply ×' },
  { sym: '·', title: 'Recipe coefficient ·' },
  { sym: '→', title: 'Yields / dependency →' },
  // Set theory
  { sym: '∈', title: 'Member ∈' },
  { sym: '∉', title: 'Not member ∉' },
  { sym: '⊂', title: 'Proper subset ⊂' },
  { sym: '⊆', title: 'Subset ⊆' },
  { sym: '⊃', title: 'Proper superset ⊃' },
  { sym: '⊇', title: 'Superset ⊇' },
  { sym: '∅', title: 'Empty set ∅' },
  // Angle brackets (register-set notation)
  { sym: '⟨', title: 'Open angle ⟨ (register-set)' },
  { sym: '⟩', title: 'Close angle ⟩' },
];

// Frontend pre-processing of input before the compiler sees it. Two passes:
// 1. Newlines (Shift+Enter) become `;` so multi-line layout renders as a real
//    multi-statement program — the compiler treats `\n` as ordinary whitespace
//    and would otherwise smash statements together. Existing `;` is preserved
//    (a trailing `;` before the newline is collapsed, not doubled).
// 2. ASCII fallbacks for users without easy Unicode entry — `in`, `notin`,
//    `subset`, etc. become their Unicode equivalents so the compiler (which
//    only tokenizes Unicode) accepts them.
// Order matters: longer aliases first so `notin` doesn't match as `not`+`in`.
function expandAsciiAliases(text: string): string {
  return text
    .replace(/;?\s*\n\s*/g, '; ')     // multi-line program → ;-separated
    .replace(/\bnotin\b/g, '∉')
    .replace(/\bsubseteq\b/g, '⊆')
    .replace(/\bsubset\b/g, '⊂')
    .replace(/\bsupseteq\b/g, '⊇')
    .replace(/\bsupset\b/g, '⊃')
    .replace(/\bemptyset\b/g, '∅')
    .replace(/\bin\b/g, '∈');
}
const DOMAIN_NAMES: Record<string, string> = { P: 'Principled', C: 'Cognitive', E: 'Evaluative', O: 'Operational' };
const DRIVE_NAMES = ['Unity', 'Wisdom', 'Vitality', 'Connection', 'Agency', 'Structure', 'Purpose'];
const REGISTER_NAMES: Record<string, string> = { T: 'Transcendent', A: 'Analytical', f: 'Affective', E: 'Embodied' };

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

interface NlPipelineResult {
  text: string;
  signals: {
    operator_scores: number[];
    domain_scores: number[];
    drive_scores: number[];
    rpm_signal: number;
    word_count: number;
  };
  synthesized_notation: string;
  notation_english: string;
  compilation: {
    valid: boolean;
    error?: string | null;
    engine?: string;
    tokens: number;
    bytecode: number;
    warnings: string[];
    ast?: Record<string, unknown> | null;
    result?: Record<string, unknown> | null;
  } | null;
  interpretation: string;
}

interface HistoryEntry {
  input: string;
  result: CompileResult | null;
  nlResult?: NlPipelineResult | null;
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
    // CO-N operator (legacy form)
    const coMatch = s.slice(i).match(/^CO-\d+/);
    if (coMatch) {
      parts.push(<span key={i} className="text-cyan-400">{coMatch[0]}</span>);
      i += coMatch[0].length;
      continue;
    }
    // ^N operator (caret form)
    if (s[i] === '^' && /[0-9]/.test(s[i + 1] ?? '')) {
      parts.push(<span key={i} className="text-cyan-400">^{s[i + 1]}</span>);
      i += 2;
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
    // |⟨R1,R2,...⟩ register-set (CAS v7.7)
    const regSetMatch = s.slice(i).match(/^\|⟨[^⟩]+⟩/);
    if (regSetMatch) {
      parts.push(<span key={i} className="text-fuchsia-400">{regSetMatch[0]}</span>);
      i += regSetMatch[0].length;
      continue;
    }
    // |R single register (CAS v7.5)
    if (s[i] === '|' && /[TAfE]/.test(s[i + 1] ?? '') && !/[{a-zA-Z]/.test(s[i + 2] ?? '')) {
      parts.push(<span key={i} className="text-fuchsia-400">|{s[i + 1]}</span>);
      i += 2;
      continue;
    }
    // Y_T( / Y_A( yield query (CAS v7.6)
    const yieldMatch = s.slice(i).match(/^Y_[TA]\b/);
    if (yieldMatch) {
      parts.push(<span key={i} className="text-purple-400">{yieldMatch[0]}</span>);
      i += yieldMatch[0].length;
      continue;
    }
    // Recipe / production tokens (CAS v7.6)
    if (s.slice(i, i + 5) === 'Theta' || s[i] === 'Θ') {
      const len = s[i] === 'Θ' ? 1 : 5;
      parts.push(<span key={i} className="text-pink-400">{s.slice(i, i + len)}</span>);
      i += len;
      continue;
    }
    // Ω_name production target (with optional _name suffix)
    if (s.slice(i, i + 5) === 'Omega' || s[i] === 'Ω') {
      const headLen = s[i] === 'Ω' ? 1 : 5;
      const tailMatch = s.slice(i + headLen).match(/^_(?:\{[^}]+\}|[A-Za-z][A-Za-z0-9_]*)/);
      const totalLen = headLen + (tailMatch ? tailMatch[0].length : 0);
      parts.push(<span key={i} className="text-orange-400">{s.slice(i, i + totalLen)}</span>);
      i += totalLen;
      continue;
    }
    // Λ leakage / κ catalyst / ι inhibitor (with optional _name)
    const recipeSym = s.slice(i).match(/^(Lambda|Λ|kappa|κ|iota|ι|eta|η)(_(?:\{[^}]+\}|[A-Za-z][A-Za-z0-9_]*))?/);
    if (recipeSym) {
      parts.push(<span key={i} className="text-orange-400">{recipeSym[0]}</span>);
      i += recipeSym[0].length;
      continue;
    }
    // RPM
    if (s.slice(i, i + 3) === 'RPM') {
      parts.push(<span key={i} className="text-purple-400">RPM</span>);
      i += 3;
      continue;
    }
    // ASCII aliases for set-theory operators — colored same as their Unicode
    // equivalents so users see the alias is recognized. Expanded on submit.
    const aliasMatch = s.slice(i).match(/^(notin|subseteq|subset|supseteq|supset|emptyset|in)\b/);
    if (aliasMatch && (i === 0 || !/[A-Za-z0-9_]/.test(s[i - 1] ?? ''))) {
      const word = aliasMatch[0];
      const cls = word === 'emptyset' ? 'text-violet-300' : 'text-teal-300 font-bold';
      parts.push(<span key={i} className={cls}>{word}</span>);
      i += word.length;
      continue;
    }
    // Meta-set names (Set Theory layer): Noetics, Domains, Worlds, Drives,
    // Registers, States, Foundations, SubFoundations, Foundation_1..7, EmptySet
    const metaSetMatch = s.slice(i).match(
      /^(?:Noetics|Domains|Worlds|Drives|Registers|States|SubFoundations|Foundations|Foundation_[1-7]|EmptySet)\b/
    );
    if (metaSetMatch && (i === 0 || !/[A-Za-z0-9_]/.test(s[i - 1] ?? ''))) {
      parts.push(<span key={i} className="text-violet-300">{metaSetMatch[0]}</span>);
      i += metaSetMatch[0].length;
      continue;
    }
    // Set-theory operators (∈ ∉ ⊂ ⊆ ⊃ ⊇)
    if ('∈∉⊂⊆⊃⊇'.includes(s[i])) {
      parts.push(<span key={i} className="text-teal-300 font-bold">{s[i]}</span>);
      i += 1;
      continue;
    }
    // ∅ empty-set literal
    if (s[i] === '∅') {
      parts.push(<span key={i} className="text-violet-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Phi / Φ
    if (s.slice(i, i + 3) === 'Phi' || s[i] === 'Φ') {
      const len = s[i] === 'Φ' ? 1 : 3;
      parts.push(<span key={i} className="text-pink-400">{s.slice(i, i + len)}</span>);
      i += len;
      continue;
    }
    // Multiplicative ops × ÷ ∘ (and ASCII aliases * /) — matches Operations key color
    if ('*×/÷∘'.includes(s[i])) {
      parts.push(<span key={i} className="text-orange-400">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Recipe coefficient · — matches Operations key color
    if (s[i] === '·') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    if (s.slice(i, i + 2) === '->') {
      parts.push(<span key={i} className="text-white">→</span>);
      i += 2;
      continue;
    }
    if (s[i] === '→' || s[i] === '←' || s[i] === '↔') {
      parts.push(<span key={i} className="text-white">{s[i]}</span>);
      i += 1;
      continue;
    }
    // Bare pipe — cardinality wrapper |Set| OR recipe-condition separator (key: slate-300)
    if (s[i] === '|') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    // = (recipe definition / emergent assignment)
    if (s[i] === '=') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
      i += 1;
      continue;
    }
    if (s[i] === '+' || s[i] === '-') {
      parts.push(<span key={i} className="text-slate-300">{s[i]}</span>);
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

  // Natural language pipeline result
  if (entry.nlResult) {
    const nl = entry.nlResult;
    const valid = nl.compilation?.valid ?? false;
    return (
      <div className={`animate-[fadeSlideIn_0.3s_ease-out] rounded-lg border p-4 font-mono text-xs ${valid ? 'border-emerald-500/20 bg-emerald-500/[0.03]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-purple-400">nl&gt;</span>
          <span className="text-sm text-slate-300 font-sans">{entry.input}</span>
        </div>

        {/* Signal extraction */}
        <div className="mb-3 rounded border border-white/[0.06] bg-white/[0.02] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Signal Extraction</p>
          <div className="space-y-1">
            {nl.signals.operator_scores.map((score, i) => score > 0 ? (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="text-cyan-400 w-32 shrink-0">CO-{i} {OPERATOR_NAMES[i]}</span>
                <div className="flex-1 h-2 rounded-full bg-white/[0.04] overflow-hidden">
                  <div className="h-full rounded-full bg-cyan-500/60" style={{ width: `${score * 10}%` }} />
                </div>
                <span className="text-slate-500 w-8 text-right">{score.toFixed(1)}</span>
              </div>
            ) : null)}
          </div>
          <div className="flex gap-4 mt-2 text-[10px]">
            {(['P', 'C', 'E', 'O'] as const).map((d, i) => (
              <span key={d} className="text-emerald-400">
                {d}={nl.signals.domain_scores[i]?.toFixed(2)}
              </span>
            ))}
            <span className="text-amber-400">RPM={nl.signals.rpm_signal.toFixed(2)}</span>
          </div>
        </div>

        {/* Synthesized notation */}
        {nl.synthesized_notation && (
          <div className="mb-3 rounded border border-accent-teal/20 bg-accent-teal/[0.03] p-3">
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Synthesized Notation</p>
            <p className="text-accent-teal text-[12px]">{highlightSyntax(nl.synthesized_notation)}</p>
            {nl.notation_english && (
              <p className="text-[10px] text-slate-400 mt-1 font-sans">{nl.notation_english}</p>
            )}
          </div>
        )}

        {/* Compilation */}
        {nl.compilation && (
          <div className="mb-3 flex items-center gap-2 text-[10px]">
            {nl.compilation.valid ? <span className="text-emerald-400">Compiled</span> : <span className="text-red-400">Compilation failed</span>}
            {nl.compilation.engine && <span className="text-slate-600">engine: {nl.compilation.engine}</span>}
            <span className="text-slate-600">tokens: {nl.compilation.tokens}</span>
            <span className="text-slate-600">bytecode: {nl.compilation.bytecode}</span>
          </div>
        )}

        {/* Interpretation */}
        <div className="rounded border border-purple-500/20 bg-purple-500/[0.03] p-3">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Interpretation</p>
          <p className="text-[11px] text-slate-300 font-sans leading-relaxed">{nl.interpretation}</p>
        </div>
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

// ── Reference panel content (shared by desktop side panel + mobile overlay) ──

function RefPanelContent({ onPickExample }: { onPickExample: (expr: string) => void }) {
  const grouped = EXAMPLES.reduce<Record<string, Example[]>>((acc, ex) => {
    (acc[ex.category] ||= []).push(ex);
    return acc;
  }, {});

  return (
    <>
      {/* Examples — grouped by framework version */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Examples</p>
        <div className="space-y-3">
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <p className="text-[9px] font-mono uppercase tracking-wider text-fuchsia-400/70 mb-1">{category}</p>
              <div className="space-y-1">
                {items.map((ex) => (
                  <button
                    key={ex.expr}
                    onClick={() => onPickExample(ex.expr)}
                    className="w-full text-left rounded px-2 py-1.5 text-[10px] font-mono hover:bg-white/[0.04] transition-colors"
                  >
                    <span className="text-slate-500 block text-[9px] font-sans mb-0.5">{ex.label}</span>
                    <span className="block">{highlightSyntax(ex.expr)}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Noetics (10 cognitive operators — authoritative names) */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Noetics (^0 – ^9)</p>
        <div className="space-y-0.5">
          {OPERATOR_NAMES.map((name, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px]">
              <span className="text-cyan-400 font-mono w-8">^{i}</span>
              <span className="text-slate-500">{name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Domains */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Domains (P ≻ C ≻ E ≻ O)</p>
        {Object.entries(DOMAIN_NAMES).map(([code, name]) => (
          <div key={code} className="flex items-center gap-2 text-[10px]">
            <span className="text-emerald-400 font-mono w-6">^{code}</span>
            <span className="text-slate-500">{name}</span>
          </div>
        ))}
      </div>

      {/* Drives */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Drives (F1 – F7)</p>
        {DRIVE_NAMES.map((name, i) => (
          <div key={i} className="flex items-center gap-2 text-[10px]">
            <span className="text-amber-400 font-mono w-6">F{i + 1}</span>
            <span className="text-slate-500">{name}</span>
          </div>
        ))}
      </div>

      {/* Phenomenological Registers — CAS v7.5 */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Registers (v7.5)</p>
        {Object.entries(REGISTER_NAMES).map(([code, name]) => (
          <div key={code} className="flex items-center gap-2 text-[10px]">
            <span className="text-fuchsia-400 font-mono w-6">|{code}</span>
            <span className="text-slate-500">{name}</span>
          </div>
        ))}
        <p className="text-[9px] text-slate-600 mt-1.5 leading-relaxed">
          Specifies operational character. Optional — omit for register-neutral.
        </p>
      </div>

      {/* Production Semantics — CAS v7.6 */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Production (v7.6)</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-pink-400 font-mono">Θ(Ω)</span> <span className="text-slate-500">Recipe for target Ω</span></div>
          <div><span className="text-orange-400 font-mono">Ω_name</span> <span className="text-slate-500">Production target</span></div>
          <div><span className="text-purple-400 font-mono">Y_T / Y_A</span> <span className="text-slate-500">Theoretical / actual yield</span></div>
          <div><span className="text-orange-400 font-mono">Λ_n</span> <span className="text-slate-500">Leakage / side-reaction</span></div>
          <div><span className="text-orange-400 font-mono">κ_n</span> <span className="text-slate-500">Catalyst</span></div>
          <div><span className="text-orange-400 font-mono">ι_n</span> <span className="text-slate-500">Inhibitor</span></div>
        </div>
      </div>

      {/* Operator Discipline — CAS v7.7 */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Operator Discipline (v7.7)</p>
        <div className="space-y-1 text-[10px]">
          <div><span className="text-fuchsia-400 font-mono">|⟨…⟩</span> <span className="text-slate-500">Register-set specification</span></div>
          <div><span className="text-slate-300 font-mono">+</span> <span className="text-slate-500">Co-presence (defeasible)</span></div>
          <div><span className="text-orange-400 font-mono">×</span> <span className="text-slate-500">Integration → emergent Ω</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-1.5 leading-relaxed">
          Same-Noetic <span className="font-mono">×</span> requires named <span className="font-mono">Ω</span> result.
        </p>
      </div>

      {/* Set Theory / discrete-math layer */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Set Theory</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-teal-300 font-mono">∈ ∉</span> <span className="text-slate-500">Member / not member</span></div>
          <div><span className="text-teal-300 font-mono">⊂ ⊆</span> <span className="text-slate-500">Proper subset / subset</span></div>
          <div><span className="text-teal-300 font-mono">⊃ ⊇</span> <span className="text-slate-500">Proper superset / superset</span></div>
          <div><span className="text-violet-300 font-mono">∅</span> <span className="text-slate-500">Empty set</span></div>
          <div><span className="text-slate-300 font-mono">|S|</span> <span className="text-slate-500">Cardinality of S</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-2 mb-1 uppercase tracking-wider">Built-in sets</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-violet-300 font-mono">Noetics</span> <span className="text-slate-500">{'{^0…^9}, |·|=10'}</span></div>
          <div><span className="text-violet-300 font-mono">Domains</span> <span className="text-slate-500">{'{P,C,E,O}, |·|=4'}</span></div>
          <div><span className="text-violet-300 font-mono">Drives</span> <span className="text-slate-500">{'{F1…F7}, |·|=7'}</span></div>
          <div><span className="text-violet-300 font-mono">Registers</span> <span className="text-slate-500">{'{T,A,f,E}, |·|=4'}</span></div>
          <div><span className="text-violet-300 font-mono">States</span> <span className="text-slate-500">{'10×4 = 40 cog. states'}</span></div>
          <div><span className="text-violet-300 font-mono">Foundations</span> <span className="text-slate-500">{'7 named foundations'}</span></div>
          <div><span className="text-violet-300 font-mono">SubFoundations</span> <span className="text-slate-500">{'7×4 = 28 sub-foundations'}</span></div>
          <div><span className="text-violet-300 font-mono">Foundation_1…7</span> <span className="text-slate-500">{'individual foundation set'}</span></div>
          <div><span className="text-violet-300 font-mono">EmptySet</span> <span className="text-slate-500">{'≡ ∅'}</span></div>
        </div>
        <p className="text-[9px] text-slate-600 mt-2 leading-relaxed">
          ASCII fallbacks accepted (auto-expanded on submit):{' '}
          <span className="font-mono text-teal-300">in</span>,{' '}
          <span className="font-mono text-teal-300">notin</span>,{' '}
          <span className="font-mono text-teal-300">subset</span>,{' '}
          <span className="font-mono text-teal-300">subseteq</span>,{' '}
          <span className="font-mono text-teal-300">supset</span>,{' '}
          <span className="font-mono text-teal-300">supseteq</span>,{' '}
          <span className="font-mono text-violet-300">emptyset</span>.
        </p>
      </div>

      {/* Operations */}
      <div>
        <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Operations</p>
        <div className="space-y-0.5 text-[10px]">
          <div><span className="text-orange-400 font-mono">×</span> <span className="text-slate-500">Composition / integration</span></div>
          <div><span className="text-orange-400 font-mono">÷</span> <span className="text-slate-500">Division (algebraic)</span></div>
          <div><span className="text-orange-400 font-mono">∘</span> <span className="text-slate-500">Fractal (algebraic)</span></div>
          <div><span className="text-slate-300 font-mono">+</span> <span className="text-slate-500">Co-presence (syntactic)</span></div>
          <div><span className="text-slate-300 font-mono">·</span> <span className="text-slate-500">Recipe coefficient</span></div>
          <div><span className="text-white font-mono">→</span> <span className="text-slate-500">Dependency / yields</span></div>
        </div>
      </div>
    </>
  );
}

// ── Main Page ──

export function CompilerPage() {
  const [mode, setMode] = useState<'cas' | 'nl'>('cas');
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [showRef, setShowRef] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mirrorRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight, behavior: 'smooth' });
  }, [history]);

  // Auto-resize the textarea to fit its contents (capped to keep input area sane)
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 240) + 'px';
  }, [input]);

  const addEntry = useCallback((entry: HistoryEntry) => {
    setHistory((prev) => [...prev, entry]);
  }, []);

  // Insert a symbol from the palette at the input cursor position
  function insertSymbol(sym: string) {
    const el = inputRef.current;
    if (!el) {
      setInput((cur) => cur + sym);
      return;
    }
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const newValue = el.value.slice(0, start) + sym + el.value.slice(end);
    setInput(newValue);
    setTimeout(() => {
      el.focus();
      const pos = start + sym.length;
      try { el.setSelectionRange(pos, pos); } catch { /* selection range may be unsupported on some inputs */ }
    }, 0);
  }

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

    // Route based on mode
    setLoading(true);
    if (mode === 'nl') {
      try {
        const nlResult = await apiFetch<NlPipelineResult>('/notation/natural-language', {
          method: 'POST',
          body: JSON.stringify({ text: trimmed, compile: true }),
        });
        addEntry({ input: trimmed, result: null, nlResult, isCommand: false, timestamp: ts });
      } catch (err) {
        const detail = err instanceof Error ? err.message : String(err);
        const isNotFound = detail.includes('Not Found') || detail.includes('404');
        const errorMsg = isNotFound
          ? 'Natural Language endpoint not available. The backend needs to be redeployed with the latest code. Try deploying the API to Railway.'
          : detail;
        addEntry({ input: trimmed, result: { source: '', valid: false, error: errorMsg }, isCommand: false, timestamp: ts });
      } finally {
        setLoading(false);
      }
      return;
    }

    // CAS notation mode — compile expression. Expand ASCII aliases (in, notin,
    // subset, etc.) to canonical Unicode before the compiler sees them.
    const compileSource = expandAsciiAliases(trimmed);
    try {
      const result = await apiFetch<CompileResult>('/notation/compile', {
        method: 'POST',
        body: JSON.stringify({ expression: compileSource }),
      });
      addEntry({ input: compileSource, result, isCommand: false, timestamp: ts });
    } catch (err) {
      // If compile returns 422, the error detail has the compilation error
      const detail = err instanceof Error ? err.message : String(err);
      // Try to get the full artifact even on error
      try {
        const raw = await fetch(`${import.meta.env.PROD ? '/api' : (import.meta.env.VITE_API_URL ?? '/api')}/notation/compile`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ expression: compileSource }),
        });
        if (raw.status === 422) {
          const body = await raw.json();
          addEntry({
            input: compileSource,
            result: { source: compileSource, valid: false, error: body.detail ?? detail, engine: 'rust+python' },
            isCommand: false,
            timestamp: ts,
          });
        } else {
          addEntry({
            input: compileSource,
            result: { source: compileSource, valid: false, error: detail },
            isCommand: false,
            timestamp: ts,
          });
        }
      } catch {
        addEntry({
          input: compileSource,
          result: { source: compileSource, valid: false, error: detail },
          isCommand: false,
          timestamp: ts,
        });
      }
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      // Plain Enter submits; Shift+Enter inserts a newline (textarea default)
      e.preventDefault();
      handleSubmit();
      return;
    }
    // History recall: only when the textarea is empty, so multi-line editing
    // can use arrows naturally once any text is present.
    if (e.key === 'ArrowUp' && input.length === 0) {
      e.preventDefault();
      const next = Math.min(historyIdx + 1, cmdHistory.length - 1);
      setHistoryIdx(next);
      if (cmdHistory[next]) setInput(cmdHistory[next]);
    }
    if (e.key === 'ArrowDown' && input.length === 0) {
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
                {/* TKS 10-dot formation — 3D spheres with shadow matching ASCII depth */}
                <svg viewBox="0 0 800 1100" className="shrink-0" style={{ height: '100px', width: '58px' }}>
                  <defs>
                    <radialGradient id="dotGrad" cx="35%" cy="35%" r="65%">
                      <stop offset="0%" stopColor="#5ce0d6" />
                      <stop offset="70%" stopColor="#38b2ac" />
                      <stop offset="100%" stopColor="#2a9d8f" />
                    </radialGradient>
                    <filter id="dotShadow" x="-20%" y="-20%" width="150%" height="150%">
                      <feDropShadow dx="8" dy="8" stdDeviation="0" floodColor="rgba(56,178,172,0.3)" />
                      <feDropShadow dx="0" dy="0" stdDeviation="12" floodColor="rgba(56,178,172,0.2)" />
                    </filter>
                  </defs>
                  <circle cx="400" cy="55"   r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0s infinite alternate' }} />
                  <circle cx="110" cy="190"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.25s infinite alternate' }} />
                  <circle cx="690" cy="190"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.5s infinite alternate' }} />
                  <circle cx="400" cy="400"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 0.75s infinite alternate' }} />
                  <circle cx="110" cy="545"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.0s infinite alternate' }} />
                  <circle cx="690" cy="545"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.25s infinite alternate' }} />
                  <circle cx="400" cy="690"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.5s infinite alternate' }} />
                  <circle cx="110" cy="870"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 1.75s infinite alternate' }} />
                  <circle cx="690" cy="870"  r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 2.0s infinite alternate' }} />
                  <circle cx="400" cy="1020" r="90" fill="url(#dotGrad)" filter="url(#dotShadow)" style={{ animation: 'tks-breathe 2.5s ease-in-out 2.25s infinite alternate' }} />
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

        {/* Mode toggle + Input area */}
        <div className="border-t border-white/[0.06]" style={{ backgroundColor: '#0d1117' }}>
          <div className="flex gap-1 px-3 pt-2">
            <button
              onClick={() => setMode('cas')}
              className={`rounded px-2 py-1 text-[10px] font-mono transition-colors ${mode === 'cas' ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-600 hover:text-slate-400'}`}
            >
              CAS Notation
            </button>
            <button
              onClick={() => setMode('nl')}
              className={`rounded px-2 py-1 text-[10px] font-mono transition-colors ${mode === 'nl' ? 'bg-purple-500/15 text-purple-400' : 'text-slate-600 hover:text-slate-400'}`}
            >
              Natural Language
            </button>
          </div>
          {/* Quick-insert symbol palette — Unicode chars hard to type on a US keyboard */}
          {mode === 'cas' && (
            <div className="px-3 pt-2 pb-0 flex items-center gap-1 overflow-x-auto whitespace-nowrap scrollbar-thin">
              {SYMBOL_PALETTE.map((item) => (
                <button
                  key={item.sym}
                  onClick={() => insertSymbol(item.sym)}
                  title={item.title}
                  type="button"
                  className="shrink-0 px-2 py-1 rounded text-xs font-mono border border-white/[0.06] hover:border-accent-teal/50 hover:bg-white/[0.04] transition-colors leading-none min-h-[28px]"
                >
                  {highlightSyntax(item.sym)}
                </button>
              ))}
            </div>
          )}
          <div className="p-3 pt-1 flex items-start gap-2">
          <span className={`font-mono text-sm font-bold shrink-0 pt-2 ${mode === 'nl' ? 'text-purple-400' : 'text-accent-teal'}`}>
            {mode === 'nl' ? 'nl>' : 'cas>'}
          </span>
          <div className="flex-1 relative min-h-[44px]">
            {mode === 'cas' && input && (
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 font-mono text-sm overflow-hidden"
              >
                <div ref={mirrorRef} className="whitespace-pre-wrap break-words py-2">
                  {highlightSyntax(input)}
                </div>
              </div>
            )}
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onScroll={(e) => {
                // Keep the colored mirror in lockstep with the textarea's scroll
                if (mirrorRef.current) {
                  mirrorRef.current.style.transform =
                    `translateY(${-e.currentTarget.scrollTop}px)`;
                }
              }}
              placeholder={mode === 'nl'
                ? 'Type any sentence or paragraph...'
                : 'Θ(Ω_focus)|κ_n = 0.6·^2^P_{F2}|A + 0.4·^5^C → Ω_focus;  ^2 ∈ Noetics'}
              rows={1}
              className={`block w-full bg-transparent border-none outline-none text-sm placeholder-slate-700 resize-none whitespace-pre-wrap break-words py-2 px-0 leading-normal ${mode === 'nl' ? 'font-sans caret-purple-400 text-slate-200' : 'font-mono caret-accent-teal text-transparent selection:bg-accent-teal/30'}`}
              style={{ maxHeight: '240px', overflowY: 'auto' }}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <button
            onClick={() => setShowRef(!showRef)}
            className="shrink-0 px-2 py-1 rounded text-[10px] font-mono text-slate-500 hover:text-slate-300 border border-white/[0.06] hover:border-white/[0.12] transition-colors min-h-[36px] mt-1"
          >
            {showRef ? 'Hide Ref' : 'Ref'}
          </button>
          </div>
        </div>
      </div>

      {/* Desktop side panel — only renders at sm and up */}
      {showRef && (
        <div className="hidden sm:block w-72 border-l border-white/[0.06] overflow-y-auto p-4 space-y-5 shrink-0" style={{ backgroundColor: '#0d1117' }}>
          <RefPanelContent onPickExample={(expr) => { setInput(expr); inputRef.current?.focus(); }} />
        </div>
      )}

      {/* Mobile full-screen overlay — only renders below sm. No slide-out side panel. */}
      {showRef && (
        <div className="sm:hidden fixed inset-0 z-50 flex flex-col" style={{ backgroundColor: '#0d1117' }}>
          <div className="flex items-center justify-between border-b border-white/[0.06] p-3 shrink-0">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-300">Reference</span>
            <button
              onClick={() => setShowRef(false)}
              className="px-3 py-1.5 rounded text-[11px] font-mono text-slate-200 border border-white/[0.12] hover:border-white/[0.24] active:bg-white/[0.04]"
            >
              Close
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            <RefPanelContent
              onPickExample={(expr) => {
                setInput(expr);
                setShowRef(false);
                inputRef.current?.focus();
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
