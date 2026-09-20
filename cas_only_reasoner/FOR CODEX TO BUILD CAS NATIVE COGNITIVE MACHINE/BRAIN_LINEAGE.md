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
| **Current version** | **0.1** |
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

## Helm 0.1 — the record

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

**NOT CERTIFIED.** This is the most important row in this file.

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
