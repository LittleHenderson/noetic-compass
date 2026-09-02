# CMB-P2 — P8+P9 Controlled Confirmation · PREREGISTRATION v0.1 (FROZEN)

**Authorized by owner directive, 2026-09-02.** One-shot confirmation, **not** another open
redesign round. **Additional repair after this result is PROHIBITED.**
**Parent:** `99909e8c79b9283412826fd7658956794247b777` — the exact final CMB-P1 result commit,
recorded in `PARENT_COMMIT.txt` before any file was modified.
**Status:** frozen before any held-out world is read.

---

## 1. The one question

CMB-P1 returned `PHASE_MEMORY_UNSAFE`: `P7`, `P8` and `P9` each failed **alone**. But the
*exploratory* `P8+P9` combination reached **90% / 84% / 77% of oracle accuracy** with merge
fraction `0.002 / 0.003 / 0.001`. **That result cannot count, because it had no phase-shuffled
control.**

> **Does frequency spread plus phase-history readout genuinely preserve separate thought
> chains, or did the extra machinery merely happen to score well?**

Nothing else is asked. No new mechanism is introduced.

## 2. Evaluation worlds — NEW and UNTOUCHED

CMB-P0 and CMB-P1 used world ids **0–25**. Those worlds have already revealed the promising
combination and are **excluded**. CMB-P2 uses a disjoint id range, which produces entirely
fresh seeds because each world key is derived from its id:

```
world ids   0 - 25     USED BY CMB-P0 / CMB-P1 -- EXCLUDED, never read here
world ids 500 - 505    CMB-P2 DEV        construct validity + smoke only
world ids 506 - 535    CMB-P2 HELD-OUT   30 worlds, read ONCE
```

The **world is the independent statistical unit.** All arms are paired on identical worlds and
identical queries.

```
K = 2, 3    PRIMARY   every registered decision is made here
K = 1       sanity
K = 4       DIAGNOSTIC ONLY -- its oracle failed competence in CMB-P0
```

## 3. The ten registered arms

All receive matched graph, retrieval, top-k, scoring, propagation and candidate budgets.

| Arm | What it is |
|---|---|
| `P0_SCALAR` | ordinary one-state propagation |
| `P2_INFERRED_TAG` | practical inferred-tag competitor (link graph + content) |
| `P3_GENERIC_TWO_STATE` | matched two-state non-phase control |
| `P6_SCALAR_TWO_CHANNEL` | matched second-channel control |
| `B_PHASE_FREE_CONTENT` | cheapest registered phase-free content baseline |
| `P8_ONLY` | frequency spread, **endpoint** readout |
| `P9_ONLY` | **uniform** frequency, **history** readout |
| **`P8P9_EXACT`** | registered frequency spread **+** phase-history readout |
| **`P8P9_PHASE_SHUFFLED`** | identical machinery, **phase correspondence destroyed** |
| **`P8P9_RANDOM_FREQUENCY`** | identical frequency **distribution**, random assignment |

`P1_ORACLE` is additionally computed **as a gate only**. It is handed the true chain labels,
is never a method, and appears in no success criterion — it exists solely to prove the task is
solvable at K=2 and K=3.

## 4. Frozen mechanisms — no new machinery

```
omega_i   = OMEGA * v_i / max|v|     v = low eigenvector of the normalised Laplacian
                                     OMEGA = 0.80, frozen in CMB-P1 at the converged budget
dtheta_i  = omega_i + (Kc/deg_i) * sum_j A_ij * a_j * sin(theta_j - theta_i)

history readout   coh_j   = (1/T) * sum_t cos(theta_j(t) - theta_cue(t))   -- NO free parameter
score             score_j = a_j * clamp_min(coh_j, 0)
```

`P8P9_PHASE_SHUFFLED` permutes phase-to-node correspondence at readout while keeping the
**cue's own phase** as the reference — so the control isolates chain structure instead of
destroying its own baseline. `P8P9_RANDOM_FREQUENCY` draws `omega` per node with the **same
spread** as the spectral field but no structure at all.

**Not authorized and not present:** pulse width, a free `Q`, another frequency family, another
readout repair, another dynamics repair. `Q` remains derived telemetry only.

## 5. Primary success law — `P8P9_EXACT` advances only if ALL hold

Evaluated at the **full registered propagation budget** (200 substeps), on **held-out** worlds,
at **K=2 and K=3**, under the previously frozen margins:

```
MARGIN         = 0.02      top-1
WIN_FRACTION   = 0.70      must hold in >=70% of worlds WITHIN EACH K
MERGE_MAX      = 0.15      merge_fraction = merged pairs / C(K,2)
CONTAM_MARGIN  = 0.05
```

1. beats `P0` at K=2 and K=3
2. beats `P2` at K=2 and K=3
3. beats `P3` **and** `P6`
4. beats `P8_ONLY`
5. beats `P9_ONLY`
6. beats `B_PHASE_FREE_CONTENT`
7. `merge_fraction <= 0.15` at K=2 and K=3
8. remains **stable** at the full budget — finite states, no divergence
9. does not increase wrong-chain retrieval or false admission beyond `CONTAM_MARGIN`

**No criterion may be relaxed after results are seen.**

## 6. Killer controls — operationalised in advance

```
PHASE DEPENDENCE      P8P9_PHASE_SHUFFLED must MATERIALLY LOSE the advantage.
                      Operationalised: it falls BELOW P0 -- the same standard applied to
                      every shuffle control in CMB-P0 and CMB-P1.

FREQUENCY STRUCTURE   P8P9_EXACT must MATERIALLY BEAT P8P9_RANDOM_FREQUENCY.
                      Operationalised: a paired win under the frozen MARGIN and
                      WIN_FRACTION, at BOTH primary K.
```

Both reuse the previously frozen margins and world-count rules, as the directive requires, and
both are written down **before** the run so neither can be tuned to the answer.

## 7. Status vocabulary — frozen

```
clears the full law AND phase shuffling destroys the advantage
    -> PHASE_HISTORY_FREQUENCY_SPREAD_SIGNAL

clears the law BUT random frequency approximately matches it
    -> GENERIC_DESYNCHRONIZATION_PLUS_PHASE_HISTORY_SIGNAL

phase shuffling PRESERVES the result
    -> COMBINATION_NOT_PHASE_DEPENDENT

merging exceeds the safety ceiling
    -> PHASE_MEMORY_UNSAFE

no combination clears the full law
    -> PHASE_REPAIR_NOT_CONFIRMED
```

Plus `STATUS_NOT_EMITTED` for a precondition failure — not an outcome, but a refusal to run the
law on an instrument that cannot answer.

**No CAS-specific, cognition-general, or production-memory claim is licensed by any outcome.**
Even the strongest result is a development finding about a synthetic memory mechanism.

## 8. Precondition gates — checked before the law, and before AWS spend

```
GATE_HEADROOM         P0 top-1 < 0.90 at K=2 and K=3
GATE_ORACLE           P1 top-1 >= 0.60 at K=2 and K=3
GATE_NO_ONE_HOP       one-hop argmax from the cue must sit at CHANCE
GATE_NO_CONTENT_LEAK  content argmax must sit at CHANCE
GATE_DISTINCT_Q       distinct query rows per world above a registered floor
```

The last three are the construct-validity checks the directive requires **before AWS spend**.
They run on dev worlds and are persisted in the receipt. `GATE_NO_CONTENT_LEAK` exists because
this exact leak was found in CMB-P0 and would have invalidated the tag arm here.

## 9. Compute

One remote AWS GPU instance. No experimental workload on the owner's local CPU. All substantive
tensor operations on CUDA, failing closed on silent CPU fallback. Remote host CPU only for
orchestration, file I/O, hashing, serialization, monitoring and shutdown.

```
HARD COST CEILING       $0.40
AUTOMATIC TERMINATION   on success, failure, timeout, upload failure, cancellation
```

Persisted: GPU and CUDA identity, tensor-device audit, CUDA and host runtime, peak VRAM,
estimated and actual cost, raw results, the complete receipt, and termination proof.

**Raw results are flushed to disk BEFORE receipt construction.** The CMB-P1 first launch
completed every GPU computation and then lost all of it to a receipt-serialisation crash. The
complete `main()` path, including JSON writing, is smoke-tested before launch — the specific
thing that was not tested last time.

## 10. Stop and audit

Stop after emitting the deterministic status. **Do not merge the phase mechanism into CMB-R1.**
Send the exact result commit to a **third-party auditor** who did not build or modify CMB-P0,
CMB-P1 or CMB-P2. 🔒 Owner-actionable: neither Claude nor GLM qualifies.

```
verified positive   -> owner rules on integration
negative or unsafe  -> the phase lane CLOSES
```

**No additional repair is authorized after this result, whatever it is.**

## 11. Falsifiers

- `P8P9_PHASE_SHUFFLED` keeps the advantage → `COMBINATION_NOT_PHASE_DEPENDENT`; the result was
  extra machinery, not phase.
- `P8P9_RANDOM_FREQUENCY` matches the spectral field → the structural derivation is inert and
  only the spread matters.
- `P8P9_EXACT` fails to beat `P8_ONLY` or `P9_ONLY` → the combination adds nothing over its
  parts, and the CMB-P1 number was a fluke of those particular worlds.
- Any gate fails → `STATUS_NOT_EMITTED`, escalated rather than resolved by me.

---

**Frozen. No held-out world has been read.**
