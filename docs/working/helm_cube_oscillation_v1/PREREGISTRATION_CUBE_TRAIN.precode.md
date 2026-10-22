# PREREGISTRATION_CUBE_TRAIN — retrain HELM's CTT to propose cube readings for TEACH-2 (pre-code, 2026-10-22 PDT)

Status: DESIGN, WRITTEN BEFORE ANY CODE. Nothing here is a result. Every number below is frozen now; the frozen reader
applies them. This file is hashed (`PREREGISTRATION_CUBE_TRAIN.precode.sha256`); dated amendments are appended below it,
never edited into it. Approval: the owner's choice "train the CTT first", recorded as `CUBE TRAIN at 3 USD` by
A-TEACH2-17 (the owner writes nothing; the operator wrote that record).

## 1. Gate answer (one sentence)

"After retraining on cube readings, do three copies of HELM's CTT, voting unanimously, propose the true (thing, slot,
value, replaces) reading of a teaching line often enough for TEACH-2's cube arm to be exercised, while proposing a
confident wrong reading almost never and inventing no word the person did not type?"

## 2. What is trained (reused, not rebuilt)

- **The model:** the CTT of `HELM_CTT_20261019` (`helm_cas_translator\model.py`, class `CTTModel`): encoder-decoder
  transformer from scratch, shared embedding, sinusoid positions, copy (pointer) head. Main size 9,585,566 parameters
  (width 256, 4 + 4 layers), vocabulary 8,349. Three copies **A4-s1, A4-s2, A4-s3**, plus the **c45-size twin** (A5,
  2,482,718 parameters) as the size check of TEACH-2 pre-code §2. Initialised from the c45 weights of the same arm
  (fine-tuning, not from zero), so the earlier CAS-record skill is kept.
- **The training code:** `ctt_train\train.py` (seeds `seed_of` = sha256("CTT-TRAIN-<name>-<date>") mod 2^63, the date of
  the seal), the write audit of `audit.py` as amended by A-CTT-2 (v3 rule), the serving code `serve.py`.
- **New, built test-first before the seal (0 USD, laptop):** the row builder for this task, and the **CTT adapter**
  (`propose(text) -> Reading | None`) that turns a CTT output into a `helm_cube_osc.Reading`; the adapter refuses any
  output that is not exactly in the target format or that holds a word not in the person's line (that is "no reading").

## 3. The task and its target format

Input: one teaching line, prefixed by the task tag `<CUBE>` (new special token). Target: one line
`<thing> | <slot words, sorted, space-separated> | <value> | <replaces or ->`, or the single token `NONE` when the line
states no fact. Every word of the target must be copyable from the input (the copy head); `NONE` and the separators are
the only non-copied tokens. The old CAS-record task keeps its own tag and its rows (§4.3), so it is not forgotten.

## 4. Training data (all `SYNTHETIC_ONLY`; disjoint from every exam)

1. **SDG cube rows:** TEACH-1's world generator and its two templates (hive yards, bus lines), seeds from a TRAIN band
   taken at the seal (above every band on the spec sheet, and disjoint from TEACH-2's bands, which are taken later
   above this one). Labels come from the **generator's own truth** (the fact it wrote), never from the rule reader, so the
   CTT does not learn to copy the baseline. Kinds as TEACH-2: FACT, FIX (with `replaces`), TRAP (decoys; the label is
   the true value), SMALL (`NONE`). Target **40,000** rows.
2. **The `LLM_WRITTEN` stratum** (A-TEACH2-1 item 7): **1,200** lines written by three model families (the same three
   command-line writers as TEACH-1: Claude, Codex, Gemini, on their subscriptions, 0 USD) from SDG facts of the TRAIN
   band, 400 per family, each keyed by the other two families; a line is used only when both keyers agree with the
   generator's truth. Writers and keyers are AI models; the owner writes nothing.
3. **Kept CAS-record rows:** 20,000 rows drawn without replacement from c45's 227,497 training rows, with their own tag.
4. **Held-out DEV** (never trained on): 2,000 SDG cube rows and 300 `LLM_WRITTEN` lines from a separate DEV band, same
   rules. TEACH-2's worlds and lines are not drawn yet and are drawn later above these bands; the seal checks that no
   TRAIN or DEV world seed or line text can occur in TEACH-2 (disjoint check, as TEACH-1).

## 5. Where and how much

One AWS **g5.xlarge**, us-west-2, the reusable controller (`claude_jobkit`, a transport lease, presigned S3 URLs, no
instance profile), on-demand, the A-CTT-2 write audit at the GPU smoke test. **Hard cap 3 USD**: the job stops itself at
the cap, and the controller terminates the instance. Expected about 2 USD (c45 trained four arms for 1.40 USD). The
spend is written to `AWS_COMBINED_ALLOCATION_CURRENT.json` (113.34 of 200 USD before this job). Cleanup: the instance is
terminated and verified; weights and logs are downloaded and backed up (three sha256 confirmations); the job's S3 prefix
is kept.

## 6. Reading the result (the frozen reader, on DEV only)

For each copy and for the unanimous vote (ACCEPT-2: all three copies give the same reading, and it passes the adapter):
- `VOTE_RIGHT` = unanimous readings equal to the truth (all four fields); `VOTE_WRONG` = unanimous readings that differ
  from the truth (**confident wrong**); `VOTE_NONE` = no unanimous reading; `INVENTED` = any output holding a word not in
  the input (counted before the adapter refuses it).
- Rates over the 1,200 FACT/FIX/TRAP lines of DEV-SDG and, separately, over DEV-LLM's 300 lines.

## 7. Instrument rows (all must hold, else `INCONCLUSIVE`)
- I1 the package zip's sha256 equals the sealed one; I2 the GPU smoke test passed the v3 write audit; I3 all four models
  trained to their frozen step count (below) with no NaN; I4 the weights downloaded match the sha256 printed on the host;
  I5 the disjoint check held; I6 DEV has its frozen sizes; I7 the cost stayed under 3 USD.

Frozen training settings: the c45 settings for each arm, except steps = **6,000** per copy, batch and learning rate as
c45, mixing SDG cube : LLM : CAS-record rows = 6 : 1 : 3 per batch.

## 8. Gates (one false = `TRAIN_NOT_READY`; TEACH-2 waits)
- **G-INVENT:** `INVENTED` = 0 for every copy, on all of DEV (the copy head must hold).
- **G-CONFIDENT-WRONG:** `VOTE_WRONG` ≤ **1 %** of DEV-SDG lines and ≤ **2 %** of DEV-LLM lines, and on TRAP lines ≤ 1 %.
- **G-EXERCISED:** `VOTE_RIGHT` ≥ **40 %** of DEV-SDG FACT/FIX/TRAP lines and ≥ **25 %** of DEV-LLM lines (TEACH-2's I18
  needs about 64 kept cubes from about 288 FACT lines, about 22 %, after the brain side's check and say-back).
- **G-KEEP-OLD:** on c45's own CAS-record validation rows, the main copies lose at most 2 points of exact match against
  c45 (the old skill is kept).

## 9. Status words (frozen order; the first that applies is printed)
1. `INCONCLUSIVE` — any instrument row false.
2. `TRAIN_NOT_READY` — any gate false (TEACH-2 is not sealed with these weights; the reason is reported).
3. `TRAIN_READY` — everything holds: the three copies' and the twin's weights are pinned by sha256 into TEACH-2's
   package (TEACH-2 I16), and TEACH-2 may be sealed.

Labels printed with every word: `SYNTHETIC_ONLY`, `LLM_WRITTEN_STRATUM`, `CTT_RETRAINED_V1`. `TRAIN_READY` is not a claim
about TEACH-2 and licenses nothing: it only lets the exam be sealed with these weights. Never licensed here: that the
CTT reads real people's sentences; any acting on a proposal.

## 10. Forecast (written now)
- G-INVENT holds (the copy head plus the adapter's refusal). G-EXERCISED on DEV-SDG likely holds (generator truth,
  40,000 rows). The honest doubts are **DEV-LLM** (c45 failed its LLM-written pass on confident wrong proposals, 2/5/3
  against a cap of 2) and **TRAP lines**. Words: `TRAIN_READY` about 0.45, `TRAIN_NOT_READY` about 0.4 (most likely on
  G-CONFIDENT-WRONG for DEV-LLM), `INCONCLUSIVE` about 0.15.

## 11. Order of work
1. This file, hashed and committed (now).
2. Row builder and CTT adapter, tests first (laptop, 0 USD).
3. The `LLM_WRITTEN` stratum, by the three writer families, keyed (0 USD).
4. Package, disjoint check, seal; seeds by the house rule from the recorded approval `CUBE TRAIN at 3 USD` and the sealed
   zip's sha256.
5. GPU smoke test, then training, on AWS (cap 3 USD).
6. The frozen reader reads DEV; record; spec sheet; if `TRAIN_READY`, pin the weights into TEACH-2.
