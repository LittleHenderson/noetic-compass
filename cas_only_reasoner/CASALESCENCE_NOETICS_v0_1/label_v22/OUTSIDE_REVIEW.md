# Outside review

Asked for model: `deepseek-v4-pro`. Answered by model: `deepseek-v4-pro`. Finish reason: `stop`.

Files sent:

- `02_LABELING_GUIDE_v2_2.md` (66479 bytes, sha256 `20cb3a79eb7cab4d90253630fd0c4aa19b0c0436dad357a1f055d68dc65e4b42`)
- `09_LABEL_AGREEMENT_PLAN_v2_2.md` (14350 bytes, sha256 `59ca2b2d39ac58833ee304e10373ef9be0b75b495829789851cafa1d65538eea`)
- `OWNER_SIGNOFF_SHEET.md` (2619 bytes, sha256 `9d2ebfcb2f69f466462af44dda04a2c0f5cb7e14a0bf817ce895ea67034d9649`)
- `OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json` (5576 bytes, sha256 `d7ae5b5e3bdff0903b3b9942d9a11281712a30e37ee55c7be94122f36bf23b7a`)
- `09_LABEL_AGREEMENT_PLAN_v2_1.md` (25993 bytes, sha256 `657413f77f182c7310071505e89d01452eb9e62cd97ac0c69d954051218430cd`)

## Reply, word for word

VERDICT: REJECT

**1. BLOCKER — Plan v2.2 §5 / sign-off item 2.** The plan still says the bar row is “clear entries, not a `^9` reached by reasoning,” and later: “The rule-15 row `'^9 reached by reasoning'` will show only entries a labeler flagged against the instructions.” The sign-off says “every clear Effect counts toward the pass mark.” These conflict. If one team obeys the guide and a second accidentally sets `"reached_by": "reasoning"`, that clear `^9` is excluded from the bar row and cannot pair with the first team’s unflagged `^9`. The core measure then depends on an instruction violation, not on the guide’s claimed design. The disclosure is not enough; the scorer should not count such a flag apart. Fix: have the checker reject any `reached_by` field, and have the scorer include every clear `^9`; delete the “not a `^9` reached by reasoning” exclusion from the bar row.

**2. MAJOR — Guide change table, row “E4’s `^7` label” / sign-off item 1.** The change table admits the draft the owner approved wrote “had served for years” but v2.2 changes the label to “for years.” The owner answered yes to a draft containing “had served for years,” and the sign-off says “the ten examples you approved.” He is therefore being asked to sign an example different from the one he approved. Fix: restore “had served for years,” or get an explicit owner approval for the changed label.

**3. MAJOR — Guide rule 4, last sentence.** “A being that is only spoken of is listed too. That last point is the operator’s reading of the ruling, not the owner’s words.” This is a study-written presence rule for `^1`, going beyond the owner’s sentence on Mind. It is disclosed, but it remains in force if the owner signs. Fix: strike the operator’s extension unless the owner expressly adopts it; otherwise rule 4 should end after the owner’s Mind sentence.

**4. MAJOR — Rule 15(a)–(d) boundaries.** Two careful labelers will still part widely here. First, (a) versus (d): (a) requires words like “reminded,” “knew,” “meant,” while (d) covers a sign “just before” the idea with “no word links them.” “Just before” and whether “At once” links are not defined; X1 and E9 both turn on that. Second, (b) versus (a): “brings the conclusion to Mind as a trigger does” is subjective; E10 treats “told her” as a trigger, but a labeler could read the same sentence as reasoning. Third, (c) says when a sign and working-through bring the same conclusion, write the `^9` once “quoting the sign’s `^8`,” but does not say how to choose that `^8` when several triggers are present. Fix: give a closed link-word list for (a) and a default of (d) otherwise; make (b) require an explicitly trigger-like verb independent of reasoning verbs; and specify the `^8` choice in (c).

**5. MAJOR — Changes not all sourced to the owner’s recorded answers.** The owner’s recorded answer settles recognizing a sign, uncertain memory following a sign, evidence as Cause, Male only inside a named whole, and the book’s physical examples. But two operator changes go beyond those answers: the E4 label change above, and rule 15(c)’s “write its `^9` once, quoting the sign’s `^8`.” The rule may be sensible, but it is not the owner’s recorded decision. Fix: list it explicitly in the sign-off sheet as requiring owner adoption, or remove it.

On the remaining checks: the worked examples E1–E10 and X5/X6 appear consistent with the rules as written, apart from the E4 issue. The pass/failure claims in plan §3 and the sign-off’s “What to expect” are appropriately limited: pass means inter-team agreement only, not correctness; failure is a method failure for that Noetic, not a claim about CAS. The measure, pass marks, minimum counts, outcome words and validity rules are otherwise frozen and copied from v2.1, but the vestigial reasoning-flag exclusion in scorer/plan is a pre-label defect and must be fixed before the owner signs.
