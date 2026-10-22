# Open questions — the owner's decisions for the memory-compaction packet v1 (2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Each item is the owner's to decide. The designer has decided none of them. Each carries one line of recommendation and the cost of each option, so the owner can answer with a number and a word. Operational details (folder names, instance size, retention) are not here; they are the operator's.

## Answered 2026-10-21 PDT (after the merge of PR #441)

Owner's words, typed into the design session, verbatim: `“add them”; OPEN_QUESTIONS Q1–Q3 in one line (recommended: “build v1, rule capsules, census first”).`

Reading recorded (the owner may correct it with one word): **Q1 = (a)** build v1 now behind its own switch, default OFF; **Q2 = (a)** run the free census first, with its STOP floor; **Q3 = the rule skin** (the §7.31 CCE skin writes the capsule's CAS in v1; no CTT, 0 USD). "add them" = the four Atlas scenarios go into DESIGN §6.1 (done in the same commit). Q4–Q14 remain open; the recommendations stand as written. No money is approved by this line; no test line is signed.


1. **Go or hold on the line of work.** Build v1 (rule capsules, laptop, 0 USD) now, or hold until the talk packet's exam (`TALK EXAM at 1 USD`) has a word, since both change the chat.
   Options: (a) build v1 now behind its own switch, default OFF: 0 USD, a few laptop sessions; (b) hold: 0 USD, nothing learned about memory until the talk line settles.
   Recommendation: (a). The switch keeps the two lines apart, and the census (Q2) is free either way.

2. **The free census first.** Count how many turns today's FIFO dropped in the sealed chat sessions c51–c54 and how often `user_facts` hit its cap of 20. Counts only, STOP floor: if fewer than 8 turns were dropped across all four sessions, the squeeze does not matter yet and the packet waits.
   Options: (a) run it (0 USD, under an hour); (b) skip it (0 USD, but the design's "space fills" premise stays unmeasured).
   Recommendation: (a).

3. **Who writes the capsule's CAS in v1: the rule skin or the CTT.** The hand-written CCE skin of spec §7.31 (laptop, 0 USD, no torch) or a new compaction head on the CTT (AWS GPU, `COMPACT TRAIN at 3 USD`, and then the exam must run on a CPU host because the ears cannot run on the laptop).
   Recommendation: the rule skin for v1; the CTT head only after v1 has a word. It keeps the first test at 0 USD and keeps the CTT's `EARS_HARMED` negative in view.

4. **The mechanism-free baseline must stay in.** `SUMMARY_TEXT` (a plain-English note with the same clues and breadcrumb, no CAS) is the arm the CAS capsule must beat by +4. The honest forecast is a tie on recall. If the owner wants the CAS form kept for checkability regardless of recall, say so now, and R2 becomes reported-only.
   Options: (a) R2 required for the keep word (as written); (b) R2 reported only. Both 0 USD.
   Recommendation: (a). If CAS capsules do not beat a text note, the owner should know that from a frozen number, not from prose.

5. **Which compiler is the compiler of record.** The repo copy (5,813 lines, on the thread branch, pinned by the package) or the newer site copy (6,415 lines, sha256 `464fd4ad…`, local only, adds nesting analysis and CAS-Ohm).
   Options: (a) repo copy: 0 USD, pinned by `git show`; (b) site copy: 0 USD, but it must be vendored into the package by hash first, and nesting is not needed for v1 capsules.
   Recommendation: (a) for v1; (b) when a capsule needs a nested Noetic form.

6. **Which budget triggers compaction in v1.** Turn budget only (B = 12, as frozen) or turn budget plus a byte budget.
   Options: (a) turns only: simplest, deterministic; (b) both: closer to the owner's "as space gets taken up", but the byte line depends on the machine and makes replay harder.
   Recommendation: (a) for v1; the byte line in v2 with a fixed per-item size table so replay stays exact.

7. **Who writes the teaching turns.** AI model families only, the owner reviews (the talk packet amendment's rule), or named people.
   Options: (a) `LLM_WRITTEN` by at least three families, keyed by a fourth: 0 USD where free tiers cover it, label `LLM_WRITTEN_ONLY`; (b) named people: 0 USD but the owner said that writing is too much work.
   Recommendation: (a), per the owner's ruling of 2026-10-21 afternoon.

8. **The subject templates.** Two frozen subject templates (a family's beekeeping year; a town's bus lines) or one. More templates cost design time, not money.
   Recommendation: two, so the result is not about one subject's shape.

9. **May the scripted person give a wrong refresh answer?** In v1 the scripted person answers right (0.75) or "I don't remember" (0.25), never wrong. A wrong-answer stratum would test whether strengthening can be fooled.
   Options: (a) no wrong answers in v1; (b) a 0.10 wrong-answer share with a mark that a fooled strengthening counts as HARM.
   Recommendation: (a) for v1, (b) in v2; one new failure mode per test.

10. **Planted damage to the COLD copies.** M1 planted missing, corrupt and stale copies and failed on exactly that gate (H8). v1 as written plants none, so HG-H8 is tested only on the clean path.
    Options: (a) no planted damage in v1 (as written); (b) plant 2 damaged copies per world as M1 did, so HG-H8 is exercised.
    Recommendation: (b). It costs nothing and it is the one gate that has already failed once; a clean-path-only pass would not be worth much.

11. **The Eye's mode in TEACH-1.** REPORT-ONLY with a plain routine doing the housekeeping (as written), or the Eye's involuntary tier doing the housekeeping itself.
    Options: (a) report-only: 0 USD, the Eye's acting stays untested here and `NOT LICENSED`; (b) the Eye acts: needs its own U-series test and a control that cannot repeat answers (the U1 lesson), its own owner word, 0 USD on the laptop.
    Recommendation: (a) inside TEACH-1; (b) as a separate test after it.

12. **The exam host.** The laptop (0 USD; v1 has no torch) or one m6i.xlarge-class CPU host under `COMPACT EXAM at 1 USD` (expected under 0.10 USD) if the laptop's memory refuses 7 arms × 16 worlds.
    Recommendation: the laptop first; the line only if the practice run shows the laptop cannot hold it.

13. **The real cloud COLD tier.** Not in v1 (a local folder stands in). When the owner wants it: name the bucket, prefix, retention and a monthly cap (M1 `CLOUD_TIER.md`); storage of a few megabytes is under 0.01 USD per month, but the owner's word is required for any new AWS destination.
    Recommendation: after v1 has a word.

14. **Who builds.** The same designer, or a separate builder blind to this packet's forecast (prereg §11).
    Recommendation: a separate builder, as wave 7 separated builder and custodian; the designer reviews the FIX FIRST record only.
