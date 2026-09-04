'use client';

import { KeyboardEvent, RefObject, SyntheticEvent, useMemo, useState } from 'react';
import {
  Brain,
  CircleAlert,
  FileJson2,
  GitCompareArrows,
  LoaderCircle,
  MessageCircle,
  Network,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Bubble, BubbleContent } from '@/components/ui/bubble';
import { Button } from '@/components/ui/button';
import {
  Message,
  MessageContent,
  MessageFooter,
  MessageGroup,
  MessageHeader,
} from '@/components/ui/message';
import { Textarea } from '@/components/ui/textarea';
import {
  CncmClient,
  ConversationTurn,
  MemorySummary,
} from '@/lib/cncm-client';

type CognitiveTab = 'meaning' | 'dialogue' | 'reasoning' | 'kernel' | 'raw';

interface ChatExchange {
  id: number;
  user: string;
  turn: ConversationTurn;
}

interface ChatPanelProps {
  clientRef: RefObject<CncmClient | null>;
  runtimeReady: boolean;
  onNotice: (message: string) => void;
  onMemoryChange: (memory: MemorySummary) => void;
  onResetMind: () => Promise<void>;
  onLoadProblem: (problem: Record<string, unknown>) => void;
}

const SCRIPTS = [
  {
    title: 'Prove mortality',
    description: 'Fact → rule → verified answer',
    turns: ['Alice is human.', 'Every human is mortal.', 'Is Alice mortal?'],
  },
  {
    title: 'Resolve “she”',
    description: 'One clear recent referent',
    turns: ['Ada is human.', 'Every human is mortal.', 'Is she mortal?'],
  },
  {
    title: 'Force clarification',
    description: 'Two candidates; no guessing',
    turns: ['Every human is mortal.', 'Ada is human.', 'Grace is human.', 'Is she mortal?'],
  },
  {
    title: 'Expose a gap',
    description: 'No supporting fact or rule',
    turns: ['Is Turing patient?'],
  },
];

const COGNITIVE_TABS: Array<{ id: CognitiveTab; label: string }> = [
  { id: 'meaning', label: 'Meaning' },
  { id: 'dialogue', label: 'Dialogue' },
  { id: 'reasoning', label: 'Reasoning' },
  { id: 'kernel', label: 'Kernel trace' },
  { id: 'raw', label: 'Raw turn' },
];

function JsonPanel({ value, className = '' }: { value: unknown; className?: string }) {
  return (
    <pre className={`overflow-auto border border-border bg-[#050b0e] p-3 font-mono text-[10px] leading-5 text-cyan-50 ${className}`}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function statusStyle(status: ConversationTurn['status']) {
  if (status === 'ANSWERED') return 'border-emerald-400/35 bg-emerald-400/10 text-emerald-200';
  if (status === 'CLARIFICATION_REQUIRED' || status === 'NO_COMMITMENT') return 'border-amber-400/35 bg-amber-400/10 text-amber-200';
  if (status === 'REJECTED') return 'border-rose-400/35 bg-rose-400/10 text-rose-200';
  return 'border-primary/35 bg-primary/10 text-cyan-100';
}

function displayScalar(value: unknown, fallback = '—') {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  return value == null ? fallback : JSON.stringify(value);
}

function conclusionText(bundle: Record<string, unknown> | null) {
  const summary = bundle?.summary as Record<string, unknown> | undefined;
  const conclusion = summary?.conclusion as Record<string, unknown> | null | undefined;
  if (!conclusion?.predicate) return 'No conclusion committed';
  const argumentsValue = Array.isArray(conclusion.arguments) ? conclusion.arguments.join(', ') : '';
  return `${conclusion.polarity === false ? '¬' : ''}${displayScalar(conclusion.predicate)}(${argumentsValue})`;
}

export function ChatPanel({
  clientRef,
  runtimeReady,
  onNotice,
  onMemoryChange,
  onResetMind,
  onLoadProblem,
}: ChatPanelProps) {
  const [draft, setDraft] = useState('');
  const [turns, setTurns] = useState<ChatExchange[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<CognitiveTab>('meaning');
  const [busy, setBusy] = useState(false);

  const selected = useMemo(
    () => turns.find((item) => item.id === selectedId) ?? turns.at(-1) ?? null,
    [selectedId, turns],
  );
  const selectedTrace = selected?.turn.trace;
  const reasoningBundle = selectedTrace?.reasoning_bundle ?? null;
  const reasoningSummary = reasoningBundle?.summary as Record<string, unknown> | undefined;
  const reasoningEvidence = reasoningBundle?.evidence as Record<string, unknown> | undefined;
  const kernelTrace = reasoningBundle?.trace as unknown[] | undefined;
  const verificationValid = (selectedTrace?.verification as Record<string, unknown> | null)?.valid === true;
  const parity = selectedTrace?.execution_parity;
  const answerAccepted = selected?.turn.status === 'ANSWERED' && verificationValid && parity?.matches === true;
  const paritySummary = parity
    ? {
        schema_version: parity.schema_version,
        performed: parity.performed,
        matches: parity.matches,
        claim_scope: parity.claim_scope,
        does_not_establish: parity.does_not_establish,
        compared_fields: parity.compared_fields,
        primary_run: parity.primary_run,
        confirmation_run: parity.confirmation_run,
      }
    : null;

  const dispatch = async (text: string): Promise<ChatExchange | null> => {
    const client = clientRef.current;
    if (!client || !runtimeReady) return null;
    const reply = await client.conversationTurn(text);
    if (reply.memory) onMemoryChange(reply.memory);
    if (!reply.ok || !reply.conversation) {
      throw new Error(reply.error?.message ?? 'The conversation bridge failed closed.');
    }
    const exchange = {
      id: reply.conversation.trace.turn_index,
      user: text,
      turn: reply.conversation,
    };
    setTurns((current) => [...current, exchange].slice(-64));
    setSelectedId(exchange.id);
    setActiveTab(reply.conversation.trace.reasoning_bundle ? 'reasoning' : 'meaning');
    return exchange;
  };

  const send = async (text: string) => {
    const clean = text.trim();
    if (!clean || busy || !runtimeReady) return;
    setBusy(true);
    onNotice('Interpreting the controlled sentence…');
    try {
      const exchange = await dispatch(clean);
      setDraft('');
      onNotice(
        exchange?.turn.status === 'ANSWERED'
          ? 'Answer committed, evidence verified, and reproduced on a second fresh machine.'
          : exchange?.turn.status === 'CLARIFICATION_REQUIRED'
            ? 'Reference unresolved. The Mind asked instead of guessing.'
            : 'Conversation turn complete. Inspect the synchronized cognitive record.',
      );
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    void send(draft);
  };

  const handleDraftKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void send(draft);
    }
  };

  const runScript = async (script: (typeof SCRIPTS)[number]) => {
    const client = clientRef.current;
    if (busy || !runtimeReady || !client) return;
    setBusy(true);
    onNotice(`Running “${script.title}” through the language and reasoning boundaries…`);
    try {
      const resetReply = await client.conversationReset();
      if (resetReply.memory) onMemoryChange(resetReply.memory);
      setTurns([]);
      setSelectedId(null);
      for (const text of script.turns) await dispatch(text);
      onNotice('Example complete. Select a response to inspect its actual trace.');
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const clearConversation = async () => {
    const client = clientRef.current;
    if (!client || busy) return;
    setBusy(true);
    try {
      const reply = await client.conversationReset();
      if (reply.memory) onMemoryChange(reply.memory);
      setTurns([]);
      setSelectedId(null);
      setActiveTab('meaning');
      onNotice('Conversation facts, rules, references, and transcript cleared.');
    } catch (error) {
      onNotice(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const resetWholeMind = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await onResetMind();
      setTurns([]);
      setSelectedId(null);
      setActiveTab('meaning');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="border border-border bg-card/75">
      <div className="grid gap-px bg-border xl:grid-cols-[minmax(360px,0.9fr)_minmax(420px,1.1fr)]">
        <div className="flex min-h-[760px] min-w-0 flex-col bg-card">
          <div className="border-b border-border p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="eyebrow">Conversation pane</p>
                <h2 className="mt-1 flex items-center gap-2 text-base font-semibold"><MessageCircle className="size-4 text-primary" /> Chat With This Mind</h2>
                <p className="mt-2 max-w-xl text-[11px] leading-5 text-muted-foreground">
                  This first language board accepts five exact sentence patterns. It does not use an external model and never turns unsupported prose into facts.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="rounded-sm border-primary/30 bg-primary/5 font-mono text-[9px] text-primary">CONTROLLED ENGLISH</Badge>
                <Badge variant="outline" className="rounded-sm border-border font-mono text-[9px] text-muted-foreground">CONV: NOT QUALIFIED</Badge>
              </div>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {SCRIPTS.map((script) => (
                <button
                  key={script.title}
                  type="button"
                  onClick={() => void runScript(script)}
                  disabled={busy || !runtimeReady}
                  className="border border-border bg-muted/15 px-3 py-2 text-left transition-colors hover:border-primary/35 hover:bg-primary/5 disabled:cursor-wait disabled:opacity-50"
                >
                  <span className="block font-mono text-[10px] text-cyan-100">{script.title}</span>
                  <span className="mt-1 block text-[9px] text-muted-foreground">{script.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="min-h-[390px] flex-1 overflow-y-auto p-4" aria-live="polite">
            {turns.length === 0 ? (
              <div className="grid min-h-[360px] place-items-center text-center">
                <div className="max-w-md">
                  <div className="mx-auto grid size-14 place-items-center rounded-full border border-primary/30 bg-primary/5 text-primary"><Sparkles className="size-5" /></div>
                  <h3 className="mt-4 text-sm font-semibold">Teach it facts, then ask a question</h3>
                  <div className="mt-3 border border-border bg-[#050b0e] p-3 text-left font-mono text-[10px] leading-6 text-cyan-50">
                    Alice is human.<br />
                    Alice is not mechanical.<br />
                    Every human is mortal.<br />
                    Is Alice mortal?<br />
                    I mean Alice.
                  </div>
                </div>
              </div>
            ) : (
              <MessageGroup className="gap-5">
                {turns.map((exchange) => (
                  <div key={exchange.id} className="space-y-2">
                    <Message align="end">
                      <MessageContent>
                        <MessageHeader>You · turn {exchange.id}</MessageHeader>
                        <Bubble align="end" variant="secondary"><BubbleContent>{exchange.user}</BubbleContent></Bubble>
                      </MessageContent>
                    </Message>
                    <Message>
                      <MessageContent>
                        <MessageHeader>CAS Mind</MessageHeader>
                        <Bubble variant="tinted"><BubbleContent>{exchange.turn.response}</BubbleContent></Bubble>
                        <MessageFooter className="gap-2">
                          <Badge variant="outline" className={`rounded-sm font-mono text-[8px] ${statusStyle(exchange.turn.status)}`}>{exchange.turn.status}</Badge>
                          <button type="button" className="font-mono text-[9px] text-primary hover:underline" onClick={() => setSelectedId(exchange.id)}>Inspect actual trace</button>
                        </MessageFooter>
                      </MessageContent>
                    </Message>
                  </div>
                ))}
              </MessageGroup>
            )}
          </div>

          <form onSubmit={submit} className="border-t border-border p-3">
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleDraftKey}
              maxLength={512}
              rows={3}
              aria-label="Controlled English message"
              placeholder="Type: Alice is human."
              className="min-h-20 resize-none rounded-none border-border bg-[#050b0e] font-mono text-[11px] text-cyan-50"
            />
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <span className="text-[9px] text-muted-foreground">Ctrl/⌘ + Enter to send · 512 characters maximum</span>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="outline" size="sm" className="rounded-none" onClick={() => void clearConversation()} disabled={busy || !runtimeReady}><RotateCcw data-icon="inline-start" /> Clear conversation</Button>
                <Button type="submit" size="sm" className="rounded-none" disabled={busy || !runtimeReady || !draft.trim()}>
                  {busy ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <Send data-icon="inline-start" />}
                  Send
                </Button>
              </div>
            </div>
          </form>
        </div>

        <div className="min-w-0 bg-card">
          <div className="flex min-h-[92px] flex-wrap items-center justify-between gap-3 border-b border-border p-4">
            <div>
              <p className="eyebrow">Live cognitive pane</p>
              <h2 className="mt-1 flex items-center gap-2 text-base font-semibold"><Brain className="size-4 text-primary" /> What produced this response</h2>
              <p className="mt-1 text-[10px] text-muted-foreground">Select any response. This pane shows its stored record, not a newly invented explanation.</p>
            </div>
            {selected && <Badge variant="outline" className={`rounded-sm font-mono text-[9px] ${statusStyle(selected.turn.status)}`}>TURN {selected.id} · {selected.turn.status}</Badge>}
          </div>

          {!selected ? (
            <div className="grid min-h-[665px] place-items-center p-8 text-center">
              <div className="max-w-sm">
                <Network className="mx-auto size-8 text-primary" />
                <h3 className="mt-4 text-sm font-semibold">The cognitive record will appear here</h3>
                <p className="mt-2 text-[11px] leading-5 text-muted-foreground">Run an example or send one controlled sentence. Questions expose the exact compiled packet, two fresh-machine executions, verified result, proof, and sealed kernel trace.</p>
              </div>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto border-b border-border" role="tablist" aria-label="Conversation cognitive record">
                <div className="flex min-w-max px-2 pt-2">
                  {COGNITIVE_TABS.map((tab) => (
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
              <div className="min-h-[590px] p-4">
                {activeTab === 'meaning' && (
                  <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="border border-border bg-muted/10 p-3"><p className="eyebrow">Selected meaning</p><JsonPanel value={selectedTrace?.selected_meaning} className="mt-2 max-h-48" /></div>
                      <div className="border border-border bg-muted/10 p-3"><p className="eyebrow">Reference bindings</p><JsonPanel value={selectedTrace?.references} className="mt-2 max-h-48" /></div>
                    </div>
                    <div><p className="eyebrow">Response plan</p><JsonPanel value={selectedTrace?.response_plan} className="mt-2 max-h-56" /></div>
                    <div><p className="eyebrow">All parse candidates</p><JsonPanel value={selectedTrace?.parse_candidates} className="mt-2 max-h-56" /></div>
                  </div>
                )}

                {activeTab === 'dialogue' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-4 gap-px border border-border bg-border">
                      {[
                        ['TURNS', selected.turn.state.turn_index],
                        ['ENTITIES', selected.turn.state.entities.length],
                        ['FACTS', selected.turn.state.facts.length],
                        ['RULES', selected.turn.state.rules.length],
                      ].map(([label, value]) => <div key={String(label)} className="bg-card p-3 text-center"><p className="font-mono text-[8px] text-muted-foreground">{label}</p><p className="mt-1 font-mono text-lg text-primary">{value}</p></div>)}
                    </div>
                    <JsonPanel value={selected.turn.state} className="max-h-[490px]" />
                  </div>
                )}

                {activeTab === 'reasoning' && (
                  reasoningBundle ? (
                    <div className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className={`border p-3 ${verificationValid ? 'border-emerald-400/30 bg-emerald-400/5' : selectedTrace?.verification ? 'border-rose-400/30 bg-rose-400/5' : 'border-border bg-muted/10'}`}>
                          <div className={`flex items-center gap-2 text-xs font-semibold ${verificationValid ? 'text-emerald-200' : selectedTrace?.verification ? 'text-rose-200' : 'text-muted-foreground'}`}><ShieldCheck className="size-4" /> Evidence verifier</div>
                          <p className="mt-2 font-mono text-[10px]">{selectedTrace?.verification ? (verificationValid ? 'TRUE' : 'FALSE') : 'NOT RUN'}</p>
                        </div>
                        <div className={`border p-3 ${parity?.matches ? 'border-emerald-400/30 bg-emerald-400/5' : 'border-amber-400/30 bg-amber-400/5'}`}>
                          <div className="flex items-center gap-2 text-xs font-semibold"><GitCompareArrows className="size-4" /> Exact second-execution parity</div>
                          <p className="mt-2 font-mono text-[10px]">{parity?.performed ? (parity.matches ? 'MATCHED' : 'DID NOT MATCH') : 'NOT RUN'}</p>
                          <p className="mt-2 text-[9px] leading-4 text-muted-foreground">Same compiled packet, two fresh machines. This tests deterministic execution, not language understanding.</p>
                        </div>
                      </div>
                      <div>
                        <p className="eyebrow">{answerAccepted ? 'Accepted committed outcome' : 'Kernel-reported outcome · not accepted as an answer'}</p>
                        <div className={`mt-2 border p-4 ${answerAccepted ? 'border-primary/30 bg-primary/5' : 'border-amber-400/30 bg-amber-400/5'}`}>
                          <p className="font-mono text-sm text-cyan-100">{conclusionText(reasoningBundle)}</p>
                          <p className="mt-2 font-mono text-[9px] text-muted-foreground">terminal · {displayScalar(reasoningSummary?.terminal_status)}</p>
                          {!answerAccepted && <p className="mt-2 text-[9px] leading-4 text-amber-100/80">This kernel result was not accepted or rendered as the conversation answer.</p>}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {selectedTrace?.problem_packet && <Button variant="outline" size="sm" className="rounded-none" onClick={() => onLoadProblem(selectedTrace.problem_packet as Record<string, unknown>)}><FileJson2 data-icon="inline-start" /> Open exact packet in Problem Lab</Button>}
                      </div>
                      <div><p className="eyebrow">Execution-parity receipt</p><JsonPanel value={paritySummary} className="mt-2 max-h-64" /></div>
                      <div><p className="eyebrow">Proof and branch evidence</p><JsonPanel value={{ proof_steps: reasoningEvidence?.proof_steps, branch_summary: reasoningEvidence?.branch_summary, rpm_summary: reasoningEvidence?.rpm_summary }} className="mt-2 max-h-72" /></div>
                    </div>
                  ) : (
                    <div className="grid min-h-[470px] place-items-center text-center">
                      <div className="max-w-sm"><CircleAlert className="mx-auto size-7 text-amber-300" /><h3 className="mt-3 text-sm font-semibold">No kernel run for this turn</h3><p className="mt-2 text-[11px] leading-5 text-muted-foreground">Facts and rules update explicit dialogue state. Unsupported input and unresolved references never fabricate a problem packet.</p></div>
                    </div>
                  )
                )}

                {activeTab === 'kernel' && (
                  reasoningBundle ? (
                    <div className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div><p className="eyebrow">Exact problem packet</p><JsonPanel value={selectedTrace?.problem_packet} className="mt-2 max-h-72" /></div>
                        <div><p className="eyebrow">Sealed kernel events</p><JsonPanel value={kernelTrace} className="mt-2 max-h-72" /></div>
                      </div>
                      <div><p className="eyebrow">Verified evidence packet</p><JsonPanel value={reasoningEvidence} className="mt-2 max-h-72" /></div>
                    </div>
                  ) : <div className="border border-border bg-muted/10 p-5 text-xs text-muted-foreground">No kernel trace exists because this turn did not authorize a reasoning run.</div>
                )}

                {activeTab === 'raw' && <JsonPanel value={selected.turn} className="max-h-[570px]" />}
              </div>
            </>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border p-3">
            <span className="font-mono text-[9px] text-muted-foreground">NO NETWORK MODEL · NO TOOLS · NO DURABLE MEMORY</span>
            <Button type="button" variant="outline" size="sm" className="rounded-none" onClick={() => void resetWholeMind()} disabled={busy || !runtimeReady}><RotateCcw data-icon="inline-start" /> Reset entire Mind</Button>
          </div>
        </div>
      </div>
    </section>
  );
}
