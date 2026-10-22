# Sign request: HELM-R1 wave 4 (the EYE_SCAN wave)

**Why.** U3-T1 showed that HELM's Unity Eye can look itself over and find planted faults, and that its whisper
reaches a stand-in of the brain. This wave puts that self-check on the REAL brain (the same one as wave 3b) as one
switch, EYE_SCAN, and tests it against an exam nobody on the build side has seen.

**What runs.** The same brain and switches as wave 3b, plus EYE_SCAN. Three new exams made from your sign line by a
separate custodian: English-64, Faces-64, and the self-check exam (152 copies of a conversation; in 88 of them a saved
record is secretly tampered with, a sealed brain file changes, or the store drifts; 64 are clean). Also the older
exams (Gate B, Task B, the checked-form skin, cascade, idle) on used data, to show the switch costs nothing there.
80 small units on one machine.

**What is new.** When the Eye finds a fault, it whispers. The whisper now goes to the brain's real reply path. If the
next answer uses the broken record, HELM holds that answer back and says why, in plain words. It writes nothing.

**Cost.** One small AWS machine (m6i.xlarge), about 15-25 minutes, about $0.05-0.12. Worst case about $0.70 with the
one retry. Cap $1.00. No GPU.

**A PASS with EYE_SCAN_EARNED_KEEP would mean.** On synthetic worlds only: the Eye found every planted fault, the
next answer held back every answer that used the broken record, no wave-3b exam lost more than 2 items, no false
alarm, nothing written, and every sentence it said points to a record.

**It would not mean.** That HELM knows itself in any general sense; that it finds faults nobody planted; that the
hold-back rule is right for real use; anything about real kitchens or real data. Depth is not in this wave.

**Sign line (copy exactly):**

```
APPROVE R1W4: EYE_SCAN wave, sealed package 4bd0d740, one attempt + one plumbing retry, cap $1.00.
```
