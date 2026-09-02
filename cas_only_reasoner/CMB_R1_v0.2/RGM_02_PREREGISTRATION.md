# RGM-0.2 — Admission Safety and Matched-Control Repair · PREREGISTRATION v0.1 (FROZEN)

**Authorized by owner directive, 2026-09-02:** *"I need you to build RGM-0.2 and I'll have
another model audit."*
**Builder:** Claude. **Auditor:** a different model, named by the owner. I do not audit this.
**Base:** `cas_only_reasoner/CMB_R1_v0.1/` at GLM's commit `a086a770`, imported **code only**.
GLM's `CHANGELOG.md` deletion (my CRITICAL finding G-1) is **not** merged; `CHANGELOG.md`
stands at 1150 lines.
**Branch:** `research/cmb-r1-rgm02-v1`, from `e82ae4b1`.
**Status:** frozen before any held-out world is read.

---

## 0. A conflict of interest, declared

I audited RGM-0 and RGM-0.1. I am now building RGM-0.2 **on my own audit findings**. That is
efficient — I know exactly what is broken — and it is also exactly the arrangement the
governance rule warns about: one model as auditor and builder of the same lane. Two
consequences, both binding:

1. **Every defect this build repairs is quoted from my audit with its measured numbers**, so
   the incoming auditor can check whether the repair addresses the finding or merely restates
   it.
2. **I emit no status for RGM-0.2 that depends on my own prior judgement.** Where my audit
   *overturned* a GLM status, I re-measure rather than inherit.

## 1. What this build fixes, and the measurement that says so

Every item below is a defect I measured during the RGM-0/0.1 audits. Nothing here is new
theory.

### Item 1 — the false near-match admission problem

Measured (RGM-0.1 audit, echo-attack table, 20 worlds):

| config | classic echo | overlap | **near-miss (lev-1)** | violations |
|---|---|---|---|---|
| BOTH | 0 | 0 | **359** | 3 |
| COH_ONLY | 0 | 0 | 377 | 14 |
| ROOT_ONLY | 334 | 327 | 359 | 3 |
| NEITHER | 443 | 399 | 360 | 14 |

**On the near-miss attack `BOTH` (359) is indistinguishable from `NEITHER` (360).** The
defences do nothing.

**Cause, as recorded in the audit:** `TAU_COH = 0.75` is an **absolute** threshold and the
attack is constructed at similarity 0.75–0.833, sitting exactly on it. *A fixed threshold
cannot separate a near-miss from a true match by construction.*

**Repair, following the direction the audit recorded:** replace the absolute gate with a
**relative** one. A candidate is judged against the best competing candidate *from a different
provenance root* in the same result set, not against a constant.

```
ABSOLUTE FLOOR   coh >= TAU_FLOOR                     (keeps obvious junk out)
RELATIVE MARGIN  coh >= best_other_root_coh - DELTA   (near-miss and true match cannot both pass)
```

### Item 2 — separate retrieved candidates from memories authorized to influence reasoning

Today `arm_d` returns one `verified` list. Anything in it is equally usable. **RGM-0.2 splits
admission into two tiers**, which is also what makes item 1's ambiguity survivable:

```
RETRIEVED    passed the floor. May be SHOWN or used as context.
AUTHORIZED   may influence REASONING or LEARNING (replay, weight updates).
             Requires strictly more: the relative margin, provenance independence,
             and unambiguity -- if two different roots are within DELTA of each other,
             NEITHER is authorized.
```

**Ambiguity downgrades rather than silently admits.** That is the link between items 1 and 2:
a near-miss that cannot be told from a true match is exactly the case that must not be allowed
to influence learning.

### Item 3 — keeping the matched control matched under a NEW verifier

> **🟥 CORRECTION, 2026-09-02, before any run. MY ORIGINAL CLAIM HERE WAS WRONG.**
>
> This section first asserted that the matched generic geometry control was *handicapped*,
> citing `cmb_r1_core.py:490`:
> ```python
> coherence_off = (geo_mode == "generic") or not use_coherence
> ```
> **That line does not affect the generic geometry control.** `E2` — the actual matched
> control — is run through `arm_prop(field="role", ...)` in `cmb_r1_v01_core.py`, whose
> `coherence` parameter **defaults to `True`**, and whose verifier (lines 133–155) *does*
> apply the `TAU_COH` check. `PROP_ARMS["E2"]` passes no `coherence` key, so `E2` receives the
> verifier.
>
> The `coherence_off` line reaches only `M_NOISE`, which `run_rgm01.py:92` runs with
> `use_coherence=False` **deliberately** — it is the relational misinformation control and is
> *supposed* to have no verifier.
>
> **So `GENERIC_GEOMETRY_ADVANTAGE` was measured fairly on this axis in RGM-0.1**, and my own
> earlier audit said so ("the verifier configuration is no longer silently disabled for it").
> I contradicted my own audit by reading one line without checking which arm uses that path —
> the exact error class I have criticised in others. The claim is **withdrawn**; no RGM-0.1
> status changes because of it.

**What item 3 actually is.** The handicap does not exist in RGM-0.1 — but **it would be
introduced by my own RGM-0.2 change** if I gave the CAS arm the new two-tier verifier and left
the control on the old one. That would manufacture precisely the defect I falsely alleged.

**Repair:** the generic control gets the identical verifier, the identical two-tier admission,
and the identical thresholds. `GENERIC_GEOMETRY_ADVANTAGE` is then **re-measured from
scratch** and its previous value is superseded **because the verifier changed for both arms**, not
because the old measurement was unfair.

### Item 1b — WHICH condition does the work (measured, and it corrected me twice)

I wrote that the **relative margin** is what generalises. Measured, it is not. Ablation over
20 near-miss queries on 2 dev worlds:

| config | FALSE authorized | TRUE authorized | blocked by |
|---|---|---|---|
| *registered attack, false coherence 0.8333, bar 0.90* | | | |
| all three conditions | 0 | 60 | — |
| absolute OFF | 0 | 60 | — (relative alone suffices) |
| relative OFF | 0 | 0 | **consistency** |
| *adaptive attack, forged at 0.9375 — above the bar AND inside the margin* | | | |
| all three conditions | **0** | 0 | **consistency** |
| absolute OFF | 0 | 0 | **consistency** |
| relative OFF | 0 | 0 | **consistency** |

**The load-bearing condition is (c) consistency — the top cluster must agree with itself.** An
attacker who knows the thresholds can forge above the absolute bar and inside the relative
margin; what they cannot do is make a forgery *agree with the truth it is impersonating*,
because if it agreed it would not be a forgery.

**Disclosed cost, not hidden:** under the adaptive attack the system authorises **nothing** —
true memories included. It fails **closed**. That is the right trade for a memory system, but
a flood of near-identical forgeries can deny authorisation to legitimate memories. That is an
availability cost and it is a registered limitation, not a footnote.

*Also recorded: my first ablation set `delta = 0` to "disable" the relative condition, which
actually empties the top cluster and disables authorisation entirely — a degenerate control,
not an ablation. Disabling it properly requires `delta` LARGE. The corrected ablation is the
one above.*

### Item 4 — confirm across new independent memory worlds

New, disjoint world seeds, and **the five-depth shortcut gate**
(`cas_only_reasoner/SHORTCUT_GATE_v0_1/`) run on them **before any arm is scored**. Three
benches in the phase arc were solvable without the capability under test, and each shortcut
was created by the repair for the previous one. This lane does not get to repeat that.

## 2. What is NOT built in this round

Owner's gating, honored literally: *"Build the selective replay selector only after admission
safety passes."*

```
item 5  selective replay selector          NOT BUILT -- gated on items 1-4 passing
item 6  replay vs random vs semantic-only  NOT BUILT -- gated on item 5
```

If admission safety fails, this round ends with that finding and no replay work.

## 3. Mechanisms carried forward unchanged

Exactly the owner's list. None is redesigned; the repairs are to the **verifier** and the
**controls**, not to the retrieval mechanisms.

```
semantic retrieval              static CMB backup and re-ranking
static CAS geometry             bounded graph propagation
ordered CAS trajectories        additive corroboration
trajectory-coherence checking   verifier-controlled memory admission
```

**Phase, frequency, pulse width and Q are absent.** Phase integration is NOT AUTHORIZED
(owner ruling, 2026-09-02) and nothing from the phase lane enters this build.

## 4. Arms

| Arm | What it is |
|---|---|
| `A_SEMANTIC` | semantic retrieval only |
| `B_STATIC_CMB` | semantic + static CAS geometry, no propagation |
| `C_TRAJECTORY` | + ordered trajectory re-scoring |
| `D_FULL_CAS` | full pipeline: propagation + two-tier verifier |
| `E_GENERIC_GEOMETRY` | **matched** control — role-coarsened geometry, **now with the identical verifier** |
| `M_NOISE` | relational misinformation control |
| `B_SHORTCUT_GATE` | the five-depth mechanism-free baseline, run before any arm is scored |

## 5. Registered measurements

```
near_miss_admitted          count admitted under the lev-1 near-miss attack
near_miss_authorized        count reaching the AUTHORIZED tier  <- the safety number
classic_echo_admitted       must stay at 0
overlap_echo_admitted       must stay at 0
rank_violations             a false memory outranking a true witness
retrieval_top1 / recall     capability, per family
generic_geometry_delta      D - E, RE-MEASURED with the control un-handicapped
authorized_precision        fraction of AUTHORIZED memories that are actually correct
```

`authorized_precision` is the one that matters for a memory system: **what fraction of what we
let influence reasoning is true.**

## 6. Frozen thresholds

```
TAU_FLOOR   = 0.60     absolute floor for RETRIEVED
DELTA       = 0.08     relative margin required for AUTHORIZED
MARGIN      = 0.02     paired top-1 margin, as in every bench in this project
WIN_FRACTION= 0.70     a win must hold in >=70% of worlds
```

`TAU_FLOOR` is deliberately **below** the old `TAU_COH = 0.75`: the floor's job is only to
exclude junk. Separation is now `DELTA`'s job, and putting both in one constant is the defect
being repaired.

## 7. Status law

```
ADMISSION_SAFETY_REPAIRED        near-miss AUTHORIZED count materially below the RGM-0.1
                                 baseline, classic and overlap echo still 0, and
                                 authorized_precision materially above the RGM-0.1 admitted set
ADMISSION_SAFETY_NOT_REPAIRED    the near-miss attack still reaches AUTHORIZED
GENERIC_GEOMETRY_ADVANTAGE_*     re-emitted from scratch against the un-handicapped control
STATUS_NOT_EMITTED               a precondition or the shortcut gate failed
```

**A hard gate that fails is a FAILURE, never "PASS with caveats."** Claim status is emitted by
a deterministic program reading frozen thresholds, not by prose.

## 8. Compute

One remote AWS GPU instance if the workload warrants it; this bench is graph algebra and
string similarity, so if it is CPU-bound and small it runs on the remote host CPU **and says
so** — the GPU-only law covers neural inference, which this has none of. No workload on the
owner's local machine beyond `$0` construct-validity checks that record no measurement.

```
HARD COST CEILING   $0.40
```

## 9. Stop and audit

Stop after the deterministic report. **Send to the owner's named third-party auditor.** I built
it; I do not audit it. The audit surface includes this preregistration, the repairs, and the
declared conflict of interest in §0.

---

**Frozen. No held-out world has been read.**
