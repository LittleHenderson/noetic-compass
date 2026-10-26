# CTT growth and the brain ratio — what the record says (2026-10-26)

Status: search result and proposed policy. No numeric size ratio was found in the local record; what exists is a
1:1 **checkability** rule and a growth rule. Both are quoted below.

## 1. What I searched, and what I found

| Searched | Result |
|---|---|
| `docs/` for CTT/brain ratio, 1:1, interpretability ratio | 96 hits for "1:1", none about CTT size; the CTT design doc is the substantive one |
| `Documents\Codex\2026-10-19\` (the CTT design set) | no "1:1" or size ratio between CTT and the brain |
| `Documents\Codex` broadly | blocked in places by permission errors; nothing found in readable areas |
| `sessions/` chat logs for "ratio" + CTT/brain | no matches |

**Conclusion: the numeric ratio the owner remembers is not saved in any file I can read.** It may have been in a chat
that was not written to disk. I will not invent a number and attribute it to another LLM.

## 2. What IS on record (the CTT design of 2026-10-19)

From `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\ARCHITECTURE.md`:

- **Hard boundary, owner ruling 2026-10-19:** "if interpretablity is an issue let's just separate the cas transformer
  from the brain we already built and have". The translator has its own folder, process, parameters, weights file and
  manifest; it shares no tensor and no write path with the brain.
- **The brain stays readable:** 68 learned values in RB1g2 (32 requirements, 32 ceilings, 4 bindings) and 32
  parameters in RB-det c26. Nothing the translator does can reach those values.
- **1:1 checkability:** every spoken sentence must be accepted by the voice's read-back or by the reader's checker.
  The translator "suggests"; a deterministic check accepts or refuses. Refused suggestions cost nothing.
- **No-harm gates:** H-NOHARM — brain exams come out identical with the translator on and off, only wording may
  differ; H-REMOVE — deleting the translator folder reproduces the translator-off digests exactly.
- **Size rationale:** 9.6M parameters, and each part has a stated job. **"When to grow: only if the frozen test shows
  UNDER-fitting, that is, the model misses the training mark itself. If it fits training and fails held-out, that is
  not a capacity failure; more parameters would make it worse."**

## 3. What this means for the v3 result

The v3 mouth reached a **training loss of 0.0757** — it fits its training data. Its failure is held-out variety
(distinctness 0.659 because there are only eight realisations per tag). Under the project's own rule, **that is a data
problem, not a capacity problem, so CTT should NOT be grown yet.** Growing it now would follow exactly the failure mode
the design warns about.

## 4. Proposed policy (the ratio, stated as rules rather than a parameter count)

The interpretability ratio that matters is **1:1 checkability**, not a parameter ratio:

1. **One checkable basis per sentence.** Every utterance must map to a licensed frame or brain receipt. An utterance
   with no basis is refused. This is already implemented in `speech_gateway.py`.
2. **Brain frozen.** The brain's learned value count does not change when CTT changes. No shared parameters.
3. **Switch-off invariance.** With CTT off, every brain answer, receipt digest and exam result is unchanged
   (H-NOHARM/H-REMOVE).
4. **Growth only on under-fitting.** CTT may grow only when it misses its own training mark. Held-out failure goes to
   data first.
5. **If a numeric cap is wanted**, the honest starting point is the current **9,585,823 parameters**; any cap above it
   should be a fresh owner decision with a stated reason, not a remembered figure.

## 5. What I need from the owner

Either the remembered number (or where it came from), or agreement to adopt the five rules above as the ratio. Until
then I will hold CTT at its current size and spend the effort on data, which is where the v3 evidence points.
