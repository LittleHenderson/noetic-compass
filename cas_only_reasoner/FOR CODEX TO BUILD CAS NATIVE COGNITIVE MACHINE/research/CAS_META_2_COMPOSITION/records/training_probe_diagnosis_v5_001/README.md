# The nested-program weakness also appears on training examples

The saved epoch-60 CAS probe matched only 5/16 nested training programs and
bindings: 2/8 at depth two and 3/8 at depth three. It matched 8/8 at depth one.
The generic selector matched 13/16 nested examples: 5/8 and 8/8 respectively.

These are the same 24 fixed training examples, not unseen tasks or a random
estimate of full-training performance. The old training run has an incomplete
audit packet. These records show what its saved predictions contain; they do
not establish independently reproduced neural behavior or native task success.

`run.py` checks the original partial packet and reconstructed training file
against their pinned hashes. It resolves every probe task ID against those
3,072 training examples, recomputes the reported scores using the preserved
scorer, and requires exact equality for all 28 CAS/generic probe files. The
same 24 IDs and eight examples at each depth must occur in every file.
Neural and provider imports are blocked. Input and scoring-source hashes
are rechecked after analysis. No checkpoint is loaded or changed.

Run from `research/CAS_META_2_COMPOSITION`:

```powershell
& C:/Python314/python.exe -B records/training_probe_diagnosis_v5_001/run.py
```

The receipt is exclusive-create. Preserve it; use a separate record directory
for another run. The full curves and file hashes are in `receipt.json`.

## Consequence for the next experiment

Unfamiliar held-out graphs cannot be the sole explanation: the saved CAS
model also fails these familiar nested examples. That does not isolate
optimization, capacity, the decoder or the training objective as the cause.
The probe also falls from 16/24 exact matches at epoch 50 to 13/24 at epochs
55 and 60. More epochs did not give monotonic improvement on this probe.

Before paying for a larger fresh-data campaign, run a bounded, explicitly
training-only fit diagnostic on known examples with both matched selectors.
Measure freely generated complete programs as well as prediction accuracy
at child-call, input and return decisions. A successful fit diagnostic proves
only fit to its known examples; it must not qualify a skill for promotion.
Use the result to select the training correction, then test that correction
on a separately registered fresh curriculum through the accepted runtime.

Keep the full program-synthesis and persistent-learning objective unchanged.
Do not replace it with the diagnostic or with choosing among authored programs.
Do not alter the accepted executor, verifier, permissions or baseline weights.
