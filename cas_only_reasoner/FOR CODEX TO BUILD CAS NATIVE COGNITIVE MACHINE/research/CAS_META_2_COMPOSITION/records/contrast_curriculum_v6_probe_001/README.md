# Prototype practice for input binding and child selection

This is runnable pure construction and cold verification, not training or the
next registered experiment. It leaves the model, accepted executor, and earlier
experiment source unchanged.

The prototype contains 128 matched pairs / 256 tasks. There are 32 pairs for
each combination of depth 2 or 3 and input-binding or child-selection contrast.
Every program has four reachable procedures. Both members of a pair keep the
same observations, initial observation binding, procedure names, presentation
order, and sentence-template combination. Exactly one target field changes.
The public wording reflects that change, and the independent parser reconstructs
the corresponding target. The symbolic required RUN dependencies or selected
result also change; these are not meaningless renamings.

Construction excluded 7,704 previously known graph signatures. The 256 new
prototype signatures are listed in receipt.json and must be excluded from future
held-out tests. Both members of a pair must stay in the same data partition.
The prototype does not yet supply a full curriculum, validation split, held-out
native execution, or a new measured learning result.

Checks completed:

- 128 pairs reloaded and verified in a separate process using verify.py.
- All 256 public problems independently parse to their targets.
- One changed target field per pair; every pair changes required symbolic work.
- No graph duplicates; observations shared only inside their own pair.
- 1,024-token public-input and 256-token action limits pass.
- Four invalid/identical-pair controls rejected during construction.
- Neural and provider imports blocked; no local tensors or AWS calls.

Tasks SHA-256: `ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46`.

From CAS_META_2_COMPOSITION:

```powershell
C:/Python314/python.exe -B records/contrast_curriculum_v6_probe_001/build.py
C:/Python314/python.exe -B records/contrast_curriculum_v6_probe_001/verify.py
```

Outputs use new/exclusive records. For reproduction, run from a pristine source
copy with these output files absent; do not delete or overwrite the retained
evidence. A later reusable generator needs explicit output/seed arguments and
source-bound partition rules before cloud launch.

Why this direction: the stored execution comparison found concrete input and
child-call differences, while the fit diagnostic showed the existing model can
learn a small set of nested programs. Contrastive practice is a testable next
hypothesis, not proof that it will fix generalization. Future measurement must
compare matched models through the unchanged native task verifier and keep the
earlier CAS 0/72 outcome intact.
