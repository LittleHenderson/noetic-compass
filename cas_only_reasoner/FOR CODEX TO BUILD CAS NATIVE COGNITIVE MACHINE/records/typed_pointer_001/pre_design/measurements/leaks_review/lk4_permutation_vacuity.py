"""LEAKS LENS lk4: permutation vacuity -- which checks and metrics cannot fail by construction.

Measures, per kind, whether the PRIVATE answer is determined by structure alone (invariant
under renaming the focus world's node refs), because a pointer machine that treats nodes
symmetrically cannot know a name-determined answer. Pure Python, no torch, no network.

    python lk4_permutation_vacuity.py
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lk0_material import KINDS, Material, SIDES, flags_for, order_dependent  # noqa: E402

assert "torch" not in sys.modules
sys.stdout.reconfigure(line_buffering=True)

m = Material()
frozen, checker, answers, slots = m.frozen, m.checker, m.answers, m.slots
packets, worlds, side = m.packets, m.worlds, m.side
canonical = m.canonical
kind_of = m.kind_of
NODE_KINDS = ("role_set", "definition", "context", "parts", "edge_account", "reach", "correspondence", "analogy")
# exhaustive renaming for the cheap kinds; one non-identity renaming for the two kinds whose rule is
# defined by exhaustive bijection enumeration (their value is a world id / a bijection set, which is
# invariant as a set by construction -- the sampled check is a guard, the argument is analytic).
SAMPLED = ("analogy", "correspondence")

print()
print("MATERIAL")
print("  records held/trained/excluded", len(m.held), len(m.trained), len(m.excluded))
print("  eligible", len(m.eligible), "shortcut-removed", len(m.shortcut_hit))
print("  eligible by kind", dict(sorted(Counter(kind_of[q] for q in m.eligible).items())))

print()
print("PART A -- the facts that make some permutation claims vacuous")
print("  (1) world vector g_w = MEAN of the final node states (DESIGN_DRAFT_v0.1 section 2.2). A mean over")
print("      nodes is invariant under any renaming of the nodes, so every world-choice head (definition")
print("      kind_ref/function_ref, context setting_ref, analogy world_id) is ORDER-BLIND BY CONSTRUCTION.")
print("  (2) each node head emits one logit per node, indexed by the node's position in the sorted-ref node")
print("      tensor, which IS the public alias N0..N9 (slots.py:55-60). So node outputs are equivariant by")
print("      wiring; an equivariance test tests the plumbing, not the learning.")
print("  (3) the shared decoder breaks ties by symbol order (slots.py:293: 'argmax over each slot's declared")
print("      symbol order; first wins exact ties'), so equal logits always emit the first declared symbol.")


print()
print("PART B -- is the private answer name-blind? (renaming the focus world's node refs, then re-deriving)")
print("  exhaustive renaming for role_set/definition/context/parts/edge_account/reach, one renaming for")
print("  analogy/correspondence; scored with the private rule functions because the public validator rebuilds")
print("  node refs positionally (source.py:254 TYPED_SOURCE_WORLD_RECONSTRUCTION), so no free renaming exists")
print("  in the public model -- which is itself the reason a pointer machine cannot see a name.")
dep_by_record = order_dependent(m)
order_dependent_counts = Counter()
kind_total = Counter()
for row in frozen["registry"]:
    rid = row["record_id"]
    if rid in m.excluded_set:
        continue
    kind = row["query"]["kind"]
    kind_total[(side[rid], kind)] += 1
    order_dependent_counts[(side[rid], kind)] += bool(dep_by_record[rid])
print("  records whose private answer is NOT invariant under renaming (a name-blind machine cannot know it):")
for s in ("held", "trained"):
    for kind in NODE_KINDS:
        if kind_total[(s, kind)]:
            print("    %-8s %-14s %d/%d" % (s, kind, order_dependent_counts[(s, kind)], kind_total[(s, kind)]))

print()
print("PART C -- which held-back questions the renaming dependence removes")
dep_questions = sorted(q for q, records in m.held_questions.items()
                       if any(dep_by_record.get(r, False) for r in records))
print("  all held-back questions affected", len(dep_questions), "of", len(m.held_questions),
      dict(sorted(Counter(kind_of[q] for q in dep_questions).items())))
elig_dep = sorted(q for q in dep_questions if q in m.eligible_set)
print("  ELIGIBLE held-back questions affected", len(elig_dep), "of", len(m.eligible),
      dict(sorted(Counter(kind_of[q] for q in elig_dep).items())))
print("  eligible question ids", elig_dep)
print("  held-back question ids affected (all)", dep_questions)
print()
print("PART D -- VACUOUS: checks and reported numbers that cannot fail, with the reason")
VACUOUS = (
    ("node-relabelling invariance of any WORLD-level output (definition kind_ref/function_ref, context "
     "setting_ref, analogy world_id) offered as evidence about learning",
     "g_w is a MEAN over node states, so those logits are identical for every renaming; a pass proves nothing."),
    ("node-relabelling equivariance of the node heads offered as evidence (draft S9)",
     "the readout index is the node's sorted-ref position, so equivariance is the wiring. Keep as an "
     "engineering test only, which is what the draft's section 5 already says."),
    ("any 'the assembled answer is unchanged when node refs are shuffled' metric",
     "for every kind where Part B shows the private answer is name-blind, such a metric can only pass."),
    ("a relabelling-invariance claim IF the optional rank feature (DG3) is adopted",
     "rank IS the alphabetical position of the hidden ref, so the machine stops being permutation-equivariant; "
     "the vacuity law no longer applies to it and the claim must be withdrawn, not merely reported."),
    ("the checkpoint probe accuracy as a transfer measure",
     "the probe reads node vectors and never a position, so its value is order-invariant by construction."),
    ("I3 as written ('initial model identity re-derives from the seed')",
     "the pure-Python reader cannot run torch, so it collapses into comparing the job with itself (pipeline "
     "review DG4/V3); vacuous unless it becomes DG4's in-job check list."),
    ("the registered secondary flag RELATIONAL_TRANSFER as a transfer measure, unless the removals of "
     "section REQUIRED_REMOVALS are applied first",
     "with the flag-solvable relational questions still inside it, the flag is satisfied by the same "
     "flag-copying that FP1 identified."),
)
for name, why in VACUOUS:
    print("  - %s" % name)
    print("      why: %s" % why)

print()
print("PART E -- REQUIRED permutation tests (engineering only; none is learning evidence)")
REQUIRED = (
    "E1 no-alias-channel: rename every node ref in every world and assert the pointer input tensors are "
    "byte-identical (the reader must never read node['ref'] except through the registered rank feature).",
    "E2 wiring: permute a world's node rows and assert the node-head logits permute by exactly that "
    "permutation while the world vector g_w stays bit-identical.",
    "E3 symbol-row alignment: assert the node tensor row order is the order the reader built and that slot "
    "symbol order still maps row i to alias N<i> (slots.py:88, 101, 103, 107).",
    "E4 rank feature (only if DG3 is resolved by adding rank): assert every rank is the sorted-ref position, "
    "assert rank is the ONLY order-derived feature, and register that the section 5 vacuity paragraph no "
    "longer applies to this machine.",
    "E5 answer-side precondition: the frozen removal test must carry the per-record list from Part B/C above; "
    "a question whose answer is not name-blind cannot be in the gate population.",
)
for one in REQUIRED:
    print("  - %s" % one)
