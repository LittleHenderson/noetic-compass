# Open questions — the owner's decisions for the continuity packet v1 (2026-10-20 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Each item below is the owner's to decide. The builder has not decided any of them. Each carries one line of recommendation so the owner can answer with one word.

1. **Sequencing against wave 7 (§7.98).** Land the two-file wiring only after the wave 7 reading is on the spec sheet (chosen in DESIGN section 5), or allow the wrapper form (`helm_chat_continuity.py`, no pinned file touched) sooner?
   Recommendation: wait for the wave 7 reading; one chat change at a time.

2. **Owner line and cap, if AWS is needed.** `CONTINUITY at 1 USD` (19 UTF-8 bytes; cap 1.00 USD, one attempt + one plumbing retry), used only if a unit's practice peak exceeds 300 MiB on the laptop.
   Recommendation: approve the line now so the laptop-first rule can fall back without a second round trip; expect 0 USD.

3. **Wide brain state during the exam.** As shipped (ON) in every arm, or a second pass with `HELM_WIDE_BRAIN=0`?
   Recommendation: as shipped only; the canonical brain is the wide brain and a second pass doubles the units for no new word.

4. **Equal-Bias resume (D-C1-3).** When the interruption wrote nothing, the Bias version is equal, and return-address rule 4 refuses `BIAS_EQUAL_NOT_NEWER`. Keep the rule and bump the version on suspend (a bookkeeping write), or add a distinct interruption-resume call that accepts equal?
   Recommendation: keep rule 4 and bump on suspend; one rule, no second code path.

5. **Idle advance.** Should a thread ever move on its own between lines in the chat (as the drive loop does on idle ticks), with a per-station wall-clock budget, or only on resume as in v1?
   Recommendation: not in v1; decide after this exam's word, because idle advance is what makes CUT hard.

6. **Does HELM say it resumed?** A one-line preface ("Picking up where I left off: ...") on a resumed answer, or the plain answer only?
   Recommendation: plain answer only in v1 (mark CONV is simpler and the voice is wave 7's concern); add the preface as a later voice item.

7. **Seed bands.** WORLDS 1,996,000,001 to 1,997,000,000 and INTERRUPT 1,998,000,001 to 1,999,000,000 (both above wave 7's last band at 1,995,000,000).
   Recommendation: accept; next free band after this packet starts at 2,000,000,001.

8. **Family mix.** 16 worlds each in F-A small talk, F-B unrelated stock, F-C cited stock (dirty restart), F-D two threads; 64 in all.
   Recommendation: accept; F-A is kept at 16 on purpose so the cheap baseline's tie is visible in the reported rows.

9. **THREAT margins.** 12 answers and 32 station crossings against RESTART_LAST_LINE.
   Recommendation: accept; 12 is a quarter of the 48 worlds where the path can win at all.

10. **Where threads live on disk.** `threads.jsonl` in the chat's session folder (`HELM_SESSION_DIR`), or inside the cube store under its own context id?
    Recommendation: the session folder; the cube store holds facts, and a thread is not a fact until it finishes through the gate.

11. **A thread's lifetime.** Does a WAITING thread outlive the chat session (saved and reloadable next session), or die with it?
    Recommendation: dies with the session in v1; a cross-session resume is a different exam with its own stale rules.

12. **Who builds.** The same builder as the design, or a separate builder blind to this packet's forecasts (section 11)?
    Recommendation: a separate builder, as wave 7 separated builder and custodian; the designer then reviews the FIX FIRST record only.
