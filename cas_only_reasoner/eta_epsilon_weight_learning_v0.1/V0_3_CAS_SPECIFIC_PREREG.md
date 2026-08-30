# v0.3 CAS-SPECIFIC PRE-REGISTRATION (B1 vetoed) — AWAITING OWNER SIGN-OFF

Filed 2026-08-30. B1 (drop the CAS framing) is VETOED. This pre-registers
a genuinely CAS-specific test. Per the lesson from the goal-substitution
violation, this design is pre-registered and **not self-authorized** — the
claim-bearing run waits for owner sign-off. An EXPLORATORY preview
(non-claim-bearing) is reported separately to inform the decision.

## The central dilemma (state it before anything)

A CAS-specific readout faces a fork, and both prongs are hard:
- A CAS label that is **mechanically derivable from the words** (e.g. the
  Noetic implied by the verb) is **surface-decodable** -> a bag-of-words
  baseline reads it, so the readout cannot beat surface. This is exactly
  the Phase-2 wall.
- A CAS label that is **NOT surface-derivable** needs a reliable
  English->CAS-40 labeler -> which does not exist (the 0/37 failure).

So a valid CAS-specific readout must thread the needle: a CAS coordinate
that is **semantic** (the model represents it) and **generalizes beyond
the surface words** (tested on HELD-OUT vocabulary), AND beats a
**matched non-CAS semantic taxonomy** of equal size (not just surface, not
just a random partition). If CAS only ties a generic semantic taxonomy,
CAS-specificity is NOT established (it is just semantics).

## Readout target (proposed)

A CAS Noetic coordinate over 4 Noetics, each instantiated by a distinct
verb set (mechanical labels, no LLM): ^2 Positive/attraction, ^3
Negative/aversion, ^6 Male/decomposition, ^8 Above/Cause/triggering.
Sentences "the A <verb> the B." Lexical split holds out verbs per Noetic,
so surface memorization is controlled.

## Controls (the missing ones, now required)

- surface bag-of-words;
- random-partition matched (same verbs, arbitrary equal-size groups) —
  tests generalizable structure vs memorization;
- **matched non-CAS SEMANTIC taxonomy** of equal size (a genuine
  alternative categorization, e.g. concreteness/animacy or a topic split)
  — the decisive CAS-specificity control.

## Gate (CAS-specificity)

On held-out verbs, the CAS-Noetic readout must beat BOTH surface AND the
matched non-CAS semantic taxonomy (AUROC/accuracy, margin >= 0.10, CI
excludes zero). If it beats surface but ties the matched semantic
taxonomy -> `CAS_SPECIFICITY_NOT_ESTABLISHED_GENERIC_SEMANTICS`.

## Honest prediction (pre-registered)

I expect the CAS-Noetic readout to beat surface on held-out verbs (the
model represents attraction/aversion/etc. semantically) but to **tie a
matched non-CAS semantic taxonomy** — i.e. the signal is generic
semantics, not CAS-specific. If so, the honest verdict is CAS-specificity
not established. A genuine CAS-specific win requires CAS to capture
structure a matched semantic taxonomy cannot.

## Discipline

Pre-registered, not self-authorized. No claim-bearing run, no ledger
change, until the owner signs off on this design (readout target, the
matched-non-CAS-semantic control choice, gates, thresholds, seeds). The
EXPLORATORY preview below does not license any claim.
