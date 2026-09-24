"""HSET-2 sealed stage: the improved Helm test at 5 and 6 nodes (Claude, temporary builder while Codex is away).

Label: CLAUDE_BUILT_CLAUDE_CHECKED. Implements `../EVALUATION_DESIGN_v0_4.md` with its Amendment A1 (d840ea02), plus
the builder's PROPOSED Amendment A2 (`REVIEW_HSET2_BUILD_20260924.md`): five more registered bars, each a no-learning
rule that two reviewers showed could pass a claim. A2 only adds bars; the designer or owner must accept it (or choose
the other option each finding names) before the HSET-2 salt is made.
Also conforms to Codex's PROPOSED Amendment A2 (statistical policy; EVALUATION_DESIGN_v0_4.md at f287f965 on Codex's
branch, and its STATISTICAL_POLICY.json): A2.1 complete finite families (FIXED_POSITION_1..7, STATUS_BY_COUNT_0..8,
every member a bar; nothing tuned on TEST); A2.2 the degree-group and shared-shape-component views beside the original
cluster calculation (labelled CONDITIONAL_CLUSTER_DIAGNOSTIC); A2.4 the feasibility table. And two switches for the
design owner: REGISTER_FRONTIER_FALLBACK (finding V-1, decision D1) and REGISTER_FLAGS_TIEBREAK_GUESS (note N1), both
registered by default. Two different texts are called "A2": this docstring says "Codex A2" for the statistical policy.
Choices the design leaves open are written in `BUILDER_REPORT_HSET2.md` ("Choices where the design is silent").
Non-neural: no model is loaded, nothing is trained, no forward pass.

RUN ONLY ON AWS, by the coordinator, with the real salts:
    python -B hset2_build.py --package-root <CNCM tree at 785c9bd1> \
        --salt-file-hset1a <HSET-1A salt.hex> --salt-file-hset2 <HSET-2 salt.hex> \
        --expect-test5-shapes-digest <HSET-1A public test_shapes_digest> \
        --out-public DIR --out-sealed DIR [--processes N]
Throwaway mode (tests, smoke): no salt file is read; both salts are derived from a public string, so a throwaway
run can never reproduce the sealed TEST. Its files are named THROWAWAY_* and every cell's role is THROWAWAY_NOT_DEV
(its 5-node 'DEV' split is random, so it holds real TEST_NEW_5 and WITHHELD_5 classes); neither output folder may be
inside a git work tree:
    python -B hset2_build.py --package-root ... --throwaway-seed STRING --out-public DIR --out-sealed DIR \
        [--processes N] [--limit-foci K] [--remeasure-trained-states]
In real mode any uncaught exception's traceback goes ONLY to --out-sealed; the public log gets its type only.

What it builds (design sections in brackets):
  5 nodes  TEST_NEW_5 and DEV_NEW_5 by `hset1a_build.split_five` with the HSET-1A salt (never re-drawn) [s3];
           WITHHELD_5 = every class not DEV_NEW_5, not TEST_NEW_5, not PUBLIC_EXCLUDED, asserted [s3, M11]
  6 nodes  the stage-0 sides, recomputed and required byte-identical to the committed stage-0 files [A1 D1];
           TEST_NEW_6 = 60 TEST-side foci from the MIX sampler with the HSET-2 salt; WITHHELD_6 the rest [s3]
  cells    TEST_NEW_6 and DEV_NEW_6: REACH_FIRST_DIRECT, REACH_BFS [s5.1], ANALOGY [s5.2], CORRESPONDENCE [s5.3],
           PARTS and EDGE_ACCOUNT (diagnostic) [s1]; TEST_NEW_5/CORRESPONDENCE with the widened foci [A1 D2];
           DEV_NEW_5/CORRESPONDENCE and DEV_NEW_5/ANALOGY_RELAXED (feedback only) [s5.4]
  checks   every packet: the frozen packet validator, the larger-question route (LARGER), slots v2, Helm's input
           reader (`pointer_inputs.read_packet`), checker v2's gold, an independent gold (reach rules re-implemented;
           the D-1 oracle's canonical form and its method-M2 isomorphism enumeration), every registered comparator
           graded by checker v2 and cross-checked by direct comparison [s6]
  printed  everything s7 lists before any model is read, plus can_carry_a_claim per cell from the floor [s7, s9];
           Codex A2.4's feasibility table (clusters, degree groups, shared-shape components, W of every bar in every
           view, the A2.4 floors, the exact conditional sign-power grid), counts only, labelled THROWAWAY in throwaway
           mode; the claim REPAIR_IMPROVES_ANALOGY_6 with its floors (Codex A2.3)

Custody [s8]: TEST and WITHHELD items, answers, shapes and per-cluster results go ONLY to --out-sealed, which must not
be inside a git work tree. Public outputs carry TEST numbers only as totals and list digests. No per-item digest over an
answer is published.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import concurrent.futures.process
import hashlib
import json
import math
import multiprocessing
import os
import pathlib
import platform
import random
import sys
import time
from copy import deepcopy
from fractions import Fraction

HERE =pathlib.Path(__file__).resolve().parent
DESIGN_DIR = HERE.parent
HSET1A_DIR = DESIGN_DIR / "hset1a"
ORACLE_DIR = DESIGN_DIR / "d1_acceptance"

LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
SCHEMA_SUMMARY = "claude.hset2-build-summary/0.3"
DESIGN_BASIS = ("EVALUATION_DESIGN_v0_4.md + Amendment A1 (d840ea02) + the builder's PROPOSED Amendment A2 "
                "(hset2/REVIEW_HSET2_BUILD_20260924.md; the designer or owner must accept it before the salt is made) "
                "+ conformance to Codex's PROPOSED Amendment A2 statistical policy (EVALUATION_DESIGN_v0_4.md and "
                "STATISTICAL_POLICY.json at f287f965, branch codex/helm-controlled-prelaunch-20260924): A2.1 families, "
                "A2.2 views, A2.4 feasibility table; switches REGISTER_FRONTIER_FALLBACK and "
                "REGISTER_FLAGS_TIEBREAK_GUESS (both registered)")
# ---- pins, committed before any build
HSET1A_SALT_SHA256 = "33f9d350700470cc968597a525f1c50ae0598d11e99f8604463a730fe0909754"   # BUILD_SPEC_v0_1.md s5
# The coordinator makes the HSET-2 salt (32 random bytes, 64 hex characters) and commits its sha256 HERE before the
# build (design s3 step 6 and s9 step 2). While this is None the build refuses real mode.
HSET2_SALT_SHA256 = None
SOURCE_COMMIT = "785c9bd10f1416deb95f9c30aacb43124134fe45"     # claude/helm-builder-continuation-20260923
CHECKER_V2_PROFILE_ANCHOR = "b0e565314a91083f8c5559ce1be16fd667e82a52d7dd224de88440bdb0709075"   # D-1 ACCEPTED
SLOTS_V2_PROFILE_ANCHOR = "3f384e6053036c5eecd0464d32101fe773edf64ecb9e0481af92e80494aeb453"     # D-1 ACCEPTED
FROZEN_CHECKER_PROFILE_ANCHOR = "2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81"
BANK_DIGEST_ANCHOR = "0f563762a70e67513ca3e6996d988afd4421dd90fe63e1a04942a31a79e9c388"
GATES_PROGRAM = "records/typed_pointer_001/evaluate_gates.py"
GATES_PROGRAM_LF_SHA256 = "d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d"    # A1 D4
TYPED_TEACHING_FILES = ("__init__.py", "answers.py", "answers_v2.py", "checker.py", "checker_v2.py", "course.py",
                        "course_plan.py", "focal.py", "input_frames.py", "matched_contract.py", "pointer_contract.py",
                        "pointer_inputs.py", "pointer_learner.py", "practice_contract.py", "slots.py", "slots_v2.py",
                        "source.py", "tokenization.py", "worker_contract.py")
EVAL_PATH_FILES = ("__init__.py", "larger_question_scope.py", "larger_question_fixtures.py",
                   "fixtures/larger_question_fixtures_v0_1.json")

ALPHA = 0.01
MIN_CLUSTERS = 10
FOCI = 60
POOL_TOTAL_SECONDS = 3600
THROWAWAY_PREFIX = "HSET-2-THROWAWAY-SALT|"
SPLITS_SECRET = ("TEST_NEW_6", "TEST_NEW_5")
SPLITS_PUBLIC = ("DEV_NEW_6", "DEV_NEW_5")

# ---- comparators (design s6). Every one is a bar of its kind's claims, except as each claim says.
# The bars marked A2 are the builder's PROPOSED Amendment A2 (REVIEW_HSET2_BUILD_20260924.md, findings F1 and F2):
# each is a no-learning rule that passed a claim in 6 of 6 throwaway salts while it was not registered. Adding a bar
# only makes a claim harder to pass. The designer or owner must accept A2 (or choose the other option each finding
# names) BEFORE the HSET-2 salt is made; adding a bar after the sealed build prints W would be a post-hoc change.
# ---- the design owner's two switches (the fresh verification of 1520e17c: finding V-1, decision D1; note N1). Each
# defaults to REGISTERED, so the default only adds bars. D1 (a) keep = True. D1 (b) (declare REACH_3_STEP_TRANSFER_6
# NOT_TESTABLE or rename it) and D1 (c) (rebalance the reach cell) are design changes that need their own amendment;
# setting a switch to False is recorded in `registered_comparators()` and its digest, and the rule's W is still printed
# as a diagnostic, so turning a bar off can never be hidden.
REGISTER_FRONTIER_FALLBACK = True       # V-1: FRONTIER_FALLBACK is a bar of both reach claims
REGISTER_FLAGS_TIEBREAK_GUESS = True    # N1: FLAGS_TIEBREAK_GUESS_THEN_CHECK is an analogy bar
THREE_HOP = "THREE_HOP_FIRST_CHILD"
SINGLE_ROOT = "SINGLE_ROOT_FALLBACK"                                   # A2 (F2): two-hop, then a root-count fallback
SINGLE_ROOT_THREE_HOP = "SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP"        # A2 (F2): three-hop, then the same fallback
FRONTIER = "FRONTIER_FALLBACK"                                        # V-1: two-hop, then a 2-step-frontier fallback
BUILT_ON_THREE_HOP = (THREE_HOP, SINGLE_ROOT_THREE_HOP)               # not bars of REACH_3_STEP_TRANSFER_6
FLAGS_TIEBREAK = "FLAGS_TIEBREAK_GUESS_THEN_CHECK"                   # N1: degree sort, ties by declared flags, then rank
# Codex A2.1 (PROPOSED, f287f965): complete finite families, every member a registered bar, nothing tuned on TEST.
FIXED_POSITIONS = tuple("FIXED_POSITION_%d" % j for j in range(1, 8))  # the j-th non-focus alias, numeric alias order
STATUS_BY_COUNT_M = tuple(range(0, 9))
STATUS_BY_COUNT_FAMILY = tuple("STATUS_BY_COUNT_%d" % m for m in STATUS_BY_COUNT_M)
# The pre-A2 tuned bar BEST_FIXED_POSITION chose one displayed alias W0..W7 (focus included) at its best value on the
# cell. Its whole table is kept, untuned, as eight registered bars, so no bar is dropped (the tuned choice was always
# one of them). STATUS_BY_COUNT's old table is exactly STATUS_BY_COUNT_0..8 above.
FIXED_ALIASES = tuple("FIXED_ALIAS_W%d" % k for k in range(8))
ANALOGY_BASE_COMPARATORS = (("ALWAYS_NO_MATCH", "FIRST_CANDIDATE", "NODE_EDGE_COUNT_MATCH", "DEGREE_MULTISET_MATCH",
                             "FLAG_ANCHOR") + FIXED_POSITIONS + FIXED_ALIASES + ("CANDIDATE_ONLY_NOVELTY",)
                            + STATUS_BY_COUNT_FAMILY + ("OTHER_DOMAIN_ONLY",
                                                        # A2 (F1): one guess per candidate
                                                        "DEGREE_GUESS_THEN_CHECK", "WHOLE_ANCHOR_GUESS_THEN_CHECK",
                                                        "FLAG_ANCHOR_GUESS_THEN_CHECK"))


def analogy_comparators():
    """The registered analogy bars: design s6, Codex A2.1's families, the builder's proposed A2, and the flags
    tie-break guess while its switch is on (read at call time, so the switch is one recorded constant)."""
    return ANALOGY_BASE_COMPARATORS + ((FLAGS_TIEBREAK,) if REGISTER_FLAGS_TIEBREAK_GUESS else ())


def analogy_computed_not_registered():
    """Analogy rules computed and printed as diagnostics only (a switched-off bar stays visible)."""
    return () if REGISTER_FLAGS_TIEBREAK_GUESS else (FLAGS_TIEBREAK,)
# The three one-guess rules, the same in both bank kinds: how many declared participants are mapped first (0: none;
# 1: the declared whole; 3: the whole and both participants), then the rest by (in-degree, out-degree, rank).
GUESS_ANCHORS = {"DEGREE_GUESS_THEN_CHECK": 0, "WHOLE_ANCHOR_GUESS_THEN_CHECK": 1, "FLAG_ANCHOR_GUESS_THEN_CHECK": 3}
# Printed diagnostics only, never bars (Codex A2.1): the old tuned choices, re-derived from the families above.
TUNED_DIAGNOSTIC_FAMILIES = {"BEST_FIXED_POSITION": FIXED_ALIASES, "BEST_FIXED_NON_FOCUS_POSITION": FIXED_POSITIONS,
                             "BEST_STATUS_BY_COUNT": STATUS_BY_COUNT_FAMILY}
CORRESPONDENCE_COMPARATORS = ("ALWAYS_NO_MATCH", "IDENTITY_BY_RANK", "DEGREE_SORTED", "DEGREE_GUESS_THEN_CHECK",
                              "FLAG_ANCHOR_GUESS_THEN_CHECK",
                              "WHOLE_ANCHOR_GUESS_THEN_CHECK")      # A2: completes the same one-guess family
A2_BARS = {"analogy": ("DEGREE_GUESS_THEN_CHECK", "WHOLE_ANCHOR_GUESS_THEN_CHECK", "FLAG_ANCHOR_GUESS_THEN_CHECK"),
           "correspondence": ("WHOLE_ANCHOR_GUESS_THEN_CHECK",),
           "reach": (SINGLE_ROOT, SINGLE_ROOT_THREE_HOP)}
# Codex A2.2 / A2.4 (PROPOSED): the two added views and the confirmatory analogy floors
ORIGINAL_VIEW_LABEL = "CONDITIONAL_CLUSTER_DIAGNOSTIC"
VIEWS = ("original_cluster", "degree_group", "shared_shape_component")
A2_4_MIN_UNITS = 10
SIGN_POWER_Q = ((3, 5), (7, 10), (4, 5), (1, 1))                      # q = 0.60, 0.70, 0.80, 1.00, exact
# Measured 2026-09-23 by this builder: the frozen checker over the frozen public course's registry main queries (70
# analogy and 88 correspondence records). NO_MATCH was never trained for either kind (review m4). Re-measured by the
# sealed build, which fails closed on any difference.
TRAINED_BANK_STATES = {"analogy": {"MATCH": 70}, "correspondence": {"MAPPING": 88}}
SCOPE_SENTENCE = ("At 6 nodes or fewer this test can show that the model does better than every registered no-learning "
                  "rule, including degree counting. It cannot tell full structural comparison from one hop of "
                  "neighbour-degree matching.")
DECLARED_NOT_TESTABLE = {
    "ANALOGY_BEYOND_DEGREE_5": "design s1: the whole 5-node universe has only 6 degree groups with 4 or more members",
    "REACH_3_STEP_TRANSFER_5": "design s1: HSET-1A measured W = 2 on TEST_NEW_5",
    "REACH_4_STEP_TRANSFER_5": "design s1: HSET-1A measured W = 2 on TEST_NEW_5"}


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _paths(package_root):
    sys.dont_write_bytecode = True
    for p in (str(ORACLE_DIR), str(HSET1A_DIR), str(HERE), str(pathlib.Path(package_root) / "research" / "CAS_META_2_COMPOSITION")):
        if p not in sys.path:
            sys.path.insert(0, p)


def reach_comparators():
    """The registered reach bars (design s6, the builder's proposed A2, and FRONTIER_FALLBACK while its switch is on)."""
    import hset1a_build as A
    return (tuple(A.COMPARATORS["reach"]) + (THREE_HOP, SINGLE_ROOT, SINGLE_ROOT_THREE_HOP)
            + ((FRONTIER,) if REGISTER_FRONTIER_FALLBACK else ()))


def reach_computed_not_registered():
    """Reach rules computed and printed as diagnostics only (a switched-off bar stays visible)."""
    return () if REGISTER_FRONTIER_FALLBACK else (FRONTIER,)


def registered_comparators():
    """The whole bar set, printed with its digest in every summary, so anyone can see which bars were fixed before the
    salt was made (design s6 and s7; the proposed additions are listed separately, with where each came from)."""
    reach = list(reach_comparators())
    return {"reach": {"REACH_3_STEP_TRANSFER_6": [x for x in reach if x not in BUILT_ON_THREE_HOP],
                      "REACH_4_STEP_TRANSFER_6": reach},
            "analogy": list(analogy_comparators()),
            "correspondence": list(CORRESPONDENCE_COMPARATORS),
            "added_by_proposed_amendment_A2": {k: list(v) for k, v in sorted(A2_BARS.items())},
            "added_by_codex_A2_1_complete_families": {"analogy": list(FIXED_POSITIONS + STATUS_BY_COUNT_FAMILY)},
            "pre_A2_tuned_bars_completed_untuned": {"BEST_FIXED_POSITION": list(FIXED_ALIASES),
                                                    "STATUS_BY_COUNT": list(STATUS_BY_COUNT_FAMILY)},
            "tuned_on_the_cell_diagnostic_only_never_a_bar": sorted(TUNED_DIAGNOSTIC_FAMILIES),
            "design_owner_switches": {"REGISTER_FRONTIER_FALLBACK": REGISTER_FRONTIER_FALLBACK,
                                      "REGISTER_FLAGS_TIEBREAK_GUESS": REGISTER_FLAGS_TIEBREAK_GUESS},
            "added_by_switches": {"reach": [FRONTIER] if REGISTER_FRONTIER_FALLBACK else [],
                                  "analogy": [FLAGS_TIEBREAK] if REGISTER_FLAGS_TIEBREAK_GUESS else []},
            "computed_not_registered_printed_only": {"reach": list(reach_computed_not_registered()),
                                                     "analogy": list(analogy_computed_not_registered())}}


# ============================================================================ plain graphs (public helpers)
def world_graph(world):
    """(n, sorted edges) of a built world over rank positions (the sorted node refs), plus the refs."""
    refs = sorted(node["ref"] for node in world["nodes"])
    index = {ref: i for i, ref in enumerate(refs)}
    edges = tuple(sorted((index[e["source"]], index[e["target"]]) for e in world["contains"]))
    return len(refs), edges, refs


def degrees(n, edges):
    ind, outd = [0] * n, [0] * n
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    return ind, outd


def three_hop_payload(world, query):
    """THREE_HOP_FIRST_CHILD (design s6, review M4), read off the packet's focus world like every reach comparator.

    first-child rule: DIRECT if direct; else VIA the lowest-rank child of the whole with a path of at most 2 steps to
    the part; else ABSENT. BFS rule (its BFS variant): DIRECT if direct; else VIA the lowest-rank child with an
    arrow to the part (two-hop); else VIA the first node at 2 steps (BFS order, neighbours by rank) with an arrow to
    the part; else ABSENT. So it is TWO_HOP_FIRST_CHILD one step deeper, and never weaker than it."""
    nodes = sorted(n["ref"] for n in world["nodes"])
    rank = {ref: i for i, ref in enumerate(nodes)}
    out = collections.defaultdict(list)
    for e in world["contains"]:
        out[e["source"]].append(e["target"])
    for k in out:
        out[k].sort(key=rank.get)
    whole, part = query["arguments"]["whole"], query["arguments"]["part"]
    kids = out[whole]
    if part in kids:
        return {"state": "DIRECT", "via": None}
    if query["rule"] == "first_direct_constituent_lexical_v1":
        for c in kids:
            if part in out[c] or any(part in out[g] for g in out[c]):
                return {"state": "VIA", "via": c}
        return {"state": "ABSENT", "via": None}
    two = [c for c in kids if part in out[c]]
    if two:
        return {"state": "VIA", "via": two[0]}
    seen, level2 = {whole, *kids}, []
    for c in kids:
        for g in out[c]:
            if g not in seen:
                seen.add(g)
                level2.append(g)
    three = [g for g in level2 if part in out[g]]
    return {"state": "VIA", "via": three[0]} if three else {"state": "ABSENT", "via": None}


def single_root_fallback_payload(world, query, base):
    """SINGLE_ROOT_FALLBACK (A2, review F2), read off the packet's focus world. It follows no path longer than `base`.

    Take the `base` answer (the registered two-hop answer, or the three-hop answer for the ..._AFTER_THREE_HOP form).
    If it is ABSENT and the world has exactly one root (one node of in-degree 0, read off the joint degree list), a
    whole there reaches every node, so answer VIA: the lowest-rank child of the whole (first-child rule), or the
    lowest-rank parent of the part (BFS rule). Otherwise keep ABSENT."""
    if base["state"] != "ABSENT":
        return dict(base)
    nodes = sorted(n["ref"] for n in world["nodes"])
    rank = {ref: i for i, ref in enumerate(nodes)}
    targets = {e["target"] for e in world["contains"]}
    if sum(1 for ref in nodes if ref not in targets) != 1:
        return {"state": "ABSENT", "via": None}
    whole, part = query["arguments"]["whole"], query["arguments"]["part"]
    if query["rule"] == "first_direct_constituent_lexical_v1":
        near = sorted((e["target"] for e in world["contains"] if e["source"] == whole), key=rank.get)
    else:
        near = sorted((e["source"] for e in world["contains"] if e["target"] == part), key=rank.get)
    return {"state": "VIA", "via": near[0]} if near else {"state": "ABSENT", "via": None}


def frontier_fallback_payload(world, query, base):
    """FRONTIER_FALLBACK (the fresh verification of 1520e17c, finding V-1, REVIEW section V.3), read off the packet's
    focus world. It never follows an edge more than 2 steps from the whole, and never checks where a third step goes.

    Take the registered two-hop answer (`base`). If it is ABSENT: answer VIA when (i) some node exactly two steps from
    the whole (a child of a child that is not itself a child of the whole) has at least one child, and (ii) the part
    has at least one parent; otherwise ABSENT. The via: first-child rule, the whole's child with the most children
    (ties: lowest rank); BFS rule, among the part's parents that have a parent themselves, the one with the most
    parents (ties: lowest rank). If that via does not exist, ABSENT. (It is the verifier's V4_FRONTIER_MAXOUT.)"""
    if base["state"] != "ABSENT":
        return dict(base)
    nodes = sorted(n["ref"] for n in world["nodes"])
    rank = {ref: i for i, ref in enumerate(nodes)}
    out, inn = collections.defaultdict(list), collections.defaultdict(list)
    for e in world["contains"]:
        out[e["source"]].append(e["target"])
        inn[e["target"]].append(e["source"])
    whole, part = query["arguments"]["whole"], query["arguments"]["part"]
    kids = out[whole]
    level2 = [g for c in kids for g in out[c] if g not in kids and g != whole]
    if not (any(out[g] for g in level2) and inn[part]):
        return {"state": "ABSENT", "via": None}
    if query["rule"] == "first_direct_constituent_lexical_v1":
        pick = max(kids, key=lambda c: (len(out[c]), -rank[c])) if kids else None
    else:
        parents = [p for p in inn[part] if inn[p]]
        pick = max(parents, key=lambda p: (len(inn[p]), -rank[p])) if parents else None
    return {"state": "VIA", "via": pick} if pick is not None else {"state": "ABSENT", "via": None}


def extra_reach_payloads(world, query, hset1a_payloads):
    """The reach comparators design s6, the builder's proposed A2 and finding V-1 add to HSET-1A's eight, each read off
    the packet's focus world. FRONTIER_FALLBACK is always computed; it is a bar only while its switch is on."""
    three = three_hop_payload(world, query)
    two = hset1a_payloads["TWO_HOP_FIRST_CHILD"]
    return {THREE_HOP: three,
            SINGLE_ROOT: single_root_fallback_payload(world, query, two),
            SINGLE_ROOT_THREE_HOP: single_root_fallback_payload(world, query, three),
            FRONTIER: frontier_fallback_payload(world, query, two)}


def one_guess(F, T, anchored):
    """ONE guess of a node map from world F to world T, then ONE check (design s6: one guess, one check, no search).

    The first `anchored` declared participants (0: none; 1: the declared whole; 3: the whole and both participants)
    are mapped in order; the other nodes are paired after sorting both sides by (in-degree, out-degree, rank).
    Returns (frefs, trefs, map over rank positions or None, valid)."""
    fn, fe, frefs = world_graph(F)
    tn, te, trefs = world_graph(T)
    if fn != tn:
        return frefs, trefs, None, False
    fin, fout = degrees(fn, fe)
    tin, tout = degrees(tn, te)
    fidx, tidx = {r: i for i, r in enumerate(frefs)}, {r: i for i, r in enumerate(trefs)}
    m = {fidx[a]: tidx[b] for a, b in zip(F["declarations"]["participants"][:anchored],
                                          T["declarations"]["participants"][:anchored])}
    left = sorted((a for a in range(fn) if a not in m), key=lambda a: (fin[a], fout[a], a))
    right = sorted((b for b in range(tn) if b not in m.values()), key=lambda b: (tin[b], tout[b], b))
    m.update(zip(left, right))
    return frefs, trefs, m, {(m[a], m[b]) for a, b in fe} == set(te)


def flags_tiebreak_guess(F, T):
    """ONE guess, then ONE check (note N1 of the verification of 1520e17c): every node of each world sorted by
    (in-degree, out-degree, declared-flag position, rank), where the flag position is 0 for the declared whole, 1 and
    2 for the other two participants and 3 for any other node; the two sorted lists are paired. No node is anchored.
    Returns whether the guess passes the edge check (False if the node counts differ)."""
    fn, fe, frefs = world_graph(F)
    tn, te, trefs = world_graph(T)
    if fn != tn:
        return False

    def order(W, n, edges, refs):
        ind, outd = degrees(n, edges)
        p = W["declarations"]["participants"]
        flag = {i: (p.index(r) if r in p else 3) for i, r in enumerate(refs)}
        return sorted(range(n), key=lambda a: (ind[a], outd[a], flag[a], a))
    m = dict(zip(order(F, fn, fe, frefs), order(T, tn, te, trefs)))
    return {(m[a], m[b]) for a, b in fe} == set(te)


def analogy_payloads(public, focus_id, trained_shape_keys, canonical_key):
    """Every analogy comparator (design s6, Codex A2.1, the switches), read off the packet: {name: payload}.

    Candidates are the bank worlds other than the focus, in alias order (sorted world_id, as Helm's W aliases: the
    numeric alias index is the position in that sorted list). Every family member is its own entry; nothing is tuned.
    A computed-but-unregistered rule (a switch set to False) is also returned, so its W can be printed."""
    worlds = {w["world_id"]: w for w in public["worlds"]}
    bank = sorted(public["bank"]["world_ids"])
    focus = worlds[focus_id]
    fn, fe, _ = world_graph(focus)
    fdom = focus["declarations"]["domain"]
    fdeg = sorted(zip(*degrees(fn, fe)))

    def info(wid):
        w = worlds[wid]
        n, e, refs = world_graph(w)
        ind, outd = degrees(n, e)
        idx = {r: i for i, r in enumerate(refs)}
        flags = [(ind[idx[r]], outd[idx[r]]) for r in w["declarations"]["participants"]]
        return {"n": n, "edges": len(e), "deg": sorted(zip(ind, outd)), "domain": w["declarations"]["domain"],
                "flags": flags, "shape": (n, e)}
    finfo = info(focus_id)
    cands = [w for w in bank if w != focus_id]
    ci = {w: info(w) for w in cands}
    other = [w for w in cands if ci[w]["domain"] != fdom]
    same_deg_other = [w for w in other if ci[w]["deg"] == fdeg]
    pick = lambda ws: {"world_id": ws[0] if ws else None}              # noqa: E731
    out = {"ALWAYS_NO_MATCH": {"world_id": None},
           "FIRST_CANDIDATE": pick(cands),
           "NODE_EDGE_COUNT_MATCH": pick([w for w in other if ci[w]["n"] == fn and ci[w]["edges"] == len(fe)]),
           "DEGREE_MULTISET_MATCH": pick(same_deg_other),
           "FLAG_ANCHOR": pick([w for w in same_deg_other if ci[w]["flags"] == finfo["flags"]]),
           "CANDIDATE_ONLY_NOVELTY": pick([w for w in other if ci[w]["n"] == fn and (
               ci[w]["n"] > 4 or canonical_key(ci[w]["shape"]) not in trained_shape_keys)]),
           "OTHER_DOMAIN_ONLY": {"world_id": same_deg_other[0] if len(same_deg_other) == 1 else None}}
    # A2 (review F1): the correspondence guess-then-check made once per same-degree other-domain candidate, in alias
    # order; the first candidate whose one guess passes the check, else NO_MATCH
    for name, anchored in GUESS_ANCHORS.items():
        out[name] = pick([w for w in same_deg_other if one_guess(focus, worlds[w], anchored)[3]])
    # N1: the same, with the flags tie-break guess
    out[FLAGS_TIEBREAK] = pick([w for w in same_deg_other if flags_tiebreak_guess(focus, worlds[w])])
    # Codex A2.1: FIXED_POSITION_j = the j-th non-focus candidate (NO_MATCH if the bank has fewer than j); the pre-A2
    # table FIXED_ALIAS_Wk = the k-th displayed alias, focus included (NO_MATCH if absent); STATUS_BY_COUNT_m: E = the
    # same-degree other-domain candidates in alias order; NO_MATCH if E is empty or len(E) < m, else E[0]
    for j, name in enumerate(FIXED_POSITIONS, start=1):
        out[name] = {"world_id": cands[j - 1] if len(cands) >= j else None}
    for k, name in enumerate(FIXED_ALIASES):
        out[name] = {"world_id": bank[k] if len(bank) > k else None}
    for m, name in zip(STATUS_BY_COUNT_M, STATUS_BY_COUNT_FAMILY):
        out[name] = {"world_id": same_deg_other[0] if same_deg_other and len(same_deg_other) >= m else None}
    return out


def correspondence_payloads(public, focus_id, target_id):
    """Every registered correspondence comparator (design s6): one guess at most, and one check at most."""
    worlds = {w["world_id"]: w for w in public["worlds"]}
    F, T = worlds[focus_id], worlds[target_id]
    no = {"status": "NO_MATCH", "pairs": []}
    frefs, trefs, guess, valid = one_guess(F, T, 0)
    out = {"ALWAYS_NO_MATCH": no}
    if guess is None:                                                  # node counts differ
        out.update({name: no for name in CORRESPONDENCE_COMPARATORS})
        return out

    def mapping(m):
        return {"status": "MAPPING", "pairs": [{"source": frefs[a], "target": trefs[m[a]]} for a in range(len(frefs))]}
    out["IDENTITY_BY_RANK"] = mapping({a: a for a in range(len(frefs))})
    out["DEGREE_SORTED"] = mapping(guess)
    for name, anchored in GUESS_ANCHORS.items():                      # the one-guess family (s6, A2)
        _, _, m, ok = one_guess(F, T, anchored)
        out[name] = mapping(m) if ok else no
    return {name: out[name] for name in CORRESPONDENCE_COMPARATORS}


# ============================================================================ worker (one per process)
_W = {}


def _init(package_root):
    _paths(package_root)
    import hset_worlds as hw
    import hset1a_build as A
    import oracle_isomorphism as oracle
    import hset2_stage0_public as S0
    from cas_meta2.typed_teaching import answers, checker_v2, course, pointer_inputs, source
    from eval_paths import larger_question_scope as scope
    _, families = hw.vocabulary(source)
    trained = set()
    for f in families:
        index = {label: i for i, label in enumerate(f["labels"])}
        trained.add(S0.class_key(oracle.canonical_form(len(f["labels"]), [(index[b["source"]], index[b["target"]])
                                                                          for b in f["branches"]])))
    _W.update(hw=hw, A=A, oracle=oracle, S0=S0, source=source, answers=answers, course=course, checker=checker_v2,
              pointer_inputs=pointer_inputs, scope=scope, bank=source.freeze_bank(families), trained_shapes=trained)


def build_multi_packet(item):
    """NEW PACKET CODE (design s5.2, s5.3, m3): a closed packet shaped like `course.model_packet` (0 supports) whose
    public source holds exactly the item's worlds and whose bank holds exactly `item["bank"]` (analogy: the focus plus
    7; correspondence: the target alone)."""
    hw, source, answers, course = _W["hw"], _W["source"], _W["answers"], _W["course"]
    worlds = [hw.world_from_spec(source, spec) for spec in item["worlds"]]
    ids = [w["world_id"] for w in worlds]
    if len(set(ids)) != len(ids):
        raise ValueError("HSET2_DUPLICATE_WORLD_IN_PACKET")
    focus = worlds[item["focus"]]
    bank_worlds = [worlds[i] for i in item["bank"]]
    by_id = {w["world_id"]: w for w in bank_worlds}
    by_id[focus["world_id"]] = focus
    public = {"focus_world_id": focus["world_id"], "worlds": [by_id[k] for k in sorted(by_id)],
              "bank": source._bank_record(bank_worlds)}
    arguments = {"target_world_id": worlds[item["target"]]["world_id"]} if item["kind"] == "correspondence" else None
    query = answers.compile_query(public, kind=item["kind"], rule=None, arguments=arguments, focus_world_id=focus["world_id"])
    body = {"schema": course.PACKET_SCHEMA, "source_digest": source.public_digest(public),
            "source_world_id": focus["world_id"], "query": query, "cue": item["cue"],
            "instruction": course.REQUESTS[item["kind"]], "role_catalog": deepcopy(course.ROLE_CATALOG), "supports": []}
    return {"source": public, "record": {"record_id": "typed-input-" + source.digest(body), **body}}, worlds


def build_packet(item):
    """The exact packet of one item, single-world (reach, parts, edge account: HSET-1A's) or multi-world (new)."""
    if "world" in item:
        packet, _, _ = _W["hw"].packet_from_item(_W["source"], _W["answers"], _W["course"], _W["bank"], item)
        return packet
    return build_multi_packet(item)[0]


def _grade(public, query, payloads, admissible_keys):
    hw, answers, checker = _W["hw"], _W["answers"], _W["checker"]
    distinct, verdicts = {}, {}
    for name, payload in payloads.items():
        key = hw.canon(payload)
        if key not in distinct:
            distinct[key] = bool(checker.check_answer(public, query, answers.make_answer(public, query, payload))["correct"])
        verdicts[name] = distinct[key]
    consistent = all(verdicts[name] == (hw.canon(payloads[name]) in admissible_keys) for name in verdicts)
    return verdicts, consistent, len(distinct)


def _evaluate(item):
    started = time.perf_counter()
    try:
        row = _evaluate_single(item) if "world" in item else _evaluate_multi(item)
    except Exception as error:  # noqa: BLE001 -- reported per item; any error fails the build
        return {"item_id": item["item_id"], "error": "%s: %s" % (type(error).__name__, str(error)[:300])}
    row["evaluation_seconds"] = round(time.perf_counter() - started, 4)
    return row


def _evaluate_single(item):
    hw, A, source, answers, course, checker, scope = (_W[k] for k in ("hw", "A", "source", "answers", "course", "checker", "scope"))
    packet, focus, refs = hw.packet_from_item(source, answers, course, _W["bank"], item)
    course.validate_model_packet(packet)
    route, plan = scope.compile_plan(packet)
    reading = _W["pointer_inputs"].read_packet(packet)
    public, query = packet["source"], packet["record"]["query"]
    rank = hw.ranks(item["world"])
    n, edges = len(item["world"]["labels"]), [tuple(e) for e in item["world"]["edges"]]
    reader_ok = (route == scope.LARGER and reading["record_id"] == packet["record"]["record_id"] == plan["record_id"]
                 and reading["query"]["world_count"] == 1 and reading["focus_world"]["node_count"] == n
                 and reading["query"]["whole"] == (None if item.get("whole") is None else rank[item["whole"]])
                 and reading["query"]["part"] == (None if item.get("part") is None else rank[item["part"]])
                 and max(max(d) for d in hw.degree_multiset(n, edges)) <= 4)
    target = checker.derive_target(public, query)
    admissible = [row["value"] for row in target["admissible_answers"]]
    gold = admissible[0] if len(admissible) == 1 else None
    independent = A._independent_gold(hw, item, refs)
    payloads, aux = A._comparators(item["kind"], focus, query)
    if item["kind"] == "reach":
        payloads.update(extra_reach_payloads(focus, query, payloads))
    verdicts, consistent, graded = _grade(public, query, payloads, {hw.canon(a) for a in admissible})
    flags = {}
    if item["kind"] == "reach" and gold is not None and gold["state"] == "VIA":
        flags = {"GOLD_VIA_IS_PARTICIPANT_2": gold["via"] == aux["p2"],
                 "GOLD_VIA_IS_LOWEST_RANK_CHILD": bool(aux["kids"]) and gold["via"] == aux["kids"][0],
                 "GOLD_VIA_IS_RANK_LAST_CHILD": bool(aux["kids"]) and gold["via"] == aux["kids"][-1]}
    return {"item_id": item["item_id"], "record_id": packet["record"]["record_id"], "query_id": query["query_id"],
            "source_digest": packet["record"]["source_digest"], "packet_sha256": hw.sha(packet), "route": route,
            "plan_digest": plan["plan_digest"], "slot_count": len(plan["slots"]), "reader_ok": reader_ok,
            "node_rank_feature": reading["node_rank_feature"], "admissible_count": len(admissible), "gold": gold,
            "admissible_values": admissible, "expected_admissible_count": 1,
            "independent_gold_agrees": gold is not None and hw.canon(gold) == hw.canon(independent),
            "comparator_scoring_consistent": consistent, "distinct_payloads_graded": graded,
            "comparators": verdicts, "flags": flags}


def _evaluate_multi(item):
    hw, source, oracle, S0, course, checker, scope = (_W[k] for k in ("hw", "source", "oracle", "S0", "course", "checker", "scope"))
    packet, worlds = build_multi_packet(item)
    course.validate_model_packet(packet)
    route, plan = scope.compile_plan(packet)
    reading = _W["pointer_inputs"].read_packet(packet)
    public, query = packet["source"], packet["record"]["query"]
    focus = worlds[item["focus"]]
    fn, fe, frefs = world_graph(focus)
    target_id = worlds[item["target"]]["world_id"] if item["kind"] == "correspondence" else None
    reader_ok = (route == scope.LARGER and reading["record_id"] == packet["record"]["record_id"] == plan["record_id"]
                 and reading["query"]["world_count"] == (len(public["worlds"]) if item["kind"] == "analogy" else 2)
                 and reading["focus_world"]["node_count"] == fn and reading["query"]["target_world_id"] == target_id
                 and len(public["worlds"]) == len(item["worlds"]) and len(public["bank"]["world_ids"]) == len(item["bank"]))
    target = checker.derive_target(public, query)
    admissible = [row["value"] for row in target["admissible_answers"]]
    # ---- the independent gold: the D-1 oracle (method M1 canonical form; method M2 isomorphism enumeration)
    by_id = {w["world_id"]: w for w in public["worlds"]}
    if item["kind"] == "analogy":
        fkey = oracle.canonical_form(fn, fe)
        hits = []
        for wid in sorted(public["bank"]["world_ids"]):
            w = by_id[wid]
            if w["declarations"]["domain"] == focus["declarations"]["domain"]:
                continue
            n, e, _ = world_graph(w)
            if n == fn and len(e) == len(fe) and oracle.canonical_form(n, e) == fkey:
                hits.append({"world_id": wid})
        independent = hits or [{"world_id": None}]
        expected = ([{"world_id": worlds[item["roles"].index("PARTNER")]["world_id"]}] if item["status"] == "MATCH"
                    else [{"world_id": None}])
        payloads = analogy_payloads(public, focus["world_id"], _W["trained_shapes"],
                                    lambda shape: S0.class_key(oracle.canonical_form(*shape)))
    else:
        tw = by_id[target_id]
        tn, te, trefs = world_graph(tw)
        maps = oracle.all_isomorphisms_m2((fn, frozenset(fe)), (tn, frozenset(te)))
        independent = ([{"status": "MAPPING", "pairs": [{"source": frefs[a], "target": trefs[m[a]]} for a in range(fn)]}
                        for m in maps] or [{"status": "NO_MATCH", "pairs": []}])
        expected = None
        payloads = correspondence_payloads(public, focus["world_id"], target_id)
    admissible_keys = sorted(hw.canon(a) for a in admissible)
    independent_agrees = admissible_keys == sorted(hw.canon(a) for a in independent) and (
        expected is None or admissible_keys == sorted(hw.canon(a) for a in expected))
    status_agrees = (item["status"] in ("MATCH", "MAPPING")) == (admissible[0].get("world_id") is not None
                                                                   if item["kind"] == "analogy"
                                                                   else admissible[0]["status"] == "MAPPING")
    # every comparator, family member and switched-off rule is graded by checker v2 and checked against direct
    # comparison (Codex A2.1: duplicate predictions share one calculation, every rule ID keeps its own verdict)
    verdicts, consistent, graded = _grade(public, query, payloads, set(admissible_keys))
    sorted_ids = sorted(w["world_id"] for w in public["worlds"])
    role_alias = {}
    for role in ("PARTNER", "DISTRACTOR"):
        if role in item["roles"]:
            role_alias[role] = "W%d" % sorted_ids.index(worlds[item["roles"].index(role)]["world_id"])
    if item["kind"] == "correspondence":
        role_alias["TARGET"] = "W%d" % sorted_ids.index(target_id)
    return {"item_id": item["item_id"], "record_id": packet["record"]["record_id"], "query_id": query["query_id"],
            "source_digest": packet["record"]["source_digest"], "packet_sha256": hw.sha(packet), "route": route,
            "plan_digest": plan["plan_digest"], "slot_count": len(plan["slots"]), "reader_ok": reader_ok,
            "node_rank_feature": reading["node_rank_feature"], "admissible_count": len(admissible),
            "gold": admissible[0] if len(admissible) == 1 else None, "admissible_values": admissible,
            "expected_admissible_count": len(independent),
            "independent_gold_agrees": independent_agrees and status_agrees,
            "comparator_scoring_consistent": consistent, "distinct_payloads_graded": graded,
            "comparators": {name: verdicts[name] for name in payloads},
            "role_alias": role_alias, "world_ids": sorted_ids}


# ============================================================================ building items (main process)
def world_pair(hw, vocab, rng, shape, domain):
    """One world, two presentations (design s4, s5): a fresh declared whole (a uniformly random root), two fresh other
    participants (uniformly random other nodes), a fresh kind word from the world's domain, node labels from the
    domain's trained `declaration_labels`; presentation 2 permutes the same labels so the rank order differs."""
    n, edges = shape
    v = vocab[domain]
    whole = rng.choice(hw.roots(n, list(edges)))
    p2, p3 = rng.sample([x for x in range(n) if x != whole], 2)
    kind = rng.choice(v["kinds"])
    label_set = rng.sample(v["declaration_labels"], n)

    def signature(assign):
        order = sorted(assign)
        rk = {i: order.index(assign[i]) for i in range(n)}
        return (tuple(sorted((rk[a], rk[b]) for a, b in edges)), rk[whole], rk[p2], rk[p3])
    first = rng.sample(label_set, n)
    for _ in range(200):
        second = rng.sample(label_set, n)
        if signature(second) != signature(first):
            break
    else:
        raise RuntimeError("NO_DISTINCT_SECOND_PRESENTATION")
    specs = [{"labels": list(assign), "edges": [list(e) for e in edges], "primary": [whole, p2, p3],
              "declarations": {"domain": domain, "kind": kind, "setting": v["setting"],
                               "function": v["function_template"] % {"whole": assign[whole], "child": assign[p2]}}}
             for assign in (first, second)]
    return specs, {"whole": whole, "p2": p2, "p3": p3}


def draw_item_worlds(hw, vocab, source, rng, members):
    """Fresh worlds for one item. Redraws (from the same seeded stream) any world whose id would repeat another's."""
    from hset2_stage0_public import key_shape
    pairs = [world_pair(hw, vocab, rng, key_shape(cls), dom) for _, cls, dom in members]
    for _ in range(50):
        ok = True
        for k in (0, 1):
            ids = [hw.world_from_spec(source, p[0][k])["world_id"] for p in pairs]
            seen = set()
            for i, wid in enumerate(ids):
                if wid in seen:
                    pairs[i] = world_pair(hw, vocab, rng, key_shape(members[i][1]), members[i][2])
                    ok = False
                seen.add(wid)
        if ok:
            return pairs
    raise RuntimeError("WORLD_ID_COLLISIONS_PERSIST")


def flags_on_image(aut, f, g):
    """Do world g's flags fall on the images of world f's flags? (same class, same canonical edge numbering)."""
    return {"whole": any(s[f["whole"]] == g["whole"] for s in aut),
            "all_three": any(s[f["whole"]] == g["whole"] and s[f["p2"]] == g["p2"] and s[f["p3"]] == g["p3"] for s in aut)}


def analogy_items(ctx, split, cell, seed, foci, partners_of, filler_pool_of, with_distractor, relaxed=False):
    """Design s5.2 (or the named relaxed recipe of s5.4 at 5 nodes). Exactly 2 items per focus: MATCH and its
    NO_MATCH twin, each with an 8-world bank (the focus plus 7), each in 2 presentations."""
    hw, vocab, source, S0 = ctx["hw"], ctx["vocab"], ctx["source"], ctx["S0"]
    domains = hw.TRAINING_DOMAINS
    items, clusters = [], []
    for focus in foci:
        rng = random.Random(hw.keyed_int(seed, "analogy-bank", split, focus))
        decoys = rng.sample(sorted(partners_of(focus)), 4)
        wd = focus in with_distractor
        pool = sorted(set(filler_pool_of(focus)) - set(decoys) - {focus})
        fillers = rng.sample(pool, 2 if wd else 3)
        f_dom = rng.choice(domains)
        others = [d for d in domains if d != f_dom]
        partner_dom = rng.choice(others)
        decoy_doms = [rng.choice(others) for _ in range(4)]
        filler_doms = [rng.choice(domains) for _ in fillers]
        slots = ([("DISTRACTOR", focus, f_dom)] if wd else []) + [("FILLER", c, d) for c, d in zip(fillers, filler_doms)]
        common = [("DECOY", decoys[i], decoy_doms[i]) for i in range(3)] + slots
        members = {"MATCH": [("FOCUS", focus, f_dom), ("PARTNER", focus, partner_dom)] + common,
                   "NO_MATCH": [("FOCUS", focus, f_dom), ("DECOY", decoys[3], decoy_doms[3])] + common}
        cid = "%s|%s|%s" % (split, cell, hw.sha(focus)[:16])
        n, edges = S0.key_shape(focus)
        aut = ctx["aut"](focus)
        meta = {"cluster_id": cid, "split": split, "cell": cell, "shape_key": focus, "n": n, "edge_count": len(edges),
                "group_key": S0.group_key((n, edges)), "with_distractor": wd, "decoys": decoys, "fillers": fillers,
                "focus_domain": f_dom, "relaxed_recipe": relaxed, "profiles": {},
                "same_degree_other_domain_non_isomorphic_decoys": {}, "flag_image": {}, "items": [],
                # Codex A2.2: every canonical class in every packet role (focus, partner, decoy, distractor, filler)
                # of both twins; both presentations carry the same classes. Custodian-only for TEST (sealed tables)
                "role_classes": sorted({cls for rows in members.values() for _, cls, _ in rows})}
        for status in ("MATCH", "NO_MATCH"):
            rows = members[status]
            irng = random.Random(hw.keyed_int(seed, "analogy-item", split, focus, status))
            pairs = draw_item_worlds(hw, vocab, source, irng, rows)
            fflags = pairs[0][1]
            image = {}
            for role in ("PARTNER", "DISTRACTOR"):
                if any(r[0] == role for r in rows):
                    image[role] = flags_on_image(aut, fflags, pairs[[r[0] for r in rows].index(role)][1])
            meta["flag_image"][status] = image
            meta["profiles"][status] = bank_profile(S0, rows)
            meta["same_degree_other_domain_non_isomorphic_decoys"][status] = same_degree_decoys(S0, rows)
            for k in (0, 1):
                iid = "%s|%s|pres%d" % (cid, status, k)
                items.append({"item_id": iid, "cluster_id": cid, "split": split, "cell": cell, "presentation": k,
                              "kind": "analogy", "rule": None, "cue": "CUBE_FACE_3", "status": status, "focus": 0,
                              "target": None, "bank": list(range(len(rows))), "roles": [r[0] for r in rows],
                              "classes": [r[1] for r in rows], "domains": [r[2] for r in rows],
                              "worlds": [p[0][k] for p in pairs], "flags": [p[1] for p in pairs]})
                meta["items"].append(iid)
        if not relaxed:
            if meta["profiles"]["MATCH"] != meta["profiles"]["NO_MATCH"]:
                raise AssertionError("TWIN_PROFILE_MISMATCH")
            for status in ("MATCH", "NO_MATCH"):
                if meta["same_degree_other_domain_non_isomorphic_decoys"][status] < 3:
                    raise AssertionError("FEWER_THAN_3_SAME_DEGREE_OTHER_DOMAIN_DECOYS")
        meta["profiles_equal"] = meta["profiles"]["MATCH"] == meta["profiles"]["NO_MATCH"]
        meta["diagnostic_pairs"] = [pair_invariants(S0.key_shape(focus), S0.key_shape(d)) for d in decoys]
        clusters.append(meta)
    return items, clusters


def bank_profile(S0, rows):
    """Design s5.2: the bank profile, the counts of non-focus bank worlds with the focus's node count, edge count,
    degree multiset and domain. The twins must have the same profile (asserted)."""
    focus_cls, focus_dom = rows[0][1], rows[0][2]
    fn, fe = S0.key_shape(focus_cls)
    fg = S0.group_key((fn, fe))
    out = collections.Counter()
    for role, cls, dom in rows[1:]:
        n, e = S0.key_shape(cls)
        out["node_count"] += n == fn
        out["edge_count"] += len(e) == len(fe)
        out["degree_multiset"] += S0.group_key((n, e)) == fg
        out["domain"] += dom == focus_dom
    return {k: out[k] for k in ("node_count", "edge_count", "degree_multiset", "domain")}


def same_degree_decoys(S0, rows):
    """Review M3 fix 2: bank worlds with the focus's degree multiset, another domain, and a different class."""
    focus_cls, focus_dom = rows[0][1], rows[0][2]
    fg = S0.group_key(S0.key_shape(focus_cls))
    return sum(1 for _, cls, dom in rows[1:] if S0.group_key(S0.key_shape(cls)) == fg and dom != focus_dom and cls != focus_cls)


def correspondence_items(ctx, split, cell, seed, foci, partners_of):
    """Design s5.3: exactly 2 items per focus, MAPPING (a relabelled isomorphic copy) and NO_MATCH (one same-degree,
    non-isomorphic class of the focus's group); the packet's bank holds exactly the target world."""
    hw, vocab, source, S0 = ctx["hw"], ctx["vocab"], ctx["source"], ctx["S0"]
    domains = hw.TRAINING_DOMAINS
    items, clusters = [], []
    for focus in foci:
        rng = random.Random(hw.keyed_int(seed, "correspondence", split, focus))
        f_dom = rng.choice(domains)
        no_match = rng.choice(sorted(partners_of(focus)))
        cid = "%s|%s|%s" % (split, cell, hw.sha(focus)[:16])
        n, edges = S0.key_shape(focus)
        meta = {"cluster_id": cid, "split": split, "cell": cell, "shape_key": focus, "n": n, "edge_count": len(edges),
                "group_key": S0.group_key((n, edges)), "no_match_class": no_match, "focus_domain": f_dom,
                "flag_image": {}, "items": [],
                "role_classes": sorted({focus, no_match})}                # Codex A2.2: focus and both targets
        for status, cls in (("MAPPING", focus), ("NO_MATCH", no_match)):
            irng = random.Random(hw.keyed_int(seed, "correspondence-item", split, focus, status))
            t_dom = irng.choice([d for d in domains if d != f_dom])
            rows = [("FOCUS", focus, f_dom), ("TARGET", cls, t_dom)]
            pairs = draw_item_worlds(hw, vocab, source, irng, rows)
            if status == "MAPPING":
                meta["flag_image"][status] = {"TARGET": flags_on_image(ctx["aut"](focus), pairs[0][1], pairs[1][1])}
            for k in (0, 1):
                iid = "%s|%s|pres%d" % (cid, status, k)
                items.append({"item_id": iid, "cluster_id": cid, "split": split, "cell": cell, "presentation": k,
                              "kind": "correspondence", "rule": None, "cue": "CUBE_FACE_4", "status": status,
                              "focus": 0, "target": 1, "bank": [1], "roles": ["FOCUS", "TARGET"],
                              "classes": [focus, cls], "domains": [f_dom, t_dom],
                              "worlds": [p[0][k] for p in pairs], "flags": [p[1] for p in pairs]})
                meta["items"].append(iid)
        meta["diagnostic_pairs"] = [pair_invariants(S0.key_shape(focus), S0.key_shape(no_match))]
        clusters.append(meta)
    return items, clusters


# ============================================================================ printed diagnostics (never bars)
def _invariants(shape):
    n, edges = shape
    out = collections.defaultdict(set)
    for a, b in edges:
        out[a].add(b)
    desc = {}
    for v in range(n):
        seen, stack = set(), [v]
        while stack:
            x = stack.pop()
            for y in out[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        desc[v] = seen
    anc = {v: {u for u in range(n) if v in desc[u]} for v in range(n)}
    ind, outd = degrees(n, edges)
    memo = {}

    def depth(v):
        if v not in memo:
            memo[v] = max((1 + depth(w) for w in out[v]), default=0)
        return memo[v]
    return {"longest_path": max(depth(v) for v in range(n)),
            "reachable_pairs": sum(len(desc[v]) for v in range(n)),
            "node_in_out_descendants_ancestors": tuple(sorted((ind[v], outd[v], len(desc[v]), len(anc[v])) for v in range(n)))}


def _joint_refinement(g, h, rounds):
    """Directed colour refinement run on both graphs with one shared colour table. rounds=None: until stable."""
    def adj(shape):
        n, edges = shape
        outs, ins = [[] for _ in range(n)], [[] for _ in range(n)]
        for a, b in edges:
            outs[a].append(b)
            ins[b].append(a)
        return n, outs, ins
    graphs = [adj(g), adj(h)]
    colours = [[(len(ins[v]), len(outs[v])) for v in range(n)] for n, outs, ins in graphs]
    k, previous = 0, len({c for cs in colours for c in cs})
    while rounds is None or k < rounds:
        sigs = [[(cs[v], tuple(sorted(cs[u] for u in outs[v])), tuple(sorted(cs[u] for u in ins[v]))) for v in range(n)]
                for cs, (n, outs, ins) in zip(colours, graphs)]
        names = {s: i for i, s in enumerate(sorted({s for ss in sigs for s in ss}))}
        colours = [[names[s] for s in ss] for ss in sigs]
        k += 1
        if rounds is None:
            now = len(names)
            if now == previous:
                break
            previous = now
    return sorted(colours[0]) != sorted(colours[1])


def pair_invariants(g, h):
    """Which printed diagnostics separate a same-degree pair (design s6: printed, never bars)."""
    a, b = _invariants(g), _invariants(h)
    out = {name: a[name] != b[name] for name in a}
    out["colour_refinement_1_round"] = _joint_refinement(g, h, 1)
    out["colour_refinement_full"] = _joint_refinement(g, h, None)
    return out


DIAGNOSTIC_NAMES = ("longest_path", "reachable_pairs", "node_in_out_descendants_ancestors",
                    "colour_refinement_1_round", "colour_refinement_full")


# ============================================================================ statistics and cell summaries
def smallest_detectable_regression(A):
    c = 1
    while A.sign_p(c, 0) > ALPHA:
        c += 1
    return c


def power_grid(A, wrong, n):
    if not n:
        return None
    acc = (n - wrong) / n
    uniform = sorted({round(min(1.0, acc + d), 4) for d in (0.10, 0.20, 0.30)} | {1.0})
    return {"assumption": ("conditional on the binding comparator's measured per-cluster results; clusters independent; "
                           "exact one-sided sign test at alpha %s; no zero-loss veto; one run (each of 3 runs must "
                           "pass); passing the binding bar is necessary, not sufficient, under BEATS_ALL_REGISTERED_BARS"
                           % ALPHA),
            "uniform_model_accuracy": {("%.4f" % q): A.power_given_bar(wrong, n - wrong, q, q) for q in uniform},
            "never_loses_where_bar_is_right_wins_fraction": {("%.2f" % f): A.power_given_bar(wrong, n - wrong, f, 1.0)
                                                             for f in (0.5, 0.75, 1.0)}}


def floor_block(A, members, bars, *, need_groups=False):
    """Design s7: W_X for every bar, the binding W (the smallest), and the floor."""
    n = len(members)
    W = {x: sum(1 for c in members if not c["comparators"][x]) for x in bars}
    binding = min(bars, key=lambda x: (W[x], bars.index(x))) if bars else None
    wb = W[binding] if bars else 0
    groups = len({c["group_key"] for c in members}) if members and "group_key" in members[0] else None
    out = {"clusters": n, "bars": list(bars), "W_by_comparator": W,
           "comparator_cluster_accuracy": {x: (round((n - W[x]) / n, 6) if n else None) for x in bars},
           "binding_comparator": binding, "binding_comparators_tied": [x for x in bars if W[x] == wb],
           "binding_W": wb, "distinct_shapes_behind_binding_W": len({c["shape_key"] for c in members
                                                                     if not c["comparators"][binding]}) if bars else 0,
           "distinct_degree_groups": groups,
           "distinct_degree_groups_behind_binding_W": (len({c["group_key"] for c in members if not c["comparators"][binding]})
                                                       if groups is not None and bars else None),
           "power_conditional_on_binding_bar": power_grid(A, wb, n)}
    why = []
    if n < MIN_CLUSTERS:
        why.append("clusters %d < %d" % (n, MIN_CLUSTERS))
    if wb < MIN_CLUSTERS:
        why.append("binding W %d < %d (%s)" % (wb, MIN_CLUSTERS, binding))
    if need_groups and (groups or 0) < MIN_CLUSTERS:
        why.append("distinct degree groups %d < %d" % (groups or 0, MIN_CLUSTERS))
    out["can_carry_a_claim"] = not why
    out["why_not"] = "; ".join(why) or None
    return out


def cluster_results(clusters, rows_by_item, names):
    """A cluster is right for a comparator only if every item and every presentation is right (design s5). No
    parameter is chosen on the cell (Codex A2.1): every family member keeps its own cluster results."""
    for c in clusters:
        rows = [rows_by_item[i] for i in c["items"]]
        c["comparators"] = {x: all(r["comparators"][x] for r in rows) for x in names}


def tuned_diagnostic(W):
    """The pre-A2 tuned choices, printed ONLY as a labelled diagnostic (Codex A2.1): for each family, the member with
    the fewest wrong clusters on this cell (ties: the first). Never used by a floor, a bar or a claim."""
    out = {"label": ("DIAGNOSTIC_ONLY_NEVER_A_BAR: a parameter chosen at its best value on this cell; every family "
                     "member is a registered bar with its own W (Codex A2.1)")}
    for name, family in sorted(TUNED_DIAGNOSTIC_FAMILIES.items()):
        best = min(family, key=lambda x: (W[x], family.index(x)))
        out[name] = {"chosen": best, "W": W[best]}
    return out


# ---- Codex A2.2 (PROPOSED): degree-group and shared-shape-component views; exact rational arithmetic
ALPHA_EXACT = Fraction(1, 100)
assert Fraction(ALPHA).limit_denominator(1000) == ALPHA_EXACT


def sign_tail_exact(B, C):
    """The exact one-sided sign-test tail sum(comb(B+C, k), k = B..B+C) / 2**(B+C); p = 1 if B + C = 0 (Codex A2.2).
    Ties never enter the denominator."""
    n = B + C
    if n == 0:
        return Fraction(1)
    return Fraction(sum(math.comb(n, k) for k in range(B, n + 1)), 2 ** n)


def view_units(members):
    """Codex A2.2: the cell's degree groups and shared-shape components, fixed from the build before any model is read.

    Each cluster carries `view_group` (its focus's degree-group key: node count and joint degree multiset) and
    `role_classes` (every canonical class in every packet role and presentation). Two degree groups are joined when
    their class sets intersect; components are the transitive closure. Returns ({group key: [clusters]}, {group key:
    component index}); component indices follow the sorted order of each component's smallest group key."""
    groups = collections.defaultdict(list)
    for c in members:
        groups[c["view_group"]].append(c)
    keys = sorted(groups)
    parent = {g: g for g in keys}

    def find(g):
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g
    owner = {}
    for g in keys:
        for k in sorted({k for c in groups[g] for k in c["role_classes"]}):
            if k not in owner:
                owner[k] = g
                continue
            a, b = find(g), find(owner[k])
            if a != b:
                parent[max(a, b)] = min(a, b)
    index = {r: i for i, r in enumerate(sorted({find(g) for g in keys}))}
    return dict(groups), {g: index[find(g)] for g in keys}


def _sign_counts(values):
    return (sum(1 for v in values if v > 0), sum(1 for v in values if v < 0), sum(1 for v in values if v == 0))


def paired_views(A, members, groups, component_of, a_right, b_right):
    """ONE paired comparison in all three views (Codex A2.2): `a` is the model (or the repaired arm), `b` a registered
    bar (or the unchanged arm). a_right, b_right: {cluster_id: bool}, a cluster being right only if every item and
    presentation is right (design s5). Differences are a - b per cluster, in {-1, 0, 1}.

    original_cluster: the section 7 calculation, unchanged (b > c and exact one-sided p <= 0.01), labelled
    CONDITIONAL_CLUSTER_DIAGNOSTIC. degree_group: each group's exact mean difference; its sign is one observation.
    shared_shape_component: the equally weighted mean of the member groups' means; its sign is one observation. A view
    passes iff B > C, the overall accuracy difference is positive, and the exact tail is <= 1/100."""
    d = {c["cluster_id"]: int(bool(a_right[c["cluster_id"]])) - int(bool(b_right[c["cluster_id"]])) for c in members}
    n = len(members)
    overall = Fraction(sum(d.values()), n) if n else Fraction(0)
    gmean = {g: Fraction(sum(d[c["cluster_id"]] for c in cs), len(cs)) for g, cs in groups.items()}
    by_comp = collections.defaultdict(list)
    for g, v in gmean.items():
        by_comp[component_of[g]].append(v)
    cmean = {k: sum(vs, Fraction(0)) / len(vs) for k, vs in by_comp.items()}
    out = {"overall_accuracy_difference": str(overall), "overall_accuracy_difference_float": round(float(overall), 6)}
    b, c, t = _sign_counts(d.values())
    out["original_cluster"] = {"label": ORIGINAL_VIEW_LABEL, "b": b, "c": c, "ties": t, "p": A.sign_p(b, c),
                               "p_exact": str(sign_tail_exact(b, c)),
                               "pass": b > c and A.sign_p(b, c) <= ALPHA}
    for view, values in (("degree_group", gmean.values()), ("shared_shape_component", cmean.values())):
        B, C, T = _sign_counts(values)
        p = sign_tail_exact(B, C)
        out[view] = {"units": len(values), "B": B, "C": C, "ties": T, "p_exact": str(p), "p": float(p),
                     "pass": B > C and overall > 0 and p <= ALPHA_EXACT}
    return out


def evaluate_cell_views(A, members, bars, model_right):
    """What the scorer runs per cell and run (Codex A2.2, A2.3): the model against EVERY registered bar of the claim,
    in all three views. A view passes iff the model beats every bar in it. `largest_p` is the largest p over the bars
    (the intersection-union reading); it is valid only if the view's own assumptions hold (A2.2)."""
    groups, component_of = view_units(members)
    per_bar = {x: paired_views(A, members, groups, component_of, model_right,
                               {c["cluster_id"]: c["comparators"][x] for c in members}) for x in bars}
    return {"per_bar": per_bar,
            "passes_every_bar": {v: bool(bars) and all(per_bar[x][v]["pass"] for x in bars) for v in VIEWS},
            "largest_p": {v: max((per_bar[x][v]["p"] for x in bars), default=1.0) for v in VIEWS}}


def _histogram(sizes):
    counts = collections.Counter(sizes)
    return {str(k): counts[k] for k in sorted(counts)}


def views_block(members, bars, *, confirmatory_analogy=False, diagnostics=()):
    """Codex A2.4, per cell (reach: per claim): the units of every view, their size distributions, W_X of every bar in
    every view (the units in which a perfect model could improve on X), each view's binding minimum, the A2.4 floors
    (binding only for the confirmatory analogy claim; printed for every other cell) and the unit counts for the power
    grid. Counts only: no class, group key or membership (those stay in the cluster tables, custodian-only for TEST)."""
    groups, component_of = view_units(members)
    comp_groups = collections.Counter(component_of.values())
    comp_clusters = collections.Counter()
    for g, cs in groups.items():
        comp_clusters[component_of[g]] += len(cs)
    units = {"original_cluster": len(members), "degree_group": len(groups), "shared_shape_component": len(comp_groups)}

    def w(x):
        bad = [g for g, cs in groups.items() if any(not c["comparators"][x] for c in cs)]
        return {"original_cluster": sum(1 for c in members if not c["comparators"][x]), "degree_group": len(bad),
                "shared_shape_component": len({component_of[g] for g in bad})}
    W = {x: w(x) for x in bars}
    binding = {}
    for v in VIEWS:
        if bars:
            x = min(bars, key=lambda y: (W[y][v], bars.index(y)))
            binding[v] = {"comparator": x, "W": W[x][v], "tied": [y for y in bars if W[y][v] == W[x][v]]}
        else:
            binding[v] = {"comparator": None, "W": 0, "tied": []}
    checks = [("original clusters", units["original_cluster"]), ("degree groups", units["degree_group"]),
              ("shared-shape components", units["shared_shape_component"])]
    checks += [("binding W in the %s view (%s)" % (v, binding[v]["comparator"]), binding[v]["W"]) for v in VIEWS]
    reasons = ["%s %d < %d" % (name, value, A2_4_MIN_UNITS) for name, value in checks if value < A2_4_MIN_UNITS]
    out = {"units": units,
           "distinct_focus_shapes": len({c["shape_key"] for c in members}),
           "size_distributions": {"clusters_per_degree_group": _histogram(len(cs) for cs in groups.values()),
                                  "degree_groups_per_component": _histogram(comp_groups.values()),
                                  "clusters_per_component": _histogram(comp_clusters.values())},
           "W_by_comparator_by_view": W, "binding_by_view": binding,
           "original_view_label": ORIGINAL_VIEW_LABEL,
           "floors": {"rule": ("Codex A2.4: at least %d original clusters, degree groups and shared-shape components, "
                               "and binding W >= %d in every view" % (A2_4_MIN_UNITS, A2_4_MIN_UNITS)),
                      "applies": ("BINDING: the confirmatory analogy claim (REPAIR_IMPROVES_ANALOGY_6)"
                                  if confirmatory_analogy else
                                  "PRINTED_NOT_BINDING: A2.4 names these floors only for the confirmatory analogy "
                                  "claim; this cell's claims keep their original floor"),
                      "meets_every_floor": not reasons,
                      "not_testable_reasons": reasons},
           "repaired_vs_unchanged_informative_count": {"state": "NOT_YET_OBSERVED",
                                                       "structural_maximum_units": units},
           "power": {"original_cluster": "the HSET-1A grid (power_conditional_on_binding_bar) for the binding bar, "
                                         "labelled CONDITIONAL_CLUSTER_DIAGNOSTIC; and the conditional sign-power "
                                         "grid for n = the original cluster count",
                     "degree_group": "NOT_IDENTIFIED_FROM_RAW_ACCURACY; the conditional sign-power grid for n = the "
                                     "degree-group count",
                     "shared_shape_component": "NOT_IDENTIFIED_FROM_RAW_ACCURACY; the conditional sign-power grid for "
                                               "n = the component count",
                     "grid_table": "conditional_sign_power_by_unit_count (top level), rows n = %s"
                                   % sorted(set(units.values()))}}
    if diagnostics:
        out["computed_not_registered_W_by_view"] = {x: w(x) for x in diagnostics}
    return out


_SIGN_MIN_WINS = {}


def sign_min_wins(d):
    """The smallest B (of d discordant units) with B > d - B and exact tail <= 1/100, or None (exact integers)."""
    if d not in _SIGN_MIN_WINS:
        best, tail = None, 0
        for B in range(d, -1, -1):
            tail += math.comb(d, B)
            if B > d - B and 100 * tail <= 2 ** d:
                best = B
            else:
                break
        _SIGN_MIN_WINS[d] = best
    return _SIGN_MIN_WINS[d]


def conditional_sign_power(d, q):
    """Codex A2.4: P(the exact sign test passes | d discordant units, each positive with probability q), summed
    exactly over Binomial(d, q): sum over B >= sign_min_wins(d) of comb(d, B) q**B (1 - q)**(d - B). q = (num, den)."""
    lo = sign_min_wins(d)
    if lo is None:
        return Fraction(0)
    a, b = q
    return Fraction(sum(math.comb(d, B) * a ** B * (b - a) ** (d - B) for B in range(lo, d + 1)), b ** d)


def sign_power_table(unit_counts):
    """{n: {q: [power for d = 0..n]}} for every unit count n that occurs, computed exactly, rounded only at print."""
    top = max(unit_counts, default=0)
    grid = {"%.2f" % (a / b): [conditional_sign_power(d, (a, b)) for d in range(top + 1)] for a, b in SIGN_POWER_Q}
    return {"how": ("Codex A2.4: conditional on d discordant units; each discordant unit positive with probability q; "
                    "power = sum over B of Binomial(d, q) probabilities whose exact null tail at q = 0.5 is <= 0.01 "
                    "(and B > d - B); exact rational sums, rounded to 6 places only at print. A sensitivity "
                    "calculation, not a forecast of any model's power"),
            "all_win_minimum_discordant_units": next(d for d in range(1, 64) if sign_min_wins(d) is not None),
            "by_unit_count": {str(n): {q: [round(float(v), 6) for v in values[:n + 1]] for q, values in grid.items()}
                              for n in sorted(set(unit_counts))}}


def summarise_bank_cell(A, cell, kind, clusters, rows_by_item, claim_role):
    names = analogy_comparators() if kind == "analogy" else CORRESPONDENCE_COMPARATORS
    extra = analogy_computed_not_registered() if kind == "analogy" else ()
    cluster_results(clusters, rows_by_item, names + extra)
    for c in clusters:
        c["view_group"] = c["group_key"]
    s = {"cell": cell, "kind": kind, "claim_role": claim_role, "cluster_unit": "FOCUS_CLASS (every item and presentation)",
         "items_per_focus": 2, "presentations_per_item": 2, "original_calculation_label": ORIGINAL_VIEW_LABEL,
         **floor_block(A, clusters, names, need_groups=(kind == "analogy"))}
    if kind == "analogy":
        s["tuned_on_this_cell_diagnostic_not_a_bar"] = tuned_diagnostic(s["W_by_comparator"])
    if extra:
        s["computed_not_registered_W"] = {x: sum(1 for c in clusters if not c["comparators"][x]) for x in extra}
    s["a2_views"] = views_block(clusters, names, confirmatory_analogy=(cell == "TEST_NEW_6/ANALOGY"),
                                diagnostics=extra)
    statuses = ("MATCH", "NO_MATCH") if kind == "analogy" else ("MAPPING", "NO_MATCH")
    rows = [rows_by_item[i] for c in clusters for i in c["items"]]
    s["item_level_accuracy_by_status"] = {}
    for st in statuses:
        pairs = collections.defaultdict(list)
        for c in clusters:
            for i in c["items"]:
                if "|%s|" % st in i:
                    pairs[i.rsplit("|", 1)[0]].append(rows_by_item[i])
        s["item_level_accuracy_by_status"][st] = {
            "items": len(pairs),
            **{x: (round(sum(all(r["comparators"][x] for r in rs) for rs in pairs.values()) / len(pairs), 6)
                   if pairs else None) for x in names}}
    s["flag_image_rates"] = {}
    for st in statuses:
        roles = collections.defaultdict(list)
        for c in clusters:
            for role, v in c["flag_image"].get(st, {}).items():
                roles[role].append(v)
        s["flag_image_rates"][st] = {role: {"items": len(v), "whole_on_an_image": round(sum(x["whole"] for x in v) / len(v), 6),
                                            "whole_and_both_participants_on_one_image": round(sum(x["all_three"] for x in v) / len(v), 6)}
                                     for role, v in sorted(roles.items())}
    alias = collections.defaultdict(collections.Counter)
    for r in rows:
        for role, a in r.get("role_alias", {}).items():
            alias["%s_presentation_%s" % (role, r["item_id"][-1])][a] += 1
    s["alias_positions"] = {k: dict(sorted(v.items(), key=lambda kv: int(kv[0][1:]))) for k, v in sorted(alias.items())}
    diag = collections.Counter()
    pairs_total = 0
    for c in clusters:
        for p in c["diagnostic_pairs"]:
            pairs_total += 1
            for name in DIAGNOSTIC_NAMES:
                diag[name] += p[name]
    s["printed_diagnostics_never_bars"] = {"focus_versus_decoy_pairs": pairs_total,
                                           "pairs_are_same_degree": not (clusters and clusters[0].get("relaxed_recipe")),
                                           "pairs_separated_by": {name: diag[name] for name in DIAGNOSTIC_NAMES}}
    if kind == "analogy":
        s["distractor_split_diagnostic"] = {
            half: floor_block(A, [c for c in clusters if c["with_distractor"] == flag], names, need_groups=True)
            for half, flag in (("WITH_SAME_DOMAIN_DISTRACTOR", True), ("WITHOUT_DISTRACTOR", False))}
        s["twin_profiles_equal"] = sum(c["profiles_equal"] for c in clusters)
        s["relaxed_recipe"] = bool(clusters and clusters[0]["relaxed_recipe"])
    return s


def summarise_reach_cell(hw, A, cell, clusters, rows_by_item, items_by_cluster, seed, claim_role):
    """HSET-1A's reviewed summary (balancing, ties, alternative cuts), then design s7's per-bar W and both claims, with
    Codex A2.2's views per claim (the focus's degree group; reach packets have one listed role, the focus)."""
    import hset2_stage0_public as S0
    names = reach_comparators()
    extra = reach_computed_not_registered()
    s = A.summarise_cell(hw, cell, clusters, rows_by_item, items_by_cluster, seed)
    single_bar = {k: s.pop(k) for k in ("bar", "bar_cluster_accuracy", "bar_wrong_clusters_W", "bar_right_clusters",
                                        "can_carry_a_claim", "why_not", "can_possibly_pass_W_at_least_7",
                                        "W_meets_10_cluster_floor", "power_conditional_on_measured_bar",
                                        "comparator_cluster_accuracy") if k in s}
    s["hset1a_single_best_bar_diagnostic_without_three_hop"] = single_bar
    s["claim_role"] = claim_role
    if s["kind"] != "reach":
        s["can_carry_a_claim"], s["why_not"] = False, "diagnostic cell (design s1): its no-learning rule reads the answer off the input"
        return s
    for c in clusters:
        rows = [rows_by_item[i["item_id"]] for i in items_by_cluster[c["cluster_id"]]]
        for x in (THREE_HOP, SINGLE_ROOT, SINGLE_ROOT_THREE_HOP, FRONTIER):
            c["comparators"][x] = all(r["comparators"][x] for r in rows)
        _, edges = json.loads(c["shape_key"])
        c["whole_has_children"] = any(a == c["whole"] for a, _ in edges)
        c["single_root_shape"] = len({a for a, _ in edges} | {b for _, b in edges}) - len({b for _, b in edges}) == 1
        # Codex A2.2: the unit keys. The frozen 64-world training bank rides unchanged in every reach packet and is
        # not a listed packet role (F4; Helm's reader reads only the focus for reach), so it joins no two groups.
        c["view_group"] = S0.group_key(S0.key_shape(c["shape_key"]))
        c["role_classes"] = [c["shape_key"]]
    primary = [c for c in clusters if c["role"] == "PRIMARY"]
    for c in primary:
        c["group_key"] = None
    claim_bars = {"REACH_3_STEP_TRANSFER_6": tuple(x for x in names if x not in BUILT_ON_THREE_HOP),
                  "REACH_4_STEP_TRANSFER_6": names}
    s["claims"] = {claim: floor_block(A, primary, bars) for claim, bars in claim_bars.items()}
    for claim, block in s["claims"].items():
        block.pop("distinct_degree_groups")
        block.pop("distinct_degree_groups_behind_binding_W")
        block["original_calculation_label"] = ORIGINAL_VIEW_LABEL
        block["a2_views"] = views_block(primary, claim_bars[claim], diagnostics=extra)
    if extra:
        s["computed_not_registered_W"] = {x: sum(1 for c in primary if not c["comparators"][x]) for x in extra}
    s["genuine_no_path_primary_absent_clusters_whose_whole_has_children"] = sum(
        1 for c in primary if c["state"] == "ABSENT" and c["whole_has_children"])
    s["primary_absent_clusters"] = sum(1 for c in primary if c["state"] == "ABSENT")
    # A2 (F2), printed: a whole in a one-root shape reaches every node, so ABSENT clusters come only from shapes with
    # two or more roots. This is what SINGLE_ROOT_FALLBACK exploits without following any path.
    s["primary_by_state_single_root_shape"] = {st: {"one_root": sum(1 for c in primary if c["state"] == st and c["single_root_shape"]),
                                                    "two_or_more_roots": sum(1 for c in primary if c["state"] == st and not c["single_root_shape"])}
                                               for st in ("ABSENT", "DIRECT", "VIA")}
    s["can_carry_a_claim"] = s["claims"]["REACH_3_STEP_TRANSFER_6"]["can_carry_a_claim"]
    s["can_carry_a_claim_note"] = ("cell-level value = the REACH_3_STEP_TRANSFER_6 floor; REACH_4_STEP_TRANSFER_6 has its "
                                   "own floor in claims")
    return s


def trained_answer_states(frozen=None):
    """Design s7 / review m4: which answer states the trained course ever asked, per kind.

    Analogy and correspondence: `TRAINED_BANK_STATES`, measured by this builder on 2026-09-23 with the frozen checker
    over the frozen public course's registry main queries. When `frozen` (the loaded course) is given, they are
    measured again and must be equal (the sealed build does this; it costs about 158 frozen-checker targets).
    Reach: HSET-1A's record of the same course (`hset1a_build.TRAINED_REACH_STATES`), as HSET-1A and HSET-1B did."""
    import hset1a_build as A
    out = {kind: dict(states) for kind, states in TRAINED_BANK_STATES.items()}
    if frozen is not None:
        from cas_meta2.typed_teaching import checker, course
        counts = {"analogy": collections.Counter(), "correspondence": collections.Counter()}
        for row in frozen["registry"]:
            q = row["query"]
            if q["kind"] not in counts:
                continue
            values = [a["value"] for a in checker.derive_target(course._public(frozen["bank"], row["source_world_id"]), q)["admissible_answers"]]
            if q["kind"] == "analogy":
                counts["analogy"]["NO_MATCH" if values == [{"world_id": None}] else "MATCH"] += 1
            else:
                counts["correspondence"]["NO_MATCH" if values[0]["status"] == "NO_MATCH" else "MAPPING"] += 1
        if {k: dict(sorted(v.items())) for k, v in counts.items()} != out:
            raise SystemExit("REFUSED: the trained course's analogy/correspondence answer states differ from the pinned record")
    out.update({cell: dict(states) for cell, states in A.TRAINED_REACH_STATES.items()})
    out["source"] = ("analogy, correspondence: frozen checker over the frozen public course's registry main queries "
                     "(pinned 2026-09-23; %s); reach: hset1a_build.TRAINED_REACH_STATES"
                     % ("re-measured and equal in this run" if frozen is not None else "not re-measured in this run"))
    return out


# ============================================================================ main
def is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def resolve_salts(args):
    if args.throwaway_seed is not None:
        if args.salt_file_hset1a or args.salt_file_hset2:
            raise SystemExit("REFUSED: throwaway mode reads no salt file")
        derive = lambda which: hashlib.sha256((THROWAWAY_PREFIX + args.throwaway_seed + "|" + which).encode()).hexdigest()  # noqa: E731
        s1, s2 = derive("hset1a"), derive("hset2")
        if hashlib.sha256(s1.encode()).hexdigest() == HSET1A_SALT_SHA256 or (
                HSET2_SALT_SHA256 and hashlib.sha256(s2.encode()).hexdigest() == HSET2_SALT_SHA256):
            raise SystemExit("REFUSED: a throwaway salt equals a real one")
        return "THROWAWAY_SALTS_NOT_A_BUILD", s1, s2
    if args.limit_foci or args.only:
        raise SystemExit("REFUSED: --limit-foci and --only are smoke options and need throwaway salts")
    if HSET2_SALT_SHA256 is None:
        raise SystemExit("REFUSED: HSET2_SALT_SHA256 is not committed yet (design s3 step 6, s9 step 2)")
    if not (args.salt_file_hset1a and args.salt_file_hset2 and args.expect_test5_shapes_digest):
        raise SystemExit("REFUSED: real mode needs both salt files and --expect-test5-shapes-digest")
    if not is_hex64(args.expect_test5_shapes_digest):
        raise SystemExit("REFUSED: --expect-test5-shapes-digest must be 64 lowercase hex characters")
    salts = []
    for path, pin, name in ((args.salt_file_hset1a, HSET1A_SALT_SHA256, "HSET-1A"), (args.salt_file_hset2, HSET2_SALT_SHA256, "HSET-2")):
        try:
            salt = pathlib.Path(path).read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError) as error:             # names the error type only, never the content
            raise SystemExit("REFUSED: the %s salt file cannot be read (%s)" % (name, type(error).__name__)) from None
        if not is_hex64(salt):
            raise SystemExit("REFUSED: the %s salt must be 64 lowercase hex characters" % name)
        if hashlib.sha256(salt.encode("ascii")).hexdigest() != pin:
            raise SystemExit("REFUSED: the %s salt is not the one whose sha256 was committed" % name)
        salts.append(salt)
    return "SEALED_BUILD", salts[0], salts[1]


def check_withheld_5(all5, dev5, test5, withheld5, excluded):
    """Design s3 and review M11: no PUBLIC_EXCLUDED class may be in TEST_NEW_5 (the real guard: CUSTODY_BREACH), and
    WITHHELD_5 must be every 5-node class not in DEV_NEW_5, not in TEST_NEW_5 and not in PUBLIC_EXCLUDED. The second
    rule is checked as a partition (WITHHELD_5 meets none of the three; the four together cover all 267 classes), not
    by recomputing the formula that made WITHHELD_5. In the build it guards against a later edit of that formula; the
    unit test shows it catches a wrong WITHHELD_5. Fails closed; names no class."""
    all5, dev5, test5, withheld5 = set(all5), set(dev5), set(test5), set(withheld5)
    if test5 & excluded:
        raise SystemExit("CUSTODY_BREACH: %d PUBLIC_EXCLUDED classes are in TEST_NEW_5" % len(test5 & excluded))
    if dev5 & test5 or len(dev5) != 60 or len(test5) != 60:
        raise SystemExit("REFUSED: DEV_NEW_5 and TEST_NEW_5 are not two disjoint sets of 60")
    if withheld5 & (dev5 | test5 | excluded) or withheld5 | dev5 | test5 | (excluded & all5) != all5:
        raise SystemExit("REFUSED: WITHHELD_5 is not every class outside DEV_NEW_5, TEST_NEW_5 and PUBLIC_EXCLUDED")
    return True


def disjointness_measured(all5, dev5, test5, withheld5, excluded, dev_side, test_side, dev6, test6, withheld6):
    """The printed split-disjointness table (design s9 step 4). Every value is COUNTED from the sets themselves, so it
    can show a failure; the build has already exited (CUSTODY_BREACH or REFUSED) if a required value is wrong."""
    all5, dev5, test5, withheld5 = set(all5), set(dev5), set(test5), set(withheld5)
    dev_side, test_side, dev6, test6, withheld6 = set(dev_side), set(test_side), set(dev6), set(test6), set(withheld6)
    return {"how": "counted from the sets; the build exits before this print if a required value fails",
            "five": {"dev_new_5_meets_test_new_5": len(dev5 & test5),
                     "withheld_5_meets_dev_new_5": len(withheld5 & dev5),
                     "withheld_5_meets_test_new_5": len(withheld5 & test5),
                     "withheld_5_meets_public_excluded": len(withheld5 & excluded),
                     "public_excluded_in_test_new_5": len(test5 & excluded),
                     "public_excluded_in_dev_new_5_printed_only_dev_is_public": len(dev5 & excluded),
                     "classes_not_covered_by_the_four_sets": len(all5 - dev5 - test5 - withheld5 - excluded)},
            "six": {"dev_side_meets_test_side": len(dev_side & test_side),
                    "public_excluded_on_dev_side": len(dev_side & excluded),
                    "public_excluded_on_test_side": len(test_side & excluded),
                    "test_new_6_off_the_test_side": len(test6 - test_side),
                    "dev_new_6_off_the_dev_side": len(dev6 - dev_side),
                    "withheld_6_meets_test_new_6": len(withheld6 & test6),
                    "test_side_not_covered_by_test_new_6_and_withheld_6": len(test_side - test6 - withheld6)}}


def inside_git_work_tree(path):
    p = pathlib.Path(path).resolve()
    return any((q / ".git").exists() for q in [p, *p.parents])


def load_stage0(root):
    """Stage 0, recomputed from the pinned fixture and required byte-identical to the committed files (A1 D1)."""
    import hset2_stage0_public as S0
    files0, _ = S0.outputs(S0.read_fixture_bytes(package_root=root))
    bad = S0.committed_check(files0, HERE)
    if bad:
        raise SystemExit("REFUSED: stage 0 recomputed differs from the committed files: %s" % bad)
    pe = json.loads(files0[S0.PUBLIC_EXCLUDED_FILE])
    return {"pe": pe, "summary0": json.loads(files0[S0.SUMMARY_FILE]),
            "sides": {s: json.loads(files0[f]) for s, f in (("DEV", S0.DEV_GROUPS_FILE), ("TEST", S0.TEST_GROUPS_FILE))},
            "excluded": {r["canonical_form"] for r in pe["classes"]}}


def derive(stage0, salt1a, salt2, vocab, source, *, limit_foci=0, only=None, facts5=None, expect_test5_digest=None):
    """The splits (s3), the eligible foci on the FULL pools (s5.2, s5.3, A1 D2), and every item and cluster.

    Deterministic in the two salts. `limit_foci` and `only` are smoke options (main refuses them with real salts);
    `facts5` may be passed in to skip recomputing the salt-free 5-node facts. Fails closed on the s3 split rules.
    `expect_test5_digest` (the sealed build passes HSET-1A's public test_shapes_digest) is checked right after
    `split_five`, before any item is built (review F10)."""
    import hset_worlds as hw
    import hset1a_build as A
    import oracle_isomorphism as oracle
    import hset2_stage0_public as S0
    sides, summary0, excluded = stage0["sides"], stage0["summary0"], stage0["excluded"]

    # ---- 5 nodes (s3): the HSET-1A split, the same salt and code, never re-drawn
    if facts5 is None:
        classes5 = oracle.dag_classes(5)
        if len(classes5) != 267:
            raise SystemExit("REFUSED: 5-node class count %d" % len(classes5))
        facts5 = {S0.class_key(s): A.shape_facts(hw, s) for s in classes5}
    dev5, test5, strata5 = A.split_five(hw, salt1a, facts5)
    test5_digest = hw.sha(sorted(test5))
    if expect_test5_digest is not None and test5_digest != expect_test5_digest:
        raise SystemExit("REFUSED: TEST_NEW_5 does not reproduce HSET-1A's public test_shapes_digest")
    withheld5 = sorted(set(facts5) - set(dev5) - set(test5) - excluded)
    check_withheld_5(facts5, dev5, test5, withheld5, excluded)
    # ---- 6 nodes (s3): the stage-0 sides; TEST_NEW_6 from the HSET-2 salt
    group_of, side_of = {}, {}
    for s in ("DEV", "TEST"):
        for row in sides[s]["groups"]:
            for k in row["classes"]:
                group_of[k], side_of[k] = row["group_key"], s
    dev_side = sorted(k for k, s in side_of.items() if s == "DEV")
    test_side = sorted(k for k, s in side_of.items() if s == "TEST")
    dev6 = summary0["dev_new_6"]["classes_in_draw_order"]
    dev_decoys6 = summary0["dev_decoys_6"]["classes"]
    test6, test_draws = S0.draw_side(salt2, "test", 6, FOCI, set(test_side))
    withheld6 = sorted(set(test_side) - set(test6))
    if (set(test6) & set(dev_side) or set(dev_side) & set(test_side) or (set(test_side) | set(dev_side)) & excluded
            or not set(test6) <= set(test_side) or not set(dev6) <= set(dev_side)):
        raise SystemExit("REFUSED: the 6-node splits are not disjoint as design s3 requires")
    disjoint = disjointness_measured(facts5, dev5, test5, withheld5, excluded, dev_side, test_side, dev6, test6, withheld6)

    # ---- eligibility (s5.2, s5.3, A1 D2) on the FULL pools; --limit-foci only trims the focus lists afterwards
    group5 = {k: S0.group_key(S0.key_shape(k)) for k in facts5}
    members6 = collections.defaultdict(set)
    for k, g in group_of.items():
        members6[g].add(k)

    def partners6(pool):
        return lambda k: sorted(c for c in members6[group_of[k]] if c != k and c in pool)
    test_pool6, dev_pool6 = set(test_side), set(dev_side)
    t5_pool = set(test5) | set(withheld5)
    d5_pool = set(dev5)

    def partners5(pool):
        return lambda k: sorted(c for c in pool if c != k and group5[c] == group5[k])
    elig = {"TEST_NEW_6/ANALOGY": [k for k in test6 if len(partners6(test_pool6)(k)) >= 4],
            "TEST_NEW_6/CORRESPONDENCE": [k for k in test6 if len(partners6(test_pool6)(k)) >= 1],
            "DEV_NEW_6/ANALOGY": [k for k in dev6 if len(partners6(dev_pool6)(k)) >= 4],
            "DEV_NEW_6/CORRESPONDENCE": [k for k in dev6 if len(partners6(dev_pool6)(k)) >= 1],
            "TEST_NEW_5/CORRESPONDENCE": sorted(k for k in t5_pool if partners5(t5_pool)(k)),
            "DEV_NEW_5/CORRESPONDENCE": sorted(k for k in dev5 if partners5(d5_pool)(k)),
            "DEV_NEW_5/ANALOGY_RELAXED": sorted(dev5)}
    eligible_full_counts = {c: len(v) for c, v in elig.items()}
    test6_use, dev6_use = test6, dev6
    if limit_foci:
        elig = {c: v[:limit_foci] for c, v in elig.items()}
        test6_use, dev6_use = test6[:limit_foci], dev6[:limit_foci]

    def halves(seed, split, foci):
        order = sorted(foci, key=lambda k: hw.keyed_int(seed, "analogy-distractor-half", split, k))
        return set(order[:len(order) // 2])
    aut_cache = {}

    def aut(key):
        if key not in aut_cache:
            n, e = S0.key_shape(key)
            aut_cache[key] = hw.automorphisms(n, list(e))
        return aut_cache[key]
    ctx = {"hw": hw, "vocab": vocab, "source": source, "S0": S0, "aut": aut}
    items, bank_clusters = [], {}

    want = lambda family: only in (None, family)                          # noqa: E731
    # reach, parts, edge account at 6 nodes: the reviewed HSET-1A code path (s5.1)
    single_clusters = []
    for split, seed, shapes in (("DEV_NEW_6", S0.DEV_SEED, dev6_use), ("TEST_NEW_6", salt2, test6_use)):
        if not want("reach"):
            break
        facts6 = {k: A.shape_facts(hw, S0.key_shape(k)) for k in shapes}
        i, c = A.build_items(hw, vocab, split, seed, shapes, facts6)
        items += i
        single_clusters += c
    # analogy (s5.2; DEV per s5.4 and A1 D3)
    for split, seed, cell, pool, fillers_from in (
            ("TEST_NEW_6", salt2, "ANALOGY", test_pool6, test_pool6),
            ("DEV_NEW_6", S0.DEV_SEED, "ANALOGY", dev_pool6, set(dev_decoys6))):
        if not want("analogy"):
            break
        foci = elig["%s/%s" % (split, cell)]
        fp = (lambda pool_: (lambda k: [c for c in pool_ if group_of[c] != group_of[k]]))(sorted(fillers_from))
        i, c = analogy_items(ctx, split, cell, seed, foci, partners6(pool), fp, halves(seed, split, foci))
        items += i
        bank_clusters["%s/%s" % (split, cell)] = c
    if want("analogy"):
        foci = elig["DEV_NEW_5/ANALOGY_RELAXED"]
        i, c = analogy_items(ctx, "DEV_NEW_5", "ANALOGY_RELAXED", S0.DEV_SEED, foci,
                             lambda k: [x for x in dev5 if x != k], lambda k: [x for x in dev5 if group5[x] != group5[k]],
                             halves(S0.DEV_SEED, "DEV_NEW_5", foci), relaxed=True)
        items += i
        bank_clusters["DEV_NEW_5/ANALOGY_RELAXED"] = c
    # correspondence (s5.3; 5 nodes with the widened foci of A1 D2)
    for split, seed, pf in (("TEST_NEW_6", salt2, partners6(test_pool6)), ("DEV_NEW_6", S0.DEV_SEED, partners6(dev_pool6)),
                            ("TEST_NEW_5", salt2, partners5(t5_pool)), ("DEV_NEW_5", S0.DEV_SEED, partners5(d5_pool))):
        if not want("correspondence"):
            break
        cell = "%s/CORRESPONDENCE" % split
        i, c = correspondence_items(ctx, split, "CORRESPONDENCE", seed, elig[cell], pf)
        items += i
        bank_clusters[cell] = c
    return {"facts5": facts5, "dev5": dev5, "test5": test5, "strata5": strata5, "test5_digest": test5_digest,
            "withheld5": withheld5, "dev_side": dev_side, "test_side": test_side, "dev6": dev6, "dev_decoys6": dev_decoys6,
            "test6": test6, "test_draws": test_draws, "withheld6": withheld6, "disjoint": disjoint, "elig": elig,
            "eligible_full_counts": eligible_full_counts, "test6_use": test6_use, "items": items,
            "single_clusters": single_clusters, "bank_clusters": bank_clusters, "members6": members6,
            "group_of": group_of, "group5": group5, "test_pool6": test_pool6, "partners6": partners6,
            "partners5": partners5, "t5_pool": t5_pool}


def output_names(mode):
    """File names and cell-role words per mode. Throwaway outputs are named THROWAWAY_* and every cell's role is
    THROWAWAY_NOT_DEV (review F11): a throwaway 5-node split puts real TEST_NEW_5 and WITHHELD_5 classes into its
    'DEV_NEW_5', so no throwaway output may ever be read as development feedback."""
    if mode == "SEALED_BUILD":
        return {"public": "HSET2_CELLS_PUBLIC.json", "summary": "HSET2_BUILD_SUMMARY.json", "sealed": "HSET2_SEALED_TEST.json",
                "traceback": "build_traceback.txt", "role_override": None}
    return {"public": "THROWAWAY_HSET2_CELLS_NOT_DEV.json", "summary": "THROWAWAY_HSET2_BUILD_SUMMARY.json",
            "sealed": "THROWAWAY_HSET2_SEALED_TEST.json", "traceback": "THROWAWAY_build_traceback.txt",
            "role_override": "THROWAWAY_NOT_DEV"}


def main(argv=None):
    """Parse, then run. In real (sealed) mode ANY exception that the build does not turn into a fixed refusal code is
    caught here: its full traceback goes ONLY to --out-sealed, and the public log gets only the exception type
    (review F6 and F8: an exception message could carry a TEST class key or a world spec)."""
    args = parse_args(argv)
    if args.throwaway_seed is not None:
        return _run(args)
    try:
        return _run(args)
    except SystemExit:
        raise                                                      # the build's own refusal codes name no TEST item
    except BaseException as error:  # noqa: BLE001 -- custody: nothing but the type may reach a public log
        import traceback
        written = False
        try:
            sealed = pathlib.Path(args.out_sealed)
            if not inside_git_work_tree(sealed):
                sealed.mkdir(parents=True, exist_ok=True)
                (sealed / output_names("SEALED_BUILD")["traceback"]).write_text(traceback.format_exc(), encoding="utf-8")
                written = True
        except BaseException:  # noqa: BLE001
            pass
        raise SystemExit("BUILD_FAILED_UNCAUGHT: %s (full traceback %s)" % (
            type(error).__name__, "written to the sealed output only" if written else "NOT written")) from None


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--salt-file-hset1a")
    parser.add_argument("--salt-file-hset2")
    parser.add_argument("--expect-test5-shapes-digest")
    parser.add_argument("--throwaway-seed")
    parser.add_argument("--out-public", required=True)
    parser.add_argument("--out-sealed", required=True)
    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--limit-foci", type=int, default=0, help="throwaway smoke only: keep K foci per split")
    parser.add_argument("--only", choices=("reach", "analogy", "correspondence"), default=None,
                        help="throwaway only: build one family of cells (to measure a family at full size in a short run)")
    parser.add_argument("--remeasure-trained-states", action="store_true",
                        help="throwaway mode: also re-measure the trained answer states (the sealed build always does; "
                             "the AWS smoke passes this so the paid build runs no code path for the first time)")
    return parser.parse_args(argv)


def _run(args):
    t0 = time.monotonic()
    root = pathlib.Path(args.package_root).resolve()
    _paths(root)
    if inside_git_work_tree(args.out_sealed):
        raise SystemExit("REFUSED: --out-sealed is inside a git work tree (design s8: nothing sealed goes into git)")
    if args.throwaway_seed is not None and inside_git_work_tree(args.out_public):
        raise SystemExit("REFUSED: throwaway outputs may not be written inside a git work tree (review F11: a throwaway "
                         "5-node split holds real TEST_NEW_5 and WITHHELD_5 classes)")
    mode, salt1a, salt2 = resolve_salts(args)
    outn = output_names(mode)
    remeasure = mode == "SEALED_BUILD" or args.remeasure_trained_states
    import hset_worlds as hw
    import hset1a_build as A
    import hset2_stage0_public as S0
    from cas_meta2.typed_teaching import checker, checker_v2, pointer_contract, pointer_inputs, slots_v2, source
    from eval_paths import larger_question_scope as scope
    tt = root / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching"
    ep = root / "research/CAS_META_2_COMPOSITION/eval_paths"
    identity = {"label": LABEL, "mode": mode, "source_commit_expected": SOURCE_COMMIT,
                "builder_sha256_lf": lf_sha(__file__), "stage0_sha256_lf": lf_sha(HERE / "hset2_stage0_public.py"),
                "hset_worlds_sha256_lf": lf_sha(HSET1A_DIR / "hset_worlds.py"),
                "hset1a_build_sha256_lf": lf_sha(HSET1A_DIR / "hset1a_build.py"),
                "hset1b_build_sha256_lf": lf_sha(HSET1A_DIR / "hset1b_build.py"),
                "oracle_sha256_lf": lf_sha(ORACLE_DIR / "oracle_isomorphism.py"),
                "salt_sha256": {"hset1a": hashlib.sha256(salt1a.encode("ascii")).hexdigest(),
                                "hset2": hashlib.sha256(salt2.encode("ascii")).hexdigest()},
                "typed_teaching_sha256_lf": {f: lf_sha(tt / f) for f in TYPED_TEACHING_FILES},
                "eval_paths_sha256_lf": {f: lf_sha(ep / f) for f in EVAL_PATH_FILES},
                "face_corpus_sha256_lf": lf_sha(root / "research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/face_corpus.py"),
                "checker_v2_profile_digest": checker_v2.checker_profile()["profile_digest"],
                "slots_v2_profile_digest": slots_v2.profile()["profile_digest"],
                "frozen_checker_profile_digest": checker.checker_profile()["profile_digest"],
                "larger_path_source_pins": "verified" if scope.verify_source_pins() else None,
                "gates_program": {"path": GATES_PROGRAM, "pinned_sha256_lf": GATES_PROGRAM_LF_SHA256,
                                  "observed_sha256_lf": lf_sha(root / GATES_PROGRAM) if (root / GATES_PROGRAM).is_file() else None},
                "python": platform.python_version(), "platform": platform.platform(), "processes": args.processes}
    for name, anchor in (("checker_v2_profile_digest", CHECKER_V2_PROFILE_ANCHOR), ("slots_v2_profile_digest", SLOTS_V2_PROFILE_ANCHOR),
                         ("frozen_checker_profile_digest", FROZEN_CHECKER_PROFILE_ANCHOR)):
        if identity[name] != anchor:
            raise SystemExit("REFUSED: %s is not the accepted one" % name)
    if identity["gates_program"]["observed_sha256_lf"] != GATES_PROGRAM_LF_SHA256:
        raise SystemExit("REFUSED: %s is missing or not the pinned version (A1 D4)" % GATES_PROGRAM)
    vocab, families = hw.vocabulary(source)
    bank = source.freeze_bank(families)
    frozen_course = pointer_contract.load_material(root)[0]
    if bank["bank"]["bank_digest"] != BANK_DIGEST_ANCHOR or hw.canon(frozen_course["bank"]["bank"]) != hw.canon(bank["bank"]):
        raise SystemExit("REFUSED: the rebuilt bank is not the trained course's bank")
    identity["bank_digest"] = bank["bank"]["bank_digest"]
    identity["vocabulary_digest"] = hw.sha(vocab)
    identity["label_cache_digest"] = pointer_inputs.label_cache(root)["cache_digest"]
    identity["registered_comparators"] = registered_comparators()
    identity["registered_comparators_digest"] = hw.sha(identity["registered_comparators"])

    # ---- trained answer states (s7, m4), from the frozen public course; salt-free, so measured FIRST (review F10)
    trained = trained_answer_states(frozen_course if remeasure else None)
    del frozen_course
    print("trained answer states %s in %.1f s" % ("re-measured" if remeasure else "read from the pinned record",
                                                  time.monotonic() - t0), flush=True)

    # ---- stage 0, recomputed and required identical to the committed files (A1 D1)
    stage0 = load_stage0(root)
    identity["stage0_files_sha256"] = stage0["summary0"]["files_sha256"]
    print("identity and stage 0 checked in %.1f s" % (time.monotonic() - t0), flush=True)
    # ---- splits (s3), eligibility (s5, A1 D2) and every item; the TEST_NEW_5 digest is checked inside derive,
    # right after split_five and before any item is built (review F10)
    D = derive(stage0, salt1a, salt2, vocab, source, limit_foci=args.limit_foci, only=args.only,
               expect_test5_digest=args.expect_test5_shapes_digest)
    pe, summary0 = stage0["pe"], stage0["summary0"]
    (dev5, test5, strata5, test5_digest, withheld5, dev_side, test_side, dev6, dev_decoys6, test6, test_draws, withheld6,
     disjoint, elig, eligible_full_counts, test6_use, items, single_clusters, bank_clusters, members6, group_of,
     test_pool6, partners6, partners5, t5_pool) = (D[k] for k in (
        "dev5", "test5", "strata5", "test5_digest", "withheld5", "dev_side", "test_side", "dev6", "dev_decoys6", "test6",
        "test_draws", "withheld6", "disjoint", "elig", "eligible_full_counts", "test6_use", "items", "single_clusters",
        "bank_clusters", "members6", "group_of", "test_pool6", "partners6", "partners5", "t5_pool"))
    print("items %d, built in %.1f s" % (len(items), time.monotonic() - t0), flush=True)

    # ---- evaluate every packet: preflight one of each form in THIS process first, then the pool
    _init(str(root))
    for probe in [next(x for x in items if form in x) for form in ("world", "worlds") if any(form in x for x in items)]:
        first = _evaluate(probe)
        if "error" in first:
            raise SystemExit("PREFLIGHT_ITEM_FAILED: %s" % (first["error"] if probe["split"] not in SPLITS_SECRET
                                                            else first["error"].split(":")[0]))
    rows, t1 = [], time.monotonic()
    if args.processes <= 1:
        for item in items:
            rows.append(_evaluate(item))
            if len(rows) % 500 == 0:
                print("  evaluated %d / %d (%.0f s)" % (len(rows), len(items), time.monotonic() - t1), flush=True)
    else:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=args.processes, mp_context=multiprocessing.get_context("spawn"),
                                                          initializer=_init, initargs=(str(root),))
        try:
            for row in executor.map(_evaluate, items, chunksize=4, timeout=POOL_TOTAL_SECONDS):
                rows.append(row)
                if len(rows) % 500 == 0:
                    print("  evaluated %d / %d (%.0f s)" % (len(rows), len(items), time.monotonic() - t1), flush=True)
        except (concurrent.futures.process.BrokenProcessPool, TimeoutError) as error:
            executor.shutdown(wait=False, cancel_futures=True)
            raise SystemExit("POOL_FAILED: %s after %d of %d items" % (type(error).__name__, len(rows), len(items)))
        executor.shutdown(wait=True)
    evaluation_seconds = round(time.monotonic() - t1, 1)
    rows_by_item = {r["item_id"]: r for r in rows}
    ok_rows = [r for r in rows if "error" not in r]
    errors = [r for r in rows if "error" in r]
    split_of = lambda iid: iid.split("|")[0]                                   # noqa: E731
    problems = {
        "errors": [[split_of(r["item_id"]), r["error"] if split_of(r["item_id"]) not in SPLITS_SECRET else r["error"].split(":")[0]]
                   for r in errors][:20],
        "error_count": len(errors),
        "admissible_count_unexpected": sum(1 for r in ok_rows if r["admissible_count"] != r["expected_admissible_count"]),
        "independent_gold_disagrees": sum(1 for r in ok_rows if not r["independent_gold_agrees"]),
        "comparator_scoring_inconsistent": sum(1 for r in ok_rows if not r["comparator_scoring_consistent"]),
        "reader_or_route_check_failed": sum(1 for r in ok_rows if not r["reader_ok"]),
        "duplicate_record_ids": len(rows) - len({r.get("record_id") for r in rows}),
        "twin_profile_mismatches": sum(1 for cell, cs in bank_clusters.items() if not cell.endswith("RELAXED")
                                       for c in cs if "profiles_equal" in c and not c["profiles_equal"]),
    }
    build_ok = not any(v for k, v in problems.items() if k != "errors")
    items_by_cluster = collections.defaultdict(list)
    for item in items:
        items_by_cluster[item["cluster_id"]].append(item)

    # ---- cells (s7: printed before any model is read)
    summaries, tables = {}, {}
    role = lambda split, cell: (outn["role_override"] or  # noqa: E731
                                ("PRIMARY_CLAIM_CANDIDATE" if split in SPLITS_SECRET and cell in ("REACH_FIRST_DIRECT", "REACH_BFS", "ANALOGY", "CORRESPONDENCE")
                                 else "DEVELOPMENT_FEEDBACK" if split in SPLITS_PUBLIC and cell != "PARTS" and cell != "EDGE_ACCOUNT"
                                 else "DIAGNOSTIC"))
    if build_ok:
        for split, seed in (("DEV_NEW_6", S0.DEV_SEED), ("TEST_NEW_6", salt2)) if args.only in (None, "reach") else ():
            for cell in ("REACH_FIRST_DIRECT", "REACH_BFS", "PARTS", "EDGE_ACCOUNT"):
                members = [c for c in single_clusters if c["split"] == split and c["cell"] == cell]
                s = summarise_reach_cell(hw, A, cell, members, rows_by_item, items_by_cluster, seed, role(split, cell))
                s["cell"] = "%s/%s" % (split, cell)
                if cell.startswith("REACH"):
                    s["trained_course_answer_states_for_this_rule"] = trained[cell]
                summaries[s["cell"]], tables[s["cell"]] = s, members
        for name, members in bank_clusters.items():
            split, cell = name.split("/")
            kind = "analogy" if cell.startswith("ANALOGY") else "correspondence"
            s = summarise_bank_cell(A, name, kind, members, rows_by_item, role(split, cell))
            s["trained_course_answer_states_for_this_kind"] = trained[kind]
            s["eligible_foci_full_pool"] = eligible_full_counts[name]
            summaries[name], tables[name] = s, members
    if build_ok and "TEST_NEW_6/ANALOGY" in summaries:
        s = summaries["TEST_NEW_6/ANALOGY"]
        eligible = set(elig["TEST_NEW_6/ANALOGY"])
        rest = [k for k in test6_use if k not in eligible]

        def profile(keys):
            return {"count": len(keys),
                    "edge_count_histogram": dict(sorted(collections.Counter(str(len(S0.key_shape(k)[1])) for k in keys).items())),
                    "test_side_group_size_mean": (round(sum(len(members6[group_of[k]] & test_pool6) for k in keys) / len(keys), 3)
                                                  if keys else None),
                    "roots_histogram": dict(sorted(collections.Counter(str(len(hw.roots(*S0.key_shape(k)))) for k in keys).items()))}
        s["eligible_foci_versus_rest_of_test"] = {"eligible": profile(sorted(eligible)), "rest": profile(rest)}
    sdr = smallest_detectable_regression(A)
    claims = {
        "REACH_3_STEP_TRANSFER_6": ("TEST_NEW_6/REACH_FIRST_DIRECT", "TEST_NEW_6/REACH_BFS"),
        "REACH_4_STEP_TRANSFER_6": ("TEST_NEW_6/REACH_FIRST_DIRECT", "TEST_NEW_6/REACH_BFS"),
        "ANALOGY_BEYOND_DEGREE_6": ("TEST_NEW_6/ANALOGY",),
        "CORRESPONDENCE_BEYOND_DEGREE_6": ("TEST_NEW_6/CORRESPONDENCE",),
        "CORRESPONDENCE_BEYOND_DEGREE_5": ("TEST_NEW_5/CORRESPONDENCE",)}

    def cell_floor(claim, cell):
        s = summaries.get(cell)
        if s is None:
            return None
        return s["claims"][claim] if "claims" in s else s

    def cell_views(claim, cell):
        f = cell_floor(claim, cell)
        return f["a2_views"] if f is not None and "a2_views" in f else None

    claims_table = {}
    for claim, cells in claims.items():
        floors = {c: cell_floor(claim, c) for c in cells}
        testable = all(f is not None and f["can_carry_a_claim"] for f in floors.values())
        claims_table[claim] = {"cells": list(cells), "per_arm": "evaluated per arm, both arms always reported (s7.1)",
                               "bars": ("every registered reach comparator except the two built on three-hop (%s)"
                                        % ", ".join(BUILT_ON_THREE_HOP) if claim == "REACH_3_STEP_TRANSFER_6"
                                        else "every registered comparator of the cell's kind"),
                               "can_carry_a_claim_before_any_model": testable,
                               "status_if_not": None if testable else "NOT_TESTABLE",
                               "binding_W": {c: (f["binding_W"] if f else None) for c, f in floors.items()},
                               "original_calculation_label": ORIGINAL_VIEW_LABEL,
                               "codex_A2_3_role": ("MANDATORY_EXPLORATORY: report EXPLORATORY_NOMINAL_PASS, "
                                                   "EXPLORATORY_NO_NOMINAL_PASS or NOT_TESTABLE; no confirmatory "
                                                   "allocation"),
                               "a2_views_binding_W_printed_not_binding": {
                                   c: ({v: cell_views(claim, c)["binding_by_view"][v]["W"] for v in VIEWS}
                                       if cell_views(claim, c) else None) for c in cells},
                               "scope_sentence": SCOPE_SENTENCE}
    for claim, why in DECLARED_NOT_TESTABLE.items():
        claims_table[claim] = {"cells": [], "can_carry_a_claim_before_any_model": False, "status_if_not": "NOT_TESTABLE",
                               "declared_before_any_build": why}
    # Codex A2.3 (PROPOSED): the one confirmatory claim. Before any model it can only be NOT_TESTABLE or open.
    an = summaries.get("TEST_NEW_6/ANALOGY")
    if an is not None:
        reasons = ([] if an["can_carry_a_claim"] else ["original floor: %s" % an["why_not"]])
        reasons += ["A2.4: %s" % r for r in an["a2_views"]["floors"]["not_testable_reasons"]]
        claims_table["REPAIR_IMPROVES_ANALOGY_6"] = {
            "cells": ["TEST_NEW_6/ANALOGY"], "codex_A2_3_role": "THE_ONE_CONFIRMATORY_CLAIM (PROPOSED)",
            "requires": ["REPAIR_BEATS_UNCHANGED_ANALOGY in all 3 seed pairs, in the degree-group and shared-shape "
                         "views (and the original cluster calculation as an extra CONDITIONAL_CLUSTER_DIAGNOSTIC "
                         "condition)", "ANALOGY_BEYOND_DEGREE_6[repaired] against every registered analogy bar, in "
                         "both added views", "the corrected mechanism gate (A2.6; outside this builder)",
                         "no regression detected by the listed paired tests (s7.2)"],
            "inferential_p": "the largest degree-group or shared-shape-component p over every required comparison "
                             "and all three seed pairs; never 0.01 ** 3; never a product of seed p-values",
            "can_carry_a_claim_before_any_model": not reasons, "status_if_not": None if not reasons else "NOT_TESTABLE",
            "not_testable_reasons": reasons,
            "repaired_vs_unchanged_informative_count": "NOT_YET_OBSERVED",
            "inference_assumptions": "see inference_assumptions (top level)"}
    v_cells = sorted({c for claim, cells in claims.items() for c in cells if cell_floor(claim, c) and cell_floor(claim, c)["can_carry_a_claim"]})
    all_claim_cells = sorted({c for cells in claims.values() for c in cells})
    gates = {"pinned_program": {"path": GATES_PROGRAM, "sha256_lf": GATES_PROGRAM_LF_SHA256,
                                "observed": identity["gates_program"]["observed_sha256_lf"]},
             "smallest_detectable_regression_c_prime_with_b_prime_0": sdr,
             "H1": {"id": "G_LEARN_population", "unit": "Helm's historical held-back questions (the program's own)",
                    "smallest_detectable_regression": sdr},
             "H2": {"id": "G_LEARN_all_kinds", "unit": "Helm's historical held-back questions (the program's own)",
                    "smallest_detectable_regression": sdr},
             "V": [{"cell": c, "unit": "the cell's clusters", "clusters": summaries[c]["clusters"] if "clusters" in summaries[c] else summaries[c]["primary_clusters"],
                    "smallest_detectable_regression": sdr} for c in v_cells],
             "left_out_cells_cannot_carry_a_claim": [c for c in all_claim_cells if c not in v_cells]}
    family_wise = ("up to %d testable base claims per arm, each with a nominal false-pass risk of at most about %s per "
                   "run; none pooled; under Codex A2.3 (PROPOSED) they are mandatory exploratory results with no "
                   "study-wide guarantee, and only REPAIR_IMPROVES_ANALOGY_6 is confirmatory" % (
                       sum(1 for k in claims if claims_table[k]["can_carry_a_claim_before_any_model"]), ALPHA))
    # ---- Codex A2.4 (PROPOSED): the feasibility table, per registered cell and claim (counts only; no membership)
    feasibility_rows = []
    for name, s in sorted(summaries.items()):
        blocks = ([(claim, b) for claim, b in s["claims"].items()] if "claims" in s else [(None, s)])
        for claim, b in blocks:
            if "a2_views" in b:
                feasibility_rows.append({"cell": name, "claim": claim, "claim_role": s.get("claim_role"), **b["a2_views"]})
    feasibility = {
        "label": LABEL,
        "table_state": ("ACTUAL_AGGREGATES_OF_THIS_BUILD: Codex A2.4 accepts them only from the authorized custodian "
                        "build" if mode == "SEALED_BUILD" else
                        "THROWAWAY: throwaway salts; an estimate of the table's shape only; NOT the A2.4 table and "
                        "never a result"),
        "rows": feasibility_rows,
        "conditional_sign_power_by_unit_count": sign_power_table(
            [u for r in feasibility_rows for u in r["units"].values()]),
        "repaired_vs_unchanged_informative_count": "NOT_YET_OBSERVED (A2.4: unknowable before both arms are scored)"}
    inference_assumptions = {
        "state": "OPEN_FOR_THE_BUILDER_SCORER_REVIEW",
        "rule": ("Codex A2.2: a p-value is conditional on independent units and exchangeable paired signs under the "
                 "null; the builder/scorer review states whether the sampling construction supports them; if it "
                 "cannot, the status is INFERENCE_ASSUMPTIONS_UNSUPPORTED (all scores and conditional p-values still "
                 "reported; no confirmatory claim)"),
        "known_dependencies_by_construction": [
            "both presentations and both twins (or MATCH/NO_MATCH, MAPPING/NO_MATCH) of a focus form one cluster",
            "reach: several rooted questions of one shape are separate clusters; they share a degree group",
            "analogy decoys and correspondence NO_MATCH targets come from the focus's own degree group, so foci of "
            "one group can appear in each other's packets (the same degree-group unit)",
            "analogy fillers come from other degree groups; a shared filler joins two groups into one component",
            "every TEST_NEW_6 focus comes from one salted MIX-sampler draw without replacement; the units are not "
            "independent draws from a fixed population",
            "reach: the ABSENT / DIRECT / VIA balancing chooses primary clusters by a salted order within each state",
            "reach: the frozen 64-world training bank rides unchanged in every reach packet (not a listed role)"]}

    # ---- write
    pub, sealed = pathlib.Path(args.out_public), pathlib.Path(args.out_sealed)
    pub.mkdir(parents=True, exist_ok=True)
    sealed.mkdir(parents=True, exist_ok=True)

    def dump(path, value):
        data = json.dumps(value, indent=1, sort_keys=True).encode("utf-8")
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def payload(names):
        return {"items": [dict(i, evaluation=rows_by_item.get(i["item_id"])) for i in items if i["split"] in names],
                "clusters": {k: v for k, v in tables.items() if k.split("/")[0] in names}}
    sealed_sha = dump(sealed / outn["sealed"], {
        "schema": "claude.hset2-sealed/0.1", "custody": "CLAUDE_ONLY_NEVER_COMMIT", "label": LABEL, "identity": identity,
        "splits": {"TEST_NEW_6": test6, "WITHHELD_6": withheld6, "TEST_NEW_5": test5, "WITHHELD_5": withheld5},
        "eligible_foci": {c: v for c, v in elig.items() if c.split("/")[0] in SPLITS_SECRET},
        "test_new_6_draws": test_draws, **payload(SPLITS_SECRET)})
    public_sha = dump(pub / outn["public"], {
        "schema": "claude.hset2-public-cells/0.1", "label": LABEL, "identity": identity,
        "splits": {"DEV_NEW_6": dev6, "DEV_DECOYS_6_digest": summary0["dev_decoys_6"]["digest"], "DEV_NEW_5": dev5},
        "eligible_foci": {c: v for c, v in elig.items() if c.split("/")[0] in SPLITS_PUBLIC}, **payload(SPLITS_PUBLIC)})
    summary = {"schema": SCHEMA_SUMMARY, "label": LABEL, "mode": mode, "build_ok": build_ok, "problems": problems,
               "identity": identity, "design": DESIGN_BASIS,
               "status": "BUILD_ONLY: no model was run; nothing here is a result about Helm",
               "throwaway_warning": (None if mode == "SEALED_BUILD" else
                                     "THROWAWAY_NOT_DEV: throwaway salts; its 'DEV_NEW_5' holds real TEST_NEW_5 and "
                                     "WITHHELD_5 classes; never use any of these files as development feedback"),
               "custody_label": "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT",
               "limit_foci": args.limit_foci,
               "splits": {"five_nodes": {"classes": 267, "DEV_NEW_5": len(dev5), "TEST_NEW_5": len(test5),
                                         "WITHHELD_5": len(withheld5), "PUBLIC_EXCLUDED_5": sum(1 for r in pe["classes"] if r["nodes"] == 5),
                                         "test_new_5_shapes_digest": test5_digest, "strata": strata5},
                          "six_nodes": {"classes": summary0["six_node_universe"]["classes_enumerated"],
                                        "dev_side": len(dev_side), "test_side": len(test_side), "DEV_NEW_6": len(dev6),
                                        "DEV_DECOYS_6": len(dev_decoys6), "TEST_NEW_6": len(test6), "WITHHELD_6": len(withheld6),
                                        "test_new_6_draws": test_draws, "test_new_6_shapes_digest": hw.sha(sorted(test6)),
                                        "collision_share_printed_never_required": round(
                                            sum(1 for k in test6 if partners6(test_pool6)(k)) / len(test6), 6)},
                          "five_nodes_collision_share_printed_never_required": round(
                              sum(1 for k in test5 if partners5(t5_pool)(k)) / len(test5), 6),
                          "disjointness": disjoint, "public_excluded_class_digests_digest": pe["class_digests_digest"]},
               "eligible_foci_full_pools": eligible_full_counts,
               "counts": {"items": len(items), "items_by_split": dict(collections.Counter(i["split"] for i in items)),
                          "items_by_kind": dict(collections.Counter(i["kind"] for i in items))},
               "cells": summaries, "claims_before_any_model": claims_table, "family_wise_risk": family_wise,
               "no_regression_gates": gates, "scope_sentence": SCOPE_SENTENCE,
               "success_rule": ("BEATS_ALL_REGISTERED_BARS per cell per run: for every registered comparator X of the "
                                "cell, b_X > c_X and exact one-sided p(b_X, b_X + c_X) <= 0.01; no zero-loss veto (s7); "
                                "labelled %s under Codex A2.2 (PROPOSED), which adds the degree-group and "
                                "shared-shape-component views (B > C, positive overall accuracy difference, exact "
                                "sign tail <= 0.01)" % ORIGINAL_VIEW_LABEL),
               "a2_4_feasibility": feasibility, "inference_assumptions": inference_assumptions,
               "files": {outn["public"]: public_sha, outn["sealed"]: sealed_sha},
               "evaluation_seconds": evaluation_seconds, "seconds": round(time.monotonic() - t0, 1)}
    dump(pub / outn["summary"], summary)
    print("\n%-34s %5s %6s %-30s %6s  %s" % ("cell", "n", "bindW", "binding comparator", "groups", "can carry a claim"))
    for name, s in sorted(summaries.items()):
        blocks = s["claims"].items() if "claims" in s else [(None, s)]
        for claim, b in blocks:
            if "binding_W" not in b:
                continue
            print("%-34s %5d %6d %-30s %6s  %s%s" % (name, b["clusters"], b["binding_W"], b["binding_comparator"],
                                                     b.get("distinct_degree_groups") or "-",
                                                     "yes" if b["can_carry_a_claim"] else "NO: %s" % b["why_not"],
                                                     "  [%s]" % claim if claim else ""))
    print("\nCodex A2.4 feasibility (%s)" % feasibility["table_state"].split(":")[0])
    print("%-34s %-24s %17s %20s  %s" % ("cell", "claim", "units c/g/k", "binding W c/g/k", "A2.4 floors"))
    for r in feasibility_rows:
        u, b = r["units"], r["binding_by_view"]
        print("%-34s %-24s %17s %20s  %s" % (
            r["cell"], r["claim"] or "-", "%d/%d/%d" % (u["original_cluster"], u["degree_group"], u["shared_shape_component"]),
            "%d/%d/%d" % tuple(b[v]["W"] for v in VIEWS),
            ("met" if r["floors"]["meets_every_floor"] else "NOT_TESTABLE: " + "; ".join(r["floors"]["not_testable_reasons"]))
            + ("" if r["floors"]["applies"].startswith("BINDING") else " (printed, not binding)")))
    print("registered_comparators_digest %s" % identity["registered_comparators_digest"])
    print(json.dumps({"build_ok": build_ok, "problems": problems, "evaluation_seconds": evaluation_seconds,
                      "seconds": summary["seconds"]}), flush=True)
    return 0 if build_ok else 2


if __name__ == "__main__":
    sys.exit(main())
