# Dataset Scout — Q&A / Direct-Answer Discipline Candidates (X2)

**Date:** 2026-05-07
**Author:** dataset-scouting agent (X2 deliverable)
**Scope:** External Q&A datasets evaluated for the CAS-Native v1 training mix, specifically to teach **direct-answer discipline** — answer the question, stay on topic, terse when terseness is appropriate, hedge or say "I don't know" when warranted.
**Out of scope:** Dialogue/instruction (X1), casual/OOD/refusal (X3), and any compiler-fluency CAS data (Path D handles that).
**Companion docs read first:**
- `docs/working/path_B4_human_relevance_failure_2026_05_07.md` — the rambling failure mode this slice is designed to fix.
- `docs/working/path_D_compiler_fluency_curriculum_2026_05_07.md` §11 — confirms external corpora are admitted only to teach **conversational discipline**, never as CAS-grounded supervision.
- Memory `feedback_audit_corpus_before_proposing_reuse.md` — every candidate sample-read before recommending.

## Summary

The B-4 audit failed for one specific reason on notation-task prompts: the model produced reflective monologues instead of direct answers. The Tier 3 corpus taught "say something thoughtful," not "answer the question." The fix on the corpus side is a small, high-quality slice of external Q&A data with one job — **discipline of answering**.

I evaluated 7 candidates across four answer-style profiles:

1. **Short-extractive factoid** (terseness discipline) — SQuAD 2.0, Natural Questions, TriviaQA, WebQuestions.
2. **Mixed short/long well-formed** (concise but complete sentence answer) — MS MARCO.
3. **Multi-turn conversational short** (acknowledge-prior-context discipline) — CoQA.
4. **Long-form explanatory** (on-topic explanation without rambling) — ELI5 (sentence-transformers mirror).
5. **Multi-hop reasoning short answer** (eval-only candidate) — HotpotQA.

The headline finding: **license is the dominant filter, not content quality.** Several otherwise excellent candidates (Natural Questions, SQuAD 2.0, HotpotQA, CoQA — all CC-BY-SA, and TriviaQA / WebQuestions / MS MARCO with unspecified or unclear licenses) are flagged for legal review before commercial inclusion in CAS-Native v1 weights, because the v1 model is downstream of USPTO #64/037,173 and any commercial Noetic Compass deployment.

Top recommendation for inclusion is **MS MARCO well-formed answers** as the terseness-with-completeness anchor (real Bing user queries, mixed length, sentence-grade answers) IF MSR's research-license terms permit weights-downstream use; otherwise, fall back to **a license-clean slice of SQuAD 2.0 + ELI5 (sentence-transformers mirror)** with IP attorney sign-off on CC-BY-SA-4.0 derivative-work treatment.

The X2 slice should be small — target **5K–15K records total**, sampled across answer-length buckets, not bulk dumped. Rationale: this is conversational-discipline *correction*, not a knowledge-injection corpus. Path D will own the CAS knowledge.

## Per-candidate evaluation

### 1. Google Natural Questions (NQ) — `google-research-datasets/natural_questions`

- **Source URL:** https://huggingface.co/datasets/google-research-datasets/natural_questions
- **License:** **CC-BY-SA-3.0**. Flagged for commercial concern. Share-alike clause is the legal hot spot — any model trained on NQ may be argued to be a derivative work; CC-BY-SA-3.0 is *not* compatible with proprietary commercial release without IP attorney sign-off. (See compliance table.)
- **Size:** ~315K records total (307,373 train + 7,830 validation). Generated dataset 99.8 GB on disk (HTML documents inflate size).
- **Schema:** Document (title/URL/HTML/tokens), Question (text/tokens), Annotations (long_answers, short_answers, yes_no_answer). Supports `-1` candidate_index = "no answer" and `-1` yes_no = "no yes/no answer."
- **Sample readings (verbatim from card):**
  1. "when is the last episode of season 8 of the walking dead"
  2. "in greek mythology who was the goddess of spring growth"
  3. "benefits of colonial life for single celled organisms"
  4. "how many season of the man in the high castle"
  5. "who was the first ministry head of state in nigeria"
  6. "how many nominations does game of thrones have"
  7. "what is the name of the most important jewish text"
  8. "until we meet again filipino soap episode 10"
  9. "what is the name of spain's most famous soccer team"
  10. "when was the first robot used in surgery"
- **Fit for CAS-Native v1:**
  - **Question style:** Real anonymized Google search queries — extremely high signal for "what does an actual user prompt look like" (real-world OOD distribution). This is the strongest property for fixing B-4's casual-prompt failures.
  - **Answer-length profile:** Both short answers (single span, often 1–5 tokens) AND long answers (paragraph-length context) supported. The short-answer slice is the terseness-discipline gold.
  - **"I don't know" handling:** Built-in via `candidate_index: -1`. Teaches the model that some questions don't have answers in the provided context — directly maps to B-4's "no CAS signal detected" routing problem.
  - **Real user queries:** Yes. Highest realism of any candidate evaluated.
- **Concerns:**
  - License (CC-BY-SA-3.0). Hard blocker without IP attorney clearance for derivative/commercial use.
  - Size: 100GB on disk is overkill — would only sample 5K–10K records.
  - Some queries are search-fragments not full sentences ("benefits of colonial life for single celled organisms" — no question word). Style-mismatched against assistant chat.
- **Verdict:** **Conditional A.** Best content fit; license is the gate.

### 2. CoQA — `stanfordnlp/coqa`

- **Source URL:** https://huggingface.co/datasets/stanfordnlp/coqa (Kaggle mirror also exists)
- **License:** **Multi-licensed by source segment**. Literature/Wikipedia portion CC-BY-SA-4.0; MCTest children's stories under MSR-LA; RACE under custom license; CNN under Apache-2.0. No single coherent license — must filter by source.
- **Size:** ~8K conversations / 127K questions total (7,199 train / 500 validation). 58 MB downloaded.
- **Schema:** `source`, `story`, `questions: List[str]`, `answers: {input_text, answer_start, answer_end}`. `-1` answer_start = unanswerable.
- **Sample readings (verbatim from card):**
  1. "When was the Vat formally opened?" → "It was formally established in 1475"
  2. "what is the library for?" → "research"
  3. "for what subjects?" → "history, and law"
  4. "and?" → "philosophy, science and theology"
  5. "Where was the Auction held?" → "Hard Rock Cafe"
  6. "How much did they make?" → "$2 million."
  7. "How much did they expected?" → "$120,000"
  8. "Was Budapest always one city?" → "no"
  9. "How many was it?" → "two"
  10. "What was one called?" → "Buda"
- **Fit for CAS-Native v1:**
  - **Question style:** Multi-turn conversational. Strong coreference dependence ("and?", "why?", "what else?"). This is the only candidate evaluated that explicitly trains the model to **stay on the conversational thread** — directly counters B-4's tendency to drift into unrelated reflective prose.
  - **Answer-length profile:** Almost all answers 1–15 tokens. Sometimes single-word ("research", "no", "two"). Strong terseness signal.
  - **"I don't know" handling:** Built in via `-1` answer_start. Used sparingly — most examples have valid spans.
  - **Real user queries:** No — researcher-curated dialogues over passages. Mid signal for OOD.
- **Concerns:**
  - License heterogeneity. The Apache-2.0 CNN slice and the CC-BY-SA-4.0 Wikipedia/literature slice have very different commercial profiles — must select carefully.
  - Multi-turn structure means single-turn extraction loses the load-bearing context. Either include conversation history (token cost) or accept that single-turn samples drop the coreference resolution discipline.
- **Verdict:** **Conditional B.** Excellent terseness + multi-turn, but license-fragmented and multi-turn-context-heavy. Best used as the Apache-2.0 (CNN) slice only.

### 3. SQuAD 2.0 — `rajpurkar/squad_v2`

- **Source URL:** https://huggingface.co/datasets/rajpurkar/squad_v2
- **License:** **CC-BY-SA-4.0**. Same share-alike concern as NQ.
- **Size:** 142,192 records (130,319 train + 11,873 validation). 17.7 MB.
- **Schema:** `id`, `title`, `context`, `question`, `answers: {text: List[str], answer_start: List[int]}`. Empty `answers.text` = unanswerable (~50K of 142K).
- **Sample readings (verbatim from card):**
  1. "When did Beyonce start becoming popular?" → "in the late 1990s"
  2. "What areas did Beyonce compete in when she was growing up?" → "singing and dancing"
  3. "In what city and state did Beyonce grow up?" → "Houston, Texas"
  4. "When did Beyonce leave Destiny's Child and become a solo singer?" → "2003"
  5. "In which decade did Beyonce become famous?" → "late 1990s"
  6. "In what R&B group was she the lead singer?" → "Destiny's Child"
  7. "What album made her a worldwide known artist?" → "Dangerously in Love"
  8. "Who managed the Destiny's Child group?" → "Mathew Knowles"
  9. "Who was the first person to notice Beyonce's singing ability?" → "Darlette Johnson"
  10. "When did Destiny's Child end their group act?" → "June 2005"
- **Fit for CAS-Native v1:**
  - **Question style:** Curated, well-formed, factual. Single-turn. Lower realism than NQ but cleaner and more uniformly question-shaped.
  - **Answer-length profile:** Heavily short — 1 to ~5 tokens dominant. Strongest terseness signal of any candidate.
  - **"I don't know" handling:** ~35% of SQuAD 2.0 questions are adversarially-written unanswerables — the headline feature. This is the **gold-standard "abstain when there is no valid answer" training signal** for the B-4 OOD-routing failure.
  - **Real user queries:** No — crowdsourced over Wikipedia passages. Curated.
- **Concerns:**
  - License (CC-BY-SA-4.0). Hard blocker without IP attorney clearance.
  - Curated style means model learns Wikipedia-comprehension language, not casual-user language.
  - Extractive answers are spans — model trained on these may produce ungrammatical span fragments instead of full sentence replies.
- **Verdict:** **Conditional A.** Cleanest abstention training data available; license is the gate. The 50K unanswerables are individually the most valuable record cohort across all candidates evaluated, for the specific "abstain on no-CAS-signal" routing failure.

### 4. MS MARCO — `microsoft/ms_marco`

- **Source URL:** https://huggingface.co/datasets/microsoft/ms_marco
- **License:** **Not specified on HF card** (page literally says "More Information Needed"). Original MS MARCO release page on Microsoft's site uses a custom non-commercial research license — must verify directly. **Hard flag for commercial use** until verified.
- **Size:** ~1.1M records total (v1.1: 102K; v2.1: 1,010,916).
- **Schema:** `passages: {is_selected, passage_text, url}`, `queries: {query, query_id, query_type}`, `answers: {answers, wellFormedAnswers}`. `query_type` ∈ {description, numeric, entity, person, location}.
- **Sample readings (verbatim from card):**
  1. "what is rba" → "Results-Based Accountability is a disciplined way of thinking and taking action that communities can use to improve the lives of children, youth, families, adults and the community as a whole."
  2. "was ronald reagan a democrat" → "Yes"
  3. "how long do you need for sydney and surrounding areas" → "20-25 minutes"
  4. "price to install tile in shower" → "$11 to $22 per square foot"
  5. "where are the lungs located in the back" → "Inside the rib cage."
  6. "what is a conifer" → "A tree or shrub which produces distinctive cones as part of its sexual reproduction."
  7. "what is rappelling" → "Rappelling is the process of coming down from a mountain that is usually done with two pieces of rope."
- **Fit for CAS-Native v1:**
  - **Question style:** Real Bing search queries — same realism property as NQ. Highest of the curated alternatives.
  - **Answer-length profile:** **The mixed profile is the killer feature.** Short answers ("Yes", "20-25 minutes"), short sentences ("Inside the rib cage."), and well-formed full-sentence definitions. The `wellFormedAnswers` field is specifically grammatically-complete sentence answers — closest match to "say it as a competent assistant would" of any candidate.
  - **"I don't know" handling:** Implicit via `is_selected` flagging on passages; not as clean as SQuAD 2.0's adversarial unanswerables.
  - **Real user queries:** Yes — 100K+ from real Bing logs.
- **Concerns:**
  - License unclear on HF card. MS MARCO's original terms (per upstream) are non-commercial research-only. **This is likely a hard blocker** for CAS-Native v1 commercial weights.
  - Mid-2010s Bing-era queries — slight stylistic dating but not a problem at this scale.
- **Verdict:** **Conditional A+ on content; D on license** until verified. If the license question can be resolved, MS MARCO `wellFormedAnswers` is the single best training-discipline data found in this scout.

### 5. ELI5 (sentence-transformers mirror) — `sentence-transformers/eli5`

- **Source URL:** https://huggingface.co/datasets/sentence-transformers/eli5
- **License:** **Not explicitly specified.** Source data is from Reddit r/explainlikeimfive — Reddit ToS plus Reddit user-content posture is now (post-2023 API restrictions) hostile to commercial training. **The canonical `eli5` HF page is 404 / deprecated** — likely takedown-related. The sentence-transformers preprocessing is incidentally still available but inherits the same upstream concern.
- **Size:** 325,475 question-answer pairs / 113 MB.
- **Schema:** Two columns: `question` (19–300 chars), `answer` (28–1.02k chars).
- **Sample readings (verbatim from card):**
  1. Q: "In football whats the point of wasting the first two plays with a rush — up the middle — not regular rush plays i get those"
     A: "Keep the defense honest, get a feel for the pass rush, open up the passing game. An offense that's too one dimensional will fail. And those rushes up the middle can be busted wide open sometimes for big yardage."
  2. Q: "How do muscles grow?"
     A: "...the basic idea that I understand is that your muscles rip and tear on a microscopic level when you are working out, and the harder you push those muscles, the more they rip..."
  3. Q: "Why does the water from my kitchen faucet taste different than the water from my bathroom faucet?"
     A: "Yes, but the pipes going to one place could have a build up that's changing the taste or the composition of the pipes can be different, i.e. pvc pipes going to your kitchen, but copper pipes to your bathroom."
  4. Q: "Why are the insides of Ovens Dark and Not Metallic or Mirror Like?"
     A: "How often do you polish the inside of your oven? I suspect a big reason would be just to keep the interior from quickly looking horrible."
- **Fit for CAS-Native v1:**
  - **Question style:** Casual, often grammatically informal — best match for B-4's casual-prompt distribution ("Bro I don't know," "this is wack as fuck"). The colloquial register here directly counters the formal-reflective register the v0 corpus instilled.
  - **Answer-length profile:** Long-form explanatory (28 to ~1k chars; mid-range is 100–500 chars). This trains a different discipline: **on-topic explanation without rambling**. ELI5 answers are remarkably on-task — the social pressure of the subreddit is anti-tangent.
  - **"I don't know" handling:** Not built-in.
  - **Real user queries:** Yes — actual Reddit posts.
- **Concerns:**
  - Reddit-derived content has commercial-use legal risk that has hardened post-2023.
  - Casual register sometimes shades into low-quality crowd-answer noise (sample #2 quoted as an opener: "the basic idea that I understand is that..." — exactly the "ramble before answer" pattern we're trying to remove).
  - Strict filter required: must select for terse openers + on-topic body, reject opener-hedge patterns.
- **Verdict:** **Conditional B.** Casual register is unique among candidates; sample quality is uneven and the Reddit license picture is genuinely murky in 2026. If used, must apply a hard quality filter.

### 6. TriviaQA — `mandarjoshi/trivia_qa`

- **Source URL:** https://huggingface.co/datasets/mandarjoshi/trivia_qa
- **License:** **Unspecified** ("University of Washington does not own the copyright"). Hard flag.
- **Size:** ~847K rows total across `rc`, `rc.nocontext`, `unfiltered`, `unfiltered.nocontext` subsets.
- **Schema:** `question`, `question_id`, `question_source`, `answer: {value, normalized_value, aliases}`, `entity_pages`, `search_results`.
- **Sample readings (verbatim from card):**
  1. "Which American-born Sinclair won the Nobel Prize for Literature in 1930?" → "Upton Sinclair"
  2. "Where in England was Dame Judi Dench born?" → "York"
  3. "In which decade did Billboard magazine first publish an American hit chart?" → "1930s"
  4. "From which country did Angola achieve independence in 1975?" → "Portugal"
  5. "Which city does David Soul come from?" → "Chicago"
  6. "Who won Super Bowl XX?" → "Chicago Bears"
  7. "Which was the first European country to abolish capital punishment?" → "Norway"
- **Fit for CAS-Native v1:**
  - **Question style:** Trivia-club authored. Highly formal, well-formed, factual. Lower realism than NQ/MS MARCO.
  - **Answer-length profile:** Almost all 1–3 tokens (names, places, dates). Pure terseness signal.
  - **"I don't know" handling:** Not built-in.
  - **Real user queries:** No — trivia enthusiasts.
- **Concerns:**
  - License is the hardest unknown of any candidate. UW disclaims copyright but didn't grant a license. Effectively unusable until clarified.
  - Trivia register is even more curated than SQuAD; further from real-user distribution.
- **Verdict:** **Eval-only candidate** at most. License blocks training inclusion. Style mismatch reduces value as training data even if license cleared.

### 7. HotpotQA — `hotpotqa/hotpot_qa`

- **Source URL:** https://huggingface.co/datasets/hotpotqa/hotpot_qa
- **License:** **CC-BY-SA-4.0**. Same flag as NQ/SQuAD.
- **Size:** ~203K rows (Distractor 97.9K + Fullwiki 105K).
- **Schema:** `id`, `question`, `answer`, `type` (comparison/bridge), `level` (easy/medium/hard), `supporting_facts`, `context`.
- **Sample readings (verbatim from card):**
  1. "Which magazine was started first Arthur's Magazine or First for Women?" → "Arthur's Magazine"
  2. "The Oberoi family is part of a hotel company that has a head office in what city?" → "Delhi"
  3. "Musician and satirist Allie Goertz wrote a song about the 'The Simpsons' character Milhouse, who Matt Groening named after who?" → "President Richard Nixon"
  4. "What nationality was James Henry Miller's wife?" → "American"
  5. "Cadmium Chloride is slightly soluble in this chemical, it is also called what?" → "alcohol"
  6. "In which American football game was Malcolm Smith named Most Valuable player?" → "Super Bowl XLVIII"
  7. "The 1988 American comedy film, The Great Outdoors, starred a four-time Academy Award nominee, who received a star on the Hollywood Walk of Fame in what year?" → "2006"
- **Fit for CAS-Native v1:**
  - **Question style:** Multi-hop reasoning chains. Highly structured.
  - **Answer-length profile:** Short (1–10 tokens, mostly proper nouns).
  - **"I don't know" handling:** Not built-in.
  - **Real user queries:** No — crowdsourced.
- **Concerns:**
  - Multi-hop is overkill for the discipline-of-answering use case. CAS-Native v1 is not training reasoning depth here; that's Path D's compiler-fluency curriculum.
  - License same as SQuAD/NQ.
- **Verdict:** **Eval-only candidate** for v1, useful as a stress test for "does the model still answer concisely when the question has multiple linked entities" — same purpose the audit revealed Stage 2 currently fails (silhouette without content). Not training-corpus material for the conversational-discipline slice.

## Recommendation

Ranked recommendation, conditional on license clearance from IP attorney:

**Tier 1 — top picks (include in v1 conversational-discipline mix):**

1. **MS MARCO `wellFormedAnswers` slice** — IF license can be cleared. Mixed-length sentence-grade answers + real Bing user queries is the single best fit. Volume target: **~5,000 records**, sampled to balance short (≤10 tokens) and well-formed (full sentence) answers 50/50.
2. **SQuAD 2.0 unanswerables slice** — license-conditional. The 50K adversarial unanswerables are uniquely valuable for the "abstain when no CAS signal" routing problem. Volume target: **~3,000 records** drawn from the unanswerable cohort + ~2,000 from the answerable cohort to keep the ratio honest.
3. **Natural Questions short-answer slice** — license-conditional. Real Google user queries are the highest-realism source. Volume target: **~3,000 records**, short-answer-only.

**Tier 2 — include only if Tier 1 fails license:**

4. **ELI5 (sentence-transformers mirror)** with strict quality filter (reject opener-hedge "the basic idea that I understand is..." patterns; reject answers >500 chars; require on-topic first sentence). Volume target: **~2,000 records** post-filter. Audit-corpus rule applies — sample 100, hand-grade quality, project filter pass-rate before volume commitment.
5. **CoQA (Apache-2.0 CNN slice only)** — single-turn extracts only, drop the multi-turn-context discipline. Volume target: **~1,000 records**. Mostly used as terseness reinforcement.

**Eval-only (do not include in training):**

6. HotpotQA — multi-hop reasoning stress test for "does discipline survive complex questions."
7. TriviaQA — license unknown.

**Total v1 X2 slice target: 5,000–15,000 records** post-filter. This is intentionally small. Path D is the corpus-scale workstream; X2 is the discipline-correction slice. The B-4 audit failure was not "not enough data" — it was "wrong distribution." A clean small slice fixes that better than a large noisy one.

**Mix rationale:** Short-extractive (terseness) ≈ 40%, sentence-grade well-formed (assistant-voice) ≈ 30%, abstention/unanswerable (no-CAS-signal routing) ≈ 20%, long-form on-topic explanation (anti-ramble) ≈ 10%.

## License compliance summary

| Dataset | License | Commercial training use? | Action |
|---|---|---|---|
| Natural Questions | CC-BY-SA-3.0 | **Conditional — share-alike** | IP attorney sign-off required before inclusion |
| SQuAD 2.0 | CC-BY-SA-4.0 | **Conditional — share-alike** | IP attorney sign-off required |
| HotpotQA | CC-BY-SA-4.0 | **Conditional — share-alike** | IP attorney sign-off; eval-only recommended |
| CoQA | Multi-license (CC-BY-SA-4.0 / MSR-LA / RACE custom / Apache-2.0) | **Mixed** | Filter to Apache-2.0 (CNN) slice only OR get sign-off per-segment |
| MS MARCO | Unspecified on HF; upstream MSR research-license | **Likely no** | Verify upstream MSR license terms; if non-commercial, drop |
| ELI5 (sentence-transformers) | Unspecified; Reddit-derived | **Likely no** | Reddit ToS post-2023 hostile to commercial training; drop unless cleared |
| TriviaQA | Unspecified (UW disclaims copyright, no grant) | **No** | Eval-only at most |
| WebQuestions (incidental check) | Unspecified | **No** | Skip |
| Tevatron/wikipedia-nq (incidental check) | Unspecified, derives from NQ | **Inherits NQ flag** | Skip — use canonical NQ if cleared |

Eliminated outright on license grounds (no IP attorney clearance possible without further information): TriviaQA, WebQuestions, Tevatron/wikipedia-nq.

Eliminated on derivation-source grounds: ELI5 (Reddit) — flag for IP attorney; do not include without explicit Reddit/sentence-transformers compatibility opinion.

CC-BY-SA share-alike datasets (NQ, SQuAD 2.0, HotpotQA, CoQA literature/Wikipedia segments): all carry the same legal question — does training a commercial proprietary model on CC-BY-SA-licensed text constitute creating a derivative work that triggers share-alike? This is an unsettled legal question in 2026 and the same question that gates X1 (dialogue/instruction) and X3 (casual/OOD/refusal) datasets. A single IP attorney opinion settles all of X1+X2+X3 on this axis simultaneously.

## Open questions for IP attorney

1. **CC-BY-SA training treatment.** Does training a commercial proprietary CAS-Native model on CC-BY-SA-3.0 (NQ) and CC-BY-SA-4.0 (SQuAD 2.0, HotpotQA, parts of CoQA) text constitute a derivative-work act under share-alike? If yes, can the trained-weights output be excluded from share-alike on the "model weights are not text" theory, or must we treat weights as encumbered? This is the single largest blocker on the X2 slice, and the answer also unblocks (or blocks) X1 and X3.
2. **MS MARCO upstream license terms.** The HF card says "More Information Needed." Microsoft's original MS MARCO release page contains the actual license. We need an opinion on whether the MSR research-license terms (likely non-commercial) bar inclusion in CAS-Native v1 weights, and whether a commercial-license negotiation with MSR is feasible at our scale.
3. **Reddit-derived content (ELI5).** Post-2023 Reddit content-licensing changes have hardened against commercial training. Does the sentence-transformers mirror change the legal posture (i.e., is sentence-transformers a downstream redistributor that took the licensing risk), or does the Reddit ToS reach through to any downstream commercial use of the derived corpus?
4. **TriviaQA "we don't own copyright" disclaimer.** UW's "we don't own the copyright of the questions and documents" notice without an affirmative grant — what is the actionable legal status? Effectively unlicensed and unusable, or does the public release imply an implied license for research-and-commercial use?
5. **CoQA per-segment filtering.** If we include only the Apache-2.0 (CNN) segment, is segment-level filtering legally clean, or does the dataset's release as a single CoQA artifact carry combined-license obligations regardless of which records we use?
6. **USPTO #64/037,173 interaction.** Are there any specific concerns about training a model that is part of a Noetic-Compass-branded commercial product on share-alike or Reddit-derived data, given the patent's claim structure? The legal framing in CLAUDE.md flags IP attorney consultation for v7.5/v7.6/v7.7 framework changes; the same attorney should opine on training-data licensing alongside.
