# CMB-P2 — PRE-LAUNCH STOP. **$0 spent. Nothing launched.**

**Date:** 2026-09-02 · **Branch:** `research/cmb-p2-p8p9-confirmation`
**Parent:** `99909e8c79b9283412826fd7658956794247b777`
**Decision:** **DO NOT LAUNCH.** The directive's own §4 requires proving there is no answer
shortcut *before AWS spend*. That check failed.

---

## 1. What was found

**A phase-free rule that never looks at which chains are active beats the arm that is handed
the true chain labels.**

Measured by me, with the real bench code (`build_world_p1`, `build_queries`,
`propagate_scalar`, `propagate_channels`), on throwaway world ids 900000–900005 so that no
CMB-P2 dev or held-out world was read:

| | K=2 | K=3 |
|---|---|---|
| `P0_SCALAR` | 0.4974 | 0.3464 |
| **`P1_ORACLE` — handed the true chain labels** | **0.7682** | **0.6797** |
| `B_TWOHOP` — two-hop mass from the cue, masked to a label-free candidate set | **0.8255** | **0.8568** |
| `B_TWOHOP × amplitude` | **0.9661** | **0.9323** |

The shortcut has two parts, both label-free:

**(a) The candidate set falls out of the adjacency matrix.** A completion is exactly the node
with `pool` edges of weight `1.0` — one from every cue. Recovered **exactly in 6/6 worlds at
both K**, using no seeds, no active set and no labels.

**(b) Two-hop mass identifies the gold.** One hop is flat, exactly as the CMB-P0 C1 repair
intended:

```
A [cue0, completions] = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
A2[cue0, completions] = [1.0975, 0.195, 0.09, 0.0, 0.09, 0.0, 0.4875]
                         ^^^^^^ gold                        ^^^^^^ best rival
```

The gold carries roughly **2.3×** the two-hop mass of its nearest rival here, because the path
`cue → (a node of the cue's own chain) → gold` exists at weight `1.0 × 0.65` and `0.55 × 0.65`.

## 2. Why this is fatal rather than fixable-in-place

**I built this shortcut myself, in the repair for the previous one.** The C1 fix removed the
cue's private one-hop edge to its own completion, and replaced the chain-specific evidence with
0.65-weight edges from the cue's chain's *earlier* nodes to that chain's completion. That is
precisely a two-hop signature from the cue.

Consequences:

- **The construct claim in all three preregistrations is FALSE.** The comment in `cmb_p0.py`
  and §2.1 of the CMB-P0 preregistration say the answer is "recoverable only by knowing which
  active seeds belong to the cued chain." It is not. It is recoverable from the wiring.
- **Fresh worlds give ZERO protection.** This is a property of the generator, not of the seeds.
  CMB-P2's new worlds 500–535 have it too.
- **"% of oracle" is not a scale.** The oracle is not the ceiling; a label-free rule is above
  it. Every "90% / 84% / 77% of oracle" statement about `P8P9` must be withdrawn as a framing.
- **`GATE_NO_ONE_HOP` passed honestly and was looking one hop too shallow.** It measures
  exactly what it claims and the shortcut lives at depth two.

**The minimal repair is a redesign, which the directive prohibits.** Flattening two-hop mass
means linking every completion to every chain's earlier nodes equally — but then no
chain-specific evidence exists at all and the *oracle* cannot solve the task either. Making the
evidence readable only when the active set is known is a different world generator, not a
parameter change. The directive says this is "a one-shot confirmation, not another open
redesign round," so that decision is not mine to take.

## 3. What this does and does not change about the published results

**Does NOT change:**

- `PHASE_MEMORY_UNSAFE` for CMB-P0 and CMB-P1. Both stand.
- Any measured number in either receipt.
- The arm-versus-arm comparisons. **No CMB-P0/P1/P2 arm uses the shortcut** — they propagate
  from *all* active seeds and none masks to the recovered candidate set — so every arm was
  equally blind to it and the paired comparisons between them remain internally valid.

**DOES change:**

- The claim that the task requires chain separation. **Withdrawn.**
- The "fraction of oracle" framing for `P8P9`. **Withdrawn** — the oracle is not the ceiling.
- The strength of every "beats the phase-free baseline" criterion. The registered phase-free
  baselines (`B_STRUCT_GATE_REACH`, `B_PHASE_FREE_CONTENT`) were the *weak* ones; the strong
  one was never registered and was never run.

## 4. Everything else the review found (all real, all cheap, none of it the reason for stopping)

| | Finding | Fix |
|---|---|---|
| B2 | `OMEGA_SHUFFLED` — the frequency control that returned **`structure_adds_beyond_spread = false` at both primary K** in CMB-P1 — was dropped; only the weaker `OMEGA_RANDOM` remained, and it gates the strongest status word | add one `phase()` call, +$0.026 |
| B3 | the endpoint-view merge fraction is computed on every phase run and then discarded; the safety criterion reads only the flattering trajectory view (they differ 20–100×) | pass it into `put()`, $0 |
| B4 | the launcher uploads the receipt **before** the raw file and downloads only the receipt, so the flush repair can lose the file it exists to protect | reorder + add to the download list, $0 |
| B5 | the preregistration promises a persisted tensor-device audit; `"device"` is in `VOLATILE` and stripped from both outputs, and `assert_cuda` is called **0 times** in the runner | remove one token, $0 |
| B6 | **a verifying agent read held-out worlds 506–512** during the review, so "No held-out world has been read" is now false | move the range to 536–565, $0 |

**B6 matters independently of the stop:** 7 of the 30 registered held-out worlds have been
touched, on non-registered hardware. Whatever happens next, that range is burned and the
held-out set must move.

## 5. Verified as NOT defects — recorded so nobody re-litigates them

- **The phase-shuffle control is fair and informative.** I measured the no-information limit
  directly: with every phase forced equal, shuffling is an **exact no-op** — shuffled `0.495` =
  P0 `0.495`, gap `0.0000` — and the collapse then scales with real structure (zero-omega gap
  0.255/0.154; spectral gap 0.674/0.542). A control that always failed would prove nothing;
  this one only fires when the field carries structure.
- **`GATE_NO_ONE_HOP` uses the correct null.** Every cue links to every completion at exactly
  1.0, so the one-hop argmax is a tie inside the completion set and `1/pool` is right.
- **Cost and memory were never the risk.** Projected $0.10–$0.13, peak VRAM under 100 MB on a
  15.6 GB card.
- **Do not canonicalise the eigenvector sign** hours before a one-shot run.

## 6. Status

```
CMB-P2 LAUNCHED            NO
SPEND                      $0.00
HELD-OUT WORLDS 506-535    7 of 30 touched by a verifying agent -- range must move
CMB-P0 / CMB-P1 STATUS     PHASE_MEMORY_UNSAFE, both PRESERVED, unchanged
CONSTRUCT CLAIM            WITHDRAWN -- the task does not require chain separation
DECISION OWED              owner: the fix is a world redesign, which the directive prohibits
```

**This is the standing project rule doing its job, for the third time:** *a win by mechanism M
is uninterpretable until it beats the cheapest method without M.* The cheapest method without
phase has now been built and measured. It beats the oracle.
