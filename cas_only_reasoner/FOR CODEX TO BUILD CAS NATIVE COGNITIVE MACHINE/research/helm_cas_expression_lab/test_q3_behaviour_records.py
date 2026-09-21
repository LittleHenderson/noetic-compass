"""Q3 tests -- the visibility boundary, the splits and the baselines are only real if a program checks them.

  1. DETERMINISM   a fresh build into a temp dir is byte-identical to the committed data, file by file.
  2. SEALED        no withheld field appears in any visible file; family A's visible side carries no bool;
                   family R's carries nothing named target/ast. Every visible id has exactly one sealed row.
  3. IDS           record ids recompute from (seed, family:split, index) -- position only, never content.
  4. SPLITS        R: no AST shape shared across splits. A: no (operator, source_domain, target_domain)
                   cell shared across splits among valid rows; 24 eval + 16 dev cells held. C: depths as declared.
  5. ORACLE        every sealed target recomputes from the reference (A, C) or the compiler (R, sampled).
  6. BASELINES     registered on eval; the modular-sum rule scores 1.0 on C (conformance-only by construction).
  7. SEPARATION    no learner* file under the lab opens a sealed_* file.
  8. PINS          the compiler hash recorded in the manifest still matches the compiler on disk.

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

DATA = HERE / "data" / "q3_v0_1"
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
    allowed = set(MANIFEST["visibility"][fam]["visible"])
    withheld = set(MANIFEST["visibility"][fam]["withheld"])
    for v, s in _pairs(fam, split):
        assert set(v) <= allowed, "UNDECLARED_VISIBLE_FIELD:%s" % (set(v) - allowed)
        assert not (set(v) & withheld), "WITHHELD_FIELD_LEAKED:%s" % (set(v) & withheld)
        text = json.dumps(v)
        if fam == "A":
            assert '"target": true' not in text and '"target": false' not in text
            assert "outcome" not in text and "INVALID" not in text
        if fam == "R":
            assert "target" not in text and '"ast"' not in text and "shape" not in text
        if fam == "C":
            assert "target" not in text and "depth" not in text


# --- 3 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("fam", q3.FAMILIES)
@pytest.mark.parametrize("split", q3.SPLITS)
def test_record_ids_are_position_only(fam, split):
    vis = _rows("visible_%s_%s.jsonl" % (fam, split))
    for i, v in enumerate(vis):
        assert v["record_id"] == q3._record_id(SEED, "%s:%s" % (fam, split), i)
        assert re.fullmatch(r"[0-9a-f]{24}", v["record_id"])


# --- 4 ----------------------------------------------------------------------------------------
def test_R_shapes_disjoint_across_splits():
    shapes = {s: {r["shape_key"] for r in _rows("sealed_R_%s.jsonl" % s)} for s in q3.SPLITS}
    assert not (shapes["train"] & shapes["eval"]) and not (shapes["train"] & shapes["dev"]) and not (shapes["dev"] & shapes["eval"])
    for s in q3.SPLITS:
        assert 0 < len(_rows("sealed_R_%s.jsonl" % s)) <= q3.SIZES[s]


def test_A_cells_disjoint_and_held_out_as_declared():
    cells = {s: {r["cell"] for r in _rows("sealed_A_%s.jsonl" % s) if r["cell"]} for s in q3.SPLITS}
    assert not (cells["train"] & cells["eval"]) and not (cells["train"] & cells["dev"]) and not (cells["dev"] & cells["eval"])
    assert cells["eval"] == set(MANIFEST["stats"]["A"]["held_cells_eval"]) and len(cells["eval"]) == 24
    assert cells["dev"] == set(MANIFEST["stats"]["A"]["held_cells_dev"]) and len(cells["dev"]) == 16
    assert len(cells["train"]) == 160 - 40
    for s in q3.SPLITS:
        rows = _rows("sealed_A_%s.jsonl" % s)
        assert sum(1 for r in rows if r["outcome"] == "INVALID_INPUT") >= 1
        assert q3.SIZES[s] <= len(rows) <= q3.SIZES[s] + q3.SIZES[s] // 16 + 1


def test_C_depths_as_declared():
    for s in q3.SPLITS:
        depths = {r["depth"] for r in _rows("sealed_C_%s.jsonl" % s)}
        assert depths <= set(MANIFEST["stats"]["C"]["depths"][s]), (s, depths)
    assert max(r["depth"] for r in _rows("sealed_C_eval.jsonl")) > max(r["depth"] for r in _rows("sealed_C_train.jsonl"))


# --- 5 ----------------------------------------------------------------------------------------
def test_A_targets_recompute_from_the_reference():
    for s in q3.SPLITS:
        for v, sd in _pairs("A", s):
            o = v["observation"]
            if sd["outcome"] == "INVALID_INPUT":
                with pytest.raises(ref.InvalidInput):
                    ref.is_admissible(o["operator"], tuple(o["source"]), tuple(o["target"]))
            else:
                assert ref.is_admissible(o["operator"], tuple(o["source"]), tuple(o["target"])) is sd["target"]


def test_C_targets_recompute_from_the_reference():
    def evaluate(expr):
        expr = expr.strip()
        if expr.isdigit():
            return int(expr)
        assert expr.startswith("compose(") and expr.endswith(")")
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


def test_R_targets_recompute_from_the_compiler_on_a_sample():
    compile_expression, pin = q3._load_compiler()
    assert pin["sha256"] == MANIFEST["compiler"]["sha256"], "COMPILER_DRIFTED_SINCE_BUILD"
    for s in q3.SPLITS:
        for v, sd in _pairs("R", s)[:40]:
            art = compile_expression(v["observation"]).to_dict()
            assert art["valid"] and q3.canonical(art["ast"]) == sd["target_canonical_ast"]
            assert q3.canonical(sd["target_ast"]) == sd["target_canonical_ast"]


# --- 6 ----------------------------------------------------------------------------------------
def test_baselines_registered_and_C_is_conformance_only():
    b = json.loads((DATA / "baselines.json").read_text(encoding="utf-8"))
    assert b["scored_on"] == "eval" and set(b) >= {"A", "C", "R"}
    assert b["C"]["modular_sum_ignoring_grouping"]["exact"] == 1.0
    assert b["A"]["exact_symbolic_reference"]["exact"] == 1.0
    mechanism_free = [k for k in b["A"] if k != "exact_symbolic_reference"]
    bar = max(b["A"][k]["exact"] for k in mechanism_free)
    assert 0.0 < bar < 1.0, "the mechanism-free bar for A must be strictly between 0 and 1, got %s" % bar
    assert all(b["A"][k]["refusals_missed"] >= 1 for k in mechanism_free)


# --- 7 ----------------------------------------------------------------------------------------
def test_no_learner_file_opens_sealed_data():
    offenders = [p.name for p in HERE.rglob("learner*.py") if re.search(r"sealed_", p.read_text(encoding="utf-8"))]
    assert not offenders, "SEALED_DATA_OPENED_BY_LEARNER:%s" % offenders
