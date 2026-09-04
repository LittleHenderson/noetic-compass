'use client';

import { useMemo, useRef, useState } from 'react';
import type { ChangeEvent, RefObject } from 'react';
import {
  CheckCircle2,
  FileCheck2,
  FileJson,
  FlaskConical,
  LoaderCircle,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import type { BridgeReply, CncmClient } from '@/lib/cncm-client';

interface VerificationCheck {
  name?: string;
  passed?: boolean;
}

interface ReceiptVerification {
  schema_version?: string;
  valid?: boolean;
  checks?: VerificationCheck[];
  errors?: string[];
}

interface ReceiptPanelProps {
  clientRef: RefObject<CncmClient | null>;
  runtimeReady: boolean;
  latestBundle?: Record<string, unknown>;
  onNotice: (message: string) => void;
}

interface ReceiptSummary {
  problemId: string;
  terminalStatus: string;
  events: number;
  bytes: number;
}

const MAX_RECEIPT_BYTES = 5 * 1024 * 1024;

function summarizeReceipt(text: string): ReceiptSummary | null {
  if (!text.trim()) return null;
  try {
    const parsed = JSON.parse(text) as {
      summary?: { problem_id?: unknown; terminal_status?: unknown };
      trace?: unknown;
    };
    return {
      problemId: typeof parsed.summary?.problem_id === 'string' ? parsed.summary.problem_id : 'unknown',
      terminalStatus: typeof parsed.summary?.terminal_status === 'string' ? parsed.summary.terminal_status : 'unknown',
      events: Array.isArray(parsed.trace) ? parsed.trace.length : 0,
      bytes: new Blob([text]).size,
    };
  } catch {
    return null;
  }
}

export function ReceiptPanel({
  clientRef,
  runtimeReady,
  latestBundle,
  onNotice,
}: ReceiptPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [receiptText, setReceiptText] = useState('');
  const [receiptName, setReceiptName] = useState('No receipt loaded');
  const [verification, setVerification] = useState<ReceiptVerification | null>(null);
  const [bridgeError, setBridgeError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const summary = useMemo(() => summarizeReceipt(receiptText), [receiptText]);
  const checks = verification?.checks ?? [];
  const passedChecks = checks.filter((check) => check.passed).length;
  const failedChecks = checks.length - passedChecks;

  const clearResult = () => {
    setVerification(null);
    setBridgeError(null);
  };

  const loadLatest = () => {
    if (!latestBundle) return;
    setReceiptText(JSON.stringify(latestBundle, null, 2));
    setReceiptName('Latest Problem Lab run');
    clearResult();
    onNotice('Latest run loaded into Receipt Lab. Verify it or create a tampered copy.');
  };

  const loadFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.size > MAX_RECEIPT_BYTES) {
      onNotice('Receipt rejected before loading: the file is larger than 5 MB.');
      return;
    }
    try {
      const text = await file.text();
      JSON.parse(text);
      setReceiptText(text.trim());
      setReceiptName(file.name);
      clearResult();
      onNotice(`${file.name} loaded locally. No file was uploaded to a server.`);
    } catch (error) {
      onNotice(error instanceof Error ? `Receipt JSON is invalid: ${error.message}` : 'Receipt JSON is invalid.');
    }
  };

  const tamperWithCopy = () => {
    try {
      const parsed = JSON.parse(receiptText) as {
        final_state?: Record<string, unknown>;
      };
      if (!parsed.final_state || typeof parsed.final_state !== 'object') {
        throw new Error('receipt has no final_state object');
      }
      parsed.final_state.state_hash = '0'.repeat(64);
      setReceiptText(JSON.stringify(parsed, null, 2));
      setReceiptName(`${receiptName} · tampered copy`);
      clearResult();
      onNotice('Tampered copy created by replacing the retained final-state hash. Verify it to observe fail-closed behavior.');
    } catch (error) {
      onNotice(error instanceof Error ? `Cannot create tampered copy: ${error.message}` : 'Cannot create tampered copy.');
    }
  };

  const verifyReceipt = async () => {
    if (!clientRef.current || !runtimeReady || !receiptText.trim()) return;
    setBusy(true);
    clearResult();
    onNotice('Running the same bundled verifier against the loaded receipt…');
    try {
      const reply: BridgeReply = await clientRef.current.verify(receiptText);
      const report = reply.report as ReceiptVerification | undefined;
      if (!reply.ok || !report) {
        const message = reply.error?.message ?? 'The verifier returned no report.';
        setBridgeError(message);
        onNotice(`Receipt verification failed closed: ${message}`);
        return;
      }
      setVerification(report);
      onNotice(
        report.valid
          ? 'Receipt passed the same-runtime structural and hash verifier.'
          : 'Receipt failed verification. Inspect the failed checks and errors below.',
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setBridgeError(message);
      onNotice(`Receipt verification failed closed: ${message}`);
    } finally {
      setBusy(false);
    }
  };

  const clearReceipt = () => {
    setReceiptText('');
    setReceiptName('No receipt loaded');
    clearResult();
    onNotice('Receipt Lab cleared.');
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(420px,0.95fr)_minmax(420px,1.05fr)]">
      <section className="border border-border bg-card/75">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <p className="eyebrow">Portable artifact input</p>
            <h2 className="mt-1 text-sm font-semibold">Receipt JSON</h2>
          </div>
          <Badge variant="outline" className="rounded-sm border-primary/30 bg-primary/5 font-mono text-[9px] text-primary">
            BROWSER-LOCAL
          </Badge>
        </div>

        <div className="border-b border-border p-3">
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" className="min-h-10 rounded-none" onClick={loadLatest} disabled={!latestBundle || busy}>
              <FileJson data-icon="inline-start" /> Load latest run
            </Button>
            <Button type="button" variant="outline" className="min-h-10 rounded-none" onClick={() => inputRef.current?.click()} disabled={busy}>
              <Upload data-icon="inline-start" /> Open JSON file
            </Button>
            <input ref={inputRef} type="file" accept="application/json,.json" className="hidden" onChange={(event) => void loadFile(event)} />
            <Button type="button" variant="outline" className="min-h-10 rounded-none" onClick={tamperWithCopy} disabled={!summary || busy}>
              <FlaskConical data-icon="inline-start" /> Tamper copy
            </Button>
            <Button type="button" variant="ghost" className="min-h-10 rounded-none" onClick={clearReceipt} disabled={!receiptText || busy}>
              <Trash2 data-icon="inline-start" /> Clear
            </Button>
          </div>
          <p className="mt-3 break-all font-mono text-[10px] text-muted-foreground">{receiptName}</p>
        </div>

        <div className="p-3">
          <Textarea
            aria-label="Evidence receipt JSON"
            value={receiptText}
            onChange={(event) => {
              setReceiptText(event.target.value);
              setReceiptName('Edited receipt');
              clearResult();
            }}
            spellCheck={false}
            placeholder="Load the latest run, open a downloaded bundle, or paste receipt JSON here."
            className="min-h-[520px] resize-y rounded-none border-border bg-[#050b0e] p-4 font-mono text-[11px] leading-5 text-cyan-50 shadow-inner"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border p-3">
          <p className="text-[11px] text-muted-foreground">Maximum local file size: 5 MB</p>
          <Button type="button" className="min-h-10 rounded-none" onClick={() => void verifyReceipt()} disabled={!runtimeReady || !receiptText.trim() || busy}>
            {busy ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <ShieldCheck data-icon="inline-start" />}
            Verify receipt
          </Button>
        </div>
      </section>

      <section className="border border-border bg-card/75">
        <div className="border-b border-border px-4 py-3">
          <p className="eyebrow">Independent recheck</p>
          <h2 className="mt-1 text-sm font-semibold">Verification result</h2>
        </div>

        {!verification && !bridgeError && (
          <div className="grid min-h-[650px] place-items-center p-8 text-center">
            <div className="max-w-md">
              <div className="mx-auto grid size-16 place-items-center rounded-full border border-primary/30 bg-primary/5 text-primary">
                <FileCheck2 className="size-6" />
              </div>
              <h3 className="mt-5 text-base font-semibold">Load a receipt and verify it</h3>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                The checker reconstructs the retained event hashes, trace chain, state bindings, proof and control identities, and evidence projections. Try the tamper control to see a changed artifact fail closed.
              </p>
            </div>
          </div>
        )}

        {bridgeError && (
          <div className="p-4">
            <div className="border border-rose-400/30 bg-rose-400/5 p-4 text-rose-100">
              <div className="flex items-center gap-2 text-sm font-semibold"><ShieldAlert className="size-4" /> Verification could not run</div>
              <p className="mt-2 text-xs leading-5 text-rose-100/75">{bridgeError}</p>
            </div>
          </div>
        )}

        {verification && (
          <div className="space-y-4 p-4">
            <div className={`border p-4 ${verification.valid ? 'border-emerald-400/35 bg-emerald-400/7 text-emerald-100' : 'border-rose-400/35 bg-rose-400/7 text-rose-100'}`}>
              <div className="flex items-start gap-3">
                {verification.valid ? <CheckCircle2 className="mt-0.5 size-5 shrink-0" /> : <XCircle className="mt-0.5 size-5 shrink-0" />}
                <div>
                  <h3 className="text-sm font-semibold">{verification.valid ? 'Receipt structure and bindings verified' : 'Receipt rejected'}</h3>
                  <p className="mt-1 text-[11px] leading-5 opacity-75">
                    {verification.valid
                      ? 'Every retained check passed inside the same bundled runtime.'
                      : 'At least one required hash, chain, identity, or projection check failed.'}
                  </p>
                </div>
              </div>
            </div>

            {summary && (
              <div className="grid grid-cols-2 gap-px border border-border bg-border sm:grid-cols-4">
                {[
                  ['PROBLEM', summary.problemId],
                  ['STATUS', summary.terminalStatus],
                  ['EVENTS', String(summary.events)],
                  ['BYTES', summary.bytes.toLocaleString()],
                ].map(([label, value]) => (
                  <div key={label} className="min-w-0 bg-card p-3 text-center">
                    <p className="font-mono text-[8px] text-muted-foreground">{label}</p>
                    <p className="mt-1 truncate font-mono text-[11px] text-primary" title={value}>{value}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="grid grid-cols-3 gap-px border border-border bg-border">
              {[
                ['CHECKS', checks.length],
                ['PASSED', passedChecks],
                ['FAILED', failedChecks],
              ].map(([label, value]) => (
                <div key={String(label)} className="bg-card p-3 text-center">
                  <p className="font-mono text-[8px] text-muted-foreground">{label}</p>
                  <p className="mt-1 font-mono text-lg text-primary">{value}</p>
                </div>
              ))}
            </div>

            {(verification.errors?.length ?? 0) > 0 && (
              <div>
                <p className="eyebrow">Errors</p>
                <ul className="mt-2 space-y-2">
                  {verification.errors?.map((error, index) => (
                    <li key={`${index}-${error}`} className="border border-rose-400/25 bg-rose-400/5 px-3 py-2 font-mono text-[10px] leading-5 text-rose-100">{error}</li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="eyebrow">All checks</p>
                <Badge variant="outline" className="rounded-sm font-mono text-[9px]">{verification.schema_version ?? 'cncm.verification/0.1'}</Badge>
              </div>
              <div className="max-h-[430px] overflow-auto border border-border bg-muted/10">
                {checks.map((check, index) => (
                  <div key={`${index}-${check.name}`} className="flex items-center justify-between gap-3 border-b border-border/70 px-3 py-2 last:border-0">
                    <code className="min-w-0 break-all text-[10px] text-cyan-50">{check.name ?? `check-${index + 1}`}</code>
                    {check.passed ? <CheckCircle2 className="size-3.5 shrink-0 text-emerald-300" /> : <XCircle className="size-3.5 shrink-0 text-rose-300" />}
                  </div>
                ))}
              </div>
            </div>

            <div className="border border-amber-400/25 bg-amber-400/5 p-3">
              <div className="flex items-center gap-2 text-[11px] font-medium text-amber-200"><ShieldAlert className="size-3.5" /> Claim boundary</div>
              <p className="mt-1.5 text-[10px] leading-5 text-muted-foreground">
                This verifies retained structure and internal bindings. It does not authenticate storage, prove that packet assertions are true, or award CRQS, capability, evidence-tier, or deployment-authority grades.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
