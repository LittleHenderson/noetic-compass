# CAS Forex UI — Handoff 2026-06-22

## One-command start
```
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui && npm run dev
# → http://localhost:5174
```

## What was built today
A self-contained React 18 + TypeScript + Vite proof cockpit — 8 live pages, 0 placeholders.

### Page inventory

| Page | Data source | Key content |
|---|---|---|
| Proof | Real evidence fixtures | Paper proof progress, backsolve (16,800 scenarios/0 viable), MT5 receipt (BROKER_API_VERIFIED), walk-forward (3/3 positive) |
| Audit | Daily bundle | 10-stage pipeline (NOT_RUN on Gates 0+3), 18 event context labels with priority/vol |
| Dashboard | strategy_leads.json | 4 strategy leads with headline results + open gates |
| Trade | Daily bundle | Symbol/timeframe/style selector, proposal preview, forecast harness, CAS expression |
| Adaptive | AdaptiveCockpitPayload (optional) | ADD_TO_WINNER/TIGHTEN_STOP/CLOSE_BASKET actions, basket state, memory snapshots |
| History | Condition tally + temporal lacunarity | D1/H1 buckets, S1-Y1 gap map (0.875 gap fraction) |
| Settings | OwnerControlState | 6 autonomy modes, max concurrent 15, compounding thresholds, legal gates |
| PCBA/CJT | Static | 5 reference boards, 5 CJT features (all NOT_READY), 22-component catalog, LLM optimizer guard |

### File map
```
cas-forex/ui/src/
├── App.tsx              # State wires all 8 pages; imports from fixtures
├── App.css              # ~1600 lines — all component styles
├── index.css            # Dark theme CSS variables
├── types/evidence.ts    # ~340 lines — ALL TypeScript interfaces
├── data/fixtures.ts     # ~440 lines — static fixtures + real evidence
├── components/          # Shell, ModeBanner, GlassPanel, StatusChip, EvidenceHashRow, LockReasonList
└── pages/               # ProofPage, AuditPage, DashboardPage, TradePage, AdaptivePage, HistoryPage, SettingsPage, PcbaPage
```

### Key types (`evidence.ts`)
`DashboardState` carries: uiReadiness, dailySchedule, dailyBundle, adaptive?, ownerControl?, mtHistory?, strategyLeads?, backsolve?, conditionTally?, walkForward?, mt5Receipt?

### Claim boundary (DO NOT BREAK)
- Live trading, broker ACCEPT, auto-deposit, debit/card/bank, payout automation = NOT LICENSED everywhere
- 5 bundles = multi-day proof maturity; 30/30 paper days = deployment gate
- Trading edge = OPEN

### Verification
```
npx tsc --noEmit    # clean
npx vite build       # 43 modules, 228KB JS, 65KB gzip
```

## Remaining gaps

1. **Live API wiring** — UI reads static fixtures; connect to `/api/forex/*`
2. **Adaptive cockpit JSON generation** — run `run_adaptive_cockpit.py`
3. **30-day paper proof ledger viewer**
4. **Chart integration** — no charting lib yet
5. **LLM optimizer interactive queue**
6. **Condition Lab interactive view**
