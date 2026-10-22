# EYE-ACT-1 amendment A2 — hard gate H10 separates "not yet noticed" from "invented" (written 2026-10-21 PDT, AFTER
# the practice run on dev seeds and BEFORE the seal and before any scored world exists)

Disclosed: this change was chosen after reading the PRACTICE numbers (dev seeds `dev:1`–`dev:8`, never scored).

What practice showed: on the F4 (lost source) practice world, HOLD (A1) and ACT (A2) answered P2 WRONG. The fault was
planted right after a cadence sweep, so neither had looked yet; their P2 answer was the SAME damaged answer the no-Eye
arm A0 gave on that world (value and limiting ingredient equal). At P3, after the next sweep, A1 held and A2 asked. The
frozen H10 ("on F4, A1–A3 give 0 WRONG items") counts that as invention and reads INCONCLUSIVE. It is not invention:
the Eye introduced no value; it had not looked yet. That miss is already counted where it belongs, in the WRONG mark.

Change (instrument only):
- H10 `G_NO_INVENT` — on F4, an eye arm's WRONG item is an invention only if its answer (value or limiting ingredient)
  differs from A0's answer on the same world and probe. Gate: 0 inventions. WRONG items equal to A0's stay WRONG in the
  marks and in the harm rule (which already exempts them: harm needs A0 RIGHT or ASK where the eye arm is WRONG).
- One reader test is added: a WRONG equal to A0's is not an invention; a WRONG different from A0's is.

Nothing else changes: no arm, fault, mark, other gate, threshold, status word or prediction. Practice numbers stay
unscored and are reported as practice.
