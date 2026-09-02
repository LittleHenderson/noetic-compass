# A third repair candidate: read the phase TRAJECTORY, not the endpoint

**Author:** Claude · 2026-09-02 · dev worlds 0–5 only, local RTX 4070 smoke lane, **$0**
**Status:** PROPOSAL for CMB-P1. **No measurement recorded. Held-out worlds 6–25 untouched.**
**Owner invitation:** *"FEEL FREE TO ALSO EXPLORE IDEAS OF YOUR OWN."*

---

## 1. The clue was already in CMB-P0's own receipt

The persisted convergence sweep says the chain separation **exists and then dies**:

| phase substeps | within-chain order | cross-chain separation | P4 top-1 |
|---|---|---|---|
| 1 | 0.5973 | 1.3268 | 0.2474 |
| 4 | 0.9143 | 0.8053 | 0.4601 |
| 10 *(frozen)* | 0.9937 | 0.2497 | 0.4123 |
| 25 | 0.9998 | 0.0166 | 0.3602 |

And P4 beat the explicit-clustering arm P2 by **+0.24 / +0.16 / +0.14**, while P2's clustering
purity was only 0.787. So the phase field holds **more** chain structure than agglomerative
clustering extracts. The information is there. **The endpoint is simply the one moment it is
gone.**

Reading the last frame of a system that is converging to global synchrony is like taking the
group photograph after everyone has already stood in the same spot.

## 2. The mechanism — and it has NO free parameter

Integrate phase coherence over the whole trajectory instead of sampling its final frame:

```
coh_j   = (1/T) * sum_t cos( theta_j(t) - theta_cue(t) )
score_j = a_j * clamp_min(coh_j, 0)
```

That is a plain unweighted mean. **There is no knob.** I also tried weighting each moment by
how unsynchronised the population was, `w(t) = (1 - R(t))^p` — and **every** sharpening made
it worse:

| variant | K=2 Δ vs P0 | K=3 Δ vs P0 | K=4 Δ vs P0 |
|---|---|---|---|
| **p = 0 (flat, no knob)** | **+0.037** | **+0.099** | **+0.081** |
| p = 1 | −0.047 | +0.018 | +0.039 |
| p = 2 | −0.099 | −0.034 | +0.000 |
| p = 8 | −0.169 | −0.102 | −0.052 |
| early-stop R < 0.5 | −0.216 | −0.078 | −0.037 |

The simplest form is the best form. That is worth noting precisely because the opposite —
"it works if you tune it" — is what a tuning artifact looks like.

**Legality:** uses no chain labels, no inferred clusters, no oracle, and no new free
parameter. The only quantity read is the system's own phase history.

## 3. What it buys — an ~8× reduction in merging

Dev worlds, `merge_fraction = merges / C(K,2)` (the owner's normalised metric):

| K | endpoint (current P4) | **flat trajectory** | reduction |
|---|---|---|---|
| 2 | 0.6302 | **0.0755** | **8.3×** |
| 3 | 0.6719 | **0.0877** | **7.7×** |
| 4 | 0.6068 | **0.0677** | **9.0×** |

Accuracy is preserved and, at K=3 and K=4, **improved over the endpoint**:

| K | P0 | endpoint P4 | flat trajectory |
|---|---|---|---|
| 2 | 0.4948 | **0.5651** | 0.5312 |
| 3 | 0.3333 | 0.3906 | **0.4323** |
| 4 | 0.2630 | 0.2839 | **0.3438** |

## 4. Kill-checks — one passed decisively, one FAILED

**Criterion 5 (shuffle control): PASS, decisively.** Destroying phase-to-node correspondence
collapses it to **below** the scalar baseline:

| K | P0 | flat trajectory | **shuffled** |
|---|---|---|---|
| 2 | 0.4948 | 0.5312 | **0.2188** |
| 3 | 0.3333 | 0.4323 | **0.2500** |
| 4 | 0.2630 | 0.3438 | **0.1667** |

It is reading chain structure, not amplitude with extra steps.

**K=1 sanity: FAIL, and it is a real cost.** Where there is nothing to separate, the arm
should reduce to the scalar engine. It does not:

```
K=1:  P0 0.9219   endpoint P4 0.9167   flat trajectory 0.7448
```

Cause is understood, not mysterious: at K=1 every active node *should* share the cue's phase,
so the early random-initialisation frames are pure noise, and averaging them in dilutes a
signal that the endpoint gets for free.

## 5. The burn-in trade curve — a structural choice, not a tuned knob

Skipping frames *before the first amplitude wave has propagated* is justified by the
mechanism: until then the phase field carries no graph information at all, only its random
initialisation. Burn-in is measured in whole amplitude waves, so it is discrete.

| burn-in | K=1 | K=2 top1 / frac | K=3 top1 / frac | K=4 top1 / frac |
|---|---|---|---|---|
| *P0 reference* | 0.9219 | 0.4948 / — | 0.3333 / — | 0.2630 / — |
| *endpoint P4* | 0.9167 | 0.5651 / 0.630 | 0.3906 / 0.672 | 0.2839 / 0.607 |
| **0 waves** | 0.7448 | 0.5312 / **0.076** | 0.4323 / **0.088** | 0.3438 / **0.068** |
| **1 wave** | 0.8646 | **0.6250** / 0.302 | **0.4844** / 0.299 | **0.3698** / 0.214 |
| **2 waves** | 0.9010 | 0.6198 / 0.422 | 0.4661 / 0.431 | 0.3255 / 0.356 |

**This is the finding, and it is more useful than any single point:** there is a genuine,
continuous trade between retrieval accuracy and chain attribution, and the burn-in exposes the
whole curve. Burn-in 1 gives the largest accuracy gain ever measured on this bench
(**+0.130 / +0.151 / +0.107** over P0, roughly double the endpoint's advantage) at moderate
merging. Burn-in 0 gives by far the best attribution at a smaller accuracy gain and a real
K=1 regression.

**I am not choosing the flattering row.** The registered primary should be **burn-in 0**,
because the entire purpose of CMB-P1 is to fix attribution, and burn-in 0 is the only setting
that decisively does. The rest of the curve is reported as the diagnostic it is, with the K=1
regression disclosed as a cost rather than buried.

## 6. The honest limitation — this is a READOUT repair, not a DYNAMICS repair

Measured: the global order parameter still ends near 1.0.

```
K=2:  R(t)  start 0.3280  ->  mid 0.8177  ->  END 0.9596
K=3:  R(t)  start 0.2968  ->  mid 0.8122  ->  END 0.9551
```

**The chains still synchronise.** This mechanism does not stop the collapse; it declines to
depend on the collapsed frame. That distinction matters for three reasons:

1. It must never be described as "fixing synchronisation". It is not.
2. It is **orthogonal** to the owner's two proposals, which change the *dynamics* (`P7`
   signed coupling, `P8` frequency heterogeneity). So it satisfies the
   "each mechanism must stand or fall alone" rule cleanly — it is a different axis, not a
   competing implementation of the same one.
3. A system whose internal state still collapses may be fragile in ways this bench does not
   probe, even when its readout is accurate. That is an open risk, stated rather than hidden.

## 7. Proposed arm

```
P9_PHASE_TRAJECTORY_COHERENCE
    dynamics : IDENTICAL to P4 -- not one parameter changed
    readout  : mean over the trajectory of cos(theta_j(t) - theta_cue(t)), times amplitude
    knobs    : NONE (burn-in = 0 registered; the curve reported as a diagnostic)
    controls : P9-shuffled (phase correspondence destroyed) must fall BELOW P0 -- it does,
               to 0.219 / 0.250 / 0.167
```

Because its dynamics are byte-identical to `P4`, `P9 − P4` isolates **the readout alone**.
That is the cleanest possible attribution of any effect, and it costs no extra propagation —
the trajectory is already computed and then thrown away.

## 8. What I am NOT claiming

Dev worlds only, six of them, one construction, one seed regime. Nothing here is a result;
the held-out worlds have not been read. It has not been compared against `P7` or `P8`, which
do not exist yet. It does not repair the synchronisation itself. And no CAS-specific or
resonance-specific reading is licensed by any of it.
