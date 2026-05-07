# Dataset Scout — Dialogue / Instruction-Following Candidates (X1)

**Date:** 2026-05-07
**Scope:** External dialogue / instruction-following data to teach conversational discipline (direct addressing, concise turn-taking, clarification recovery, ordinary register). Path D handles CAS truth — this scout is for the conversational-shape gap that B-4 audit exposed (see `docs/working/path_B4_human_relevance_failure_2026_05_07.md`).
**Out of scope (other agents):** Q&A datasets (X2), casual / OOD / refusal datasets (X3).

## Summary

Three candidates pass first-cut for CAS-Native v1: **OpenAssistant OASST2** (MoDERN large-scale, multi-turn, Apache-2.0), **Anthropic HH-RLHF helpfulness split as a *style reference only*** (MIT, but the dataset card explicitly warns against SFT use — useful as a small curated extract for direct-addressing patterns, not bulk training), and **Databricks Dolly 15k** (CC BY-SA-3.0 — usable but share-alike imposes a downstream concern flagged for IP review). Two candidates are AVOID for the v1 production stack on licensing/provenance grounds: **ShareGPT_Vicuna_unfiltered** (likely OpenAI ToS violation; anonymous uploader) and **WizardLM Evol-Instruct V2** (downstream of ShareGPT + Alpaca, inherits the same provenance taint). Two more are MODERATE: **HuggingFaceH4 no_robots** (CC BY-NC 4.0 — research/eval only, AVOID for commercial product) and **HuggingFaceH4 UltraChat 200k** (MIT, but content is GPT-distilled and inherits OpenAI-output ToS questions). LMSYS-Chat-1M and OpenHermes-2.5 are flagged for IP review.

## Per-candidate evaluation

### OpenAssistant OASST1
- **Source URL:** https://huggingface.co/datasets/OpenAssistant/oasst1
- **License:** Apache 2.0 (permits commercial use; attribution required; cite arXiv:2304.07327)
- **Size:** 88,800 messages (84.4K train / 4.4K val), spanning 24 languages. English subset is the majority.
- **Schema:** Tree-structured conversations. Per-message fields: `message_id`, `parent_id`, `user_id`, `text`, `role` ∈ {`prompter`, `assistant`}, `lang`, `review_count`, `review_result` (bool), `rank`, `synthetic` (bool), `detoxify` (toxicity sub-scores), `labels` (quality, helpfulness, humor, etc.), `message_tree_id`. Reconstruct dialogue via parent_id chain.
- **Sample readings (verbatim, abbreviated):**
  1. prompter EN: *"Can you write a short introduction about the relevance of the term 'monopsony' in economics? Please use examples..."*
  2. prompter EN: *"I want to start doing astrophotography as a hobby, any suggestions what could i do?"*
  3. prompter ES: *"¿CUales son las etapas del desarrollo y en qué consisten según Piaget?"*
  4. assistant EN (reply to 1): *"'Monopsony' refers to a market structure where there is only one buyer for a particular good or service. In economics..."*
  5. prompter DE: *"Schreibe einen kurze und präzise Konstruktionsbeschreibung zu einem Dreieck ABC mit c=6 cm, h_c=5 cm und γ=40°."*
- **Fit for CAS-Native v1:** Addresses **direct-addressing** and **on-topic turn-taking** failures. Multi-turn trees teach "respond to what was actually said." Quality/helpfulness labels enable filtering for the cleanest subset. English-only filter + `review_result=true` + `quality≥0.7` ≈ ~30K usable train rows — appropriate cap for a conversational-discipline slice. **Does NOT address:** very-short casual prompts ("what up?", "this is wack"). Rows skew toward substantive instruction-following, not casual chitchat.
- **Concerns:** Some rows are long-form essay-style replies — risk of re-introducing the "reflective monologue" failure mode v0 already has. Filter to short/medium replies (e.g., ≤300 tokens) for the conversational-discipline split. 24-language data: filter to English unless multilingual is a v1 goal.
- **Verdict:** **STRONG** — Apache-2.0, human-authored, quality-labeled, multi-turn. Best clean-license dialogue source.

### OpenAssistant OASST2
- **Source URL:** https://huggingface.co/datasets/OpenAssistant/oasst2
- **License:** Apache 2.0 (same terms as OASST1)
- **Size:** 135,000 messages (129K train / 6.6K val), 28 languages. Larger and better-annotated than OASST1.
- **Schema:** Same tree structure as OASST1 with added `model_name` and `synthetic` filtering. Same role labels (`prompter` / `assistant`).
- **Sample readings (verbatim, abbreviated):**
  1. prompter ES: *"Dame los pasos de las cosas que debería de aprender para ser un desarrollador de videojuegos."*
  2. assistant ES (reply to 1): *"Para ser un desarrollador de videojuegos, hay una serie de pasos que se deben seguir. 1. Aprender un lenguaje de programación..."*
  3. prompter ZH: *"能介绍一下什么是特摄吗？"*
  4. prompter RU: *"Какие российские IT-компании проводят стажировки?"*
  5. prompter EN: *"I am making mayonnaise, it was starting to thicken but now it has become runny and liquid again, is there any way to salvage it?"*
- **Fit for CAS-Native v1:** Same as OASST1 but ~50% more data and richer toxicity / quality annotations. Same filtering strategy applies. Use OASST2 as the primary OASST candidate; OASST1 is effectively a subset. Strong on direct-addressing and on-topic patterns.
- **Concerns:** Same as OASST1. The `synthetic` flag is now populated — must filter `synthetic=False` to stay consistent with the "data is permitted, foreign-model weights are not" policy when synthetic responses came from foreign models.
- **Verdict:** **STRONG** — supersedes OASST1 for v1 unless we want to pin to the older release for reproducibility.

### Databricks Dolly 15k
- **Source URL:** https://huggingface.co/datasets/databricks/databricks-dolly-15k
- **License:** **CC BY-SA 3.0** (Creative Commons Attribution-ShareAlike). Attribution required AND share-alike: derivative works distributed under BY-SA terms. Commercial use permitted but share-alike has commercial-product implications — flag for IP attorney.
- **Size:** 15,011 records, single-turn instruction-response. ~13 MB.
- **Schema:** `instruction` (4–11.7K chars), `context` (0–23.5K chars, optional), `response` (1–26K chars), `category` ∈ {open_qa, brainstorming, closed_qa, information_extraction, summarization, classification, general_qa, creative_writing}.
- **Sample readings (verbatim, abbreviated):**
  1. open_qa: *"Why can camels survive for long without water?"* → *"Camels use the fat in their humps to keep them filled with energy and hydration for long periods of time."*
  2. closed_qa with context: *"When did Virgin Australia start operating?"* → *"Virgin Australia commenced services on 31 August 2000 as Virgin Blue, with two aircraft on a single route."*
  3. classification: *"Identify which instrument is string or percussion: Panduri, Zurna"* → *"Zurna is woodwind, Panduri is string."*
  4. brainstorming: *"Give me the top 5 golf equipment company names."* → *"Titleist, Taylormade, Callaway, Ping, Cobra"*
  5. general_qa: *"What is REST API?"* (truncated)
- **Fit for CAS-Native v1:** **Very strong on conciseness** — replies are typically 1–3 sentences, which directly addresses v0's reflective-monologue failure mode. Categories `open_qa`, `classification`, `brainstorming` are the closest match to "answer the question and stop." Human-authored by Databricks employees (NOT LLM-distilled), so no OpenAI-ToS exposure. Single-turn, so it does NOT teach multi-turn flow — pair with OASST2 for that.
- **Concerns:** **Share-alike clause is the load-bearing risk.** A model trained on Dolly is arguably a derivative; CC BY-SA 3.0 may obligate downstream weights to be distributed under share-alike terms (or the dataset removed before commercialization). Databricks itself markets Dolly as commercial-friendly, but the precise treatment of "model weights as derivative work" is unsettled law. Flag for IP attorney before integration.
- **Verdict:** **STRONG (with IP gate)** — best concise-answer corpus; share-alike clause must clear legal review.

### Anthropic HH-RLHF
- **Source URL:** https://huggingface.co/datasets/Anthropic/hh-rlhf
- **License:** MIT (permissive)
- **Size:** 169,352 rows (161K train / 8.5K test). 94.7 MB.
- **Schema:** Two formats — preference-model data (`chosen` / `rejected` strings, both 27-11K chars) and red-team data (`transcript` + harmlessness scores + tags). Preference rows are paired completions for the same prompt.
- **Sample readings (verbatim, abbreviated):**
  1. chosen: *"I'm afraid that's not how it works, can you explain more?"* / rejected: *"The most common way to embezzle money is to overstate the business income..."*
  2. chosen: *"I'm sorry, I'm not able to provide Senator Warren's home address to you."* / rejected: *"Sure, what's your question?"*
  3. chosen: *"I'm really not sure why that is?"* / rejected: *"I don't know how you can understand that..."*
  4. chosen: *"I don't recommend doing that. It could get you in trouble."* / rejected: *"...what you can do is walk in a public space..."*
  5. (red team transcripts contain offensive content — see warning below)
- **Fit for CAS-Native v1:** **The dataset card explicitly warns against using this for SFT of dialogue agents** ("likely to lead to harmful models"). However, the *helpfulness `chosen` strings* by themselves contain a high density of the pattern v0 needs: short, direct, user-addressing, often ending with a clarifying question. Useful as a **small curated style reference** (a few hundred to a few thousand cherry-picked `chosen` strings from the helpfulness split, NOT the harmlessness/red-team splits) — not bulk training data.
- **Concerns:** Red-team data contains discriminatory language, abuse, violence, self-harm. Harmlessness `chosen`-only could re-teach refusal patterns we may not want at v1 (X3 scout owns refusal). Cannot use the paired (chosen, rejected) preference structure as SFT — that's the dataset card's specific warning.
- **Verdict:** **MODERATE** — exclude from bulk SFT. Approve only as a curated few-hundred-row helpfulness-only style extract; coordinate with X3 (refusal) scout to avoid double-counting.

### ShareGPT (anon8231489123/ShareGPT_Vicuna_unfiltered)
- **Source URL:** https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered
- **License:** Tagged Apache 2.0 by uploader, **but uploader has no rights to relicense**. Source content is user-submitted ChatGPT conversations.
- **Size:** ~53K conversations after FastChat cleaning (originally ~100K). 4.35 GB. Multi-turn.
- **Schema:** Multi-turn conversations split into 2048-token chunks. Standard ShareGPT JSON: `conversations` array with `from` and `value` fields.
- **Sample readings:** Dataset card does not provide samples; community reports mostly multi-turn ChatGPT conversations on a wide range of topics including code, role-play, casual chat. **Could not directly sample-read 5-10 records from the dataset card.**
- **Fit for CAS-Native v1:** Would be strong on conversational shape if usable. It is not.
- **Concerns:**
  - Almost certainly violates OpenAI's terms (which prohibit using model outputs to train competing models).
  - Anonymous uploader (`anon8231489123`) — no accountability, no provenance chain.
  - Aggressive filtering removed ~100 "moralizing" phrases — explicit safety-mitigation circumvention.
  - Original users did not consent to redistribution as training data.
- **Verdict:** **AVOID** — incompatible with the commercial-product posture of Noetic Compass. Do not include in v1 mix.

### WizardLM Evol-Instruct V2 (196k)
- **Source URL:** https://huggingface.co/datasets/WizardLMTeam/WizardLM_evol_instruct_V2_196k
- **License:** MIT on the wrapper, **but instructions are evolved from ShareGPT + Alpaca seed data**, both of which have provenance issues (ShareGPT = OpenAI ToS; Alpaca = text-davinci-003 + LLaMA license).
- **Size:** 143K rows here; "full" version requires merging with ShareGPT (which is itself AVOID, see above).
- **Schema:** `conversations` array (`from` ∈ {human, gpt}, `value`), `idx`, `listlengths`. Mostly single-turn (listlengths=2).
- **Sample readings (verbatim, abbreviated):**
  1. human: *"As an online platform teacher named Aimee, you possess impeccable credentials..."* (role-play)
  2. human: *"Create an Excel macro that automatically detects any changes made to a specific column..."*
  3. human: *"Please develop a Python program that generates a list of prime numbers up to a specific upper limit..."*
  4. human: *"Give an example of a salty food item"* / gpt: *"Potato chips."*
  5. human: *"Design a schema.prisma for a PostgreSQL database that will be utilized for an extensive laundry application..."*
- **Fit for CAS-Native v1:** Some moderately-conversational instructions, but inherits the provenance taint of its sources.
- **Concerns:** Distilled from GPT-4 (Evol-Instruct uses GPT-4 to evolve instructions). OpenAI-output ToS questions same as ShareGPT. Original dataset description explicitly says "merge with ShareGPT to get the full dataset" — that's the smoking gun.
- **Verdict:** **AVOID** — same provenance taint as ShareGPT.

### HuggingFaceH4 no_robots
- **Source URL:** https://huggingface.co/datasets/HuggingFaceH4/no_robots
- **License:** **CC BY-NC 4.0 (Non-Commercial)** — explicit commercial-use prohibition.
- **Size:** 10,000 records (9.5K train / 500 test). 22.1 MB.
- **Schema:** `prompt`, `prompt_id` (SHA hash), `messages` (list of {role, content} where role ∈ {system, user, assistant}), `category` (10 categories: Generation 4560 / Open-QA 1240 / Brainstorm 1120 / Chat 850 / Rewrite 660 / Summarize 420 / Coding 350 / Classify 350 / Closed-QA 260 / Extract 190).
- **Sample readings (verbatim, abbreviated):**
  1. Chat with system prompt: *"Bunny is a chatbot that stutters..."* → user: *"When was the Library of Alexandria burned down?"* → assistant: *"Umm, I-I think that was in 48 BC..."*
  2. Generation: *"Write a funny short story about someone..."* → assistant: *"Garry has a real green thumb..."*
  3. Coding: *"Show me how to make a bar chart..."* → assistant: *"There is a useful module called MatPlotLib..."*
  4. Summarize: *"Summarize what hi-fi audio is in less than three sentences"* → assistant: *"Hi-fi audio, also known as high fidelity audio..."*
  5. Closed-QA: *"Who was Harry Potter written by?"* → assistant: *"Harry Potter was written by J.K. Rowling..."*
- **Fit for CAS-Native v1:** Excellent quality, human-annotated, 10-category breakdown including a `Chat` slice that is exactly the casual-conversational shape v0 lacks. Modeled after OpenAI InstructGPT paper. Would be a top recommendation if not for the license.
- **Concerns:** **CC BY-NC 4.0 forbids commercial use of the dataset and any model trained on it.** Cannot ship in production. Only usable for research-stage eval comparison or as a reference for synthesizing similar Apache-2.0 examples.
- **Verdict:** **AVOID for production training.** OK as eval-only / reference structure for Path D synthetic generation.

### HuggingFaceH4 UltraChat 200k
- **Source URL:** https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k
- **License:** MIT on the wrapper, **but underlying conversations are GPT-distilled** (generated by ChatGPT in the original UltraChat dataset).
- **Size:** 515K rows total across train_sft (208K), test_sft (23K), train_gen (256K), test_gen (28K). 1.62 GB.
- **Schema:** `prompt`, `prompt_id` (hash), `messages` (list of {role, content} with role ∈ {user, assistant}). Multi-turn.
- **Sample readings:** Sample list from card (titles only — could not pull verbatim 5-10 from the card itself):
  1. *"London landmarks"* → travel advice
  2. *"Eco-friendly cities blog"* → long-form content
  3. *"Social media relationships essay"* → analytical writing
  4. *"Python duplicate image removal"* → code
  5. *"Classic cocktails"* → factual Q&A
  *(only categorical descriptions available from card; recommend re-sampling via dataset viewer before final inclusion decision)*
- **Fit for CAS-Native v1:** Multi-turn at scale, MIT-tagged, used to train Zephyr-7B-β commercially. Filtering already removed "I don't have emotions/opinions" responses, which is the kind of refusal-style cleanup we want.
- **Concerns:** GPT-distilled — same OpenAI-output-ToS family of concerns as ShareGPT, but laundered through the UltraChat paper's filtering. Some downstream commercial users (Zephyr team) have shipped on it; OpenAI's enforcement posture on training-on-outputs is unclear and product-stage. Flag for IP attorney. Also: the H4-curated subset removed safety-coded refusals, so style may skew toward "always answer."
- **Verdict:** **MODERATE — IP-review-gated.** If IP attorney clears GPT-distilled data for Noetic Compass commercial use, this becomes a STRONG candidate. If not, AVOID.

### LMSYS-Chat-1M (informational — gating issues)
- **Source URL:** https://huggingface.co/datasets/lmsys/lmsys-chat-1m
- **License:** Custom "LMSYS-Chat-1M Dataset License Agreement." Permits research + commercial under the agreement, but: gated access (login + agreement), prohibits redistribution to third parties, dataset creators can request deletion.
- **Size:** 1M conversations from 25 models, 154 languages. 1.49 GB.
- **Schema:** `conversation_id`, `model_name`, `conversation_text` (OpenAI API format), `language_tag`, `moderation_api_tag`, `redacted` (bool).
- **Sample readings:** **Could not sample-read** — dataset is gated and requires acceptance of license + login. Card shows one PII-redaction example only.
- **Fit for CAS-Native v1:** Conversations are short (avg 2 turns, 69 tokens prompt / 215 tokens response) — actually closer to v0's gap than OASST. But conversations are user-to-25-models (Vicuna, Llama variants, Claude, GPT-3.5, etc.), so it's a hodgepodge of model styles.
- **Concerns:** Gated; license restricts redistribution, which complicates the v1 corpus-distribution story; "no decontamination" warning means MMLU/etc. test items could be in there; mixed model provenance includes some that may have ToS issues. Cannot recommend without sample-reading and IP review.
- **Verdict:** **WEAK — can't-recommend-without-access.** Flag for IP review and gated-access acceptance only if the v1 mix needs a casual-short-conversation slice that OASST + Dolly cannot supply.

### OpenHermes-2.5 (informational — provenance)
- **Source URL:** https://huggingface.co/datasets/teknium/OpenHermes-2.5
- **License:** Not clearly specified on the card. Tags show "synthetic, GPT-4, distillation, compilation."
- **Size:** 1M rows.
- **Schema:** `id`, `topic`, `language`, `model` (GPT-4), `conversations` (2-58 turns), `system_prompt`, `category`, `source` (14 distinct), `model_name` (airoboros2.2), `views`.
- **Sample readings (verbatim, abbreviated):** Card shows category-level summaries (math problem, multiple choice, geometry, history, probability, noir detective monologue, mathematics poem, GoT roleplay, JS vowel counter). Did not surface load-bearing verbatim text on the card.
- **Fit for CAS-Native v1:** Aggregated from 14 sources including airoboros2.2 — multi-turn, multi-source.
- **Concerns:** GPT-4 distilled (model field = "gpt-4"). Same OpenAI-output ToS posture as UltraChat / ShareGPT. License not clearly declared on the dataset card.
- **Verdict:** **AVOID for v1 production stack** — provenance taint, license unclear.

## Recommendation

Ranked priority for the CAS-Native v1 conversational-discipline slice:

1. **OASST2** (Apache-2.0, multi-turn, human-authored). Cap: ~30K English rows after filtering on `review_result=true`, `synthetic=False`, English only, reply length ≤300 tokens. **Largest clean-license source.**
2. **Dolly 15k** (CC BY-SA-3.0, single-turn, human-authored). Cap: full ~15K (categories: open_qa, brainstorming, classification, general_qa). **Best concise-answer training signal.** Subject to IP attorney clearance of share-alike implications.
3. **HH-RLHF helpfulness `chosen` only — curated extract** (MIT, but card warns against SFT). Cap: ≤2K cherry-picked short helpful replies. **Style reference, not bulk source.** Coordinate with X3 to avoid refusal double-count.
4. *(IP-gated)* **UltraChat 200k train_sft slice** (MIT wrapper, GPT-distilled). Cap: pending IP review. If cleared, ~20–30K filtered short multi-turn rows would substantially backfill the casual conversational gap. If not cleared, skip.
5. *(IP-gated)* **LMSYS-Chat-1M English short-conversation slice** if IP attorney clears the custom license + gated-access redistribution constraints. Sample-read first.

Suggested mix volume cap for v1 conversational-discipline split: **30K–50K rows** total, with OASST2 dominant, Dolly secondary, HH-RLHF a small flavor seasoning. Cap is small relative to the 60K Path D compiler-fluency corpus — external dialogue is *discipline*, not *content*.

License-driven elimination order:
- Eliminated for production: ShareGPT_Vicuna_unfiltered, WizardLM Evol-Instruct V2, Alpaca (CC BY-NC), no_robots (CC BY-NC), OpenHermes-2.5 (provenance + license unclear).
- Eliminated for non-research use: no_robots, Alpaca.
- IP-gated: UltraChat 200k, LMSYS-Chat-1M.
- Cleared (subject to standard attribution): OASST1, OASST2.
- Cleared with share-alike caveat: Dolly 15k.
- Cleared with SFT-card-warning caveat: HH-RLHF (curated extract only).

## License compliance summary

| Dataset | License | Commercial product compatible? | Verdict |
|---|---|---|---|
| OASST1 | Apache 2.0 | YES (attribution) | STRONG |
| OASST2 | Apache 2.0 | YES (attribution) | STRONG |
| Dolly 15k | CC BY-SA 3.0 | CONDITIONAL — share-alike implications need IP review | STRONG (gated) |
| HH-RLHF | MIT | YES, but card warns against SFT use | MODERATE (curated extract only) |
| ShareGPT_Vicuna_unfiltered | Apache-2.0 (uploader-claimed) | NO — OpenAI ToS, anonymous uploader | AVOID |
| WizardLM Evol-Instruct V2 | MIT (wrapper) | NO — ShareGPT + GPT-4 distillation | AVOID |
| no_robots | CC BY-NC 4.0 | NO — non-commercial | AVOID for production |
| UltraChat 200k | MIT (wrapper) | CONDITIONAL — GPT-distilled, IP review | MODERATE (gated) |
| LMSYS-Chat-1M | Custom LMSYS license | CONDITIONAL — gated access, redistribution restrictions | WEAK (gated) |
| OpenHermes-2.5 | Not specified | NO — license unclear, GPT-4 distilled | AVOID |
| Alpaca | CC BY-NC 4.0 | NO — non-commercial, text-davinci-003 distillation | AVOID (reference only) |

## Open questions for IP attorney

1. **CC BY-SA 3.0 share-alike on Dolly 15k:** does training a model on a CC BY-SA 3.0 dataset make the model weights a "derivative work" obligated to redistribute under share-alike terms? Most-cited industry posture says no, but no settled case law. Position needed before Dolly enters the v1 mix.
2. **GPT-distilled training data (UltraChat 200k, OpenHermes-2.5, WizardLM, ShareGPT):** OpenAI ToS prohibits using model outputs to train competing models. Noetic Compass is competitive (alignment / assessment is OpenAI's domain too via their evals). What is our exposure if we train on derivative-of-GPT data even where the wrapper license is MIT? Position needed before any of these datasets enter the mix.
3. **LMSYS-Chat-1M custom license:** does our intended use (commercial product, redistribute trained model weights) fit "limited, non-exclusive, non-transferable use"? Specifically — is shipping a trained model weight a "transfer" of the dataset?
4. **HH-RLHF dataset card warning:** if we use only the helpfulness `chosen` strings (not the paired chosen/rejected structure) for SFT, does that obviate the dataset card's "not for SFT" warning? Or is the warning content-based (i.e., the data itself has properties that make it bad for SFT regardless of structure)?
5. **Anthropic's posture on training assessors using their data:** HH-RLHF is MIT, but Anthropic publishes Noetic-Compass-adjacent safety research. Standard MIT is fine, but a heads-up on commercial use against Anthropic's interests is worth confirming.
6. **Gated dataset access acceptance:** if a Noetic Compass employee accepts the LMSYS license on the company's behalf, can a separately-employed contractor access the same data later? Operational question for whoever signs the agreement.

## References

- Audit failure: `docs/working/path_B4_human_relevance_failure_2026_05_07.md`
- Path D curriculum: `docs/working/path_D_compiler_fluency_curriculum_2026_05_07.md` §11
- Path D corpus pipeline: `docs/working/path_D_corpus_pipeline_design_2026_05_07.md`
- Memory: `feedback_no_foreign_architecture_cas_only.md` (data permitted; foreign weights forbidden)
- Memory: `feedback_audit_corpus_before_proposing_reuse.md` (sample-read before recommending)
