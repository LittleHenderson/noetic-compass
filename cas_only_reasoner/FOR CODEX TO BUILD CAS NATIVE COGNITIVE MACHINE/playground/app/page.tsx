'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  Braces,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clipboard,
  Cpu,
  Database,
  Download,
  FileCheck2,
  GitBranch,
  History,
  Info,
  LoaderCircle,
  MemoryStick,
  MessageCircle,
  Play,
  RefreshCcw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  SquareTerminal,
  Sigma,
  TriangleAlert,
  XCircle,
} from 'lucide-react';

import { ChatPanel } from '@/app/chat-panel';
import { CasOhmPanel } from '@/app/cas-ohm-panel';
import { CognitiveApprenticeshipPanel } from '@/app/cognitive-apprenticeship-panel';
import { LanguageApprenticeshipPanel } from '@/app/language-apprenticeship-panel';
import { MathPanel } from '@/app/math-panel';
import { ReceiptPanel } from '@/app/receipt-panel';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  BridgeReply,
  CncmClient,
  MemorySummary,
  RuntimeReady,
} from '@/lib/cncm-client';

type TabId = 'outcome' | 'proof' | 'branches' | 'rpm' | 'trace' | 'evidence' | 'raw';
type SurfaceMode = 'chat' | 'language' | 'faculty' | 'math' | 'attention' | 'lab' | 'receipt';

interface FixtureInfo {
  id: string;
  title: string;
  category: string;
  description: string;
  expected: string;
}

interface Proposition {
  predicate?: string;
  arguments?: unknown[];
  polarity?: boolean;
  evidence_status?: string;
  scope?: string;
}

interface RunSummary {
  run_id?: string;
  problem_id?: string;
  terminal_status?: string;
  conclusion?: Proposition | null;
  logical_ticks?: number;
  final_state_hash?: string;
  trace_head?: string;
  trace_digest?: string;
  evidence_digest?: string;
}

interface TraceIntent {
  intent_id?: string;
  intent_type?: string;
  issuer_subsystem?: string;
  branch_id?: string | null;
  target_scope?: string;
  required_capability?: string;
  proposed_mutation?: unknown;
}

interface TraceEvent {
  event_id?: string;
  event_hash?: string;
  previous_event_hash?: string;
  logical_tick?: number;
  enabled_components?: string[];
  scheduled_components?: string[];
  proposed_intents?: TraceIntent[];
  authorized_intent_ids?: string[];
  rejected_intents?: unknown[];
  committed_mutations?: string[];
  sealed?: boolean;
  terminal_status?: string;
  pre_state_hash?: string;
  post_state_hash?: string;
}

interface ProofStep {
  step_id?: string;
  branch_id?: string;
  operation?: string;
  rule_id?: string;
  premise_keys?: string[];
  conclusion?: Proposition;
  verified?: boolean;
}

interface BranchSummary {
  branch_id?: string;
  candidate_id?: string;
  status?: string;
  assumptions?: string[];
  contradictions?: string[];
  unknowns?: string[];
  proposition_keys?: string[];
  proof_step_ids?: string[];
}

interface ComparisonReport {
  report_id?: string;
  winner_branch_id?: string;
  ordered_branch_ids?: string[];
  shared_features?: string[];
  differences?: string[];
  evaluation_frame_hash?: string;
}

interface RpmSummary {
  event_count?: number;
  final_depth?: number;
  events?: unknown[];
}

interface VerificationReport {
  valid?: boolean;
  failures?: unknown[];
  checks?: Record<string, boolean>;
}

interface EvidencePacket {
  terminal_status?: string;
  event_count?: number;
  evidence_digest?: string;
  final_state_hash?: string;
  trace_digest?: string;
  trace_head?: string;
  problem_packet_hash?: string;
  query_result?: {
    supported?: boolean;
    conclusion?: Proposition | null;
    query?: Proposition;
    lacunae?: string[];
  };
  proof_steps?: ProofStep[];
  branch_summary?: BranchSummary[];
  comparison?: ComparisonReport[];
  rpm_summary?: RpmSummary;
  commitment_gates?: Record<string, boolean>;
  claim_boundary?: Record<string, unknown>;
  diagnostics?: string[];
  learning_disposition?: string;
}

interface RunBundle {
  summary?: RunSummary;
  final_state?: Record<string, unknown>;
  trace?: TraceEvent[];
  evidence?: EvidencePacket;
}

interface RuntimeState {
  phase: 'loading' | 'ready' | 'error';
  runtimeVersion?: string;
  bridgeVersion?: string;
  runtimeSha256?: string;
  packageTreeSha256?: string;
  sourceSpecSha256?: string;
  pyodideVersion?: string;
  conversationProtocolVersion?: string;
  capabilities?: string[];
  error?: string;
}

const FIXTURES: FixtureInfo[] = [
  {
    id: 'deduction',
    title: 'Deduction',
    category: 'proof',
    description: 'Derive Q from asserted P and the rule P → Q.',
    expected: 'CONCLUDED',
  },
  {
    id: 'transitive_reasoning',
    title: 'Transitive reasoning',
    category: 'proof',
    description: 'Apply the declared transitive predicate contract.',
    expected: 'CONCLUDED',
  },
  {
    id: 'branch_rollback',
    title: 'Branch rollback',
    category: 'branches',
    description: 'Compare two declared candidates and discard the blocked path.',
    expected: 'CONCLUDED',
  },
  {
    id: 'rpm_recursion',
    title: 'RPM success',
    category: 'prerequisite',
    description: 'Push a declared prerequisite, resolve it, and return to the parent.',
    expected: 'CONCLUDED',
  },
  {
    id: 'rpm_failure',
    title: 'RPM failure',
    category: 'prerequisite',
    description: 'Fail closed when a declared prerequisite cannot be resolved.',
    expected: 'NEEDS_INFORMATION',
  },
  {
    id: 'contradiction',
    title: 'Contradiction',
    category: 'conflict',
    description: 'Surface incompatible authoritative propositions explicitly.',
    expected: 'CONFLICT_UNRESOLVED',
  },
  {
    id: 'missing_information',
    title: 'Missing information',
    category: 'lacuna',
    description: 'Stop with a typed information gap instead of guessing.',
    expected: 'NEEDS_INFORMATION',
  },
  {
    id: 'memory_recall',
    title: 'Exact memory recall',
    category: 'memory',
    description: 'Cold: needs information. Warm: run Deduction first, then retry.',
    expected: 'COLD → NEEDS_INFORMATION',
  },
];

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'outcome', label: 'Outcome' },
  { id: 'proof', label: 'Proof' },
  { id: 'branches', label: 'Branches' },
  { id: 'rpm', label: 'Prerequisites' },
  { id: 'trace', label: 'Trace' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'raw', label: 'Raw bundle' },
];

const EMPTY_MEMORY: MemorySummary = { episode_count: 0, episode_ids: [] };

function formatProposition(value?: Proposition | null) {
  if (!value?.predicate) return 'No conclusion committed';
  const argumentsText = (value.arguments ?? []).map(String).join(', ');
  const sign = value.polarity === false ? '¬' : '';
  return `${sign}${value.predicate}(${argumentsText})`;
}

function statusCopy(status?: string) {
  switch (status) {
    case 'CONCLUDED':
      return { title: 'Conclusion proved within the declared packet', detail: 'The commitment gates passed and a packet-bound conclusion was written.', tone: 'success' };
    case 'NEEDS_INFORMATION':
      return { title: 'More information needed', detail: 'The machine stopped at an explicit lacuna instead of guessing.', tone: 'warning' };
    case 'CONFLICT_UNRESOLVED':
      return { title: 'Conflicting facts', detail: 'The machine detected incompatible authoritative propositions.', tone: 'danger' };
    case 'BUDGET_EXHAUSTED':
      return { title: 'Budget exhausted', detail: 'A declared reasoning limit stopped this run.', tone: 'warning' };
    default:
      return { title: status ? 'Run stopped' : 'Ready for a run', detail: status ?? 'Choose a fixture or edit the JSON packet.', tone: 'neutral' };
  }
}

function toneClasses(tone: string) {
  if (tone === 'success') return 'border-emerald-400/35 bg-emerald-400/8 text-emerald-100';
  if (tone === 'warning') return 'border-amber-400/35 bg-amber-400/8 text-amber-100';
  if (tone === 'danger') return 'border-rose-400/35 bg-rose-400/8 text-rose-100';
  return 'border-border bg-muted/20 text-foreground';
}

function shortHash(value?: string) {
  if (!value) return '—';
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

function JsonBlock({ value, className = '' }: { value: unknown; className?: string }) {
  return (
    <pre className={`overflow-auto border border-border bg-[#050b0e] p-3 font-mono text-[10px] leading-5 text-cyan-50 ${className}`}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function HashRow({ label, value, onCopy }: { label: string; value?: string; onCopy: (value: string) => void }) {
  return (
    <div className="grid gap-1 border-b border-border/70 py-2 last:border-0 sm:grid-cols-[150px_1fr_auto] sm:items-center">
      <span className="eyebrow">{label}</span>
      <code className="min-w-0 break-all font-mono text-[10px] text-cyan-100">{value ?? '—'}</code>
      {value && (
        <button type="button" className="justify-self-start p-1 text-muted-foreground hover:text-primary" onClick={() => onCopy(value)} aria-label={`Copy ${label}`}>
          <Clipboard className="size-3.5" />
        </button>
      )}
    </div>
  );
}

export default function Home() {
  const clientRef = useRef<CncmClient | null>(null);
  const resultHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const [runtime, setRuntime] = useState<RuntimeState>({ phase: 'loading' });
  const [selectedFixture, setSelectedFixture] = useState('deduction');
  const [problemText, setProblemText] = useState('');
  const [fixtureBaseline, setFixtureBaseline] = useState('');
  const [fixtureLoading, setFixtureLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [reply, setReply] = useState<BridgeReply | null>(null);
  const [manualVerification, setManualVerification] = useState<VerificationReport | null>(null);
  const [replayResult, setReplayResult] = useState<boolean | null>(null);
  const [replayAvailable, setReplayAvailable] = useState(false);
  const [memory, setMemory] = useState<MemorySummary>(EMPTY_MEMORY);
  const [activeTab, setActiveTab] = useState<TabId>('outcome');
  const [surfaceMode, setSurfaceMode] = useState<SurfaceMode>('chat');
  const [traceIndex, setTraceIndex] = useState(0);
  const [notice, setNotice] = useState('Loading the pinned browser runtime…');
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    const client = new CncmClient((message) => {
      if (message.type === 'fatal') {
        setRuntime({ phase: 'error', error: message.error });
        setNotice(`Runtime failed closed: ${message.error}`);
        return;
      }
      const ready = message as RuntimeReady;
      setRuntime({
        phase: 'ready',
        runtimeVersion: ready.runtimeVersion,
        bridgeVersion: ready.bridgeVersion,
        runtimeSha256: ready.runtimeSha256,
        packageTreeSha256: ready.packageTreeSha256,
        sourceSpecSha256: ready.sourceSpecSha256,
        pyodideVersion: ready.pyodideVersion,
        conversationProtocolVersion: ready.conversationProtocolVersion,
        capabilities: ready.capabilities,
      });
      setMemory(ready.memory);
      setNotice('Exact CNCM-RRK runtime ready in this browser.');
    });
    clientRef.current = client;
    return () => {
      client.dispose();
      clientRef.current = null;
    };
  }, []);

  const loadFixture = useCallback(async (fixtureId: string) => {
    setSelectedFixture(fixtureId);
    setFixtureLoading(true);
    setNotice(`Loading ${fixtureId}…`);
    try {
      const response = await fetch(`/fixtures/${fixtureId}.json`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`fixture fetch failed: HTTP ${response.status}`);
      const text = await response.text();
      JSON.parse(text);
      setProblemText(text.trim());
      setFixtureBaseline(text.trim());
      setReply(null);
      setManualVerification(null);
      setReplayResult(null);
      setReplayAvailable(false);
      setTraceIndex(0);
      setActiveTab('outcome');
      setNotice(`${fixtureId} loaded. Edit the packet or run it unchanged.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setFixtureLoading(false);
    }
  }, []);

  useEffect(() => {
    const task = queueMicrotask(() => void loadFixture('deduction'));
    return () => task;
  }, [loadFixture]);

  const bundle = reply?.result as RunBundle | undefined;
  const summary = bundle?.summary;
  const evidence = bundle?.evidence;
  const trace = bundle?.trace ?? [];
  const status = summary?.terminal_status ?? evidence?.terminal_status;
  const outcome = statusCopy(status);
  const traceEvent = trace[Math.min(traceIndex, Math.max(trace.length - 1, 0))];
  const verification = reply?.verification as VerificationReport | undefined;
  const totalRejected = trace.reduce(
    (count, event) => count + (event.rejected_intents?.length ?? 0),
    0,
  );
  const totalAuthorized = trace.reduce(
    (count, event) => count + (event.authorized_intent_ids?.length ?? 0),
    0,
  );

  const updateMemory = (nextReply: BridgeReply) => {
    if (nextReply.memory) setMemory(nextReply.memory);
  };

  const runMachine = async () => {
    if (!clientRef.current || runtime.phase !== 'ready') return;
    setBusy('run');
    setNotice('Running the deterministic scheduler…');
    setManualVerification(null);
    setReplayResult(null);
    try {
      const nextReply = await clientRef.current.run(problemText);
      setReply(nextReply);
      updateMemory(nextReply);
      setReplayAvailable(Boolean(nextReply.result));
      setTraceIndex(0);
      setActiveTab('outcome');
      setNotice(nextReply.ok ? 'Run complete. The generated bundle passed its built-in verifier.' : nextReply.error?.message ?? 'Run failed closed.');
      requestAnimationFrame(() => resultHeadingRef.current?.focus());
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const validatePacket = async () => {
    if (!clientRef.current || runtime.phase !== 'ready') return;
    setBusy('validate');
    setNotice('Checking the problem contract…');
    try {
      const nextReply = await clientRef.current.validate(problemText);
      updateMemory(nextReply);
      const report = nextReply.report as VerificationReport | undefined;
      setNotice(report?.valid ? 'Problem packet is valid.' : nextReply.error?.message ?? 'Problem packet did not pass validation.');
      if (!nextReply.ok || !report?.valid) setReply(nextReply);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const verifyBundle = async () => {
    if (!clientRef.current || !bundle) return;
    setBusy('verify');
    setNotice('Rechecking every bundle invariant…');
    try {
      const verificationReply = await clientRef.current.verify(JSON.stringify(bundle));
      updateMemory(verificationReply);
      const report = verificationReply.report as VerificationReport | undefined;
      setManualVerification(report ?? null);
      setNotice(report?.valid ? 'Receipt verified: all hash and structure checks passed.' : 'Receipt verification failed closed.');
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const replayLast = async () => {
    if (!clientRef.current || !bundle) return;
    setBusy('replay');
    setNotice('Replaying from the run’s original episodic snapshot…');
    try {
      const replayReply = await clientRef.current.replay();
      updateMemory(replayReply);
      const matches = Boolean(replayReply.report?.matches);
      setReplayResult(matches);
      setNotice(matches ? 'Session replay matched final state, trace, and evidence.' : 'Replay diverged and failed closed.');
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const resetMemory = async () => {
    if (!clientRef.current || runtime.phase !== 'ready') return;
    setBusy('reset');
    setNotice('Creating a fresh CognitiveMachine…');
    try {
      const resetReply = await clientRef.current.reset();
      updateMemory(resetReply);
      setReplayResult(null);
      setReplayAvailable(false);
      setNotice('Session memory reset. Previous receipts remain visible but are no longer replayable.');
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const inspectRuntimeStatus = async () => {
    if (!clientRef.current || runtime.phase !== 'ready') return;
    setBusy('status');
    try {
      const statusReply = await clientRef.current.status();
      updateMemory(statusReply);
      if (!statusReply.ok) throw new Error(statusReply.error?.message ?? 'Runtime status failed closed');
      const turn = statusReply.conversation_state?.turn_index ?? 0;
      const episodes = statusReply.memory?.episode_count ?? 0;
      setNotice(`Live worker status: runtime ${statusReply.runtime_version ?? runtime.runtimeVersion}, conversation turn ${turn}, ${episodes} retained session episode${episodes === 1 ? '' : 's'}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  };

  const downloadJson = (value: unknown, suffix: string, label: string) => {
    if (value === undefined || value === null) return;
    const payload = new Blob([`${JSON.stringify(value, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(payload);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${summary?.problem_id ?? 'cncm-run'}-${suffix}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice(`${label} downloaded as JSON.`);
  };

  const downloadBundle = () => downloadJson(bundle, 'bundle', 'Evidence bundle');
  const downloadTrace = () => downloadJson(bundle?.trace, 'trace', 'Sealed trace');
  const downloadFinalState = () => downloadJson(bundle?.final_state, 'final-state', 'Final state');
  const downloadEvidence = () => downloadJson(bundle?.evidence, 'evidence', 'Evidence packet');

  const copyHash = async (value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(value);
    setTimeout(() => setCopied(null), 1200);
  };

  const loadConversationProblem = (problem: Record<string, unknown>) => {
    const text = JSON.stringify(problem, null, 2);
    setProblemText(text);
    setFixtureBaseline(text);
    setSelectedFixture('conversation_semantic_packet');
    setReply(null);
    setManualVerification(null);
    setReplayResult(null);
    setReplayAvailable(false);
    setTraceIndex(0);
    setActiveTab('outcome');
    setSurfaceMode('lab');
    setNotice('The exact conversation-generated semantic packet is open in Problem Lab. Run it directly to inspect the same CAS reasoning boundary.');
  };

  const runtimeReady = runtime.phase === 'ready';
  const controlsDisabled = !runtimeReady || fixtureLoading || busy !== null;

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border/80 bg-background/94 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-[1900px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center border border-primary/50 bg-primary/10 text-primary shadow-[0_0_30px_rgb(34_211_238/12%)]">
              <Cpu className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-primary">CAS / CNCM-RRK</p>
              <h1 className="text-sm font-semibold tracking-tight sm:text-base">Native Cognitive Machine Playground</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge variant="outline" className="rounded-sm border-primary/35 bg-primary/5 font-mono text-[9px] text-primary">REFERENCE DEMONSTRATOR · BOUNDED</Badge>
            <Badge variant="outline" className="rounded-sm border-border bg-card font-mono text-[9px] text-muted-foreground">CRQS: NOT RUN</Badge>
            <Badge
              variant="outline"
              className={`rounded-sm font-mono text-[9px] ${runtime.phase === 'ready' ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300' : runtime.phase === 'error' ? 'border-rose-400/40 bg-rose-400/10 text-rose-300' : 'border-amber-400/40 bg-amber-400/10 text-amber-300'}`}
            >
              {runtime.phase === 'loading' && <LoaderCircle className="mr-1 size-3 animate-spin" />}
              {runtime.phase === 'ready' ? `BOUNDED BROWSER RUNTIME ${runtime.runtimeVersion} READY` : runtime.phase === 'error' ? 'RUNTIME FAILED CLOSED' : 'LOADING BOUNDED RUNTIME'}
            </Badge>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-[1900px] px-4 py-4 sm:px-6 sm:py-6">
        <div className="mb-4 grid gap-px border border-border bg-border sm:grid-cols-2 xl:grid-cols-5">
          {[
            { label: 'RUNTIME', value: runtime.runtimeVersion ?? 'loading', icon: <Activity key="runtime" /> },
            { label: 'INTERFACES', value: 'chat + language + faculty + math + attention + packet + receipt', icon: <Braces key="fixtures" /> },
            { label: 'MEMORY', value: `${memory.episode_count} episode${memory.episode_count === 1 ? '' : 's'}`, icon: <MemoryStick key="memory" /> },
            { label: 'EVIDENCE', value: 'hash + structure', icon: <ShieldCheck key="evidence" /> },
            { label: 'AUTHORITY', value: 'no external actions', icon: <CircleDot key="authority" /> },
          ].map(({ label, value, icon }) => (
            <div key={label} className="flex items-center gap-3 bg-card/95 px-4 py-3">
              <span className="text-primary [&>svg]:size-4">{icon}</span>
              <div>
                <p className="font-mono text-[9px] tracking-[0.18em] text-muted-foreground">{label}</p>
                <p className="text-sm font-medium">{value}</p>
              </div>
            </div>
          ))}
        </div>

        <output className="mb-4 flex w-full items-start gap-3 border border-primary/25 bg-primary/5 px-4 py-3" aria-live="polite">
          {busy ? <LoaderCircle className="mt-0.5 size-4 shrink-0 animate-spin text-primary" /> : <SquareTerminal className="mt-0.5 size-4 shrink-0 text-primary" />}
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[10px] leading-5 text-cyan-50">{notice}</p>
            {runtime.phase === 'loading' && <p className="mt-1 text-[10px] text-muted-foreground">First load starts a browser-local Python/WebAssembly runtime and may take a few seconds.</p>}
          </div>
          {copied && <span className="hidden items-center gap-1 font-mono text-[9px] text-emerald-300 sm:flex"><Check className="size-3" /> COPIED</span>}
        </output>

        <nav className="mb-4 flex flex-wrap items-center justify-between gap-3 border border-border bg-card/75 p-2" aria-label="Playground mode">
          <div className="grid w-full grid-cols-2 gap-1 sm:flex sm:w-auto sm:flex-wrap">
            <button
              type="button"
              onClick={() => setSurfaceMode('chat')}
              aria-pressed={surfaceMode === 'chat'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'chat' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <MessageCircle className="size-3.5" /> Chat With This Mind
            </button>
            <button
              type="button"
              onClick={() => setSurfaceMode('math')}
              aria-pressed={surfaceMode === 'math'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'math' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <Sigma className="size-3.5" /> Exact Math
            </button>
            <button
              type="button"
              onClick={() => setSurfaceMode('language')}
              aria-pressed={surfaceMode === 'language'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'language' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <Cpu className="size-3.5" /> Language Apprenticeship
            </button>
            <button
              type="button"
              onClick={() => setSurfaceMode('faculty')}
              aria-pressed={surfaceMode === 'faculty'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'faculty' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <GitBranch className="size-3.5" /> Cognitive Faculty
            </button>
            <button
              type="button"
              onClick={() => setSurfaceMode('attention')}
              aria-pressed={surfaceMode === 'attention'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'attention' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <Activity className="size-3.5" /> CAS-Ohm Attention
            </button>
            <button
              type="button"
              onClick={() => setSurfaceMode('lab')}
              aria-pressed={surfaceMode === 'lab'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'lab' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <Braces className="size-3.5" /> Problem Lab
            </button>
            <button
              type="button"
              onClick={() => setSurfaceMode('receipt')}
              aria-pressed={surfaceMode === 'receipt'}
              className={`flex min-h-11 items-center justify-center gap-2 border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] sm:min-h-0 ${surfaceMode === 'receipt' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'}`}
            >
              <ShieldCheck className="size-3.5" /> Receipt Lab
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" className="rounded-none" onClick={() => void inspectRuntimeStatus()} disabled={!runtimeReady || busy !== null}>
              <Activity data-icon="inline-start" /> Live status
            </Button>
            <Badge variant="outline" className="rounded-sm border-primary/30 bg-primary/5 font-mono text-[9px] text-primary">LANGUAGE PROTOCOL {runtime.conversationProtocolVersion ?? '0.1'}</Badge>
            <Badge variant="outline" className="rounded-sm border-border bg-card font-mono text-[9px] text-muted-foreground">CONV: NOT QUALIFIED</Badge>
          </div>
        </nav>

        <div hidden={surfaceMode !== 'chat'}>
          <ChatPanel
            clientRef={clientRef}
            runtimeReady={runtimeReady}
            onNotice={setNotice}
            onMemoryChange={setMemory}
            onResetMind={resetMemory}
            onLoadProblem={loadConversationProblem}
          />
        </div>
        <div hidden={surfaceMode !== 'math'}>
          <MathPanel
            clientRef={clientRef}
            runtimeReady={runtimeReady}
            onNotice={setNotice}
          />
        </div>
        <div hidden={surfaceMode !== 'language'}>
          <LanguageApprenticeshipPanel
            clientRef={clientRef}
            runtimeReady={runtimeReady}
            onNotice={setNotice}
          />
        </div>
        <div hidden={surfaceMode !== 'faculty'}>
          <CognitiveApprenticeshipPanel
            clientRef={clientRef}
            runtimeReady={runtimeReady}
            onNotice={setNotice}
          />
        </div>
        <div hidden={surfaceMode !== 'attention'}>
          <CasOhmPanel active={surfaceMode === 'attention'} />
        </div>
        <div hidden={surfaceMode !== 'lab'}>
        <div className="grid gap-4 xl:grid-cols-[250px_minmax(380px,0.95fr)_minmax(380px,1.15fr)]">
          <aside className="h-fit border border-border bg-card/75 xl:sticky xl:top-24">
            <div className="border-b border-border px-4 py-3">
              <p className="eyebrow">Problem library</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">Exact retained fixtures. Cold baselines assume empty memory; session memory intentionally persists.</p>
            </div>
            <nav className="p-2" aria-label="Problem fixtures">
              {FIXTURES.map((fixture) => (
                <button
                  key={fixture.id}
                  type="button"
                  onClick={() => void loadFixture(fixture.id)}
                  disabled={busy !== null || fixtureLoading}
                  className={`group mb-1 flex w-full items-start gap-3 border px-3 py-3 text-left transition-colors last:mb-0 disabled:cursor-wait disabled:opacity-60 ${selectedFixture === fixture.id ? 'border-primary/40 bg-primary/10' : 'border-transparent hover:border-border hover:bg-muted/40'}`}
                >
                  <span className={`mt-1 size-1.5 shrink-0 rounded-full ${fixture.expected.includes('CONCLUDED') ? 'bg-emerald-400' : fixture.expected.includes('CONFLICT') ? 'bg-rose-400' : 'bg-amber-400'}`} />
                  <span className="min-w-0 flex-1">
                    <span className="block font-mono text-[11px]">{fixture.title}</span>
                    <span className="mt-0.5 block font-mono text-[8px] uppercase tracking-[0.12em] text-muted-foreground">{fixture.category}</span>
                    <span className="mt-1.5 block text-[10px] leading-4 text-muted-foreground">{fixture.description}</span>
                    <span className="mt-1.5 block font-mono text-[8px] text-primary/75">COLD · {fixture.expected}</span>
                  </span>
                  <ChevronRight className="mt-0.5 size-3 shrink-0 text-muted-foreground group-hover:text-foreground" />
                </button>
              ))}
            </nav>
            <div className="border-t border-border p-3">
              <div className="border border-amber-400/25 bg-amber-400/5 p-3">
                <div className="flex items-center gap-2 text-[11px] font-medium text-amber-200"><Database className="size-3.5" /> Warm-memory experiment</div>
                <p className="mt-1.5 text-[10px] leading-4 text-muted-foreground">Run Deduction, load Exact memory recall without resetting, then run again.</p>
              </div>
              <Button variant="outline" size="sm" className="mt-2 w-full rounded-none" onClick={() => void resetMemory()} disabled={!runtimeReady || busy !== null}>
                <RefreshCcw data-icon="inline-start" /> Reset session memory
              </Button>
            </div>
          </aside>

          <section className="flex min-h-[720px] flex-col border border-border bg-card/75">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
              <div>
                <p className="eyebrow">Problem packet</p>
                <p className="mt-1 font-mono text-[11px]">fixtures/{selectedFixture}/problem.json</p>
              </div>
              <Badge variant="outline" className="rounded-sm border-primary/30 bg-primary/5 font-mono text-[9px] text-primary">EDITABLE JSON</Badge>
            </div>
            <div className="relative flex-1 p-3">
              <Textarea
                aria-label="Problem packet JSON"
                value={problemText}
                onChange={(event) => setProblemText(event.target.value)}
                spellCheck={false}
                className="h-full min-h-[570px] resize-y rounded-none border-border bg-[#050b0e] p-4 font-mono text-[11px] leading-5 text-cyan-50 shadow-inner selection:bg-primary/30"
              />
            </div>
            <div className="border-t border-border p-3">
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" className="rounded-none" onClick={() => { setProblemText(fixtureBaseline); setNotice('Editor restored to the retained fixture.'); }} disabled={fixtureLoading || busy !== null}>
                  <RotateCcw data-icon="inline-start" /> Restore fixture
                </Button>
                <Button variant="outline" size="sm" className="rounded-none" onClick={() => void validatePacket()} disabled={controlsDisabled}>
                  <FileCheck2 data-icon="inline-start" /> Check packet
                </Button>
                <Button size="sm" className="rounded-none shadow-[0_0_28px_rgb(34_211_238/18%)]" onClick={() => void runMachine()} disabled={controlsDisabled}>
                  {busy === 'run' ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <Play data-icon="inline-start" />}
                  Run machine
                </Button>
              </div>
              <div className="mt-3 flex items-center justify-between gap-3 text-[10px] text-muted-foreground">
                <span>Browser-local execution · no arbitrary Python · no external actions</span>
                <span className="font-mono text-primary">SOLE-WRITER KERNEL</span>
              </div>
            </div>
          </section>

          <section className="min-w-0 border border-border bg-card/75">
            <div className="flex min-h-[72px] flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
              <div>
                <p className="eyebrow">Run inspector</p>
                <h2 ref={resultHeadingRef} tabIndex={-1} className="mt-1 text-sm font-semibold outline-none">{bundle ? outcome.title : reply?.error ? 'Run rejected' : 'Awaiting execution'}</h2>
              </div>
              {status && <Badge className={`rounded-sm ${status === 'CONCLUDED' ? 'bg-emerald-400/15 text-emerald-300' : status === 'CONFLICT_UNRESOLVED' ? 'bg-rose-400/15 text-rose-300' : 'bg-amber-400/15 text-amber-300'}`}>{status}</Badge>}
            </div>

            {!bundle && !reply?.error && (
              <div className="grid min-h-[650px] place-items-center p-8 text-center">
                <div className="max-w-sm">
                  <div className="mx-auto grid size-16 place-items-center rounded-full border border-primary/30 bg-primary/5 text-primary"><Play className="size-6" /></div>
                  <h3 className="mt-5 text-base font-semibold">Run a real reasoning episode</h3>
                  <p className="mt-2 text-xs leading-6 text-muted-foreground">The inspector will expose the conclusion, proof steps, branches, prerequisite frames, sealed trace, hashes, and downloadable evidence bundle.</p>
                </div>
              </div>
            )}

            {!bundle && reply?.error && (
              <div className="p-4">
                <div className="border border-rose-400/30 bg-rose-400/5 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-rose-200"><XCircle className="size-4" /> {reply.error.type}</div>
                  <p className="mt-2 text-xs leading-5 text-rose-100/80">{reply.error.message}</p>
                  <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.16em] text-rose-300">{reply.error.kind}</p>
                </div>
                {(reply.validation || reply.report) && <JsonBlock value={reply.validation ?? reply.report} className="mt-3 max-h-[520px]" />}
              </div>
            )}

            {bundle && (
              <>
                <div className="grid grid-cols-4 gap-px border-b border-border bg-border">
                  {[
                    ['TICKS', String(summary?.logical_ticks ?? '—')],
                    ['EVENTS', String(trace.length)],
                    ['AUTHORIZED', String(totalAuthorized)],
                    ['REJECTED', String(totalRejected)],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-card px-2 py-3 text-center">
                      <p className="font-mono text-[8px] text-muted-foreground">{label}</p>
                      <p className="mt-1 font-mono text-lg text-primary">{value}</p>
                    </div>
                  ))}
                </div>
                <div className="overflow-x-auto border-b border-border" role="tablist" aria-label="Run artifact sections">
                  <div className="flex min-w-max px-2 pt-2">
                    {TABS.map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={activeTab === tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`border-b-2 px-3 py-2 font-mono text-[9px] uppercase tracking-[0.12em] ${activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="min-h-[520px] p-4">
                  {activeTab === 'outcome' && (
                    <div className="space-y-4">
                      <div className={`border p-4 ${toneClasses(outcome.tone)}`}>
                        <div className="flex items-start gap-3">
                          {outcome.tone === 'success' ? <CheckCircle2 className="mt-0.5 size-5 shrink-0" /> : outcome.tone === 'danger' ? <ShieldAlert className="mt-0.5 size-5 shrink-0" /> : <TriangleAlert className="mt-0.5 size-5 shrink-0" />}
                          <div>
                            <h3 className="text-sm font-semibold">{outcome.title}</h3>
                            <p className="mt-1 text-[11px] leading-5 opacity-75">{outcome.detail}</p>
                          </div>
                        </div>
                      </div>
                      <div>
                        <p className="eyebrow">Committed conclusion</p>
                        <div className="mt-2 border border-primary/30 bg-primary/5 p-4 font-mono text-sm text-cyan-100">{formatProposition(summary?.conclusion ?? evidence?.query_result?.conclusion)}</div>
                      </div>
                      {(evidence?.query_result?.lacunae?.length ?? 0) > 0 && (
                        <div>
                          <p className="eyebrow">Explicit lacunae</p>
                          <ul className="mt-2 space-y-1.5">
                            {evidence?.query_result?.lacunae?.map((item) => <li key={item} className="border border-amber-400/20 bg-amber-400/5 px-3 py-2 font-mono text-[10px] text-amber-100">{item}</li>)}
                          </ul>
                        </div>
                      )}
                      {(evidence?.diagnostics?.length ?? 0) > 0 && <JsonBlock value={evidence?.diagnostics} />}
                      <div className="border border-border bg-muted/15 px-3">
                        <HashRow label="RUN ID" value={summary?.run_id} onCopy={copyHash} />
                        <HashRow label="FINAL STATE" value={summary?.final_state_hash} onCopy={copyHash} />
                        <HashRow label="TRACE DIGEST" value={summary?.trace_digest} onCopy={copyHash} />
                      </div>
                    </div>
                  )}

                  {activeTab === 'proof' && (
                    <div>
                      <div className="mb-4 flex items-center justify-between"><p className="eyebrow">Verified proof steps</p><Badge variant="outline" className="rounded-sm font-mono text-[9px]">{evidence?.proof_steps?.length ?? 0} STEPS</Badge></div>
                      {(evidence?.proof_steps?.length ?? 0) === 0 ? (
                        <div className="border border-border bg-muted/15 p-5 text-xs leading-6 text-muted-foreground">No proof step was committed in this run. Inspect Outcome and Prerequisites for the machine’s explicit stopping reason.</div>
                      ) : (
                        <div className="space-y-3">
                          {evidence?.proof_steps?.map((step, index) => (
                            <article key={step.step_id ?? index} className="border border-border bg-muted/10 p-3">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2"><span className="grid size-6 place-items-center border border-primary/30 font-mono text-[9px] text-primary">{index + 1}</span><code className="text-[10px] text-cyan-100">{step.operation}</code></div>
                                <Badge variant="outline" className={step.verified ? 'rounded-sm border-emerald-400/30 text-emerald-300' : 'rounded-sm border-rose-400/30 text-rose-300'}>{step.verified ? 'VERIFIED' : 'UNVERIFIED'}</Badge>
                              </div>
                              <p className="mt-3 font-mono text-xs text-foreground">{(step.premise_keys ?? []).join(' + ') || 'declared support'} → {formatProposition(step.conclusion)}</p>
                              <div className="mt-2 flex flex-wrap gap-2 font-mono text-[9px] text-muted-foreground"><span>rule {step.rule_id ?? '—'}</span><span>·</span><span>branch {step.branch_id ?? '—'}</span><span>·</span><span>{step.step_id}</span></div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'branches' && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between"><p className="eyebrow">Preserved branch results</p><Badge variant="outline" className="rounded-sm font-mono text-[9px]">{evidence?.branch_summary?.length ?? 0} BRANCHES</Badge></div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {evidence?.branch_summary?.map((branch) => (
                          <article key={branch.branch_id} className="border border-border bg-muted/10 p-3">
                            <div className="flex items-center justify-between gap-2"><code className="text-[10px] text-cyan-100">{branch.branch_id}</code><Badge variant="outline" className="rounded-sm font-mono text-[8px]">{branch.status}</Badge></div>
                            <p className="mt-2 text-[10px] text-muted-foreground">candidate: <span className="font-mono text-foreground">{branch.candidate_id}</span></p>
                            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                              {[['PROOFS', branch.proof_step_ids?.length ?? 0], ['UNKNOWNS', branch.unknowns?.length ?? 0], ['CONFLICTS', branch.contradictions?.length ?? 0]].map(([label, count]) => <div key={String(label)} className="border border-border/70 p-2"><p className="font-mono text-[7px] text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm text-primary">{count}</p></div>)}
                            </div>
                          </article>
                        ))}
                      </div>
                      {(evidence?.comparison?.length ?? 0) > 0 && (
                        <div>
                          <p className="eyebrow">Shared-frame comparison</p>
                          {evidence?.comparison?.map((report) => (
                            <div key={report.report_id} className="mt-2 border border-primary/25 bg-primary/5 p-3">
                              <div className="flex items-center gap-2 text-xs"><GitBranch className="size-4 text-primary" /> Winner: <code className="text-primary">{report.winner_branch_id}</code></div>
                              <p className="mt-2 text-[10px] leading-5 text-muted-foreground">Order: {report.ordered_branch_ids?.join(' → ')}</p>
                              <p className="mt-1 break-all font-mono text-[9px] text-muted-foreground">frame {shortHash(report.evaluation_frame_hash)}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'rpm' && (
                    <div>
                      <div className="grid grid-cols-2 gap-px border border-border bg-border">
                        <div className="bg-card p-3"><p className="eyebrow">RPM events</p><p className="mt-1 font-mono text-xl text-primary">{evidence?.rpm_summary?.event_count ?? 0}</p></div>
                        <div className="bg-card p-3"><p className="eyebrow">Final depth</p><p className="mt-1 font-mono text-xl text-primary">{evidence?.rpm_summary?.final_depth ?? 0}</p></div>
                      </div>
                      {(evidence?.rpm_summary?.events?.length ?? 0) === 0 ? (
                        <div className="mt-4 border border-border bg-muted/15 p-5 text-xs leading-6 text-muted-foreground">This fixture did not enter the Recursive Prerequisite Manager. Select RPM success or RPM failure to inspect explicit push, return, and resolution events.</div>
                      ) : (
                        <JsonBlock value={evidence?.rpm_summary?.events} className="mt-4 max-h-[480px]" />
                      )}
                    </div>
                  )}

                  {activeTab === 'trace' && (
                    <div>
                      <div className="flex items-center justify-between"><p className="eyebrow">Sealed event chain</p><span className="font-mono text-[9px] text-muted-foreground">{traceIndex + 1} / {trace.length}</span></div>
                      <input className="mt-4 w-full accent-cyan-400" type="range" min={0} max={Math.max(trace.length - 1, 0)} step={1} value={Math.min(traceIndex, Math.max(trace.length - 1, 0))} onChange={(event) => setTraceIndex(Number(event.target.value))} aria-label="Trace event" />
                      {traceEvent && (
                        <div className="mt-4 space-y-3">
                          <div className="border border-primary/25 bg-primary/5 p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2"><code className="text-[10px] text-cyan-100">tick {traceEvent.logical_tick} · {traceEvent.proposed_intents?.map((intent) => intent.intent_type).join(' + ') || 'NO INTENT'}</code><Badge variant="outline" className={traceEvent.sealed ? 'rounded-sm border-emerald-400/30 text-emerald-300' : 'rounded-sm border-rose-400/30 text-rose-300'}>{traceEvent.sealed ? 'SEALED' : 'UNSEALED'}</Badge></div>
                            <p className="mt-2 font-mono text-[9px] text-muted-foreground">{traceEvent.enabled_components?.join(', ')}</p>
                          </div>
                          <div className="grid gap-2 sm:grid-cols-3">
                            {[['PROPOSED', traceEvent.proposed_intents?.length ?? 0], ['AUTHORIZED', traceEvent.authorized_intent_ids?.length ?? 0], ['REJECTED', traceEvent.rejected_intents?.length ?? 0]].map(([label, count]) => <div key={String(label)} className="border border-border bg-muted/10 p-2 text-center"><p className="font-mono text-[8px] text-muted-foreground">{label}</p><p className="mt-1 font-mono text-base text-primary">{count}</p></div>)}
                          </div>
                          <JsonBlock value={traceEvent} className="max-h-[390px]" />
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'evidence' && (
                    <div className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className={`border p-3 ${verification?.valid ? 'border-emerald-400/30 bg-emerald-400/5' : 'border-rose-400/30 bg-rose-400/5'}`}>
                          <div className="flex items-center gap-2 text-xs font-semibold">{verification?.valid ? <ShieldCheck className="size-4 text-emerald-300" /> : <ShieldAlert className="size-4 text-rose-300" />} Generated bundle</div>
                          <p className="mt-1.5 text-[10px] text-muted-foreground">{verification?.valid ? 'Same-runtime verifier passed.' : 'Verifier did not pass.'}</p>
                        </div>
                        <div className={`border p-3 ${manualVerification?.valid ? 'border-emerald-400/30 bg-emerald-400/5' : 'border-border bg-muted/10'}`}>
                          <div className="flex items-center gap-2 text-xs font-semibold"><FileCheck2 className="size-4 text-primary" /> Fresh same-runtime recheck</div>
                          <p className="mt-1.5 text-[10px] text-muted-foreground">{manualVerification ? (manualVerification.valid ? 'Receipt recheck passed.' : 'Receipt recheck failed.') : 'Press Verify receipt to run it.'}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button variant="outline" size="sm" className="rounded-none" onClick={() => void verifyBundle()} disabled={busy !== null}><ShieldCheck data-icon="inline-start" /> Verify receipt</Button>
                        <Button variant="outline" size="sm" className="rounded-none" onClick={() => void replayLast()} disabled={busy !== null || !replayAvailable}><History data-icon="inline-start" /> Session replay</Button>
                        <Button variant="outline" size="sm" className="rounded-none" onClick={downloadBundle}><Download data-icon="inline-start" /> Download bundle</Button>
                        <Button variant="outline" size="sm" className="rounded-none" onClick={downloadTrace}><Download data-icon="inline-start" /> Trace</Button>
                        <Button variant="outline" size="sm" className="rounded-none" onClick={downloadFinalState}><Download data-icon="inline-start" /> Final state</Button>
                        <Button variant="outline" size="sm" className="rounded-none" onClick={downloadEvidence}><Download data-icon="inline-start" /> Evidence</Button>
                      </div>
                      {replayResult !== null && <div className={`border px-3 py-2 text-xs ${replayResult ? 'border-emerald-400/30 bg-emerald-400/5 text-emerald-200' : 'border-rose-400/30 bg-rose-400/5 text-rose-200'}`}>{replayResult ? 'Session replay matched final state, trace, and evidence.' : 'Replay diverged.'}</div>}
                      <div>
                        <p className="eyebrow">Commitment gates</p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          {Object.entries(evidence?.commitment_gates ?? {}).map(([gate, passed]) => <div key={gate} className="flex items-center justify-between border border-border bg-muted/10 px-3 py-2"><code className="text-[9px]">{gate}</code>{passed ? <CheckCircle2 className="size-3.5 text-emerald-300" /> : <XCircle className="size-3.5 text-rose-300" />}</div>)}
                        </div>
                      </div>
                      <div className="border border-border bg-muted/10 px-3">
                        <HashRow label="PROBLEM PACKET" value={evidence?.problem_packet_hash} onCopy={copyHash} />
                        <HashRow label="FINAL STATE" value={evidence?.final_state_hash} onCopy={copyHash} />
                        <HashRow label="TRACE HEAD" value={evidence?.trace_head} onCopy={copyHash} />
                        <HashRow label="TRACE DIGEST" value={evidence?.trace_digest} onCopy={copyHash} />
                        <HashRow label="EVIDENCE" value={evidence?.evidence_digest} onCopy={copyHash} />
                      </div>
                      <div>
                        <p className="eyebrow">Claim boundary carried in the receipt</p>
                        <JsonBlock value={evidence?.claim_boundary} className="mt-2 max-h-[280px]" />
                      </div>
                    </div>
                  )}

                  {activeTab === 'raw' && <JsonBlock value={bundle} className="max-h-[690px]" />}
                </div>
              </>
            )}
          </section>
        </div>
        </div>

        <div hidden={surfaceMode !== 'receipt'}>
          <ReceiptPanel
            clientRef={clientRef}
            runtimeReady={runtimeReady}
            latestBundle={bundle as Record<string, unknown> | undefined}
            onNotice={setNotice}
          />
        </div>

        <section className="mt-4 grid gap-px border border-border bg-border lg:grid-cols-2">
          <div className="bg-card p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-200"><CheckCircle2 className="size-4" /> Working now</div>
            <p className="mt-2 text-[11px] leading-6 text-muted-foreground">Controlled facts, rules, questions, negative propositions, bounded pronoun resolution, typed clarification, exact integer/rational CAS-Math, checked linear proofs, bounded counterexamples, deterministic inference, RPM event/receipt inspection, sealed traces, session-local replay, artifact export, independent receipt verification, browser-local language and domain-neutral cognitive-apprenticeship laboratories, and an interactive CAS-Ohm whole-machine design simulation.</p>
          </div>
          <div className="bg-card p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-200"><Info className="size-4" /> Proposed — not implemented</div>
            <p className="mt-2 text-[11px] leading-6 text-muted-foreground">A live AWS 20B teacher connection, kernel-integrated lesson promotion, live teacher-model generation, autonomous cross-domain learning, current-fact retrieval, neural distillation, multimodal grounding, durable native lesson memory, R1 rollback authority, live CAS-Ohm runtime records or scheduler allocation, compiled CJT identities, general English, a Transformer language peripheral, full CCB-L1/CCB-D1, mathematical strategy learning and RRK math-state integration, topic-stack dialogue, a full Foundry/Board editor, CRQS or CONV grades, external actions, production security, and broader intelligence claims.</p>
          </div>
        </section>

        <footer className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border py-4 font-mono text-[9px] text-muted-foreground">
          <span>REFERENCE DEMONSTRATOR ONLY · HOMEBASE SOURCE {shortHash(runtime.sourceSpecSha256)}</span>
          <span>RUNTIME {runtime.runtimeVersion ?? '—'} · BRIDGE {runtime.bridgeVersion ?? '—'} · CONVERSATION {runtime.conversationProtocolVersion ?? '—'} · PYODIDE {runtime.pyodideVersion ?? '—'} · TREE {shortHash(runtime.packageTreeSha256)}</span>
        </footer>
      </section>
    </main>
  );
}
