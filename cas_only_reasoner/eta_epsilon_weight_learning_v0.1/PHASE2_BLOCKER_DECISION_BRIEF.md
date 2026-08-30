# PHASE 2 BLOCKER — DECISION BRIEF (for a v0.2 amendment)

Filed 2026-08-30. Phase 2 dev smoke returned a negative result. Phases
3-8 cannot honestly proceed until two decisions are made. This brief
lays out the options. It does NOT choose for you (the negative-result
law forbids me improvising the fix). Pick one option per decision and I
run Phase 2 for real as v0.2.

## The finding, restated

Role labels in templated active/passive sentences are decidable from the
words alone. "was ... by" marks the voice; the voice fixes the roles. So:
bag-of-words surface baseline = 1.000, hidden-state probe = 1.000, margin
0.000 (need >= 0.10). The readout shows nothing beyond surface.

The deeper problem, stated plainly: **for a task whose answer is marked on
the surface, there is no CAS-specific signal (and no signal of ANY
taxonomy) beyond surface to exploit.** So this task, as framed, cannot
show that CAS adds value over plain surface features. That is the real
block, not just a bad label choice.

## DECISION A — the readout target (must be surface-resistant)

- **A1. Model-correctness probe.** First measure Qwen's OWN behavior:
  ask "who did the chasing?" for each sentence, score right/wrong. Then
  probe whether hidden states predict the model's correctness. Surface-
  resistant IF the model's errors are not themselves surface-determined.
  Directly tests the real failure (role reversal). RISK: if the model is
  wrong on all passives and right on all actives, correctness is again
  surface-decodable (bag-of-words wins) and this too hits the wall.
- **A2. Surface-matched minimal pairs.** Stimuli where the same surface
  tokens do not fix the roles. HONEST WARNING: in English, active/passive
  roles are always lexically marked, so this is very hard to build within
  templated data; likely futile.
- **A3. Change the task.** Pick a skill whose answer is NOT surface-
  marked (a small inference / disambiguation task), where a semantic
  readout can beat surface. Bigger change; strongest chance of showing
  CAS-or-any-taxonomy value.

My honest read: A1 or A3. A2 is likely a dead end.

## DECISION B — CAS-40 labeling

- **B1. Drop the 40-state CAS framing for this task.** Use only the
  empirical behavior direction (already what Decision 6 does). HONEST
  CONSEQUENCE: the study becomes a generic interpretability-guided
  training study. It can NOT claim CAS-specific value; "CAS" would be a
  name, not a load-bearing part.
- **B2. Build a CAS-40 labeler for these sentences.** Needs a reliable
  English -> CAS-40 map. HONEST WARNING: this is exactly the component
  that already failed (0/37). High risk, likely large effort.
- **B3. Pick a task where CAS-40 labels are meaningful and available**
  (pairs with A3). Then the matched-non-CAS-taxonomy control can actually
  test whether CAS beats a generic taxonomy.

My honest read: B1 makes the study honest but non-CAS-specific. B3 is the
only path that lets the study test CAS-specific value, and it depends on
having (or building) real CAS-40 labels.

## The fork in one sentence

Either accept a **generic** interpretability-guided-training study (A1 +
B1) — real, publishable, but not evidence that CAS specifically helps — or
commit to a **task with a non-surface-marked target and real CAS-40
labels** (A3 + B3) to actually test CAS-specific value, at higher cost and
with the CAS-40 labeler risk on the table.

## What I need from you

One choice for A, one for B. Then I write the v0.2 amendment, re-run
Phase 2 for real under it, and continue. Until then Phases 3-8 stay
unstarted; running them now would be either fabrication or a banned
mid-flight rescue.
