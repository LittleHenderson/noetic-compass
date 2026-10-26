# Outside review

Asked for model: `deepseek-v4-pro`. Answered by model: `deepseek-v4-pro`. Finish reason: `stop`.

Files sent:

- `08_OPTION_B_PLAN_v1_0.md` (117215 bytes, sha256 `7fee7afd59e1e0da94ed62433847450ad5474cfffe72351d10c4893ec53fd0c7`)

## Reply, word for word

VERDICT: ACCEPT_WITH_NOTES

**MAJOR — §§13/15.4, report line for code 7.**  
The standard error is defined as standard deviation of 10,000 resamples divided by the count. That is not a bootstrap standard error; it will be many times too small, making the “gain under about X points could have been missed” number near 5 points even when real uncertainty is much larger. This contradicts §20.4 and can misread a miss.  
Fix: use the standard deviation of the resampled differences as the bootstrap SE, or use the 95% percentile range directly for X; remove division by count.

**MAJOR — Intended change (1), §10 Step 1/D4, Step 4, Step 7.**  
Making the question writer DeepSeek v4-pro puts the question writer in the same vendor family as label team B, the key solver `deepseek-chat`, and the ordinary-note writer `deepseek-chat`. This creates shared model-family priors between question writing, key validation, and the ordinary notes. The likely tilt is toward ORD-INFORMED/ORD-FREE or toward shared blind spots, weakening the “independent model families” guard.  
Fix: keep a different-vendor question writer, or move the ordinary-note writer/key solver to another vendor; otherwise this dependency must be explicitly pre-registered as a known limitation.

**MAJOR — Intended change (2), §10 Step 7, D6, §11.1 who-sees-what.**  
Using Claude Sonnet from the start as the support checker conflicts with the plan’s own statement that Claude agents get CAS definitions in project instructions and cannot be blind. The support checker is part of producing the rival ordinary notes, so the ORD rival is no longer clearly independent of CAS-informed processing. Direction of tilt is uncertain, but the control is contaminated.  
Fix: use a support checker with no project-level CAS exposure, or run Claude in a task where no CAS definitions are present and pin that context.

**MAJOR — Plan not yet synchronized with the two intended changes.**  
§10 Step 1, §10 Step 7, D4, and D6 still describe Gemini as question writer and Gemini as support checker with a Claude fallback. If sealed as written, plan, constants, and tools will disagree or the wrong services will be called.  
Fix: update every affected section, `PLAN_CONSTANTS.json`, and tool input before seal; delete the now-dead Gemini blocked/fallback rule if Claude is primary checker.

**MAJOR — §11.1 repair lines, §19.1, §24 items 29–30.**  
`TR_TOOLS_REPAIRED` and `6R_PROGRAMS_REPAIRED` allow changing sealed tools/programs after derivation has begun. Even with review records, this is a post-seal code-change path that could alter question/note filters after practice counts are seen.  
Fix: remove repair lines after seal; if a sealed tool/program fails, stop and require a new reviewed plan version. If repairs are kept, forbid them after any derived file has been used or any final question/note exists.

**MAJOR — §15.4 C5 with §11.2 QUOTES-ONLY.**  
QUOTES-ONLY removes role tags, canon definitions, and Mind/related fields all at once. So C5 cannot isolate “role names add anything beyond pointing”; it tests the whole role-note apparatus against bare quotes. A C5 pass may be due to definition lines or relation fields rather than correct role names.  
Fix: state in §21 that the pass shows formatted role information, not names alone; or add a group with names/definitions but no label-relation fields if the third question is to be answered separately.

**MAJOR — §15.4 outcome table / §21 status table.**  
The outcome table has two rows numbered 8, while §21 refers to 11 outcome codes. This makes the central code list ambiguous to readers and to the owner-signed status table.  
Fix: renumber the codes 1–11 uniquely and update the status-table count and keys.
