'use client';

import { useMemo, useState } from 'react';
import type { RefObject } from 'react';
import {
  CheckCircle2,
  CircleDot,
  GitCompareArrows,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  StepForward,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CncmClient } from '@/lib/cncm-client';

type DemoCase = 'passive_voice' | 'negation' | 'teacher_cannot_commit';

interface GateResult {
  gate?: string;
  passed?: boolean;
  details?: string[];
}

interface QualificationReceipt {
  receipt_id?: string;
  receipt_digest?: string;
  candidate_id?: string;
  suite_content_id?: string;
  suite_digest?: string;
  independent_seed?: string;
  passed?: boolean;
  gates?: GateResult[];
  examiner?: Record<string, unknown>;
}

interface ParseResult {
  status?: string;
  semantics?: Record<string, unknown> | null;
  interpretations?: Array<Record<string, unknown>>;
}

interface LanguageQualificationResult {
  case_id?: DemoCase;
  principle?: string;
  candidate_id?: string;
  candidate_status?: string;
  active_count?: number;
  active_count_after_teacher_submission?: number;
  active_digest_before?: string;
  active_digest_after_submission?: string;
  parse_without_receipts?: ParseResult;
  native_parse_before_qualification?: ParseResult;
  qualification_receipt?: QualificationReceipt;
  provisional_version?: Record<string, unknown>;
  shadow_parse_after_provisional?: ParseResult;
  retention_receipt?: Record<string, unknown>;
  durable_version?: Record<string, unknown>;
  semantic_law?: Record<string, unknown>;
  store_snapshot_digest?: string;
  active_grammar_digest?: string;
  teacher_confidence_basis_points_informational_only?: number;
  teacher_confidence_informational_only?: number;
  authority_boundary?: Record<string, unknown>;
  kernel_integrated?: boolean;
}

interface LanguageApprenticeshipPanelProps {
  clientRef: RefObject<CncmClient | null>;
  runtimeReady: boolean;
  onNotice: (message: string) => void;
}

const CASES: Array<{
  id: DemoCase;
  label: string;
  eyebrow: string;
  description: string;
  law: string;
}> = [
  {
    id: 'passive_voice',
    label: 'Passive voice',
    eyebrow: 'ROLE PRESERVATION',
    description: 'Qualify one reusable passive construction against active/passive equivalence and role reversal.',
    law: 'active core = passive core; role-reversed core ≠ active core',
  },
  {
    id: 'negation',
    label: 'Negation',
    eyebrow: 'POLARITY PRESERVATION',
    description: 'Qualify a past-tense negation construction without collapsing the positive event.',
    law: 'predicate stays equal; polarity stays different',
  },
  {
    id: 'teacher_cannot_commit',
    label: 'Teacher attack',
    eyebrow: 'AUTHORITY BOUNDARY',
    description: 'Submit a high-confidence teacher lesson and verify that no active grammar changes without receipts.',
    law: 'teacher proposal → candidate only; active grammar writes = 0',
  },
];

function shortHash(value?: string) {
  if (!value) return '—';
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

function statusTone(value?: string | boolean) {
  if (value === true || value === 'PARSED' || value === 'CCB_L1_GRAM_ACTIVE') {
    return 'border-emerald-400/30 bg-emerald-400/5 text-emerald-200';
  }
  if (value === false || value === 'UNKNOWN_CONSTRUCTION') {
    return 'border-amber-400/30 bg-amber-400/5 text-amber-100';
  }
  return 'border-border bg-muted/15 text-foreground';
}

function JsonBlock({ value, className = '' }: { value: unknown; className?: string }) {
  return (
    <pre className={`overflow-auto border border-border bg-[#050b0e] p-3 font-mono text-[10px] leading-5 text-cyan-50 ${className}`}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function SemanticCard({ label, value }: { label: string; value: unknown }) {
  return (
    <article className="border border-border bg-muted/10 p-3">
      <p className="font-mono text-[8px] uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <JsonBlock value={value ?? 'NOT AVAILABLE'} className="mt-2 max-h-56 border-border/70" />
    </article>
  );
}

export function LanguageApprenticeshipPanel({
  clientRef,
  runtimeReady,
  onNotice,
}: LanguageApprenticeshipPanelProps) {
  const [caseId, setCaseId] = useState<DemoCase>('passive_voice');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<LanguageQualificationResult | null>(null);
  const [revealedGates, setRevealedGates] = useState(0);

  const selected = useMemo(() => CASES.find((item) => item.id === caseId) ?? CASES[0], [caseId]);
  const gates = result?.qualification_receipt?.gates ?? [];
  const visibleGates = gates.slice(0, revealedGates || gates.length);
  const isAttack = caseId === 'teacher_cannot_commit';
  const semanticLaw = result?.semantic_law ?? {};
  const authorityBoundary = result?.authority_boundary ?? {};

  const runQualification = async () => {
    if (!clientRef.current || !runtimeReady) return;
    setBusy(true);
    setResult(null);
    setRevealedGates(0);
    onNotice(`Running the browser-local ${selected.label.toLowerCase()} apprenticeship case…`);
    try {
      const reply = await clientRef.current.languageQualify(caseId);
      if (!reply.ok || !reply.language_qualification) {
        throw new Error(reply.error?.message ?? 'Language qualification failed closed.');
      }
      const next = reply.language_qualification as LanguageQualificationResult;
      setResult(next);
      setRevealedGates(next.qualification_receipt?.gates?.length ?? 0);
      onNotice(
        isAttack
          ? 'Authority check complete: the teacher proposal produced no active grammar write.'
          : 'Local qualification complete. Inspect the evidence and the explicit non-kernel boundary.',
      );
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setResult(null);
    setRevealedGates(0);
    onNotice('Language apprenticeship bench reset. No CNCM kernel or durable memory state was changed.');
  };

  return (
    <section className="border border-border bg-card/75">
      <header className="border-b border-border p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="rounded-sm border-amber-400/35 bg-amber-400/5 font-mono text-[9px] text-amber-200">EXPERIMENTAL</Badge>
              <Badge variant="outline" className="rounded-sm border-cyan-400/35 bg-cyan-400/5 font-mono text-[9px] text-cyan-200">LOCAL QUALIFICATION</Badge>
              <Badge variant="outline" className="rounded-sm border-rose-400/35 bg-rose-400/5 font-mono text-[9px] text-rose-200">NOT KERNEL-INTEGRATED</Badge>
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-tight text-foreground">Language Apprenticeship Qualification Bench</h2>
            <p className="mt-2 text-xs leading-6 text-muted-foreground">
              Exercise the bounded grammar compiler, independent examination ladder, semantic contrasts, retention receipts, and proposal-only teacher boundary inside the pinned browser runtime.
            </p>
          </div>
          <div className="border border-primary/25 bg-primary/5 px-3 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-primary">
            Foreign proposals permitted · foreign commitments prohibited
          </div>
        </div>
      </header>

      <div className="grid gap-px bg-border lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="bg-card p-3">
          <p className="eyebrow px-1">Qualification cases</p>
          <div className="mt-2 space-y-2">
            {CASES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setCaseId(item.id);
                  setResult(null);
                  setRevealedGates(0);
                }}
                className={`w-full border p-3 text-left transition-colors ${caseId === item.id ? 'border-primary/40 bg-primary/10' : 'border-border/70 bg-muted/5 hover:border-primary/25 hover:bg-muted/20'}`}
              >
                <span className="block font-mono text-[8px] tracking-[0.14em] text-primary/75">{item.eyebrow}</span>
                <span className="mt-1 block text-sm font-medium">{item.label}</span>
                <span className="mt-1.5 block text-[10px] leading-5 text-muted-foreground">{item.description}</span>
              </button>
            ))}
          </div>
          <div className="mt-3 space-y-2 border-t border-border pt-3">
            <Button type="button" className="w-full rounded-none" onClick={() => void runQualification()} disabled={!runtimeReady || busy}>
              {busy ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <Play data-icon="inline-start" />}
              Run local grammar qualification
            </Button>
            <Button type="button" variant="outline" className="w-full rounded-none" onClick={reset} disabled={busy}>
              <RotateCcw data-icon="inline-start" /> Reset bench
            </Button>
          </div>
        </aside>

        <div className="min-w-0 bg-background/40 p-4 sm:p-5">
          <div className="grid gap-3 md:grid-cols-3">
            {[
              ['TEACHER', 'Typed lesson proposal only', 'No state or promotion authority'],
              ['EXAMINER', 'Local identity-separated fixture suite', 'Different identity and seed; not external custody'],
              ['NATIVE / SHADOW', 'Candidate compiler comparison', 'Provisional rule cannot silently commit'],
            ].map(([label, title, detail]) => (
              <article key={label} className="border border-border bg-card/60 p-3">
                <p className="font-mono text-[8px] tracking-[0.15em] text-primary">{label}</p>
                <p className="mt-1.5 text-xs font-medium">{title}</p>
                <p className="mt-1 text-[10px] leading-5 text-muted-foreground">{detail}</p>
              </article>
            ))}
          </div>

          <div className="mt-4 border border-border bg-card/55 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="eyebrow">Selected law</p>
                <h3 className="mt-1.5 text-base font-semibold">{selected.label}</h3>
                <p className="mt-1 text-[11px] leading-5 text-muted-foreground">{selected.law}</p>
              </div>
              <Badge variant="outline" className="rounded-sm font-mono text-[9px]">{result ? 'EXECUTED IN BROWSER' : 'READY'}</Badge>
            </div>
          </div>

          {!result && (
            <div className="mt-4 grid min-h-64 place-items-center border border-dashed border-border bg-muted/10 p-8 text-center">
              <div className="max-w-lg">
                <GitCompareArrows className="mx-auto size-8 text-primary" />
                <p className="mt-3 text-sm font-medium">Run the selected case</p>
                <p className="mt-2 text-[11px] leading-6 text-muted-foreground">
                  The browser will invoke the packaged Python apprenticeship runtime, generate content-derived receipts, and return the exact candidate, gate, semantic, and authority evidence.
                </p>
              </div>
            </div>
          )}

          {result && isAttack && (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <article className={`border p-3 ${statusTone(result.candidate_status)}`}>
                  <p className="eyebrow">Candidate state</p>
                  <p className="mt-2 font-mono text-xs">{result.candidate_status ?? '—'}</p>
                </article>
                <article className={`border p-3 ${result.active_count === 0 ? 'border-emerald-400/30 bg-emerald-400/5 text-emerald-100' : 'border-rose-400/30 bg-rose-400/5 text-rose-100'}`}>
                  <p className="eyebrow">Active grammar writes</p>
                  <p className="mt-2 font-mono text-xl">{result.active_count ?? '—'}</p>
                </article>
                <article className={`border p-3 ${result.active_digest_before === result.active_digest_after_submission ? 'border-emerald-400/30 bg-emerald-400/5 text-emerald-100' : 'border-rose-400/30 bg-rose-400/5 text-rose-100'}`}>
                  <p className="eyebrow">Active digest</p>
                  <p className="mt-2 font-mono text-xs">{result.active_digest_before === result.active_digest_after_submission ? 'UNCHANGED' : 'CHANGED'}</p>
                </article>
              </div>
              <div className="border border-emerald-400/30 bg-emerald-400/5 p-4">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-300" />
                  <div>
                    <p className="text-sm font-semibold text-emerald-100">Teacher commitment was blocked</p>
                    <p className="mt-1 text-[11px] leading-6 text-emerald-100/70">The lesson exists only as a content-addressed candidate. Native parsing remains unsupported until independent receipts and a separate promotion action exist.</p>
                  </div>
                </div>
              </div>
              <JsonBlock value={result} className="max-h-[520px]" />
            </div>
          )}

          {result && !isAttack && (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 sm:grid-cols-4">
                {[
                  ['TEACHER WRITES', String(result.active_count_after_teacher_submission ?? '—')],
                  ['QUALIFICATION', result.qualification_receipt?.passed ? 'PASS' : 'FAIL'],
                  ['KERNEL INTEGRATED', authorityBoundary.kernel_integrated === true ? 'YES' : 'NO'],
                  ['STORE DIGEST', shortHash(result.store_snapshot_digest)],
                ].map(([label, value]) => (
                  <article key={label} className="border border-border bg-card/60 p-3">
                    <p className="font-mono text-[8px] text-muted-foreground">{label}</p>
                    <p className="mt-1.5 break-all font-mono text-xs text-primary">{value}</p>
                  </article>
                ))}
              </div>

              <section className="border border-border bg-card/55 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="eyebrow">Semantic fault injection</p>
                    <p className="mt-1 text-[11px] leading-5 text-muted-foreground">These are frames from the bounded apprenticeship runtime, not a claim of full CAS-Sem integration.</p>
                  </div>
                  <GitCompareArrows className="size-5 text-primary" />
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  {caseId === 'passive_voice' ? (
                    <>
                      <SemanticCard label="ACTIVE CORE" value={semanticLaw.active} />
                      <SemanticCard label="PASSIVE CORE" value={semanticLaw.passive} />
                      <SemanticCard label="ROLE-REVERSED CORE" value={semanticLaw.role_reversed} />
                    </>
                  ) : (
                    <>
                      <SemanticCard label="POSITIVE CORE" value={semanticLaw.positive} />
                      <SemanticCard label="NEGATED CORE" value={semanticLaw.negative} />
                      <SemanticCard label="SEMANTIC LAW" value={{ same_predicate: semanticLaw.same_predicate, polarity_remains_different: semanticLaw.polarity_remains_different }} />
                    </>
                  )}
                </div>
              </section>

              <section className="border border-border bg-card/55 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="eyebrow">Acceptance ladder</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">Every green gate is local candidate evidence—not CNCM kernel promotion authority.</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="rounded-none"
                      onClick={() => setRevealedGates((count) => Math.min(gates.length, Math.max(1, count + 1)))}
                      disabled={revealedGates >= gates.length}
                    >
                      <StepForward data-icon="inline-start" /> Step gate
                    </Button>
                    <Badge variant="outline" className="rounded-sm font-mono text-[9px]">{visibleGates.length}/{gates.length}</Badge>
                  </div>
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {visibleGates.map((gate, index) => (
                    <article key={`${gate.gate}-${index}`} className={`flex items-start gap-3 border p-3 ${gate.passed ? 'border-emerald-400/25 bg-emerald-400/5' : 'border-rose-400/25 bg-rose-400/5'}`}>
                      <span className="grid size-6 shrink-0 place-items-center border border-border font-mono text-[9px] text-muted-foreground">{index + 1}</span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          {gate.passed ? <CheckCircle2 className="size-3.5 text-emerald-300" /> : <XCircle className="size-3.5 text-rose-300" />}
                          <code className="break-all text-[9px]">{gate.gate}</code>
                        </div>
                        <p className="mt-1.5 text-[10px] leading-5 text-muted-foreground">{gate.details?.join(' · ')}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="grid gap-3 lg:grid-cols-2">
                <article className="border border-primary/25 bg-primary/5 p-4">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="mt-0.5 size-5 shrink-0 text-primary" />
                    <div>
                      <p className="text-sm font-semibold">Local evidence chain</p>
                      <p className="mt-1 text-[10px] leading-5 text-muted-foreground">Qualification and delayed-retention receipts are bound to the candidate, examiner, fixture suite, and independent seeds.</p>
                      <p className="mt-2 font-mono text-[9px] text-primary">{shortHash(result.qualification_receipt?.suite_digest)}</p>
                    </div>
                  </div>
                </article>
                <article className="border border-amber-400/30 bg-amber-400/5 p-4">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-300" />
                    <div>
                      <p className="text-sm font-semibold text-amber-100">Kernel authority remains absent</p>
                      <p className="mt-1 text-[10px] leading-5 text-amber-100/70">The active result belongs only to the isolated language laboratory. It did not write MachineState, CAS-GEM, or the protected CAS-RRK workstream.</p>
                      <p className="mt-2 font-mono text-[9px] text-amber-200">CNCM STATE WRITES: 0 · CAS-RRK RECEIPT: NONE</p>
                    </div>
                  </div>
                </article>
              </section>

              <details className="border border-border bg-card/55">
                <summary className="cursor-pointer px-4 py-3 font-mono text-[9px] uppercase tracking-[0.13em] text-muted-foreground hover:text-foreground">Raw qualification bundle</summary>
                <JsonBlock value={result} className="max-h-[650px] border-x-0 border-b-0" />
              </details>
            </div>
          )}
        </div>
      </div>

      <footer className="grid gap-px border-t border-border bg-border sm:grid-cols-3">
        {[
          ['TEACHER AUTHORITY', 'PROPOSAL ONLY'],
          ['CNCM KERNEL WRITES', '0'],
          ['R1 PROMOTION', 'NOT INTEGRATED'],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3 bg-card px-4 py-3">
            <span className="font-mono text-[8px] text-muted-foreground">{label}</span>
            <span className="flex items-center gap-1.5 font-mono text-[9px] text-amber-200"><CircleDot className="size-3" />{value}</span>
          </div>
        ))}
      </footer>
    </section>
  );
}
