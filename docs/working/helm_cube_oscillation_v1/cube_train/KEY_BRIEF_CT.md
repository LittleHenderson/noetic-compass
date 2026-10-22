# KEY BRIEF — CUBE TRAIN lines (for the AI model keyers)

You read lines a person typed about a made-up subject (hive yards, or bus lines). For each line you are told the
`thing` (a yard or line name) and `about` (the words naming which fact of that thing). Say what the LINE states as the
CURRENT value of that fact:
- `value`: the number word, or the name, the line gives as the current value of that fact, copied exactly as written in
  the line; `NONE` when the line states no value for it (for example "I don't remember…", or small talk).
- `replaces`: when the line says an earlier value was wrong ("…, not seven", "instead of seven", "seven was wrong"), that
  old value copied exactly; otherwise `-`.
Ignore any other number, month, place or name the line mentions in passing: only the current value of the named fact
counts. Do not guess: if the line does not clearly state it, say `NONE`.

Reply with ONLY a JSON list, one object per line: `{"id": "<id>", "value": "<word or NONE>", "replaces": "<word or ->"}`.
No other text.
