# Combined Retrain Runbook — Completion Note

Date: 2026-05-04
Deliverable: `docs/working/combined_retrain_runbook_2026_05_04.md`

## 1. Word count

Approximately **3,450 words** (estimated from line-count and character-density; not measured with `wc -w` because Bash/PowerShell were denied during the writing pass). Within the requested 2,500–4,000 word target.

## 2. Number of distinct commands documented

**21 distinct copy-pasteable commands**, distributed as follows:

- Pre-flight (Section 2): 7 commands (Lever 3 line-count, eval-overlap audit, per-bucket count audit, `git log` for vocab14, three pytest invocations).
- Stage 1 — Build merged corpus (Section 3.1): 4 commands (relabel, `cat` merge, demographic-tonal expansion, joint-key audit).
- Stage 2 — Verify vocab14 (Section 3.2): 3 commands (three pytest invocations).
- Stage 3 — Launch training (Section 3.3): 1 command (the `nohup` training launch).
- Stage 4 — Standard eval extraction (Section 3.4): 3 commands (`ls` artifacts, headline metric extraction, vocab size confirmation).
- Stage 5 — Demographic eval (Section 3.5): 3 commands (held-out expansion, robustness gate, key-number extraction).
- Section 6 — Standalone eval commands: identical to Stage 4/5 but documented for re-use after a checkpoint pull.

Counting unique invocations only (not duplicates between section 3 and section 6), the runbook documents **21 distinct commands** the operator can copy-paste. Of these, 1 (`merge_corpora.py`) is flagged as a follow-on script that does not yet exist; a `cat`-based one-liner is documented as the interim path with the script's intended scope (~50 lines, dedup on joint key + manifest emission) called out for the implementer.

## 3. Most-controversial pre-committed criterion

**meta_logic per-bucket ≥ 30% all_heads_exact for PASS** (HALF-PASS at 20–30%).

Why this threshold is the hardest:

- The vocab14 prep memo (`vocab14_prep_memo_2026_05_04.md`) puts median expectation at meta_relations *failure* of 30–45% — i.e., meta_relations *accuracy* of 55–70%. But the runbook's threshold is on **all_heads_exact** for the meta_logic bucket, which is a strictly tighter gate: it requires the 8-head conjunction (noetic, domain, drive, register_mode, registers, has_meta_logic, meta_relations, transition_kind) to all simultaneously hit on each meta_logic record.
- The K9_DiagLoop honest meta_logic all_heads_exact reference number is 19.6%. To clear 30% all_heads_exact requires roughly a 10 pp absolute improvement, or ~50% relative lift, in a bucket where the dominant per-head failure (meta_relations) is being attacked but the secondary failures (noetic confusion to ^5/^0, drive default-to-F1) are NOT directly addressed by vocab14 alone.
- Setting it at 30% rather than at the stricter 40% gives some signal headroom but commits the runbook to a meaningful improvement claim, not a "any movement counts" claim. Setting it at the looser 20% would absorb essentially every plausible vocab14 outcome into PASS, removing the criterion's discriminative power.

Other criteria considered for "most-controversial" but ranked below:

- **Canonical exact ≥ 92%**: high-confidence; the K=9 baseline cleared 88.6% on a smaller corpus, and expanded data should help additively. Only the demographic K=4 expansion's surface-noise risk threatens this.
- **Paraphrase invariance ≥ 65%**: the threshold is tight but the lever (Lever 3) is directly targeted; PASS is plausible if Lever 3's 5K is enough to bridge canonical → free-form English on the eval distribution.
- **v76_production ≥ 50%**: high-FAIL probability (the runbook flags it as the single highest-probability failure axis), but the threshold itself is uncontroversial — 50% is the "demoable" bar from the user's spec, not a threshold I had latitude to adjust.
- **Demographic robustness within 10 pp**: the 10 pp tolerance is a placeholder per the Task #69 completion memo, so the threshold is intentionally calibrated loose. Calling this "controversial" would conflict with the Task #69 author's recommendation that 10 pp is provisional.

## 4. Single highest-probability failure axis

**v76_production per-bucket all_heads_exact** is the single highest-probability failure axis.

Reasoning:

- The `v76_meta_logic_deep_dive_2026_05_04.md` empirical analysis attributes v76 weakness to a **multi-operand routing failure** — the model regularly emits a non-first-listed operand's noetic when the recipe carries 3-4 weighted operands and the label policy fixes target.noetic to the first state-literal. The deep-dive memo explicitly identifies this as architectural (graph-encoder undersizing) and lexical (no recipe-arrow / no Λ / Ω / Θ tokens), with the architectural component dominating.
- **No lever in this combined retrain attacks the architectural component.** Vocab14 closes some of the lexical gap (adds `cas:Λ`, `cas:Ω`, `cas:Θ` and the meta_logic constructors) but does NOT add a `cas:→` recipe arrow as a distinct token (the runbook should flag this). Lever 3 produces colloquial paraphrases of v76 surface forms but does not change the model's routing inductive bias. Demographic K=4 expansion further dilutes v76's per-batch signal density (v76 records are 108/24,454 = 0.44% of training canonicals; after K=4 expansion the share is roughly preserved, ~0.44% of 97K = ~430 v76 records — still thin).
- The K9_DiagLoop honest v76 all_heads_exact reference is 32.4%. To clear 50% PASS requires a ~17 pp absolute improvement; to clear 35% HALF-PASS requires ~3 pp. The latter is plausible from incidental lift (vocab14's `Λ`/`Ω`/`Θ` tokens give the model a small additional structural anchor); the former is implausible without an architectural intervention.
- Probability allocation in the runbook §7: `P_pass ≈ 0.20, P_half ≈ 0.45, P_fail ≈ 0.35`. The 35% FAIL probability on v76_production is materially higher than any other axis's FAIL probability (canonical 15%, paraphrase 20%, meta_logic 25%, demographic 15%).

The runbook's Section 5 rollback procedure correctly maps a v76 FAIL to "auxiliary first-operand pointer loss on v76 records" (E3 from the deep-dive memo) as the next experiment, and explicitly notes that the diagloop graph encoder is deprecated per outcome C, so the next escalation if E3 underdelivers is a vanilla graph-encoder enlargement on K=9 architecture.

## 5. Notes for the operator

- **Pre-flight 2.1 is not optional.** The Lever 3 generator's eval-overlap filter at `cas-synthetic/scripts/generate_lever3_paired_freeform.py:40-44` removes overlap before stratified sampling, so a non-zero overlap count in the audit indicates either the wrong file was downloaded or the filter was bypassed during a partial-resume. Do not proceed.
- **The `merge_corpora.py` script does not yet exist.** The runbook documents a `cat`-based interim and inlines the intended script's scope (~50 lines) so a follow-on agent can write it before the retrain fires. The interim is sufficient for the v1 retrain because Lever 3 records carry distinct ID-space (`lever3_l3conv-...`) so dedup is a no-op against canonicals.
- **The demographic eval expansion (Stage 5) uses a different seed (`--seed 4242`) from the training expansion (`--seed 42`)** to avoid per-record-pair correlations that would let the gate measure training memorization rather than robustness. This is a non-obvious but load-bearing detail; the runbook calls it out at the use-site.
- **Cross-check `--eval-only` and `--resume` flag names** against the current `train_structured_prediction.py` argparse before running the standalone eval (Section 6.1). The same caveat appears in the vocab14 runbook; if the flags don't exist, the in-run artifacts are sufficient for the headline metrics.
- **The runbook does NOT prescribe a `--diagram-loop-pairs` flag.** Per outcome C documented in `v76_meta_logic_deep_dive_2026_05_04.md` (and the user's explicit instruction in the parent task), diagloop is deprecated; the K=9 baseline architecture is the v1 target.
