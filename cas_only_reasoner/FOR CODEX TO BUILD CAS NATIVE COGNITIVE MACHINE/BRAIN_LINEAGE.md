# The learning brain — lineage record

**This file is the single place that names the brain that learns, says what it has actually
achieved, and says where the proof is. Every agent that touches this work reads this file first
and updates it in the same commit as any new result.**

If you are an agent picking this up: do not rename the brain, do not restate a result from prose,
and do not promote a claim that this file marks as not certified. Add a row to the table, point it
at the evidence folder, and leave the old rows alone. Negative results stay. They are the reason
any of the positive ones can be trusted.

**If your job is to audit, verify, or independently test this work rather than extend it, read
`AUDIT_PACK.md`** — it carries the exact commands, the frozen numbers, the file hashes, the traps
that have already fooled people, and eight attempts to break the claim that you are expected to run
and report on.

---

## The brain

| | |
|---|---|
| **Name** | **Helm** |
| **Current version** | **1.0 — CERTIFIED** |
| **What it is** | The learning part of the CNCM pointer machine. It reads a small structure of parts and "contains" links, and answers questions about which part holds which. |
| **Learned numbers** | **157,919**, in **46** groups |
| **Biggest group** | the word table, `declaration_table`, 1,024 × 64 = **65,536**, which is **41.5%** of the whole brain |
| **Does it grow as it learns?** | **No.** Learning changes the values, never the count. The count moves only when the design is widened on purpose, and that is a version bump. |

### Versioning scheme

| version | meaning |
|---|---|
| **0.x** | being tried out. Nothing officially certified. |
| **1.0** | the first version that passes the official three-run test. |
| **1.1, 1.2** | same shape, trained better. |
| **2.0** | the shape changed, so the number count moved. |

---

## Helm 1.0 — CERTIFIED on 2026-09-20

**The grader printed the label. This is the first version that earned it.**

```
LABEL : LEARNS_NEW_WORLDS
integrity: pass, failures []
```

The label was printed by `records/typed_pointer_001/evaluate_gates.py`, run over
`records/typed_pointer_001/admission_001/study.json` by `execute_study.py` as the last step of the
study itself. **No hand was on it.** Certifying reading:
`records/typed_pointer_001/admission_001/gate_reading.json`, 202862 bytes, sha256
`475379d2f9d47387a821c79e03a239f9a1f1277a0bbb25b298417557f9b058a9`.

### The three runs

Three seeds, three separate machines, run one after another on AWS. Every one of them finished
completely: launcher status `AWS_CANDIDATE_FINISHED`, `completed_deliverable: true`,
`cleanup.complete: true`, worker status `COMPLETE_TYPED_POINTER_ARM`, **no failed checks**, and the
save-and-reload step verified `true`.

| | seed 20260917 | seed 20260918 | seed 20260919 |
|---|---|---|---|
| the frozen 18, before | **2 of 18** | **0 of 18** | **0 of 18** |
| the frozen 18, after | **12 of 18** | **12 of 18** | **11 of 18** |
| gained | **10** | **12** | **11** |
| broken (must be 0) | **0** | **0** | **0** |
| the bar (7) | cleared | cleared | cleared |
| odds this is luck | **1/1024** | **1/4096** | **1/2048** |
| kinds improved (need 2) | **3** | **3** | **3** |
| worlds improved (need 2) | **5** | **5** | **5** |
| never-shown worlds, per answer (127) | 9 → **84** | 2 → **88** | 5 → **81** |
| taught worlds, per answer (358) | 16 → 258 | 10 → 284 | 13 → 275 |
| the whole course (564) | 30 → **392** | 17 → **422** | 20 → **407** |
| memory check (96) | 93 → 93 | 93 → 93 | 87 → 87 |
| the run's own clock | 7791.257429470999 s | 7834.867562267 s | 7792.573039091 s |

**All three seeds passed the primary test.** Nine of nine gate comparisons that the label depends on
came back `pass`.

### Every gate the grader reported

| gate | result |
|---|---|
| `integrity` | **pass** — `failures: []` |
| **`G_LEARN_population`** — the label's own test | **pass, all 3 seeds** |
| `G_LEARN_all_kinds` | pass, all 3 seeds |
| `TRAINED_start_to_final` | pass, all 3 seeds |
| `TRAINED_first_to_final` | pass, all 3 seeds |
| `G_LEARN_DIRECT_READ` | pass, all 3 seeds |
| `MORE_PRACTICE_population` | **fail, all 3 seeds** |
| `G_LEARN_TEXT` | **fail, all 3 seeds** |
| `kind_g_learn` (8 kinds) | **fail, all 3 seeds** |

### The three that did not pass, and why they are not failures of the claim

These are REPORTED comparisons, not the label. Say all three plainly whenever this result is quoted,
because a reader will notice them.

- **`MORE_PRACTICE_population` — failed.** It asks whether the machine got better *after its first
  pass*, i.e. whether extra practice beyond the first pass bought anything on the frozen 18. It did
  not: most of the gain lands in pass 1. So the honest reading of Helm 1.0 is **"it learned from the
  teaching it was given"**, not "it kept improving the longer it trained". This matches the earlier
  finding that the training loss flattened from pass 6.
- **`G_LEARN_TEXT` — failed.** That is the `role_set` tier, 6 questions, where **0 were gained and 0
  lost**. Nothing got worse; nothing got better. It is a null result on a tier the label does not use.
- **`kind_g_learn` — all eight failed.** These compare each question kind on its own, and the small
  kinds have only 5 or 6 questions. With a bar of 7 improved, a 5-question kind **cannot pass by
  construction** — the arithmetic makes it impossible regardless of the machine. These entries are
  informational. One of them is worth reading anyway: `edge_account`, `parts` and `reach` are where
  the real gains are, and those are exactly the three the primary test names as improved.

### A weakness in this test, found on 2026-09-20 — read this before quoting the result

**The five "never-shown worlds" are new parts and new names arranged in wiring that teaching had already
shown. All five. This was measured, not suspected.**

Throw away the part names and look only at the wiring — which part points at which — treating any
renaming of the same pattern as the same pattern. Then:

- Teaching used **19 worlds but only 6 distinct wiring patterns**. Five of the 19 share one pattern,
  five share another, and the rest repeat three more.
- The five test worlds use **4 distinct patterns**, and **all 4 of those are among the 6 patterns
  teaching already contained**.
- So **5 of the 5 test worlds** are a pattern Helm had already practised, redecorated with new part
  names.
- Part names are genuinely new: 68 distinct names in teaching, 20 in the test worlds, and only
  **two** appear in both — `Chuck` and `Gear`.

**What this does and does not change.**

It does **not** change the certified label. The grader is frozen, the question set was fixed before
the result was seen, and the worlds really were never read during training. `LEARNS_NEW_WORLDS` was
printed by that grader and stands.

It **does** narrow what the words mean. The honest description of Helm 1.0 is:

> new parts, new names, **already-seen wiring**.

Not "new worlds" in the sense a reader would assume. Helm did not have to work out a new kind of
structure. It had to apply a structure it had already seen to parts it had not, and get the direction
right. That is still real work — the before-behaviour was listing every possible pair and even naming
a part as containing itself — but the test is easier than the phrase "worlds it had never seen"
suggests, and anyone quoting this result must say so.

**The fix for Helm 1.1** is a harder test set: held-out wiring patterns that appear **nowhere** in
teaching, and larger worlds with more parts. Six patterns is a thin basis for a transfer claim, and
the current test cannot detect whether Helm can generalise to a shape it has never seen.

### What may be claimed, and what may not

**MAY be claimed:** Helm 1.0, measured by the frozen grader over three independent runs whose
question set was fixed before any result was seen, learned to read which part contains which in
**machines it had never been shown**, going from 0–2 of 18 to 11–12 of 18, gaining 10, 12 and 11
questions while breaking none, across 3 question kinds and all 5 held-out worlds. Retention held.
**Say it as: new parts, new names, already-seen wiring** — the section above this one measures why the
last three words are required.

**MAY NOT be claimed:** that it works on anything beyond small structures of parts and containment
links; that the transfer is to a novel *domain* (the five held-out worlds are the same kind of thing
as 11 of the taught ones — machines); that the transfer is to **novel wiring**, which was the original
wording here and is **measured false** — all 5 held-out worlds reuse a pattern teaching already
contained, out of only 6 patterns teaching ever had; that it would handle a shape it has never seen,
which this test cannot tell you; that extra practice beyond the first pass helps; that the whole CNCM
machine exists.

**Also not claimed, and worth stating because it is easy to slide past:** this is a result on a
**fixed, stored** test set, not on new work arriving later. By the standard set out in
`CAS_RPA_Replay_Policy_Lab_Development_Directive_v1.md` section 12, that makes it a *screening*
result. "Fresh benefit" — does it help on genuinely new work under matched conditions — has **not**
been demonstrated for Helm and would need a different experiment.

**Certified is not the same as independently audited.** The grader is frozen and the runs are real,
but the same session built the machine and read the result. `AUDIT_PACK.md` names the checks and the
falsification attempts an outside agent should run.

---

## Helm 0.1 — the record (uncertified, kept as history)

**Measured on 2026-09-20**, job `cas-meta2-tpntr-20260920033528-1af25973-m-20260917`, seed
`20260917`.

### What it was taught

A world is a small set of parts with "contains" links between them. Teaching used **19 worlds**:

- **11 machines** — four parts, three links each, e.g. a Loom, Shuttle, Thread and Bearing wired
  together.
- **8 grammar patterns** — e.g. "a list pattern": **List, Item, Determiner, Marker**, where List
  contains Marker, Item contains Marker, and List contains Determiner.

**8 kinds of question** were asked, **564 questions** in all: `context` 70, `correspondence` 88,
`reach` 107, `definition` 70, `role_set` 36, `parts` 53, `analogy` 70, `edge_account` 70.
358 questions were used for practice, **127 were held back**, 79 were set aside and never counted.

Training: **10 passes**, **1470** weight updates, about 526 seconds per pass.

### What it was tested on

**5 worlds it was never shown.** All five are machines in a workshop. The link count varies — one of
them has four links, the rest have three.

| machine | its parts | what contains what |
|---|---|---|
| a weaving machine | Bearing, Loom, Shuttle, Thread | Loom→Thread, Shuttle→Thread, Loom→Bearing |
| a turning machine | Bolt, Chuck, Lathe, Tool | Lathe→Chuck, Lathe→Tool, Tool→Bolt |
| a transmission assembly | Gear, Gearbox, Manifold, Shaft | Gearbox→Shaft, Shaft→Gear, Gear→Manifold |
| a stopping assembly | Brake, Disc, Pad, Pinion | Brake→Pad, Brake→Disc, Disc→Pinion |
| a lifting machine | Bracket, Cable, Crane, Hook | Crane→Hook, Crane→Cable, Cable→Bracket, Hook→Bracket |

**Honest scope of the claim.** These five are the *same kind* of thing as some of the worlds it was
taught — machines — so this is transfer to **new individuals with new part names and new wiring**,
not to a wholly new kind of thing. That is real transfer. A machine that had memorised would fail
it. It is not a claim about novel domains.

### How well it did

The graders fixed **18 questions in advance**, all about the five never-shown worlds. This is the
score that counts, because it was chosen before the result was known.

| measure | before | after |
|---|---|---|
| **the frozen 18** | **2 of 18** | **12 of 18** |
| used to be wrong, now right | — | **10** |
| used to be right, now wrong | — | **0** |
| the bar it had to clear | — | **7** |
| odds this is luck | — | **1 in 1024** |

Everything else measured, for the record:

| measure | before | after |
|---|---|---|
| held-out worlds, per answer (127) | 9 right | **84 right** |
| taught worlds, per answer (358) | 16 right | 258 right |
| the whole course (564) | 30 right | **392 right** |
| all 45 eligible held-back questions | — | 26 gained, **0 lost** |
| taught questions (189) | — | 124 gained, **1 lost** |
| held worlds, retention check (96) | 93 | 93 |

### What it said before and after — the clearest evidence

Four of the ten gained questions, in the machine's own words:

| the machine | before | after | correct |
|---|---|---|---|
| a turning machine, every link | 7 links incl. `Tool contains Tool`, `Bolt contains Lathe` | `Lathe→Chuck`, `Lathe→Tool`, `Tool→Bolt` | same |
| a weaving machine, every link | all **12** possible pairs incl. `Thread contains Thread` | `Loom→Bearing`, `Loom→Thread`, `Shuttle→Thread` | same |
| a weaving machine, what the Loom holds | **nothing** — empty answer | Bearing and Thread | Bearing and Thread |
| a transmission assembly, what the Gearbox holds | Manifold | Shaft | Shaft |

Before, it was guessing: listing every pair, naming a part as containing itself, or answering
nothing. After, it read the actual structure of a machine it had never seen.

### The official verdict

**NOT CERTIFIED** — this is **Helm 0.1's** verdict, kept as history. Helm 1.0, above, is certified. The
paragraphs that follow explain why this particular run can never be certified, and that reason is a
lesson worth keeping.

The run itself succeeded completely — status `COMPLETE_TYPED_POINTER_ARM`, no failed checks, the
save-and-reload step verified `true`, 99 of 99 required files produced. But the frozen grader
**did not certify it and cannot**, for two hard reasons:

1. The certificate is written by the launching program, not by the machine doing the training. That
   program was killed by an interrupted tool call before it wrote the certificate. The grader reads
   `completed_deliverable` and `cleanup.complete` out of that file.
2. The ledger refuses to run the same job twice (`JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY`), so that
   job can never be run again.

There is no collect-only path, and writing the certificate by hand is forbidden — that is exactly
the forgery the whole design exists to prevent.

**So the correct way to describe Helm 0.1 is: the learning is real and measured with the graders'
own test code, and it is not an official pass.** Never write that Helm 0.1 "passed".

### Where the proof lives

| what | where |
|---|---|
| the machine's own records, 612 files, 143 MB | `records/typed_pointer_001/receipt_20260917_orphaned_1af25973/s3_worker_records/` |
| the launcher's records from that attempt | `records/typed_pointer_001/receipt_20260917_orphaned_1af25973/` |
| the grader | `records/typed_pointer_001/evaluate_gates.py` |
| the frozen question set, 18 questions | `cas_meta2/typed_teaching/pointer_contract.py`, `relational_population` |
| the three runs meant to earn the certificate | `records/typed_pointer_001/receipt_2026091{7,8,9}/` |

---

## Generations

Add a row. Never edit an old one.

| version | date | numbers | taught on | tested on | the frozen 18 | official verdict | evidence |
|---|---|---|---|---|---|---|---|
| **Helm 1.0** | 2026-09-20 | 157,919 | 19 worlds (11 machines, 8 grammar patterns) | 5 never-shown machines | 2/18→**12/18**, 0/18→**12/18**, 0/18→**11/18**; gained 10, 12, 11; lost 0 | **`LEARNS_NEW_WORLDS` — CERTIFIED, all 3 seeds** | `receipt_2026091{7,8,9}/` + `admission_001/gate_reading.json` |
| **Helm 0.1** | 2026-09-20 | 157,919 | 19 worlds (11 machines, 8 grammar patterns) | 5 never-shown machines | 2/18 → **12/18**, gained 10, lost 0 | **NOT CERTIFIED** | `receipt_20260917_orphaned_1af25973/` |

---

## Rules for whoever comes next

1. **A result is only a result if a grader printed it.** The grader here is
   `records/typed_pointer_001/evaluate_gates.py`, run over a study file. Run it and quote what it
   printed.
2. **Never call an uncertified run a pass**, however good its numbers look. Say "measured, not
   certified" and give both numbers.
3. **Never write or edit a certificate, a lifecycle record, or a reservation by hand.** If a run's
   certificate is missing, the run is lost. Say so and run it again.
4. **Never change the 18-question set or the pass mark** to make a result land. They were fixed
   before the result was known; that is the only reason they mean anything.
5. **Do not delete a failed run's folder.** Run 7's failure and the two killed attempts are what
   prove the fixes were real.
6. **Update this file in the same commit as the result**, and point the new row at the folder.
