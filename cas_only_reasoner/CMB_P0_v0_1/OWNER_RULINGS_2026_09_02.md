# OWNER RULINGS — 2026-09-02 (post-CMB-P0)

Owner: Little Henderson (Prof. Hermes M. Thoth). Recorded by Claude, verbatim where the
wording is load-bearing. These rulings are **binding** on CMB-P0's record and on CMB-P1's
design. Claude is not the research governor; nothing here was decided by me.

---

## R1 — `P6_SCALAR_TWO_CHANNEL`: **RATIFIED**

> "P6 asks whether the benefit came merely from having a second channel rather than from
> angular phase. Phase beat P6 at every tested `K`, so P6 strengthens rather than weakens the
> finding. Removing it would make the phase result less convincing."

`P6` is now a **registered arm**, not a Claude addition awaiting ratification. It carries
forward into CMB-P1.

## R2 — the `P0` merge comparator is **RETIRED AS UNIMPLEMENTABLE**

`P0` produces no chain grouping, so it has no merge count in the same sense. §6 of the
CMB-P0 preregistration cannot be satisfied as written.

**For the completed CMB-P0 run:**
- the implemented `P2` comparison is **preserved as a documented deviation**;
- it is also recorded that `P4` exceeded the **absolute** merge threshold;
- it is recorded that the **oracle produced zero merges**;
- **`PHASE_MEMORY_UNSAFE` is PRESERVED.**

> "The outcome does not depend on choosing P2. P4 failed against the absolute threshold, the
> oracle, and every reasonable floor."

**For all future versions**, the metric is normalised:

```
merge_fraction = false_merged_chain_pairs / C(K, 2)
```

so the raw count cannot grow merely because `K` grows. Applied to CMB-P0's numbers:

| K | merges | C(K,2) | **merge fraction** |
|---|---|---|---|
| 2 | 0.657 | 1 | **0.657** |
| 3 | 1.852 | 3 | **0.617** |
| 4 | 3.538 | 6 | **0.590** |

A majority of all possible chain distinctions collapsed at every K. This was not a boundary
miss.

## R3 — `K=4` is **DIAGNOSTIC ONLY**

At `K=4` the oracle itself scored `0.560`, below its own `0.60` competence gate, so that
stratum is partly ill-posed.

```
Primary reportable range:   K = 2 and K = 3
K = 4:                      diagnostic data only, excluded from headline decisions
```

> "This does not rescue phase. The safety failure is already decisive at `K=3`, where the
> oracle passed."

## R4 — ONE anti-synchrony repair bench is **AUTHORIZED**: CMB-P1

Narrow, separately versioned. **Phase is NOT retrofitted into CMB-R1.** The production
memory board stays scalar and accountable; the phase system stays a **quarantined
experimental subsystem**.

Two repairs, tested **separately** — *"Do not combine P7 and P8 initially. Each must stand or
fall on its own, so we know which mechanism caused any improvement."*

- **`P7` — repulsive / inhibitory cross-chain coupling.** Attractive within a candidate
  chain, repulsive between incompatible ones. **May not use gold chain labels**; the
  supportive-vs-competing distinction must be inferred from information available equally to
  all arms.
- **`P8` — controlled frequency heterogeneity.** Frequency has now earned **one specific
  possible job — prevent cross-chain phase locking** — and *not* admission as an adjustable
  free knob. Offsets must be: frozen before held-out evaluation; derived from registered cue
  or structural information; **unavailable from gold chain identity**; tested against an
  explicit-tag control; and corrupted in an ablation.

> "A frequency code that simply assigns a unique frequency using the true chain ID would be
> an analog chain tag wearing a tiny tuxedo. It would not prove self-organized phase
> separation."

### Registered arm list for CMB-P1

```
P0  scalar propagation
P1  oracle chain tags -- CEILING ONLY, never a method
P2  competent inferred chain tracking
P3  matched two-state non-oscillatory recurrence
P4  original phase engine -- KNOWN UNSAFE reference
P5  phase-shuffled control
P6  scalar two-channel control
P7  phase + structurally derived repulsive coupling
P8  phase + frozen frequency heterogeneity
```

### Advancement criteria — a repaired phase system advances only if ALL EIGHT hold

1. Preserves the retrieval advantage at **both** `K=2` and `K=3`.
2. Reduces false chain merging **below the frozen safety threshold**.
3. Beats the matched generic two-state arm.
4. Beats or approaches a competent inferred-tag method.
5. **Loses its advantage when phase correspondence is shuffled.**
6. Does not increase wrong-chain retrieval or false memory admission.
7. Passes across independently seeded held-out worlds.
8. **Uses no oracle chain membership in the primary mechanism.**

### Registered verdicts

```
PHASE RETRIEVAL WIN, MERGING REMAINS      -> PHASE_MEMORY_UNSAFE
INHIBITION FIXES MERGING                  -> PHASE_SEPARATION_BY_SIGNED_COUPLING
FREQUENCY SPREAD FIXES MERGING            -> PHASE_SEPARATION_BY_FREQUENCY_HETEROGENEITY
TAGS MATCH OR BEAT SAFE PHASE             -> EXPLICIT_CHAIN_TAGS_PREFERRED
NO REPAIR PRESERVES BOTH ACCURACY
  AND ATTRIBUTION                         -> PHASE_RETIRED_FOR_MULTICHAIN_MEMORY
```

## R5 — a **THIRD** auditor is required

> "Claude built CMB-P0. GLM built the adjacent CMB-R1 lane. Neither should serve as the final
> independent auditor of the phase repair."

**🔒 This is owner-actionable and I cannot satisfy it myself.** Any subagent I spawn is still
Claude, so it does not meet the independence requirement. The owner must name and instruct a
third agent.

## R6 — the universal-attractor claim is **WITHDRAWN** (a correction to *my* wording)

> "I would not promote the broader 'exactly one attractor for every connected graph'
> statement without a formal proof covering the precise graph topology and nonlinear update."

The over-claim was mine, not GLM's. Retained, narrower, measured statement:

> **The registered `P4` system on these benchmark graphs converged toward global
> synchronisation.**

Corrected in `CMB_P0_PREREGISTRATION.md` (A1.3) and in the runner's interpretation guard.

## R7 — resonance labels, FIXED

```
Scalar CMB-R1 lane:
    RESONANCE-SPECIFIC            NOT SUPPORTED
    correct current term          BOUNDED ACTIVATION PROPAGATION

CMB-P0:
    PHASE-CODED MULTICHAIN RETRIEVAL    SUPPORTED
    SAFE PHASE MEMORY                   NOT SUPPORTED
```

> "Phase is a genuine oscillatory mechanism in P4, but that does not establish broad
> resonance, frequency selectivity, or a complete resonant-memory architecture."

## R8 — CJT-EX1 is **CLOSED**

> "The learned sparse E1S router collapsed, but the valid E4 control already tied the CAS
> expert organization almost exactly: E2 `0.7806` vs E4 `0.7800`. That is sufficient negative
> evidence that CAS expert meanings were not load-bearing on that task."

The E1S load-balancing repair moves to the **engineering backlog**, not another primary
research round. No further EX1 experiment is authorized.

## R9 — pulse width and Q remain **NOT admitted**

```
Phase                    has demonstrated retrieval value
Frequency heterogeneity  now has a specific possible job
Cross-chain inhibition   now has a specific possible job
Pulse width              NO demonstrated missing capability
Q                        diagnostic telemetry only
```

Also affirmed: the registered linear-spectrum values (`rho`, `tau`, `Q`) describe the
**generic two-state engine**, *not* the nonlinear phase arm.
