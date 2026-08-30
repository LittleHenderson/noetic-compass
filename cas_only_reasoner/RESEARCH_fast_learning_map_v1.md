# FAST-LEARNING ARCHITECTURE MAP v1

Filed 2026-08-29. Combines two independent passes:
- a web literature survey (fan-out search + 3-vote adversarial
  verification; 24 confirmed claims, primary sources cited);
- a path-cited inventory of the local tksCAS tree.

Rule of this document: **PUBLISHED-WITH-EVIDENCE and SPECULATION are
kept strictly separate.** Anything about the CAS/simplex/verifier
combination is a HYPOTHESIS, not a result, and is marked so. This
document may not be used to re-inflate any capability claim
(see `CORRECTION_RECORD_v1.md` §8).

---

## PART 1 — WHAT THE PUBLISHED EVIDENCE SAYS (verified, cited)

"Fast learning" is three different things that hype conflates. Only
the third is genuine data efficiency.

### Kind 1 — Inference speed (State-Space Models: Mamba, S4, RWKV)
- Real and large: Mamba ~5x generation throughput (1.69–3.66x in
  practice), S4 ~60x, RWKV linear-in-length. Mamba-3B matches a
  Transformer ~2x its size.
- **This is deployment cost, NOT training time or data need.** Every
  headline comparison is at MATCHED training data. `2312.00752`,
  `2111.00396`, `2305.13048`.
- Documented failure modes absent in Transformers: (1) fixed-size
  state bottlenecks associative recall — a 70M attention model beats
  a 1.4B gated-conv model at multi-query recall (`2402.01032`,
  Zoology ICLR 2024); (2) optimization instability on synthetic
  recall tasks, but only 2-1 vote, synthetic-only, and DeltaNet is
  the counterexample (`2508.19029`).
- **Bottom line: SSMs do NOT give sample efficiency or faster
  training. They are not what "learns fast" needs.**

### Kind 2 — Few-shot adaptation (MAML / meta-learning)
- "Fast" = a few gradient steps to adapt an ALREADY-trained model to
  a new task. Meta-training itself is a full, often COSTLIER run
  (second-order gradients). `1703.03400`.
- Ablations show the "rapid learning" is largely illusory: ANIL
  (no inner loop) matches MAML; deeper backbones erase method
  differences; a plain fine-tuned baseline is competitive or better.
  `1909.09157`, `1904.04232`.
- **Bottom line: not "learn from scratch in hours." It is
  sample-efficient FINE-TUNING of an expensive pretrained model.**

### Kind 3 — Genuine one-shot sample efficiency (Bayesian Program
Learning) — THE ONE REAL RESULT
- BPL matches human one-shot Omniglot accuracy: **3.3% error vs 4.5%
  human**, beats Siamese ConvNet (8.0%) and ConvNet (13.5%). Lake,
  Salakhutdinov & Tenenbaum, Science 2015; `1902.03477`.
- Robust under scarce data: cut pretraining to 5 alphabets and BPL
  stays ~4%, while a ConvNet collapses to ~24% and meta-learners to
  ~30%.
- **The catch, load-bearing:** it buys this with strong HAND-BUILT
  compositional/causal priors (stroke model, ~964 background
  characters), in a NARROW symbolic domain. Not tabula-rasa, not a
  general learner.
- **Bottom line: the only evidenced order-of-magnitude sample
  efficiency comes from HARD STRUCTURE in a CONSTRAINED domain.**

### Other real, bounded tools
- Gaussian processes: genuinely sample-efficient for low-data
  optimization + calibrated uncertainty, but O(n^3) and weak in high
  dimensions. `2212.04450`.
- Delta-rule fast weights: linear attention == 1990s fast-weight
  programmers; the delta rule fixes their memory-capacity limit.
  A real, principled mechanism. `2102.11174`.

### Direct answer to "learn in hours instead of weeks/months"
**Overclaim for training a capable general model from scratch.** None
of the 24 confirmed claims evidences a wall-clock TRAINING-time
reduction. Fast learning is real ONLY as: inference speed (Kind 1),
few-shot adaptation of a pretrained model (Kind 2), or genuine data
efficiency in a narrow heavily-structured domain (Kind 3).

---

## PART 2 — WHAT YOU ACTUALLY HAVE (local, path-cited)

- Only one real trained neural line: the 40-simplex + Fisher-Rao
  model, and your own files record it as largely FALSIFIED — 0/37
  (0.0%) free-decode on fresh records
  (`docs/working/broader_b3_eval/broader_b3_eval_findings.md`), 3/30
  valid generation (`.../CAUSAL_1500_RUN_REPORT_2026-04-28.md`).
- The one experiment that WORKED (Candidate E, 0.78 dev / 0.64
  held-out) was a TRAINING TRICK (scheduled sampling + anchor
  losses), NOT an architecture change; decoder stayed a transformer.
- The SSM/Mamba attempt (Candidate D) was ONE non-canonical run
  (Python-loop scan, no HiPPO, no CUDA), abandoned. No real evidence.
- Probabilistic/Bayesian work: essentially ABSENT. The simplex is
  information geometry (Fisher-Rao), NOT a probabilistic model.
- Strongest genuinely-built theme: NEUROSYMBOLIC — the exact CAS
  compiler used as a verifier/router (`cas-native/inference/
  cas_routing.py`, `evaluation/compiler_preservation_scorer.py`,
  `round_trip_grounding_eval.py`).
- Your own docs already concluded: "the fix has to be in the
  representation, not the output filter"; "a 39-dimensional simplex
  alone cannot speak English. It cannot."

---

## PART 3 — THE CONVERGENCE (this is a HYPOTHESIS, not a result)

The web survey and your local repo point at the same place from
opposite directions:
- Web: the ONLY evidenced order-of-magnitude sample efficiency (BPL)
  comes from HARD STRUCTURE + priors in a NARROW domain.
- Local: you already HAVE hard structure (typed CAS states, a
  40-simplex, an EXACT compiler/verifier) and a NARROW domain (CAS
  notation).

So the one evidence-backed principle in the entire survey
("structure buys sample efficiency") lines up with the one asset your
repo actually has ("structure + verifier").

**But no one has tested this.** The web survey's own open question:
"No surveyed source tests a ~40-dim simplex plus an exact symbolic
verifier — this needs a purpose-built experiment." And BPL's
generality out of narrow domains is UNESTABLISHED. So this is a
well-motivated bet, not a discovery. Treat any claim beyond "worth
testing" as unsupported.

---

## PART 4 — HONEST VERDICT ON YOUR THREE IDEAS

1. "Probabilistic/stochastic model that learns fast" — the evidenced
   version is BPL-style structured program induction or GPs, in
   NARROW low-data domains. A general fast-learning LLM is not
   evidenced. "Learn in hours from scratch" should be dropped.
2. "Use the 40-simplex" — as a probabilistic MODEL it does not exist
   (the simplex is geometry, not inference), and the trained simplex
   model was falsified. As STRUCTURE/prior it aligns with the BPL
   principle, but untested for CAS.
3. "Use the CNCM to keep the LLM in check" — the direction with BOTH
   real local precedent (compiler-as-verifier code already exists)
   AND a clean open research question the survey flagged as
   motivated-but-untested. **This is the most defensible thing to
   build and MEASURE.**

---

## PART 5 — THE ONE EXPERIMENT WORTH RUNNING (falsifiable, cheap)

Do NOT build a novel fast-learning architecture from scratch — that
is overclaim territory. Instead test the single hypothesis both the
literature and your assets support, with a pre-registered kill
criterion (your own A->E methodology):

> **Does an exact CAS verifier gating a general LLM's decoding
> measurably improve correctness / reduce hallucination on a narrow
> CAS task, versus the same LLM unconstrained?**

Why this and not the others:
- Cheap: uses an existing LLM + your existing compiler. No training
  from scratch, no GPU months.
- Evidence-motivated: the BPL principle + the survey's flagged open
  question.
- Has local precedent: compiler-as-router is already built.
- Falsifiable: pre-register the metric and the kill line before
  running (e.g. "verifier-gated must beat unconstrained by >= X on
  held-out CAS-validity AND not regress fluency, or the hypothesis
  is rejected").
- Does not depend on trusting any single model, including me: it is a
  measured comparison you can reproduce.

What it does NOT promise: it does not make anything "learn in hours,"
and it does not resurrect the falsified simplex model. It tests
whether "structure + verifier helps," which is the only claim the
evidence actually supports pursuing.

---

## SOURCES (primary, from the verified survey)
arXiv: 2312.00752 (Mamba), 2111.00396 (S4), 2305.13048 (RWKV),
2402.01032 (attention vs recall), 2508.19029 (SSM optimization),
1703.03400 (MAML), 1909.09157 (ANIL feature-reuse), 1904.04232
(few-shot baselines), 2212.04450 (GAUCHE/GPs), 2102.11174 (fast-weight
programmers). Science 2015 (Lake et al., BPL) + 1902.03477 (Omniglot
progress report). Full 24-source list in the workflow output.
