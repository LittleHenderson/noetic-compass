"""E1b scorer: the sealed HSET-2 TEST readout and every claim label (readout plan item 10). Pure Python; no torch.

Label: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT. Rules: EVALUATION_DESIGN_v0_4.md
sections 5, 7, 8 and Amendment A2 (A2.2 views, A2.3 labels, A2.4 floors, A2.5 endpoint, A2.6 wording), as fixed at
c3a128ee. It turns per-item right/wrong for six final.pt readings into every registered label. It never decides a
number itself where the builder already has a function: the three views come from the builder's own
`evaluate_cell_views` and `paired_views` (hset2_build.py at the commit P2 ran), imported from `--hset2-dir`, and the
scorer refuses unless that code is byte-identical (LF sha256) to what the sealed build recorded in its identity.

WHAT IS READ, AND WHEN (prereg A5.1, A5.3, A5.5; plan item 10):
  * a repaired run is read only if the A5.5 matched-start reading says MATCHED_START_REPRODUCED;
  * a repaired run's ANALOGY items are read only if the ITEM2 reading (probe v0.3) says mechanism_gate CLEARED and
    ITEM2_PASS, bound to these final.pt files; otherwise they are never predicted (NOT_READ_MECHANISM_GATE_OPEN);
  * a historical Helm 2.0 control (seeds 20260918, 20260919) is read only if the U17 reproduction reading says
    STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED (option C);
  * the fresh unchanged run U17 is always read.
A run that is not read stays unread: TEST is read once per registered run (s7.3), so nothing here reads it "for now".

LABELS (all printed, every time; none is ever dropped):
  REPAIR_IMPROVES_ANALOGY_6 (the one confirmatory claim, A2.3): PASS (with the A2.3 caption) or FAIL, unless a
    status word applies, in this fixed order: NOT_TESTABLE, MECHANISM_GATE_OPEN, COMPARISON_INCOMPLETE,
    INFERENCE_ASSUMPTIONS_UNSUPPORTED. Every word that applies is listed, with every reason and score.
  the s7.1 base claims per arm, each seed-pair REPAIR_BEATS_UNCHANGED_<cell>, every cell result per arm and the
    analogy distractor halves (A1 D5): EXPLORATORY_NOMINAL_PASS, EXPLORATORY_NO_NOMINAL_PASS, NOT_TESTABLE,
    COMPARISON_INCOMPLETE or NOT_READ_MECHANISM_GATE_OPEN;
  the no-regression gates H1, H2 and V:<cell> per seed pair: NO_REGRESSION_DETECTED, REGRESSION_DETECTED,
    LEFT_OUT_CANNOT_CARRY_A_CLAIM, NOT_READ_MECHANISM_GATE_OPEN or COMPARISON_INCOMPLETE.
  INFERENCE_ASSUMPTIONS_UNSUPPORTED is the default until a committed ruling record says SUPPORTED (bus claude-0024 Q-D).

CUSTODY (design s8). Public output: counts, p-values, accuracies, labels, code and input-record digests. Never an item
id, record id, cluster id, class key, answer, per-item flag, or any digest whose input contains an answer (not even the
sealed file's own sha256). All per-item and per-cluster detail goes to the sealed document only.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys
from fractions import Fraction

LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
CUSTODY_LABEL = "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT"
SCHEMA_PUBLIC = "claude.e1b-readout-public/0.1"
SCHEMA_SEALED = "claude.e1b-readout-sealed/0.1"
SCHEMA_RUNS = "claude.e1b-runs/0.1"
SCHEMA_INFERENCE_RULING = "claude.e1b-inference-ruling/0.1"
SCHEMA_ITEM2 = "claude.item2-reading/0.3"
SCHEMA_MATCHED_START = "helm.matched-start-reading/0.1"
SCHEMA_REPRODUCTION = "cncm.helm-unchanged-reproduction-reading/0.5"
H1H2_READER = "h1h2-paired/1.0"
SEALED_SCHEMA = "claude.hset2-sealed/0.1"
SEEDS = (20260917, 20260918, 20260919)
ARMS = ("repaired", "unchanged")
PROVENANCES = {"repaired": ("fresh_repaired",), "unchanged": ("fresh_unchanged", "historical_helm2")}
MODES = {"SEALED_BUILD": "SEALED_TEST_READOUT", "THROWAWAY_SALTS_NOT_A_BUILD": "THROWAWAY_STAND_IN_NOT_A_RESULT"}
ALPHA = Fraction(1, 100)

REACH_CELLS = ("TEST_NEW_6/REACH_FIRST_DIRECT", "TEST_NEW_6/REACH_BFS")
ANALOGY_CELL = "TEST_NEW_6/ANALOGY"
CORR6, CORR5 = "TEST_NEW_6/CORRESPONDENCE", "TEST_NEW_5/CORRESPONDENCE"
CLAIM_CELLS = REACH_CELLS + (ANALOGY_CELL, CORR6, CORR5)
PAIRED_LABEL = {REACH_CELLS[0]: "REPAIR_BEATS_UNCHANGED_REACH_FIRST_DIRECT",
                REACH_CELLS[1]: "REPAIR_BEATS_UNCHANGED_REACH_BFS", ANALOGY_CELL: "REPAIR_BEATS_UNCHANGED_ANALOGY",
                CORR6: "REPAIR_BEATS_UNCHANGED_CORRESPONDENCE", CORR5: "REPAIR_BEATS_UNCHANGED_CORRESPONDENCE_5"}
CONFIRMATORY = "REPAIR_IMPROVES_ANALOGY_6"
HALVES = (("WITH_SAME_DOMAIN_DISTRACTOR", True), ("WITHOUT_DISTRACTOR", False))
REPRODUCED_U17 = "STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED"
MATCHED = "MATCHED_START_REPRODUCED"

PASS, FAIL = "PASS", "FAIL"
NOT_TESTABLE = "NOT_TESTABLE"
IAU = "INFERENCE_ASSUMPTIONS_UNSUPPORTED"
MGO = "MECHANISM_GATE_OPEN"
INCOMPLETE = "COMPARISON_INCOMPLETE"
EXP_PASS, EXP_NO = "EXPLORATORY_NOMINAL_PASS", "EXPLORATORY_NO_NOMINAL_PASS"
NOT_READ_GATE = "NOT_READ_MECHANISM_GATE_OPEN"
NO_REG, REG = "NO_REGRESSION_DETECTED", "REGRESSION_DETECTED"
LEFT_OUT = "LEFT_OUT_CANNOT_CARRY_A_CLAIM"
CONFIRMATORY_PRECEDENCE = (NOT_TESTABLE, MGO, INCOMPLETE, IAU)
STATUS_VOCABULARY = {
    "confirmatory": [PASS, FAIL] + list(CONFIRMATORY_PRECEDENCE),
    "exploratory": [EXP_PASS, EXP_NO, NOT_TESTABLE, INCOMPLETE, NOT_READ_GATE],
    "no_regression": [NO_REG, REG, LEFT_OUT, NOT_READ_GATE, INCOMPLETE],
    "run": ["READ", "READ_WITHOUT_ANALOGY_MECHANISM_GATE_OPEN", "NOT_READ_MATCHED_START_NOT_REPRODUCED",
            "NOT_READ_CONTROL_NOT_ADMITTED", "RUN_READING_INVALID"],
    "stage0": ["CUSTODY_MANIFEST_PASS", "CUSTODY_MANIFEST_STOP"]}
CAPTION_A2_3 = ("The repair improved registered six-node analogy performance in all three seed pairs, cleared the "
                "registered bars and mechanism checks, and had no regression detected by the listed tests.")
NO_REGRESSION_CAPTION = "no regression detected by the listed paired tests"
FORBIDDEN_WORDING = ("no ability lost", "preserved performance", "noninferior")
DECLARED_NOT_TESTABLE_REASON = "declared NOT_TESTABLE in design s1/s7.1 before any build"


class Refused(Exception):
    """A fixed refusal code. The code never contains TEST content (no key, id or answer)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def lf_sha256(path):
    return sha256_bytes(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n"))


# ================================================================================================ the builder's code
def load_builder(hset2_dir):
    """(hset2_build, hset1a_build) imported from `hset2_dir`, a folder laid out like helm_eval_design_20260923/
    (hset2/, hset1a/, d1_acceptance/) at the commit P2 ran. Refuses a module found anywhere else."""
    root = pathlib.Path(hset2_dir).resolve()
    for sub in ("d1_acceptance", "hset1a", "hset2"):
        if not (root / sub).is_dir():
            raise Refused("HSET2_DIR_LAYOUT:%s" % sub)
        if str(root / sub) not in sys.path:
            sys.path.insert(0, str(root / sub))
    sys.dont_write_bytecode = True
    import hset1a_build as A
    import hset2_build as B
    for module, sub in ((B, "hset2"), (A, "hset1a")):
        if pathlib.Path(module.__file__).resolve().parent != root / sub:
            raise Refused("BUILDER_IMPORTED_FROM_ELSEWHERE:%s" % module.__name__)
    return B, A


def builder_identity(B):
    """The LF sha256 of every builder file the sealed build recorded, and the registered-comparator digest."""
    import hset_worlds as hw
    here = pathlib.Path(B.__file__).resolve().parent
    return {"builder_sha256_lf": lf_sha256(B.__file__), "stage0_sha256_lf": lf_sha256(here / "hset2_stage0_public.py"),
            "hset_worlds_sha256_lf": lf_sha256(B.HSET1A_DIR / "hset_worlds.py"),
            "hset1a_build_sha256_lf": lf_sha256(B.HSET1A_DIR / "hset1a_build.py"),
            "hset1b_build_sha256_lf": lf_sha256(B.HSET1A_DIR / "hset1b_build.py"),
            "oracle_sha256_lf": lf_sha256(B.ORACLE_DIR / "oracle_isomorphism.py"),
            "registered_comparators_digest": hw.sha(B.registered_comparators())}


def check_builder_identity(B, sealed_identity):
    observed = builder_identity(B)
    bad = sorted(k for k, v in observed.items() if sealed_identity.get(k) != v)
    if bad:
        raise Refused("BUILDER_CODE_IS_NOT_THE_SEALED_BUILDS:%s" % ",".join(bad))
    return observed


# ================================================================================================ inputs
def load_sealed_and_summary(B, sealed_bytes, summary_bytes):
    """The sealed build file and its public summary, bound to each other by the summary's own file digest."""
    try:
        sealed, summary = json.loads(sealed_bytes), json.loads(summary_bytes)
    except ValueError:
        raise Refused("SEALED_OR_SUMMARY_NOT_JSON")
    if sealed.get("schema") != SEALED_SCHEMA or not isinstance(sealed.get("identity"), dict):
        raise Refused("SEALED_SCHEMA")
    mode = sealed["identity"].get("mode")
    if mode not in MODES or summary.get("mode") != mode:
        raise Refused("SEALED_MODE:%s" % mode)
    if summary.get("build_ok") is not True:
        raise Refused("SUMMARY_BUILD_NOT_OK")
    name = B.output_names(mode)["sealed"]
    if (summary.get("files") or {}).get(name) != sha256_bytes(sealed_bytes):
        raise Refused("SUMMARY_NOT_BOUND_TO_THIS_SEALED_FILE")
    if (summary.get("identity") or {}).get("registered_comparators_digest") != sealed["identity"].get(
            "registered_comparators_digest"):
        raise Refused("SUMMARY_AND_SEALED_COMPARATORS_DIFFER")
    return sealed, summary, mode


def forbidden_keys(sealed):
    """Design s3: the whole TEST side at 6 nodes (TEST_NEW_6 and WITHHELD_6), TEST_NEW_5 and WITHHELD_5."""
    splits = sealed.get("splits") or {}
    want = ("TEST_NEW_6", "WITHHELD_6", "TEST_NEW_5", "WITHHELD_5")
    if not all(isinstance(splits.get(s), list) for s in want):
        raise Refused("SEALED_SPLITS_MISSING")
    return sorted({k for s in want for k in splits[s]})


def cell_members(sealed, summary, three):
    """{cell: clusters of the claim unit} (reach: PRIMARY clusters only) and {cluster_id: [item ids]}. Every count must
    equal the public summary's (the A2.4 table the owner saw)."""
    items_of = collections.defaultdict(list)
    for item in sealed.get("items", ()):
        items_of[item["cluster_id"]].append(item["item_id"])
    members = {}
    for cell in CLAIM_CELLS:
        clusters = (sealed.get("clusters") or {}).get(cell)
        s = (summary.get("cells") or {}).get(cell)
        if not isinstance(clusters, list) or not isinstance(s, dict):
            raise Refused("SEALED_OR_SUMMARY_CELL_MISSING:%s" % cell)
        if cell in REACH_CELLS:
            clusters = [c for c in clusters if c.get("role") == "PRIMARY"]
            expected = s["claims"][three]["clusters"]
        else:
            expected = s["clusters"]
        if len(clusters) != expected:
            raise Refused("SUMMARY_SEALED_CLUSTER_COUNT:%s" % cell)
        if any(not items_of.get(c["cluster_id"]) for c in clusters):
            raise Refused("CLUSTER_WITHOUT_ITEMS:%s" % cell)
        members[cell] = clusters
    return members, dict(items_of)


def floors(summary, three, four):
    """Before-any-model floors from the public summary: per claim, per cell, V set, distractor halves, and A2.4."""
    cbm, cells = summary["claims_before_any_model"], summary["cells"]

    def why_not(name):
        row = cbm[name]
        if row.get("declared_before_any_build"):
            return [row["declared_before_any_build"]]
        out = []
        for c in row.get("cells", []):
            block = cells[c]["claims"][name] if "claims" in cells[c] else cells[c]
            if not block["can_carry_a_claim"]:
                out.append("floor %s: %s" % (c, block.get("why_not")))
        return out or list(row.get("not_testable_reasons") or ["the build says it cannot carry a claim"])
    claim = {name: {"can_carry": bool(cbm[name]["can_carry_a_claim_before_any_model"]),
                    "reasons": [] if cbm[name]["can_carry_a_claim_before_any_model"] else why_not(name)}
             for name in cbm}
    cell = {}
    for c in CLAIM_CELLS:
        s = cells[c]
        cell[c] = {"can_carry": bool(s["can_carry_a_claim"]), "why_not": s.get("why_not")}
        if c in REACH_CELLS:
            cell[c]["claims"] = {k: {"can_carry": bool(s["claims"][k]["can_carry_a_claim"]),
                                     "why_not": s["claims"][k].get("why_not")} for k in (three, four)}
    gates = summary["no_regression_gates"]
    v_cells = [row["cell"] for row in gates["V"]]
    halves = {half: {"can_carry": bool(cells[ANALOGY_CELL]["distractor_split_diagnostic"][half]["can_carry_a_claim"]),
                     "why_not": cells[ANALOGY_CELL]["distractor_split_diagnostic"][half].get("why_not")}
              for half, _ in HALVES}
    conf = cbm.get(CONFIRMATORY) or {"can_carry_a_claim_before_any_model": False,
                                     "not_testable_reasons": ["the build printed no row for %s" % CONFIRMATORY]}
    return {"claim": claim, "cell": cell, "v_cells": v_cells,
            "left_out": list(gates.get("left_out_cells_cannot_carry_a_claim", [])), "halves": halves,
            "confirmatory": {"can_carry": bool(conf["can_carry_a_claim_before_any_model"]),
                             "reasons": list(conf.get("not_testable_reasons") or [])},
            "smallest_detectable_regression": gates.get("smallest_detectable_regression_c_prime_with_b_prime_0")}


# ================================================================================================ prerequisites
def _record(raw):
    if raw is None:
        return None, None
    try:
        return json.loads(raw), sha256_bytes(raw)
    except ValueError:
        return "UNREADABLE", sha256_bytes(raw)


def read_runs(raw):
    try:
        doc = json.loads(raw)
    except ValueError:
        raise Refused("RUNS_NOT_JSON")
    runs = doc.get("runs") if isinstance(doc, dict) and doc.get("schema") == SCHEMA_RUNS else None
    if not isinstance(runs, list) or len(runs) != 6:
        raise Refused("RUNS_SCHEMA_OR_COUNT")
    seen = set()
    for run in runs:
        arm, seed = run.get("arm"), run.get("seed")
        if (arm not in ARMS or seed not in SEEDS or (arm, seed) in seen or run.get("provenance") not in PROVENANCES[arm]
                or run.get("switch") is not (arm == "repaired") or not isinstance(run.get("run_id"), str)
                or not isinstance(run.get("checkpoint_sha256"), str) or len(run["checkpoint_sha256"]) != 64):
            raise Refused("RUN_ROW:%s" % run.get("run_id"))
        seen.add((arm, seed))
    if len({r["run_id"] for r in runs}) != 6:
        raise Refused("RUN_IDS_NOT_UNIQUE")
    return runs


def read_item2(raw, runs):
    """Mechanism gate (A2.6, prereg v0.3 s7). CLEARED only for an ITEM2_PASS reading bound to these three finals."""
    rec, digest = _record(raw)
    out = {"record_sha256": digest, "gate": MGO, "outcome": None, "reasons": []}
    if rec is None:
        out["reasons"].append("ITEM2_READING_MISSING: the corrected probe has not read")
        return out
    if not isinstance(rec, dict) or rec.get("schema") != SCHEMA_ITEM2:
        out["reasons"].append("ITEM2_READING_SCHEMA_NOT_PROBE_V0_3")
        return out
    out["outcome"] = str(rec.get("outcome"))[:40]
    if rec.get("mechanism_gate") != "CLEARED":
        out["reasons"].append("ITEM2_MECHANISM_GATE_%s" % str(rec.get("mechanism_gate"))[:40])
    if rec.get("outcome") != "ITEM2_PASS":
        out["reasons"].append("ITEM2_OUTCOME_NOT_PASS")
    if rec.get("historical_gate_on_repaired_arm") != "MAY_RUN_FROZEN_EVALUATE_GATES":
        out["reasons"].append("ITEM2_READER_SAYS_G_LEARN_ON_NOT_READ")
    finals = {(r.get("model_seed"), r.get("checkpoint_relative_path")): r for r in rec.get("entries") or []
              if isinstance(r, dict)}
    for run in runs:
        if run["arm"] == "repaired":
            row = finals.get((run["seed"], "final.pt"))
            if row is None or row.get("checkpoint_sha256") != run["checkpoint_sha256"]:
                out["reasons"].append("ITEM2_NOT_BOUND_TO_THIS_FINAL:%d" % run["seed"])
    if len(finals) != 18 or any(r.get("verdict") != "PRESENT_GRAPH_AND_DOMAIN" or r.get("problems") != []
                                for r in finals.values()):
        out["reasons"].append("ITEM2_NOT_ALL_18_PRESENT_GRAPH_AND_DOMAIN")
    if not out["reasons"]:
        out["gate"] = "CLEARED"
    return out


def read_verdict(raw, schema, admitted_word, name):
    rec, digest = _record(raw)
    out = {"record_sha256": digest, "verdict": None, "admitted": False, "reasons": []}
    if rec is None:
        out["reasons"].append("%s_READING_MISSING" % name)
    elif not isinstance(rec, dict) or rec.get("schema") != schema:
        out["reasons"].append("%s_READING_SCHEMA" % name)
    else:
        out["verdict"] = str(rec.get("verdict"))[:60]
        out["admitted"] = rec.get("verdict") == admitted_word
        if not out["admitted"]:
            out["reasons"].append("%s_VERDICT_%s" % (name, out["verdict"]))
    return out


def read_inference_ruling(raw):
    """Q-D default: INFERENCE_ASSUMPTIONS_UNSUPPORTED until a committed ruling record says SUPPORTED."""
    rec, digest = _record(raw)
    out = {"record_sha256": digest, "supported": False, "ruling": None, "reasons": []}
    if rec is None:
        out["reasons"].append("NO_RULING_RECORD: default Q-D (bus claude-0024) prints %s until ruled" % IAU)
    elif (not isinstance(rec, dict) or rec.get("schema") != SCHEMA_INFERENCE_RULING
          or rec.get("ruling") not in ("SUPPORTED", "UNSUPPORTED") or not rec.get("ruled_by") or not rec.get("basis")):
        out["reasons"].append("RULING_RECORD_MALFORMED")
    else:
        out["ruling"], out["ruled_by"] = rec["ruling"], str(rec["ruled_by"])[:80]
        out["supported"] = rec["ruling"] == "SUPPORTED"
        if not out["supported"]:
            out["reasons"].append("RULED_UNSUPPORTED")
    return out


def read_h1h2(raw, seed):
    """One h1h2_paired.py document for one seed pair (wave-1 reader h1h2-paired/1.0). Counts are kept; ids are not."""
    rec, digest = _record(raw)
    out = {"record_sha256": digest, "state": "MISSING", "registered_view": False, "reasons": []}
    if rec is None:
        out["reasons"].append("H1H2_READING_MISSING")
        return out
    gates = {g.get("gate"): g for g in rec.get("gates", ()) if isinstance(g, dict)} if isinstance(rec, dict) else {}
    if (not isinstance(rec, dict) or rec.get("reader") != H1H2_READER or rec.get("seed") != seed
            or rec.get("status") not in ("READ", "READ_REPORT_INCOMPLETE") or set(gates) != {"H1", "H2"}
            or any(not isinstance(g.get("regression_flagged"), bool) for g in gates.values())):
        out["state"] = "INVALID"
        out["reasons"].append("H1H2_READING_NOT_A_VALID_READ_FOR_THIS_SEED")
        return out
    out["state"] = "READ"
    out["view"] = rec.get("view")
    out["registered_view"] = rec.get("view") == "REGISTERED_H1_H2"
    out["claim_bearing_inputs"] = rec.get("claim_bearing_inputs") is True
    if not out["registered_view"]:
        out["reasons"].append("H1H2_ONLY_NON_ANALOGY_VIEW_EXPLORATORY")
    if not out["claim_bearing_inputs"]:
        out["reasons"].append("H1H2_INPUTS_NOT_CLAIM_BEARING")
    for name, g in sorted(gates.items()):
        out[name] = {k: g.get(k) for k in ("questions", "b_prime_gains", "c_prime_losses", "ties", "p_one_sided",
                                           "regression_flagged", "unchanged_accuracy", "repaired_accuracy",
                                           "difference_accuracy_repaired_minus_unchanged", "question_set")}
    crossings = rec.get("old_gate_crossings") if isinstance(rec.get("old_gate_crossings"), dict) else {}
    out["old_gate_crossings"] = {"status": crossings.get("status"), "crossings": list(crossings.get("crossings") or [])}
    return out


def reading_plan(runs, prereq):
    """{run_id: {"read": bool, "analogy": bool, "status": word, "reasons": [...]}} (the admission rules above)."""
    plan = {}
    for run in runs:
        row = {"read": True, "analogy": True, "status": "READ", "reasons": []}
        if run["arm"] == "repaired" and not prereq["matched_start"]["admitted"]:
            row.update(read=False, analogy=False, status="NOT_READ_MATCHED_START_NOT_REPRODUCED",
                       reasons=list(prereq["matched_start"]["reasons"]))
        elif run["provenance"] == "historical_helm2" and not prereq["reproduction"]["admitted"]:
            row.update(read=False, analogy=False, status="NOT_READ_CONTROL_NOT_ADMITTED",
                       reasons=list(prereq["reproduction"]["reasons"]))
        elif run["arm"] == "repaired" and prereq["item2"]["gate"] != "CLEARED":
            row.update(analogy=False, status="READ_WITHOUT_ANALOGY_MECHANISM_GATE_OPEN",
                       reasons=list(prereq["item2"]["reasons"]))
        plan[run["run_id"]] = row
    return plan


def items_to_predict(plan, members, items_of):
    """{run_id: [item ids]}: every item of every claim-cell cluster, minus the analogy cell where it is not read."""
    out = {}
    for run_id, row in plan.items():
        if not row["read"]:
            continue
        cells = [c for c in CLAIM_CELLS if row["analogy"] or c != ANALOGY_CELL]
        out[run_id] = sorted(i for c in cells for cl in members[c] for i in items_of[cl["cluster_id"]])
    return out


# ================================================================================================ scoring
def cluster_right(members, items_of, item_right):
    """{cluster_id: bool} (right only if every item and presentation is right, design s5), or None if any is missing."""
    out = {}
    for c in members:
        values = [item_right.get(i) for i in items_of[c["cluster_id"]]]
        if any(v is None for v in values):
            return None
        out[c["cluster_id"]] = all(values)
    return out


def _compact_views(per_bar):
    return {x: {"overall_accuracy_difference": v["overall_accuracy_difference"],
                "original_cluster": {k: v["original_cluster"][k] for k in ("b", "c", "ties", "p_exact", "pass")},
                "degree_group": {k: v["degree_group"][k] for k in ("units", "B", "C", "ties", "p_exact", "pass")},
                "shared_shape_component": {k: v["shared_shape_component"][k]
                                           for k in ("units", "B", "C", "ties", "p_exact", "pass")}}
            for x, v in per_bar.items()}


def run_cell_block(B, A, members, bars, right):
    """One run, one cell, one bar list: the builder's evaluate_cell_views, kept as aggregates only."""
    ev = B.evaluate_cell_views(A, members, list(bars), right)
    n, k = len(members), sum(1 for c in members if right[c["cluster_id"]])
    largest = {v: str(max((Fraction(ev["per_bar"][x][v]["p_exact"]) for x in bars), default=Fraction(1)))
               for v in B.VIEWS}
    return {"clusters": n, "right_clusters": k, "cluster_accuracy": str(Fraction(k, n)) if n else None,
            "bars": len(bars), "passes_every_bar": dict(ev["passes_every_bar"]), "largest_p_exact": largest,
            "original_view_label": B.ORIGINAL_VIEW_LABEL, "per_bar": _compact_views(ev["per_bar"])}


def pair_block(B, A, members, rep_right, unch_right):
    """Repaired (a) against unchanged (b) on the same clusters: all three views, plus the s7.2 regression test."""
    groups, component_of = B.view_units(members)
    pv = B.paired_views(A, members, groups, component_of, rep_right, unch_right)
    gains, losses, ties = pv["original_cluster"]["b"], pv["original_cluster"]["c"], pv["original_cluster"]["ties"]
    p_reg = B.sign_tail_exact(losses, gains)
    n = len(members)
    return {"clusters": n,
            "repaired_right": sum(1 for c in members if rep_right[c["cluster_id"]]),
            "unchanged_right": sum(1 for c in members if unch_right[c["cluster_id"]]),
            "overall_accuracy_difference": pv["overall_accuracy_difference"],
            "original_cluster": {k: pv["original_cluster"][k] for k in ("label", "b", "c", "ties", "p_exact", "pass")},
            "degree_group": {k: pv["degree_group"][k] for k in ("units", "B", "C", "ties", "p_exact", "pass")},
            "shared_shape_component": {k: pv["shared_shape_component"][k]
                                       for k in ("units", "B", "C", "ties", "p_exact", "pass")},
            "regression": {"b_prime_gains": gains, "c_prime_losses": losses, "ties": ties, "p_exact": str(p_reg),
                           "flagged": losses > gains and p_reg <= ALPHA}}


def score(B, A, sealed, summary, runs, plan, item_right, invalid, prereq, h1h2):
    """Every label. item_right: {run_id: {item_id: bool}}; invalid: {run_id: [error type names]}.
    Returns (public part, sealed part)."""
    three, four = B.reach_claim_names()
    fl = floors(summary, three, four)
    members, items_of = cell_members(sealed, summary, three)
    by_id = {r["run_id"]: r for r in runs}
    runs_of = {(r["arm"], r["seed"]): r["run_id"] for r in runs}
    bars_of = {ANALOGY_CELL: list(B.analogy_comparators()), CORR6: list(B.CORRESPONDENCE_COMPARATORS),
               CORR5: list(B.CORRESPONDENCE_COMPARATORS)}
    reach_bars = {k: list(v) for k, v in B.reach_claim_bars().items()}
    claim_cells = {three: [(c, three) for c in REACH_CELLS], four: [(c, four) for c in REACH_CELLS],
                   "ANALOGY_BEYOND_DEGREE_6": [(ANALOGY_CELL, None)],
                   "CORRESPONDENCE_BEYOND_DEGREE_6": [(CORR6, None)],
                   "CORRESPONDENCE_BEYOND_DEGREE_5": [(CORR5, None)]}

    def bars(cell, claim):
        return reach_bars[claim] if cell in REACH_CELLS else bars_of[cell]

    # ---- per run: cluster right/wrong per cell (None = not read or incomplete)
    run_state, rights = {}, {}
    for run in runs:
        rid, row = run["run_id"], plan[run["run_id"]]
        status = row["status"]
        if row["read"] and invalid.get(rid):
            status = "RUN_READING_INVALID"
        rights[rid] = {}
        for cell in CLAIM_CELLS:
            ok = row["read"] and status != "RUN_READING_INVALID" and (row["analogy"] or cell != ANALOGY_CELL)
            rights[rid][cell] = cluster_right(members[cell], items_of, item_right.get(rid, {})) if ok else None
        if status == "READ" or status.startswith("READ_WITHOUT"):
            if any(rights[rid][c] is None for c in CLAIM_CELLS if row["analogy"] or c != ANALOGY_CELL):
                status = "RUN_READING_INVALID"
                invalid.setdefault(rid, []).append("ITEM_RESULTS_INCOMPLETE")
                rights[rid] = {c: None for c in CLAIM_CELLS}
        run_state[rid] = {"run_id": rid, "arm": run["arm"], "seed": run["seed"], "provenance": run["provenance"],
                          "switch": run["switch"], "checkpoint_sha256": run["checkpoint_sha256"], "status": status,
                          "reasons": row["reasons"] + sorted(set(invalid.get(rid, []))),
                          "items_predicted": len(item_right.get(rid, {})),
                          "analogy_items_read": bool(row["read"] and row["analogy"])}

    def why_missing(rid, cell):
        st = run_state[rid]["status"]
        if st.startswith("READ_WITHOUT") and cell == ANALOGY_CELL:
            return NOT_READ_GATE, "%s: %s" % (rid, st)
        return INCOMPLETE, "%s: %s" % (rid, st)

    # ---- per run, per cell, per claim: the model against every registered bar (A2.2 views)
    cells_public = {}
    for cell in CLAIM_CELLS:
        cells_public[cell] = {}
        claims_here = [three, four] if cell in REACH_CELLS else [None]
        for rid in by_id:
            right = rights[rid][cell]
            cells_public[cell][rid] = None if right is None else {
                (claim or "cell"): run_cell_block(B, A, members[cell], bars(cell, claim), right) for claim in claims_here}
    labels = []

    where_fields = ("arm", "seed_pair", "cell", "gate", "claim", "half", "run_id", "seed", "role")

    def add(label, status, reasons=(), **fields):
        entry = {"label": label, "status": status, "reasons": list(reasons)}
        entry.update({k: v for k, v in fields.items() if v is not None or k not in where_fields})
        labels.append(entry)
        return entry

    # ---- s7.1 base claims per arm, and every cell result per arm (A2.3: mandatory exploratory)
    def arm_status(arm, pairs_list, floor_ok, floor_reasons):
        words, reasons, passes = [], list(floor_reasons), True
        for seed in SEEDS:
            rid = runs_of[(arm, seed)]
            for cell, claim in pairs_list:
                block = cells_public[cell][rid]
                if block is None:
                    w, why = why_missing(rid, cell)
                    words.append(w)
                    reasons.append(why)
                    passes = False
                else:
                    passes = passes and block[claim or "cell"]["passes_every_bar"]["original_cluster"]
        if not floor_ok:
            return NOT_TESTABLE, reasons
        if words:
            return (NOT_READ_GATE if all(w == NOT_READ_GATE for w in words) else INCOMPLETE), reasons
        return (EXP_PASS if passes else EXP_NO), reasons

    for arm in ARMS:
        for claim, pairs_list in claim_cells.items():
            f = fl["claim"][claim]
            status, reasons = arm_status(arm, pairs_list, f["can_carry"], f["reasons"])
            add(claim, status, reasons, arm=arm, role="MANDATORY_EXPLORATORY (A2.3)",
                original_calculation="BEATS_ALL_REGISTERED_BARS in all 3 runs, CONDITIONAL_CLUSTER_DIAGNOSTIC")
        for claim, pairs_list in claim_cells.items():
            for cell, sub in pairs_list:
                f = fl["cell"][cell]["claims"][sub] if sub else fl["cell"][cell]
                status, reasons = arm_status(arm, [(cell, sub)], f["can_carry"],
                                             [] if f["can_carry"] else ["floor: %s" % f["why_not"]])
                add("CELL_RESULT", status, reasons, arm=arm, claim=claim, cell=cell)
    for claim, why in sorted(B.DECLARED_NOT_TESTABLE.items()):
        add(claim, NOT_TESTABLE, [why, DECLARED_NOT_TESTABLE_REASON], arm="both")

    # ---- A1 D5: the analogy cell split by the same-domain distractor, per arm (diagnostic; exploratory)
    halves_public = {}
    for arm in ARMS:
        for half, flag in HALVES:
            part = [c for c in members[ANALOGY_CELL] if bool(c.get("with_distractor")) is flag]
            words, reasons, passes, blocks = [], [], True, {}
            for seed in SEEDS:
                rid = runs_of[(arm, seed)]
                right = rights[rid][ANALOGY_CELL]
                if right is None:
                    w, why = why_missing(rid, ANALOGY_CELL)
                    words.append(w)
                    reasons.append(why)
                    passes = False
                    continue
                blocks[rid] = run_cell_block(B, A, part, bars_of[ANALOGY_CELL], {c["cluster_id"]: right[c["cluster_id"]]
                                                                                 for c in part})
                passes = passes and blocks[rid]["passes_every_bar"]["original_cluster"]
            f = fl["halves"][half]
            status = (NOT_TESTABLE if not f["can_carry"] else
                      (NOT_READ_GATE if words and all(w == NOT_READ_GATE for w in words) else INCOMPLETE) if words
                      else EXP_PASS if passes else EXP_NO)
            add("ANALOGY_6_DISTRACTOR_HALF", status,
                ([] if f["can_carry"] else ["floor: %s" % f["why_not"]]) + reasons, arm=arm, half=half)
            halves_public["%s/%s" % (arm, half)] = blocks

    # ---- s7.2 per seed pair: REPAIR_BEATS_UNCHANGED_<cell>, and the V regression gates
    paired_public, regression_public, pair_missing = {}, {}, {}
    for seed in SEEDS:
        rr, ur = runs_of[("repaired", seed)], runs_of[("unchanged", seed)]
        paired_public[seed], regression_public[seed] = {}, {}
        for cell in CLAIM_CELLS:
            a, b = rights[rr][cell], rights[ur][cell]
            missing = [why_missing(rid, cell) for rid, r in ((rr, a), (ur, b)) if r is None]
            pair_missing[(seed, cell)] = missing
            block = None if missing else pair_block(B, A, members[cell], a, b)
            paired_public[seed][cell] = block
            f = fl["cell"][cell]
            if missing:
                status = NOT_READ_GATE if all(w == NOT_READ_GATE for w, _ in missing) else INCOMPLETE
            elif not f["can_carry"]:
                status = NOT_TESTABLE
            else:
                status = EXP_PASS if block["original_cluster"]["pass"] else EXP_NO
            add(PAIRED_LABEL[cell], status, [why for _, why in missing] + ([] if f["can_carry"] else
                                                                           ["floor: %s" % f["why_not"]]),
                seed_pair=seed, cell=cell,
                role=("CONDITION 1 OF %s (views in the confirmatory block) and MANDATORY_EXPLORATORY" % CONFIRMATORY
                      if cell == ANALOGY_CELL else "MANDATORY_EXPLORATORY (A2.3)"))
            gate = "V:%s" % cell
            if cell not in fl["v_cells"]:
                regression_public[seed][gate] = {"status": LEFT_OUT}
                add("NO_REGRESSION_CHECK", LEFT_OUT, ["the cell cannot carry a claim (s7.2 V)"], seed_pair=seed,
                    gate=gate)
            elif missing:
                st = NOT_READ_GATE if all(w == NOT_READ_GATE for w, _ in missing) else INCOMPLETE
                regression_public[seed][gate] = {"status": st}
                add("NO_REGRESSION_CHECK", st, [why for _, why in missing], seed_pair=seed, gate=gate)
            else:
                st = REG if block["regression"]["flagged"] else NO_REG
                regression_public[seed][gate] = dict(block["regression"], status=st)
                add("NO_REGRESSION_CHECK", st, [], seed_pair=seed, gate=gate,
                    caption=None if st == REG else NO_REGRESSION_CAPTION)
            # threshold crossings of the per-run cell pass (information only, s7.2)
            crossings = []
            for claim in ([three, four] if cell in REACH_CELLS else [None]):
                ra, ua = cells_public[cell][rr], cells_public[cell][ur]
                if ra and ua:
                    pa = ra[claim or "cell"]["passes_every_bar"]["original_cluster"]
                    pu = ua[claim or "cell"]["passes_every_bar"]["original_cluster"]
                    if pa != pu:
                        crossings.append("%s%s: repaired %s, unchanged %s" % (
                            cell, " [%s]" % claim if claim else "", "PASS" if pa else "FAIL", "PASS" if pu else "FAIL"))
            regression_public[seed][gate]["cell_threshold_crossings_information_only"] = crossings
        # H1, H2 from the wave-1 reader's documents. A5.5: a pair whose repaired run is not admitted (matched start) or
        # whose control is not admitted (U17 verdict) is never shown side by side, so its counts are withheld here.
        h = h1h2.get(seed) or read_h1h2(None, seed)
        pair_admitted = plan[rr]["read"] and plan[ur]["read"]
        for gate in ("H1", "H2"):
            if not pair_admitted:
                st, why = INCOMPLETE, ["PAIR_NOT_ADMITTED: %s %s, %s %s (counts withheld)" % (
                    rr, plan[rr]["status"], ur, plan[ur]["status"])]
            elif h["state"] != "READ":
                st, why = INCOMPLETE, list(h["reasons"])
            elif not h["registered_view"]:
                st, why = (NOT_READ_GATE if prereq["item2"]["gate"] != "CLEARED" else INCOMPLETE), list(h["reasons"])
            else:
                st, why = (REG if h[gate]["regression_flagged"] else NO_REG), list(h["reasons"])
            regression_public[seed][gate] = {"status": st, "counts": h.get(gate) if pair_admitted else None,
                                             "view": h.get("view"),
                                             "old_gate_crossings": h.get("old_gate_crossings") if pair_admitted else None}
            add("NO_REGRESSION_CHECK", st, why, seed_pair=seed, gate=gate,
                caption=NO_REGRESSION_CAPTION if st == NO_REG else None)
            if pair_admitted and h["state"] == "READ" and not h["registered_view"]:
                add("NO_REGRESSION_CHECK_NON_ANALOGY_VIEW_EXPLORATORY",
                    REG if h[gate]["regression_flagged"] else NO_REG, ["exploratory only (Q-J default)"],
                    seed_pair=seed, gate=gate)

    # ---- the one confirmatory claim (A2.3)
    words, reasons = [], []
    if not fl["confirmatory"]["can_carry"]:
        words.append(NOT_TESTABLE)
        reasons += ["A2.4/s7 floor: %s" % r for r in fl["confirmatory"]["reasons"]]
    if prereq["item2"]["gate"] != "CLEARED":
        words.append(MGO)
        reasons += prereq["item2"]["reasons"]
    # A gap caused by the open mechanism gate is already MECHANISM_GATE_OPEN; any other gap is COMPARISON_INCOMPLETE.
    cond1, cond2, cond4, p_parts, unknown, failed = {}, {}, {}, [], [], []
    for seed in SEEDS:
        block = paired_public[seed][ANALOGY_CELL]
        if block is None:
            cond1[seed] = None
            gaps = pair_missing[(seed, ANALOGY_CELL)]
            if not all(w == NOT_READ_GATE for w, _ in gaps):
                unknown.append("condition 1, seed pair %d: not read (%s)" % (seed, "; ".join(y for _, y in gaps)))
        else:
            cond1[seed] = {v: block[v]["pass"] for v in ("degree_group", "shared_shape_component", "original_cluster")}
            p_parts += [Fraction(block[v]["p_exact"]) for v in ("degree_group", "shared_shape_component")]
            if not all(cond1[seed].values()):
                failed.append("condition 1, seed pair %d: %s" % (seed, sorted(k for k, v in cond1[seed].items() if not v)))
        rid = runs_of[("repaired", seed)]
        cb = cells_public[ANALOGY_CELL][rid]
        if cb is None:
            cond2[rid] = None
            word, why = why_missing(rid, ANALOGY_CELL)
            if word != NOT_READ_GATE:
                unknown.append("condition 2, %s: not read (%s)" % (rid, why))
        else:
            cond2[rid] = dict(cb["cell"]["passes_every_bar"])
            p_parts += [Fraction(cb["cell"]["largest_p_exact"][v]) for v in ("degree_group", "shared_shape_component")]
            if not all(cond2[rid].values()):
                failed.append("condition 2, %s: %s" % (rid, sorted(k for k, v in cond2[rid].items() if not v)))
        gates4 = {g: regression_public[seed][g]["status"] for g in regression_public[seed]
                  if g in ("H1", "H2") or g.startswith("V:")}
        cond4[seed] = gates4
        for g, st in sorted(gates4.items()):
            if st == REG:
                failed.append("condition 4, seed pair %d: %s regression detected" % (seed, g))
            elif st == INCOMPLETE:
                unknown.append("condition 4, seed pair %d: %s %s" % (seed, g, st))
    if unknown:
        words.append(INCOMPLETE)
        reasons += unknown
    if not prereq["inference"]["supported"]:
        words.append(IAU)
        reasons += prereq["inference"]["reasons"]
    ordered = [w for w in CONFIRMATORY_PRECEDENCE if w in words]
    all_met = not failed and not unknown and prereq["item2"]["gate"] == "CLEARED" and fl["confirmatory"]["can_carry"]
    status = ordered[0] if ordered else (PASS if all_met else FAIL)
    add(CONFIRMATORY, status, reasons + failed, role="THE_ONE_CONFIRMATORY_CLAIM (A2.3), alpha 1/100",
        status_words_that_apply=ordered, performance_conditions_known_failed=failed,
        performance_conditions_all_met=all_met,
        inferential_p_max_of_required_group_and_component_p=(str(max(p_parts)) if p_parts else None),
        inferential_p_covers_every_required_comparison=not unknown and prereq["item2"]["gate"] == "CLEARED",
        caption=CAPTION_A2_3 if status == PASS else None,
        conditions={"1_repair_beats_unchanged_analogy_each_pair_views": {str(k): v for k, v in cond1.items()},
                    "2_analogy_beyond_degree_6_repaired_each_run_views": cond2,
                    "3_mechanism_gate": {"state": prereq["item2"]["gate"], "reasons": prereq["item2"]["reasons"]},
                    "4_no_regression_detected_each_pair": {str(k): v for k, v in cond4.items()},
                    "a2_4_floors": fl["confirmatory"]},
        scope_sentence=B.scope_sentence(),
        control_provenance=("option C: seed 20260917's control is the fresh unchanged run; seeds 20260918 and "
                            "20260919's controls are the historical Helm 2.0 finals, admitted only by the U17 "
                            "reproduction verdict (%s)" % prereq["reproduction"]["verdict"]))
    for rid, st in run_state.items():
        add("RUN_READING", st["status"], st["reasons"], run_id=rid, arm=st["arm"], seed=st["seed"])
    public = {"runs": list(run_state.values()), "cells": cells_public, "paired": {str(k): v for k, v in paired_public.items()},
              "regression": {str(k): v for k, v in regression_public.items()}, "distractor_halves": halves_public,
              "floors_from_the_build": fl, "labels": labels}
    sealed_part = {"cluster_right": {rid: {cell: rights[rid][cell] for cell in CLAIM_CELLS} for rid in by_id}}
    return public, sealed_part


def expected_label_keys(B):
    """Every label the scorer must print (no omission is possible without a test failing)."""
    three, four = B.reach_claim_names()
    base = (three, four, "ANALOGY_BEYOND_DEGREE_6", "CORRESPONDENCE_BEYOND_DEGREE_6", "CORRESPONDENCE_BEYOND_DEGREE_5")
    keys = {(CONFIRMATORY,)}
    for arm in ARMS:
        keys |= {(c, arm) for c in base}
        keys |= {("CELL_RESULT", arm, c, cell) for c in base for cell in
                 (REACH_CELLS if c in (three, four) else
                  {"ANALOGY_BEYOND_DEGREE_6": (ANALOGY_CELL,), "CORRESPONDENCE_BEYOND_DEGREE_6": (CORR6,),
                   "CORRESPONDENCE_BEYOND_DEGREE_5": (CORR5,)}[c])}
        keys |= {("ANALOGY_6_DISTRACTOR_HALF", arm, h) for h, _ in HALVES}
    keys |= {(c, "both") for c in B.DECLARED_NOT_TESTABLE}
    for seed in SEEDS:
        keys |= {(PAIRED_LABEL[c], seed) for c in CLAIM_CELLS}
        keys |= {("NO_REGRESSION_CHECK", seed, g) for g in ["H1", "H2"] + ["V:%s" % c for c in CLAIM_CELLS]}
    return keys


def label_key(entry):
    label = entry["label"]
    if label == CONFIRMATORY:
        return (label,)
    if label == "CELL_RESULT":
        return (label, entry["arm"], entry["claim"], entry["cell"])
    if label == "ANALOGY_6_DISTRACTOR_HALF":
        return (label, entry["arm"], entry["half"])
    if label == "NO_REGRESSION_CHECK":
        return (label, entry["seed_pair"], entry["gate"])
    if label.startswith("REPAIR_BEATS_UNCHANGED"):
        return (label, entry["seed_pair"])
    if label == "RUN_READING":
        return (label, entry["run_id"])
    if label == "NO_REGRESSION_CHECK_NON_ANALOGY_VIEW_EXPLORATORY":
        return (label, entry["seed_pair"], entry["gate"])
    if label == "STAGE0_CUSTODY_MANIFEST":
        return (label,)
    return (label, entry.get("arm"))


def label_table(labels):
    """Plain lines for the log: label, where, status, first reason. Aggregates and words only."""
    lines = ["%-48s %-70s %-40s %s" % ("label", "arm / run / seed pair / gate / claim / cell / half", "status",
                                       "first reason")]
    for e in labels:
        where = " ".join(str(e[k]) for k in ("arm", "run_id", "seed_pair", "gate", "claim", "cell", "half") if k in e)
        lines.append("%-48s %-70s %-40s %s" % (e["label"], where, e["status"], (e["reasons"] or [""])[0][:100]))
    return lines
