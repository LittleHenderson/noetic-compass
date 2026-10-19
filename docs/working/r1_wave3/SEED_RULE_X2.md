# X2 seed rule (HELM-R1 wave 3, fresh exam X2) — written into the preregistration, so no amendment is needed

Written 2026-10-19 by the wave-3 builder, before the owner's R1W3 line exists. Implemented by
`r1w3/seed_rule_x2.py` (this package). Lesson carried from X1 (amendment R1W2-A1): a 1,000,000-wide band next to a
used seed can have zero free slots, and the English-16 seed had no step rule. Both are fixed here, in advance.

## 1. Input
`H3 = sha256(UTF-8 bytes of the owner's R1W3 sign line, verbatim, no trailing newline)`. Cuts as X0 / X1:
`k1 = int(H3[0:16],16)`, `k2 = [16:32]`, `k3 = [32:48]`, `k4 = [48:64]`.

## 2. Bands (X1's bands moved up again; new bands for the new parts)

| Part | Band | Slots | Slot from |
|---|---|---|---|
| GB | X0's Gate B band + 4,000,000: world seeds 1,004,000,001 to 1,104,000,000 (slot 100,000) | 1,000 | k1 mod 1,000 |
| TB | X0's draw band + 20 draws: windows of 60 draws from d = 5,970 | 33 | k2 mod 33 |
| D34 | X0's depth band + 4,000,000: row bases 1,654,000,000 to 1,743,999,999 (slot 2,000,000) | 45 | k3 mod 45 |
| LANG (CCE) | 1,806,000,001 to 1,807,000,000 | 1,000,000 | k4 mod 1,000,000 |
| E16 | 1,808,000,001 to 1,809,000,000 | 1,000,000 | k4 mod 1,000,000 |
| F16 | 1,810,000,001 to 1,811,000,000 | 1,000,000 | k1 mod 1,000,000 |
| CASC | 1,812,000,001 to 1,813,000,000 | 1,000,000 | k2 mod 1,000,000 |
| IDLE | 1,814,000,001 to 1,815,000,000 | 1,000,000 | k3 mod 1,000,000 |

Inside GB, TB and D34, X0's layout applies word for word with the new base (series, panel, new worlds, wash; 20 kept
draws in the window; family bases +0 / +400,000 / +800,000).

## 3. Used table and check
Used = X0's table (`x0/seed_rule.py used_ranges`) + X0's own fresh ranges (`SEED_DERIVATION_FRESH_W1.json`,
sha256 641b246a...) + X1's nine fresh ranges (`SEED_DERIVATION_X1.json`, sha256 a18ddd96...); used draw indices = X0's
list + X0's Task B window + X1's Task B window (7,760-7,819). Every X2 range, widened by 1,000,000 on each side, must
not meet any used range or another X2 range; every number below 2^31 - 1. Step rule: `s <- (s + 1) mod N` in the same
band, at most N steps, each recorded; no free slot = STOP (no other band is tried; nothing is generated).

## 4. Why no band can be dead (checked by the builder on 2026-10-19 with the program above)
- The five 1,000,000-wide bands: every slot is free. Their lowest seed 1,806,000,001 is more than 1,000,000 above
  X1's highest language-type seed 1,804,932,603, and each band starts 1,000,001 above the previous one's end.
- GB: 954 of 1,000 slots free. TB: 23 of 33 windows free. D34: 31 of 45 slots free.
- A dry derivation with a dummy line (not the owner's) printed `overlap_check: PASS`, every part `in_band: true`.

## 5. Text rule (E16 and F16)
A turn whose normalised text (lower case; only letters, digits, spaces; runs of spaces collapsed) equals any string
constant of the packaged English tests, the voice, the live trace, the faces lexicon file, the builder's fixtures, or
any turn of X1's `ENGLISH16_X1.json` is a hit; step that file's seed to the next slot (section 3), recorded.
