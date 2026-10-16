# R1-RT design, appendix E: the assumption that fails, and what survives it

**Date:** 2026-10-16
**Status:** the design's central assumption is **falsified by measurement**. The rest of the design
stands, and one part of it becomes *more* load-bearing rather than less.

## 1. The assumption

Parts one and two, appendix C and appendix D all assume the same thing: that the recipe brain can be
hosted **inside HELM's own runtime, in the runtime's own process**, sitting where the runtime's
operation module sits. Appendix D exists to make that hosting work.

## 2. The measurement that kills it

`rb/__init__.py` installs an import blocker on import, and that blocker's `install()` **raises if
torch is already loaded**:

```
RuntimeError: RB1G: ['torch', 'numpy'] already imported before the blocker;
              the RB process must not hold torch
```

Once installed, the blocker refuses any later `import torch`:

```
rb.no_torch.TorchRefused: RB1G: import of 'torch' is refused inside the RB process (rb.no_torch)
```

Four import orders were run, each in its own subprocess so that the first import could not poison the
second. **All four were refused.**

| order | outcome |
|---|---|
| `torch`, then `rb` — what route D needs | REFUSED: `['torch', 'numpy'] already imported before the blocker` |
| `rb`, then `torch` | REFUSED: `import of 'torch' is refused inside the RB process` |
| `torch`, `rb`, then `rb3` | REFUSED: same as the first |
| the runtime's own modules (`cas_cjt.types`, `cas_cjt.neural`), then `rb` | REFUSED: same as the first |

Reproduce with `probe_brain_in_runtime.py <v3-package-root>`. The last order matters most: it shows
that the refusal is not about torch alone. **`numpy` rides in with torch**, and the blocker refuses
both, so there is no partial order in which the runtime's own modules are loaded and the brain is not
already too late.

## 3. The refusal is correct, and must not be worked around

The blocker is not an obstacle to route around. It is **the mechanism by which the brain's own run is
shown to be torch-free**. Removing it, or removing the blocker from `sys.meta_path` after importing
`rb`, would leave the brain's reading unable to say what it says. The package is also frozen
(`FROZEN.json`, `PACKAGE_FREEZE.json`).

HELM's own `rb3` package states the trade-off in its docstring and resolves it the other way:

> `block_torch()` installs an import blocker for torch and numpy; the pure stages and the unit tests
> call it so a stray import fails loudly. **It is NOT installed on import, because `t_on_b/t_b.py`
> imports these pure modules and then imports torch.**

So the project has met this exact shape before. `rb3` made the blocker **opt-in** so a torch script
could import the pure modules and then torch. `rb` (RB1g2, the sealed brain) made it **unconditional
on import**, because its reading requires the refusal. Both are deliberate. They cannot both hold in
one process.

## 4. What this costs

**Route D, as designed, is not buildable.** Not because the patch is wrong — the patch is tested and
works — but because the thing the patch is for cannot be placed where the patch puts it.

## 5. What survives, and it is almost all of it

| artefact | status after this finding |
|---|---|
| Appendix A, the input rule | **unchanged.** It converts the case into the brain's recipe inputs. That conversion can happen on the brain's side of a boundary. |
| Appendix B, the output rule | **unchanged.** It says how a label becomes the output tensor. The in-runtime side still does that. |
| Appendix C, the seam | **unchanged, and better read.** The seam it describes is now a process seam as well as a call seam. |
| Appendix D, the patch | **unchanged, tested, and now NECESSARY rather than convenient.** See below. |
| Parts one and two, the envelope | **must be re-costed** for a boundary. Not yet done. |

**Why the patch becomes necessary.** Across a process boundary, the in-runtime operation stops being
the brain and becomes the brain's **client**. A client has to send the *question*. Without the case,
the client holds only CASformer's attention projection of the question — a tensor — and there is
nothing to send. Passing `cause.content` to the operation is therefore no longer a design preference
that makes the frozen input rule work nicely. It is the only way the client can know what to ask.

Measured in appendix D: the case does arrive, as a read-only `mappingproxy` whose sequence values are
tuples.

## 6. The corrected shape

**R1-RT = appendix D's patch + a process boundary.**

The runtime keeps its patch and gains a thin client where the operation module sits. The client holds
a long-lived child process that has `rb` imported and has never seen torch. Per tick the client sends
the case content and receives a label; it writes that label into the output tensor by appendix B's
rule. Appendix A's conversion runs on the brain's side.

A long-lived worker, rather than a process per tick, is the shape the envelope can afford: one
interpreter start plus one JSON line per tick, against the transformer side's 84,910.44 s over 44
units already on the record.

## 7. What is NOT yet known

Stated plainly so nobody reads this appendix as a finished design.

1. Whether the runtime accepts an `EXPERIMENTAL_OPEN_SEMANTICS` operation as a node's **registered**
   operation. `_prepare_inference` binds the contract for the node's registered operation id; whether
   that path admits an experimental one has not been measured.
2. Whether the runtime's verifier accepts a proposal whose candidate effect came from outside the
   process. The verifier evaluates cause, candidate, contract, evidence and bias — all of which are
   in-process — so this looks tractable, but it is not measured.
3. The per-tick cost of the boundary, and the re-costed envelope.
4. Whether the client must be an `nn.Module`. `neural.py:211-212` requires it for a **registered**
   operation module. A client with no parameters is still an `nn.Module`, so this is likely fine, and
   is not measured.

## 8. What did not change

The owner's decision is not made for them by this appendix. It narrows what the decision is about.

- **Route D alone** is no longer on the table.
- **Route D plus a process boundary** is the design's recommendation, and it is now the only shape
  that both keeps the frozen input rule working on the clean case and lets the brain run as itself.
- **Route A** — no runtime edit, the brain answers CASformer's projection — remains available, and
  remains the only route that needs no boundary. It still has to be labelled, because the brain would
  be answering a projection rather than the question.
- **The seal still needs the owner's word.** Nothing here was applied to a frozen tree.
