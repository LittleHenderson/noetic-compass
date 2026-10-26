# HELM speech v3 — tags, context encoding, conversation data

This folder preserves the working files behind the conversational upgrade, copied from the training payload so they
are not single-copy.

- speech_tags_v2.py — 24 situation tags, 8 varied realizations each.
- uild_tag_data_v2.py — builds and guard-checks the tagged rows (2,760 passed).
- uild_conversation_data.py — 10 coherent multi-turn dialogues → 43 context rows.
- mouth_task/vocab_m.py — **v3 encoder**: the source now carries the situation tag and the prior turns. In v1/v2 the
  situation argument was accepted and **ignored**, so the model never knew what kind of turn it was writing.
- mouth_task/check.py — social tags may use idiomatic number words; fact tags keep the strict rule; digits and
  invented facts stay blocked.
- data/ — generated rows and the tag statistics.

Not yet trained: mouth v3 training on the mixed corpus and a multi-turn held-out evaluation are the next steps.
