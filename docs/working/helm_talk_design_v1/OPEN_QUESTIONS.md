# Open questions — the owner's decisions for the talk packet v1 (2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Each item is the owner's to decide. The designer has decided none of them. Each carries one line of recommendation so the owner can answer with one word. Operational details (folder names, instance size, retention) are not here; they are the operator's.

1. **Who writes the human turns, and how many.** Four writers (the owner + three named people), 32 singles + 4 dialogues each → 128 singles + 16 dialogues against floors of 112 + 16 (DESIGN §3.3).
   Recommendation: four writers; name the three to the custodian only.

2. **May the owner's own typed turns be an exam stratum?** The owner has read this packet's example sentences and the kind list; the three others see kind codes only. If yes, the owner's slice is labelled and reported separately; if no, floors drop to 12 per kind / 12 dialogues and the word carries `KH_THREE_WRITERS`.
   Recommendation: yes, as a labelled stratum; the marks hold with or without it and the report shows both.

3. **The training line and cap.** `TALK TRAIN at 3 USD` (cap 3.00 USD; expected about 2.2 USD; c45's 1.40 USD on 227,497 rows is the yardstick; about 351,500 rows here). A separate approval from the exam.
   Recommendation: approve the line as written; it is the only new money above 1 USD in this packet.

4. **Are LLM-written turns allowed in training (stratum T2, about 4,000 rows, labelled `LLM_WRITTEN`, under CTT-2R's pool rules, never human exam turns)?**
   Recommendation: yes, as a separate labelled stratum; it is the only source of sentence shapes the rule generator cannot invent, and it is kept out of every exam by hash.

5. **The margin for EARS_GAIN.** +8 singles and +4 dialogue turns over EARS_OFF and over KEYWORD_ROUTER; +4 over RETRIEVAL_VOTE (CTT-1 / CTT-2R's margins).
   Recommendation: accept; a smaller margin would let one or two keying disagreements decide the word.

6. **Does "normal conversation" include non-kitchen topics at all, and if so what may HELM say about them?** The design scores an `OFF` turn on not saving stock and not recipe-speaking only. Options: (a) acknowledge in one short line and say nothing more ("Sounds like a big move for her."), (b) acknowledge and keep the fact in `user_facts` (verbatim, at most 20) so "what do you know about me" can recall it, (c) refuse the topic in plain words ("That's outside what I can help with here").
   Recommendation: (b): keep the fact verbatim, acknowledge in one line, never comment on it; the content of the line is reported, never scored, in v1.

7. **The exam line and cap.** `TALK EXAM at 1 USD` (cap 1.00 USD; one m6i.xlarge-class CPU host; expected 0.03–0.15 USD) — needed because the ears cannot run on the laptop (spec §7.82: torch needs 475 MiB; per-process limit 300 MiB).
   Recommendation: approve together with Q3 so training and exam need no third round trip; expect under 0.20 USD.

8. **Which HELM cut carries the exam.** The thread head after the reader-gap builds D1–D6 (§7.109, branch `claude/helm-reader-gap-build-20261021`) are merged and HELM's suites pass; or the current head `420f070b` if the builds are not merged when the K-H turns are ready.
   Recommendation: wait for D1–D6; the ears are only called where the reader asks, so the reader's asks must be the honest ones first.

9. **Seed bands.** HUMAN 2,018,000,001–2,019,000,000; SYNTH 2,020,000,001–2,021,000,000; NOISE 2,022,000,001–2,023,000,000 (above wave 7 v6's 2,017,000,000).
   Recommendation: accept; the next free band after this packet starts at 2,024,000,001.

10. **Who builds.** The same designer, or a separate builder blind to this packet's forecasts (§11) and to the K-H files?
    Recommendation: a separate builder, as wave 7 separated builder and custodian; the designer reviews the FIX FIRST record only.

11. **The `NOTHING_TO_SAVE` token.** One new CAS-side special token in the translator's vocabulary (8,349 → 8,350). It is an output of the ears, never a CAS symbol a person sees.
    Recommendation: accept; without it the ears cannot be silent on purpose, only silent by failure.
