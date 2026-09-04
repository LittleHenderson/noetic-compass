'use client';

import { type RefObject, useState } from 'react';
import {
  Calculator,
  CheckCircle2,
  Download,
  FileCheck2,
  LoaderCircle,
  Search,
  ShieldCheck,
  Sigma,
  TriangleAlert,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { CncmClient } from '@/lib/cncm-client';

type MathMode = 'solve' | 'counterexample';

interface RationalValue {
  numerator: number;
  denominator: number;
}

interface MathReceipt {
  receipt_id?: string;
  accepted?: boolean;
  rejection_code?: string;
  discharged_guards?: string[];
  detail?: string;
}

interface MathStep {
  index?: number;
  proposal?: {
    operation?: string;
    proposed_conclusion?: Record<string, unknown>;
  };
  receipt?: MathReceipt;
  resulting_claim?: {
    claim_id?: string;
    statement?: Record<string, unknown>;
    status?: string;
  } | null;
}

interface MathResult {
  problem_id?: string;
  terminal_status?: string;
  solve_variable?: string;
  solution?: RationalValue | null;
  checked_steps?: MathStep[];
  evidence?: {
    verified?: boolean;
    proof_digest?: string;
    evidence_digest?: string;
    checker_version?: string;
    claim_boundary?: Record<string, unknown>;
  };
  detail?: string;
  result_digest?: string;
  [key: string]: unknown;
}

interface CounterexampleResult {
  status?: string;
  assignment?: Array<[string, number]>;
  exact_left?: RationalValue | null;
  exact_right?: RationalValue | null;
  tested_assignments?: number;
  max_assignments?: number;
  detail?: string;
  result_digest?: string;
  [key: string]: unknown;
}

interface CounterexampleBound {
  variable: string;
  lower: number;
  upper: number;
}

interface MathPanelProps {
  clientRef: RefObject<CncmClient | null>;
  runtimeReady: boolean;
  onNotice: (message: string) => void;
}

const SOLVE_PRESETS = [
  ['Parentheses', '2*(x+3)=14'],
  ['Exact rational', 'x+1/3=5/6'],
  ['Both sides', '2*x+1=x+4'],
  ['No solution', '0*x=3'],
] as const;

function rational(value?: RationalValue | null) {
  if (!value) return '—';
  return value.denominator === 1 ? String(value.numerator) : `${value.numerator}/${value.denominator}`;
}

function shortHash(value?: string) {
  if (!value) return '—';
  return `${value.slice(0, 12)}…${value.slice(-8)}`;
}

function parseCounterexampleBounds(value: string): CounterexampleBound[] {
  const parsed: unknown = JSON.parse(value);
  if (!Array.isArray(parsed) || parsed.length < 1 || parsed.length > 3) {
    throw new Error('Bounds must be a JSON array containing one to three variable bounds.');
  }
  const names = new Set<string>();
  return parsed.map((item, index) => {
    if (typeof item !== 'object' || item === null || Array.isArray(item)) {
      throw new Error(`Bound ${index + 1} must be an object.`);
    }
    const record = item as Record<string, unknown>;
    if (
      Object.keys(record).some((key) => !['variable', 'lower', 'upper'].includes(key)) ||
      typeof record.variable !== 'string' ||
      record.variable.trim() === '' ||
      !Number.isSafeInteger(record.lower) ||
      !Number.isSafeInteger(record.upper)
    ) {
      throw new Error(`Bound ${index + 1} requires only variable, lower, and upper with safe integer limits.`);
    }
    const variable = record.variable.trim();
    const lower = record.lower as number;
    const upper = record.upper as number;
    if (names.has(variable)) throw new Error(`Duplicate bound for variable ${variable}.`);
    if (lower > upper) throw new Error(`Bound ${index + 1} requires lower ≤ upper.`);
    names.add(variable);
    return { variable, lower, upper };
  });
}

function parseGuards(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function JsonView({ value }: { value: unknown }) {
  return (
    <pre className="max-h-[420px] overflow-auto border border-border bg-[#050b0e] p-3 font-mono text-[10px] leading-5 text-cyan-50">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function MathPanel({ clientRef, runtimeReady, onNotice }: MathPanelProps) {
  const [mode, setMode] = useState<MathMode>('solve');
  const [notation, setNotation] = useState('2*(x+3)=14');
  const [variable, setVariable] = useState('x');
  const [boundsJson, setBoundsJson] = useState('[{"variable":"x","lower":-3,"upper":3}]');
  const [guardsText, setGuardsText] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<MathResult | null>(null);
  const [counterexample, setCounterexample] = useState<CounterexampleResult | null>(null);
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);
  const [validation, setValidation] = useState<Record<string, unknown> | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  const invalidateRetainedEvidence = () => {
    setResult(null);
    setCounterexample(null);
    setVerification(null);
    setValidation(null);
    setShowRaw(false);
  };

  const validateNotation = async () => {
    if (!clientRef.current || !runtimeReady) return;
    setBusy('validate');
    setValidation(null);
    try {
      const variables = mode === 'solve'
        ? [variable.trim()]
        : parseCounterexampleBounds(boundsJson).map((item) => item.variable);
      const statements = [notation, ...(mode === 'counterexample' ? parseGuards(guardsText) : [])];
      const reports: Record<string, unknown>[] = [];
      for (const statement of statements) {
        const reply = await clientRef.current.mathValidate(statement, variables);
        if (!reply.ok || !reply.report) {
          throw new Error(reply.error?.message ?? 'Math notation validation failed closed');
        }
        reports.push({ notation: statement, ...reply.report });
      }
      const valid = reports.every((report) => report.valid === true);
      setValidation({ valid, reports });
      onNotice(valid ? 'Every entered statement is valid in the bounded ASCII grammar.' : 'At least one statement is outside the bounded grammar.');
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const solve = async () => {
    if (!clientRef.current || !runtimeReady) return;
    const requestedNotation = notation;
    const solveVariable = variable.trim();
    setBusy('solve');
    setResult(null);
    setCounterexample(null);
    setVerification(null);
    onNotice('The bounded CAS-Math solver is proposing a linear proof; the exact checker will reconstruct every step…');
    try {
      const reply = await clientRef.current.mathSolve(requestedNotation, solveVariable);
      if (!reply.ok || !reply.math_result) {
        throw new Error(reply.error?.message ?? 'CAS-Math solve failed closed');
      }
      const mathResult = reply.math_result as MathResult;
      setResult(mathResult);
      setVerification(reply.math_verification ?? null);
      onNotice(
        mathResult.terminal_status === 'VERIFIED'
          ? `Exact solution ${mathResult.solve_variable ?? solveVariable} = ${rational(mathResult.solution)} verified by protected reconstruction.`
          : `CAS-Math stopped with ${mathResult.terminal_status}: ${mathResult.detail}`,
      );
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const searchCounterexample = async () => {
    if (!clientRef.current || !runtimeReady) return;
    const requestedNotation = notation;
    const requestedBounds = boundsJson;
    const requestedGuards = guardsText;
    setBusy('counterexample');
    setResult(null);
    setVerification(null);
    setCounterexample(null);
    onNotice('Searching the frozen bounded-integer order for one exact falsifying assignment…');
    try {
      const bounds = parseCounterexampleBounds(requestedBounds);
      const guards = parseGuards(requestedGuards);
      const reply = await clientRef.current.mathCounterexample(
        requestedNotation,
        bounds,
        guards,
      );
      if (!reply.ok || !reply.math_counterexample) {
        throw new Error(reply.error?.message ?? 'Counterexample search failed closed');
      }
      const found = reply.math_counterexample as CounterexampleResult;
      setCounterexample(found);
      setVerification(reply.math_verification ?? null);
      onNotice(
        found.status === 'FOUND'
          ? `Exact counterexample found after ${found.tested_assignments} assignment(s).`
          : `${found.status}: ${found.detail}`,
      );
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const verifyAgain = async () => {
    if (!clientRef.current || (!result && !counterexample)) return;
    setBusy('verify');
    onNotice(
      result
        ? 'Re-executing the retained math proof from its typed input…'
        : 'Re-running the retained bounded counterexample search…',
    );
    try {
      const reply = result
        ? await clientRef.current.mathVerify(result as Record<string, unknown>)
        : await clientRef.current.mathVerifyCounterexample(
            counterexample as Record<string, unknown>,
          );
      if (!reply.ok || !reply.report) throw new Error(reply.error?.message ?? 'Math verification failed');
      setVerification(reply.report);
      const valid = reply.report.valid === true;
      onNotice(
        valid
          ? 'Fresh same-runtime semantic re-execution matched exactly.'
          : 'Math result failed re-execution.',
      );
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const download = () => {
    const payload = result ?? counterexample;
    if (!payload) return;
    const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${result?.problem_id ?? 'cncm-math-counterexample'}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    onNotice('CAS-Math receipt downloaded as JSON.');
  };

  const status = result?.terminal_status ?? counterexample?.status;
  const statusSuccess = status === 'VERIFIED' || status === 'FOUND';

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(360px,0.8fr)_minmax(520px,1.2fr)]">
      <div className="h-fit border border-border bg-card/80 xl:sticky xl:top-24">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Standalone CAS-Math</p>
              <h2 className="mt-1 text-lg font-semibold">Exact verification bench</h2>
            </div>
            <Badge variant="outline" className="rounded-sm border-emerald-400/30 text-emerald-300">BOUNDED EXACT CHECKER</Badge>
          </div>
          <p className="mt-3 text-xs leading-6 text-muted-foreground">
            CAS proposes the work. The separate exact kernel reconstructs each admitted transformation. A generated status label is never enough: checked claims require a semantically re-executable receipt chain.
          </p>
        </div>

        <div className="space-y-4 p-4">
          <div className="flex gap-1 border border-border bg-muted/10 p-1">
            <button type="button" disabled={busy !== null} onClick={() => { setMode('solve'); setNotation('2*(x+3)=14'); invalidateRetainedEvidence(); }} className={`flex-1 border px-3 py-2 font-mono text-[10px] disabled:cursor-not-allowed disabled:opacity-50 ${mode === 'solve' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground'}`}>
              <Calculator className="mr-1 inline size-3.5" /> Solve linear
            </button>
            <button type="button" disabled={busy !== null} onClick={() => { setMode('counterexample'); setNotation('x*x<5'); setBoundsJson('[{"variable":"x","lower":-3,"upper":3}]'); setGuardsText(''); invalidateRetainedEvidence(); }} className={`flex-1 border px-3 py-2 font-mono text-[10px] disabled:cursor-not-allowed disabled:opacity-50 ${mode === 'counterexample' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground'}`}>
              <Search className="mr-1 inline size-3.5" /> Counterexample
            </button>
          </div>

          <label className="block" htmlFor="math-notation">
            <span className="eyebrow">{mode === 'solve' ? 'Equation' : 'Universal conjecture'}</span>
            <Textarea id="math-notation" value={notation} disabled={busy !== null} onChange={(event) => { setNotation(event.target.value); invalidateRetainedEvidence(); }} className="mt-2 min-h-24 rounded-none font-mono text-sm" spellCheck={false} />
          </label>

          {mode === 'solve' ? (
            <label htmlFor="math-variable">
              <span className="eyebrow">Variable</span>
              <Input id="math-variable" value={variable} disabled={busy !== null} onChange={(event) => { setVariable(event.target.value); invalidateRetainedEvidence(); }} className="mt-2 rounded-none font-mono" />
            </label>
          ) : (
            <div className="grid gap-3">
              <label htmlFor="math-bounds">
                <span className="eyebrow">Bounds JSON · 1–3 variables</span>
                <Textarea id="math-bounds" value={boundsJson} disabled={busy !== null} onChange={(event) => { setBoundsJson(event.target.value); invalidateRetainedEvidence(); }} className="mt-2 min-h-20 rounded-none font-mono text-[11px]" spellCheck={false} />
              </label>
              <label htmlFor="math-guards">
                <span className="eyebrow">Optional guards · one statement per line</span>
                <Textarea id="math-guards" value={guardsText} disabled={busy !== null} onChange={(event) => { setGuardsText(event.target.value); invalidateRetainedEvidence(); }} placeholder={'x!=0 is not in the grammar; use a supported relation such as 0<x'} className="mt-2 min-h-16 rounded-none font-mono text-[11px]" spellCheck={false} />
              </label>
            </div>
          )}

          {mode === 'solve' && (
            <div>
              <p className="eyebrow">Exact fixtures</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {SOLVE_PRESETS.map(([label, value]) => <Button key={label} variant="outline" size="xs" className="rounded-none" disabled={busy !== null} onClick={() => { setNotation(value); invalidateRetainedEvidence(); }}>{label}</Button>)}
              </div>
            </div>
          )}

          <div className="grid gap-2 sm:grid-cols-[0.7fr_1.3fr]">
            <Button variant="outline" className="rounded-none" disabled={!runtimeReady || busy !== null} onClick={() => void validateNotation()}>
              {busy === 'validate' ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <FileCheck2 data-icon="inline-start" />}
              Validate notation
            </Button>
            <Button className="rounded-none" disabled={!runtimeReady || busy !== null} onClick={() => void (mode === 'solve' ? solve() : searchCounterexample())}>
              {busy && busy !== 'validate' ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : mode === 'solve' ? <Sigma data-icon="inline-start" /> : <Search data-icon="inline-start" />}
              {mode === 'solve' ? 'Propose + verify proof' : 'Search exact bounds'}
            </Button>
          </div>

          {validation && (
            <div className={`border p-3 text-[10px] leading-5 ${validation.valid === true ? 'border-emerald-400/30 bg-emerald-400/5 text-emerald-100' : 'border-rose-400/30 bg-rose-400/5 text-rose-100'}`}>
              Notation validation: {validation.valid === true ? 'VALID' : 'INVALID'} · fresh parser check in this runtime.
            </div>
          )}

          <div className="border border-border bg-muted/10 p-3 text-[10px] leading-5 text-muted-foreground">
            <p className="font-mono text-cyan-100">cncm.q-linear/0.1</p>
            <p>ASCII grammar · explicit multiplication · exact rationals · guarded division · one variable for solving · one to three bounded variables plus optional guards for counterexamples.</p>
          </div>
        </div>
      </div>

      <div className="min-h-[620px] border border-border bg-card/80">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4">
          <div>
            <p className="eyebrow">Exact result</p>
            <div className="mt-1 flex items-center gap-2">
              <h2 className="text-lg font-semibold">{counterexample ? 'Search receipt inspector' : 'Proof and receipt inspector'}</h2>
              {status && <Badge variant="outline" className={`rounded-sm ${statusSuccess ? 'border-emerald-400/30 text-emerald-300' : 'border-amber-400/30 text-amber-300'}`}>{status}</Badge>}
            </div>
          </div>
          <div className="flex gap-2">
            {(result || counterexample) && <Button variant="outline" size="sm" className="rounded-none" onClick={() => void verifyAgain()} disabled={busy !== null}><ShieldCheck data-icon="inline-start" /> Re-execute</Button>}
            {(result || counterexample) && <Button variant="outline" size="sm" className="rounded-none" onClick={download}><Download data-icon="inline-start" /> Download</Button>}
          </div>
        </div>

        {!result && !counterexample ? (
          <div className="grid min-h-[540px] place-items-center p-8 text-center">
            <div className="max-w-md">
              <Sigma className="mx-auto size-10 text-primary/70" />
              <h3 className="mt-4 text-base font-semibold">Run an exact mathematical task</h3>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">{mode === 'solve' ? 'A solve result shows the typed AST, every proposal, checker-created receipts, discharged guards, checked claims, and tamper-evident digests.' : 'A search result shows the typed statement, guards, exact bounds, tested-assignment count, first falsifying assignment when found, and a tamper-evident digest.'}</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4 p-4">
            {result && (
              <>
                <div className={`grid gap-px border bg-border sm:grid-cols-3 ${result.terminal_status === 'VERIFIED' ? 'border-emerald-400/30' : 'border-amber-400/30'}`}>
                  <div className="bg-card p-4"><p className="eyebrow">Terminal</p><p className="mt-2 font-mono text-sm text-cyan-100">{result.terminal_status}</p></div>
                  <div className="bg-card p-4"><p className="eyebrow">Exact solution</p><p className="mt-2 font-mono text-xl text-primary">{result.solution ? `${result.solve_variable ?? '—'} = ${rational(result.solution)}` : '—'}</p></div>
                  <div className="bg-card p-4"><p className="eyebrow">Checked steps</p><p className="mt-2 font-mono text-xl text-primary">{result.checked_steps?.length ?? 0}</p></div>
                </div>
                <p className="border border-border bg-muted/10 px-3 py-2 text-xs leading-6 text-muted-foreground">{result.detail}</p>

                <div>
                  <div className="mb-2 flex items-center justify-between"><p className="eyebrow">Reconstructed proof</p><Badge variant="outline" className="rounded-sm font-mono text-[9px]">{result.evidence?.checker_version}</Badge></div>
                  <div className="space-y-2">
                    {result.checked_steps?.map((step) => (
                      <article key={step.receipt?.receipt_id ?? step.index} className="border border-border bg-muted/10 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2"><span className="grid size-6 place-items-center border border-primary/30 font-mono text-[9px] text-primary">{(step.index ?? 0) + 1}</span><code className="text-[10px] text-cyan-100">{step.proposal?.operation}</code></div>
                          <Badge variant="outline" className={step.receipt?.accepted ? 'rounded-sm border-emerald-400/30 text-emerald-300' : 'rounded-sm border-rose-400/30 text-rose-300'}>{step.receipt?.accepted ? 'ACCEPTED' : step.receipt?.rejection_code}</Badge>
                        </div>
                        <p className="mt-2 break-all font-mono text-[9px] text-muted-foreground">receipt {step.receipt?.receipt_id}</p>
                        {(step.receipt?.discharged_guards?.length ?? 0) > 0 && <p className="mt-2 text-[10px] text-emerald-200">Guards: {step.receipt?.discharged_guards?.join(' · ')}</p>}
                      </article>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className={`border p-3 ${verification?.valid === true ? 'border-emerald-400/30 bg-emerald-400/5' : 'border-border bg-muted/10'}`}>
                    <div className="flex items-center gap-2 text-xs font-semibold">{verification?.valid === true ? <CheckCircle2 className="size-4 text-emerald-300" /> : <FileCheck2 className="size-4 text-primary" />} Fresh same-runtime re-execution</div>
                    <p className="mt-1.5 text-[10px] text-muted-foreground">{verification?.valid === true ? 'The same exact implementation reproduced the retained result from typed input.' : 'Press Re-execute to check this result again.'}</p>
                  </div>
                  <div className="border border-border bg-muted/10 p-3"><p className="eyebrow">Proof digest</p><p className="mt-2 break-all font-mono text-[9px] text-cyan-100">{shortHash(result.evidence?.proof_digest)}</p></div>
                </div>
              </>
            )}

            {counterexample && (
              <>
                <div className="grid gap-px border border-border bg-border sm:grid-cols-3">
                  <div className="bg-card p-4"><p className="eyebrow">Search status</p><p className="mt-2 font-mono text-sm text-primary">{counterexample.status}</p></div>
                  <div className="bg-card p-4"><p className="eyebrow">Assignments tested</p><p className="mt-2 font-mono text-xl text-primary">{counterexample.tested_assignments}</p></div>
                  <div className="bg-card p-4"><p className="eyebrow">Exact comparison</p><p className="mt-2 font-mono text-sm text-cyan-100">{rational(counterexample.exact_left)} vs {rational(counterexample.exact_right)}</p></div>
                </div>
                {counterexample.status === 'FOUND' ? (
                  <div className="border border-rose-400/30 bg-rose-400/5 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-rose-200"><TriangleAlert className="size-4" /> Universal conjecture disproved within declared bounds</div><p className="mt-2 font-mono text-sm text-rose-100">{counterexample.assignment?.map(([name, value]) => `${name} = ${value}`).join(', ')}</p></div>
                ) : (
                  <div className="border border-amber-400/30 bg-amber-400/5 p-4 text-xs leading-6 text-amber-100">{counterexample.detail}</div>
                )}
                <p className="text-[10px] leading-5 text-muted-foreground">No counterexample within finite bounds never upgrades a conjecture to VERIFIED.</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className={`border p-3 ${verification?.valid === true ? 'border-emerald-400/30 bg-emerald-400/5' : 'border-border bg-muted/10'}`}>
                    <div className="flex items-center gap-2 text-xs font-semibold">{verification?.valid === true ? <CheckCircle2 className="size-4 text-emerald-300" /> : <FileCheck2 className="size-4 text-primary" />} Fresh same-runtime search re-execution</div>
                    <p className="mt-1.5 text-[10px] text-muted-foreground">{verification?.valid === true ? 'The exact bounded search reproduced the retained result.' : 'Press Re-execute to run the retained search again.'}</p>
                  </div>
                  <div className="border border-border bg-muted/10 p-3"><p className="eyebrow">Search digest</p><p className="mt-2 break-all font-mono text-[9px] text-cyan-100">{shortHash(counterexample.result_digest)}</p></div>
                </div>
              </>
            )}

            <button type="button" onClick={() => setShowRaw((value) => !value)} className="font-mono text-[10px] uppercase tracking-[0.12em] text-primary hover:underline">{showRaw ? 'Hide' : 'Show'} raw typed receipt</button>
            {showRaw && <JsonView value={result ?? counterexample} />}
          </div>
        )}
      </div>
    </section>
  );
}
