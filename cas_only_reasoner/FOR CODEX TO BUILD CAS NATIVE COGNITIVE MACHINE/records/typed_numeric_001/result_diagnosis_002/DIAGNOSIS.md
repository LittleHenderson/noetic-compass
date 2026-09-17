# Recorded answer patterns — completed run 002

The completed training run changed the answers, but context, definition, and edge-account exact-answer scores stayed at **0/70**. Analogy fell from **12/70 to 10/70**: all 12 earlier successes were lost, and 10 different cases became correct. These are already-exposed training cases.

Observed patterns in the saved final outputs:

- **Definition:** all 70 function references point to a different world than the emitted whole. Only six kind references share the whole's world; no answer has both declarations in that world. Of the 140 declaration selections, 83 select the same public alias, `W36`.
- **Context:** 13 answers contain no participants. In 51 of the other 57 answers, the setting reference points outside the emitted participants' world. The setting selects `W36` in 39/70 cases. More participants were emitted after training (90 total versus 10), without an exact-answer success.
- **Edge account:** emitted edges increased from 69 to 264 across the 70 answers. The final outputs include 65 self-edges in 41 answers, versus 20 self-edges in 17 answers initially. More emitted relations did not yield a completely correct edge list.
- **Analogy:** all 70 selected answers changed. Final selections use only six worlds: `W36` in 42 cases and `W21` in 14. Initial outputs used 15 worlds plus `NO_MATCH`; final outputs never select `NO_MATCH`. Seven of the 12 lost cases now select `W36`. The 10 gains select either `W36` (six) or `W21` (four).

These counts show concentrated world choices and inconsistent reference combinations. Weak linking between a question's world and its declaration choices is a possible explanation. Interference across training is another possibility for the analogy turnover. **Neither cause is established:** this inspection cannot distinguish encoding, core capacity, frozen readout, optimization, or curriculum effects, nor identify which updates caused a change.

Correctness was read from the retained scoring receipts. The reference comparisons above are consistency checks between emitted fields, not newly computed partial-credit scores. No checker, model, checkpoint decoder, provider, or new experiment was run. This is not held-out transfer evidence or a matched learning-advantage claim.

Job: `cas-meta2-typedcourse-20260917024221-2a221243`  
Source: `2a221243bf2f82f82bdce19514fe04bcb6b26bb0`

`diagnosis.json` retains counts, example record IDs, and hashes of the seven input files. `diagnose.py` reproduces the JSON from those files using only the Python standard library. The script writes a new `diagnosis.json` and refuses to overwrite an existing one. Input bytes were unchanged during inspection; `receipt.json` binds this diagnosis's artifacts.
