# CAS Forex Fit Audit - CAS PCBA Engineer Book

Date: 2026-06-20

Source reviewed:

- `book/CAS_PCBA_Engineer/CAS_PCBA_Engineer.pdf`
- Markdown source in `book/CAS_PCBA_Engineer/`

## Verdict

The CAS PCBA Engineer book can help CAS Forex, but the useful path is not to let PCBA, CJT, CCDL, or CCB boards create broker `ACCEPT`.

The useful path is a bounded engineering layer:

- CCDL-style board specs for gate schematics and versioned static checks.
- CJT diagnostics for explaining forecast disagreement, weak edge, macro shock, drawdown overload, broker mismatch, and model drift.
- CCB reference boards as evidence sidecars: CSB, COB, CDAB, CMB, CPMB.
- Chapter 23 fault-injection discipline for fail-closed tests.
- Chapter 25 deployment ladder and Evidence Packet discipline for paper/live proof gates.
- Chapter 26 governance package shape: schematic, BOM, test report, evidence packets.

Current claim boundary stays unchanged for money flow:

- CAS Forex live trading remains `NOT LICENSED`.
- PCBA/CJT/CCDL must not create broker `ACCEPT`.
- PCBA/CJT/CCDL may explain, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or contribute to `LIVE_LOCKED`.

## What Already Fits The Current Build

CAS Forex already contains several book-aligned pieces.

| Book concept | Book source | Current CAS Forex fit |
|---|---|---|
| CCDL/CJT design-rule checks | `Appendix_C_CCDL_Language_Reference.md:439` | `cas-forex/cas_forex/cjt_compiler.py` and `cas-forex/cas_forex/crc_linter.py` already run CJT/CRC validation passes. |
| CCB reference boards | `Appendix_D_CCB_Reference_Designs.md` | `cas-forex/cas_forex/ccb_designs.py:30` defines CSB/COB/CDAB/CMB/CPMB reference designs. |
| Evidence packets | `Chapter_25_Production_Deployment.md:65` | `cas-forex/cas_forex/evidence_store.py:13` and `schemas/evidence.py` already support local hash-chain evidence. |
| Post-trade reconciliation | `Chapter_25_Production_Deployment.md:65` | `cas-forex/cas_forex/post_trade.py:15` reconciles broker state and can trigger `LIVE_LOCKED`. |
| Forecast harness before execution | `Chapter_23_Testing_Cognitive_Circuits.md:11` | `cas-forex/cas_forex/forecast/harness.py:23` suppresses weak, unavailable, unstable, or disagreeing model signals before CAS audit. |
| Live lock controller | `Chapter_25_Production_Deployment.md:144` | `cas-forex/cas_forex/verifier/live_lock.py:16` persists `LIVE_LOCKED` and requires signed unlock evidence. |
| Hidden/encoded prompt screening | PCBA safety and prompt-injection chapters plus current CAS work | `cas-forex/cas_forex/pcba_prompt_injection.py:69` normalizes zero-width, HTML, URL, and base64 surfaces for shadow detection. |

## Highest-Value Ideas To Add To CAS Forex

### 1. CCDL Board Spec Layer For The Forex Pipeline

Implement a `ccdl` module that can express the current CAS Forex pipeline as a board:

```text
ForecastHarness -> CASCompilerGate -> RiskGate -> MacroGate -> MarketGate -> ExecutionGate -> BrokerBridge -> PostTradeHarness
```

Each stage should have:

- named input/output terminals
- gate type
- expected status outputs
- allowed failure route
- test points
- evidence fields
- version hash

This should stay static/design-time. A passing CCDL/CRC check means "well-formed board", not "safe to trade".

### 2. Add Forex-Specific Test Points To Evidence Packets

The book's evidence-packet model maps cleanly to CAS Forex if each trade gets fixed test points:

- `TP1_forecast`: model signals, baselines, agreement, intervals
- `TP2_cas`: CAS compiler valid/admissible/descent result
- `TP3_risk_macro_market`: drawdown, exposure, macro event, spread/session/ATR
- `TP4_execution`: duplicate/slippage/stop-distance/broker mode/order outcome
- `TP5_post_trade`: broker ticket reconciliation, PnL, slippage, mismatch, margin, disconnect

These should be recorded on every `PROPOSED`, `SUPPRESSED`, `FLAG_FOR_HUMAN_REVIEW`, `ACCEPTED`, `EXECUTED`, `REJECTED`, `CLOSED_WIN`, `CLOSED_LOSS`, and `LIVE_LOCKED` packet.

### 3. Use CSB As The Safety/Lock Explanation Board

The CSB chapter is directly relevant to CAS Forex risk control. Map it this way:

- pre-amp: expand hidden/encoded risk surfaces in forecast rationale, market context, and broker response
- differential pair: compare attraction to trade vs aversion/risk signal
- cascade: categorize, evaluate, decide
- mux/fuse: route to pass, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or `LIVE_LOCKED`
- feedback: only slow, reviewed, next-session configuration changes

This can improve explainability of suppressions and locks without authorizing trades.

### 4. Use CDAB For Model And Baseline Disagreement

The CDAB chapter maps strongly to Forecast Harness.

Use CDAB diagnostics when:

- TimeGPT vs technical vs Chronos/TimesFM disagree
- raw model beats neither baseline nor no-trade
- one model is highly confident but unsupported
- two timeframe styles disagree

Route:

- small divergence: note only
- material divergence: `SUPPRESS`
- high-confidence single-model divergence: `FLAG_FOR_HUMAN_REVIEW`
- drift after closed trades: `LIVE_LOCKED`

### 5. Use CMB For Trade Memory And Lacunarity

The CMB chapter is useful for deciding where the system lacks evidence.

Add memory/lacunarity diagnostics across:

- symbol
- session
- timeframe
- macro regime
- spread/volatility regime
- model combination
- gate outcome
- trade outcome

This should help the harvester say "we have no proven evidence in this region" rather than over-generalizing from thin backtests.

### 6. Use CPMB For Risk Budgeting

The CPMB energy-budget idea maps to forex risk budgets.

Implement a budget ledger for:

- risk per trade
- daily drawdown budget
- weekly drawdown budget
- correlated exposure
- model uncertainty budget
- evidence-write failure budget
- broker-health budget

When budget is exhausted, route to `SUPPRESS` or `LIVE_LOCKED`. Do not let this become a reason to increase size.

### 7. Use COB For Session And Regime Rhythm

COB is useful for recurring market rhythms:

- London/New York overlap
- Asia session
- pre/post macro release windows
- high-volatility clusters
- repeated stop-out cycles
- repeated model-drift cycles

This can improve MTFA and macro gates by marking unstable rhythm/entrainment. It should not predict profit by itself.

### 8. Add Fault-Injection Tests From Chapter 23

Add explicit tests that break safety pieces and prove fail-closed behavior:

- kill CAS compiler bridge: must not `ACCEPT`
- corrupt EvidenceStore write: paper/live must `LIVE_LOCKED`
- stale broker heartbeat with open trade: `LIVE_LOCKED`
- suppress macro calendar provider: no blind pass during high-impact window
- unbalance model ensemble: `SUPPRESS` or `FLAG_FOR_HUMAN_REVIEW`
- remove risk snapshot: no unlock
- force wrong broker symbol/volume: `LIVE_LOCKED`

### 9. Add A Circuit Registry

Chapter 25's rollback logic suggests adding a registry for:

- CCDL board version
- gate config version
- macro calendar version
- risk policy version
- broker mode/legal gate version
- forecast harness version
- PCBA/CJT diagnostic version

Every Evidence Packet should pin the version hashes. Rollback should select a previous signed version for the next session only.

## What Not To Implement As Authority

Do not implement these as trade-authority paths:

- CCDL compiler pass -> broker `ACCEPT`
- CJT region active/saturation -> broker `ACCEPT`
- CSB green path -> broker `ACCEPT`
- CDAB agreement -> broker `ACCEPT`
- CMB memory match -> broker `ACCEPT`
- CPMB budget available -> broker `ACCEPT`
- COB rhythm lock -> broker `ACCEPT`

The only broker `ACCEPT` path should remain the existing CAS Forex auditor/broker path after Forecast Harness, CAS compiler, risk, macro, market, execution, evidence, paper/live, legal/account, and human-unlock gates.

## Recommended Implementation Order

1. Add `ccdl_forex.py` with a static Forex pipeline board spec and version hash.
2. Add test-point fields or a `test_points` map to `ForexEvidencePacket`.
3. Emit TP1-TP5 in backtest and post-trade paths.
4. Add CDAB diagnostics to Forecast Harness disagreement and weak-edge paths.
5. Add CMB lacunarity diagnostics to backtest/paper proof reports.
6. Add CPMB budget ledger to RiskGate/LiveLock evidence.
7. Add COB session/rhythm diagnostics to MacroGate/MarketGate/MTFA.
8. Add fault-injection tests proving every missing/broken safety component fails closed.
9. Add a signed circuit registry and rollback command.

## Bottom Line

The book is useful. It gives CAS Forex a stronger design language for gates, evidence, diagnostics, rollback, and governance.

It does not change the live-money boundary. CAS Forex live trading remains `NOT LICENSED`, and PCBA/CJT/CCDL must remain diagnostic/evidence layers unless separate proof gates license a specific claim.
