# AMENDMENT 1 to `JUDGE-POSITIVE-CONTROL-v1`

**Filed BEFORE any data is collected.** Parent pre-registration: commit `8ab16b2d`.
**Date:** 2026-07-27

---

## The conflict

The parent pre-registration specifies `280` rows per tier (`28` foundations × `10` items).

For tier `T0` that is **impossible without violating a defect this campaign already documented.**
`T0`'s item text is the choice-key definition *verbatim*, and there is exactly **one** verbatim
definition per foundation. Ten items per foundation would therefore be **ten byte-identical
copies**, giving `row_count = 280` and `effective_n = 28` — precisely the row-duplication defect
recorded as trap #1 in `HANDOFF_PACKAGE.md` §6, and the same defect that invalidated an earlier
dataset (`640` rows, effective `80`).

I wrote a pre-registration that would have manufactured the exact error I documented.

## The amendment

| Tier | Parent spec | Amended | Reason |
|---|---|---|---|
| `T0` | `280` rows | **`28` rows**, one per foundation, all distinct | Only 28 distinct verbatim definitions exist. `effective_n = 28` either way; this reports it honestly instead of inflating `row_count`. |
| `T1` | `280` rows | **up to `280`**, mechanically generated, **deduplicated**; actual count reported | Clause rotation yields a bounded number of distinct variants per definition. Whatever survives dedup is what runs. |
| `T2` | `280` rows | `280` rows | Unchanged — real scenarios are all distinct. |

**Bars are UNCHANGED.** `C1 >= 0.90`, `C2 >= 0.50`, `C3 >= 0.20`, `C4` no foundation above `30%`.

At `n = 28`, the `C1` bar of `0.90` means **`26` of `28` correct**. This is a smaller sample than
the parent specified, which makes `C1` *harder* to clear by chance, not easier: under blind
guessing at `1/28`, the probability of reaching 26/28 is astronomically small either way, and the
reduced `n` widens the confidence interval on a pass. The amendment is conservative.

## What this does not change

No bar moved. No criterion was added or removed. No consequence was rewritten. The
`C1`-failure branch — reclassifying all eight `NOT_LICENSED` verdicts as uninterpretable — stands
exactly as written in the parent.

## Disclosure standard

This amendment exists because the alternative was to run the parent spec as written and report
`280` rows for a tier whose effective sample size is `28`. That number would have been true and
misleading at the same time, which is the failure mode this campaign's controls exist to prevent.

Filed before data. Nothing licensed. Gate 2 remains OPEN at `0.38`.
