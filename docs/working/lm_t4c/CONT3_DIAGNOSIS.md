# CONT3_DIAGNOSIS — why mark CONT-3 read 106,320 of 106,400 in LM-T4 and LM-T4b

Written 2026-10-20 (laptop, 0 USD) BEFORE any LM-T4c part ran. Owner's order (verbatim, 2026-10-20): "Fix the CONT-3
run-code defect (CREATED vs ATTEMPTED), seal, and rerun LM-T4 on the laptop at 0 USD as LM-T4c."

## 1. What CONT-3 measures

Every crossing of a station carries two words. The **label** (`provenance`) says what really happened to the pointer
the crossing wrote: `FOLLOWED` (the pointer existed before this tick), `CREATED` (written this tick and later admitted
or answered), `ATTEMPTED` (written this tick and refused or still open at the end). The **key** (`provenance_key`) is
what the design expects the label to be, written at the same moment as the crossing. Mark CONT-3 counts the crossings
whose label equals their key (`key_mismatch` = 0 means 100 percent). The frozen threshold is 100 percent. The reader
(`merge_t4b.py`, lines 545-553) reads arm A1 only, both brains of every Task B draw (`provenance` for the taught brain and
`provenance_twin` for the untaught twin) and every dialogue world.

## 2. The exact place

- File: `lm_t4/stations.py` (LM-T4 sha256 `64a2051bc17c200c570d7ea1f5428842a774ccb311d08cf7f9c4e0dc1c8fb8db`, the same
  bytes in LM-T4 and LM-T4b).
- Class and function: `TaskBThinker.s5` (the S5 "RPM link" crossing of a Task B thought), lines 517-522.
- Line 520 (the defect):
  `rec = record(tid, "S5", None, cas5, cce5, gaps5, "ATTEMPTED", self.ds, key="CREATED", note="asking wrote open question pointers")`
- The comment above it (lines 518-519) states the assumption: "the world teaches every support slot in the end (c26: 10 of
  10 filled), so the pointer is expected to be answered = CREATED".

## 3. Why the key is wrong, and only for the twin

`s5` runs the asking faculty (F4) when a thought's recipe is UNDETERMINED at gate G1 with absent support slots: it names
each absent slot once per draw (`asked_slots` keeps the set), writes one question record per slot, and records ONE S5
crossing with label `ATTEMPTED` (open now) and key `CREATED` (expected to be answered later). At the end of the draw
`Thinker.finalize_provenance` (lines 238-257) turns the label into `CREATED` if the question was answered, else leaves
`ATTEMPTED`, and counts `key_mismatch`.

Each Task B draw runs two brains through the same code (`arms.run_task_b_draw`, `arms.py` lines 103-115):

- the **taught** brain (`tag="taught"`): teaching fills the support slots, so every question it asked is answered; label
  `CREATED`, key `CREATED`, 0 mismatches;
- the **untaught twin** (`tag="twin"`, the control that must stay near chance): it scores the `b_chain` panels with a fresh
  brain that is never taught, so its questions are never answered; label `ATTEMPTED`, key `CREATED`, mismatch on every
  asking crossing.

So the key's assumption ("the world teaches every support slot") is true for the taught brain and false for the twin.
The label is right in both brains; only the key is wrong on the twin. The key feeds nothing but `key_mismatch`: it is not in
the content digest, not in the path digest, not in any tap sentence, not in any answer.

## 4. Why exactly 80 (from the data, not guessed)

From LM-T4b's `runs/LM_T4_MSI_P12/RESULTS_T4.json`, unit `TB:A1:0-19`, every one of the 20 draws reads:

- taught brain: `{"FOLLOWED": 4672, "CREATED": 4, "ATTEMPTED": 0, "key_mismatch": 0, "crossings": 4676}`,
  `questions: asked 10, answered 10`;
- twin: `{"FOLLOWED": 220, "CREATED": 0, "ATTEMPTED": 4, "key_mismatch": 4, "crossings": 224}`.

The fixture draw (`tools/twin_asking_detail.py`, output `TWIN_ASKING_DETAIL_OLD_CODE.txt`) shows the same shape and names
the crossings: the twin thinks 32 thoughts (16 `b_chain` worlds, plain panel and shuffled panel), each crossing the 7
stations S0-S6: 32 x 7 = **224 crossings**. The draw's chain uses 4 recipes (k = 0, 1, 2, 3), each with 2 or 3 absent
support slots (10 slots in all: [0,0] [0,1] | [1,2] [1,3] | [2,4] [2,5] [2,6] | [3,2] [3,5] [3,7]). The twin asks a
recipe's slots once, at the first chain thought that needs that recipe (thoughts 1, 5, 9, 13 of the plain panel), so there
are **4 asking crossings per draw, all at station S5**, carrying 10 questions, 0 answered. The taught brain asks the same 10
slots in 4 crossings during teaching (keyed thoughts 1, 9, 18, 28) and all 10 are answered.

Arithmetic: 4 asking crossings per twin per draw x 20 draws = **80** mismatches in arm A1. Per-draw crossings in A1:
4,676 taught + 224 twin = 4,900; x 20 draws = 98,000; plus the 48 dialogue worlds' 8,400 crossings = **106,400**;
106,400 - 80 = **106,320** (99.92 percent). Dialogue asking crossings (`DialogueThinker.s5`, lines 879-889) set their key
by the planted-slot rule and mismatch 0 times.

The same 80 appear in every Task B arm whose config has `faculties: True` and a twin: A1_NOTAP (part P11), A1 (P12),
A1_REPLAY (P13), A1_NOEYE (P14), A2 (P15): 80 each; A3 and A4 (`faculties: False`) ask nothing and mismatch 0 (P14's A4 and
P16's A3 read 0). CONT-3 reads A1 only, so the mark reads 80, not 400. Per part, the crossings CONT-3 reads: P12 98,000
(A1 Task B, 80 mismatches) and P13 + P15 8,400 (A1 dialogues seeds 11, 29, 47; 0 mismatches).

## 5. The fix (the smallest change that makes the twin's asking crossing carry ATTEMPTED)

Line 520 becomes `key="CREATED" if self.tag == "taught" else "ATTEMPTED"` (and the comment above it says why). The taught
brain keeps `CREATED` (its questions are answered); the twin gets `ATTEMPTED` (its questions stay open). Nothing else in
the run code changes; the reader `merge_t4b.py` is unchanged. Diff and test outputs: `CONT3_FIX_DIFF.md`.

## 6. What the fix can and cannot move

- It moves `provenance_key` on 4 twin crossings per draw in the faculties-on Task B arms. `key_mismatch` on the twin goes
  4 -> 0 per draw; CONT-3 should read 106,400 of 106,400.
- It cannot move any answer, any path digest (`path_digest` reads the label, not the key), any tap sentence, any receipt,
  any eye reading, any hard gate or any other mark: the key is read only by `finalize_provenance`'s `key_mismatch` count.
  Any OTHER number that differs from LM-T4b is therefore a finding and is reported as one, never smoothed.
- Mark H6 ("A5 CREATED 0") reads the injection records in `tap_inject.py`, not this key; unchanged.
