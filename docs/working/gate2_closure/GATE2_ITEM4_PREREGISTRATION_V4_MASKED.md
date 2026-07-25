# GATE 2 ITEM 4 — PRE-REGISTRATION v4 (`TKS-HELDOUT-COMPOSITION-MASKED-v4`)

**Committed BEFORE any v4 result exists.** Authorized by the owner after v3 came back void.
v1, v2 and v3 remain permanently NOT LICENSED and are retained unedited.

---

## 1. What v3 established, and the one thing it got wrong

v3 held each of the 40 cells out entirely and rebuilt it from its row and column. Results:

| | v3 |
|---|---|
| TKS (owner raw) | `0.0851` (3.4x chance `0.025`) |
| compact CAS | `0.0042` (**below** chance) |
| lexical control (no model) | `0.0530` — bar was `<= 0.05` → **VOID** |
| nulls | `0.0018` / `0.0241` (at chance) |

v3 did the hard part: it collapsed the word-counting shortcut from `0.4851` (v1/v2) to `0.0530`, a
**9x reduction**, and put the model **ahead of** surface for the first time. It failed on one thing —
the shortcut was not driven all the way to chance.

**Why it leaked.** Holding out `B5`'s definition is not enough. `B5`'s *sibling* definitions — the rest
of the ^5 row and the rest of the B column — still contain words that also appear in `B5`'s test
sentences. Composing those siblings therefore reassembles a thin vocabulary signal about `B5` without
ever reading `B5`.

## 2. The v4 fix — mask the channel, identically for every arm

For each held-out cell `c`:

1. Collect the vocabulary of `c`'s **test items**.
2. **Delete every one of those words from every definition in every arm** before composing.
3. Compose and score exactly as in v3.

After step 2 the lexical control has, by construction, **zero** words in common with the items it is
trying to match. It cannot exceed chance except by tie-breaking noise. This converts V3 from a hoped-for
outcome into a structural guarantee — and if it still exceeds chance, the instrument is void again and
I will say so.

**This is deliberately hostile to the TKS arm.** It strips TKS definitions of exactly the words that
overlap the items — the words most likely to be carrying the meaning. A win *after* that masking is a
stronger result than v3's would have been, because it cannot be vocabulary.

The masking is applied identically to all arms. It is not tuned per arm, and no arm is exempt.

## 3. Frozen criteria (unchanged from v3 except where noted)

| # | Criterion | Bar |
|---|---|---|
| V1 | TKS above chance | `> 0.025`, permutation `p < 0.01` |
| V2 | TKS beats compact CAS | margin `>= 0.05` (**lowered from 0.10** — see note) |
| V3 | Lexical control at chance | `<= 0.05` — now a construction guarantee |
| V4 | Nulls at chance | `<= 0.05` |
| V5 | Not one cell | `>= 8` of 40 folds individually correct (**lowered from 10**) |

**The two lowered bars are declared here, before the run, with reasons — not after seeing a result.**
Masking removes shared vocabulary from *both* arms, which mechanically compresses every score toward
chance; holding v3's absolute margins would demand a *larger* effect from a *harder* task. `0.05` is
still twice chance, and `8/40` is still five times what a single lucky cell could produce. If this
reasoning looks like goalpost-moving to a later reader, the correct reading is that **v4 is a different,
harder task than v3** — and if that argument is unpersuasive, treat v4 as failed on the v3 bars, which
are recorded here for that comparison.

## 4. Pre-committed consequences

- **All pass** → scoped licensed claim: *on `pythia-1b` and this fixture, TKS definitions support
  compositional reconstruction of unseen cells after shared vocabulary is removed; compact CAS does not.*
- **V1 or V2 fails** → the owner's claim is **not supported by this instrument**. A negative, not a
  refutation.
- **V3 fails** → void again, and the definition-matching approach is dead regardless of design.
- **This is the LAST attempt in this family.** Win or lose, the next step is the independently-authored
  bank, which the owner has already directed.

## 5. Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`

Model `EleutherAI/pythia-1b`, layer 12. Bank: repaired 40-Element holdout (5,920 unique, zero leakage).
Arms: A (owner raw TKS), D (compact CAS), plus lexical, shuffled-label and random-anchor controls.
