# Paper A v2 §5.7 Draft — Completion Note

**Date.** 2026-05-04.
**Agent task.** Draft §5.7 (diagloop / tri-channel architecture section) using the smoke v2 honest result as the empirical anchor, with explicit placeholders for K9_DiagLoop full v3 numbers landing tonight. Read-only on existing files; only writes are the new draft, the v3 sub-section template, and this completion note.

---

## 1. Word counts

| File | Word count |
|---|---:|
| `docs/paper_a_v2_section_5_7_diagloop_draft_2026_05_04.md` (full §5.7 draft) | **3,099 words** |
| `docs/paper_a_v2_section_5_7_v3_results_template.md` (§5.7.5 fill-in template) | **1,284 words** |

The full draft is approximately 600 words above the 2,500-word target ceiling. The overshoot is concentrated in §5.7.4 (smoke results table commentary) and §5.7.5 (three pre-committed interpretation cases written as full prose rather than schematic). Trimming to ≤2,500 is achievable by collapsing the per-head and per-bucket commentary into single paragraphs and abbreviating the Case A / B / C interpretation prose, but the trade-off is that the template-driven fill-in step at §5.7.5 becomes harder to execute mechanically. Recommend keeping the present length unless §5.7 specifically must hit a hard 2,500-word ceiling for the venue.

The v3 template at 1,284 words is sized for fill-in mechanics rather than narrative density: the bulk of its tokens are the smoke-vs-full comparison tables and the three Case-prose blocks that carry placeholders for the case-specific extension sentences.

---

## 2. Citations / file references

The draft cites the following implementation files and artifacts. All paths are repo-relative; cite-level precision is "file" rather than "function/line" because the full §5.7 narrative does not require deeper specificity.

**Code files referenced.**
- `cas-native/model/graph_encoder.py` — GAT graph encoder (NODE_FEATURE_DIM=49, EDGE_FEATURE_DIM=34, hidden_dim=64, two layers)
- `cas-native/model/graph_text_fusion.py` — cross-attention fusion between text-encoder and graph-encoder hidden states
- `cas-native/training/diagram_serialization.py` — K=3 diagram-loop training augmentation
- `cas-native/training/evaluate_diagram_loop_honest.py` — PR #19 honest two-pass eval protocol
- `cas-native/training/evaluate_diagram_loop_invariance.py` — original (oracle-leaky) reference, deprecated
- `cas-native/training/train_structured_prediction.py` — `--limit` default trap, requires `--limit 100000` for full runs
- `cas-native/training/runs/K9_DiagLoop_full_v2_honest/manifest.json` — manifest format for the full-scale run
- `cas-native/training/runs/K9_DiagLoop_full_v3_2026_05_04/manifest.json` — target manifest path for the v3 run (does not exist yet)

**Eval datasets referenced.**
- `level3_recoverable_eval_1000_v77_relabeled.jsonl` — held-out 1K evaluation labels (post-relabel, the correct file per memory note on eval-file-slip)

**Run identifiers / commits referenced.**
- K=9 baseline checkpoint commit `3232f05`
- Smoke v2 run: K=8 paraphrase + K=3 diagram-loop, 5K canonical, 5 epochs
- Full v3 run: 16,570 canonical, 20 epochs, ~31,080 steps, PID 10441 on pod 104.255.9.187, started 2026-05-04 18:19 UTC

**PRs referenced.**
- PR #19 — honest two-pass eval protocol with monkeypatch oracle-leak invariant
- PR #6 / branch `proposal/diagram-loop-impl` (referenced obliquely as the architectural-realization origin; not cited by name in the draft, only by file paths)

**Concepts referenced from upstream paper sections.**
- §5.5 — K=9 bare-slot retrain (registers head as strongest gainer)
- §5.6 — self-conditioning small-scale smoke null result (linear `[PRIOR]` block insufficient for drive recovery)
- §5.7.3 → §5.7.4 → §5.7.5 → §5.7.6 → §5.7.7 internal cross-references

**Concepts referenced from CAS framework.**
- CAS v7.7 ontology (10 Noetics, 4 Domains, 7 Drives, 4 Registers)
- 12 prediction heads of the structured-token CAS-Native model
- Compiler-emitted typed graph (NoeticCluster, RelationCluster, IntegrationEdge)
- Recipe semantics (CAS v7.6) for `v76_production` bucket
- Cluster expressions for `meta_logic` bucket

The draft uses authoritative Noetic terminology where Noetic concepts are mentioned (e.g., "axis identity," "registers identity," "10 Noetics") and does not paraphrase or rename canonical operators.

---

## 3. Headline empirical claim from §5.7.4 (smoke v2 sub-section)

**Headline claim.** On the K9_DiagLoop smoke v2 honest evaluation (5K canonical records, K=8 paraphrase + K=3 diagram-loop, 5 epochs, two-pass protocol with no oracle leak), the tri-channel architecture delivers a **+18.8 pp paraphrase invariance lift** (paraphrase-with-self-prior 45.4% vs paraphrase-text-only 26.6%) AND simultaneously achieves a **registers per-head consistency of 98.6% under self-prior** — the strongest single-head result observed across any CAS-Native experiment to date. The architecture matches the K=9 notation-only baseline at the same training scale on canonical text-only paraphrase recovery (45.4% vs 46.9%, within statistical noise) while lifting paraphrase invariance through the graph channel, which is the smoke-scale evidence that the graph channel is non-redundant rather than capacity-competing.

**Per-head ordering.** registers (98.6%) > noetic (85.1%) > domain (81.0%) > drive (71.6%). The asymmetry is the empirical foundation for the per-head channel routing hypothesis discussed in §5.7.7.

**Per-bucket flag.** `v76_production` (24.4%) and `meta_logic` (7.5%) are architectural canaries at smoke scale, suggesting the graph encoder hidden_dim=64 is undersized for high-arity recipe and cluster expressions. Whether the canary persists or recovers at full scale is one of the load-bearing questions that the v3 result will answer.

---

## 4. Honest assessment — paper-quality at <50% paraphrase-with-self-prior?

The instruction is: "if v3 lands at <50% paraphrase_with_self_prior, can this section still be a paper-quality result? (be brutal)"

**Answer: yes, but only as a different paper.**

The draft as written treats the full-scale result as the headline empirical claim (§5.7.5). If v3 lands at <50% paraphrase-with-self-prior, three things are true simultaneously:

1. **The smoke-vs-full divergence is itself a publishable methodological finding.** The pattern "smoke positive at +18.8 pp lift, full collapse to <50% paraphrase-with-self-prior" is a cleanly diagnosable case of either capacity-stealing (the 64-dim shared bottleneck cannot host both feature paths under full-data training pressure) or signal-shift (the K=3 diagram-loop augmentation ratio that worked at 5K records dilutes or competes with paraphrase signal at 16.5K records). Publishing this as a negative result with the diagnosis is publishable methodology — it is the same kind of result the existing v2 outline is already framed around (the agent-pv2 worktree's existing §5.7 already reports the K9_DiagLoop full v2 honest retrain as a publishable negative result with capacity-stealing as the load-bearing mechanism). The Case C path in §5.7.5 is pre-committed to this framing.

2. **The tri-channel benchmark methodology in §4 is unaffected.** Cross-channel consistency rate, the headline contribution of Paper A v2, is a benchmark-level diagnostic metric whose value does not depend on whether any particular tri-channel-trained model outperforms the baseline. Paper A is a benchmark-and-methodology paper, not an architecture paper; the diagloop result is empirical motivation for the methodology, not the methodology itself.

3. **The smoke v2 result loses its stand-alone value.** This is the brutal part. If full v3 lands at <50%, the smoke v2 result becomes evidence of a small-scale artifact rather than evidence of a real lever. The +18.8 pp smoke-scale lift remains real as a measurement, but it cannot be cited as evidence that the graph channel adds non-redundant signal in production-scale training. The §5.7.4 sub-section as currently written would need to be rewritten to frame smoke v2 as part of the lever-exploration narrative ("this is the lift we saw at smoke and it did not hold") rather than as the empirical anchor of the tri-channel claim ("this is the lift the architecture delivers"). The headline empirical claim shifts from §5.7.4 to §5.7.5, and §5.7.5 becomes a Case-C negative-result section.

**What would not survive Case C.**
- Any paragraph that frames smoke v2 as architectural evidence (rather than as a development milestone).
- The implicit case for the diagloop architecture as a production candidate.
- The per-head channel routing follow-on as an obvious next experiment (it remains a candidate, but it is no longer "obvious" — it is one of several).

**What would survive Case C.**
- The tri-channel benchmark methodology in §4.
- The honest two-pass eval protocol in §5.7.3 and the methodology lessons in §5.7.6.
- The cross-paper relevance of the two-pass eval protocol in §5.7.7.
- The capacity-stealing diagnosis as a publishable mechanism for the divergence.
- The K=9 notation-only baseline as the deployment recommendation.

**Net assessment.** The §5.7 draft as written is robust to Case C in its essential structure: the eval methodology, methodology lessons, and discussion sections all hold. The §5.7.4 sub-section needs reframing as smoke→full-scale-artifact rather than smoke-as-anchor. The §5.7.5 sub-section is already pre-committed to a Case-C negative-result interpretation via the §5.7.5 Case C prose block. The honest answer is that Case C reduces the section from "headline empirical contribution + methodology" to "methodology + publishable negative result" — still paper-quality, but at a lower contribution tier than Case A or B.

The paper would not collapse under Case C. The section would.

---

## 5. Files written

- `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\paper_a_v2_section_5_7_diagloop_draft_2026_05_04.md` — full §5.7 draft (3,099 words)
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\paper_a_v2_section_5_7_v3_results_template.md` — §5.7.5 fill-in template (1,284 words)
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\paper_a_v2_section_5_7_completion_2026_05_04.md` — this file

No existing paper files were modified. No worktree state was changed.
