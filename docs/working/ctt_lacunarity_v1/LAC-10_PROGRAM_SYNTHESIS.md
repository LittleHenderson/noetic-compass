# LAC-10 — Program synthesis: what CAS-LAC-001 established (2026-10-24)

Status: **closing synthesis for Phases 0–4.** Phase 5 (shadow-mode integration) was **not entered**, because no
measure passed the Phase 4 gate. That is the correct outcome under the directive's own rules, not an omission.

## 1. The answer to the central question

**Can CAS lacunarity diagnose a HELM weakness, select a repair, and improve outcomes?**

- **Diagnose a weakness: partly.** The per-cell Noetic error decomposition detects a real, replicable pattern: cells
  with fewer training rows carry higher held-out error at both checkpoints, in two independent source sets, in all
  three seeds.
- **Add value beyond simpler baselines: no.** The pattern is the exposure count itself. The lacunarity scalar (`Λ`)
  was small (0.009832–0.070758 across all runs) and moved in inconsistent directions. It added nothing.
- **Select a repair that improves outcomes: no.** The preregistered targeted intervention failed 2 of 3 conditions:
  it made the targeted cells worse (+0.019028) and cost generation quality (−0.024067).
- **So the full loop — measure, diagnose, repair, verify — does not close** with the measures tested here.

## 2. What is established, with status

| Finding | Status | Artifact |
|---|---|---|
| The existing CAS formulas (state, fractal, domain, drive, RPM resolution) compute what they claim | Mathematically Verified | `LAC-03A`, 30 checks |
| The formula mirror exists in Rust and Python; no test proves they agree | Implemented, not cross-tested | `LAC-01` |
| Held-out Noetic error rises from step 1,000 to 6,000 | Replicated, 3/3 seeds, 2 sources | `LAC-00` §10, `LAC-05` |
| Low-exposure cells carry higher error at both checkpoints | Replicated, 3/3 seeds, 2 sources | `LAC-05` |
| High-exposure cells worsen more | **NOT replicated** (1/3, then 2/3) | `LAC-00` §10 |
| `Λ` adds information beyond exposure | **NOT DEMONSTRATED** | `LAC-05` §2.3 |
| Targeted replay repairs the weak cells | **FAILED** | `LAC-07` result |
| More training improves generated replies | Replicated (3 arms beat baseline; earlier 3 seeds) | `LAC-07` §6, `GENERATION_COMPARISON_RESULT` |
| Recipe and RPM lacunarity | `PROPOSED` — formulas defined, no code, no labels to evaluate | `LAC-02`, `LAC-03A` |

## 3. The failure that matters most

The diagnostic said "these cells are weak". The intervention gave those cells more examples. The cells got **worse**,
not better, and reply quality dropped against the undirected control.

A likely reading (HYPOTHESIS, not tested): the cells are weak because they are intrinsically harder, not because
they are under-trained. Adding rows to hard cells may sharpen the model on their surface forms while displacing the
signal that generalises. The placebo anomaly — random labels giving the best Noetic error — points the same way: it
was the *label noise*, not the targeting, that changed the outcome.

## 4. What the program did not do, and why

- **Recipe and RPM evaluation:** no labelled data describes ingredient structures or prerequisite graphs per row.
  Evaluating them needs a structural export that does not exist yet. Blocked on data, recorded as such.
- **Combined measures (LAC-06):** the directive requires individual evaluation first. With one measure failing
  incremental value and the others unevaluated, there is nothing honest to combine.
- **Engineering interface (LAC-08) and controller (LAC-09):** gated on a validated measure. None passed.
- **Phase 5 shadow mode:** not entered, same reason.

## 5. What would change the answer

1. A labelled structure set for recipes or RPM — the only route to testing those families.
2. A measure that predicts failure **beyond** exposure — the Noetic family does not have one.
3. An intervention that beats its undirected and placebo controls — the first attempt did not.

## 6. Cost

- Historical training: ~2.40 USD (before this program).
- This program: **0 USD** for Ranks 1–5. The 3–5 USD approved for a second source was not needed (the source was
  built from the grammar), and the 1.00 USD approved for the intervention was not spent (local diagnostic).

## 7. One result worth carrying forward

The strongest finding in the whole arc is not a lacunarity measure. It is that **the later checkpoint predicts worse
but writes better** (+0.121088, +0.106669, +0.122451 on the generation composite, 3 of 3 seeds), while held-out
Noetic error rises. Training longer buys reply quality and costs notation generalisation. That trade-off is the
concrete phenomenon any future structural diagnostic should be asked to explain.
