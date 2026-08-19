# W0 hidden-prompt-injection bank — recovered from pod `w0pjqx3ndaxfkg` (2026-08-19)

Recovered **before terminating** the A40 pod. The bank was **not in git** and existed only
on that pod; prompt-injection detection is a Gate-3 capability, so losing it would have cost
the scenario set behind that whole track.

| File | What it is |
|---|---|
| `hidden_prompt_injection_bank_v0_20260617.json` | 640 scenarios, created 2026-06-18. sha256 `2df5b9ced77d767694ed13829fd9995432fc3e53d27862cd1145c5dd139b2a34` (verified equal on pod and locally). |
| `w0_extract.py`, `w0_extract_v2.py` | the hidden-state extraction scripts that turn the bank into activation captures |
| `w0.log` | the extraction run log |

**Claim ceiling, carried verbatim from the bank's own metadata:** *"Data-readiness only.
Internal W0 prompt-injection detection, live pre-speech interception, prevention/removal/
reversal, hall…"* — i.e. this is a **fixture**, not a validated detector. See also the
standing finding that **a W0 detector was withdrawn** once a char-level surface control was
applied; that gate is now permanent.

**Not recovered (deliberately):** `w0_hidden_pi_v0*.npz` (~60 MB of mean-pooled activation
captures for 1b/2.8b). Per the repo data policy large ML captures stay off git, and they are
**regenerable** from this bank + the pinned models + `w0_extract*.py`. If the pod is
terminated they are gone, but reproducible — which is why the bank and the scripts were the
priority.
