# Post-Mortem: −$55,069 on the Hugosway Demo Account (June–July 2026)

All numbers cross-validated against the sha256-reconciled ledger
(`runtime/mt5-account-growth.json`, zero residual to balance $44,930.73 on
$100,000 deposited). Per-deal analysis covers 1,721 of 1,723 closed positions
(gross price P&L ties exactly at −$53,773.77). Demo account; no real money
moved; live was never licensed.

## The headline: the proof strategy never failed — it barely ran

The plan of record (`index_tsmom_126_d1`) is D1 signals, US30/NAS100 only,
max 3 paper trades/day — a structural ceiling of ~90 trades in 30 days. What
actually traded was the **autonomous M1 scalp/WASTE paper-learning lane**:
on 2026-07-02 alone the waste-runner audit shows 2,185 EXECUTE decisions with
timeframes M1=2,081, H1=130, D1=4. Commit 258170c5 (2026-07-04) had promoted
the connected HugosWay demo terminal to be the primary paper-entry bridge, so
"paper learning" executed real orders on the demo account at scalp frequency
(median hold 14.3 minutes). D1 is not even a supported entry timeframe in the
dispatch lane (`ai_control_surface.py:46`).

## Where the money went

- **One catastrophic day.** 2026-07-02 = **97.6% of the loss**: 1,320
  positions opened and closed, net −$53,606. All eight other active days
  combined: −$1,313. Two burst windows did it — the 09:00 UTC hour
  (−$27,248, NAS100 LONGS at 0.42–0.50 lots) and the 15:00 hour
  (−$37,679, NAS100 SHORTS): the same loop churning the same symbol in both
  directions with ~$1,000 stops.
- **One symbol.** NAS100 net −$61,482 (112% of the total; 30.6% win rate).
  US30 made +$10,100. All FX pairs combined lost only ~$4,000.
- **The size tail.** 74 trades at ≥0.40 lots lost −$61,923 — more than the
  entire net loss. The 1,444 mid-size trades actually netted +$8,835.
- **Costs were noise.** Commission+swap = 2.35% of the loss. This was price
  P&L, not friction.

## Against the 0.65 win-probability bar — blunt

Realized win rate **35.85%** (payoff ratio 1.243 → breakeven needs 44.58%).
Expectancy **−$31.91 per trade**. Even on the calm days: 42.14%. The recorded
history is never within twenty points of the 0.65 bar the objective assumes.
Whatever supports $5,000/month, it is not in this data.

## Would today's gates have stopped it?

| Gate | Existed then? | Would it have helped? |
|---|---|---|
| `daily_loss_guard` ($50–500/day cap, enforced at the dispatch chokepoint for demo AND live) | **No — committed 2026-08-10** | **Yes, decisively** — would have capped 07-02 near the cap value |
| Same-UTC-day reconciled-ledger block | No — same commit | Yes — closes the evasion named in the 07-09 correction YAML |
| Per-trade risk cap at the stop | Yes (06-25) | **No** — it only fires when `risk_at_stop` is computable, and **all 2,634 recorded order intents were stop-less at intent level**, so it silently passed everything |
| `auto_halt` (10% drawdown latch, 3-loss check) | Yes (07-01) | **No for demo** — it gates LIVE authorization only; the demo lane never consults it. Had this sequence been live, it would have latched near −$10,000 |

Dating caveat: the guard designs appear in working docs from 07-04/07-09, but
the enforcement code first appears in the 2026-08-10 bulk commit, and the
account demonstrably kept bleeding through 07-15.

## DO NOT RESTART THE 30-DAY PROOF UNTIL

1. **Loss ceilings are lane-universal and proven to run.** Verify
   `daily_loss_guard` executes on every dispatch path (demo and live) with a
   test that pins it; decide whether `auto_halt` should also latch the paper
   lane.
2. **Lane discipline is enforced at the chokepoint, not by convention.**
   During the proof, only the proof plan may trade: strategy/magic allowlist,
   symbol allowlist (US30/NAS100), timeframe allowlist (D1), hard 3-trades/day
   ceiling. The WASTE scalp lane must be structurally unable to touch the
   receipt-bearing account while the proof runs.
3. **No stop, no order.** Every intent must carry a stop-loss so the per-trade
   risk gate can compute `risk_at_stop`; stop-less intents must fail closed.
   Also begin capturing MAE/MFE (null on every historical row).

These are gate-behavior changes and belong to a fresh session with owner
sign-off — recorded here as blockers, deliberately not rushed.

## Unknowns the data cannot answer

- Whether any blocking behavior ran in partial/uncommitted form during July
  (the bulk commit is undateable internally; the continued bleed says no, but
  that is inference).
- Risk-dial values during the 07-02/03 burst (the authority audit only begins
  07-09; 0.5%/trade is the lever default and the likely value).

Boundary: this document analyses demo-account history. It authorizes nothing,
changes no gate, and moves no money.
