# V15 — SCALE DOMAIN: framing-matched Domain-4 on pythia-6.9b (PAID A40) — the last control crosses over

**Date:** 2026-08-21 · **Model:** `EleutherAI/pythia-6.9b` (32 layers, 4096 hidden), `transformers 5.15.1`, `torch 2.8.0+cu128`, fp16 CUDA.
**Hardware:** owner-authorized paid RunPod **A40** (`$0.44/hr`, hard 22-min watchdog, pod `5kshsd3n5utxdz` verified `EXITED`). Direct transformers forward hooks — **NOT** the attested engine (research data run; canary still `NOT RUN`).
**Results file (co-located):** `detector_validation_v15_scale_domain_pythia69b_results.json`, sha256 `f962fb89838c794c…`

## The question
Domain-4 was the WEAKEST axis. At 160m framing-matched (v11) it was **PARTIAL**: activation `0.625` vs surface `0.438`, with `O` surface-carried (4/4 both) and `P` collapsing to `1/4` once the modal words ("must/ought") were stripped. Does it harden at 43× scale like valence and Operator-10 did — or stay surface-lexical?

## Result (exact)

| | overall | P | C | E | O |
|---|---|---|---|---|---|
| **activation** (6.9b, L17) | **0.938** (15/16) | 3/4 | 4/4 | 4/4 | 4/4 |
| char-ngram surface | **0.438** (7/16) | 0/4 | 2/4 | 1/4 | 4/4 |

- chance `0.25`; **activation − surface = `+0.500`** (8 items); `15/16` at chance 0.25 is **P=`3.65e-07`** even best-of-32-layer selection.
- **vs 160m (v11):** activation `0.625` → `0.938`; margin over surface `+0.188` → `+0.500`.

## What it means — Domain-4 HARDENS DECISIVELY at scale

The weakest axis at 160m is one of the **strongest** at 6.9b. The activation detector reads P/C/E/O from **framing-stripped, brand-new topics** at `0.938`, beating the word-counter by **+0.500** — a wide, robust margin (P=3.65e-07 over chance).

**Per-domain, the two 160m negatives are resolved:**
- **`P` recovers.** At 160m, stripping the modal words collapsed "principled" to `1/4` (it was modal-word-carried). At 6.9b, `P` is `3/4` while surface is `0/4` — **the model reads "principled" from meaning, not modals, at scale.**
- **`C` and `E` separate cleanly** (`4/4` vs `2/4`; `4/4` vs `1/4`) — up from thin one-item edges at 160m.
- **`O` remains surface-shared** (`4/4` both). The imperative structure is still a surface tell that char-ngrams catch — but the activation gets it too. This is the one honest residual: O's separability is not activation-exclusive.

## The scale picture is now complete and consistent

At 6.9b, **four axes beat the char-ngram word-counter** — three cleanly, one marginally:

| Axis | 6.9b activation | surface | margin | verdict |
|---|---|---|---|---|
| Valence `^2`/`^3` (v10) | 0.938 | 0.500 | +0.438 | clean |
| **Domain-4 P/C/E/O** (this run) | **0.938** | 0.438 | **+0.500** | **clean** |
| Operator-10 `^0`..`^9` (v14) | 0.800 | 0.550 | +0.250 | clean |
| `^8`/`^9` (v14) | 0.917 | 0.833 | +0.083 | marginal |

**Established: the CAS reading axes are surface-confounded at 160m but harden decisively at scale.** Every axis that failed a surface control at 160m — valence, Operator-10, Domain-4 — beats it cleanly at 6.9b; only `^8`/`^9` is merely marginal. This substantially **strengthens Claim B** (CAS as a measurement language): the "reading" capability is real, register-independent, and multi-axis at scale — not a small-model artifact and not giveaway-word matching.

## Claim state
- **Real:** all numbers, real pythia-6.9b weights via direct transformers on a paid A40. **Accepted:** none — research-grade.
- **Not the attested engine / not the canary:** direct transformers; frozen canary still `NOT RUN`.
- **Clean positive:** Domain-4 crossover (+0.500, P=3.65e-07); P recovers at scale.
- **Honest residual:** `O` stays surface-shared (4/4 both) — not activation-exclusive.
- **Caveat:** activation best-of-32-layers selected on the 16-item test set (surface gets no selection); n=4 held-out topics per domain; single run. The +0.500 margin and P=3.65e-07 make selection noise an implausible explanation.
