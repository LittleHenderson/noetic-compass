# Probe v0.2 self-test: expected outcomes, written before any run (2026-09-23)

**Why.** The before-reading on unchanged Helm 2.0 is all zeros. A probe that can never fire would also read
zeros. So the probe (`analogy_wiring_probe_v0_2.probe_one`, unchanged) is run on three hand-built scoring
variants. Each is wrapped around `GraphForward._world_scores` **in memory only**. The Helm source file's hash is
recorded before and after the run, and it must be the same.

**Model.** One fresh Helm 2.0 container, framework seed 20260917.

| Variant | What it adds to candidate c's score | Expected verdict | Why |
|---|---|---|---|
| `POSITIVE_COMPARISON` | `-2 * L1(degree histogram(focus), degree histogram(c)) - 2 * [domain(c) == domain(focus)]` | `PRESENT_GRAPH_AND_DOMAIN` | a real focus-to-candidate comparison of graph and domain; rewiring a bystander moves only that bystander |
| `NEGATIVE_UNIFORM` | `3 * (focus edges + focus nodes)`, the same for every candidate | `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` | standardising removes any shift shared by all candidates |
| `NEGATIVE_COUPLED` | `0.5 * <mean histogram over ALL worlds, histogram(c)>` | NOT `PRESENT_GRAPH` and NOT `PRESENT_GRAPH_AND_DOMAIN`: either `COUPLED_NOT_COMPARISON` or `MIXED` | it depends on the focus only through a pool over every world; rewiring a bystander moves everyone |

**Precision.** The variants add their terms in float64, to the float64 copy of Helm's float32 logits. A
constant added in float32 would perturb every logit by rounding, about 1e-6 at a score size near 20. That would
test float32 arithmetic, not the probe's shift-invariance.

**What a failure means.** If any expectation fails, the probe is **not fit** to check Codex's repair until it is
fixed. The failure is reported, not re-read.

**Limits.** Those of `PREREG_ANALOGY_WIRING_PROBE_v0_2.md` with amendment A1:
- the local RTX 4070;
- forward passes only;
- at most 3,600 s;
- no other CPU-heavy job running at the same time.
