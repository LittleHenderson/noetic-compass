## Amendment A-TALK-10 (2026-10-22 PDT) — mouth v2: what changed while the corpus and lessons were made; written before the v2 seal

Status: appended after A-TALK-9; nothing above is edited. Each item is a fact of the work already done or a choice fixed now, before any seal, training or money.

**K1. More regular word forms (extends A-TALK-9 J1).** Measured on v1's lessons with every vocabulary list, the off-topic lessons were 581/620 writable; the misses were mostly doubled-consonant and comparative forms. `word_forms` now also adds the doubled-consonant forms (stop → stopped, stopping; jam → jamming; cut → cutting), +est, and for a final consonant + "y" the -ies / -ied / -ier / -iest / -ily forms (happy → happier). Tested first.

**K2. A possessive states its thing.** The lesson rule refused "You said Longmoor's line got rerouted through Cresswell in September." because it read the word as "longmoor's". Both the fact check and the invented-name check now drop a final "'s" before comparing (the runtime guard already split it correctly). Tested first. This alone moved 116 Anthropic replies from refused to passing.

**K3. Sense check layer 2 joins the guard (A-TALK-7 H1 F3).** The census (`mouth_v2/SENSE_LAYER2_CENSUS.json`, laptop GPU, 0 USD) on the 989 rated c59 lines: at threshold −0.607 (the mouth's own average log-probability per piece), it rejects 112 of the 162 rater-rejected chat lines that layer 1 missed (≥ half: holds) and 34 of 682 rater-preferred lines (5.0 %, ≤ 5 %: holds). Frozen as `sense_layer2_threshold` = −0.607. Caution, stated before the run: the threshold was measured on the v1 mouth; the v2 mouth's confidence scale may differ, which would change how often the fallback fires (F-FALLBACK is measured with layer 2 on).

**K4. Speed only.** The lock remembers each word's pieces (the lock now holds ~27,000 everyday words and is rebuilt per line); no change in what it allows. The 26 package tests still pass.

**K5. Who wrote what.** Vocabulary lists: written by deepseek or openai, kept by the other (37 lists: 3 levels, 3 larger level lists, 30 professions, irregular forms). Person lines: openai and deepseek (alternate batches of 60). Replies: anthropic (Claude helper agents, file mode), openai, deepseek — each new input gets up to three. Google: none (no free quota; its 190 v1 lines stay).

**K6. v1's lessons are reused.** v1's 1,083 inputs keep their ids, written lines and keys, styled "plain" (register A) or "warm" (register f) at level grade10, as v1's brief described them.

**K7. One extra rewrite round.** After all replies were in, every new reply that still broke a rule went back once to its own family with the reason (anthropic 117 items; deepseek 118 → 97 still refused). Still-refused replies are simply not lessons.

**K8. The exam.** 800 fresh styled readings (worlds from index 70000, every style and level), the v2 held-out person lines (453 after the person-line rules) and v1's held-out person lines (styled plain / warm, grade10); none of them in the lessons.

**K9. A small race, closed.** openai's 4 refused replies were rewritten while anthropic's checking prompts were being built, so an anthropic key could belong to the old text. Every openai line that went through that rewrite is left out of the lessons.

**K10. Checks by file mode are read in without touching v1's.** anthropic's checks (Claude helper agents) are read from their reply files into the copied v1 key file (`ingest_keys`); nothing is deleted.
