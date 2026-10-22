# Sign request: HELM-R1 X-REAL (the first exam built from other people's text)

**Why.** Every HELM-R1 result so far was scored on exams our own generators wrote. X-REAL uses text other people wrote,
for other reasons, before HELM existed: real cookbook recipes (Project Gutenberg, English Wikibooks), real everyday
sentences (Tatoeba, Google Taskmaster), and real kinds of file damage. You allowed these downloads ("FETCH X-REAL") and
accepted the eight design picks.

**What was fetched and pinned (2026-10-19, 0 USD).** 281 Project Gutenberg cookery eBooks + the catalog; the English
Wikibooks dump of 2026-10-01 (Wikimedia's own sha1 matched); the Tatoeba English export; Google Taskmaster at commit
`d92cb6af`. Skipped, with the reason written down: the USDA food list, the `ftfy` release and the Tatoeba CC0 list
(SOURCES.md gave no exact web address for them, and the build order allowed only exact addresses). One eBook (1979)
was left out because its header says it is copyrighted.

**What runs.** The same brain as waves 3b-5 (the licensed recipe brain, the English reader, the voice, the triad, the
cube store) and wave 4's Unity Eye, on four parts sampled blind by a separate custodian from your sign line:
- **S** — 128 real food sentences, one at a time. Does HELM write only what was said, and ask when it should?
- **R-ASIS** — 64 real recipes, HELM as it is. **R-REBOUND** — 64 real 2-3 ingredient recipes with the brain's
  recipe shape renamed to the recipe's own ingredients.
- **F** — 192 restarts with damaged or clean saved files. Does the Eye catch the damage, or fail safe? Does a plain
  file checksum do as well?

**Compared against.** Always-ask, a reckless keyword reader, an echo, HELM with its reader or voice off, the Eye
report-only, the after-write checklist, and a plain file checksum (WATCHDOG).

**What the builder already knows (from the practice book and the public frames only — not results):**
1. **The recipe arithmetic cannot be reached with true statements.** A batch made from exactly a recipe's listed
   amounts runs out of every ingredient at once, and the brain's own receipt accepts a lesson only when ONE ingredient
   runs out first. So the brain learns one ingredient per real recipe (15 of 16 practice recipes; each value exactly
   right) and never all of them (0 of 16). Parts R therefore measure honesty, not arithmetic.
2. **The designed recipe pairing almost never gives an answerable question** (4 and 0 answerable of 400, with two
   test rank strings). A guard was added so this cannot print "the math holds" with no math tested: expect
   `R_VACUOUS`. Changing the pairing ("pick a second recipe that has ALL the ingredients") would be your research
   choice and a reseal; the builder did not change it.
3. On the practice sentences HELM wrote "no water on hand" for lines like "Tom pulled Mary out of the water" (7 of 128
   practice sentences). The real exam may show the same.

**Marks (designer's thresholds, unchanged).** Real sentences: at most 2 wrong; at least 4 more right than always-ask;
fewer wrong than the keyword reader; at most 2 non-plain replies; the Eye quiet. Recipes: at most 2 wrong. Faults: no
false alarm on 64 clean restarts; every caught fault that the answer uses is held back. Hard gates include: the Eye
writes nothing, replay identical, no key ever reaches the machine, no network.

**A PASS would mean** a claim only about the named corpora (`NAMED_CORPORA_ONLY`), per part word. **It would not
mean** "HELM reads everyday English", real kitchens, real users, or anything about a transformer.

**Cost.** One small AWS machine (m6i.xlarge, us-west-2), about 8-12 minutes, about $0.03-0.10. Worst case about $0.70.
**Cap $1.00 (PROPOSED).** No ledger hold has been placed.

**Sign line (copy exactly):**

```
APPROVE X-REAL: outside-generator exam, sealed package c275daed, one attempt + one plumbing retry, cap $1.00.
```

Package `HELM_XREAL_20261019_SOURCE_XREAL.zip` sha256 `c275daed5ed26c6759543e8e89ebe2d54d7d750fe8b8f9bc957efe82ffa7bb6e`,
freeze `7c92a5891ae25d318245743c9310cba58fc4f42468b597a188eeb04c51e3506b`. The source pins (`SOURCES_PINNED.json`
`24cfb0d1…`) and frame pins are members of that freeze, so the line binds them too.
