## Amendment A-TALK-9 (2026-10-22 PDT) — mouth v2: the vetted vocabulary joins the lock; off-topic template lines are not lessons; written before that code

Status: appended after A-TALK-8; nothing above is edited. Where it disagrees with A-TALK-7 H1 / H4, this governs.

**Why (measured on v1's 2,831 lessons, 0 USD, laptop).** With A-TALK-7's word-list rule alone, lessons writable under the lock: ANSWER 547/549, SAYBACK 537/539, ASK 560/565, WORLD 154/159, SELF 130/144, SMALL 157/175, **OFF 407/700**. The off-topic misses have two causes: (1) "telling" (72 lessons) appears only in v1's off-topic TEMPLATE, which itself builds broken English ("Thanks for telling me. What happened with the snowed?"); (2) a long tail of ordinary words each used once ("snow", "birthday", "early", "head", "picking") that the "seen in ≥ 2 lessons" rule drops.

**J1. The vetted vocabulary joins the lock.** The lock's everyday words = A-TALK-7 H1's words ∪ every word of the corpus vocabulary lists (three reading levels, 30 professions; each word kept only when a second AI family agreed it fits) ∪ their regular forms (+s, +es, +ed, +d, +ing, +er, +ly, and a final "e" dropped before +ing / +ed), minus fact words (names, numbers, months) and WORLD_NOUNS, exactly as before. These are everyday words, not facts: the promise "never a name, number or month the input lacks" is unchanged and still enforced by the lock.

Measured again with the three reading-level lists (about 700 words each) and J1–J2: OFF 542/620, SMALL 164/175 — still under 95 %, the misses being irregular forms ("heard", "gave", "kept"), contraction pieces ("doesn" of "doesn't") and everyday words the lists lack ("birthday", "calendar"). So the corpus adds, made and vetted the same way: a second, larger everyday list per level (about 1,500 more words each, different from the first) and a list of the past and past-participle forms of common irregular verbs. The pieces of English contractions (doesn, didn, isn, wasn, aren, weren, hasn, haven, hadn, couldn, wouldn, shouldn, won, can, t, s, re, ve, ll, d, m) are a fixed written list in the code.

**J2. Off-topic template lines are not lessons.** The v1 off-topic template (`helm_talk.off_react` + `off_question`) can build broken English, so its lines are dropped from the lessons. It stays the runtime fallback only (as A-TALK-5 F3 says, the fallback is the safety net, never the way HELM normally talks). The other situations' template lines stay under the 10 % cap.

**J3. The 95 % gate (A-TALK-7 H1) is unchanged** and is measured after J1 and J2 on every remaining lesson.
