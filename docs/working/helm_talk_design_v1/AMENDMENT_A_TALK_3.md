
## Amendment A-TALK-3 (2026-10-22 PDT) — five wording fixes to A-TALK-2 B4 and B6, found by the builder's own sample lines; written before the code change

Status: appended after A-TALK-2 (`52ceea92…`); nothing above is edited. Where it disagrees with A-TALK-2 B4 or B6, this governs. Still a build behind switches OFF by default; 0 USD; nothing licensed.

**What the sample showed (BUILDER_SAMPLE, `build_v1/SAMPLE_TALK_V1_20261022.json`; the builder's own 21 lines, facts that license nothing).** With HELM_TALK ON every guard held on every line (0 CAS tokens, 0 recipe-speak, 0 opinions, 0 replies over 3 sentences, exactly one question on 7 of 7 off-topic lines, 7 of 7 kept word for word, 0 tool-engine turns). Five replies still read badly: "What happened with Mount?" (the name "Mount Tam" cut in half); "What's going on with weather?" (no "the" before a common word); "What's going on with down?" (a word of "run down"); "How is Biscuit going?" (a template that fits a project, not a dog); "You told me we have 12 of flour." (the unit "cups" dropped).

**W1. A name is the whole run of capitalised words.** B4's first rule takes the first run of consecutive capitalised words after the line's first word (not a month, not "I"), joined by spaces ("Mount Tam").

**W2. "the" before a common word.** When B4's word is not a name (it came from the content-word rule), the templates read "the {w}"; a name is used as typed.

**W3. Words that are never the topic.** B4's content-word rule skips a frozen list `NOT_A_TOPIC` of feeling, time and filler words: feeling, feel, feels, tired, today, tonight, week, weekend, morning, night, lately, day, days, long, down, run, strange, kind, sort, pretty, really, been, going.

**W4. Two templates, both fit anything.** `OFF_QUESTIONS` = "What's going on with {w}?" / "What happened with {w}?" (chosen by the line's word count, so a replay is exact). When no word is left: "Do you want to tell me more?" (template words only).

**W5. Stock in its own unit.** B6's stock question says the amount with the unit the person gave (`loop.units`, e.g. "cups"): "You told me we have 12 cups of flour. Is that still right?"; with no unit on record, "12 of flour" stays.

Tests for W1–W5 are written before the change; every A-TALK-2 test stays.
