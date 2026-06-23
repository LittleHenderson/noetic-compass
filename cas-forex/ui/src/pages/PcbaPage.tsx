/* ── CAS Forex — PCBA/CJT Diagnostics ── */
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";

const BOARDS = [
  { id: "ccb-csb", name: "Cognitive Safety Board", purpose: "Structural safety firewall diagnostic", components: ["OP_AMP","FUSE","MUX","REGULATOR","CIRCUIT_BREAKER","SCHMITT_TRIGGER"] },
  { id: "ccb-dab", name: "Differential Amplifier Board", purpose: "Cross-domain signal comparison & drift detection", components: ["OP_AMP","TRANSFORMER","ADC","DAC","BRIDGE_RECTIFIER","VARACTOR"] },
  { id: "ccb-cmb", name: "Cognitive Memory Board", purpose: "Memory/storage architecture diagnostic", components: ["CAPACITOR","INDUCTOR","VARACTOR","PHOTODIODE","CRYSTAL_OSCILLATOR","RELAY"] },
  { id: "ccb-cpmb", name: "Power Management Board", purpose: "Drive homeostasis & regulation diagnostic", components: ["REGULATOR","FUSE","CIRCUIT_BREAKER","BRIDGE_RECTIFIER","RESISTOR","DIODE"] },
  { id: "ccb-ccb", name: "Cognitive Circuit Board", purpose: "Interconnect & routing architecture", components: ["TRACE","VIA","MUX","DEMUX","LOGIC_GATE","RELAY"] },
];

const CJT = [
  { f: "PRODUCTION_COMPILER_SYNTAX", detail: "Grammar, parser, IR roundtrip, semantics review — all pending" },
  { f: "LIVE_TRADING_PERMISSION_PATH", detail: "12-month backtest, 30-day paper proof, legal gates — all pending" },
  { f: "COMPILER_ENFORCED_SAFETY_CLAIM", detail: "Formal safety semantics, negative eval, red team — all pending" },
  { f: "PROMPT_INJECTION_PREVENTION_CLAIM", detail: "Matched eval, hidden text control, false positive floor — all pending" },
  { f: "GOVERNANCE_REGULATORY_PROOF_CLAIM", detail: "Regulatory mapping, legal review, audit retention — all pending" },
];

const COMPONENTS = [
  ["RESISTOR","constraint / current limiter"],["CAPACITOR","memory/storage sidecar"],["INDUCTOR","momentum/habit sidecar"],
  ["DIODE","one-way transition guard"],["TRANSFORMER","domain impedance matcher"],["OP_AMP","feedback amplifier"],
  ["OSCILLATOR","rhythm/habit cycle"],["LOGIC_GATE","boolean prerequisite"],["MUX","routing selector"],
  ["DEMUX","routing splitter"],["REGULATOR","homeostasis/limit"],["FUSE","safety cutoff"],
  ["CIRCUIT_BREAKER","resettable safety cutoff"],["TRACE","transition/interconnect"],["VIA","cross-domain interconnect"],
  ["VARACTOR","context-sensitive memory"],["RELAY","conditional enablement"],["SCHMITT_TRIGGER","hysteresis decision"],
  ["PHOTODIODE","feedback-to-activation"],["CRYSTAL_OSCILLATOR","stable rhythm reference"],["ADC","implicit-to-explicit"],["DAC","explicit-to-action"],
];

export function PcbaPage() {
  return (
    <div className="pcba-page">
      <GlassPanel title="PCBA Reference Boards" subtitle="5 cognitive circuit board diagnostic designs">
        <div className="pcba-boards-grid">
          {BOARDS.map(b => (
            <div key={b.id} className="pcba-board-card">
              <div className="pcba-board-header"><code className="pcba-board-id">{b.id}</code><StatusChip label="DIAGNOSTIC" variant="info" size="sm" /></div>
              <div className="pcba-board-name">{b.name}</div>
              <div className="pcba-board-purpose">{b.purpose}</div>
              <div className="pcba-board-components">{b.components.map(c => <span key={c} className="pcba-component-chip">{c}</span>)}</div>
            </div>
          ))}
        </div>
        <div className="pcba-claim-note">All PCBA boards are claim-bounded diagnostics. No board creates broker ACCEPT, live trading, or payment authority.</div>
      </GlassPanel>

      <GlassPanel title="CJT Production Readiness" subtitle="5 features — all NOT_READY" variant="warning">
        <div className="cjt-features">
          {CJT.map(f => (
            <div key={f.f} className="cjt-feature-row">
              <div className="cjt-feature-header"><code className="cjt-feature-name">{f.f}</code><StatusChip label="NOT_READY" variant="danger" size="sm" /><span className="cjt-checks mono">0/? checks</span></div>
              <div className="cjt-feature-detail">{f.detail}</div>
              <div className="cjt-progress-track"><div className="cjt-progress-fill" style={{width:"0%"}} /></div>
            </div>
          ))}
        </div>
      </GlassPanel>

      <GlassPanel title="LLM Optimizer Guard" subtitle="CASPCBAOptimizerGuard — RESEARCH_QUEUE only">
        <div className="dashboard-grid-3col">
          <div className="metric-stack"><Metric label="Guard" value="ACTIVE"/><Metric label="Prompt Injection" value="PASS"/></div>
          <div className="metric-stack"><Metric label="Research Queue" value="0" mono/><Metric label="Flagged" value="0" mono/><Metric label="Rejected" value="0" mono/></div>
          <div className="metric-stack"><Metric label="Can Create Broker ACCEPT" value="false" danger/><Metric label="Can Unlock Live" value="false" danger/></div>
        </div>
        <div className="optimizer-detail">No LLM optimizer proposals submitted yet. Guard evaluates prompt injection surfaces, verifies evidence refs, and enforces RESEARCH_QUEUE / FLAG_FOR_HUMAN_REVIEW / REJECT boundaries.</div>
      </GlassPanel>

      <GlassPanel title="PCBA Component Catalog" subtitle="22 cognitive circuit components">
        <div className="component-catalog-grid">
          {COMPONENTS.map(([n,r]) => <div key={n} className="component-catalog-item"><code className="component-name">{n}</code><span className="component-role">{r}</span></div>)}
        </div>
      </GlassPanel>

      <GlassPanel title="Production Gates" variant="danger">
        <div className="gate-grid">
          {["PCBA Production","CJT Compiler","Safety Claims","Prompt Injection Prevention","Governance/Regulatory","LLM Optimizer"].map(l => <div key={l} className="gate-item"><div className="gate-item-header"><span className="gate-item-label">{l}</span><StatusChip label="NOT LICENSED" variant="danger" size="sm"/></div><div className="gate-item-detail">Diagnostic only — no live authority</div></div>)}
        </div>
      </GlassPanel>
    </div>
  );
}

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return <div className="dashboard-metric"><span className="field-label">{label}</span><span className={`field-value ${mono?"mono":""}`} style={{color:danger?"var(--danger)":undefined}}>{value}</span></div>;
}
