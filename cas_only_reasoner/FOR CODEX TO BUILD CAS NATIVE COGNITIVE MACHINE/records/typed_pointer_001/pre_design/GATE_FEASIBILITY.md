# Gate feasibility: can the relational gate detect a real improvement?

> Written 2026-09-19 by the orchestrating agent, HEAD `75ffa643`. **Pure arithmetic on the frozen gate rule** —
> no material load, no torch, no AWS, $0. Script: `gate_power.py` beside this file.
>
> This is a statement about the TEST, not about the machine. It measures how often the gate would print
> `LEARNS_NEW_WORLDS` if the machine genuinely improved on a given fraction of the honest relational questions.

## 1. The gate, as the owner confirmed it

Per seed: exact one-sided binomial on **discordant** held-back relational questions, requiring `b > c` and
`p <= 0.01`; plus gains in **≥ 2 kinds** and **≥ 2 worlds**; and it must hold in **all three seeds**.

With no regressions (`c = 0`) the p-value is `2**-b`, so the smallest passing count is **7**.

## 2. Regressions raise the bar steeply

| losses `c` | smallest passing `b` | p-value |
|---|---|---|
| 0 | **7** | 0.0078125000 |
| 1 | 10 | 0.0058593750 |
| 2 | 12 | 0.0064697266 |
| 3 | 14 | 0.0063629150 |

Getting one previously-correct question wrong costs three extra gains. Any churn during training is therefore very
expensive, and the real power is always **below** the table in §3, which assumes no losses at all.

## 3. Probability that a single seed clears, by honest population size

Assumes no losses. `N` is the number of honest relational questions; `q` is the true fraction the machine improves on.

```
   N  |   q=0.10    q=0.20    q=0.30    q=0.40    q=0.50
    9 |  0.0000    0.0003    0.0043    0.0250    0.0898
   11 |  0.0000    0.0020    0.0216    0.0994    0.2744
   13 |  0.0001    0.0070    0.0624    0.2288    0.5000
   15 |  0.0003    0.0181    0.1311    0.3902    0.6964
   17 |  0.0008    0.0377    0.2248    0.5522    0.8338
   19 |  0.0017    0.0676    0.3345    0.6919    0.9165
   24 |  0.0075    0.1889    0.6114    0.9040    0.9887
   29 |  0.0216    0.3571    0.8120    0.9767    0.9988
```

## 4. Probability that ALL THREE seeds clear — the actual gate

```
   N  |   q=0.10    q=0.20    q=0.30    q=0.40    q=0.50
    9 |  0.0000    0.0000    0.0000    0.0000    0.0007
   11 |  0.0000    0.0000    0.0000    0.0010    0.0207
   13 |  0.0000    0.0000    0.0002    0.0120    0.1250
   15 |  0.0000    0.0000    0.0023    0.0594    0.3377
   17 |  0.0000    0.0001    0.0114    0.1683    0.5798
   19 |  0.0000    0.0003    0.0374    0.3313    0.7697
   24 |  0.0000    0.0067    0.2286    0.7389    0.9664
   29 |  0.0000    0.0456    0.5355    0.9316    0.9965
```

## 5. What this says

**The three-seed requirement is what does the damage.** At `N = 17` a genuine 40 % improvement gives a 55.22 % chance
in any one seed, and cubing it drops that to **16.83 %**. At `N = 13` — the floor once the legitimate `reach`
no-learning rules are applied — even a **50 %** improvement is worth only **12.50 %**.

**Corrected 2026-09-19.** This section previously put the floor at `N = 11` on the strength of a "constant `VIA n1`"
baseline. That baseline was withdrawn as an error (see `measurements/leaks_review/VERIFY_R10_FINDINGS.md` and
`REVIEW_SYNTHESIS.md` §6.4): it can only be derived by reading the held-back answers, which the custody rule forbids,
so it is the answer key and not a mechanism-free baseline. The honest floor is `N = 13`.

**Read against the honest population, the gate is close to unable to pass.** The present best estimates for `N` are:

| scenario | N | P(all three seeds) at a 30 % true improvement | at 40 % |
|---|---|---|---|
| rank kept out of the input | 17 | **0.0114** | 0.1683 |
| **most likely: rank in, R10 and DG3 applied** | **13–15** | **0.0002 – 0.0023** | **0.0120 – 0.0594** |
| no removals at all (the tier as first confirmed) | 29 | 0.5355 | 0.9316 |

**Two different failure modes, and the project has only guarded against one.** Findings FP1–FP3 protect against a
**false positive** — a `LEARNS_NEW_WORLDS` printed when nothing was learned — and they do that job well. This table
describes the opposite risk: a gate so tight that it returns `NO_TRANSFER_TO_NEW_WORLDS` whether or not the machine
learned, which the project's own vocabulary would call a **VACUOUS** test — one that cannot distinguish the two
outcomes. Both are ways of not learning anything from a run.

**Caveats, stated plainly.** This assumes no losses (§2 says losses make it worse), ignores the ≥ 2 kinds and ≥ 2
worlds rules, treats questions as independent when they are not (they come in same-world and same-kind clusters), and
assumes the machine's improvement is uniform across questions rather than concentrated in the easiest ones. Every one
of those makes the real power **lower**, not higher. So §4 is an **upper bound**.

## 6. What follows — and what does not

This does **not** overturn the owner's gate decision, and it is not an argument for weakening a gate to make a result
appear. It is an argument that the study as specified cannot answer the question it was designed to answer at the
population the reviews have now measured, and that this is a **design fact worth knowing before $13 is spent**.

The three honest options, all of which are the owner's to choose:

1. **Run it as specified, expecting `NO_TRANSFER`.** The result is still real and still closes a hypothesis; it simply
   cannot distinguish "the pointer design does not transfer" from "the gate was too tight to tell". That distinction
   must be stated in the protocol so the negative is not over-read.
2. **Enlarge the honest population before running.** More held-back relational questions, or more held-back worlds, so
   that `N` lands where a real effect is detectable. This costs design work, not compute.
3. **Reduce the all-seeds requirement to a pre-declared majority**, with the owner's explicit sign-off and recorded
   before the run. This is a legitimate preregistration choice — a gate's power is part of its design — but it must be
   made *before* seeing any result, and it makes the label weaker, not stronger, so it needs the owner's word.

Nothing here has been acted on. The gate is unchanged and no result has been produced.
