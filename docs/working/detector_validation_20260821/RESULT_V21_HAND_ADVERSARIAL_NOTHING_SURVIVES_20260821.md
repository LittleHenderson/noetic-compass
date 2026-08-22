# V21 — Hand-adversarial audit: NOTHING in the session's reading results survives ($0, no model)

**Date:** 2026-08-21 · **Cost:** `$0` (pure text analysis).
**Results file (co-located):** `hand_adversarial_results.json`, sha256 `b28a46fef314f24e…`
**Why:** v20 established that automated rule search is only a **lower bound** on how solvable a stimulus set is. So the two "SURVIVES" verdicts (valence `+0.313`, Operator-10 `+0.150`) were not safe. This attacks them **by hand**.

## Result — both fall

| set | model (published) | automated shortest rule (v20) | **hand lexicon** | verdict |
|---|---|---|---|---|
| **Valence `^2`/`^3`** | **15/16 = `0.9375`** | 0.625 | **15/16 = `0.9375`** | **BROKEN — exact tie, zero model advantage** |
| **Operator-10** | **16/20 = `0.800`** | 0.650 | **20/20 = `1.000`** | **BROKEN — lexicon beats the model by 4 items** |

- **Valence:** a standard English sentiment word list (`accepted/rejected`, `smiled/failed`, `hoped/feared`, `finally/missing`…) scores **exactly** what the 6.9b model scored — 15/16, same single miss profile in aggregate. The model contributes **nothing** over lexical sentiment on this set.
- **Operator-10:** a semantic cue lexicon scores **20/20**, i.e. **perfect**, beating the model's 16/20.

> **Script bug recorded:** the audit printed `WEAKENED` for valence because it compared `0.9375 >= 0.938` (float vs rounded constant) → `False`. The honest verdict is **BROKEN** (exact tie at 15/16). Caught before reporting.

## Honest limitation of this attack (stated, not hidden)
**The lexicons were written with sight of the sentences**, so they are partly item-derived — a strong attack, but not a fully independent one. This matters differently per axis:
- **Valence: the attack is FAIR and damning.** The discriminating words (`accepted`/`rejected`, `smiled`/`looked away`, `hoped`/`feared`, `finally`/`missing`) are **ordinary sentiment vocabulary**, not contrived to these items. Valence in this stimulus set is genuinely **lexically carried**.
- **Operator-10: the attack is WEAKER as evidence.** Some cue words are clearly item-specific (`pine tar`, `workbench`, `thousandth`), which shades toward memorization rather than a general rule. The `20/20` should be read as "a determined hand-built lexicon solves it," **not** "a generic rule solves it." Still: it means the set does **not** demonstrate the model reads something a lexicon cannot.

## What this means — the session's honest bottom line

**Every reading result produced this session is matched or beaten by a hand-written lexical rule.** Sorted:
- Domain-4 — withdrawn (v19, three regexes = `1.000`)
- `^8`/`^9` — withdrawn (v20, comma-count rule ties)
- **Valence — now withdrawn as a beyond-lexical claim** (sentiment lexicon ties exactly)
- **Operator-10 — now withdrawn as a beyond-lexical claim** (lexicon beats it)

**The harness's "reading" capability has NOT been shown to exceed lexical semantics on any stimulus set tested this session.** That is the honest state. It does **not** show the model lacks CAS structure — it shows **these experiments cannot tell**, because every stimulus set was solvable from words alone.

**What still stands (unaffected by this audit):**
- **v16 causal steering** — a *causal* result (inject → output moves, z=`11.18` vs matched-random), not a reading/classification claim. A lexicon cannot "tie" an intervention. It remains bounded by v17 to *"the valence direction steers valence output, direction-specific vs random"* — a standard steering-vector claim, not a CAS-construct claim.

**CAS-specificity: `GREY`. The reading track is now a clean negative at this stimulus quality.**

## The only way forward that can produce a real reading result
1. **Stimuli where the label is NOT lexically recoverable** — e.g. **matched minimal pairs**: the *same words* rearranged so a lexicon must tie while a structural reader can split them. (The spec sheet already records L3 matched-surface pairs as `INCONCLUSIVE BY DESIGN` — this is the same missing test, and it is the sharpest discriminator available.)
2. **Pre-registered blocking gate:** no GPU spend until a hand-adversarial lexicon **and** automated rule search both fail to beat chance+margin on the candidate set.
3. **Lean on causal/intervention evidence**, which is structurally immune to the lexicon attack, rather than classification accuracy.

## Claim state
- **Real:** all audit numbers (deterministic text analysis, `$0`). **Accepted:** none.
- **WITHDRAWN as beyond-lexical:** valence reading, Operator-10, Domain-4, `^8`/`^9`.
- **STANDS:** v16 causal steering (bounded per v17).
- **Never deleted:** all prior numbers retained; this is their correction.
