import { useState } from 'react';
import type { StageResult } from '../../api/types';
import { PIPELINE_STAGES } from '../../lib/constants';
import { researchTierLabel } from '../../lib/researchTier';

const STAGE_RULES: Record<string, string> = {
  input_analyzer: 'parse(text) → TokenStream',
  rpm_gate: 'evalChain_m(σ) for m ∈ {1..7}',
  dial_adjustment: 'adjust(dials, input) → adjusted',
  base_llm_call: 'generate(prompt, system) → response',
  operator_scoring: 'score(CO-k, response) for k ∈ {0..9}',
  domain_coherence: 'DCI = min(avg_d) / max(avg_d)',
  inversion_scan: 'scan(response, axes) for 7 axes',
  output_gate: 'compute_nccs(sub-scores) → composite',
};

function summarizeStage(stage: StageResult, index: number): { rule: string; output: string; reduction: string } {
  const name = stage.stage;
  const rule = STAGE_RULES[name] ?? name;
  const data = stage.data ?? {};

  if (stage.error) {
    return { rule, output: `FAILED: ${stage.error}`, reduction: `${PIPELINE_STAGES[index]} failed` };
  }

  switch (name) {
    case 'input_analyzer': {
      const tokens = (data.token_count as number) ?? '?';
      return { rule, output: `${tokens} tokens`, reduction: `Input validated: ${tokens} tokens processed` };
    }
    case 'operator_scoring': {
      const scores = data.scores as number[] | undefined;
      if (scores?.length) {
        const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
        return { rule, output: `10 scores, mean=${avg.toFixed(3)}`, reduction: `Operator scoring: mean ${avg.toFixed(3)}` };
      }
      return { rule, output: 'scores computed', reduction: 'Operator scoring complete' };
    }
    case 'domain_coherence': {
      const dci = (data.dci as number) ?? 0;
      return { rule, output: `DCI=${dci.toFixed(3)}`, reduction: `Domain coherence index: ${dci.toFixed(3)}` };
    }
    case 'rpm_gate': {
      const comp = (data.rpm_completeness as number) ?? 0;
      return { rule, output: `RPM=${(comp * 100).toFixed(1)}%`, reduction: `RPM completeness: ${(comp * 100).toFixed(1)}%` };
    }
    case 'inversion_scan': {
      const stealth = (data.stealth_resistance as number) ?? 0;
      return { rule, output: `stealth=${stealth.toFixed(3)}`, reduction: `Stealth resistance: ${stealth.toFixed(3)}` };
    }
    case 'output_gate': {
      const comp = (data.composite as number) ?? 0;
      const cert = (data.certification as string) ?? '?';
      const tier = researchTierLabel(cert);
      return { rule, output: `NCCS=${comp.toFixed(1)}, ${tier}`, reduction: `Final: ${comp.toFixed(1)} (${tier})` };
    }
    default:
      return { rule, output: 'ok', reduction: `${PIPELINE_STAGES[index] ?? name} completed` };
  }
}

export function TraceViewer({ stages }: { stages: StageResult[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs font-medium text-accent-teal hover:text-accent-cyan transition-colors min-h-[44px]"
      >
        <svg
          width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        >
          <path d="M4 2l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {expanded ? 'Hide Evaluation Trace' : 'Show Evaluation Trace'}
      </button>

      {expanded && (
        <div className="mt-3 rounded-lg border border-white/[0.06] bg-dark-800/80 overflow-hidden">
          <div className="px-4 py-2 border-b border-white/[0.06] bg-white/[0.02]">
            <p className="text-[10px] font-mono text-slate-500">
              CAS Assessment Derivation — {stages.length} stages
            </p>
          </div>
          <div className="p-4 space-y-0 font-mono text-[11px] overflow-x-auto">
            {stages.map((stage, i) => {
              const { rule, output, reduction } = summarizeStage(stage, i);
              const success = stage.success;
              return (
                <div key={i} className="group">
                  {/* Step header */}
                  <div className="flex items-start gap-3 py-2">
                    <span className="text-slate-600 w-14 shrink-0 text-right">
                      Step {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-semibold ${success ? 'text-slate-200' : 'text-red-400'}`}>
                          {PIPELINE_STAGES[i] ?? stage.stage}
                        </span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded ${success ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                          {success ? 'OK' : 'FAIL'}
                        </span>
                      </div>
                      <div className="text-slate-500">
                        <span className="text-slate-600">Rule: </span>
                        <span className="text-accent-teal/70">{rule}</span>
                      </div>
                      <div className="text-slate-500 mt-0.5">
                        <span className="text-slate-600">Result: </span>
                        <span className={success ? 'text-slate-300' : 'text-red-400'}>{output}</span>
                      </div>
                      <div className="text-slate-500 mt-0.5">
                        <span className="text-slate-600">→ </span>
                        <span className="text-slate-400">{reduction}</span>
                      </div>
                    </div>
                  </div>
                  {/* Divider */}
                  {i < stages.length - 1 && (
                    <div className="ml-[4.5rem] border-l border-white/[0.04] h-2" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
