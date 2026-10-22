# KEY FORMAT — TEACH-2 keyed teaching turns (the file `custody_t2.py finish --turns` reads)

**Plainly.** Every teaching line an AI model wrote is read by two other AI models, of two other families, who say what
fact the line states. If both readings match the plan, the line is `AGREE` and may be taught. If they differ, the line is
`UNDETERMINED` and goes back to its writer. The quiz answers themselves never come from these keys: they come from the
SDG world (`WORLDS.json`), drawn at the WORLD seed. The keys only prove that each line says what the plan says.
TEACH-1's key format with the TRAP kind added: a `TRAP` line is keyed like a `FACT` — each keyer names the TRUE value
the line states as the fact, never its decoy.

## The file

One JSON object, UTF-8, LF line endings:

```json
{
  "schema": "helm.teach2.keyed-turns/1",
  "turns": {
    "W01": [
      {
        "turn_index": 1,
        "kind": "TRAP",
        "fact_id": "C3",
        "trap_role": "FIRST",
        "text": "<the writer's line, byte for byte as returned>",
        "value": "<the plan's value, or null>",
        "not_value": "<FIX only: the plan's wrong value, else null>",
        "label": "LLM_WRITTEN",
        "writer": {"vendor": "<family, e.g. google>", "model": "<model name>", "version": "<as reported>"},
        "key1": {"vendor": "<a second family>", "model": "...", "states_fact_id": "C3", "states_value": "<value or null>"},
        "key2": {"vendor": "<a third family>", "model": "...", "states_fact_id": "C3", "states_value": "<value or null>"},
        "keyed": "AGREE"
      }
    ]
  }
}
```

## The rules the checker applies (`turns_t2.check_turns`, sealed mode)

| Field | Rule |
|---|---|
| `turns` | 16 worlds (`W01`–`W16`), 32 objects each, `turn_index` 1–32 in the plan's order |
| `kind`, `fact_id`, `value`, `not_value`, `trap_role` | copied from the writer packet, never edited |
| kinds | at least 18 `FACT`, exactly 4 `TRAP`, at least 2 `FIX`, at least 2 `SMALL`; every fact stated once by a `FACT`, an `UNKNOWN` or a `TRAP` with `trap_role` `FIRST` |
| `text` | the writer's line, unchanged; every rule of WRITER_BRIEF_TEACH2.md holds |
| `label` | exactly `LLM_WRITTEN` |
| `writer.vendor`, `key1.vendor`, `key2.vendor` | three DIFFERENT model families on every keyed turn; at least three families wrote the turns of each world; no family wrote more than half of a world's turns |
| `key1`, `key2` | present on every `FACT`, `TRAP`, `UNKNOWN`, `FIX`, `RESTATE` turn; each keyer reads the line alone (blind to the plan) and writes which fact it states and with what value (`null` for `UNKNOWN`) |
| `keyed` | `AGREE` when both keys name the plan's `fact_id` and `value` (for `FIX`: the new value; for `TRAP`: the true value, not the decoy); else `UNDETERMINED`, and the line is refused and rewritten |
| `SMALL` turns | `fact_id` and `value` null; keys optional; the line must carry no fact (a key that finds one sends it back) |

Agreement between the two keys is counted and reported per kind (`EXAM_CHECK_TEACH2.json`).
The owner reviews the file and never writes or keys a turn.
