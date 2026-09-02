# Shortcut Gate v0.1 — the five-depth mechanism-free baseline

**For CMB-R1 / RGM-0.2, item 4: "confirm results across new independent memory worlds."**
Also the registered return condition for any future phase work (owner ruling 2026-09-02).

Run this **before** any mechanism arm is scored on a new world, and **again after any change
to the world builder**.

---

## Why it exists

Three benches in the phase arc were each solvable *without* the capability under test. Each
shortcut was created by the repair for the previous one:

| bench | the shortcut | measured |
|---|---|---|
| CMB-P0 | the gold was the unique non-seed weight-1.0 neighbour of the cue | **1152/1152** dev queries |
| CMB-P0 | the content vector carried a chain's own flavour onto its own gold | gold picked 25/36, 25/42, 26/48 |
| CMB-P2 | two-hop mass from the cue identified the gold — **beating the oracle** | 0.8255 vs oracle 0.7682 |

**Every one of them survived reviewers reasoning about the code. None survived a
measurement.** Two of them survived a full held-out run and were only found afterwards.

**The tell worth remembering:** when the cheapest rule beats an **oracle handed the true
labels**, the task does not require the capability under test at all.

## What it measures

```
1_content              content-similarity ranking from the cue
2_one_hop              adjacency from the cue
3_two_hop              A^2 mass from the cue                 <- this is what killed CMB-P2
4_topology             cue-independent structural fingerprints (degree, weighted degree,
                       triangle count) -- can the answer be picked without looking at the cue?
5_candidate_identity   is the ANSWER SET itself recoverable from the graph alone?
```

Each depth is also measured **multiplied by an optional amplitude score**, because in CMB-P2
it was `two-hop × amplitude` that reached **0.966** — the product beat either part alone.

## Usage

```python
from shortcut_gate import run_gate, format_report

r = run_gate(
    A=adjacency,            # (N, N)
    cue=cue_indices,        # (Q,)
    gold=gold_indices,      # (Q,)
    content=content,        # (N, D) or None
    candidates=None,        # (N,) or (Q, N) bool admissible set, or None
    exclude=seed_mask,      # (Q, N) bool -- nodes that cannot be answers
    amplitude=scalar_scores,# (Q, N) optional, e.g. the retrieval engine's own output
    oracle_top1=0.78,       # optional; if a depth beats this, the task is not what you think
)
print(format_report(r))
assert r["gate"] == "PASS"
```

## The threshold, and why it is not a fixed number

A depth fails if its top-1 exceeds

```
chance + max(0.05, 3 * standard_error)
```

where the standard error uses **the number of distinct `(cue, gold)` pairs — not the number of
queries.** CMB-P0 shipped with 64 queries per world that were only **2–4 distinct**; a fixed
tolerance on a handful of distinct pairs flags sampling noise as a leak. The gate reports
`effective_n_distinct_cue_gold_pairs` so you can see the real sample size at a glance. If that
number is small, that is itself a finding about the world.

## Self-validation — run this first

```
python validate_gate.py
```

A gate that misses known leaks is worthless; so is one that fails everything. `validate_gate.py`
runs four cases with the required verdict stated in advance:

| case | required | result |
|---|---|---|
| A synthetic world with a deliberate one-hop shortcut | FAIL at `2_one_hop` | caught, 1.0000 |
| B `cmb_p0.build_world` (content leak + two-hop) | FAIL at `1_content`, `3_two_hop` | both caught |
| C `cmb_p1.build_world_p1` (content repaired) | FAIL at `3_two_hop`, PASS content | caught; content **0.0000** |
| D clean synthetic world | PASS everything | PASS |

**Current status: `GATE SELF-VALIDATION: PASS`.**

Case C doubles as independent confirmation that the CMB-P1 content repair worked: raw content
top-1 falls from `0.4062` in case B to `0.0000` in case C.

## Scope

This is graph algebra and construct validation, **not neural inference**, so it does not fall
under the GPU-only compute law. It is device-agnostic and runs wherever the caller's tensors
already are. It costs seconds.

It cannot prove a world is sound — only that these five specific shortcuts are absent. It is a
floor, not a ceiling. If a new mechanism can see a depth this gate does not measure, add that
depth **before** running the mechanism, not after.
