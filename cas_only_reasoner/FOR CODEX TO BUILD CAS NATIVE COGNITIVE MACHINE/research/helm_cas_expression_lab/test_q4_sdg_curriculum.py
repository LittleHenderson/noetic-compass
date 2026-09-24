"""Q4-SDG-1 lesson adapter tests. Pure Python: the pinned compiler is used, torch is never imported.

  1. EXCLUSION  the 16 G-train and 9 G-dev bare-shape keys are recomputed from the VISIBLE Q3 v0.7 train and dev
                files only (compiled with the pinned compiler); every generated row has an allowed shape, depth <= 3.
  2. DEV        no generated observation equals any visible Q3 dev observation (families G, R and C).
  3. Q3 FROZEN  q3_behaviour_records.py, q3_load.py and Q3_DATA_PINS.json keep the LF hashes the executed Q4 plan
                recorded; the 12 pinned Q4 runtime files are unchanged; the Q3 v0.7 manifest is the pinned one.
  4. SEEDS      the new seeds differ from every Q3 seed.
  5. SURFACE    one canonical text per tree; a missing domain and a Noetic-level register are refused.
  6. ROWS       every row recompiles to its stored target; tokens round-trip; slot kinds agree with the grammar.
  7. PAIRS      A one-field pairs differ in exactly one compiled token of that field; B swap/op pairs and C grouping,
                operator-only and leaf-only relations hold; groups never straddle splits; content occurs once.
  8. IDENTITY   record ids are positional; visible rows carry four keys only; a rebuild is byte-identical.
  9. FEEDBACK   first_wrong_decision names the right slot and mistake; family D makes fresh rows of the trigger's
                kind plus controls, and refuses triggers from dev, from Q3 dev rows and from unknown rows.

Run (small, local):  python -B -m pytest test_q4_sdg_curriculum.py -q -p no:cacheprovider
"""
import collections
import json
from pathlib import Path
import random
import shutil
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import q4_sdg_curriculum as sdg  # noqa: E402
import q3_behaviour_records as q3  # noqa: E402
import q3_load  # noqa: E402
from learner_q4_decoder import TOKEN_IDS, TOKENS, allowed_next, ast_to_tokens  # noqa: E402

CNCM = HERE.parents[1]
PLAN = CNCM / "records" / "q4_authorized_20260922" / "plan.json"
SIZE = 64


@pytest.fixture(scope="module")
def compiler():
    return sdg.Compiler()


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("q4sdg") / "pkg"
    manifest = sdg.build(out, SIZE)
    return out, manifest


def _pairs(out, split):
    rows = []
    for lesson in sdg.LESSONS:
        rows += sdg.load_lesson_pairs(out, lesson, split, pinned=False)
    return rows


# --- 0 ----------------------------------------------------------------------------------------------------
def test_adapter_imports_no_torch_and_no_evaluator_door():
    assert "torch" not in sys.modules
    source = (HERE / "q4_sdg_curriculum.py").read_text(encoding="utf-8")
    for forbidden in ("import torch", "load_split", "load_dataset", "_eval.jsonl"):
        assert forbidden not in source


# --- 1 ----------------------------------------------------------------------------------------------------
def test_frozen_g_keys_recompute_from_visible_train_and_dev_only(compiler):
    q3_load.check_pins(sdg.Q3_DATA)                  # manifest + pin only; no eval or sealed file is opened
    found = {}
    for split in ("train", "dev"):
        keys = {}
        for row in q3_load.load_visible(sdg.Q3_DATA, "G", split):
            artifact = compiler.compile_expression(row["observation"]).to_dict()
            assert artifact["valid"]
            shape = q3.tree_shape(q3.to_lab_spelling(artifact["ast"]))
            keys[sdg.bare_key16(shape)] = sdg.shape_text(shape)
        found[split] = keys
    assert found["train"] == sdg.G_TRAIN_SHAPES and len(found["train"]) == 16
    assert found["dev"] == sdg.G_DEV_SHAPES and len(found["dev"]) == 9
    assert not set(sdg.G_TRAIN_SHAPES) & set(sdg.G_DEV_SHAPES)
    assert sdg.G_DEV_SHAPES["f5844b5735f0fe95"] == "(((L L) L) L)"
    assert max(q3.tree_depth(sdg.parse_shape(t)) for t in sdg.G_TRAIN_SHAPES.values()) == 3


def test_shape_constants_are_consistent():
    for table in (sdg.G_TRAIN_SHAPES, sdg.G_DEV_SHAPES):
        for key, text in table.items():
            assert sdg.bare_key16(sdg.parse_shape(text)) == key
            assert sdg.shape_text(sdg.parse_shape(text)) == text
    assert sdg.bare_key16("L") == sdg.SINGLE_STATE_KEY
    assert sdg.SINGLE_STATE_KEY not in sdg.G_TRAIN_SHAPES and sdg.SINGLE_STATE_KEY not in sdg.G_DEV_SHAPES
    grouping = [t for n in (3, 4) for t in sdg.C_SHAPES[n]]
    assert all(sdg.bare_key16(sdg.parse_shape(t)) in sdg.G_TRAIN_SHAPES for t in grouping)
    four_leaf = {"(((L L) L) L)", "((L (L L)) L)", "((L L) (L L))", "(L ((L L) L))", "(L (L (L L)))"}
    held_out = four_leaf - set(sdg.C_SHAPES[4])
    assert held_out == {"(((L L) L) L)", "(L ((L L) L))"}
    assert all(sdg.bare_key16(sdg.parse_shape(t)) in sdg.G_DEV_SHAPES for t in held_out)


def test_every_row_has_an_allowed_shape_and_recompiles(package, compiler):
    out, _ = package
    for split in sdg.SPLITS:
        rows = _pairs(out, split)
        assert rows
        for visible, sealed in rows:
            shape = q3.tree_shape(sealed["target_ast"])
            key, depth = sdg.bare_key16(shape), q3.tree_depth(shape)
            assert depth <= 3 and key not in sdg.G_DEV_SHAPES
            assert key in sdg.G_TRAIN_SHAPES or shape == "L"
            artifact = compiler.compile_expression(visible["observation"]).to_dict()
            assert artifact["valid"] and q3.to_lab_spelling(artifact["ast"]) == sealed["target_ast"]
            tokens = ast_to_tokens(sealed["target_ast"])
            assert list(tokens) == sealed["target_tokens"]
            assert sealed["slot_kinds"] == [sdg.slot_kind(tokens[:i]) for i in range(len(tokens))]
            assert sdg.is_canonical_surface(visible["observation"])


# --- 2 ----------------------------------------------------------------------------------------------------
def test_no_observation_equals_a_visible_q3_dev_observation(package):
    out, _ = package
    dev = set()
    for family in ("G", "R", "C"):
        dev |= {r["observation"] for r in q3_load.load_visible(sdg.Q3_DATA, family, "dev")}
    for split in sdg.SPLITS:
        for visible, _ in _pairs(out, split):
            assert visible["observation"] not in dev


# --- 3 ----------------------------------------------------------------------------------------------------
def test_q3_files_are_unchanged():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    for name in ("q3_behaviour_records.py", "q3_load.py"):
        assert sdg.lf_sha256(HERE / name) == plan["source_pins"][name] == sdg.Q3_IMMUTABLE_LF_SHA256[name]
    assert sdg.lf_sha256(HERE / "Q3_DATA_PINS.json") == plan["pins_file_sha256"] == sdg.Q3_IMMUTABLE_LF_SHA256["Q3_DATA_PINS.json"]
    for name, digest in plan["source_pins"].items():          # the 12 pinned Q4 runtime files
        assert sdg.lf_sha256(HERE / name) == digest, name
    pins = json.loads((HERE / "Q3_DATA_PINS.json").read_text(encoding="utf-8"))
    assert pins["data_versions"]["helm-cas-expression-lab.q3-behaviour-records/0.7"]["manifest_sha256"] == sdg.Q3_V07_MANIFEST_SHA256
    assert sdg.lf_sha256(sdg.Q3_DATA / "manifest.json") == sdg.Q3_V07_MANIFEST_SHA256 == plan["manifest_sha256"]
    sdg.check_q3_immutable()


def test_new_pin_file_is_separate_and_starts_empty():
    pins = json.loads(sdg.PINS.read_text(encoding="utf-8"))
    assert sdg.PINS.name == "Q4_SDG_DATA_PINS.json" and pins["schema"] == sdg.PINS_SCHEMA
    assert all(not name.startswith("helm-cas-expression-lab.q3") for name in pins["data_versions"])


# --- 4 ----------------------------------------------------------------------------------------------------
def test_seeds_are_new():
    assert q3.SEED == 20260921
    q3_seeds = {q3.SEED + k for k in range(5)}
    for seed in (sdg.SEED, sdg.FEEDBACK_SEED):
        assert seed not in q3_seeds and seed not in sdg.Q3_SEEDS
    assert sdg.SEED != sdg.FEEDBACK_SEED
    with pytest.raises(sdg.LessonError, match="SEED_NOT_NEW"):
        sdg.build(Path("unused"), 16, seed=20260921)


# --- 5 ----------------------------------------------------------------------------------------------------
def test_one_canonical_surface(compiler):
    # The reason for the rule: two different texts compile to ONE tree.
    a = compiler.compile_expression("^8|A^C").to_dict()["ast"]
    b = compiler.compile_expression("^8^C|A").to_dict()["ast"]
    assert a == b
    assert compiler.compile_expression("^8").to_dict()["ast"]["domain"] == "P"   # a missing domain becomes P
    assert sdg.is_canonical_surface("^8^C|A") and sdg.is_canonical_surface("^8^C_{F2}|A")
    for text in ("^8|A^C", "^8", "(^1^C+^2^C)", "^1^C + ^2^C", "^8^C_{F2|A}", "(^1^C * ^2^C)", "^8^C|A "):
        assert not sdg.is_canonical_surface(text), text
    with pytest.raises(sdg.LessonError, match="explicit domain"):
        sdg.render_ast({"node": "StateLiteral", "operator": "^8", "domain": None, "drive": None})
    with pytest.raises(sdg.LessonError, match="no canonical text"):
        sdg.render_ast({"node": "StateLiteral", "operator": "^8", "domain": "C", "drive": None, "register": None})


def test_unsupported_output_is_refused_not_simplified(compiler):
    with pytest.raises(sdg.Refusal) as refusal:
        sdg.codec_or_refuse({"node": "StateLiteral", "operator": "^3", "domain": "P", "drive": None,
                             "register_set": ["A", "f", "T"]})
    assert refusal.value.code == "UNSUPPORTED_OPERATION"
    with pytest.raises(sdg.Refusal) as refusal:
        sdg.check_intended({"node": "StateLiteral", "operator": "^3", "domain": "P", "drive": None,
                            "register_set": ["A", "f"]}, compiler)
    assert refusal.value.code == "UNSUPPORTED_OPERATION"


def test_leaf_sampler_draws_like_q3_random_literal():
    for seed in range(40):
        assert sdg.render_ast(sdg.random_leaf(random.Random(seed))) == q3._random_literal(random.Random(seed))


def test_three_leaf_mixed_grouping_can_never_keep_both_members(compiler):
    rng = random.Random(7)
    for _ in range(20):
        leaves = sdg._unequal_leaves(rng, 3)
        for ops in (["PLUS", "TIMES"], ["TIMES", "PLUS"]):
            ok = []
            for text in sdg.C_SHAPES[3]:
                try:
                    sdg.check_intended(sdg.fill_shape(sdg.parse_shape(text), leaves, ops), compiler)
                    ok.append(text)
                except sdg.Refusal:
                    pass
            assert len(ok) <= 1


# --- 7 ----------------------------------------------------------------------------------------------------
def test_pair_integrity_and_groups(package):
    out, manifest = package
    seen, group_split = set(), {}
    groups = collections.defaultdict(list)
    for split in sdg.SPLITS:
        for visible, sealed in _pairs(out, split):
            assert sealed["content_sha256"] not in seen
            seen.add(sealed["content_sha256"])
            assert group_split.setdefault(sealed["group_id"], split) == split
            groups[sealed["group_id"]].append(sealed)
    relations = collections.Counter()
    for members in groups.values():
        assert len(members) == members[0]["group_size"]
        sdg.check_group_relation(members)
        relations[members[0]["changed_field"]] += len(members) > 1
    for relation in ("noetic", "domain", "drive", "register", "left_right_order", "op", "leaf", "grouping"):
        assert relations[relation] >= 1, relation
    a_pairs = [m for m in groups.values() if m[0]["subfamily"] == "one_field_pair"]
    for a, b in a_pairs:
        diff = [i for i, (x, y) in enumerate(zip(a["target_tokens"], b["target_tokens"])) if x != y]
        assert len(diff) == 1 and a["slot_kinds"][diff[0]] == a["changed_field"]
    b_swaps = [m for m in groups.values() if m[0]["subfamily"] == "swap_pair"]
    assert all(a["target_ast"]["left"] == b["target_ast"]["right"] != a["target_ast"]["right"] for a, b in b_swaps)


def test_group_relation_checker_catches_a_broken_pair(package):
    out, _ = package
    rows = [s for _, s in _pairs(out, "train") if s["subfamily"] == "swap_pair"]
    a = rows[0]
    b = next(r for r in rows if r["group_id"] == a["group_id"] and r is not a)
    broken = dict(b, target_ast=dict(b["target_ast"], op="PLUS" if b["target_ast"]["op"] == "TIMES" else "TIMES"))
    with pytest.raises(sdg.LessonError, match="PAIR_RELATION_BROKEN"):
        sdg.check_group_relation([a, broken])


# --- 8 ----------------------------------------------------------------------------------------------------
def test_visible_rows_carry_four_keys_and_positional_ids(package):
    out, manifest = package
    for split in sdg.SPLITS:
        seed = manifest["record_id_seeds"][split]
        for lesson in sdg.LESSONS:
            rows = sdg.load_visible_lessons(out, lesson, split, pinned=False)
            for index, row in enumerate(rows):
                assert set(row) == sdg.VISIBLE_KEYS and row["mode"] == "reconstruction"
                assert row["record_id"] == sdg.record_id(sdg.SCHEMA, seed, lesson, split, index)
                text = json.dumps(row)
                assert "target" not in text and "shape" not in text and "tokens" not in text
            assert seed == (sdg.FEEDBACK_SEED if split == "feedback" else sdg.SEED)


def test_rebuild_is_byte_identical(package, tmp_path):
    out, manifest = package
    again = tmp_path / "again"
    sdg.build(again, SIZE)
    names = sorted(p.name for p in out.iterdir())
    assert names == sorted(p.name for p in again.iterdir())
    for name in names:
        assert (out / name).read_bytes() == (again / name).read_bytes(), name


def test_output_must_be_new_and_tampering_is_refused(package, tmp_path):
    out, manifest = package
    with pytest.raises(sdg.LessonError, match="OUTPUT_NOT_EMPTY"):
        sdg.build(out, SIZE)
    copy = tmp_path / "copy"
    shutil.copytree(out, copy)
    name = "visible_A_train.jsonl"
    lines = (copy / name).read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["target_ast"] = {"node": "StateLiteral"}
    lines[0] = json.dumps(row, sort_keys=True, ensure_ascii=False)
    body = ("\n".join(lines) + "\n").encode("utf-8")
    (copy / name).write_bytes(body)
    with pytest.raises(sdg.LessonError, match="FILE_HASH_MISMATCH"):
        sdg.load_visible_lessons(copy, "A", "train", pinned=False)
    forged = json.loads((copy / "manifest.json").read_text(encoding="utf-8"))
    forged["files"][name]["sha256"] = sdg.sha256_hex(body)
    (copy / "manifest.json").write_bytes(json.dumps(forged).encode("utf-8"))
    with pytest.raises(sdg.LessonError, match="VISIBLE_ROW_KEYS_WRONG"):
        sdg.load_visible_lessons(copy, "A", "train", pinned=False)


def test_pinning_is_required_and_create_only(package, tmp_path, monkeypatch):
    out, _ = package
    pins = tmp_path / "pins.json"
    body = json.loads(sdg.PINS.read_text(encoding="utf-8"))
    body["data_versions"] = {}                        # an EMPTY pin file, whatever the real one holds (review of
    pins.write_text(json.dumps(body), encoding="utf-8")   # 3771f989: pinning the AWS package must not break this test)
    monkeypatch.setattr(sdg, "PINS", pins)            # the real pin file is never read or written by this test
    with pytest.raises(sdg.LessonError, match="NO_PIN_FOR_THIS_DATA_VERSION"):
        sdg.load_visible_lessons(out, "A", "train")
    with pytest.raises(sdg.LessonError, match="PIN_DATA_OUTSIDE_THE_LAB"):
        sdg.pin_dataset(out)
    body = json.loads(pins.read_text(encoding="utf-8"))
    body["data_versions"][sdg.SCHEMA] = {"data_dir": "x", "manifest_sha256": sdg.manifest_sha(out)}
    pins.write_text(json.dumps(body), encoding="utf-8")
    assert sdg.check_pin(out)["manifest_sha256"] == sdg.manifest_sha(out)
    assert sdg.load_visible_lessons(out, "A", "train")


def test_a_coverage_is_logged_and_balanced(package):
    _, manifest = package
    coverage = manifest["stats"]["coverage"]["train"]
    assert set(coverage["A_field_values"]) == set(sdg.FIELDS)
    assert coverage["A_distinct_cells"] == sum(coverage["A_field_values"]["noetic"].values())


def test_quotas_are_declared_and_a_is_capped():
    quotas, capped = sdg.plan_quotas(4096)
    assert not capped
    assert sum(quotas[k]["train"] for k in quotas) == 4096
    quotas, capped = sdg.plan_quotas(65536)
    assert capped and sum(quotas[k][s] for k in quotas if k[0] == "A" for s in sdg.SPLITS) <= sdg.A_DISTINCT_CAP
    assert abs(sum(sdg.MIXTURE.values()) - 1.0) < 1e-12
    with pytest.raises(sdg.LessonError, match="INVALID_SIZE"):
        sdg.plan_quotas(8)


# --- 9 ----------------------------------------------------------------------------------------------------
def _t(names):
    return tuple(TOKEN_IDS[n] for n in names)


def _complete(prefix):
    """Finish a grammar-valid prefix the cheapest way: STATE whenever a subtree is due, else the lowest id."""
    prefix = tuple(prefix)
    while True:
        allowed = allowed_next(prefix)
        if not allowed:
            return prefix
        prefix += (TOKEN_IDS["STATE"],) if TOKEN_IDS["STATE"] in allowed else (min(allowed),)


def test_token_slots_follow_the_grammar():
    tree = sdg.binary("PLUS", sdg.leaf_ast(1, "C"), sdg.binary("TIMES", sdg.leaf_ast(2, "C", 3, "A"), sdg.leaf_ast(4, "E")))
    tokens = ast_to_tokens(tree)
    slots = sdg.token_slots(tokens)
    assert [s["slot"] for s in slots] == ["expr", "op", "expr", "noetic", "domain", "drive", "register", "expr", "op",
                                          "expr", "noetic", "domain", "drive", "register", "expr", "noetic", "domain",
                                          "drive", "register", "eos"]
    assert [s["path"] for s in slots][:3] == ["", "", "L"] and slots[7]["path"] == "R" and slots[9]["path"] == "RL"


def test_first_wrong_decision_kinds():
    target = _t(["BINARY", "TIMES", "STATE", "N1", "D_C", "F_NONE", "REG_ABSENT",
                 "BINARY", "PLUS", "STATE", "N2", "D_C", "F3", "REG_A", "STATE", "N4", "D_E", "F_NONE", "REG_ABSENT", "EOS"])
    assert sdg.first_wrong_decision(target, target) is None
    lost = _complete(target[:7] + (TOKEN_IDS["STATE"],))
    got = sdg.first_wrong_decision(lost, target)
    assert (got["index"], got["slot"], got["path"], got["mistake"]) == (7, "expr", "R", "LOST_BRANCH")
    invented = _complete(target[:2] + (TOKEN_IDS["BINARY"],))
    got = sdg.first_wrong_decision(invented, target)
    assert (got["index"], got["slot"], got["path"], got["mistake"]) == (2, "expr", "L", "INVENTED_BRANCH")
    op = target[:1] + (TOKEN_IDS["PLUS"],) + target[2:]
    assert sdg.first_wrong_decision(op, target)["mistake"] == "PLUS_FOR_TIMES"
    for index, name, mistake in ((3, "N7", "WRONG_NOETIC"), (4, "D_O", "WRONG_DOMAIN"), (12, "F_NONE", "WRONG_DRIVE"),
                                 (13, "REG_T", "WRONG_REGISTER")):
        wrong = target[:index] + (TOKEN_IDS[name],) + target[index + 1:]
        got = sdg.first_wrong_decision(wrong, target)
        assert got["mistake"] == mistake and got["index"] == index
    assert sdg.first_wrong_decision(target[:5], target)["mistake"] == "PREDICTION_ENDED"
    assert sdg.first_wrong_decision(target[:3] + (TOKEN_IDS["PLUS"],), target)["mistake"] == "GRAMMAR_VIOLATION"


def _trigger_file(tmp_path, out, triggers):
    body = {"schema": sdg.TRIGGERS_SCHEMA, "parent_manifest_sha256": sdg.manifest_sha(out), "triggers": triggers}
    path = tmp_path / ("triggers_%d.json" % len(list(tmp_path.iterdir())))
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_family_d_makes_fresh_rows_of_the_trigger_kind(package, tmp_path):
    out, _ = package
    train = _pairs(out, "train")
    feedback = _pairs(out, "feedback")
    binary_row = next(s for _, s in train if s["target_ast"]["node"] == "BinaryExpr")
    single_row = next(s for _, s in feedback if s["target_ast"]["node"] == "StateLiteral")
    t = tuple(binary_row["target_tokens"])
    right = binary_row["slot_paths"].index("R")        # the right child's expr decision
    wrong_branch = _complete(t[:right] + (TOKEN_IDS["BINARY"] if TOKENS[t[right]] == "STATE" else TOKEN_IDS["STATE"],))
    s = tuple(single_row["target_tokens"])
    wrong_noetic = s[:1] + (TOKEN_IDS["N%d" % ((int(TOKENS[s[1]][1:]) + 1) % 10)],) + s[2:]
    triggers = [{"source_split": "train", "source_record_id": binary_row["record_id"], "predicted_tokens": list(wrong_branch)},
                {"source_split": "feedback", "source_record_id": single_row["record_id"], "predicted_tokens": list(wrong_noetic)}]
    d_out = tmp_path / "d1"
    manifest = sdg.build_d_round(out, _trigger_file(tmp_path, out, triggers), d_out, seed=20260961, pinned=False)
    assert manifest["counts"]["D_train"] > 0
    parent_contents = {s["content_sha256"] for split in sdg.SPLITS for _, s in _pairs(out, split)}
    rows = sdg.load_lesson_pairs(d_out, "D", "train", pinned=False)
    mistake_one = "INVENTED_BRANCH" if TOKENS[t[right]] == "STATE" else "LOST_BRANCH"
    roles = collections.Counter()
    for visible, sealed in rows:
        assert sealed["content_sha256"] not in parent_contents
        key, depth = sealed["q3_tree_shape_key"], sealed["depth"]
        assert depth <= 3 and (key in sdg.G_TRAIN_SHAPES or key == sdg.SINGLE_STATE_KEY)
        constructor = sealed["provenance"]["constructor"]
        roles[(constructor["kind"], constructor["role"])] += 1
        if constructor["kind"] == "D_" + mistake_one:
            shape = q3.tree_shape(sealed["target_ast"])
            gold_kind = "L" if mistake_one == "INVENTED_BRANCH" else "B"
            other = "B" if gold_kind == "L" else "L"
            assert sdg.node_at(shape, "R") == (gold_kind if constructor["role"] == "target" else other)
    assert roles[("D_" + mistake_one, "target")] >= 1 and roles[("D_" + mistake_one, "control")] >= 1
    assert roles[("D_WRONG_NOETIC", "target")] >= 2      # each group is a gold/predicted noetic pair
    assert sdg.verify_package(d_out, pinned=False)["train"] == manifest["counts"]["D_train"]


def test_family_d_refuses_forbidden_trigger_sources(package, tmp_path):
    out, _ = package
    dev_row = _pairs(out, "dev")[0][1]
    t = dev_row["target_tokens"]
    q3_dev_id = q3_load.load_visible(sdg.Q3_DATA, "G", "dev")[0]["record_id"]
    cases = [({"source_split": "dev", "source_record_id": dev_row["record_id"], "predicted_tokens": t},
              "TRIGGER_SOURCE_NOT_A_TRAIN_OR_FEEDBACK_ROW"),
             ({"source_split": "train", "source_record_id": q3_dev_id, "predicted_tokens": t},
              "TRIGGER_FROM_Q3_DEV_ROW_REFUSED"),
             ({"source_split": "train", "source_record_id": "0" * 24, "predicted_tokens": t},
              "TRIGGER_SOURCE_NOT_A_TRAIN_OR_FEEDBACK_ROW")]
    for index, (trigger, code) in enumerate(cases):
        with pytest.raises(sdg.LessonError, match=code):
            sdg.build_d_round(out, _trigger_file(tmp_path, out, [trigger]), tmp_path / ("bad%d" % index),
                              seed=20260961, pinned=False)
    with pytest.raises(sdg.LessonError, match="TRIGGER_SOURCE_NOT_ALLOWED"):
        sdg.trigger_from_prediction("dev", "x", t, t)
    with pytest.raises(sdg.LessonError, match="SEED_NOT_NEW"):
        sdg.build_d_round(out, _trigger_file(tmp_path, out, []), tmp_path / "bad_seed", seed=sdg.SEED, pinned=False)
