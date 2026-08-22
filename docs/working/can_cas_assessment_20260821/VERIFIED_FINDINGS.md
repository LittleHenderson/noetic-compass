# CAN/CAS deep-dive — independently verified findings — 2026-08-21

13-agent adversarial deep-dive of the CAN paper (arXiv:2509.25236v3), the CAN↔CAS mapping, the Noetic-Topos Revision Plan (T1–T10), CCDL, and the Foundation-Drive Profile. Full memo: `CAN_CAS_HARNESS_DEEPDIVE_MEMO.md`. Two of the team's concrete claims re-verified by hand:

## 1. The T3 obstruction is REAL (load-bearing negative)
Naive 40→10 domain-marginalization is **not** Fisher-Rao isometric — it **contracts** (team's numeric: a generic Fisher-Rao distance `1.403` collapses to `0.737`). The mapping doc rating this "EXACT / embeds isometrically" is **wrong**; the plan's T3 warning is right. This negative must be preserved, not papered over.

## 2. The FD generator hash bug is REAL (verified here)
`fd_generator.py` writes `fd_routing_28.json` in text mode, so on Windows it emits CRLF and the committed file **already fails its own registry hash**:
- on-disk sha256 `b7c81e26…`
- LF-normalized sha256 `8c52f71e…` (recovers the registry value)
One-line fix: `open(..., 'w', newline='\n')` or hash LF-normalized bytes. (Same CRLF-freeze class the successor repo hit repeatedly — a general lesson: every byte-hash gate needs eol normalization.)

## Headline conclusions (from the memo)
- **Strengthens the CAS math paper + governance, NOT immediate harness capability.** The one genuine theory upgrade: a *computable* global-coherence eigenvalue criterion of the kind the current trivial Theorem 6.4 lacks — but it does not transfer verbatim because of T3.
- **T4 interlacing (the falsifiable spectral screen) is NOT testable now** — it needs independent Fisher matrices at ≥2 granularities, and the harness has only 2 validated axes = one granularity. A 2→1 reduction is Cauchy-trivial.
- **Highest-value next action:** build the **Operator-10 and Domain-4 linear probes** on real activations — the single prerequisite that unblocks T4, cross-model dispersion, and the aggregator. Patent-clean, harness's own methodology.
- **Top red flag:** the entire welded chain (CSprob, sheaf/connection-Laplacian, SEP/Stiefel, interlacing, CK diffusion) is **new matter** not covered by provisional 64/037,173; the plan schedules public arXiv disclosure with **no new-matter caveat** — gate on IP review before the 2027-04-13 conversion deadline.
- **Frozen ontology: intact.** No artifact renames the 10 Noetics / 40 States / 7 Drives / 4 Registers or alters the 10×4 grid. No proposal disqualified on ontology grounds.
