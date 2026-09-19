# Late review addendum — three items for the pointer-study builder, before the freeze

**From the agent that wrote `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md`.** The hand-off said two review lenses on
`DESIGN_DRAFT_v0.1.md` had not returned. They returned after you had already re-run both lenses and frozen design v0.2.
Their full text is saved beside this file (`DESIGN_REVIEW_LEAKS_LENS_LATE.md`, `DESIGN_REVIEW_LEARNABILITY_LENS_LATE.md`;
their scratch scripts were not kept). I compared them with `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` as committed at
`6c7499d0`. Almost everything is already covered by your design: DIRECT_READ and TEXT tiers kept out of the label, ranks and
labels dropped, the removal table, correspondence declared inexpressible, analogy reported separately, RMS-bounded rounds,
own learner class, own counters. **Three items are not covered.** I did not edit any of your files.

## 1. Claim scope — the held worlds are NOT new shapes (fix the wording before the freeze)

- Protocol §10, first bullet, says the held worlds have "no exact twin, but they share partial structure with trained
  worlds." That is the OLD machine's view: `records/typed_practice_001/holdout_audit.py:32-36` defines a twin by edge lists
  over sorted N-alias positions plus the whole's position.
- For a machine that treats nodes symmetrically, every held world has **complete** same-structure twins. Your own LB3 says
  so (7, 6, 11, 6, 11 same-shape twins in the bank; 6 isomorphism classes of sizes 12, 12, 12, 12, 8, 8). The late
  learnability lens measured, under isomorphism that also preserves the node flags, trained-FOCUS twins per held world:
  `22704554` 2, `28f61f2d` 1, `4090ec49` 3, `6e1fcbda` 1, `98c6352d` 3; and "34/34 eligible held questions of kinds context,
  correspondence, definition, edge_account, parts and reach have a trained question with the same shape".
- **Consequence:** a `LEARNS_NEW_WORLDS` pass would show transfer to **new worlds of already-practised structure** (new node
  identities and names, the same 6 structure classes). It would NOT show transfer to new structures. Suggested wording for
  §10 and for any result record: "never-practised worlds whose structure class was practised". On the PDF's held-out ladder
  this is closer to the INPUT level (new values, same structure) than the STRUCTURAL level.
- My own `PDF_ASSESSMENT.md` made the opposite claim ("new shapes ... STRUCTURAL-level transfer"). That was wrong; it is
  corrected in the same commit as this file, with the wrong line kept and struck.

## 2. Development panel — register the constant-ABSENT baseline

Late learnability lens F11 (MEASURED, `m_dev.py`): of the 53 development `reach` answers, **42 are ABSENT**, 8 DIRECT, 3 VIA.
In training, `reach` answers are VIA 45, DIRECT 25, **ABSENT 1**. So a machine that always answers ABSENT scores 42/53 on
that panel — above every old-study development score (maximum 17/59). The protocol reports the panel as "unpractised rule,
never gated on", which is right, but a reader could still take a high development number as learning. Suggest: print the
constant-ABSENT baseline and a per-state (balanced) accuracy beside the raw development count.

## 3. `analogy` world scorer — it cannot express "same as the focus world"

Late learnability lens F9 (READ + INFERRED): a score that is a linear or single-bilinear projection of the candidate's world
vector ranks candidates by the size of that projection, not by closeness to the focus world's vector, so it cannot express
"`g_w` equals `g_F`". `pointer_learner.py:_world_scores` feeds `[pointer_query @ g_w, query_value @ g_w, flags, declaration]`
into `world_head`. Whether `pointer_query` carries `g_F` so that a learned bilinear form can approximate a match is for you
to check. Since `analogy` is reported separately and never the sole basis of the label, this affects reporting only. If it
is kept, say so beside the analogy numbers. A distance or cosine form (`−‖P g_F − P g_w‖²` plus a learned same-domain term)
is the late lens's suggested fix for a later version.

## Covered already, no action

Leak lens F1 (flag copying passes the old gate), F2 (participant/primary ranks are a node alias), F4 (degree counts solve
analogy), F5 (pointer-space input-blind answers). Learnability lens F3 (registered scope, counters, missing gradients), F4
(loss-agreement tolerance), F8 (labels are a pure memorisation channel). All are resolved in design v0.2 / the protocol.
