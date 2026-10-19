# Plan: score the existing small English model (Scribe L4) on the sealed 98

**Status: `NOT_RUN` — waiting for the owner's word.** Nothing in this folder has loaded the model. No torch was
imported on the laptop. The sealed 98 were not opened by this plan.

Owner order behind it (2026-10-18, `C:/Users/wakil/Documents/Codex/2026-10-18/OWNER_APPROVALS_20261018.md`,
approval 2 "no more GPU for now" and fix E): the existing small English model must be scored on the sealed 98
behind a working round-trip check before any new rented-GPU training.

## 1. What the model is (read from the commit, not from prose)

Source: branch `helm/creativity-rpa-valve-v1`, commit `84812689b6fb6de4250dc9bf2e400df88a95944c`
("HELM v0.5 'Scribe' (Trained on AWS GPU)").

| Thing | Path in the commit | sha256 |
|---|---|---|
| weights (326,230 bytes) | `HELM_DISTRIBUTION_PACKAGE/scribe_l4_aws_gpu_training/outputs/scribe_l4_weights.pt` | `e36cf3cb50fe8ae168b2986a97000a47e7632b058b34b44629f4f17f99af9dc1` |
| vocabulary (108 words) | `.../outputs/scribe_vocab.json` | `6746e5dbd77dc6ddaa7bd7270b21ca2558c4da2e439522a2fbcffc66ce4dbc1a` |
| model code | `scribe_l4_aws_gpu_training/scribe_model.py` | (hash it when extracted) |
| its own round-trip shim | `scribe_l4_aws_gpu_training/cce_shim.py` | (hash it when extracted) |
| run summary | `.../outputs/RUN_SUMMARY.json` | `e50df338ad0cff8c7d814670522e954ff710e0a1ac286287fbc2e4c7120e43dc` |

The hashes in the table are the ones the commit's own `OUTPUTS_SHA256.json` records.

**Shape.** A small transformer encoder trained from scratch: word embedding (108 words) + learned positions,
2 layers, width 64, 4 attention heads, feed-forward 128, input cut at 32 tokens, mean pooling, then 7 separate
pick-one heads. It answers with ONE clause: `turn_type` (ANSWER / CLARIFY), `subject` (Mind, Positive, Negative,
Male, Female), `verb` (intakes, processes, stores, outputs), `object` (Idea, Vibration, Rhythm, Above/Cause,
Below/Effect), `domain`, `register`, `drive`. It has **no coefficients and no recipe**.

**What it was scored on before.** Only its own synthetic sentences (`RUN_SUMMARY.json`: 800 synthetic
validation rows, exact match 90.0 %, its shim round trip 64.0 %, CLARIFY 100.0 %, `claim_status`
`SYNTHETIC_ONLY`, ceiling `ENGINEERED-NOT-VALIDATED`).

## 2. Problems found by reading the code (before any run)

1. **The gold cannot be matched by construction.** Every sealed row's gold is a recipe: two or three weighted
   states plus a named outcome (and sometimes a side product). The Scribe can only say one unweighted clause.
   Exact match against gold is therefore **expected to be 0 of 98**. This is written down now so the result
   cannot be re-read later as a surprise.
2. **Its vocabulary cannot read the sealed English.** The 108 words come from its own template sentences
   (they include "sandwich", "electron", "tuesday"). Words such as "combine", "foundational", "struck",
   "chord", "practice", "attention" are not in it; they all become `<UNK>`. Measured on the 99 DEV rows (not the
   sealed ones): 1,478 of 4,660 input words are in its vocabulary (mostly "the", "of", "in" and the four domain
   words). The script counts the same thing on the sealed 98 (count only).
3. **Its input is cut at 32 tokens** (start + 30 words + end). On the 99 DEV rows, 93 are longer than 30 words
   (shortest 24); the rest of each is never seen. The script counts the cut rows on the sealed 98.
4. **Its own round-trip check is weak.** In `cce_shim.py` the parser fills missing slots with defaults
   (`.get(..., "C")`, `"A"`, `"F2"`), and its pattern `(\w+)` cannot read the objects `Above/Cause` and
   `Below/Effect`, so those always fail; that is most of why its synthetic round trip is 64.0 %. The training
   script also counted every CLARIFY as a round-trip success.
5. **So the honest headline is a danger count, not an accuracy.** The script counts
   `answered_round_trip_ok_but_not_gold`: the model answered with confidence, the answer survives the
   round trip, and it is still not the gold. That is exactly the case a round-trip check alone cannot catch.

## 3. What the script scores — only these two checks

`score_scribe_l4.py` (this folder):

1. **Round trip** `parse(render(Ĉ)) == Ĉ`, twice:
   - (a) the Scribe's own shim (`cce_shim.verify_round_trip`), reported for comparison only;
   - (b) the real `docs/working/noetic_council/language_v3/cce.py` (`cce.round_trip`), through one declared
     adapter `scribe_to_cce`: subject `Mind` becomes the real CCE `^1` act frame
     `Mind intakes/processes/stores/outputs "<object>"` with the model's own domain, register and drive and
     the declaration `Mind is a Mind`; any other subject has **no CCE frame** and is counted as a failure
     (`NO_CCE_FRAME`), never patched. Checked on the laptop with stdlib only (no torch, no sealed row):
     all 4 verbs × 5 objects round-trip `ok` (`test_score_scribe_l4_adapter.py`, 6/6 tests).
2. **Exact match** `cce.normalize(scribe_to_cce(Ĉ)) == cce.normalize(gold)`, gold = the row's own bridge-v2
   parse turned into CCE content by `language_v3/scoring.content_from_parse`.

CLARIFY is reported as its own count; it is a refusal, not a pass.

The script refuses to start unless: the approval file contains the line `APPROVE SCORE_SCRIBE_L4_SEALED_98`;
the weights, vocabulary and sealed file hashes match the table above; and its output file does not exist yet
(the sealed 98 are scored once). It writes counts and hashes only — no sentence, seed id or per-row prediction.
It checks the sealed file's sha256 `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`
before and after.

## 4. Where it runs, and what it costs

- **Needs torch.** CPU is enough: inference only, 98 sentences, a 326 KB model.
- **Not on the laptop** (about 300 MB free RAM; owner order 2026-09-23). Not on a GPU (owner order
  2026-10-18 "no more GPU for now"; a GPU adds nothing here).
- **Host:** one AWS `t3.medium` (2 vCPU, 4 GiB), `us-west-2`, on-demand, Amazon Linux 2023 or Ubuntu 24.04,
  CPU-only torch wheel (`pip install torch --index-url https://download.pytorch.org/whl/cpu`).
- **Time:** the scoring itself takes seconds (98 forward passes of a 2-layer, width-64 encoder). Instance
  life is dominated by the torch install: about 5–10 minutes in total.
- **Cost:** t3.medium on-demand is about 0.0416 USD per hour in `us-west-2` (check the price page on the day),
  so about **0.01 USD** for one run including setup. **Proposed hard cap: 0.10 USD and 30 minutes**, after
  which the instance is terminated whatever happened.
- **Record (per CLAUDE.md):** source = this folder at the PR commit + commit `84812689`; purpose = this plan;
  instance id; start/stop times; cost; cleanup = instance terminated and its volume deleted, checked by a
  second `describe-instances` / `describe-volumes` call.

## 5. Steps (for the operator, after the owner's word)

1. Write the approval file with the owner's exact words and the line `APPROVE SCORE_SCRIBE_L4_SEALED_98`.
2. Extract the four Scribe files from commit `84812689`
   (`git show 84812689:<path> > <file>` for the weights, vocabulary, `scribe_model.py`, `cce_shim.py`);
   check the two output hashes above.
3. Copy to the instance: those four files, this folder, `docs/working/noetic_council/language_v3/`,
   the `sdg_bridge_v2` folder and the `lacunarity_machine_v1` folder (both read-only imports of
   `scoring.py` / `aliaswide.py`), and the sealed file.
4. Run:

   ```
   python3 -X utf8 -B score_scribe_l4.py --weights scribe_l4_weights.pt --vocab scribe_vocab.json \
     --scribe-src ./scribe_src --lang-v3 ./language_v3 --bridge ./bridge_root --sealed real_heldout_unparseables_98.jsonl \
     --approval OWNER_APPROVAL_SCORE_SCRIBE_L4.md --out SCRIBE_L4_SEALED_98_RECEIPT.json
   ```

   (`--bridge` must hold the folder `sdg_bridge_v2`; add the `lacunarity_machine_v1` folder to `PYTHONPATH`.)
5. Download the receipt, terminate the instance, verify cleanup, then record the counts in the spec sheet.

## 6. Predicted result, written before any run

- exact match against gold: **0 of 98** (structural, item 1 above);
- real-cce round trip passes only on ANSWER rows whose subject is `Mind`;
- CLARIFY rate: unknown — this is the one number worth having. A high CLARIFY rate means the model mostly
  refuses unreadable English (good); a high `answered_round_trip_ok_but_not_gold` means the round-trip
  interlock lets confident wrong answers through (bad).

Whatever the counts, the claim ceiling stays `ENGINEERED-NOT-VALIDATED`; no real-English reading claim can come
from a model whose output space cannot hold the answer.
