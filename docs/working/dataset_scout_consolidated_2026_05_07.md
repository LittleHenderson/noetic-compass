# Dataset Scout — Consolidated v1 Mix Recommendation + IP Brief

**Date:** 2026-05-07
**Status:** Synthesis of three parallel scout reports (X1 dialogue / X2 Q&A / X3 casual). Frames the v1 training-mix decision and packages all IP-attorney questions for a single legal review.

---

## 1. Frame

Path D produces compiler-validated CAS data (the spine of v1 training). External datasets address the *conversational responsiveness* failures the B-4.1 audit caught — irrelevance, drunk coherence, OOD ships anyway — that Path D corpus alone cannot fix.

**Locked integration pattern (from X3 scout, 2026-05-07):**

> Use external corpora as **prompt-distribution seeds + turn-shape exemplars only**. Generation targets stay CAS-Native + compiler-validated under Path D rejection sampling. The PROMPT comes from external real-user distribution; the TARGET stays under CAS-Native control.

This pattern:
- Preserves the no-foreign-architecture rule (`feedback_no_foreign_architecture_cas_only.md`)
- Cleanly avoids most CC-BY-SA share-alike concerns (we redistribute neither model outputs nor source assistant turns)
- Sharper signal for v0 failure modes — addresses distribution gap without polluting CAS truth
- Sidesteps the "prompt + GPT-distilled completion" provenance landmines

**The bulk-mix pattern** (70% Path D + 15% OpenAssistant + 10% Q&A + 5% casual) remains a fallback if prompt-seeds-only doesn't produce enough English-side training signal. Default = prompt-seeds-only.

## 2. Top picks across all three scopes

| Scope | Dataset | License | Volume target | Use as | Verdict |
|---|---|---|---|---|---|
| **Dialogue / instruction** | **OpenAssistant OASST2** | Apache-2.0 | ~30K filtered prompts | Prompt seeds (assistant-style English distribution) | STRONG primary |
| Dialogue / instruction | Databricks Dolly 15k | CC-BY-SA-3.0 | 0–15K (gated) | Concise-answer style; IP-attorney sign-off required | MODERATE — IP gated |
| Dialogue / instruction | HH-RLHF helpfulness `chosen` curated | MIT | ~2K cherry-picked | Clarification turn shapes; style seasoning only (NOT bulk SFT per dataset card warning) | NARROW |
| **Q&A / direct-answer** | **SQuAD 2.0 unanswerables slice** | CC-BY-SA-4.0 | ~5K | OOD-abstention training (uniquely valuable for the v0 "no CAS signal but ships anyway" failure) | STRONG — IP gated |
| Q&A / direct-answer | Natural Questions short-answer | CC-BY-SA-3.0 | ~5K | Real-user query distribution | STRONG — IP gated |
| Q&A / direct-answer | MS MARCO wellFormedAnswers | (D license, MSR custom) | 0 until upstream MSR terms verified | Sentence-grade answers (best content) | HOLD pending license |
| **Casual / OOD / refusal** | **WildChat (allenai/WildChat)** | ODC-BY (commercial-clear) | ~10–20K **prompts only** | OOD prompt distribution ("what up", real-user casual) | STRONG primary |
| Casual / OOD / refusal | HH-RLHF `chosen` filtered (clarification turns) | MIT | ~2K | Clarification turn shapes | STRONG narrow |
| Casual / OOD / refusal | MultiWOZ 2.2 | Apache-2.0 | ~1–2K | Slot-filling clarification supplement | NARROW |

## 3. Eliminations (avoid for production training)

| Dataset | Reason |
|---|---|
| ShareGPT_Vicuna_unfiltered | OpenAI ToS violation; anonymous uploader; unsafe provenance |
| WizardLM Evol-Instruct V2 | ShareGPT + GPT-4 distillation provenance taint |
| no_robots | CC BY-NC 4.0 (non-commercial; blocks Noetic Compass commercial product) |
| Alpaca | CC BY-NC 4.0 + text-davinci-003 distillation |
| OpenHermes-2.5 | License unclear; GPT-4 distilled |
| TriviaQA | License unspecified (UW disclaims copyright without grant); eval-only at best |
| WebQuestions | License unspecified |
| ELI5 (sentence-transformers mirror) | Reddit-derived; post-2023 commercial-use hostile; flag for IP attorney |
| HotpotQA | Multi-hop overkill for discipline slice; eval-only |
| DailyDialog | CC BY-NC-SA (non-commercial + share-alike virality) |
| ToxicChat | CC BY-NC |
| BeaverTails | CC BY-NC + role mismatch (response column = harmful completions) |
| PersonaChat | License unclear + register mismatch |

## 4. Eval-only candidates (NOT for training; populate brutal-normal-user eval set)

| Dataset | License | Use |
|---|---|---|
| LMSYS Chat 1M | Custom gated; non-transferable + content-moderation + right-of-deletion clauses | Brutal normal-user eval set per B-4 §Step 1 (the 50-100 prompt eval; LMSYS prompts are the canonical OOD distribution) |
| ToxicChat | CC BY-NC | Refusal-behavior eval set |
| BeaverTails | CC BY-NC | Safety-refusal eval set |

**Note:** for prompt-seeds-only pattern, "eval-only" can sometimes be relaxed if we use only the PROMPT (not the model output) and don't redistribute. LMSYS terms specifically bar redistribution; even prompt extraction may need attorney sign-off given their custom license. **Default = strict eval-only.**

## 5. License compliance master table

| License class | Examples in our top picks | Commercial-product status | Action required |
|---|---|---|---|
| Apache-2.0 | OASST2, MultiWOZ 2.2 | Clean | None — proceed |
| MIT | HH-RLHF | Clean | None — proceed (note dataset-card SFT warning for HH-RLHF) |
| ODC-BY | WildChat | Clean (with attribution) | Add attribution per ODC-BY terms |
| CC0 | (some Q&A mirrors) | Clean | None — proceed |
| **CC-BY-SA-3.0 / 4.0** | **Dolly, SQuAD 2.0, Natural Questions** | **Share-alike — NEEDS IP ATTORNEY** | Get the **single load-bearing opinion** before any of these enter training (see §6) |
| Custom / gated | LMSYS, MS MARCO | Restrictive | Eval-only unless attorney clears |
| CC BY-NC | DailyDialog, ToxicChat, BeaverTails, no_robots, Alpaca | Non-commercial — INELIGIBLE | Skip entirely |

## 6. IP Attorney Brief — 13 questions packaged for single consult

Each question below is gated on a real legal interpretation, not a soft preference. One attorney consult unblocks most of them.

### A. The single load-bearing question (gates ~7 candidates):

> **Q1: Does training commercial model weights on CC-BY-SA-3.0/4.0 share-alike data constitute "derivative work" under the share-alike obligation?** If yes, do downstream model weights (and their outputs) inherit the share-alike license? If yes, can we still use share-alike data as **prompt seeds only** (not output distillation) without inheriting the obligation?

If Q1 returns "no, weights are not derivative" or "yes but prompt-seeds-only is exempt": **Dolly, Natural Questions, SQuAD 2.0, ELI5 mirror, and other CC-BY-SA candidates all unblock.** That's ~7 of our 13 candidates downgraded from "IP-gated" to "proceed."

If Q1 returns "yes, weights are derivative AND prompt-seeds-only still constitutes derivative use": all CC-BY-SA candidates skip entirely. We default to OASST2 + WildChat + HH-RLHF + MultiWOZ as the externals.

### B. Provenance-related questions (gates GPT-distilled candidates):

> **Q2: GPT-distilled training data exposure** — Does training on data generated by another lab's model (Alpaca = davinci, WizardLM = GPT-4) create OpenAI ToS exposure for our derivative model? Even if those datasets are MIT-wrapped, the original generation may have violated OpenAI's ToS-forbidding-derivatives clause.

> **Q3: HH-RLHF SFT-warning scope** — Anthropic's HH-RLHF dataset card explicitly states "not meant for supervised dialogue-agent training." Does this constitute a contractual restriction or a non-binding caution? Can we use the `chosen` slice for narrow style-reference training?

> **Q4: Anthropic posture on derivative use** — Given Noetic Compass uses Anthropic API for training-data generation (Wave 3), are there Anthropic ToS restrictions on the resulting downstream model? (This matters regardless of whether HH-RLHF gets used.)

### C. Custom-license questions (gates LMSYS / MS MARCO):

> **Q5: LMSYS Chat 1M license fit for prompt-seeds-only use** — The LMSYS license bars redistribution and includes content-moderation and right-of-deletion clauses. Does extracting only PROMPTS (not assistant outputs) and using them to seed our pipeline constitute "derivative" or "redistribution" under their terms?

> **Q6: MS MARCO upstream MSR terms** — What's the actual license? The HuggingFace card is incomplete; need to verify upstream Microsoft Research dataset terms before any training use.

### D. Specific-attribution questions:

> **Q7: ODC-BY attribution requirements** — WildChat is ODC-BY. What attribution must accompany model outputs / model card / repo? (Probably modest — note dataset source. But verify.)

> **Q8: MIT acknowledgement scope** — For HH-RLHF MIT use, what's required in our model card / outputs?

### E. Compositional risk questions:

> **Q9: Compositional license risk** — If our v1 corpus mix contains 70% Path D (clean), 15% OASST2 (Apache), 10% Q&A (potentially share-alike), 5% WildChat (ODC-BY), do the most-restrictive license terms cascade to the whole corpus / model? Or does each license attach only to its own slice?

> **Q10: Deletion-compliance** — LMSYS includes right-of-deletion. WildChat doesn't. If a contributor demands deletion from the upstream corpus, what's our obligation regarding any downstream model trained on it?

### F. Context-specific questions:

> **Q11: PersonaChat license origin** — License is unclear; original Facebook AI release vs HuggingFace mirror have different posture.

> **Q12: USPTO interaction** — Noetic Compass has provisional patent USPTO #64/037,173. Does any of the external dataset usage create prior-art problems or licensing conflicts with the patent claims? (Probably no, but worth confirming.)

> **Q13: Gated-access transferability** — For datasets that require login/agreement to download (HH-RLHF on HuggingFace, LMSYS), does the access agreement transfer to derived models / inference services?

## 7. Recommended v1 mix ratio under prompt-seeds-only pattern

**Default plan (no attorney consult yet):**

| Source | Volume | Role |
|---|---|---|
| Path D compiler-fluency CAS corpus (in flight) | ~26K | Spine — CAS truth |
| OASST2 prompts (Apache-2.0) → Path D pipeline → CAS-Native targets | ~10K | Conversational distribution |
| WildChat prompts (ODC-BY) → Path D pipeline → CAS-Native targets | ~5K | Casual / OOD distribution |
| HH-RLHF chosen-clarification prompts (MIT) → Path D pipeline | ~1K | Clarification turn shapes |
| MultiWOZ slot-filling prompts (Apache-2.0) → Path D pipeline | ~500 | Clarification supplement |
| **TOTAL** | **~42.5K** | |

That's ~38% external prompts, ~62% pure Path D — meaningfully more external than the original 70/15/10/5 sketch, because under prompt-seeds-only the licensing risk is much lower. Each external prompt becomes a Path D rejection-sampling input; each output is a compiler-validated CAS+English pair grounded in our framework.

**Attorney-cleared addendum (post Q1 resolution):**

If Q1 returns favorably for share-alike, ADD:
- Dolly 15k (CC-BY-SA-3.0) — ~10K → +24% to corpus, addresses concise-answer discipline
- SQuAD 2.0 unanswerables (CC-BY-SA-4.0) — ~5K → uniquely addresses OOD-abstention
- Natural Questions short-answer (CC-BY-SA-3.0) — ~5K → real-user query distribution

That brings the corpus to ~62.5K samples — within range of the v0 50K dialogue corpus that B-3 trained on, with much better signal alignment.

## 8. Sample exemplars (paste-in from each scout's reading)

(Placeholder — pull 2-3 concrete exemplars per dataset from the individual scout reports' "Sample readings" sections when surfacing this to user. Sample reading is the gate per `feedback_samples_are_the_only_true_eval_for_cas_native.md`.)

## 9. Action items

1. **Single IP attorney consult** — submit §6 brief; budget ~$500-1500 for one focused review covering Q1 + Q2 + Q3 + Q5 (the load-bearing four). Q7-Q13 can be addressed in a follow-up if needed.
2. **Default mix start** (no consult needed) — OASST2 + WildChat + HH-RLHF + MultiWOZ via prompt-seeds-only pattern. Begin Path D pipeline integration after Wave 3 + Path C-1 land.
3. **Attorney-cleared expansion** (post Q1) — Dolly + SQuAD 2.0 + Natural Questions if share-alike clears.
4. **Eval set population** — LMSYS Chat 1M prompts populate the brutal-normal-user eval set per B-4 §Step 1 (eval-only, no training contamination).
5. **Sample-read everything** — every dataset gets 5-10 records read before integration. Per `feedback_audit_corpus_before_proposing_reuse.md`: schema isn't quality.

## 10. References

- Three scout reports:
  - `docs/working/dataset_scout_dialogue_2026_05_07.md` (X1)
  - `docs/working/dataset_scout_qa_2026_05_07.md` (X2)
  - `docs/working/dataset_scout_casual_2026_05_07.md` (X3)
- Audit failure record: `docs/working/path_B4_human_relevance_failure_2026_05_07.md`
- Path D corpus design: `docs/working/path_D_corpus_pipeline_design_2026_05_07.md`
- Memory `feedback_external_data_for_conversational_discipline.md` (prompt-seeds-only pattern)
- Memory `feedback_no_foreign_architecture_cas_only.md` (architectural rule the prompt-seeds-only pattern preserves)
- Memory `feedback_samples_are_the_only_true_eval_for_cas_native.md` (sample-reading gate)
- Memory `feedback_audit_corpus_before_proposing_reuse.md` (read records before recommending)
