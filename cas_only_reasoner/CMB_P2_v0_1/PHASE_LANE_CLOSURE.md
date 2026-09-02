# PHASE LANE — CLOSED BY OWNER RULING, 2026-09-02

**Status:** FINAL. Recorded by Claude from the owner's ruling; not a Claude decision.
**Branch:** `research/cmb-p2-p8p9-confirmation` · parent `99909e8c79b9283412826fd7658956794247b777`
**Total spend across the entire phase arc:** CMB-P0 `$0.0241` + CMB-P1 `$0.14` (crashed) +
CMB-P1 `$0.1135` + CMB-P2 `$0.00` = **`$0.2776`**.

---

## 1. Frozen project state — owner's words

```
CMB-P0 and CMB-P1:
Preserved exactly, including PHASE_MEMORY_UNSAFE.

CMB-P2:
NOT LAUNCHED.
Closed as CONSTRUCT_INVALID_TWO_HOP_SHORTCUT.

P8 + P9:
Preserved as a promising engineering observation.
Not accepted as evidence that phase separates thought chains.

Phase hypothesis:
Still open.
Not proven and not disproven.

Phase integration into CMB-R1:
NOT AUTHORIZED.

Frequency, pulse width, and Q:
Not added to the main memory system.

Another immediate phase-benchmark redesign:
Not authorized.
```

`CONSTRUCT_INVALID_TWO_HOP_SHORTCUT` is an **owner-issued status word**. It is added to the
lane's frozen vocabulary and is not subject to reinterpretation.

## 2. Why the lane closed — the one-paragraph version

The benchmark contained a two-hop shortcut, so **it never required the system to separate
thought chains**. A phase-free, label-free rule — recover the candidate set from the adjacency
matrix, then rank by two-hop mass from the cue — scored **0.8255 / 0.8568** at K=2/3, beating
the oracle that was handed the true chain labels at **0.7682 / 0.6797**. With amplitude
included it reached **0.9661 / 0.9323**. Verified on throwaway worlds with the real bench code;
`$0` spent and nothing launched.

**The shortcut was created by the repair for the previous shortcut.** Removing the cue's
private one-hop edge and substituting 0.65-weight edges from the cue's own chain to its
completion moved the signature from depth one to depth two. `GATE_NO_ONE_HOP` passed honestly
and was looking one hop too shallow.

## 3. What survives, precisely

**Preserved, unchanged, not reinterpreted:**

- `PHASE_MEMORY_UNSAFE` for CMB-P0 and for CMB-P1.
- Every measured number in both receipts.
- Every arm-versus-arm comparison. No arm in any of the three benches uses the shortcut — all
  propagate from every active seed, none masks to the recovered candidate set — so all arms
  were equally blind and the paired comparisons remain internally valid.
- Every negative result, every leak, every transient and convergence finding.

**`P8 + P9` — preserved as a PROMISING ENGINEERING OBSERVATION.** It is explicitly **not**
evidence that phase separates thought chains. The measured numbers stand as an engineering
note; the interpretation does not.

**Withdrawn:**

- The claim (CMB-P0 §2.1, inherited by P1 and P2) that the answer is recoverable only by
  knowing which active seeds belong to the cued chain.
- The "90 / 84 / 77 percent of oracle" framing, because the oracle is not the ceiling.

**The phase hypothesis itself is neither proven nor disproven.** Three benches tested an exam
that did not ask the question.

## 4. The RETURN CONDITION — the gate phase work must clear to come back

Owner's wording, recorded as a checkable gate:

> Phase work may return **only when an independently designed benchmark proves that ordinary
> content, one-hop search, two-hop search, topology, and candidate identity cannot solve the
> task.**

Operationally, a future benchmark must register and **measure** a mechanism-free baseline at
every one of these five depths, and show each one fails, **before** any phase arm is run:

```
1. ordinary content        content-similarity ranking
2. one-hop search          adjacency from the cue
3. two-hop search          A^2 mass from the cue          <- what killed CMB-P2
4. topology                any degree / structural signature of the answer set
5. candidate identity      recoverability of the candidate set itself from the graph
```

**And re-measured after ANY world repair** — because in this lane a repair that removed one
shortcut manufactured the next one, twice.

Additionally: the benchmark must be **independently designed**, i.e. not by the party proposing
the mechanism. I designed all three of these.

## 5. Outstanding, and still owed

🔒 **A third-party audit** of CMB-P0, CMB-P1 and CMB-P2 is still owner-actionable. Neither
Claude (which built all three) nor GLM (which built CMB-R1) qualifies. The audit surface now
includes this closure and the two-hop finding.

Reproduction scripts for an auditor, committed alongside this file:

```
verify_twohop_shortcut.py        reproduces the shortcut and the oracle comparison
verify_shuffle_informative.py    shows the phase-shuffle control was fair, not a foregone
                                 conclusion (no-information limit gap = 0.0000 exactly)
```

## 6. Next active lane

**CMB-R1 / RGM-0.2.** The phase mechanism does not enter it. The production memory board stays
**scalar and accountable**, and the mechanisms that survived scrutiny carry forward:

```
semantic retrieval
static CAS geometry
ordered CAS trajectories
bounded graph propagation
additive corroboration
trajectory-coherence checking
static CMB backup and re-ranking
verifier-controlled memory admission
```

Immediate agenda, in the owner's order:

1. fix the false near-match admission problem
2. separate ordinary retrieved candidates from memories authorized to influence reasoning or
   learning
3. strengthen the matched generic geometry control
4. confirm results across new independent memory worlds
5. build the selective replay selector **only after** admission safety passes
6. then test whether CMB-selected replay reduces catastrophic forgetting better than random
   replay and semantic-only replay

Note for that lane, carried from this one: **item 4 is where the shortcut family bites.** New
memory worlds need the five-depth mechanism-free baseline registered before any mechanism arm
is scored, or the same failure recurs in a new costume.
