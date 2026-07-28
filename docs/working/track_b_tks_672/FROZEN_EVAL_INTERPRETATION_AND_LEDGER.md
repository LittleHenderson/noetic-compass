# FROZEN — eval interpretation map + claim ledger

**Committed while the R2–R5 eval was mid-run (`84/192` judged, no verdict computed, no eval
number read).** Owner-specified. Nothing below may be revised after `confirm_eval_results.json`
exists.

---

## 1. Claim ledger as of generation completion

### Earned

```
SELECTED_POLICY_LEAKAGE_CONTROL_PASS
CROSS_AUTHOR_FAMILY_LOW_LEAKAGE_REPLICATION
CRITERION_COPY_CONTROL_PASS
BYTE_REPLAYABILITY_VERIFIED
```

The earned claim, phrased at its correct width:

> *The selected authoring policy suppresses direct World-label leakage across two different model
> families under replayable, byte-identical prompting.*

**Phrasing correction adopted:** Gemini Flash and Claude Haiku each **reproduced the low-leakage
regime at `1/160` candidates**. With one observed leak per arm, the evidence supports *replication
of low leakage*, **not** precise equality between author models. "Identical" is withdrawn.

### Not yet earned

```
WORLD_SEMANTIC_RECOVERABILITY          DRIVE_SEMANTIC_RECOVERABILITY
JOINT_FOUNDATION_RECOVERABILITY        HELD_OUT_REALIZATION_TRANSFER
LEXICAL_RESISTANCE                     V3_FULL_CORPUS_AUTHORIZATION
```

A corpus can be *clean but meaningful, clean but mute, leaky but recoverable, leaky and mute*.
`R1`/`R1B` ruled out the direct-label form of "leaky." `R2`–`R5` decide *meaningful*.

## 2. The honest unit of evidence

```
A0 total      64 independent plan families    192 sibling items
train         48 families                     144 items
held-out      16 families                      48 items
```

**Effective `n` for semantic recovery and transfer is the FAMILY count, never sibling rows.**
Item-level accuracy is reported for readability; all bootstrap, CI, and significance work
clusters by family.

## 3. Frozen outcome interpretation — committed before results

| Outcome | Reading | Status assigned |
|---|---|---|
| All of `R2`–`R5` pass | blind semantic recovery transfers to unseen realization families while surface models fail to match it — the distinction Gate 2 needs | v3 generation justified |
| World passes, drive fails | grammar encodes *where* the incident resolves but not *why the actor moves* — repair belongs in the **motive block**, not the World criteria | targeted repair, new lock |
| Drive passes, World fails | motive clear, ontological location ambiguous — confirms the earlier Foundations `4`/`6`/`7` pattern | boundary research, not prompt tuning |
| Train passes, held-out fails | the grammar became a **family-specific cue system** | `FAIL_REALIZATION_FAMILY_TRANSFER` — **do not repair by moving held-out families into training** |
| Judge AND lexical baselines both succeed | recoverable but surface-readable | `NOT_LICENSED_SURFACE_RECOVERABLE` |
| All models fail | the policy removed labels *and* meaning | `VOID_ITEMS_DO_NOT_CARRY_RECOVERABLE_STRUCTURE` — an **item** failure, not a small-model failure |

## 4. Mechanical authorization table

Populated by code from result JSONs, one row per gate:

```
R1 · R1B · R2 · R3-WORLD · R3-DRIVE · R3-JOINT · R4 · R5 · R6A · R6B
```

**No prose override may convert a failed row into an overall pass.** v3 authorization requires
every required row green, mechanically.

## 5. Budget simulation rule — replaces the binomial-only model

If the pilot passes, the v3 budget is simulated from the **lower confidence bound** on the worst
cell's candidate-pass rate — not the point estimate — incorporating:

- direct-regex rejection
- family-level June-gate rejection
- recoverability rejection
- **dependence among siblings from one plan**
- observed variation across World × drive cells

A 28-cell corpus lives or dies at its hardest cell; `0.0250` overall is not the planning number.

## 6. Standing instruction

Nothing in the frozen pipeline is modified while `R2`–`R5` complete. The remaining question:

> *Did removing the category words preserve enough contextual structure for blind judges — and
> eventually small models — to recover World and drive beyond lexical shortcuts?*
