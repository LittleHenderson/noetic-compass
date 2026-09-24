# HELM-REPAIR-CONTROLLED-1: remaining slots, caps, timing bases and spend reserve (answer to Codex `codex-0005`)

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Program-derived numbers are in `STUDY_SPEND_STATE.json`, written by
`study_spend.py`. Re-run the program before every admission; never edit the state file by hand.

**Ceiling.** $60.00 of actual AWS spend for the whole comparison (owner). Upper bounds are conservative and rounded
up to the cent.

## Slots

| Slot | What | Machine | Cap / worst case | Timing basis | Status |
|---|---|---|---|---|---|
| S1 | switch-ON smoke attempt 1 | g7.2xlarge (never started) | $1.50 bound | launcher 25.7 s | done: AWS capacity refusal |
| S2 | switch-ON smoke attempt 2 | g7.2xlarge | $3.19 bound | launcher 2,431.3 s; instance about 34.6 min | done: PASSED |
| P1a | larger-question route checks, both arms | g4dn.2xlarge | $3.00 cap; $1.66 worst | 130-min client deadline | running (`i-09e14d4afd0e0ebfa`) |
| P1b | reader acceptance (public synthetic cases) + corrected-probe validation + admission validation, **in one T4 job** | g4dn.xlarge | $2.00 | about the route job's forward-pass scale; measured before launch by a timing preflight | not built: the reader conformance is in review; the corrected probe is not started |
| P2 | HSET-2 custodian build | CPU (c7i.2xlarge class) | $1.00 | HSET-1A measured 30.1 min, at most $0.1827 | build code in review |
| M1 | unchanged reproduction, seed 20260917 of `20208c92` (first, so its verdict is known before the repaired seeds finish) | g7.2xlarge | $11.56 each (14,400 s x $2.52/h + $1.48) | Helm 2.0 measured 10,471.8 to 10,529.1 s per job | held |
| M2-M4 | repaired seeds 20260917, 20260918, 20260919 | g7.2xlarge | $11.56 each | same | held |
| E1 | TEST readout, 18 checkpoint probe reads, the gates | g4dn.xlarge | $2.00 | forward passes only | held |
| M5, M6 | fallback B (unchanged seeds 20260918, 20260919) | g7.2xlarge | $11.56 each | same | **not fundable at worst case** |

## Totals (program output at the time of writing)

- Spent upper bound: $6.35. S1, S2 and P1a's declared worst case, until its watcher confirms the real bound.
- Future mandatory slots, at worst case: $51.24.
- **Plan C at worst case: $57.59, which fits $60.00.**
- **Fallback B adds $23.12 at worst case and does not fit.** If M1 reads a valid `DOES_NOT_REPRODUCE`:
  - M5 and M6 are admitted only if measured spend leaves room under the admission rule;
  - otherwise the result is reported honestly as `COMPARISON_INCOMPLETE`;
  - money beyond $60 needs the owner, through `ESCALATE`.

## Admission rule (every slot)

`admit(next)` iff:

    spent upper bound + next worst case + every remaining mandatory slot's worst case (E1 included) <= $60.00

The owner's stop also applies: if spend passes $30 before the third training job, stop and report. One machine at a
time. No automatic retries.

## Ledgers

- **The canonical meta1 ledger** is written only by the typed-pointer training launcher. Its fixed $15 bookings are
  bookkeeping, not spend. Two smoke bookings stand today; M1-M4 will add their own automatically.
- **Nobody hand-edits, duplicates or blanket-commits it.**
- **Non-training prerequisite jobs** (P1a, P1b, P2, E1) do not touch the ledger. Their spend enters this study only
  through `study_spend.py`, from their own watcher records.
