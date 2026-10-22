
## Amendment A-CUBE-TRAIN-2 (2026-10-22 PDT) — how the three writer families are reached; written before any line is written

Status: appended after A-CUBE-TRAIN-1 (`cfe77203…`); nothing above is edited. Where it disagrees with the pre-code §4.2 ("the same three command-line writers as TEACH-1"), this governs.

Found by a one-question smoke test (no line written): the Claude command-line tool's login has expired ("OAuth access token has expired"); the Codex tool's default model (`gpt-6-luna`) is refused on the owner's ChatGPT account; the Gemini tool must be called by its launcher path on Windows. The owner writes nothing (A-TEACH2-17), so no re-login is asked for.

1. **Anthropic family:** written and keyed by Claude helper agents of this session (model `opus`), each in a fresh context, given only the writer view of the slots (never the truth fields) or the keyer items, through prompt and reply files under `cube_train/llm/prompts/` and `cube_train/llm/replies/`. Labelled `anthropic / claude subagent (opus)`.
2. **OpenAI family:** `codex exec`, model `gpt-5.6-terra` (TEACH-1's Codex writer model), reasoning effort `medium`, read-only sandbox, an empty working folder.
3. **Google family:** `gemini`, model `gemini-3-flash-preview` (TEACH-1's Gemini model), by its launcher path, an empty working folder.
4. **Batching:** five worlds (100 slots) per writer call; one rewrite round per batch for refused lines; keyers get 100 lines per call. Every prompt and reply is saved.
5. Unchanged: the briefs (`WRITER_BRIEF_CT.md`, `KEY_BRIEF_CT.md`), the checker, the rule that a line is kept only when both other families key the generator's truth and the copy rule holds, 0 USD (subscriptions the owner already pays for; the helper agents are part of this session).
