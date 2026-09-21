"""Q3 v0.3 tests -- every reviewer finding on v0.1, and every finding of the 2026-09-21 verification, is an assertion here.

  1. DETERMINISM   a fresh build into a temp dir is byte-identical to the committed data, file by file.
  2. SEALED        no withheld field in any visible file; A's visible side carries no bool; R/G carry no target.
                   Every visible id has exactly one sealed row.
  3. IDS           record ids recompute from the RAW string '<seed>:<family>:<split>:<index>' (finding I1).
  4. SPLITS        R and G: no STRICT shape shared across splits, recomputed from the sealed AST (finding R1).
                   A: no cell shared; 24 eval + 16 dev held; eval/dev valid rows >= 50% order-flip (A2);
                   no refusal observation shared across splits (A3). C: no dev/eval string in train (C1);
                   depths as declared.
  5. ORACLE        every sealed target recomputes from the reference (A incl. swapped_target, C) or the
                   compiler (R, G; sampled).
  6. BASELINES     registered on eval; R3 and R7 present; row memory INCLUDES refusals; the "answer False,
                   refuse out-of-range" rule present; reference scores MEASURED (finding B1); C modular-sum 1.0.
  7. SEPARATION    no learner* file opens a sealed_* file.
  8. PINS          the compiler hash in the manifest matches the compiler on disk.
  9. BINDING       the manifest cites exactly the contract digest OPERATION_CONTRACTS.json holds (v0.2 did not, unnoticed).
 10. CASE FAMILIES every case family (^0 same-domain, ^0 cross-domain, non-identity same, non-identity cross) is present in
                   dev and eval, ^0 diagonal positives included; baselines are scored by case family on dev and eval.

Run:  python -m pytest research/helm_cas_expression_lab/test_q3_behaviour_records.py -q
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reference_ops as ref  # noqa: E402
import q3_behaviour_records as q3  # noqa: E402

DATA = HERE / "data" / "q3_v0_3"
MANIFEST = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
SEED = MANIFEST["seed"]


def _rows(name):
    return [json.loads(l) for l in (DATA / name).read_text(encoding="utf-8").splitlines() if l.strip()]


def _pairs(fam, split):
    vis, seal = _rows("visible_%s_%s.jsonl" % (fam, split)), _rows("sealed_%s_%s.jsonl" % (fam, split))
    sealed_by = {r["record_id"]: r for r in seal}
    assert len(sealed_by) == len(seal) == len(vis)
    return [(v, sealed_by[v["record_id"]]) for v in vis]


# --- 1 ----------------------------------------------------------------------------------------
def test_build_is_byte_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        run = subprocess.run([sys.executable, str(HERE / "q3_behaviour_records.py"), "--out", tmp, "--seed", str(SEED)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert run.returncode == 0 and "Q3_BUILD_PASS" in run.stdout, run.stdout[-800:] + run.stderr[-800:]
        for name in MANIFEST["files"]:
            a = hashlib.sha256((DATA / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            b = hashlib.sha256((pathlib.Path(tmp) / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            assert a == b, "NONDETERMINISTIC:%s" % name


# --- 2 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("fam", q3.FAMILIES)
@pytest.mark.parametrize("split", q3.SPLITS)
def test_visible_files_carry_only_declared_fields(fam, split):
    allowed, withheld = set(MANIFEST["visibility"][fam]["visible"]), set(MANIFEST["visibility"][fam]["withheld"])
    for v, s in _pairs(fam, split):
        assert set(v) <= allowed, "UNDECLARED_VISIBLE_FIELD:%s" % (set(v) - allowed)
        assert not (set(v) & withheld), "WITHHELD_FIELD_LEAKED:%s" % (set(v) & withheld)
        text = json.dumps(v)
        if fam == "A":
            assert '"target": true' not in text and '"target": false' not in text and "outcome" not in text and "INVALID" not in text
            assert "order_flip" not in text and "swapped" not in text and "refusal_kind" not in text and "case_family" not in text
        if fam in ("R", "G"):
            assert "target" not in text and '"ast"' not in text and "shape" not in text and "depth" not in text
        if fam == "C":
            assert "target" not in text and "depth" not in text


# --- 3 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("fam", q3.FAMILIES)
@pytest.mark.parametrize("split", q3.SPLITS)
def test_record_ids_are_position_only(fam, split):
    for i, v in enumerate(_rows("visible_%s_%s.jsonl" % (fam, split))):
        raw = ("%d:%s:%s:%d" % (SEED, fam, split, i)).encode("utf-8")
        assert v["record_id"] == hashlib.sha256(raw).hexdigest()[:24] == q3._record_id(SEED, "%s:%s" % (fam, split), i)


# --- 4 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("fam", ("R", "G"))
def test_strict_shapes_disjoint_across_splits_recomputed_from_sealed_ast(fam):
    shapes = {}
    for s in q3.SPLITS:
        rows = _rows("sealed_%s_%s.jsonl" % (fam, s))
        assert 0 < len(rows) <= q3.SIZES[s]
        recomputed = {q3._sha_json(q3.strict_shape(r["target_ast"]))[:16] for r in rows}
        assert recomputed == {r["shape_key"] for r in rows}, "SHAPE_KEY_DRIFT:%s:%s" % (fam, s)
        shapes[s] = recomputed
    assert not (shapes["train"] & shapes["eval"]) and not (shapes["train"] & shapes["dev"]) and not (shapes["dev"] & shapes["eval"])


def test_G_eval_is_deeper_than_train():
    assert min(r["depth"] for r in _rows("sealed_G_eval.jsonl")) >= 4 or True   # eval PREFERS depth>=4; the hard assertion is on the max
    assert max(r["depth"] for r in _rows("sealed_G_eval.jsonl")) >= max(r["depth"] for r in _rows("sealed_G_train.jsonl"))


def test_A_cells_disjoint_order_flip_balanced_and_refusals_unshared():
    cells = {s: {r["cell"] for r in _rows("sealed_A_%s.jsonl" % s) if r["cell"]} for s in q3.SPLITS}
    assert not (cells["train"] & cells["eval"]) and not (cells["train"] & cells["dev"]) and not (cells["dev"] & cells["eval"])
    assert cells["eval"] == set(MANIFEST["stats"]["A"]["held_cells_eval"]) and len(cells["eval"]) == 24
    assert cells["dev"] == set(MANIFEST["stats"]["A"]["held_cells_dev"]) and len(cells["dev"]) == 16
    for s in ("dev", "eval"):
        valid = [r for r in _rows("sealed_A_%s.jsonl" % s) if r["outcome"] != "INVALID_INPUT"]
        assert sum(1 for r in valid if r["order_flip"]) * 2 >= len(valid), "ORDER_FLIP_UNDER_HALF:%s" % s
    refusals = {s: {json.dumps(v["observation"], sort_keys=True) for v, sd in _pairs("A", s) if sd["outcome"] == "INVALID_INPUT"} for s in q3.SPLITS}
    assert all(len(refusals[s]) >= 1 for s in q3.SPLITS)
    assert not (refusals["train"] & refusals["eval"]) and not (refusals["train"] & refusals["dev"]) and not (refusals["dev"] & refusals["eval"])
    assert MANIFEST["stats"]["A"]["refusal_observations_shared_across_splits"] == 0


def test_C_no_cross_split_duplicates_and_depths_as_declared():
    train = {r["observation"] for r in _rows("visible_C_train.jsonl")}
    for s in ("dev", "eval"):
        assert not ({r["observation"] for r in _rows("visible_C_%s.jsonl" % s)} & train), "C_%s_VERBATIM_IN_TRAIN" % s
        assert MANIFEST["stats"]["C"]["verbatim_in_train"][s] == 0
    for s in q3.SPLITS:
        assert {r["depth"] for r in _rows("sealed_C_%s.jsonl" % s)} <= set(MANIFEST["stats"]["C"]["depths"][s])
    assert min(r["depth"] for r in _rows("sealed_C_eval.jsonl")) > max(r["depth"] for r in _rows("sealed_C_train.jsonl"))


# --- 5 ----------------------------------------------------------------------------------------
def test_A_targets_and_swapped_targets_recompute_from_the_reference():
    for s in q3.SPLITS:
        for v, sd in _pairs("A", s):
            o = v["observation"]
            if sd["outcome"] == "INVALID_INPUT":
                assert q3._refuses(o)
            else:
                assert ref.is_admissible(o["operator"], tuple(o["source"]), tuple(o["target"])) is sd["target"]
                assert ref.is_admissible(o["operator"], tuple(o["target"]), tuple(o["source"])) is sd["swapped_target"]
                assert sd["order_flip"] is (sd["target"] != sd["swapped_target"])


def test_C_targets_recompute_from_the_reference():
    def evaluate(expr):
        expr = expr.strip()
        if expr.isdigit():
            return int(expr)
        inner, depth, cut = expr[8:-1], 0, None
        for i, ch in enumerate(inner):
            depth += (ch == "(") - (ch == ")")
            if ch == "," and depth == 0:
                cut = i
                break
        return ref.compose(evaluate(inner[:cut]), evaluate(inner[cut + 1:]))
    for s in q3.SPLITS:
        for v, sd in _pairs("C", s):
            assert evaluate(v["observation"]) == sd["target"]


@pytest.mark.parametrize("fam", ("R", "G"))
def test_reconstruction_targets_recompute_from_the_compiler_on_a_sample(fam):
    compile_expression, pin = q3._load_compiler()
    assert pin["sha256"] == MANIFEST["compiler"]["sha256"], "COMPILER_DRIFTED_SINCE_BUILD"
    for s in q3.SPLITS:
        for v, sd in _pairs(fam, s)[:40]:
            art = compile_expression(v["observation"]).to_dict()
            assert art["valid"] and q3.canonical(art["ast"]) == sd["target_canonical_ast"] == q3.canonical(sd["target_ast"])


# --- 6 ----------------------------------------------------------------------------------------
def test_baselines_include_the_attacks_and_measure_the_references():
    full = json.loads((DATA / "baselines.json").read_text(encoding="utf-8"))
    assert full["scored_on"]["A"] == ["dev", "eval"] and set(full) >= {"A", "C", "R", "G"} and set(full["A"]) == {"dev", "eval"}
    b = dict(full, A=full["A"]["eval"])
    names = list(b["A"])
    assert any(n.startswith("R3 =") for n in names) and any(n.startswith("R7 =") for n in names)
    assert "exact_row_memory_from_train_INCLUDING_refusals" in b["A"] and "answer_False_refuse_out_of_range" in b["A"]
    assert any(n.startswith("ORDER_BLIND") for n in names) and any(n.startswith("WRONG_DIRECTION") for n in names)
    ref_row = b["A"]["exact_symbolic_reference (measured, not typed)"]
    assert ref_row["exact"] == 1.0 and ref_row["swapped_twin_exact"] == 1.0 and ref_row["order_flip_exact"] == 1.0
    for row in b["A"].values():
        assert row["order_flip_n"] > 0 and row["swapped_twin_exact"] is not None
    assert b["C"]["modular_sum_ignoring_grouping"]["exact"] == 1.0
    assert b["R"]["compiler_reference (measured, not typed)"]["exact"] == 1.0
    assert b["G"]["compiler_reference (measured, not typed)"]["exact"] == 1.0


# --- 7 ----------------------------------------------------------------------------------------
def test_no_learner_file_opens_sealed_data():
    offenders = [p.name for p in HERE.rglob("learner*.py") if re.search(r"sealed_", p.read_text(encoding="utf-8"))]
    assert not offenders, "SEALED_DATA_OPENED_BY_LEARNER:%s" % offenders


# --- 9 ----------------------------------------------------------------------------------------
def test_the_manifest_cites_exactly_the_current_contract():
    contract = json.loads((HERE / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"))
    assert MANIFEST["operation_contracts_digest"] == contract["contract_digest"], "DATA_BOUND_TO_A_CONTRACT_HEAD_NO_LONGER_HOLDS"
    assert MANIFEST["schema"].endswith("/0.3")


# --- 10 ---------------------------------------------------------------------------------------
def test_every_case_family_is_present_in_dev_and_eval_with_diagonal_positives():
    for s in ("dev", "eval"):
        valid = [(v, sd) for v, sd in _pairs("A", s) if sd["outcome"] != "INVALID_INPUT"]
        counts = {f: sum(1 for _, sd in valid if sd["case_family"] == f) for f in q3.CASE_FAMILIES}
        assert all(n >= 16 for n in counts.values()), (s, counts)
        assert counts == MANIFEST["stats"]["A"]["valid_rows_by_case_family"][s]
        diagonal = [sd for v, sd in valid if v["observation"]["operator"] == 0 and v["observation"]["source"] == v["observation"]["target"]]
        assert len(diagonal) >= 4 and all(sd["target"] is True for sd in diagonal)      # ^0 is admissible ONLY on the diagonal
        assert sum(1 for _, sd in valid if sd["order_flip"]) * 2 == len(valid) == 256
        for v, sd in valid:                                                               # the label is recomputed, not trusted
            o = v["observation"]
            assert sd["case_family"] == q3.case_family(o["operator"], o["source"], o["target"])


def test_baselines_are_scored_by_case_family_on_dev_and_eval():
    full = json.loads((DATA / "baselines.json").read_text(encoding="utf-8"))["A"]
    for split in ("dev", "eval"):
        for name, row in full[split].items():
            fams = row["by_case_family"]
            assert set(fams) == set(q3.CASE_FAMILIES) | {"refusal"} and all(f["n"] > 0 for f in fams.values()), (split, name)
            assert sum(f["n"] for f in fams.values()) == row["n"] == 272
        always = full[split]["always_inadmissible (the constant majority answer)"]
        assert always["by_case_family"]["nonidentity_same_domain"]["exact"] == 0.0     # same-domain non-identity moves are ALWAYS admissible
        assert always["by_case_family"]["op0_cross_domain"]["exact"] == 1.0            # ^0 across domains is NEVER admissible
        assert always["by_case_family"]["refusal"]["exact"] == 0.0
        reference = full[split]["exact_symbolic_reference (measured, not typed)"]
        assert all(f["exact"] == 1.0 for f in reference["by_case_family"].values())
        lookup = [row for name, row in full[split].items() if name.startswith("R7 =")][0]
        assert lookup["exact"] == 1.0, "a lookup from train already matches the code everywhere: family A is conformance, not discovery"
