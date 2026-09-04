'use client';

import { useMemo, useState } from 'react';
import type { RefObject } from 'react';
import {
  Activity,
  Braces,
  CheckCircle2,
  CircleDot,
  GitCompareArrows,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CncmClient } from '@/lib/cncm-client';

type DemoCase =
  | 'exact_reasoning_math'
  | 'tool_use_procedure'
  | 'source_grounded_changing_fact'
  | 'protected_authority_rejection';

type TeacherSource = 'local_contract_demo' | 'aws_20b';

interface CognitiveApprenticeshipPanelProps {
  clientRef: RefObject<CncmClient | null>;
  runtimeReady: boolean;
  onNotice: (message: string) => void;
}

interface CognitiveApprenticeshipResult {
  case_id?: DemoCase;
  honest_outcome?: string;
  domain?: string;
  teacher_roles?: string[];
  transfer_channel?: string;
  proposal?: Record<string, unknown>;
  prerequisite_check?: Record<string, unknown>;
  cas_sdg_expansion?: Record<string, unknown>;
  qualification_receipt?: Record<string, unknown>;
  retention_receipt?: Record<string, unknown>;
  local_version?: Record<string, unknown>;
  teaching_episode?: Record<string, unknown>;
  cas_ohm_observation?: Record<string, unknown>;
  store_snapshot_digest?: string;
  state_scope?: string;
  authority_boundary?: Record<string, unknown>;
}

const CASES: Array<{
  id: DemoCase;
  label: string;
  eyebrow: string;
  description: string;
  verifier: string;
}> = [
  {
    id: 'exact_reasoning_math',
    label: 'Exact reasoning + math',
    eyebrow: 'CHECKABLE STRATEGY',
    description: 'A demonstrator proposes a reusable solving procedure; an exact examiner grades its steps and held-out transfer.',
    verifier: 'Exact arithmetic and strategy-step checker',
  },
  {
    id: 'tool_use_procedure',
    label: 'Tool-use procedure',
    eyebrow: 'PROCEDURAL INDUCTION',
    description: 'Qualify the recognize → intend → permit → execute → validate → resume pattern without performing an external action.',
    verifier: 'Frozen procedure-contract and permission-boundary checker',
  },
  {
    id: 'source_grounded_changing_fact',
    label: 'Changing world fact',
    eyebrow: 'SOURCE + VALIDITY REQUIRED',
    description: 'Qualify a fixed demonstration snapshot only inside its declared source and validity window; no live retrieval or native fact write occurs.',
    verifier: 'Source, date, validity-window, and contradiction custody',
  },
  {
    id: 'protected_authority_rejection',
    label: 'Protected authority attack',
    eyebrow: 'CONSTITUTIONAL FIREWALL',
    description: 'Attempt to teach a protected authority mutation and prove that autonomous promotion is structurally unavailable.',
    verifier: 'Protected-category rejection before promotion',
  },
];

const DOMAINS = [
  'Human language',
  'World knowledge',
  'Reasoning strategies',
  'Mathematics',
  'Programming',
  'Tool use',
  'Research methods',
  'Memory methods',
  'Metacognition',
  'Social dialogue',
  'Creativity',
  'Board design',
  'Self-diagnosis',
  'Multimodal grounding',
];

const CHANNELS = [
  ['SYMBOLIC', 'Facts, definitions, grammar, contracts, proof methods'],
  ['DEMONSTRATION', 'Procedures, debugging, planning, dialogue, research'],
  ['NEURAL', 'Replaceable fuzzy proposal generators only'],
  ['RETRIEVAL', 'Source-linked corpora and changing knowledge'],
  ['SYNTHETIC', 'Rare failures, counterexamples, adversarial cases'],
];

const FACULTY = ['Lecturer', 'Demonstrator', 'Socratic tutor', 'Curriculum designer', 'Adversary', 'Critic', 'Research mentor'];

function domainEvidence(domain: string) {
  if (domain === 'Human language') return 'EXISTING LOCAL SLICE';
  if (domain === 'Mathematics') return 'EXECUTABLE DEMO';
  if (domain === 'Tool use') return 'PROCEDURE DEMO';
  if (domain === 'World knowledge') return 'SOURCE-LINKED DEMO';
  return 'TYPED ONLY';
}

function shortHash(value?: string) {
  if (!value) return '—';
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

function displayValue(value: unknown, fallback = '—') {
  if (value === null || value === undefined) return fallback;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value);
  }
  return JSON.stringify(value) ?? fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function JsonBlock({ value, className = '' }: { value: unknown; className?: string }) {
  return (
    <pre className={`overflow-auto border border-border bg-[#050b0e] p-3 font-mono text-[10px] leading-5 text-cyan-50 ${className}`}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function CognitiveApprenticeshipPanel({
  clientRef,
  runtimeReady,
  onNotice,
}: CognitiveApprenticeshipPanelProps) {
  const [caseId, setCaseId] = useState<DemoCase>('exact_reasoning_math');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CognitiveApprenticeshipResult | null>(null);
  const [teacherSource, setTeacherSource] = useState<TeacherSource>('local_contract_demo');
  const selected = useMemo(() => CASES.find((item) => item.id === caseId) ?? CASES[0], [caseId]);

  const qualification = asRecord(result?.qualification_receipt);
  const gates = asRecords(qualification.gates);
  const authority = asRecord(result?.authority_boundary);
  const ohm = asRecord(result?.cas_ohm_observation);
  const expectedClosed = caseId === 'protected_authority_rejection';

  const runLesson = async () => {
    if (!clientRef.current || !runtimeReady) return;
    if (teacherSource === 'aws_20b') {
      onNotice('AWS 20B teacher is reserved but not connected. It needs a server-side Bedrock adapter, region, model ID, and credentials before it may propose lessons.');
      return;
    }
    setBusy(true);
    setResult(null);
    onNotice(`Running the browser-local CCB-T1 ${selected.label.toLowerCase()} lesson…`);
    try {
      const reply = await clientRef.current.cognitiveApprenticeshipQualify(caseId);
      if (!reply.ok || !reply.cognitive_apprenticeship) {
        throw new Error(reply.error?.message ?? 'Cognitive apprenticeship qualification failed closed.');
      }
      setResult(reply.cognitive_apprenticeship as CognitiveApprenticeshipResult);
      onNotice(
        expectedClosed
          ? 'CCB-T1 rejected the protected lesson and preserved the required fail-closed boundary.'
          : 'CCB-T1 completed local qualification. Inspect the transfer, retention, and authority evidence.',
      );
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setResult(null);
    onNotice('CCB-T1 bench reset. No CNCM kernel, durable memory, or protected state was changed.');
  };

  return (
    <section className="border border-border bg-card/75">
      <header className="border-b border-border p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="rounded-sm border-violet-400/35 bg-violet-400/5 font-mono text-[9px] text-violet-200">CCB-T1</Badge>
              <Badge variant="outline" className="rounded-sm border-cyan-400/35 bg-cyan-400/5 font-mono text-[9px] text-cyan-200">LOCAL CONTRACT + RUNTIME DEMO</Badge>
              <Badge variant="outline" className="rounded-sm border-rose-400/35 bg-rose-400/5 font-mono text-[9px] text-rose-200">NOT KERNEL-INTEGRATED</Badge>
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-tight text-foreground">Cognitive Apprenticeship Faculty</h2>
            <p className="mt-2 text-xs leading-6 text-muted-foreground">
              A larger model may lecture, demonstrate, challenge, and propose repairs. This board admits only lessons that survive independent prerequisites, counterexamples, held-out transfer, regression, replay, provenance, and retention.
            </p>
          </div>
          <div className="border border-primary/25 bg-primary/5 px-3 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-primary">
            Faculty, not oracle · proposal, not commitment
          </div>
        </div>
      </header>

      <div className="grid gap-px bg-border xl:grid-cols-[310px_minmax(0,1fr)]">
        <aside className="bg-card p-3">
          <p className="eyebrow px-1">Teaching cases</p>
          <div className="mt-2 space-y-2">
            {CASES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setCaseId(item.id);
                  setResult(null);
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
            <p className="eyebrow px-1">Teacher source</p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setTeacherSource('local_contract_demo');
                  onNotice('Local deterministic teaching packets selected. No live teacher model is running.');
                }}
                aria-pressed={teacherSource === 'local_contract_demo'}
                className={`border px-2 py-2 font-mono text-[8px] leading-4 ${teacherSource === 'local_contract_demo' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground'}`}
              >
                LOCAL DEMO
              </button>
              <button
                type="button"
                onClick={() => {
                  setTeacherSource('aws_20b');
                  setResult(null);
                  onNotice('AWS 20B teacher selected but not connected. Secrets must stay server-side; the browser will not accept AWS credentials.');
                }}
                aria-pressed={teacherSource === 'aws_20b'}
                className={`border px-2 py-2 font-mono text-[8px] leading-4 ${teacherSource === 'aws_20b' ? 'border-amber-400/40 bg-amber-400/10 text-amber-200' : 'border-border text-muted-foreground'}`}
              >
                AWS 20B
              </button>
            </div>
            {teacherSource === 'aws_20b' && (
              <div className="border border-amber-400/30 bg-amber-400/5 p-3">
                <p className="font-mono text-[8px] text-amber-200">SETUP REQUIRED · OFF</p>
                <p className="mt-1 text-[9px] leading-4 text-amber-100/70">Future AWS Bedrock teacher only. Region, exact model ID, server adapter, budget limit, and credentials are not configured.</p>
              </div>
            )}
            <Button type="button" className="w-full rounded-none" onClick={() => void runLesson()} disabled={!runtimeReady || busy}>
              {busy ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <Play data-icon="inline-start" />}
              {teacherSource === 'aws_20b' ? 'AWS setup required' : 'Run local lesson'}
            </Button>
            <Button type="button" variant="outline" className="w-full rounded-none" onClick={reset} disabled={busy}>
              <RotateCcw data-icon="inline-start" /> Reset bench
            </Button>
          </div>
        </aside>

        <div className="min-w-0 bg-background/40 p-4 sm:p-5">
          <div className="grid gap-3 md:grid-cols-4">
            {[
              ['PROPOSER', 'Typed candidate', 'No write authority'],
              ['CAS-SDG', 'Local expansion analogue', 'No live adapter'],
              ['EXAMINER', 'Identity-separated fixtures', 'Not externally custodied'],
              ['CAS-RRK', 'Promotion boundary', 'Absent from this local lab'],
            ].map(([label, title, detail]) => (
              <article key={label} className="border border-border bg-card/60 p-3">
                <p className="font-mono text-[8px] tracking-[0.15em] text-primary">{label}</p>
                <p className="mt-1.5 text-xs font-medium">{title}</p>
                <p className="mt-1 text-[10px] leading-5 text-muted-foreground">{detail}</p>
              </article>
            ))}
          </div>

          <section className="mt-4 border border-border bg-card/55 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="eyebrow">Selected qualification</p>
                <h3 className="mt-1.5 text-base font-semibold">{selected.label}</h3>
                <p className="mt-1 text-[11px] leading-5 text-muted-foreground">Examiner: {selected.verifier}</p>
              </div>
              <Badge variant="outline" className="rounded-sm font-mono text-[9px]">{result ? 'EXECUTED IN BROWSER' : 'READY'}</Badge>
            </div>
          </section>

          {!result && (
            <div className="mt-4 grid min-h-64 place-items-center border border-dashed border-border bg-muted/10 p-8 text-center">
              <div className="max-w-xl">
                <GitCompareArrows className="mx-auto size-8 text-primary" />
                <p className="mt-3 text-sm font-medium">Run the selected teaching episode</p>
                <p className="mt-2 text-[11px] leading-6 text-muted-foreground">
                  The packaged Python runtime will produce the proposal, prerequisite decision, local identity-separated curriculum expansion, qualification receipt, TeachingEpisode, CAS-Ohm-shaped observation, and explicit authority boundary. No live teacher or CAS-SDG service is connected.
                </p>
              </div>
            </div>
          )}

          {result && (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ['OUTCOME', result.honest_outcome ?? '—'],
                  ['DOMAIN', result.domain ?? '—'],
                  ['CHANNEL', result.transfer_channel ?? '—'],
                  ['KERNEL WRITES', displayValue(authority.cncm_state_writes, '0')],
                  ['STORE DIGEST', shortHash(result.store_snapshot_digest)],
                ].map(([label, value]) => (
                  <article key={label} className="border border-border bg-card/60 p-3">
                    <p className="font-mono text-[8px] text-muted-foreground">{label}</p>
                    <p className="mt-1.5 break-words font-mono text-[10px] text-primary">{value}</p>
                  </article>
                ))}
              </div>

              <div className={`border p-4 ${expectedClosed ? 'border-emerald-400/30 bg-emerald-400/5' : 'border-primary/25 bg-primary/5'}`}>
                <div className="flex items-start gap-3">
                  {expectedClosed ? <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-300" /> : <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-primary" />}
                  <div>
                    <p className="text-sm font-semibold">{expectedClosed ? 'Correct refusal is the passing result' : 'Local qualification evidence produced'}</p>
                    <p className="mt-1 text-[11px] leading-6 text-muted-foreground">
                      {expectedClosed
                        ? 'A protected authority mutation must not become native structure merely because a teacher proposed it.'
                        : 'The lesson may enter only this isolated local store. It has no CNCM kernel, CAS-GEM, deployment, or CAS-RRK promotion authority.'}
                    </p>
                  </div>
                </div>
              </div>

              <section className="grid gap-3 lg:grid-cols-3">
                <article className="border border-border bg-card/55 p-4">
                  <p className="eyebrow">Teacher faculty</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(result.teacher_roles ?? []).map((role) => <Badge key={role} variant="outline" className="rounded-sm font-mono text-[8px]">{role}</Badge>)}
                  </div>
                  <JsonBlock value={result.proposal ?? {}} className="mt-3 max-h-52" />
                </article>
                <article className="border border-border bg-card/55 p-4">
                  <p className="eyebrow">Prerequisite + CAS-SDG</p>
                  <JsonBlock value={{ prerequisite_check: result.prerequisite_check, cas_sdg_expansion: result.cas_sdg_expansion }} className="mt-3 max-h-64" />
                </article>
                <article className="border border-border bg-card/55 p-4">
                  <div className="flex items-center gap-2">
                    <Activity className="size-4 text-primary" />
                    <p className="eyebrow">CAS-Ohm observation</p>
                  </div>
                  <p className="mt-2 text-[10px] leading-5 text-muted-foreground">Before/after learning-path evidence only. Flow cannot establish truth or authorize promotion.</p>
                  <JsonBlock value={ohm} className="mt-3 max-h-52" />
                </article>
              </section>

              <section className="border border-border bg-card/55 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="eyebrow">Acceptance evidence</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">Passing gates qualify local evidence; they do not create authority.</p>
                  </div>
                  <Badge variant="outline" className="rounded-sm font-mono text-[9px]">{gates.length} GATES</Badge>
                </div>
                {gates.length > 0 ? (
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {gates.map((gate, index) => {
                      const passed = gate.passed === true;
                      const name = displayValue(gate.gate ?? gate.stage ?? gate.name, `GATE_${index + 1}`);
                      return (
                        <article key={`${name}-${index}`} className={`flex items-start gap-3 border p-3 ${passed ? 'border-emerald-400/25 bg-emerald-400/5' : 'border-amber-400/25 bg-amber-400/5'}`}>
                          {passed ? <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-emerald-300" /> : <XCircle className="mt-0.5 size-3.5 shrink-0 text-amber-300" />}
                          <div className="min-w-0">
                            <code className="break-all text-[9px]">{name}</code>
                            <p className="mt-1 text-[9px] leading-4 text-muted-foreground">{displayValue(gate.details ?? gate.reason, passed ? 'passed' : 'not passed')}</p>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <JsonBlock value={qualification} className="mt-3 max-h-72" />
                )}
              </section>

              <section className="grid gap-3 lg:grid-cols-2">
                <article className="border border-primary/25 bg-primary/5 p-4">
                  <div className="flex items-start gap-3">
                    <Braces className="mt-0.5 size-5 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold">TeachingEpisode</p>
                      <p className="mt-1 text-[10px] leading-5 text-muted-foreground">Inspectable lesson, evidence, accepted scope, exceptions, capability change, provenance, version, and rollback pointer.</p>
                      <JsonBlock value={result.teaching_episode ?? {}} className="mt-3 max-h-72" />
                    </div>
                  </div>
                </article>
                <article className="border border-amber-400/30 bg-amber-400/5 p-4">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-300" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-amber-100">Authority remains outside the faculty</p>
                      <p className="mt-1 text-[10px] leading-5 text-amber-100/70">Protected tests, proof checkers, rollback machinery, deployment permissions, constitutional values, and the definition of improvement cannot be autonomously taught into force.</p>
                      <JsonBlock value={authority} className="mt-3 max-h-72" />
                    </div>
                  </div>
                </article>
              </section>

              <details className="border border-border bg-card/55">
                <summary className="cursor-pointer px-4 py-3 font-mono text-[9px] uppercase tracking-[0.13em] text-muted-foreground hover:text-foreground">Raw CCB-T1 result</summary>
                <JsonBlock value={result} className="max-h-[680px] border-x-0 border-b-0" />
              </details>
            </div>
          )}
        </div>
      </div>

      <section className="grid gap-px border-t border-border bg-border xl:grid-cols-[1.2fr_1fr]">
        <div className="bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Teaching domain atlas</p>
              <p className="mt-1 text-[10px] leading-5 text-muted-foreground">Four bounded demonstrations are executable. Every other domain is a typed curriculum destination—not a capability claim.</p>
            </div>
            <Badge variant="outline" className="rounded-sm font-mono text-[8px]">14 DOMAINS</Badge>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {DOMAINS.map((domain) => (
              <div key={domain} className="flex items-center justify-between gap-3 border border-border bg-muted/10 px-3 py-2">
                <span className="text-[10px]">{domain}</span>
                <span className="font-mono text-[7px] text-muted-foreground">{domainEvidence(domain)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="grid gap-px bg-border sm:grid-cols-2">
          <div className="bg-card p-4">
            <p className="eyebrow">Five transfer channels</p>
            <div className="mt-3 space-y-2">
              {CHANNELS.map(([label, detail]) => (
                <div key={label} className="border-l-2 border-primary/40 pl-3">
                  <p className="font-mono text-[8px] text-primary">{label}</p>
                  <p className="mt-0.5 text-[9px] leading-4 text-muted-foreground">{detail}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-card p-4">
            <p className="eyebrow">Seven faculty roles</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {FACULTY.map((role) => <Badge key={role} variant="outline" className="rounded-sm font-mono text-[8px]">{role}</Badge>)}
            </div>
            <div className="mt-4 border border-border bg-muted/10 p-3">
              <p className="font-mono text-[8px] text-primary">SEPARATION LAW</p>
              <p className="mt-1 text-[9px] leading-5 text-muted-foreground">A proposer may not count its own criticism, examples, or grading as independent promotion evidence.</p>
            </div>
          </div>
        </div>
      </section>

      <footer className="grid gap-px border-t border-border bg-border sm:grid-cols-2 xl:grid-cols-5">
        {[
          ['LIVE TEACHERS', '0'],
          ['TEACHER AUTHORITY', 'PROPOSAL ONLY'],
          ['CNCM KERNEL WRITES', '0'],
          ['CAS-RRK COMMITS', '0'],
          ['CURRENT SCOPE', 'LOCAL CCB-T1 LAB'],
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
