# CAS Probe — Pythia interpretability experiment (research-only)

**Status:** research, not production. **DO NOT** import anything in this
directory from `api/`, `cas-native/`, `dashboard/`, or any production stack.

## Purpose

Test the central pitch of CAS Mode 7 against a fully-open language model:

> When a language model processes English text, are CAS structural axes
> (noetic, domain, register, drive) detectably present inside the model's
> internal activations — not just on its output?

If yes, CAS gives us a real interpretability handle on any open model.
If no, the CAS framing requires explicit training to surface, and the
"Mode 7 as anti-black-box" pitch needs revision.

Two tests:

1. **Detection (Stage 2).** Train a small linear classifier (a probe) to
   read CAS axis labels from Pythia hidden states. Beating chance is
   **not** enough on its own — the labels could be recoverable from the
   English text alone. The probe must also reliably beat plain-text
   baselines (TF-IDF, count-vector) by at least 5 percentage points
   with a McNemar p < 0.05 on the paired discordant samples. See the
   revised decision gates below.
2. **Causal influence (Stage 3, gated on Stage 2).** Mess with the
   detected direction inside Pythia (turn it down, scramble it) and see
   if the output changes. If yes, the structure is not just there — it's
   load-bearing. This is a different kind of evidence (causal, not
   discriminative) and remains worth running even when Stage 2 lands at
   `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT`.

## Isolation guardrails (user-ratified 2026-05-15)

This directory is sandboxed. Hard rules:

1. **Branch:** all work on `experiment/cas-probe-pythia`. Never merged to
   `master` without separate audit + explicit user approval.
2. **Directory:** code lives ONLY under `research/cas_probe/`. No Pythia
   imports anywhere else.
3. **Production isolation:** no Pythia imports in `api/`, `dashboard/`,
   `cas-native/` loader, chat REPL, or training stack. Pythia is the
   test subject, not part of CAS Native.
4. **Frozen labels:** the probe never reads live Wave 2.5 / Wave 3
   corpus files. It uses a frozen snapshot named
   `pythia_probe_labels_YYYYMMDD.jsonl` with a companion manifest
   (sha256, source files, record count, extraction rules).
5. **Naming:** all artifacts prefixed `pythia_` or marked
   `research_only`.
6. **Failure protocol:** if the experiment fails or is abandoned, delete
   this branch and the artifacts cleanly. CAS Native is untouched.

The key invariant: **Pythia never becomes CAS Native. It is the test
subject. CAS is the measuring instrument.**

## Stages

| Stage | Status | Deliverable |
|---|---|---|
| 1.0 | done | `README.md`, `build_pythia_probe_snapshot.py`, frozen labels jsonl, manifest |
| 1.1 | done | Pythia-160M activation capture script + smoke test |
| 2 | done | per-layer linear probe training |
| 2.1 | done | TF-IDF baseline, shuffled-label control, val-selected headline, confusion matrix |
| 2.2 | **done — labels recoverable, mostly text-baseline explained** | majority / stratified / count-vector baselines, paired contingency, McNemar test |
| 3 | pending (exploratory only) | causal-influence ablation |

## Decision gates (revised post-audit 2026-05-16)

These are the stricter gates after Codex audit `6a7d657`. Beating
chance is necessary but **not sufficient**. To claim a model adds
structure beyond plain text we require BOTH:

- Pythia headline test accuracy minus best-text-baseline test
  accuracy **>= 5 percentage points**, AND
- McNemar's exact binomial test on the paired discordant pairs
  (Pythia-only-correct vs text-baseline-only-correct) **p < 0.05**.

Verdict tiers:

- `PROBE_RELIABLY_ABOVE_TEXT_BASELINE` — both criteria pass.
- `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT` — headline beats chance but
  not text reliably. This is where Stage 2.2 lands.
- `PROBE_WEAKLY_ABOVE_CHANCE` — between chance and the 30% strong
  threshold.
- `NULL_RESULT` — at or below chance.

## Stage 2.2 headline result (2026-05-16, post-second-Codex-audit)

**Verdict: `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT`.** No reliable
beyond-text lift is established yet.

The pre-Codex Stage 2 framing ("92.8% strong signal") and the Stage
2.1 framing ("Pythia adds +1.4 pp over text") were both too strong.
Codex's second audit `6a7d657` re-ran the paired contingency on the
same 69-sample test set:

- both correct: 59
- Pythia layer-3 only correct: **3**
- TF-IDF only correct: **2**
- both wrong: 5
- discordant total: 5
- McNemar exact binomial p (two-sided): **1.0000**

The +1.4 pp Pythia-over-TF-IDF gap reduces to **one net sample**
on the discordant set, which is indistinguishable from chance
imbalance. **The honest claim is that the noetic label is recoverable
from this corpus, but Pythia's mid-network does not add reliable
signal over plain text on this evidence.**

**Full baseline + headline table:**

| Source | Val acc | Test acc | macro-F1 |
|---|---:|---:|---:|
| Chance (1/10) | 0.100 | 0.100 | — |
| Majority class | 0.130 | 0.130 | — |
| Stratified random | 0.130 | 0.188 | — |
| Count-vector + LogReg | 0.855 | **0.884** | 0.882 |
| TF-IDF + LogReg | 0.841 | **0.884** | 0.882 |
| **Pythia layer 3 (val-selected)** | **0.899** | **0.899** | 0.902 |
| Shuffled-label control on layer 3 | 0.130 | 0.101 | — |

Notable: count-vector and TF-IDF tie at 0.884. TF-IDF re-weighting
adds nothing here. Lexical patterns in Claude's English do almost all
the work.

**Per-layer Pythia probe accuracies for the record:**

| Layer | Train | Val | Test | macro-F1 |
|---:|---:|---:|---:|---:|
| 0 (embed) | 1.000 | 0.855 | 0.884 | 0.886 |
| 1 | 1.000 | 0.884 | 0.913 | 0.912 |
| 2 | 1.000 | 0.884 | 0.913 | 0.912 |
| **3** ← headline (val) | 1.000 | **0.899** | 0.899 | 0.902 |
| 4 | 1.000 | 0.899 | 0.928 | 0.931 |
| 5 | 1.000 | 0.884 | 0.928 | 0.926 |
| 6 | 1.000 | 0.855 | 0.913 | 0.916 |
| 7 | 1.000 | 0.812 | 0.884 | 0.884 |
| 8 | 1.000 | 0.841 | 0.899 | 0.902 |
| 9 | 1.000 | 0.812 | 0.884 | 0.887 |
| 10 | 1.000 | 0.812 | 0.870 | 0.868 |
| 11 | 1.000 | 0.812 | 0.884 | 0.886 |
| 12 | 1.000 | 0.812 | 0.870 | 0.872 |

(Same per-layer numbers as Stage 2.1; only the interpretation changed.)

**Reserved-language verdict:**

> On this CAS-labeled English corpus (n=457, test n=69), a linear
> probe on Pythia-160M layer-3 hidden states recovers the noetic label
> at test accuracy 0.899 (macro-F1 0.902), vs a 10% chance baseline
> and a 0.130 majority-class baseline. TF-IDF and count-vector
> baselines on the same text both reach 0.884. The Pythia probe adds
> +1.4 pp over TF-IDF. The paired contingency table shows 59 both
> correct, 3 Pythia-only correct, 2 TF-IDF-only correct, 5 both wrong
> (discordant n=5). McNemar's exact binomial test on the discordant
> pairs gives p=1.0000. The shuffled-label control drops to 0.101,
> ruling out a split leak.
>
> Honest claim on current evidence: the noetic label is recoverable
> from this corpus, but the lift Pythia adds over a plain text baseline
> is NOT statistically reliable on this test size. No reliable
> beyond-text lift is established yet. Causal (ablation) and
> paraphrase-control tests are required before any "Pythia
> mechanistically encodes CAS" claim. Verdict treated as
> tamper-evident, reproducible, independently inspectable; not as
> proof of mechanistic alignment.

**What this means for the Glass House AI pitch:**

The strategy memo's core claim — that probing open-model activations
gives interpretability signal beyond what plain text classifiers
offer — is **not supported by current evidence**. The memo at
`STRATEGY_GLASS_HOUSE.md` needs a re-read under the stricter standard,
and any external-facing copy must be paused until Stage 3 ablation
delivers a separate line of evidence.

**Three next moves and the order I'd take them:**

1. **Stage 3 ablation, exploratory only.** Ablate the layer-3 direction
   in Pythia and check whether the output changes in a CAS-semantically-
   correct way. This is a different kind of evidence (causal, not
   discriminative). It is the test that could rescue or kill the
   mechanistic claim — but no public Glass House claims off this single
   experiment regardless.
2. **Cross-axis (domain, register, drive).** Cheap rerun. Maybe noetic
   is the lexically-easiest axis and others show a real Pythia-over-text
   lift. Same paired-baseline gates apply.
3. **Larger Pythia.** Pythia-160M is the smallest member of the family.
   Pythia-1.4B or 2.8B may carry richer internal structure that doesn't
   appear in the 160M slice. Still gated on the same paired-baseline
   reliability check.

Public Glass House messaging stays paused until at least one of these
delivers a `PROBE_RELIABLY_ABOVE_TEXT_BASELINE` verdict.

Artifacts on disk (unchanged shapes; only the report and README
revised under Stage 2.2):

- `pythia_noetic_probes_20260515.npz` — trained probes + split indices.
- `pythia_noetic_probes_report_20260515.json` — per-layer metrics,
  full baseline set (chance, majority, stratified, count-vector,
  TF-IDF), shuffled-label control, paired Pythia-vs-TF-IDF
  contingency + McNemar p-value, headline confusion matrix,
  reserved-language verdict.

---

## Stage 2.1 result (kept for audit trail)

**Verdict: `PROBE_RECOVERS_LABELS_NOT_ABOVE_TEXT_BASELINE`.**

Per Codex audit `f0eadd0`, the previous Stage 2 framing ("Pythia
detectably encodes CAS at 92.8%") was overclaim. Two problems:

1. The headline cherry-picked the best **test** layer. The test set
   must be held out and used once, not used to pick the layer. The
   val-selected layer is layer **3** with **test acc 0.899**, not
   layer 4 at 0.928.
2. No text baseline was reported. A plain TF-IDF + logistic regression
   on the same English text reaches **0.884** test acc. Pythia's
   probe adds only **+1.4 pp** over the text baseline. The 88%-90%
   range is almost entirely a property of the English text the SDG
   pipeline produced, not of Pythia's internals.

**Honest headline table:**

| Source | Val acc | Test acc | macro-F1 |
|---|---:|---:|---:|
| TF-IDF text baseline | 0.841 | **0.884** | 0.882 |
| Pythia layer 3 (val-selected headline) | 0.899 | **0.899** | 0.902 |
| Pythia layer 4 (highest test, but test-leakage) | 0.899 | 0.928 | 0.931 |
| Shuffled-label control on layer 3 | 0.130 | **0.101** | — |
| Chance | 0.100 | 0.100 | — |

The shuffled-label control at 10.1% confirms the split is clean: when
labels are randomized on train, the probe drops to chance. The +1.4 pp
Pythia-over-TF-IDF gap is real but small.

**Per-layer accuracies (val + test) for the record:**

| Layer | Train | Val | Test | macro-F1 |
|---:|---:|---:|---:|---:|
| 0 (embed) | 1.000 | 0.855 | 0.884 | 0.886 |
| 1 | 1.000 | 0.884 | 0.913 | 0.912 |
| 2 | 1.000 | 0.884 | 0.913 | 0.912 |
| **3** ← headline (val) | 1.000 | **0.899** | 0.899 | 0.902 |
| 4 | 1.000 | 0.899 | 0.928 | 0.931 |
| 5 | 1.000 | 0.884 | 0.928 | 0.926 |
| 6 | 1.000 | 0.855 | 0.913 | 0.916 |
| 7 | 1.000 | 0.812 | 0.884 | 0.884 |
| 8 | 1.000 | 0.841 | 0.899 | 0.902 |
| 9 | 1.000 | 0.812 | 0.884 | 0.887 |
| 10 | 1.000 | 0.812 | 0.870 | 0.868 |
| 11 | 1.000 | 0.812 | 0.884 | 0.886 |
| 12 | 1.000 | 0.812 | 0.870 | 0.872 |

**Reserved-language verdict:**

> On this CAS-labeled English corpus (n=457), a linear probe on
> Pythia-160M layer-3 hidden states recovers the noetic label at test
> accuracy 0.899 (macro-F1 0.902), against a 10% chance baseline. A
> TF-IDF + logistic-regression baseline on the same text reaches
> 0.884; the Pythia probe adds +1.4 pp over text alone. A
> shuffled-label control on the same layer drops to 0.101, ruling out
> a split leak. This evidence is consistent with Pythia's internal
> representations carrying noetic-axis information beyond what is
> recoverable from surface wording, **but the marginal lift over the
> TF-IDF baseline is modest**. Causal-influence (ablation) and
> paraphrase-control tests are required before any claim that Pythia
> mechanistically encodes CAS structure beyond lexical association.
> Verdict treated as tamper-evident, reproducible, independently
> inspectable; not as proof of mechanistic alignment.

**Confusion matrix (val-headline layer 3, test set, rows = true y,
cols = pred y):**

```
     ^0  ^1  ^2  ^3  ^4  ^5  ^6  ^7  ^8  ^9
^0    7   0   0   1   0   0   0   0   0   0
^1    0   6   0   1   0   0   0   0   0   0
^2    0   0   9   0   0   0   0   0   0   0
^3    1   1   0   5   0   0   0   0   0   0
^4    0   0   0   0   6   0   0   0   0   0
^5    0   0   0   0   0   6   0   0   0   0
^6    0   0   0   0   0   0   6   0   0   0
^7    0   0   0   0   0   0   0   8   0   0
^8    1   0   0   0   0   0   0   0   4   0
^9    1   0   0   1   0   0   0   0   0   5
```

Mostly diagonal. ^0 (Idea — the generic "all things in/outside Mind"
catch-all) absorbs misclassifications from ^3, ^8, and ^9 — consistent
with ^0's broader semantic scope.

**What this means for the Glass House AI pitch:**

The honest current claim is **weaker** than Stage 2's initial framing.
On this single model, with this single axis, with Claude-generated
English, the bulk of the probe's signal is recoverable from plain
text. That's not nothing, but it does not yet support claims about
"Pythia mechanistically encoding CAS." The Glass House strategy memo
should be re-read and revised under this stricter standard.

**Decision-gate revisions for next stages.**

- Stage 3 (causal ablation) is still the right test. If ablating the
  detected layer-3 direction changes Pythia's output in a CAS-
  semantically-correct way, the +1.4 pp gap is mechanistically
  meaningful. If ablation just scrambles output, the gap is
  decoration.
- Cross-axis (domain, register, drive) is also worth running on the
  same activations — cheap (~10 min total). Maybe noetic happens to
  be the lexically-easiest axis and the others show a larger
  Pythia-over-TF-IDF lift.
- Cross-model (OLMo or Qwen) is the larger investment. Only worth it
  after at least one axis or one ablation suggests Pythia adds real
  structure over text.

Artifacts on disk:

- `pythia_noetic_probes_20260515.npz` — trained probes (coefs,
  intercepts, scaler params, per-layer, plus the train/val/test
  index arrays).
- `pythia_noetic_probes_report_20260515.json` — per-layer metrics,
  TF-IDF baseline section, shuffled-label control section, headline
  confusion matrix, Pythia-vs-TF-IDF delta, reserved-language verdict.

## Files

- `.gitattributes` — pins LF line endings on the research JSON / JSONL /
  Python / Markdown files so the manifest's sha256 of the snapshot
  matches the on-disk bytes on any host (Windows, Linux, macOS).
- `pythia_probe_source_wave3_cas_to_english_20260515.jsonl` — vendored
  slice of the wave3 corpus, containing only the 1,129 `cas_to_english`
  records. Vendored inside the branch so a clean checkout can rebuild
  the labels snapshot without depending on out-of-branch files.
- `build_pythia_probe_snapshot.py` — joins the vendored wave3 slice with
  `cas-synthetic/data/path_d/seeds.jsonl` (tracked at its canonical
  path) and writes a frozen snapshot + manifest. Deterministic: re-running
  with the same source files produces byte-identical output. Includes a
  regex-based CAS-notation leakage filter (added post-audit) so the
  probe cannot read its label off the prompt.
- `pythia_probe_labels_20260515.jsonl` — frozen labels for the
  experiment. **Read-only.** Regenerate by re-running the builder.
- `pythia_probe_manifest_20260515.json` — sha256 of the snapshot,
  source-file paths + hashes, record count, class distribution,
  extraction rules in plain text, and rejection counts (including the
  new leakage-regex rejections).
- `capture_pythia_activations.py` — Stage 1.1 capture script. Loads
  Pythia-160M, mean-pools hidden states per layer, dumps a `.npz`. NOT
  YET RUN — requires explicit user OK to install `transformers` and
  download Pythia weights.

## Decision gates (superseded — see "Decision gates (revised)" above)

The original pre-experiment gates listed below proved insufficient.
Beating chance only proves the labels are recoverable from the
English text the SDG pipeline produced — it does not show the model
adds structure beyond plain bag-of-words classification. The Stage
2.2 audit (commit `0421e7f`) replaced these gates with the stricter
paired-baseline + McNemar criterion in the **"Decision gates
(revised post-audit 2026-05-16)"** section near the top of this
README. The bullets below are retained for the audit trail only:

- ~~**Stage 2 pass:** best-layer noetic-probe test accuracy ≥ 30%
  (vs 10% chance baseline across 10 noetic classes).~~
- ~~**Stage 2 weak:** 20%–30%. Run ablation analysis to understand
  which noetics are detectable and which are not.~~
- ~~**Stage 2 fail:** <20%. CAS structure is not naturally factored
  in Pythia's activations at the prompt-encoding level.~~
- **Stage 3 pass (still load-bearing):** ablating the detected
  direction changes the output measurably (output similarity drops
  below a threshold).

## What CAS Mode 7 means here

Mode 7's mechanistic-attribution surface (`Mode7LiveShell` in the
dashboard, `api/routes/mode7.py` on the backend) was built against CAS
Native's own activations — which have named axes by construction.

For a fully-open foreign model like Pythia, "Mode 7" means the same
*idea* — bind activations to CAS commitments, trace them through the
network, test their causal role — but the binding needs trained probes
because Pythia doesn't have CAS axes baked into its architecture.

If this experiment succeeds, the pitch becomes: *"Mode 7 works on any
open-weight model after training probes; with CAS Native, the probes are
the architecture."*
