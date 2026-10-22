
## Amendment A-CUBE-TRAIN-3 (2026-10-22 PDT) — the AI-written stratum's kept sizes, and a keying gap; written before the seal and before any training

Status: appended after A-CUBE-TRAIN-2 (`170f3cd2…`); nothing above is edited. Where it disagrees with the pre-code §4.2/§4.4 sizes or I6, this governs. Nothing is sealed or trained.

**What happened (recorded in `cube_train/llm/LLM_STRATUM_RECORD.json`):** all 1,500 slots were written (TRAIN 1,200, DEV 300; 1,499 passed the checker after one rewrite round). Keying: Anthropic 999 of 999, OpenAI 1,000 of 1,000, Google 900 of 999 — Google's last batch (99 OpenAI TRAIN lines) failed with a rate limit (HTTP 429) on `gemini-3-flash-preview` and again on `gemini-3.1-pro-preview` (one retry each, recorded). A line without both keys is dropped, never guessed.

**Kept rows:** TRAIN **1,091** (anthropic 398, google 394, openai 299; FACT 605, TRAP 156, FIX 110, UNKNOWN 110, SMALL 110); DEV **295** (anthropic 100, openai 98, google 97; FACT 165, TRAP 40, FIX 30, UNKNOWN 30, SMALL 30).

1. **Sizes are written counts; kept counts are recorded.** The pre-code's "1,200" and "300" are the WRITTEN counts. The kept counts above are the stratum. Floors (instrument row I6, replacing "DEV has its frozen sizes" for the AI-written part): TRAIN kept ≥ **1,000**, DEV kept ≥ **270**, every family ≥ 90 DEV lines. Both hold.
2. **The gap.** The 99 unkeyed OpenAI TRAIN lines may be keyed by Google once its quota resets and added, but ONLY before the seal; after the seal nothing is added.
3. **DEV-LLM rates** (G-CONFIDENT-WRONG, G-EXERCISED) are computed over the kept DEV lines (295 now).
