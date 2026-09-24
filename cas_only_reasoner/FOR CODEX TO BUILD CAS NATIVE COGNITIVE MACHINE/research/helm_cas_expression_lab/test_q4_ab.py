"""Torch-free tests of the Q4-SDG-1 A-versus-B 0.2 build. NO torch, NO model, NO GPU, NO AWS call.

  1. FROZEN     hyperparameters equal run_001's plan; seeds are new; the frozen panel digests reproduce from the
                VISIBLE Q3 files with the pure-Python compiler engine (the AWS machines have no Rust engine).
  2. PANELS     SP1 is proportional, reserved and never taught; the 48 inspected dev rows are flagged; EDIT64 edits
                change exactly one field; panel content is excluded from BOTH arms' teaching (a real tiny B package).
  3. ORDER      epoch 0 of the stream is q4_smoke_job's shuffle; every epoch is a permutation.
  4. PACKAGE    the pin is required and must be the frozen package; package-digests compares two builds byte for byte;
                pin_package.py refuses anything but two identical verified builds and never overwrites a different pin.
  5. READER     read_q4_ab_results.py on results written by the RUNNER'S OWN evaluate() (driven by pure-Python fake
                models): input use, architecture, lessons, pair and run-validity labels; every refusal path.
  6. STATISTICS exact binomial and sign tests.
  7. JOBS       ceiling arithmetic ($5.00 for data build + training), launcher custody filters and pre-launch refusals,
                the watchers' safe unpacking of nested result folders, GPU_REQUIRED before any torch import.

Run (small, local):  python -B -m pytest test_q4_ab.py -q -p no:cacheprovider --basetemp <scratch folder>
"""
import collections
from fractions import Fraction
import importlib.util
import io
import json
from pathlib import Path
import random
import re
import sys
import tarfile

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import historical_compiler  # noqa: E402
import q4_ab_prep as prep  # noqa: E402
import q4_ab_rules as rules  # noqa: E402
import q4_ab_train as train  # noqa: E402
import q4_error_panel as ep  # noqa: E402
import q4_sdg_curriculum as sdg  # noqa: E402
import read_q4_ab_results as reader  # noqa: E402
from learner_q4_decoder import TOKENS, allowed_next, ast_to_tokens  # noqa: E402
from learner_q4_representation import Bottleneck  # noqa: E402

CNCM = HERE.parents[1]
RUN = CNCM / "records" / "q4_authorized_20260922" / "run_001"
DATA = HERE / "data" / "q3_v0_7"
JOBS = CNCM / "records" / "q4_sdg_1_20260923"
NEEDS_JOBS = pytest.mark.skipif(not JOBS.is_dir(), reason="the AWS bundle carries the lab and run_001 only, not the job folders")
T1_SMALLEST_PASSING_K = 112     # of 799 SP1 noetic positions (14.0%), for arm A; stated in the spec, section 7


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------------------------------------
# fixtures
# ------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def python_engine():
    """Force the pure-Python compiler engine, as on the AWS machines (no Rust engine there)."""
    module = historical_compiler.load_historical_compiler()
    saved = module.cas_engine
    module.cas_engine = None
    yield
    module.cas_engine = saved


@pytest.fixture(scope="module")
def q3prep(python_engine):
    compiler = sdg.Compiler()
    assert compiler.engine == "python"
    return prep.prepare_q3(RUN, DATA, compiler, strict=True), compiler


@pytest.fixture(scope="module")
def tiny(tmp_path_factory, python_engine, q3prep):
    """Two tiny real B packages (size 16), a temporary pin for build 1, and its B rows through the pinned door."""
    base = tmp_path_factory.mktemp("q4ab_pkg")
    b1, b2 = base / "b1" / "q4_sdg_v0_1", base / "b2" / "q4_sdg_v0_1"
    manifest = sdg.build(b1, 16, expect_engine="python")
    sdg.build(b2, 16, expect_engine="python")
    pins = base / "pins.json"
    body = json.loads(sdg.PINS.read_text(encoding="utf-8"))
    body["data_versions"] = {sdg.SCHEMA: {"data_dir": "x", "manifest_sha256": sdg.manifest_sha(b1)}}
    pins.write_text(json.dumps(body), encoding="utf-8")
    q3p, compiler = q3prep
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sdg, "PINS", pins)
        bprep = prep.prepare_b(b1, compiler, q3p["panel_contents"])
    return {"b1": b1, "b2": b2, "manifest": manifest, "pins": pins, "bprep": bprep, "base": base}


# ------------------------------------------------------------------------------------------------------------
# 1. frozen values
# ------------------------------------------------------------------------------------------------------------
def test_modules_import_no_torch():
    assert "torch" not in sys.modules
    for name in ("q4_ab_train.py", "q4_ab_prep.py", "read_q4_ab_results.py", "q4_ab_rules.py"):
        source = (HERE / name).read_text(encoding="utf-8")
        assert "\nimport torch" not in source and "\nfrom torch" not in source, name


def test_hyperparameters_equal_run_001_and_the_smoke_call_order():
    plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
    assert (rules.WIDTH, rules.LEARNING_RATE, rules.CLIP_NORM) == (plan["width"], plan["learning_rate"], plan["clip_norm"])
    assert rules.NUMERICAL_POLICY == plan["numerical_policy"]
    assert rules.sha(rules.canonical(plan)) == rules.RUN_001_PLAN_SHA256
    smoke = (HERE / "q4_smoke_job.py").read_text(encoding="utf-8")
    runner = (HERE / "q4_ab_train.py").read_text(encoding="utf-8")
    smoke_order = ["torch.manual_seed(plan[\"seed\"])", "torch.cuda.manual_seed_all(plan[\"seed\"])",
                   "torch.use_deterministic_algorithms(True)", "build_model(NeuralConfig(plan[\"width\"])",
                   "torch.optim.AdamW(model.parameters(), lr=plan[\"learning_rate\"])",
                   "random.Random(plan[\"seed\"]).shuffle(order)", "optimizer.zero_grad(set_to_none=True)",
                   "model.teacher_forced_logits(training_inputs[index], target[:-1])",
                   "torch.nn.functional.cross_entropy(logits, gold)", "loss.backward()",
                   "clip_grad_norm_(model.parameters(), plan[\"clip_norm\"], error_if_nonfinite=True)",
                   "optimizer.step()"]
    ours = ["torch.manual_seed(seed)", "torch.cuda.manual_seed_all(seed)", "set_deterministic(torch)",
            "build_model(NeuralConfig(rules.WIDTH)", "torch.optim.AdamW(model.parameters(), lr=rules.LEARNING_RATE)",
            "prep.stream_indices(len(pool), seed, updates)", "optimizer.zero_grad(set_to_none=True)",
            "model.teacher_forced_logits(inputs[index], target[:-1])",
            "torch.nn.functional.cross_entropy(logits, gold)", "loss.backward()",
            "clip_grad_norm_(model.parameters(), rules.CLIP_NORM, error_if_nonfinite=True)", "optimizer.step()"]
    for text, order in ((smoke, smoke_order), (runner[runner.index("def train_run"):], ours)):
        positions = [text.index(item) for item in order]
        assert positions == sorted(positions)


def test_seeds_are_new_and_pairs_share_them():
    used = set(rules.Q3_SEEDS) | {sdg.SEED, sdg.FEEDBACK_SEED, ep.PANEL_SEED, ep.INIT_SEED, 20260961, 20260980}
    assert len(set(rules.SEEDS)) == 3 and not set(rules.SEEDS) & used and rules.SP1_SEED not in used | set(rules.SEEDS)
    assert rules.RUN_ORDER == (("A", rules.SEEDS[0]), ("B", rules.SEEDS[0]), ("A", rules.SEEDS[1]),
                               ("B", rules.SEEDS[1]), ("A", rules.SEEDS[2]), ("B", rules.SEEDS[2]))
    assert rules.CHECKPOINTS[0] == 0 and rules.CHECKPOINTS[-1] == rules.UPDATES == rules.FINAL
    assert list(rules.CHECKPOINTS) == sorted(set(rules.CHECKPOINTS))
    assert rules.B_PACKAGE["seed"] == sdg.SEED and rules.B_PACKAGE["feedback_seed"] == sdg.FEEDBACK_SEED
    assert rules.B_PACKAGE["schema"] == sdg.SCHEMA


def test_frozen_digests_reproduce_from_visible_files(q3prep):
    q3p, _ = q3prep                       # prepare_q3(strict=True) already refused any difference
    frozen = rules.frozen_record()["digests"]
    for key, value in q3p["measured"].items():
        assert frozen[key] == value, key
    assert set(q3p["measured"]) == set(rules.MEASURED_DIGEST_KEYS) <= set(frozen)
    assert "TO_BE_MEASURED" not in json.dumps(frozen)
    assert rules.most_frequent_rate(prep.class_counts(q3p["sp1"], "noetic")) == rules.SP1_NOETIC_NULL == Fraction(90, 799)
    assert rules.most_frequent_rate(prep.class_counts(q3p["a_pool"], "noetic")) == rules.A_POOL_NOETIC_NULL


def test_strict_prep_refuses_a_changed_digest(q3prep, monkeypatch):
    q3p, _ = q3prep
    prep.check_frozen_digests(q3p["measured"])
    for key in q3p["measured"]:
        changed = dict(q3p["measured"], **{key: "0" * 64})
        with pytest.raises(prep.PrepError, match="PANEL_DIGEST_MISMATCH: %s" % key):
            prep.check_frozen_digests(changed)
    monkeypatch.setattr(rules, "SP1_DIGEST", "0" * 64)
    with pytest.raises(prep.PrepError, match="PANEL_DIGEST_MISMATCH: sp1"):
        prep.check_frozen_digests(q3p["measured"])
    source = (HERE / "q4_ab_prep.py").read_text(encoding="utf-8")
    assert "if strict:" + chr(10) + "        check_frozen_digests(measured)" in source


# ------------------------------------------------------------------------------------------------------------
# 2. panels and exclusions
# ------------------------------------------------------------------------------------------------------------
def test_sp1_is_proportional_reserved_and_never_taught(q3prep):
    q3p, _ = q3prep
    sp1, a_pool = q3p["sp1"], q3p["a_pool"]
    assert len(sp1) == rules.SP1_SIZE == 256 and len({r["content_sha256"] for r in sp1}) == 256
    inspected_train = set(q3p["inspection"]["train_ids"])
    assert len(inspected_train) == 48 and not {r["record_id"] for r in sp1} & inspected_train
    available = collections.Counter(r["q3_tree_shape_key"] for r in q3p["train_rows"] if r["record_id"] not in inspected_train)
    alloc = prep.sp1_allocation(dict(available))
    assert collections.Counter(r["q3_tree_shape_key"] for r in sp1) == +collections.Counter(alloc)
    total = sum(available.values())
    for key, n in alloc.items():                         # largest remainder: within one row of the exact share
        assert abs(n - rules.SP1_SIZE * available[key] / total) < 1 and n <= available[key] // 2
    assert set(r["q3_tree_shape_key"] for r in sp1) <= set(sdg.G_TRAIN_SHAPES)
    panel = {r["content_sha256"] for r in sp1} | {r["content_sha256"] for r in q3p["sp2"]}
    assert not panel & {r["content_sha256"] for r in a_pool}
    assert not {r["record_id"] for r in sp1} & {r["record_id"] for r in a_pool}
    assert len(a_pool) == rules.A_POOL_ROWS == 2048 - 256
    assert [r["record_id"] for r in a_pool] == [r["record_id"] for r in q3p["train_rows"] if r["record_id"] not in {x["record_id"] for x in sp1}]


def test_sp2_flags_exactly_the_48_inspected_dev_rows(q3prep):
    q3p, _ = q3prep
    sp2 = q3p["sp2"]
    flagged = [r for r in sp2 if r["inspected"]]
    assert len(sp2) == 256 and len(flagged) == 48
    assert {r["record_id"] for r in sp2[:16]} <= {r["record_id"] for r in flagged}          # old_dev16
    assert set(q3p["inspection"]["dev_ids"]) == {r["record_id"] for r in flagged}
    assert q3p["inspection"]["selection_digest"] == rules.DIAGNOSTIC_SELECTION_DIGEST


def test_edit_panel_changes_one_field_each(q3prep):
    q3p, _ = q3prep
    rows = {r["record_id"]: r for r in q3p["sp1"]}
    assert [r["record_id"] for r in q3p["edit_rows"]] == [r["record_id"] for r in q3p["sp1"][::rules.EDIT_STRIDE]]
    assert len(q3p["edit_rows"]) == 64
    measured = [e for e in q3p["edit_items"] if e["to"] is not None]
    assert len(measured) == rules.EDIT_COUNT
    for item in measured[::7]:
        row = rows[item["row"]]
        edited = ast_to_tokens(sdg.parse_surface(item["observation"]))
        diff = sdg.differing_positions(row["target_tokens"], edited)
        assert diff == [item["position"]] and row["slot_kinds"][item["position"]] == item["field"]
    runtime = train.runtime_edits(q3p["edit_items"], rows)
    assert len(runtime) == rules.EDIT_COUNT
    for edit in runtime[:40]:
        assert edit["new"] in edit["allowed"] and edit["old"] in edit["allowed"] and edit["old"] != edit["new"]
    # value versus presence edits (review MINOR 1): the from/to rule equals the input-length rule on every edit
    kinds = collections.Counter((rules.edit_kind(e["field"], e["from"], e["to"]), e["field"]) for e in measured)
    assert {f: kinds[("value", f)] for f in rules.VALUE_EDIT_COUNTS} == rules.VALUE_EDIT_COUNTS
    assert {f: kinds[("presence", f)] for f in rules.PRESENCE_EDIT_COUNTS} == rules.PRESENCE_EDIT_COUNTS
    assert (rules.VALUE_EDIT_COUNT, rules.PRESENCE_EDIT_COUNT) == (538, 235)
    for item in measured:
        presence = len(item["observation"]) != len(rows[item["row"]]["observation"])
        assert presence == (rules.edit_kind(item["field"], item["from"], item["to"]) == "presence"), item["observation"]
    assert collections.Counter(e["new_token"] for e in measured
                               if rules.edit_kind(e["field"], e["from"], e["to"]) == "presence") == {
        "F1": 95, "REG_T": 102, "REG_ABSENT": 25, "F_NONE": 13}


def test_panel_content_is_excluded_from_b_teaching(tiny, q3prep):
    q3p, compiler = q3prep
    bprep = tiny["bprep"]
    assert bprep["b_train_rows"] and not bprep["b_dropped"]           # nothing in this tiny package collides
    victim = bprep["b_train_rows"][0]
    pool, dropped = prep.teaching_pool(bprep["b_train_rows"], set(), q3p["panel_contents"] | {victim["content_sha256"]})
    assert dropped == [victim] and victim not in pool and len(pool) == len(bprep["b_train_rows"]) - 1
    for row in bprep["b_train_rows"]:
        assert sdg.parse_surface(row["observation"]) == row["target_ast"]
    assert all(r["panel"] == "B_TRAIN" for r in bprep["b_train_rows"])


def test_near_twins_and_class_counts():
    rows = [{"record_id": "p", "target_tokens": [1, 5, 15, 21, 29, 0]}]
    pool = [{"record_id": "a", "target_tokens": [1, 6, 15, 21, 29, 0]},
            {"record_id": "b", "target_tokens": [1, 7, 16, 21, 29, 0]},
            {"record_id": "c", "target_tokens": [2, 1, 3, 1, 5, 15, 21, 29, 1, 5, 15, 21, 29, 0]}]
    assert prep.near_twin_distances(rows, pool) == {"p": 1}
    assert prep.near_twin_distances(rows, pool[2:]) == {"p": None}
    leaf = sdg.leaf_ast(3, "C", 2, "A")
    counts = prep.class_counts([{"target_ast": sdg.binary("PLUS", leaf, sdg.leaf_ast(3, "E"))}], "noetic")
    assert counts["3"] == 2 and sum(counts.values()) == 2 and set(counts) == {str(n) for n in range(10)}
    assert rules.most_frequent_rate(counts) == 1


# ------------------------------------------------------------------------------------------------------------
# 3. order
# ------------------------------------------------------------------------------------------------------------
def test_stream_epoch_zero_is_the_smoke_jobs_shuffle():
    for n, seed in ((1792, rules.SEEDS[0]), (4096, rules.SEEDS[1]), (7, 5)):
        order = list(range(n))
        random.Random(seed).shuffle(order)
        stream = prep.stream_indices(n, seed, 3 * n + 5)
        assert stream[:n] == order
        for epoch in range(3):
            assert sorted(stream[epoch * n:(epoch + 1) * n]) == list(range(n))
        assert prep.stream_indices(n, seed, 3 * n + 5) == stream and len(stream) == 3 * n + 5
    assert prep.stream_indices(1792, rules.SEEDS[0], rules.UPDATES)[:10] != prep.stream_indices(1792, rules.SEEDS[1], 10)


# ------------------------------------------------------------------------------------------------------------
# 4. package, pin, digests
# ------------------------------------------------------------------------------------------------------------
def test_real_pin_file_is_either_empty_or_the_frozen_package():
    try:
        entry = prep.read_pin_entry()
    except prep.PrepError as error:
        assert str(error).startswith("B_PACKAGE_NOT_PINNED")
    else:
        assert entry["engine"] == "python" and entry["size"] == 4096


def test_pin_entry_must_be_the_frozen_package(tmp_path, tiny):
    digests = prep.package_digests(tiny["b1"], tiny["b2"], 0)
    good = dict(digests["pin_entry"], data_dir=rules.B_PACKAGE["data_dir"], size=4096)
    for broken, code in ((dict(good, engine="rust+python"), "B_PIN_NOT_THE_FROZEN_PACKAGE"),
                         (dict(good, seed=1), "B_PIN_NOT_THE_FROZEN_PACKAGE"),
                         (dict(good, files={}), "B_PIN_NOT_THE_FROZEN_PACKAGE"),
                         (dict(good, manifest_sha256="x"), "B_PIN_NOT_THE_FROZEN_PACKAGE"),
                         (None, "B_PACKAGE_NOT_PINNED")):
        path = tmp_path / ("pins_%s.json" % code)
        versions = {} if broken is None else {sdg.SCHEMA: broken}
        path.write_text(json.dumps({"schema": sdg.PINS_SCHEMA, "data_versions": versions}), encoding="utf-8")
        with pytest.raises(prep.PrepError, match=code):
            prep.read_pin_entry(path)
    path = tmp_path / "pins_good.json"
    path.write_text(json.dumps({"schema": sdg.PINS_SCHEMA, "data_versions": {sdg.SCHEMA: good}}), encoding="utf-8")
    assert prep.read_pin_entry(path)["manifest_sha256"] == sdg.manifest_sha(tiny["b1"])


def test_rebuilt_package_must_equal_the_pin(tiny, monkeypatch):
    digests = prep.package_digests(tiny["b1"], tiny["b2"], 0)
    entry = dict(digests["pin_entry"], data_dir=rules.B_PACKAGE["data_dir"])
    monkeypatch.setattr(sdg, "PINS", tiny["pins"])
    with pytest.raises(prep.PrepError, match="B_PACKAGE_MISMATCH"):          # size 16 is not the frozen 4096
        prep.check_package(tiny["b1"], entry)
    monkeypatch.setitem(rules.B_PACKAGE, "size", 16)
    assert prep.check_package(tiny["b1"], entry)["schema"] == sdg.SCHEMA
    with pytest.raises(prep.PrepError, match="B_PACKAGE_MISMATCH"):
        prep.check_package(tiny["b1"], dict(entry, manifest_sha256="0" * 64))


def test_package_digests_compare_two_builds_byte_for_byte(tiny, tmp_path, monkeypatch):
    digests = prep.package_digests(tiny["b1"], tiny["b2"], 0)
    assert digests["rebuild_byte_identical"] and digests["manifest_files_match_disk"]
    assert digests["status"] == "PACKAGE_NOT_PINNABLE"                        # size 16 is not the frozen package
    monkeypatch.setitem(rules.B_PACKAGE, "size", 16)
    assert prep.package_digests(tiny["b1"], tiny["b2"], 0)["status"] == "REBUILD_BYTE_IDENTICAL_AND_VERIFIED"
    assert prep.package_digests(tiny["b1"], tiny["b2"], 1)["status"] == "PACKAGE_NOT_PINNABLE"
    tampered = tmp_path / "b3" / "q4_sdg_v0_1"
    tampered.mkdir(parents=True)
    for path in tiny["b2"].iterdir():
        tampered.joinpath(path.name).write_bytes(path.read_bytes())
    name = "visible_A_train.jsonl"
    tampered.joinpath(name).write_bytes(tampered.joinpath(name).read_bytes() + b" ")
    bad = prep.package_digests(tiny["b1"], tampered, 0)
    assert not bad["rebuild_byte_identical"] and not bad["all_files"][name]["identical"]
    assert bad["status"] == "PACKAGE_NOT_PINNABLE"


@NEEDS_JOBS
def test_pin_package_tool_refuses_and_never_overwrites(tiny, tmp_path, monkeypatch):
    pin_tool = _load(JOBS / "data_build_job" / "pin_package.py", "q4ab_pin_package")
    monkeypatch.setitem(rules.B_PACKAGE, "size", 16)
    results = tmp_path / "results"
    results.mkdir()
    digests = prep.package_digests(tiny["b1"], tiny["b2"], 0)
    (results / "build_digests.json").write_text(json.dumps(digests), encoding="utf-8")
    (results / "manifest.json").write_bytes((tiny["b1"] / "manifest.json").read_bytes())
    entry = pin_tool.pin_entry(results, {"instance_id": "i-test", "identity": {"source_commit": "c" * 40}}, None)
    assert entry["engine"] == "python" and entry["manifest_sha256"] == sdg.manifest_sha(tiny["b1"])
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"schema": sdg.PINS_SCHEMA, "data_versions": {}, "status": "EMPTY"}), encoding="utf-8")
    written, changed = pin_tool.write_pin(entry, pins)
    assert changed and prep.read_pin_entry(pins)["manifest_sha256"] == entry["manifest_sha256"]
    monkeypatch.setattr(sdg, "PINS", pins)
    assert sdg.check_pin(tiny["b1"])["manifest_sha256"] == entry["manifest_sha256"]
    assert pin_tool.write_pin(entry, pins)[1] is False                         # identical: a no-op
    with pytest.raises(pin_tool.PinError, match="PIN_CONFLICT"):
        pin_tool.write_pin(dict(entry, manifest_sha256="0" * 64), pins)
    for key, value in (("rebuild_byte_identical", False), ("verify_exit_code", 2), ("status", "PACKAGE_NOT_PINNABLE")):
        (results / "build_digests.json").write_text(json.dumps(dict(digests, **{key: value})), encoding="utf-8")
        with pytest.raises(pin_tool.PinError, match="NOT_PINNABLE"):
            pin_tool.pin_entry(results)
    (results / "build_digests.json").write_text(json.dumps(digests), encoding="utf-8")
    (results / "manifest.json").write_bytes((tiny["b1"] / "manifest.json").read_bytes() + b"\n")
    with pytest.raises(pin_tool.PinError, match="MANIFEST_DIGEST_DIFFERS"):
        pin_tool.pin_entry(results)


# ------------------------------------------------------------------------------------------------------------
# 5. the reader, on records made by the runner's own evaluate() with pure-Python fake models
# ------------------------------------------------------------------------------------------------------------
FAKE_MODES = ("blind", "reader", "tf_reader_freegen_collapse", "no_noetic", "structure_only", "shape_operators_only",
              "shape_only")


def _shape_reader(keep_operators):
    """The verifier's scratch fakes of 294471a5 (V1, V2), made tests: keep the tree shape (and the PLUS/TIMES operators
    when keep_operators); write N0, D_P, F_NONE and REG_ABSENT at every leaf. No field value, no field presence."""
    def mapped(tokens):
        out = []
        for token in tokens:
            name = TOKENS[token]
            if re.fullmatch(r"N[0-9]", name):
                name = "N0"
            elif name.startswith("D_"):
                name = "D_P"
            elif name == "F_NONE" or re.fullmatch(r"F[1-7]", name):
                name = "F_NONE"
            elif name.startswith("REG_"):
                name = "REG_ABSENT"
            elif name in ("PLUS", "TIMES") and not keep_operators:
                name = "PLUS"
            out.append(TOKENS.index(name))
        return out
    return mapped


SHAPE_READERS = {"shape_operators_only": _shape_reader(True), "shape_only": _shape_reader(False)}


def _structure_only(tokens):
    """Keep the shape, the operators and whether each leaf has a drive or register; write N0, D_P, F1, REG_T."""
    out = []
    for token in tokens:
        name = TOKENS[token]
        if re.fullmatch(r"N[0-9]", name):
            name = "N0"
        elif name.startswith("D_"):
            name = "D_P"
        elif re.fullmatch(r"F[1-7]", name):
            name = "F1"
        elif name.startswith("REG_") and name != "REG_ABSENT":
            name = "REG_T"
        out.append(TOKENS.index(name))
    return out


class FakeModel:
    """NOT Q4. Pure-Python stand-ins, only for wiring the runner's evaluate() to the reader. Modes:
      blind                       ignores its input; always writes the same one-state tree
      reader                      decodes the true tree of whatever text it is given (a perfect reader)
      tf_reader_freegen_collapse  reads every field when given the correct previous tokens, but its first free
                                  decision is always STATE (review of 3771f989, MAJOR: T1 799/799, 1 distinct output)
      no_noetic                   reads domain, drive and register values, never the Noetic (always N0)
      structure_only              reads shape, operators and field presence only (review MINOR 1: 180 distinct)
      shape_operators_only        reads shape and PLUS/TIMES only (verification of 294471a5, V1: 44 distinct)
      shape_only                  reads shape only; always PLUS (verification of 294471a5, V2: 14 distinct)
    """

    def __init__(self, mode):
        if mode not in FAKE_MODES:
            raise ValueError(mode)
        self.mode, self.texts, self.tokens = mode, [], {}

    def encode(self, sequence):
        text = bytes(b - 1 for b in sequence.byte_ids).decode("utf-8")
        if text not in self.tokens:
            self.tokens[text] = ast_to_tokens(sdg.parse_surface(text))
            self.texts.append(text)
        return Bottleneck((0.0 if self.mode == "blind" else float(self.texts.index(text)), 1.0))

    def _true_and_wanted(self, bottleneck):
        if self.mode == "blind":
            fixed = ast_to_tokens(sdg.leaf_ast(0, "P"))
            return fixed, fixed
        true = list(self.tokens[self.texts[int(bottleneck.values[0])]])
        if self.mode == "no_noetic":
            return true, [TOKENS.index("N0") if re.fullmatch(r"N[0-9]", TOKENS[t]) else t for t in true]
        if self.mode == "structure_only":
            return true, _structure_only(true)
        if self.mode in SHAPE_READERS:
            return true, SHAPE_READERS[self.mode](true)
        return true, true

    def next_logits(self, bottleneck, prefix):
        true, want = self._true_and_wanted(bottleneck)
        n, prefix = len(prefix), tuple(prefix)
        if self.mode == "tf_reader_freegen_collapse" and n == 0:
            choice = TOKENS.index("STATE")
        elif n < len(want) and (prefix == tuple(true[:n]) or prefix == tuple(want[:n])):
            choice = want[n]
        else:
            choice = None
        logits = [0.0] * len(TOKENS)
        allowed = allowed_next(prefix)
        logits[choice if choice in allowed else min(allowed)] = 5.0
        return tuple(logits)


def _fake_teacher_logits(model, row):
    from learner_q4_representation import encode_observation
    bottleneck = model.encode(encode_observation(row["observation"]))
    target = row["target_tokens"]
    return [list(model.next_logits(bottleneck, tuple(target[:i]))) for i in range(len(target))]


class _NoDeadline:
    def check(self):
        return None


@pytest.fixture(scope="module")
def fake_records(q3prep, tiny):
    """evaluate() of the RUNNER on the full shared panels and edits, once per fake mode; TEACH_FIT per arm."""
    q3p, _ = q3prep
    bprep = tiny["bprep"]
    record = prep.prep_record(q3p, bprep, sdg.manifest_sha(tiny["b1"]))
    shared = {"SP1": [prep.with_allowed(r) for r in q3p["sp1"]], "SP2": [prep.with_allowed(r) for r in q3p["sp2"]],
              "B_DEV": [prep.with_allowed(r) for r in bprep["b_dev"]]}
    edits = train.runtime_edits(q3p["edit_items"], {r["record_id"]: r for r in q3p["sp1"]})
    pools = {"A": q3p["a_pool"], "B": bprep["b_pool"]}
    out = {"prep": record, "teach": {}, "records": {}}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ep, "teacher_logits", _fake_teacher_logits)
        for arm in rules.ARMS:
            out["teach"][arm] = [prep.with_allowed(dict(pools[arm][i], panel="TEACH_FIT"))
                                 for i in prep.stream_indices(len(pools[arm]), rules.SEEDS[0], min(4, len(pools[arm])))]
        for mode in FAKE_MODES:
            model = FakeModel(mode)
            base = train.evaluate(model, shared, edits, record["sp1_partners"], _NoDeadline())
            for arm in rules.ARMS:
                teach = train.evaluate(model, {"TEACH_FIT": out["teach"][arm]}, [], [], _NoDeadline())
                body = json.loads(rules.canonical(base))
                body["panels"]["TEACH_FIT"] = teach["panels"]["TEACH_FIT"]
                out["records"][(arm, mode)] = body
    out["bytes"] = {key: rules.canonical(value) for key, value in out["records"].items()}
    return out


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rules.canonical(value) + b"\n")


def _make_exact(record, panel, ids, prep_rows):
    """Turn the listed rows of one panel into exact reconstructions (and keep the runner's totals consistent)."""
    targets = {r["id"]: r["target_tokens"] for r in prep_rows}
    for row in record["panels"][panel]["rows"]:
        if row["id"] in ids:
            row.update(free=list(targets[row["id"]]), outcome="GENERATED", exact=1, fwd=None)
    rows = record["panels"][panel]["rows"]
    record["panels"][panel]["exact"] = sum(r["exact"] for r in rows)
    record["panels"][panel]["distinct_free_outputs"] = len({tuple(r["free"]) for r in rows})


def write_results(root, fake, *, reads=None, modes=None, exact=None, stage0="REPRODUCED_16_OF_16", missing=(),
                  reload_bad=(), init_bad=(), inconsistent=(), job_status="COMPLETE", fires_at_zero=False,
                  zero_modes=None, frozen_override=None, mutate_prep=None, mutate_final=None, inconsistent_zero=()):
    """A complete synthetic results folder. `modes[(arm, seed)]` = the fake mode of the final-checkpoint model
    (default blind); `reads[(arm, seed)] = True` is short for mode "reader"; `zero_modes[(arm, seed)]` = the mode at
    checkpoint 0 (default blind; `fires_at_zero` = "reader" for every run); `exact[(arm, seed)]` = {panel: ids} made
    exact at the final checkpoint; `mutate_prep(record)` and `mutate_final(key, body)` alter the written files;
    `inconsistent` / `inconsistent_zero` flip one SP1 exact flag at the FINAL checkpoint / at checkpoint 0.
    As the runner does: a COMPLETE job_result.json lists all six runs, and every run manifest carries its arm, seed and
    pool_ids_digest (revision 3c, Y1 and N3). A run that was never written belongs to a STOPPED job."""
    root = Path(root)
    modes = dict(modes or {})
    for key, value in (reads or {}).items():
        if value:
            modes[key] = "reader"
    record = json.loads(rules.canonical(fake["prep"]))
    if frozen_override:
        record["frozen"] = dict(record["frozen"], **frozen_override)
    if mutate_prep:
        mutate_prep(record)
    _write(root / "prep.json", record)
    _write(root / "stage0.json", {"status": stage0, "reinit_update_1": {"reproduced": True}})
    job = {"status": job_status, "stop_code": None if job_status == "COMPLETE" else "JOB_WALL_LIMIT"}
    if job_status == "COMPLETE":
        job["runs"] = ["%s_%d" % key for key in rules.RUN_ORDER]
    _write(root / "job_result.json", job)
    frozen = rules.frozen_sha256()
    for arm, seed in rules.RUN_ORDER:
        if (arm, seed) in missing:
            continue
        folder = root / "runs" / ("%s_%d" % (arm, seed))
        teach = fake["teach"][arm]
        init = "init-%d" % seed + ("-other" if (arm, seed) in init_bad else "")
        ids = (record.get("pools", {}).get(arm) or {}).get("ids")
        _write(folder / "run_manifest.json", {"arm": arm, "seed": seed, "frozen_sha256": frozen, "init_state_sha256": init,
                                              "pool_ids_digest": prep.ids_digest([{"record_id": i} for i in ids or []]),
                                              "teach_fit": [prep.panel_row_record(r) for r in teach]})
        for point in rules.CHECKPOINTS:
            if point == rules.FINAL:
                mode = modes.get((arm, seed), "blind")
            elif point == 0:
                mode = "reader" if fires_at_zero else (zero_modes or {}).get((arm, seed), "blind")
            else:
                mode = "blind"
            body = json.loads(fake["bytes"][(arm, mode)])
            if point == rules.FINAL:
                for panel, ids in ((exact or {}).get((arm, seed)) or {}).items():
                    _make_exact(body, panel, ids, record["panels"][panel])
                if (arm, seed) in inconsistent:
                    body["panels"]["SP1"]["rows"][0]["exact"] = 1 - body["panels"]["SP1"]["rows"][0]["exact"]
                if mutate_final:
                    mutate_final((arm, seed), body)
            if point == 0 and (arm, seed) in inconsistent_zero:           # review of f32b5739, X1
                body["panels"]["SP1"]["rows"][0]["exact"] = 1 - body["panels"]["SP1"]["rows"][0]["exact"]
            body.update(arm=arm, seed=seed, checkpoint=point, frozen_sha256=frozen)
            _write(folder / ("checkpoint_%05d.json" % point), body)
        _write(folder / "run_result.json", {"status": "COMPLETE", "updates": rules.UPDATES, "frozen_sha256": frozen,
                                            "presentations": rules.UPDATES})
        _write(folder / "reload_check.json", {"status": "RELOAD_MISMATCH" if (arm, seed) in reload_bad else "RELOAD_REPRODUCED"})
    return root


S1, S2, S3 = rules.SEEDS


def test_runner_records_satisfy_the_reader_and_the_levels_separate_the_fakes(fake_records):
    """Measured on the RUNNER'S OWN evaluate(): every fake gets the level the review predicts."""
    prep_record, records = fake_records["prep"], fake_records["records"]
    blind, reading = records[("A", "blind")], records[("A", "reader")]
    assert blind["panels"]["SP1"]["distinct_free_outputs"] == 1 and blind["panels"]["SP1"]["exact"] == 0
    assert reading["panels"]["SP1"]["exact"] == 256 and reading["panels"]["SP2"]["exact"] == 256
    assert len(reading["edits"]["values"]) == rules.EDIT_COUNT and reading["edits"]["columns"] == list(rules.EDIT_VALUE_COLUMNS)
    expected = {"blind": "NONE", "reader": "FULL", "tf_reader_freegen_collapse": "TEACHER_FORCED_ONLY",
                "no_noetic": "PARTIAL_FIELDS", "structure_only": "STRUCTURE_OR_OUTPUT_VARIATION",
                "shape_operators_only": "STRUCTURE_OR_OUTPUT_VARIATION", "shape_only": "STRUCTURE_OR_OUTPUT_VARIATION"}
    assert set(expected) == set(FAKE_MODES)
    for arm in rules.ARMS:
        for mode, level in expected.items():
            reading_ = reader.input_use(records[(arm, mode)], arm, prep_record)
            assert (reading_["level"], reading_["label"]) == (level, "INPUT_USE_" + level), (arm, mode)
    noetic_positions = sum(prep_record["sp1_noetic_counts"].values())
    full = reader.input_use(reading, "A", prep_record)
    assert full["T1"]["correct"] == full["T1"]["n"] == noetic_positions == 799
    assert (full["T2V"]["up"], full["T2V"]["down"], full["T2P"]["up"]) == (rules.VALUE_EDIT_COUNT, 0, rules.PRESENCE_EDIT_COUNT)
    t1 = reader.input_use(blind, "A", prep_record)["T1"]
    assert t1["correct"] == prep_record["sp1_noetic_counts"]["0"] == 88 and not t1["passes"]          # always N0
    # the reviewers' TF_READER_FREEGEN_COLLAPSE: reads every field with the correct prefix; free generation collapses
    tf = reader.input_use(records[("A", "tf_reader_freegen_collapse")], "A", prep_record)
    assert tf["T1"]["correct"] == 799 and tf["T2V"]["passes"] and tf["T3"]["distinct_free_outputs"] == 1
    # reads domain, drive and register values but not the Noetic: T1 fails, T2V passes on the other three fields
    partial = reader.input_use(records[("A", "no_noetic")], "A", prep_record)
    assert partial["T1"]["correct"] == 88 and not partial["T1"]["passes"] and partial["T2V"]["passes"]
    assert partial["T2V"]["up"] == rules.VALUE_EDIT_COUNT - rules.VALUE_EDIT_COUNTS["noetic"] == 342
    assert partial["T2V_BY_FIELD_REPORTED_NOT_DECISIVE"]["noetic"]["up"] == 0
    # the reviewers' STRUCTURE_ONLY: passes the OLD T2 (all edits) and T3, but no field-value test
    structure = reader.input_use(records[("A", "structure_only")], "A", prep_record)
    assert structure["T1"]["correct"] == 88 and not structure["T2V"]["passes"] and structure["T2V"]["up"] == 0
    assert structure["T2P"]["up"] == rules.PRESENCE_EDIT_COUNT == 235 and structure["T2P"]["down"] == 0
    assert structure["T3"]["distinct_free_outputs"] == 180 and structure["T3"]["passes"]
    assert structure["T2_ALL_EDITS_REPORTED_NOT_DECISIVE"]["passes"]          # the old T2 would have passed
    # the verifier's V1 and V2 fakes (verification of 294471a5): no field value, no field presence, but the free
    # outputs depend on the input. Revision 2 graded both NONE; revision 3 (coordinator decision 1) does not.
    for mode, distinct in (("shape_operators_only", 44), ("shape_only", 14)):
        shape = reader.input_use(records[("A", mode)], "A", prep_record)
        assert shape["T1"]["correct"] == 88 and shape["T1"]["n"] == 799 and not shape["T1"]["passes"], mode
        assert (shape["T2V"]["up"], shape["T2V"]["down"], shape["T2P"]["up"], shape["T2P"]["down"]) == (0, 0, 0, 0), mode
        assert shape["T3"]["distinct_free_outputs"] == distinct and shape["T3"]["output_varies"], mode
        assert shape["T3"]["passes"] == (distinct >= rules.T3_MIN_DISTINCT), mode
    assert not reader.input_use(blind, "A", prep_record)["T3"]["output_varies"]


# The four distinct-output classes that matter: exactly 1 (NONE possible), 2..31 (varies, T3 fails), >= 32 (T3).
DISTINCT_CASES = (1, 2, rules.T3_MIN_DISTINCT - 1, rules.T3_MIN_DISTINCT, 256)


def _level_table():
    return {(t1, t2v, t2p, d): rules.input_use_level(t1, t2v, t2p, d)
            for t1 in (False, True) for t2v in (False, True) for t2p in (False, True) for d in DISTINCT_CASES}


def test_level_function_is_a_complete_partition():
    """Every combination of T1, T2V, T2P and the distinct-output count has exactly one level (2 x 2 x 2 x 5 = 40
    cases). Coordinator decisions 1 and 2 of 2026-09-24: NONE is total collapse only."""
    seen = _level_table()
    assert len(seen) == 40 and set(seen.values()) == set(rules.LEVELS)
    t3 = lambda d: d >= rules.T3_MIN_DISTINCT                                                  # noqa: E731
    assert {k for k, v in seen.items() if v == "FULL"} == {k for k in seen if k[0] and k[1] and t3(k[3])}
    assert {k for k, v in seen.items() if v == "NONE"} == {(False, False, False, 1)}          # exactly one case
    assert all(v == "TEACHER_FORCED_ONLY" for k, v in seen.items() if (k[0] or k[1]) and not t3(k[3]))
    assert all(v == "PARTIAL_FIELDS" for k, v in seen.items() if t3(k[3]) and k[0] != k[1])
    assert {k for k, v in seen.items() if v == "STRUCTURE_OR_OUTPUT_VARIATION"} == {
        k for k in seen if not k[0] and not k[1] and (k[2] or k[3] >= 2)}
    assert all((v in rules.FIELD_LEVELS) == (k[0] or k[1]) for k, v in seen.items())         # field levels = T1 or T2V
    assert rules.input_use_level(False, False, False, 2) != "NONE"                            # 2 distinct is never NONE
    for bad in (0, -1, 1.0, True, None):
        with pytest.raises(ValueError, match="INVALID_DISTINCT_FREE_OUTPUTS"):
            rules.input_use_level(False, False, False, bad)


def _revision_2_shows_no_input_use(runs):
    """Revision 2's arm rule, for the monotonicity check: runs = [(t1, t2v, t2p, distinct, valid)] with a FINAL
    reading. Revision 2: NONE = not T1, not T2V, not T2P (distinct ignored); >= 2 valid runs, every VALID run NONE."""
    valid = [not (t1 or t2v or t2p) for t1, t2v, t2p, _, ok in runs if ok]
    return len(valid) >= 2 and all(valid)


def test_architecture_rule_can_only_become_rarer_and_always_names_a_reason():
    """Coordinator decision 3 of 2026-09-24, enumerated per arm (3 seeds; each seed: no FINAL reading, or one of 7
    test outcomes, valid or not = 15 states; 15^3 = 3,375 arms) and over all pairs of distinct arms (286 distinct
    multisets of (level, valid)) for the reasons:
      - JUSTIFIED needs every FINAL reading NONE (valid or not) and >= 2 valid NONE runs per arm;
      - an arm that shows no input use under revision 3 also did under revision 2 (so JUSTIFIED only becomes rarer;
        the calibration guard is the same T1/T2V/T2P test in both revisions);
      - every ARCHITECTURE_DECISION_INCOMPLETE carries at least one declared reason;
      - W1 of the verification of 793a4f68: with 1, 2 or 6 FINAL checkpoint files present without a reading, every
        JUSTIFIED pair becomes INCOMPLETE [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING], every other INCOMPLETE gains that
        reason last, NOT_JUSTIFIED and the guard are unchanged;
      - revision 3b, coordinator decision 2 of 2026-09-24 (review of f32b5739): each seed may also be a run whose FINAL
        checkpoint file exists without a reading (16^3 = 4,096 arms). It withholds SHOWS_NO_INPUT_USE (exactly 3 arms
        move to INPUT_USE_UNDETERMINED [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING]); every other arm label is unchanged,
        so no arm label becomes more common. SHOWS_INPUT_USE is not withheld, because such a run cannot make it false:
        the run is never valid, and filling it with every invalid reading keeps SHOWS_INPUT_USE;
      - revision 3b, coordinator decision 1 of 2026-09-24 (X1 of the review of f32b5739): with a checkpoint-0 file
        present without a reading the calibration state is CALIBRATION_UNREADABLE, and every pair, whatever its label
        under a silent or a firing guard, with 0 or 1 unread FINAL files, becomes INCOMPLETE
        [CHECKPOINT0_PRESENT_WITHOUT_READING]: the 9 JUSTIFIED pairs and the 6,171 NOT_JUSTIFIED pairs (per FINAL
        count) move; nothing becomes decisive. So both decisive labels only become rarer."""
    import itertools
    outcomes = ((False, False, False, 1), (False, False, False, 2), (False, False, False, 44), (False, False, True, 1),
                (True, False, False, 1), (False, True, False, 256), (True, True, False, 256))
    states = [None] + [o + (ok,) for o in outcomes for ok in (True, False)]
    arm_cases, new_no = [], 0
    for seeds in itertools.product(states, repeat=3):
        runs = [s for s in seeds if s is not None]
        finals = [(rules.input_use_level(*s[:4]), s[4]) for s in runs]
        label = rules.arm_label("A", finals, 0, rules.CALIBRATION_SILENT)
        shows_no = label == "ARM_A_SHOWS_NO_INPUT_USE"
        want = (all(level == "NONE" for level, _ in finals)
                and sum(1 for level, ok in finals if ok and level == "NONE") >= rules.ARM_MIN_VALID_NONE_RUNS)
        assert shows_no == want, seeds
        if shows_no:
            new_no += 1
            assert _revision_2_shows_no_input_use(runs), seeds             # never JUSTIFIED where revision 2 was not
        arm_cases.append(finals)
    assert len(arm_cases) == 3375 and new_no > 0
    # a revision-2 JUSTIFIED that revision 3 withholds (the verifier's V1, V2 and V3 paths)
    for runs in ([(False, False, False, 44, True)] * 3, [(False, False, False, 14, True)] * 3,
                 [(False, False, False, 1, True)] * 2 + [(True, True, False, 256, False)]):
        assert _revision_2_shows_no_input_use(runs)
        assert rules.arm_label("A", [(rules.input_use_level(*r[:4]), r[4]) for r in runs], 0,
                               rules.CALIBRATION_SILENT) != "ARM_A_SHOWS_NO_INPUT_USE"
    # revision 3b, coordinator decision 2 (review of f32b5739): a run whose FINAL checkpoint file exists without a
    # reading. Revision 3a left it out of the arm label; that is arm_label(..., 0).
    unread_run, withheld = "FINAL_FILE_WITHOUT_READING", ("ARM_A_SHOWS_NO_INPUT_USE", "ARM_A_INPUT_USE_UNDETERMINED")
    invalid_readings = [s for s in states[1:] if not s[4]]
    arm_moves = collections.Counter()
    for seeds in itertools.product(states + [unread_run], repeat=3):
        runs = [s for s in seeds if s is not None and s != unread_run]
        unread = sum(1 for s in seeds if s == unread_run)
        finals = [(rules.input_use_level(*s[:4]), s[4]) for s in runs]
        before = rules.arm_label("A", finals, 0, rules.CALIBRATION_SILENT)
        after, why = rules.arm_decision("A", finals, unread, rules.CALIBRATION_SILENT)
        assert after == rules.arm_label("A", finals, unread, rules.CALIBRATION_SILENT), seeds
        if unread and before == "ARM_A_SHOWS_NO_INPUT_USE":
            assert (after, why) == ("ARM_A_INPUT_USE_UNDETERMINED", ["FINAL_CHECKPOINT_PRESENT_WITHOUT_READING"]), seeds
            # needed: the unread run may have read its input (an invalid FULL reading there breaks "no input use")
            assert rules.arm_label("A", finals + [("FULL", False)] * unread, 0,
                                   rules.CALIBRATION_SILENT) != "ARM_A_SHOWS_NO_INPUT_USE", seeds
        else:
            assert (after, why) == (before, []), seeds
        if unread and before == "ARM_A_SHOWS_INPUT_USE":
            # not needed: whatever the unread run held, it is not valid, and SHOWS_INPUT_USE stays
            for fill in itertools.product(invalid_readings, repeat=unread):
                filled = finals + [(rules.input_use_level(*s[:4]), False) for s in fill]
                assert rules.arm_label("A", filled, 0, rules.CALIBRATION_SILENT) == "ARM_A_SHOWS_INPUT_USE", (seeds, fill)
        arm_moves[(before, after, unread > 0)] += 1
    assert sum(arm_moves.values()) == 16 ** 3
    assert arm_moves[withheld + (True,)] == 3                                 # the only label that moves
    assert all(before == after for (before, after, _), n in arm_moves.items() if (before, after) != withheld)
    assert arm_moves[("ARM_A_SHOWS_INPUT_USE", "ARM_A_SHOWS_INPUT_USE", True)] == 3
    for bad in (-1, 1.0, True, None, "1"):
        with pytest.raises(ValueError, match="INVALID_FINAL_CHECKPOINTS_WITHOUT_READING"):
            rules.arm_decision("A", [], bad, rules.CALIBRATION_SILENT)
    distinct_arms = sorted({tuple(sorted(finals)) for finals in arm_cases})   # the rules ignore seed order
    assert len(distinct_arms) == 286                                          # multisets of size <= 3 over 10 states
    unread_reason = "FINAL_CHECKPOINT_PRESENT_WITHOUT_READING"
    silent, fires, unreadable = rules.CALIBRATION_STATES
    unreadable_result = ("ARCHITECTURE_DECISION_INCOMPLETE", ["CHECKPOINT0_PRESENT_WITHOUT_READING"])
    moved, zero_moves = collections.Counter(), collections.Counter()
    for arm_a in distinct_arms:
        for arm_b in distinct_arms:
            finals_a, finals_b = list(arm_a), list(arm_b)
            label, reasons = rules.architecture_decision({"A": finals_a, "B": finals_b}, silent, 0)
            assert set(reasons) <= set(rules.ARCHITECTURE_REASONS) and unread_reason not in reasons
            assert "CHECKPOINT0_PRESENT_WITHOUT_READING" not in reasons
            if label == "ARCHITECTURE_DECISION_INCOMPLETE":
                assert reasons
            elif label == "ARCHITECTURE_CHANGE_JUSTIFIED":
                assert all(level == "NONE" for level, _ in finals_a + finals_b)
            before = {0: label}
            # verification of 793a4f68, W1: a FINAL checkpoint file without a reading withholds JUSTIFIED, adds its
            # own reason to every other INCOMPLETE, and changes nothing else (only JUSTIFIED becomes rarer)
            for unread in (1, 2, 6):
                label_u, reasons_u = rules.architecture_decision({"A": finals_a, "B": finals_b}, silent, unread)
                if label == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE":
                    assert (label_u, reasons_u) == (label, reasons)
                elif label == "ARCHITECTURE_CHANGE_JUSTIFIED":
                    assert (label_u, reasons_u) == ("ARCHITECTURE_DECISION_INCOMPLETE", [unread_reason])
                else:
                    assert (label_u, reasons_u) == (label, reasons + [unread_reason])
                moved[(label, label_u)] += 1
                before[unread] = label_u
            # revision 3b, coordinator decision 1 (X1): an unreadable checkpoint-0 file withholds both decisive labels
            for unread in (0, 1):
                after = rules.architecture_decision({"A": finals_a, "B": finals_b}, unreadable, unread)
                assert after == unreadable_result
                zero_moves[(before[unread], after[0])] += 1
    assert moved[("ARCHITECTURE_CHANGE_JUSTIFIED", "ARCHITECTURE_DECISION_INCOMPLETE")] == 3 * 9    # 9 JUSTIFIED pairs
    assert not any(after == "ARCHITECTURE_CHANGE_JUSTIFIED" for _, after in moved)
    assert sum(zero_moves.values()) == 2 * 286 ** 2
    assert zero_moves[("ARCHITECTURE_CHANGE_JUSTIFIED", "ARCHITECTURE_DECISION_INCOMPLETE")] == 9
    assert zero_moves[("ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE", "ARCHITECTURE_DECISION_INCOMPLETE")] == 2 * 6171
    assert {after for _, after in zero_moves} == {"ARCHITECTURE_DECISION_INCOMPLETE"}
    for unread in (0, 1):                             # coordinator confirmation (d): the guard's reason stays alone
        assert rules.architecture_decision({"A": [], "B": []}, fires, unread) == (
            "ARCHITECTURE_DECISION_INCOMPLETE", ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"])
        # decision 1: a firing guard over the readable runs gives the same kind of label under the third state
        assert rules.architecture_decision({"A": [], "B": []}, unreadable, unread) == unreadable_result
    for bad in (-1, 1.0, True, None, "1"):
        with pytest.raises(ValueError, match="INVALID_FINAL_CHECKPOINTS_WITHOUT_READING"):
            rules.architecture_decision({"A": [], "B": []}, silent, bad)
    for bad in (False, True, None, 0, "SILENT", silent.lower(), [silent]):     # revision 3a passed a bool here
        with pytest.raises(ValueError, match="INVALID_CALIBRATION_STATE"):
            rules.architecture_decision({"A": [], "B": []}, bad, 0)


def test_calibration_guard_uses_t1_t2v_t2p_only():
    """Coordinator decision 5: the guard stays on T1, T2V and T2P; distinct outputs never fire it."""
    assert not rules.calibration_guard_fires([])
    assert not rules.calibration_guard_fires([(False, False, False)] * 6)
    for tests in ((True, False, False), (False, True, False), (False, False, True)):
        assert rules.calibration_guard_fires([(False, False, False)] * 5 + [tests])
    # revision 3b (X1 of the review of f32b5739; coordinator decision 1 of 2026-09-24): three states. A checkpoint-0 file
    # present without a reading gives CALIBRATION_UNREADABLE first, whatever the readable runs show
    assert rules.CALIBRATION_STATES == ("INPUT_USE_RULE_SILENT_AT_INITIALISATION",
                                        "INPUT_USE_RULE_FIRES_AT_INITIALISATION", "CALIBRATION_UNREADABLE")
    import itertools
    one_run = list(itertools.product((False, True), repeat=3))                       # all 8 (T1, T2V, T2P) outcomes
    for readable in [[]] + [[t] for t in one_run] + [[(False, False, False)] * 5 + [t] for t in one_run]:
        fires = rules.calibration_guard_fires(readable)
        assert rules.calibration_state(readable, 0) == (rules.CALIBRATION_FIRES if fires else rules.CALIBRATION_SILENT)
        for unread in (1, 2, 6):
            assert rules.calibration_state(readable, unread) == rules.CALIBRATION_UNREADABLE
    assert rules.calibration_state(iter([(False, False, True)]), 0) == rules.CALIBRATION_FIRES      # any iterable
    for bad in (-1, 1.0, True, None, "1"):
        with pytest.raises(ValueError, match="INVALID_CHECKPOINT_0_FILES_WITHOUT_READING"):
            rules.calibration_state([], bad)
    assert rules.fields_not_read_in_any_run([]) is False                   # no FINAL reading: nothing to say
    assert rules.fields_not_read_in_any_run(["NONE", "STRUCTURE_OR_OUTPUT_VARIATION"]) is True
    for level in rules.FIELD_LEVELS:
        assert rules.fields_not_read_in_any_run(["NONE"] * 5 + [level]) is False


def test_reader_b_reads_a_does_not(tmp_path, fake_records):
    reads = {("B", s): True for s in rules.SEEDS}
    exact = {("B", s): {"SP1": set(r["id"] for r in fake_records["prep"]["panels"]["SP1"]),
                        "SP2": set(r["id"] for r in fake_records["prep"]["panels"]["SP2"])} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path, fake_records, reads=reads, exact=exact))
    assert v["job"] == "JOB_COMPLETE" and v["stage0"] == "STAGE0_REPRODUCED"
    assert v["arms"]["A"]["label"] == "ARM_A_SHOWS_NO_INPUT_USE" and v["arms"]["B"]["label"] == "ARM_B_SHOWS_INPUT_USE"
    assert v["architecture"] == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE" and v["architecture_reasons"] == []
    assert v["lessons"] == {"SP1": "LESSONS_HELP_SP1", "SP2U": "LESSONS_HELP_SP2U", "SP2ALL": "LESSONS_HELP_SP2ALL"}
    assert v["lessons_overall"] == "LESSONS_OVERALL_HELP"
    assert v["pairs"]["SP2U_PAIR1"]["b_B_exact_A_not"] == 208 and v["calibration"] == "INPUT_USE_RULE_SILENT_AT_INITIALISATION"
    assert all(v["runs"]["%s_%d" % k]["validity"] == "RUN_VALID" for k in rules.RUN_ORDER)


def test_reader_no_arm_reads_input_justifies_the_architecture_change(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path / "all", fake_records))
    assert v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED" and v["architecture_reasons"] == []
    assert v["arms"]["A"]["label"] == "ARM_A_SHOWS_NO_INPUT_USE" and v["arms"]["B"]["label"] == "ARM_B_SHOWS_NO_INPUT_USE"
    assert "FIELDS_NOT_READ_IN_ANY_RUN" in v["labels"] and v["information"]["final_readings_counted"] == 6
    assert v["final_checkpoints_present_without_reading"] == [] and v["information"]["final_checkpoints_present_without_reading"] == []
    assert v["checkpoint_0_distinct_free_outputs"] == {"%s_%d" % k: 1 for k in rules.RUN_ORDER}
    assert set(v["lessons"].values()) == {"LESSONS_EFFECT_NOT_SHOWN_SP1", "LESSONS_EFFECT_NOT_SHOWN_SP2U",
                                          "LESSONS_EFFECT_NOT_SHOWN_SP2ALL"}
    assert v["lessons_overall"] == "LESSONS_OVERALL_EFFECT_NOT_SHOWN"
    v = reader.verdict(write_results(tmp_path / "one_bad", fake_records, reload_bad={("A", S2)}))
    assert v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED"             # 2 valid NONE runs per arm are enough
    # A_S3 never written: a STOPPED job (a COMPLETE job would list it, and it would be expected; revision 3c, Y1)
    v = reader.verdict(write_results(tmp_path / "two_bad", fake_records, reload_bad={("A", S2)}, missing={("A", S3)},
                                     job_status="STOPPED"))
    assert v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED"
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["architecture_reasons"] == ["TOO_FEW_VALID_RUNS"]


def test_reader_architecture_needs_every_valid_run_to_show_no_input_use(tmp_path, fake_records):
    """Review of 3771f989, MAJOR: a model that reads its input only partly, or only with the correct previous
    tokens, must never give ARCHITECTURE_CHANGE_JUSTIFIED."""
    for mode, reason in (("tf_reader_freegen_collapse", "TEACHER_FORCED_ONLY"), ("no_noetic", "PARTIAL_FIELDS"),
                         ("structure_only", "STRUCTURE_OR_OUTPUT_VARIATION"),
                         ("shape_operators_only", "STRUCTURE_OR_OUTPUT_VARIATION"),     # verification V1 (MAJOR)
                         ("shape_only", "STRUCTURE_OR_OUTPUT_VARIATION")):              # verification V2
        v = reader.verdict(write_results(tmp_path / mode, fake_records, modes={k: mode for k in rules.RUN_ORDER}))
        assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["architecture_reasons"] == [reason], mode
        assert "ARCHITECTURE_INCOMPLETE_BECAUSE_" + reason in v["labels"]
        assert v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED"
        assert v["calibration"] == "INPUT_USE_RULE_SILENT_AT_INITIALISATION"
        fields_read = mode in ("tf_reader_freegen_collapse", "no_noetic")
        assert ("FIELDS_NOT_READ_IN_ANY_RUN" in v["labels"]) == (not fields_read), mode
    # verification V3: a fully reading run that is NOT valid (its reload failed) still withholds JUSTIFIED
    v = reader.verdict(write_results(tmp_path / "v3", fake_records, modes={("B", S3): "reader"}, reload_bad={("B", S3)}))
    assert v["runs"]["B_%d" % S3]["validity"] == "RUN_INVALID_RELOAD_MISMATCH"
    assert v["runs"]["B_%d" % S3]["readings"][str(rules.FINAL)]["level"] == "FULL"
    assert v["arms"]["B"]["label"] == "ARM_B_INPUT_USE_UNDETERMINED"
    assert v["arms"]["B"]["final_levels_of_runs_not_valid"] == ["FULL"] and v["arms"]["B"]["valid_none_runs"] == 2
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE"
    assert v["architecture_reasons"] == ["SEED_DEPENDENT", "NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID"]
    assert v["final_checkpoints_present_without_reading"] == []           # its FINAL file was read (W1 is not this)
    assert "FIELDS_NOT_READ_IN_ANY_RUN" not in v["labels"]                 # the invalid run passes T1 and T2V
    # the same with output variation only, in an invalid run
    v = reader.verdict(write_results(tmp_path / "v3s", fake_records, modes={("A", S1): "shape_only"},
                                     reload_bad={("A", S1)}))
    assert v["architecture_reasons"] == ["STRUCTURE_OR_OUTPUT_VARIATION", "NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID"]
    assert "FIELDS_NOT_READ_IN_ANY_RUN" in v["labels"]
    # one fully reading seed per arm (2 of 6 runs): the architecture can carry the input -> never JUSTIFIED
    v = reader.verdict(write_results(tmp_path / "seed", fake_records, reads={("A", S1): True, ("B", S2): True}))
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["architecture_reasons"] == ["SEED_DEPENDENT"]
    # one partial run among five input-blind runs is enough to withhold JUSTIFIED
    v = reader.verdict(write_results(tmp_path / "one", fake_records, modes={("B", S3): "no_noetic"}))
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["architecture_reasons"] == ["PARTIAL_FIELDS"]
    assert v["arms"]["A"]["label"] == "ARM_A_SHOWS_NO_INPUT_USE"
    assert v["final_checkpoints_present_without_reading"] == []


def _rewrite(path, change):
    body = json.loads(path.read_bytes().decode("utf-8"))
    change(body)
    _write(path, body)


def test_reader_final_checkpoint_present_without_reading_withholds_justified(tmp_path, fake_records):
    """Verification of 793a4f68, W1. A run whose FINAL checkpoint FILE exists but gives no FINAL reading cannot be
    counted as NONE: a wrong exact flag on any panel (TEACH_FIT included), a missing run manifest, a wrong identity, or a
    file that holds JSON null. The reader lists it, and the rule withholds ARCHITECTURE_CHANGE_JUSTIFIED with the reason
    FINAL_CHECKPOINT_PRESENT_WITHOUT_READING. The other five runs are input-blind in every case; revision 3 said
    JUSTIFIED for the verifier's three measured cases (sp1_flag, teach_fit_flag, no_manifest).
    Revision 3b (coordinator decision 2 of 2026-09-24 on the review of f32b5739): the arm of such a run has
    SHOWS_NO_INPUT_USE withheld (INPUT_USE_UNDETERMINED, reason FINAL_CHECKPOINT_PRESENT_WITHOUT_READING); an arm with 2
    valid FULL runs keeps SHOWS_INPUT_USE. A missing run manifest also leaves the checkpoint-0 file unread, so that case
    now gives CALIBRATION_UNREADABLE and the one reason CHECKPOINT0_PRESENT_WITHOUT_READING (decision 1)."""
    key, name = ("B", S3), "B_%d" % S3
    final = "checkpoint_%05d.json" % rules.FINAL
    inconsistent_final = "RUN_INVALID_RESULT_INCONSISTENT_AT_%d" % rules.FINAL
    reason = "FINAL_CHECKPOINT_PRESENT_WITHOUT_READING"
    withheld_b = "ARM_B_INPUT_USE_UNDETERMINED_BECAUSE_" + reason

    def flip_teach_fit(k, body):
        if k == key:
            row = body["panels"]["TEACH_FIT"]["rows"][0]
            row["exact"] = 1 - row["exact"]

    cases = (   # name, write_results arguments, a change to B_S3's folder after writing, B_S3's validity
        ("sp1_flag", {"modes": {key: "reader"}, "inconsistent": {key}}, None, inconsistent_final),
        ("teach_fit_flag", {"modes": {key: "reader"}, "mutate_final": flip_teach_fit}, None, inconsistent_final),
        ("no_manifest", {"modes": {key: "reader"}}, lambda f: (f / "run_manifest.json").unlink(), "RUN_INCOMPLETE"),
        ("wrong_identity", {"modes": {key: "reader"}},
         lambda f: _rewrite(f / final, lambda b: b.update(frozen_sha256="0" * 64)), inconsistent_final),
        ("json_null", {"modes": {key: "reader"}}, lambda f: (f / final).write_bytes(b"null\n"), "RUN_INCOMPLETE"),
        ("blind_run_flag", {"inconsistent": {key}}, None, inconsistent_final),       # what the file held is unknown
    )
    for case, kwargs, change, validity in cases:
        root = write_results(tmp_path / case, fake_records, **kwargs)
        if change:
            change(root / "runs" / name)
        v = reader.verdict(root)
        run = v["runs"][name]
        assert run["validity"] == validity and str(rules.FINAL) not in run["readings"], case
        assert run["final_checkpoint_file_present"] and run["final_checkpoint_present_without_reading"], case
        assert v["final_checkpoints_present_without_reading"] == [name], case
        assert (v["arms"]["A"]["final_checkpoints_present_without_reading"],
                v["arms"]["B"]["final_checkpoints_present_without_reading"]) == ([], [name]), case
        if case == "no_manifest":         # no manifest: checkpoint 0 unread too; the calibration reason stands alone
            assert v["calibration"] == "CALIBRATION_UNREADABLE", case
            assert v["checkpoint_0_files_present_without_reading"] == [name], case
            assert v["architecture_reasons"] == ["CHECKPOINT0_PRESENT_WITHOUT_READING"], case
        else:
            assert v["calibration"] == rules.CALIBRATION_SILENT, case
            assert v["checkpoint_0_files_present_without_reading"] == [], case
            assert v["architecture_reasons"] == [reason], case
            assert "ARCHITECTURE_INCOMPLETE_BECAUSE_" + reason in v["labels"], case
        assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE", case
        if case == "no_manifest":         # revision 3c, N1: a state that is not silent withholds both arm labels
            for arm in rules.ARMS:
                assert (v["arms"][arm]["label"], v["arms"][arm]["label_reasons"]) == (
                    "ARM_%s_INPUT_USE_UNDETERMINED" % arm, ["CHECKPOINT0_PRESENT_WITHOUT_READING"]), case
        else:
            # revision 3b, coordinator decision 2: B's SHOWS_NO_INPUT_USE is withheld, with the reason; A is unchanged
            assert (v["arms"]["A"]["label"], v["arms"]["A"]["label_reasons"]) == ("ARM_A_SHOWS_NO_INPUT_USE", []), case
            assert (v["arms"]["B"]["label"], v["arms"]["B"]["label_reasons"]) == ("ARM_B_INPUT_USE_UNDETERMINED",
                                                                                  [reason]), case
            assert withheld_b in v["labels"], case
        assert "ARM_B_SHOWS_NO_INPUT_USE" not in v["labels"], case
        assert run["validity"] != "RUN_VALID", case                     # such a run is never valid
        # coordinator confirmation (c): the information label speaks about the 5 runs with a reading; scope stated
        assert "FIELDS_NOT_READ_IN_ANY_RUN" in v["labels"] and v["information"]["final_readings_counted"] == 5, case
        assert v["information"]["final_checkpoints_present_without_reading"] == [name], case
    # revision 3c (Y1): a FINAL file that is absent but expected is flagged too; see
    # test_reader_expected_but_absent_file_is_flagged_like_an_unread_one (revision 3b left it out here)
    # only JUSTIFIED becomes rarer: two valid FULL runs in arm A still give NOT_JUSTIFIED, with no reason
    v = reader.verdict(write_results(tmp_path / "not_justified", fake_records,
                                     reads={("A", S1): True, ("A", S2): True}, inconsistent={key}))
    assert v["final_checkpoints_present_without_reading"] == [name]
    assert v["architecture"] == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE" and v["architecture_reasons"] == []
    assert v["arms"]["B"]["label"] == "ARM_B_INPUT_USE_UNDETERMINED" and withheld_b in v["labels"]
    # revision 3b: SHOWS_INPUT_USE is not withheld when the unread FINAL file is in the same arm (2 valid FULL runs
    # stand; the unread run is not valid, so it cannot undo them); NOT_JUSTIFIED is unchanged
    v = reader.verdict(write_results(tmp_path / "same_arm", fake_records,
                                     reads={("A", S1): True, ("A", S2): True}, inconsistent={("A", S3)}))
    assert v["arms"]["A"]["final_checkpoints_present_without_reading"] == ["A_%d" % S3]
    assert (v["arms"]["A"]["label"], v["arms"]["A"]["label_reasons"]) == ("ARM_A_SHOWS_INPUT_USE", [])
    assert v["architecture"] == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE" and v["architecture_reasons"] == []
    assert not any("_BECAUSE_" in label and label.startswith("ARM_") for label in v["labels"])
    # coordinator confirmation (d): when the guard fires, it stays the only reason (for the arms too: revision 3c, N1)
    v = reader.verdict(write_results(tmp_path / "guard", fake_records, fires_at_zero=True, inconsistent={key}))
    assert v["final_checkpoints_present_without_reading"] == [name]
    assert v["architecture_reasons"] == ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"]
    assert v["arms"]["B"]["label_reasons"] == ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"]
    # two flagged runs (run order), next to another reason: the new reason is added last
    v = reader.verdict(write_results(tmp_path / "two", fake_records, modes={("A", S1): "shape_only"},
                                     inconsistent={("A", S2), key}))
    assert v["final_checkpoints_present_without_reading"] == ["A_%d" % S2, name]
    assert v["architecture_reasons"] == ["STRUCTURE_OR_OUTPUT_VARIATION", reason]
    # unchanged: a FINAL file that holds neither a JSON object nor null stops the whole reader (no verdict, no label)
    root = write_results(tmp_path / "unparsable", fake_records)
    first = root / "runs" / ("A_%d" % S1) / final
    for body in (b"{\n", b'{"a": 1, "a": 2}\n', b'{"a": NaN}\n', b"[]\n"):
        first.write_bytes(body)
        with pytest.raises((ValueError, AttributeError)):                # ReadError is a ValueError
            reader.verdict(root)


def test_reader_checkpoint_0_present_without_reading_makes_calibration_unreadable(tmp_path, fake_records):
    """Review of f32b5739, X1; coordinator decision 1 of 2026-09-24. A run whose checkpoint-0 FILE exists but gives no
    checkpoint-0 reading was left out of the calibration guard, which still printed SILENT. Now the reader lists it, the
    calibration state is CALIBRATION_UNREADABLE (whatever the readable runs show), and the architecture label is
    ARCHITECTURE_DECISION_INCOMPLETE with the one reason CHECKPOINT0_PRESENT_WITHOUT_READING. The reviewer's cases G0-G3:
    pair 3 (A and B on the third seed) is structure_only at checkpoint 0, so T2P passes there; every FINAL reading is
    input-blind unless stated; 'unread' = one SP1 exact flag flipped in that run's checkpoint_00000.json."""
    pair3 = {("A", S3): "structure_only", ("B", S3): "structure_only"}
    reason = "CHECKPOINT0_PRESENT_WITHOUT_READING"
    a3, b3 = "A_%d" % S3, "B_%d" % S3
    at_zero = "RUN_INVALID_RESULT_INCONSISTENT_AT_0"
    zero = "checkpoint_%05d.json" % 0
    # G0 (control, unchanged from revision 3a): both pair-3 checkpoint-0 files readable, so the guard fires
    v = reader.verdict(write_results(tmp_path / "g0", fake_records, zero_modes=pair3))
    assert v["calibration"] == rules.CALIBRATION_FIRES and v["checkpoint_0_files_present_without_reading"] == []
    assert v["architecture_reasons"] == ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"]
    # G1: both pair-3 checkpoint-0 files unread. Revision 3a printed SILENT and ARCHITECTURE_CHANGE_JUSTIFIED
    v = reader.verdict(write_results(tmp_path / "g1", fake_records, zero_modes=pair3, inconsistent_zero=set(pair3)))
    assert (v["runs"][a3]["validity"], v["runs"][b3]["validity"]) == (at_zero, at_zero)
    assert v["runs"][a3]["checkpoint_0_file_present"] and v["runs"][a3]["checkpoint_0_present_without_reading"]
    assert v["calibration"] == "CALIBRATION_UNREADABLE" and v["checkpoint_0_files_present_without_reading"] == [a3, b3]
    assert v["calibration_guard_fires_over_readable_runs"] is False
    assert v["calibration_checkpoint_0"][a3] is None and v["checkpoint_0_distinct_free_outputs"][b3] is None
    assert (v["architecture"], v["architecture_reasons"]) == ("ARCHITECTURE_DECISION_INCOMPLETE", [reason])
    assert "CALIBRATION_UNREADABLE" in v["labels"] and "ARCHITECTURE_INCOMPLETE_BECAUSE_" + reason in v["labels"]
    assert not {rules.CALIBRATION_SILENT, rules.CALIBRATION_FIRES, "ARCHITECTURE_CHANGE_JUSTIFIED"} & set(v["labels"])
    # pair 3's FINAL files were read; revision 3c (N1): the state is not silent, so both arm labels are withheld
    assert v["final_checkpoints_present_without_reading"] == []
    assert (v["arms"]["A"]["label"], v["arms"]["A"]["label_reasons"]) == ("ARM_A_INPUT_USE_UNDETERMINED", [reason])
    # G2: only A_S3's checkpoint-0 file unread; B_S3 (the same starting tensors) passes T2P at checkpoint 0. Revision 3a:
    # FIRES. Decision 1: the third state comes first, whatever the readable runs show; the firing is still reported
    v = reader.verdict(write_results(tmp_path / "g2", fake_records, zero_modes=pair3, inconsistent_zero={("A", S3)}))
    assert v["calibration"] == "CALIBRATION_UNREADABLE" and v["calibration_guard_fires_over_readable_runs"] is True
    assert v["checkpoint_0_files_present_without_reading"] == [a3] and v["architecture_reasons"] == [reason]
    assert v["calibration_checkpoint_0"][b3]["T2P"] is True and v["runs"][b3]["validity"] == "RUN_VALID"
    # G3: as G1, and arm A reads fully in its 2 valid runs. Revision 3a printed SILENT and NOT_JUSTIFIED
    v = reader.verdict(write_results(tmp_path / "g3", fake_records, zero_modes=pair3, inconsistent_zero=set(pair3),
                                     reads={("A", S1): True, ("A", S2): True}))
    assert v["calibration"] == "CALIBRATION_UNREADABLE" and v["arms"]["A"]["valid_runs"] == 2
    assert v["arms"]["A"]["full_runs"] == 2 and v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED"  # N1 (3c)
    assert (v["architecture"], v["architecture_reasons"]) == ("ARCHITECTURE_DECISION_INCOMPLETE", [reason])
    assert "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE" not in v["labels"]
    # the other ways a checkpoint-0 file gives no reading, each in B_S3 alone; all FINAL readings input-blind
    for case, change, validity in (
            ("wrong_identity", lambda f: _rewrite(f / zero, lambda b: b.update(frozen_sha256="0" * 64)), at_zero),
            ("wrong_checkpoint", lambda f: _rewrite(f / zero, lambda b: b.update(checkpoint=128)), at_zero),
            ("json_null", lambda f: (f / zero).write_bytes(b"null\n"), "RUN_INCOMPLETE"),
            ("no_manifest", lambda f: (f / "run_manifest.json").unlink(), "RUN_INCOMPLETE")):
        root = write_results(tmp_path / case, fake_records)
        change(root / "runs" / b3)
        v = reader.verdict(root)
        assert v["runs"][b3]["validity"] == validity and v["runs"][b3]["checkpoint_0_present_without_reading"], case
        assert v["calibration"] == "CALIBRATION_UNREADABLE", case
        assert v["checkpoint_0_files_present_without_reading"] == [b3], case
        assert v["architecture_reasons"] == [reason], case           # it stands alone, as the guard's reason does
        # a missing manifest leaves the FINAL file unread too (decision 2); revision 3c (N1): under this state both
        # arm labels are withheld in every case, with the calibration reason alone
        assert (v["final_checkpoints_present_without_reading"] == [b3]) == (case == "no_manifest"), case
        assert (v["arms"]["B"]["label"], v["arms"]["B"]["label_reasons"]) == ("ARM_B_INPUT_USE_UNDETERMINED",
                                                                              [reason]), case
    # revision 3c (Y1): a checkpoint-0 file that is absent but expected is flagged too (revision 3b left it out); see
    # test_reader_expected_but_absent_file_is_flagged_like_an_unread_one
    # unchanged: a checkpoint-0 file that holds neither a JSON object nor null stops the whole reader (no label)
    root = write_results(tmp_path / "unparsable", fake_records)
    for body in (b"{\n", b"[]\n"):
        (root / "runs" / b3 / zero).write_bytes(body)
        with pytest.raises((ValueError, AttributeError)):                # ReadError is a ValueError
            reader.verdict(root)


def test_reader_expected_but_absent_file_is_flagged_like_an_unread_one(tmp_path, fake_records):
    """Revision 3c: Y1 of the review of c0b2faad, coordinator decision 1 of the queue of 2026-09-24. A result file is
    EXPECTED when the run's own later files prove it was written: the FINAL file when run_result.json or
    reload_check.json exists; the checkpoint-0 file when any later checkpoint, run_result.json or reload_check.json
    exists; every file of a run that a COMPLETE job_result.json lists. An expected file that is absent gets the same flag
    as a present file without a reading. The reviewer's three measured cases gave ARCHITECTURE_CHANGE_JUSTIFIED under
    revision 3b; none does now. A run that a STOPPED job never finished is still left out, as before."""
    import itertools
    import shutil
    pair3 = {("A", S3): "structure_only", ("B", S3): "structure_only"}
    a3, b3 = "A_%d" % S3, "B_%d" % S3
    zero, final = "checkpoint_%05d.json" % 0, "checkpoint_%05d.json" % rules.FINAL
    c0, fin = "CHECKPOINT0_PRESENT_WITHOUT_READING", "FINAL_CHECKPOINT_PRESENT_WITHOUT_READING"
    six = ["%s_%d" % k for k in rules.RUN_ORDER]
    # the rule itself, over every combination of the three kinds of evidence
    for later, after, listed in itertools.product((False, True), repeat=3):
        assert rules.expected_files(later, after, listed) == (later or after or listed, after or listed)
    for bad in (0, 1, None, "True"):
        with pytest.raises(ValueError, match="INVALID_EXPECTED_FILE_EVIDENCE"):
            rules.expected_files(bad, False, False)
    # case 1 (the review's zero_absent): both pair-3 starting files deleted; pair 3 passes T2P at checkpoint 0.
    # Revision 3b: SILENT and JUSTIFIED. Their later checkpoints, run_result.json and reload_check.json prove them
    root = write_results(tmp_path / "zero_absent", fake_records, zero_modes=pair3)
    (root / "runs" / a3 / zero).unlink()
    (root / "runs" / b3 / zero).unlink()
    v = reader.verdict(root)
    run = v["runs"][a3]
    assert not run["checkpoint_0_file_present"] and run["checkpoint_0_file_expected"]
    assert run["checkpoint_0_present_without_reading"] and run["validity"] == "RUN_INCOMPLETE"
    assert v["checkpoint_0_files_present_without_reading"] == [a3, b3]
    assert v["expected_files_absent_report_only"] == {"checkpoint_0": [a3, b3], "final": []}
    assert v["calibration"] == "CALIBRATION_UNREADABLE"
    assert (v["architecture"], v["architecture_reasons"]) == ("ARCHITECTURE_DECISION_INCOMPLETE", [c0])
    # case 2 (the review's final_absent): B_S3 reads fully; its FINAL file deleted. Revision 3b: JUSTIFIED and
    # ARM_B_SHOWS_NO_INPUT_USE. run_result.json and reload_check.json prove it was written
    root = write_results(tmp_path / "final_absent", fake_records, modes={("B", S3): "reader"})
    (root / "runs" / b3 / final).unlink()
    v = reader.verdict(root)
    run = v["runs"][b3]
    assert not run["final_checkpoint_file_present"] and run["final_checkpoint_file_expected"]
    assert run["final_checkpoint_present_without_reading"] and not run["checkpoint_0_present_without_reading"]
    assert v["final_checkpoints_present_without_reading"] == [b3] and v["calibration"] == rules.CALIBRATION_SILENT
    assert v["expected_files_absent_report_only"] == {"checkpoint_0": [], "final": [b3]}
    assert (v["architecture"], v["architecture_reasons"]) == ("ARCHITECTURE_DECISION_INCOMPLETE", [fin])
    assert (v["arms"]["B"]["label"], v["arms"]["B"]["label_reasons"]) == ("ARM_B_INPUT_USE_UNDETERMINED", [fin])
    assert v["arms"]["A"]["label"] == "ARM_A_SHOWS_NO_INPUT_USE"
    # case 3 (the review's own): B_S3 reads fully; its whole run folder deleted; the COMPLETE job_result.json lists
    # all six runs. Revision 3b: JUSTIFIED and ARM_B_SHOWS_NO_INPUT_USE
    root = write_results(tmp_path / "folder_absent", fake_records, modes={("B", S3): "reader"})
    shutil.rmtree(root / "runs" / b3)
    v = reader.verdict(root)
    assert v["runs_listed_by_complete_job"] == six and v["runs"][b3]["listed_by_complete_job"]
    assert v["runs"][b3]["validity"] == "RUN_INCOMPLETE"
    assert v["checkpoint_0_files_present_without_reading"] == [b3] == v["final_checkpoints_present_without_reading"]
    assert v["calibration"] == "CALIBRATION_UNREADABLE" and v["architecture_reasons"] == [c0]
    assert "ARCHITECTURE_CHANGE_JUSTIFIED" not in v["labels"] and "ARM_B_SHOWS_NO_INPUT_USE" not in v["labels"]
    # the same with a COMPLETE record that carries no run list: fail closed, all six runs are expected
    _rewrite(root / "job_result.json", lambda body: body.pop("runs"))
    v = reader.verdict(root)
    assert v["runs_listed_by_complete_job"] == six and v["architecture_reasons"] == [c0]
    # each of the two later files alone is enough to expect the FINAL file (a STOPPED job lists no run)
    for keep in ("run_result.json", "reload_check.json"):
        root = write_results(tmp_path / ("only_" + keep[:-5]), fake_records, modes={("B", S3): "reader"},
                             job_status="STOPPED")
        folder = root / "runs" / b3
        (folder / final).unlink()
        for other in {"run_result.json", "reload_check.json"} - {keep}:
            (folder / other).unlink()
        v = reader.verdict(root)
        assert v["runs_listed_by_complete_job"] == [] and v["final_checkpoints_present_without_reading"] == [b3], keep
        assert v["architecture_reasons"] == [fin] and v["arms"]["B"]["label_reasons"] == [fin], keep
    # the difference the fix keeps: a run that never finished (a STOPPED job; no FINAL file, no run_result.json, no
    # reload_check.json) is left out as before, and 2 valid NONE runs per arm still give JUSTIFIED
    root = write_results(tmp_path / "unfinished", fake_records, modes={("B", S3): "reader"}, job_status="STOPPED")
    for name in (final, "run_result.json", "reload_check.json"):
        (root / "runs" / b3 / name).unlink()
    v = reader.verdict(root)
    run = v["runs"][b3]
    assert not run["final_checkpoint_file_expected"] and run["checkpoint_0_file_expected"]    # later checkpoints exist
    assert not run["final_checkpoint_present_without_reading"] and not run["checkpoint_0_present_without_reading"]
    assert v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED"
    # and a run folder that a STOPPED job never wrote is not expected either
    v = reader.verdict(write_results(tmp_path / "never_written", fake_records, missing={("B", S3)}, job_status="STOPPED"))
    assert v["checkpoint_0_files_present_without_reading"] == [] == v["final_checkpoints_present_without_reading"]
    assert v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED"


def test_reader_final_reading_without_a_starting_file_is_flagged(tmp_path, fake_records):
    """Revision 3c: the builder's open question on an absent checkpoint-0 file, coordinator decision 6 of the queue of
    2026-09-24 ("same fail-closed shape"). A run that has a FINAL reading but no checkpoint-0 file is flagged, whatever
    else is in its folder: its FINAL file is a later checkpoint, so its starting file is expected."""
    a1, zero = "A_%d" % S1, "checkpoint_%05d.json" % 0
    reasons = ("ARCHITECTURE_DECISION_INCOMPLETE", ["CHECKPOINT0_PRESENT_WITHOUT_READING"])
    # only the starting file is missing (COMPLETE job; run_result.json and reload_check.json present)
    root = write_results(tmp_path / "bare", fake_records)
    (root / "runs" / a1 / zero).unlink()
    v = reader.verdict(root)
    assert str(rules.FINAL) in v["runs"][a1]["readings"] and v["runs"][a1]["checkpoint_0_present_without_reading"]
    assert v["checkpoint_0_files_present_without_reading"] == [a1] and v["calibration"] == "CALIBRATION_UNREADABLE"
    assert (v["architecture"], v["architecture_reasons"]) == reasons
    # the FINAL reading alone is enough: a STOPPED job (it lists no run), no run_result.json, no reload_check.json, and
    # no checkpoint file but the FINAL one. Revision 3b: the run was left out of the guard, and JUSTIFIED followed
    root = write_results(tmp_path / "final_only", fake_records, job_status="STOPPED")
    folder = root / "runs" / a1
    for point in rules.CHECKPOINTS[:-1]:
        (folder / ("checkpoint_%05d.json" % point)).unlink()
    for name in ("run_result.json", "reload_check.json"):
        (folder / name).unlink()
    v = reader.verdict(root)
    run = v["runs"][a1]
    assert set(run["readings"]) == {str(rules.FINAL)} and run["validity"] == "RUN_INCOMPLETE"
    assert not run["final_checkpoint_file_expected"] and run["checkpoint_0_file_expected"]
    assert v["checkpoint_0_files_present_without_reading"] == [a1] and v["calibration"] == "CALIBRATION_UNREADABLE"
    assert (v["architecture"], v["architecture_reasons"]) == reasons
    assert "ARCHITECTURE_CHANGE_JUSTIFIED" not in v["labels"]


def test_arm_labels_are_withheld_when_calibration_is_not_silent(tmp_path, fake_records):
    """Revision 3c: N1 of the review of c0b2faad, coordinator decision 2 of the queue of 2026-09-24. Whenever the
    calibration state is not SILENT (INPUT_USE_RULE_FIRES_AT_INITIALISATION or CALIBRATION_UNREADABLE), every arm label
    is withheld with a named reason: INPUT_USE_UNDETERMINED, with the calibration reason alone (the same shape as the
    architecture label). Under SILENT the arm rule is revision 3b's (the enumeration test above)."""
    import itertools
    outcomes = ((False, False, False, 1), (False, False, False, 2), (False, False, False, 44), (False, False, True, 1),
                (True, False, False, 1), (False, True, False, 256), (True, True, False, 256))
    unread_run = "FINAL_FILE_WITHOUT_READING"
    states = [None] + [o + (ok,) for o in outcomes for ok in (True, False)] + [unread_run]
    silent, fires, unreadable = rules.CALIBRATION_STATES
    assert rules.CALIBRATION_REASON == {fires: "INPUT_USE_RULE_FIRES_AT_INITIALISATION",
                                        unreadable: "CHECKPOINT0_PRESENT_WITHOUT_READING"}
    withheld = collections.Counter()
    for seeds in itertools.product(states, repeat=3):
        runs = [s for s in seeds if isinstance(s, tuple)]
        finals = [(rules.input_use_level(*s[:4]), s[4]) for s in runs]
        unread = seeds.count(unread_run)
        under_silent = rules.arm_label("A", finals, unread, silent)
        for state in (fires, unreadable):
            assert rules.arm_decision("A", finals, unread, state) == (
                "ARM_A_INPUT_USE_UNDETERMINED", [rules.CALIBRATION_REASON[state]]), (seeds, state)
            withheld[under_silent] += 1
    assert sum(withheld.values()) == 2 * 16 ** 3
    assert withheld["ARM_A_SHOWS_INPUT_USE"] > 0 and withheld["ARM_A_SHOWS_NO_INPUT_USE"] > 0   # both withheld now
    for bad in (False, True, None, 0, "SILENT", silent.lower(), [silent]):
        with pytest.raises(ValueError, match="INVALID_CALIBRATION_STATE"):
            rules.arm_decision("A", [], 0, bad)
    # the reader, a firing guard: arm A reads fully in 2 valid runs (revision 3b printed ARM_A_SHOWS_INPUT_USE)
    v = reader.verdict(write_results(tmp_path / "fires", fake_records, reads={("A", S1): True, ("A", S2): True},
                                     fires_at_zero=True))
    assert v["calibration"] == fires and v["arms"]["A"]["full_runs"] == 2
    # the reader, CALIBRATION_UNREADABLE: arm B is input-blind in 3 valid runs (revision 3b: ARM_B_SHOWS_NO_INPUT_USE)
    w = reader.verdict(write_results(tmp_path / "unreadable", fake_records, inconsistent_zero={("A", S3)}))
    assert w["calibration"] == unreadable and w["arms"]["B"]["valid_none_runs"] == 3
    for verdict, state in ((v, fires), (w, unreadable)):
        reason = rules.CALIBRATION_REASON[state]
        for arm in rules.ARMS:
            assert (verdict["arms"][arm]["label"], verdict["arms"][arm]["label_reasons"]) == (
                "ARM_%s_INPUT_USE_UNDETERMINED" % arm, [reason]), (state, arm)
            assert "ARM_%s_INPUT_USE_UNDETERMINED_BECAUSE_%s" % (arm, reason) in verdict["labels"]
        assert not any(label.startswith("ARM_") and "_SHOWS_" in label for label in verdict["labels"]), state
        assert (verdict["architecture"], verdict["architecture_reasons"]) == ("ARCHITECTURE_DECISION_INCOMPLETE", [reason])


def test_spec_states_the_reading_of_decision_2_as_confirmed():
    """Revision 3c: N2 of the review of c0b2faad, coordinator decision 3 of the queue of 2026-09-24. Decision 2
    withholds only SHOWS_NO_INPUT_USE; the builder's reading is confirmed, so the spec's arm section says "confirmed"
    and carries no open question about a rule it freezes."""
    spec = (HERE / "Q4_SDG_AB_SPEC_v0_2.md").read_text(encoding="utf-8")
    arms = " ".join(spec[spec.index("### 7.3 Arms"):spec.index("### 7.4 Calibration guard")].split())
    assert "open question" not in arms
    assert "confirmed by the coordinator on 2026-09-24" in arms and "SHOWS_INPUT_USE is not withheld" in arms
    assert "reading confirmed 2026-09-24" in rules.frozen_record()["rules"]["ARM"]


def test_reader_run_identity_must_match_the_folder_and_prep(tmp_path, fake_records):
    """Revision 3c: N3 of the review of c0b2faad, coordinator decision 4 of the queue of 2026-09-24. The run manifest's
    arm, seed and pool_ids_digest must match the run folder's name and prep.json, or the run fails closed: no reading at
    all (RUN_INVALID_RUN_IDENTITY_DIFFERS), its present or expected files flagged, its pairs incomplete."""
    b3, c0 = "B_%d" % S3, "CHECKPOINT0_PRESENT_WITHOUT_READING"
    # the runner's digest (q4_ab_prep.ids_digest, frozen for arm A as A_POOL_DIGEST) is what the reader recomputes
    assert rules.sha(rules.canonical(fake_records["prep"]["pools"]["A"]["ids"])) == rules.A_POOL_DIGEST
    cases = (("arm", lambda b: b.update(arm="A"), "ARM"), ("seed", lambda b: b.update(seed=S1), "SEED"),
             ("seed_float", lambda b: b.update(seed=float(S3)), "SEED"), ("no_seed", lambda b: b.pop("seed"), "SEED"),
             ("digest", lambda b: b.update(pool_ids_digest="0" * 64), "POOL_IDS_DIGEST"),
             ("digest_of_a", lambda b: b.update(pool_ids_digest=rules.A_POOL_DIGEST), "POOL_IDS_DIGEST"),
             ("no_digest", lambda b: b.pop("pool_ids_digest"), "POOL_IDS_DIGEST"))
    for case, change, problem in cases:
        root = write_results(tmp_path / case, fake_records, modes={("B", S3): "reader"})
        _rewrite(root / "runs" / b3 / "run_manifest.json", change)
        v = reader.verdict(root)
        run = v["runs"][b3]
        assert run["validity"] == "RUN_INVALID_RUN_IDENTITY_DIFFERS" and run["readings"] == {}, case
        assert run["problems"] == ["RUN_IDENTITY_DIFFERS (%s)" % problem], case
        assert run["checkpoint_0_present_without_reading"] and run["final_checkpoint_present_without_reading"], case
        assert v["calibration"] == "CALIBRATION_UNREADABLE" and v["architecture_reasons"] == [c0], case
        assert v["pairs"]["SP1_PAIR3"]["outcome"] == "PAIR_INCOMPLETE", case
        assert "%s:RUN_INVALID_RUN_IDENTITY_DIFFERS" % b3 in v["labels"], case
    # the review's swap: the A and B folders of every seed exchanged; B is exact on 10 SP1 rows in every seed
    sp1 = [r["id"] for r in fake_records["prep"]["panels"]["SP1"]]
    root = write_results(tmp_path / "swap", fake_records, exact={("B", s): {"SP1": set(sp1[:10])} for s in rules.SEEDS})
    assert reader.verdict(root)["lessons"]["SP1"] == "LESSONS_HELP_SP1"                 # control: before the swap
    runs = root / "runs"
    for seed in rules.SEEDS:
        (runs / ("A_%d" % seed)).rename(runs / "swap")
        (runs / ("B_%d" % seed)).rename(runs / ("A_%d" % seed))
        (runs / "swap").rename(runs / ("B_%d" % seed))
    v = reader.verdict(root)
    assert {run["validity"] for run in v["runs"].values()} == {"RUN_INVALID_RUN_IDENTITY_DIFFERS"}
    assert v["lessons"]["SP1"] == "LESSONS_COMPARISON_INCOMPLETE_SP1" and "LESSONS_HURT_SP1" not in v["labels"]
    assert v["lessons_overall"] == "LESSONS_OVERALL_COMPARISON_INCOMPLETE" and v["architecture_reasons"] == [c0]
    with pytest.MonkeyPatch.context() as m:               # without the check, every pair flips (what the review found)
        m.setattr(reader, "run_identity_problems", lambda *args: [])
        assert reader.verdict(root)["lessons"]["SP1"] == "LESSONS_HURT_SP1"
    # prep.json without arm B's pool ids (every other prep check passes): every B run fails closed
    v = reader.verdict(write_results(tmp_path / "no_b_ids", fake_records, mutate_prep=lambda r: r["pools"]["B"].pop("ids")))
    assert "no_verdict" not in v and v["calibration"] == "CALIBRATION_UNREADABLE"
    assert [v["runs"]["%s_%d" % (arm, s)]["validity"] for arm in rules.ARMS for s in rules.SEEDS] == (
        ["RUN_VALID"] * 3 + ["RUN_INVALID_RUN_IDENTITY_DIFFERS"] * 3)


def test_reader_calibration_guard_and_checkpoint_0_counts(tmp_path, fake_records):
    """Coordinator decision 5 of 2026-09-24: the guard stays on T1, T2V and T2P; every run's checkpoint-0 distinct
    free-output count is reported. An untrained model whose outputs vary does not fire the guard."""
    everyone = {k: "shape_operators_only" for k in rules.RUN_ORDER}
    v = reader.verdict(write_results(tmp_path / "vary", fake_records, zero_modes=everyone))
    assert v["calibration"] == "INPUT_USE_RULE_SILENT_AT_INITIALISATION"
    assert v["checkpoint_0_distinct_free_outputs"] == {"%s_%d" % k: 44 for k in rules.RUN_ORDER}
    first = v["calibration_checkpoint_0"]["A_%d" % S1]
    assert first == {"T1": False, "T2V": False, "T2P": False, "distinct_free_outputs": 44,
                     "level": "STRUCTURE_OR_OUTPUT_VARIATION"}
    assert v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED"             # FINAL readings are all NONE here
    v = reader.verdict(write_results(tmp_path / "t2p", fake_records, zero_modes={k: "structure_only" for k in rules.RUN_ORDER}))
    assert v["calibration"] == "INPUT_USE_RULE_FIRES_AT_INITIALISATION"      # T2P passes at checkpoint 0
    assert v["architecture_reasons"] == ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"]
    assert v["checkpoint_0_distinct_free_outputs"]["B_%d" % S3] == 180
    v = reader.verdict(write_results(tmp_path / "gap", fake_records, missing={("A", S2)}, job_status="STOPPED"))
    assert v["checkpoint_0_distinct_free_outputs"]["A_%d" % S2] is None and len(v["checkpoint_0_distinct_free_outputs"]) == 6
    # a run the stopped job never wrote: no file of it exists or is expected, so nothing is flagged (revision 3c, Y1)
    assert v["checkpoint_0_files_present_without_reading"] == [] and v["calibration"] == rules.CALIBRATION_SILENT


def test_reader_two_of_three_seeds_are_enough_and_one_is_not(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path / "two", fake_records, reads={("A", S1): True, ("A", S3): True}))
    assert v["arms"]["A"]["label"] == "ARM_A_SHOWS_INPUT_USE"
    assert v["architecture"] == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE"
    v = reader.verdict(write_results(tmp_path / "one", fake_records, reads={("A", S1): True}))
    assert v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED"
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["architecture_reasons"] == ["SEED_DEPENDENT"]
    v = reader.verdict(write_results(tmp_path / "gap", fake_records, reads={("A", S1): True}, missing={("A", S3)},
                                     job_status="STOPPED"))
    assert v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED"
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["runs"]["A_%d" % S3]["validity"] == "RUN_INCOMPLETE"
    assert v["architecture_reasons"] == ["SEED_DEPENDENT"]
    assert v["lessons"]["SP1"] == "LESSONS_COMPARISON_INCOMPLETE_SP1"
    assert v["lessons_overall"] == "LESSONS_OVERALL_COMPARISON_INCOMPLETE"


def test_reader_lessons_need_all_three_pairs_and_the_sign_test(tmp_path, fake_records):
    sp1 = [r["id"] for r in fake_records["prep"]["panels"]["SP1"]]
    exact = {("B", S1): {"SP1": set(sp1[:7])}, ("B", S2): {"SP1": set(sp1[:7])}, ("B", S3): {"SP1": set(sp1[:6])}}
    v = reader.verdict(write_results(tmp_path / "a", fake_records, exact=exact))
    assert [v["pairs"]["SP1_PAIR%d" % i]["outcome"] for i in (1, 2, 3)] == ["B_BEATS_A", "B_BEATS_A", "NO_PAIRED_DIFFERENCE"]
    assert v["pairs"]["SP1_PAIR3"]["p_B_beats_A"] == 1 / 64 and v["lessons"]["SP1"] == "LESSONS_EFFECT_NOT_SHOWN_SP1"
    exact = {("A", s): {"SP1": set(sp1[:10])} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path / "b", fake_records, exact=exact))
    assert v["lessons"]["SP1"] == "LESSONS_HURT_SP1" and v["lessons_overall"] == "LESSONS_OVERALL_HURT"


def test_reader_one_overall_lessons_answer(tmp_path, fake_records):
    """Review MINOR 2: one program-emitted answer over the primary panels SP1 and SP2U."""
    sp1 = [r["id"] for r in fake_records["prep"]["panels"]["SP1"]]
    sp2u = [r["id"] for r in fake_records["prep"]["panels"]["SP2"] if not r["inspected"]]
    exact = {("B", s): {"SP1": set(sp1[:10])} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path / "sp1_only", fake_records, exact=exact))
    assert v["lessons"]["SP1"] == "LESSONS_HELP_SP1" and v["lessons"]["SP2U"] == "LESSONS_EFFECT_NOT_SHOWN_SP2U"
    assert v["lessons_overall"] == "LESSONS_OVERALL_EFFECT_NOT_SHOWN" and v["lessons_overall_panels"] == ["SP1", "SP2U"]
    exact = {("B", s): {"SP1": set(sp1[:10])} for s in rules.SEEDS}
    for s in rules.SEEDS:
        exact[("A", s)] = {"SP2": set(sp2u[:10])}
    v = reader.verdict(write_results(tmp_path / "mixed", fake_records, exact=exact))
    assert (v["lessons"]["SP1"], v["lessons"]["SP2U"]) == ("LESSONS_HELP_SP1", "LESSONS_HURT_SP2U")
    assert v["lessons_overall"] == "LESSONS_OVERALL_MIXED"
    table = {("HELP", "HELP"): "HELP", ("HELP", "EFFECT_NOT_SHOWN"): "EFFECT_NOT_SHOWN", ("HURT", "HELP"): "MIXED",
             ("EFFECT_NOT_SHOWN", "HURT"): "HURT", ("COMPARISON_INCOMPLETE", "HURT"): "COMPARISON_INCOMPLETE",
             ("NOT_EVALUATED", "NOT_EVALUATED"): "NOT_EVALUATED"}
    for (a, b), want in table.items():
        assert rules.overall_lessons({"SP1": a, "SP2U": b, "SP2ALL": "HURT"}) == want


def test_reader_inspected_dev_rows_count_only_in_sp2all(tmp_path, fake_records):
    flagged = {r["id"] for r in fake_records["prep"]["panels"]["SP2"] if r["inspected"]}
    exact = {("B", s): {"SP2": flagged} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path, fake_records, exact=exact))
    assert v["lessons"]["SP2ALL"] == "LESSONS_HELP_SP2ALL" and v["lessons"]["SP2U"] == "LESSONS_EFFECT_NOT_SHOWN_SP2U"
    assert v["pairs"]["SP2U_PAIR1"]["b_B_exact_A_not"] == 0 and v["pairs"]["SP2U_PAIR1"]["rows"] == 208
    assert v["lessons_overall"] == "LESSONS_OVERALL_EFFECT_NOT_SHOWN"      # SP2ALL is not a primary panel


def test_reader_refusals_and_invalid_runs(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path / "s0", fake_records, stage0="NOT_REPRODUCED_1_OF_16_DIFFER"))
    assert v["stage0"] == "STAGE0_NOT_REPRODUCED" and v["no_verdict"] == "NO_VERDICT_STAGE0"
    assert v["architecture"] == "ARCHITECTURE_NOT_EVALUATED" and "LESSONS_NOT_EVALUATED_SP1" in v["labels"]
    assert v["lessons_overall"] == "LESSONS_OVERALL_NOT_EVALUATED"
    v = reader.verdict(write_results(tmp_path / "fr", fake_records, frozen_override={"updates": 1}))
    assert v["no_verdict"] == "NO_VERDICT_FROZEN_RULES_DIFFER"
    v = reader.verdict(write_results(tmp_path / "rl", fake_records, reads={("A", S1): True, ("A", S2): True},
                                     reload_bad={("A", S2)}))
    assert v["runs"]["A_%d" % S2]["validity"] == "RUN_INVALID_RELOAD_MISMATCH"
    assert v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED" and v["pairs"]["SP1_PAIR2"]["outcome"] == "PAIR_INCOMPLETE"
    v = reader.verdict(write_results(tmp_path / "in", fake_records, inconsistent={("B", S1)}))
    assert v["runs"]["B_%d" % S1]["validity"].startswith("RUN_INVALID_RESULT_INCONSISTENT")
    v = reader.verdict(write_results(tmp_path / "pi", fake_records, init_bad={("B", S3)}))
    assert v["pairs"]["SP1_PAIR3"]["outcome"] == "PAIR_INCOMPLETE" and v["lessons"]["SP2U"] == "LESSONS_COMPARISON_INCOMPLETE_SP2U"
    v = reader.verdict(write_results(tmp_path / "z", fake_records, reads={("A", S1): True, ("A", S2): True}, fires_at_zero=True))
    assert v["calibration"] == "INPUT_USE_RULE_FIRES_AT_INITIALISATION"
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE"
    assert v["architecture_reasons"] == ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"]
    v = reader.verdict(write_results(tmp_path / "st", fake_records, job_status="STOPPED"))
    assert v["job"] == "JOB_STOPPED_JOB_WALL_LIMIT"
    empty = tmp_path / "empty"
    empty.mkdir()
    v = reader.verdict(empty)
    assert v["job"] == "JOB_RESULT_MISSING" and v["no_verdict"] == "NO_VERDICT_STAGE0"
    with pytest.raises(reader.ReadError, match="CUSTODY_REFUSED"):
        reader.load(tmp_path / "sealed_notes.json")
    with pytest.raises(reader.ReadError, match="CUSTODY_REFUSED"):
        reader.load(tmp_path / "visible_G_eval.jsonl")


def test_reader_recomputes_what_prep_claims(tmp_path, fake_records):
    """Review MINOR 4: the reader does not trust prep.json's targets, counts, edits or null rates."""
    assert reader.prep_problems(json.loads(rules.canonical(fake_records["prep"]))) == []

    def sp2_target(record):
        row = record["panels"]["SP2"][5]
        row["target_tokens"] = row["target_tokens"][:-2] + row["target_tokens"][-1:] + row["target_tokens"][-2:-1]

    def sp1_counts(record):
        counts = record["sp1_field_counts"]["noetic"]
        counts["1"], counts["2"] = counts["1"] + 30, counts["2"] - 30

    def pool_counts(record):
        record["pools"]["A"]["field_counts"]["noetic"]["2"] += 400

    def edit_kind(record):
        item = next(e for e in record["edits"] if e["field"] == "drive" and e["from"] == "None" and e["to"])
        item["from"] = "3"

    def dropped_edit(record):
        del record["edits"][0]

    for name, mutate, problem in (("t", sp2_target, "PANEL_TARGETS_DIGEST"), ("c", sp1_counts, "SP1_FIELD_COUNTS_RECOMPUTE"),
                                  ("p", pool_counts, "A_POOL_NOETIC_NULL"), ("k", edit_kind, "EDIT_KINDS_DIGEST"),
                                  ("d", dropped_edit, "EDIT_PANEL_DIGEST")):
        v = reader.verdict(write_results(tmp_path / name, fake_records, mutate_prep=mutate))
        assert v["no_verdict"] == "NO_VERDICT_PREP_NOT_FROZEN" and problem in v["prep_problems"], name
        assert v["lessons_overall"] == "LESSONS_OVERALL_NOT_EVALUATED"

    def drop_value(key, body):
        if key == ("B", S1):
            del body["edits"]["values"][-1]

    def swap_values(key, body):
        if key == ("B", S1):
            values = body["edits"]["values"]
            values[0], values[1] = values[1], values[0]
    for name, mutate, reason in (("dv", drop_value, "EDIT_COUNT_DIFFERS"), ("sv", swap_values, "EDIT_ORDER_DIFFERS")):
        v = reader.verdict(write_results(tmp_path / name, fake_records, mutate_final=mutate))
        run = v["runs"]["B_%d" % S1]
        assert run["validity"] == "RUN_INVALID_RESULT_INCONSISTENT_AT_%d" % rules.FINAL and reason in run["problems"][0], name
        # 2 valid NONE runs per arm remain, but B_S1's FINAL file exists without a reading: JUSTIFIED is withheld
        # (verification of 793a4f68, W1; revision 3 said JUSTIFIED here)
        assert v["final_checkpoints_present_without_reading"] == ["B_%d" % S1], name
        assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE", name
        assert v["architecture_reasons"] == ["FINAL_CHECKPOINT_PRESENT_WITHOUT_READING"], name
        assert v["lessons_overall"] == "LESSONS_OVERALL_COMPARISON_INCOMPLETE"


def test_reader_labels_are_the_declared_ones(tmp_path, fake_records):
    patterns = [p.replace("<A|B>", "(A|B)").replace("<STOP_CODE>", "[A-Z0-9_]+").replace("<REASON>", "[A-Z0-9_]+")
                .replace("<PANEL>", "(SP1|SP2U|SP2ALL)").replace("<i>", "[123]") for group in reader.LABELS.values() for p in group]
    seen = set()
    for name, kwargs in (("mix", {"reads": {("B", S1): True}, "missing": {("A", S2)}}),
                         ("tf", {"modes": {k: "tf_reader_freegen_collapse" for k in rules.RUN_ORDER}}),
                         ("shape", {"modes": {k: "shape_only" for k in rules.RUN_ORDER}}),
                         ("v3", {"modes": {("B", S3): "reader"}, "reload_bad": {("B", S3)}}),
                         ("w1", {"modes": {("B", S3): "reader"}, "inconsistent": {("B", S3)}}),
                         ("x1", {"zero_modes": {("A", S3): "structure_only", ("B", S3): "structure_only"},
                                 "inconsistent_zero": {("A", S3), ("B", S3)}}),
                         ("fires", {"fires_at_zero": True}), ("blind", {})):
        v = reader.verdict(write_results(tmp_path / name, fake_records, **kwargs))
        for label in v["labels"]:
            core = label.split(":")[-1]
            assert any(re.fullmatch(p, core) for p in patterns), label
        seen.update(label.split(":")[-1] for label in v["labels"])
    assert {"FIELDS_NOT_READ_IN_ANY_RUN", "INPUT_USE_STRUCTURE_OR_OUTPUT_VARIATION",
            "ARCHITECTURE_INCOMPLETE_BECAUSE_NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID",
            "ARCHITECTURE_INCOMPLETE_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING",
            "CALIBRATION_UNREADABLE", "ARCHITECTURE_INCOMPLETE_BECAUSE_CHECKPOINT0_PRESENT_WITHOUT_READING",
            "ARM_B_INPUT_USE_UNDETERMINED_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING",
            "ARM_A_INPUT_USE_UNDETERMINED_BECAUSE_CHECKPOINT0_PRESENT_WITHOUT_READING",          # revision 3c, N1
            "ARM_B_INPUT_USE_UNDETERMINED_BECAUSE_INPUT_USE_RULE_FIRES_AT_INITIALISATION"} <= seen


# ------------------------------------------------------------------------------------------------------------
# 6. statistics
# ------------------------------------------------------------------------------------------------------------
def test_exact_binomial_and_sign_tests():
    from math import comb
    for n, k, p in ((10, 3, Fraction(1, 10)), (25, 9, Fraction(90, 799)), (6, 0, Fraction(1, 2)), (6, 7, Fraction(1, 3))):
        brute = sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(max(k, 0), n + 1))
        assert rules.binomial_upper_tail(k, n, p) == brute
    assert rules.sign_test_upper(7, 0) == Fraction(1, 128) <= rules.PAIR_ALPHA < rules.sign_test_upper(6, 0) == Fraction(1, 64)
    assert rules.sign_test_upper(0, 0) == 1
    p0 = max(Fraction(90, 799), Fraction(605, 5671))       # SP1 noetic "1": 90 of 799; A pool noetic "2": 605 of 5,671
    smallest = next(k for k in range(799) if rules.binomial_upper_tail(k, 799, p0) <= rules.T1_ALPHA)
    assert smallest == T1_SMALLEST_PASSING_K                # 14.0% noetic accuracy is needed on SP1 for arm A
    with pytest.raises(ValueError):
        rules.binomial_upper_tail(1, 2, Fraction(3, 2))


def test_t2v_boundaries_count_value_edits_only(fake_records):
    record = json.loads(fake_records["bytes"][("A", "reader")])
    values = record["edits"]["values"]
    kinds = [rules.edit_kind(e["field"], e["from"], e["to"]) for e in reader.measurable_edits(fake_records["prep"])]
    value_positions = [i for i, kind in enumerate(kinds) if kind == "value"]
    need = -(-rules.VALUE_EDIT_COUNT // 10)                 # ceil(538 / 10) = 54 rises among the value edits
    assert need == 54 and len(value_positions) == rules.VALUE_EDIT_COUNT
    for value in values:
        value[1] = value[0]
    for i in value_positions[:need]:
        values[i][1] = values[i][0] + 0.02
    reading = reader.input_use(record, "A", fake_records["prep"])
    assert reading["T2V"]["passes"] and reading["T2V"]["up"] == 54 and not reading["T2P"]["passes"]
    values[value_positions[need - 1]][1] = values[value_positions[need - 1]][0] + 0.009   # under the frozen delta
    assert not reader.input_use(record, "A", fake_records["prep"])["T2V"]["passes"]
    for i, kind in enumerate(kinds):                        # presence rises never count toward T2V
        if kind == "presence":
            values[i][1] = values[i][0] + 0.5
    reading = reader.input_use(record, "A", fake_records["prep"])
    assert not reading["T2V"]["passes"] and reading["T2P"]["passes"] and reading["T2P"]["up"] == 235


# ------------------------------------------------------------------------------------------------------------
# 7. jobs: money, custody, watchers, fail-closed
# ------------------------------------------------------------------------------------------------------------
@NEEDS_JOBS
def test_ceiling_arithmetic_whole_job_fits_five_dollars(tmp_path):
    build = _load(JOBS / "data_build_job" / "launch.py", "q4ab_build_launch")
    ab = _load(JOBS / "ab_job" / "launch.py", "q4ab_ab_launch")
    assert round(build.worst_case_usd(), 4) == ab.DATA_BUILD_WORST_CASE_USD == 0.0813
    assert round(ab.worst_case_usd(), 4) == build.TRAINING_WORST_CASE_USD == 2.1678
    assert build.worst_case_usd() + ab.worst_case_usd() <= build.DOLLAR_CEILING == ab.DOLLAR_CEILING == 5.00
    assert ab.JOB_WALL_SECONDS == rules.JOB_WALL_SECONDS < ab.MAX_SECONDS < ab.CLIENT_DEADLINE_MINUTES * 60
    assert build.MAX_SECONDS < build.CLIENT_DEADLINE_MINUTES * 60
    watch = tmp_path / "watch_record.json"
    with pytest.raises(SystemExit, match="no watch record"):
        ab.money_check(watch)
    watch.write_text(json.dumps({"cost_upper_bound_usd": 0.05}), encoding="utf-8")
    assert ab.money_check(watch) == 0.05
    watch.write_text(json.dumps({"cost_upper_bound_usd": 3.0}), encoding="utf-8")
    with pytest.raises(SystemExit, match="exceeds 5.00"):
        ab.money_check(watch)


@NEEDS_JOBS
def test_launch_custody_filters_and_prelaunch_refusals():
    build = _load(JOBS / "data_build_job" / "launch.py", "q4ab_build_launch2")
    ab = _load(JOBS / "ab_job" / "launch.py", "q4ab_ab_launch2")
    lab, data = "research/helm_cas_expression_lab/", "research/helm_cas_expression_lab/data/q3_v0_7/"
    for module in (build, ab):
        assert module.wanted(lab + "q4_ab_train.py") and module.wanted(data + "visible_G_train.jsonl")
        for refused in (data + "sealed_G_train.jsonl", data + "visible_G_eval.jsonl", lab + "SEALED_x.py",
                        lab + "data/q4_sdg_v0_1/visible_A_train.jsonl", lab + "hset1a_notes.json",
                        lab + "sub/q4_x.py", "records/hset1b/x.json"):
            assert not module.wanted(refused), refused
    assert ab.wanted(ab.SPEC) and ab.wanted(ab.RUN + "plan.json") and not build.wanted(ab.RUN + "plan.json")
    rules_ns = ab.frozen_rules_of((HERE / "q4_ab_rules.py").read_bytes())
    with pytest.raises(SystemExit, match="B_PACKAGE_NOT_PINNED"):
        ab.check_pin_blob(json.dumps({"data_versions": {}}).encode(), rules_ns)
    entry = dict(rules.B_PACKAGE, manifest_sha256="a" * 64)
    with pytest.raises(SystemExit, match="B_PIN_NOT_THE_FROZEN_PACKAGE"):
        ab.check_pin_blob(json.dumps({"data_versions": {sdg.SCHEMA: dict(entry, engine="rust+python")}}).encode(), rules_ns)
    assert ab.check_pin_blob(json.dumps({"data_versions": {sdg.SCHEMA: entry}}).encode(), rules_ns) == entry
    frozen, nl = rules.frozen_sha256(), bytes([10])
    rules_blob = (HERE / "q4_ab_rules.py").read_bytes()
    pins_blob = json.dumps({"data_versions": {sdg.SCHEMA: entry}}).encode()

    def attempt(spec, approved_frozen=frozen, approved_lf=None):
        blobs = {ab.LAB + "q4_ab_rules.py": rules_blob, ab.SPEC: spec, ab.LAB + "Q4_SDG_DATA_PINS.json": pins_blob}
        if approved_lf is None:
            approved_lf = {ab.LAB + "q4_ab_rules.py": ab.lf_sha256(rules_blob), ab.SPEC: ab.lf_sha256(spec)}
        return ab.check_frozen(blobs, approved_frozen, approved_lf)
    good = b"# Spec" + nl + nl + b"**Status: FROZEN_BEFORE_LAUNCH** frozen_sha256 `" + frozen.encode() + b"`"
    assert attempt(good)[1] == entry
    for spec in (b"Status: PROPOSED", b"**Status: PROPOSED_FOR_REVIEW**" + nl + b"It becomes FROZEN_BEFORE_LAUNCH later.",
                 b"# Spec" + nl + b"**Status: FROZEN_BEFORE_LAUNCH** (reviewed)"):
        with pytest.raises(SystemExit, match="FROZEN_BEFORE_LAUNCH"):
            attempt(spec)                                        # the word alone, or no hash, is not the status line
    with pytest.raises(SystemExit, match="names another frozen_sha256"):
        attempt(good.replace(frozen.encode(), b"0" * 64))
    with pytest.raises(SystemExit, match="FROZEN_RULES_NOT_THE_APPROVED_ONES"):
        attempt(good, approved_frozen="1" * 64)                  # rules edited after the review (review MINOR 3)
    with pytest.raises(SystemExit, match="APPROVED_SOURCE_CHANGED"):
        attempt(good, approved_lf={ab.LAB + "q4_ab_rules.py": "0" * 64, ab.SPEC: ab.lf_sha256(good)})
    with pytest.raises(SystemExit, match="not filled in"):
        attempt(good, approved_lf={ab.SPEC: "__SPEC__"})
    long_url = "https://bucket.example/" + "x" * 1600
    for module, extra in ((build, {"PACKAGE_URL": long_url}), (ab, {"TORCH_VERSION": "2.11.0", "NUMPY_VERSION": "2.5.2",
                                                                   "JOB_WALL_SECONDS": 11400})):
        template = (Path(module.__file__).parent / "job.sh.template").read_text(encoding="utf-8")
        values = dict({"MAX_SECONDS": 1, "MAX_MINUTES": 1, "BUNDLE_URL": long_url, "RESULTS_URL": long_url,
                       "PROGRESS_URL": long_url, "BUNDLE_SHA256": "0" * 64, "PYTHON_VERSION": "3.14.7"}, **extra)
        assert "__" not in module.fill(template, values)
        with pytest.raises(SystemExit, match="placeholder"):
            module.fill(template, {k: v for k, v in values.items() if k != "RESULTS_URL"})


@NEEDS_JOBS
def test_launcher_approves_exactly_the_committed_rules_programs_and_spec():
    """Two states, both fail-closed.
    UNDER REVIEW (the spec's status is PROPOSED_FOR_REVIEW, as for revision 3): launch.py still holds the approved
    values of an earlier revision, so it must REFUSE this working copy before the pin check.
    APPROVED (the spec carries the frozen status line): launch.py's APPROVED_* values equal this working copy: the
    rules hash, the spec's frozen status line, and the LF bytes of the four decision programs and the spec. Every
    check before the pin passes on the real files."""
    ab = _load(JOBS / "ab_job" / "launch.py", "q4ab_ab_launch3")
    blobs = {rel: (ab.PACKAGE / rel).read_bytes() for rel in ab.APPROVED_LF_SHA256}
    blobs[ab.LAB + "Q4_SDG_DATA_PINS.json"] = (HERE / "Q4_SDG_DATA_PINS.json").read_bytes()
    if ab.FROZEN_STATUS_LINE.search(blobs[ab.SPEC]) is None:
        assert re.search(rb"^[*][*]Status: PROPOSED_FOR_REVIEW[*][*]", blobs[ab.SPEC], re.MULTILINE)
        with pytest.raises(SystemExit, match="FROZEN_RULES_NOT_THE_APPROVED_ONES|FROZEN_BEFORE_LAUNCH"):
            ab.check_frozen(blobs)                                          # refused before the pin is even read
        return
    assert ab.APPROVED_FROZEN_SHA256 == rules.frozen_sha256()
    for rel, want in ab.APPROVED_LF_SHA256.items():
        assert ab.lf_sha256(blobs[rel]) == want, rel
    status = ab.FROZEN_STATUS_LINE.search(blobs[ab.SPEC])
    assert status and status.group(1).decode() == rules.frozen_sha256()
    # only the STATUS LINE may not say PROPOSED_FOR_REVIEW; the spec's history bullets legitimately quote that word
    assert re.search(rb"^[*][*]Status: PROPOSED_FOR_REVIEW[*][*]", blobs[ab.SPEC], re.MULTILINE) is None
    try:
        ab.check_frozen(blobs)
    except SystemExit as error:                               # before the pin exists, only the pin check may refuse
        assert "B_PACKAGE_NOT_PINNED" in str(error), str(error)


@NEEDS_JOBS
def test_launcher_refuses_b_sources_that_changed_since_the_data_build():
    """Review MINOR 6: the data build's recorded source hashes must equal the files at the source commit."""
    ab = _load(JOBS / "ab_job" / "launch.py", "q4ab_ab_launch4")
    names = set(sdg.source_pins()) | set(sdg.Q3_IMMUTABLE_LF_SHA256)
    blobs = {ab.LAB + name: (HERE / name).read_bytes() for name in names}
    blobs[ab.DATA + "manifest.json"] = (DATA / "manifest.json").read_bytes()
    assert ab.COMPILER in blobs
    manifest = {"sources_lf_sha256": sdg.source_pins(), "q3_immutable_lf_sha256": sdg.Q3_IMMUTABLE_LF_SHA256,
                "compiler": historical_compiler.source_receipt(), "q3_v0_7_manifest_sha256": sdg.Q3_V07_MANIFEST_SHA256}
    blob = json.dumps(manifest, sort_keys=True).encode()
    entry = {"manifest_sha256": ab.lf_sha256(blob)}
    assert ab.check_data_build_manifest(blob, blobs, entry)["sources_lf_sha256"] == sdg.source_pins()
    edited = dict(blobs, **{ab.LAB + "q4_sdg_curriculum.py": blobs[ab.LAB + "q4_sdg_curriculum.py"] + b"# D rounds" + bytes([10])})
    with pytest.raises(SystemExit, match="B_PACKAGE_SOURCES_CHANGED_SINCE_THE_DATA_BUILD.*q4_sdg_curriculum.py"):
        ab.check_data_build_manifest(blob, edited, entry)
    with pytest.raises(SystemExit, match="DATA_BUILD_MANIFEST_NOT_THE_PINNED_ONE"):
        ab.check_data_build_manifest(blob, blobs, {"manifest_sha256": "0" * 64})
    empty = json.dumps({"sources_lf_sha256": {}}).encode()
    with pytest.raises(SystemExit, match="no source hashes"):
        ab.check_data_build_manifest(empty, blobs, {"manifest_sha256": ab.lf_sha256(empty)})
    source = (JOBS / "ab_job" / "launch.py").read_text(encoding="utf-8")
    body = source[source.index("def assemble"):source.index("def build_bundle")]
    assert body.index("check_frozen(blobs)") < body.index("check_data_build_manifest(") < body.index("identity = {")


def test_smoke_stage_runs_the_fresh_process_reload_on_the_checkpoint_rows():
    """Review MINOR 7: the reload path runs in the smoke stage, before any main run; its rows follow the checkpoint."""
    source = (HERE / "q4_ab_train.py").read_text(encoding="utf-8")
    smoke = source[source.index("def smoke_and_project"):source.index("def reload_in_fresh_process")]
    assert (smoke.index("reload_in_fresh_process(reload_dir") < smoke.index("JobStop(\"SMOKE_RELOAD_FAILED\"")
            < smoke.index("JobStop(\"PROJECTED_OVER_TIME\""))
    assert "SMOKE_RELOAD_FAILED" in rules.STOP_CODES
    run = source[source.index("def run("):]
    assert run.index("smoke_and_project(") < run.index("stage = \"runs\"")
    prep_record = {"panels": {"SP1": [{"id": "r%d" % i, "observation": "o%d" % i} for i in range(64)]}}
    thinned = {"panels": {"SP1": {"rows": [{"id": "r%d" % i} for i in range(0, 64, rules.SMOKE_STRIDE)]}}}
    rows = train.reload_rows(thinned, prep_record)
    assert [r[0]["id"] for r in rows] == ["r0", "r16", "r32", "r48"] and [r[1] for r in rows] == ["o0", "o16", "o32", "o48"]
    full = {"panels": {"SP1": {"rows": [{"id": "r%d" % i} for i in range(64)]}}}
    assert [r[1] for r in train.reload_rows(full, prep_record)] == ["o%d" % i for i in range(train.RELOAD_ROWS)]


def _tar(members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, body, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(body)
                tar.addfile(info, io.BytesIO(body))
            elif kind == "symlink":
                info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
                tar.addfile(info)
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
    return buffer.getvalue()


@NEEDS_JOBS
def test_watchers_unpack_nested_results_safely(tmp_path):
    ab = _load(JOBS / "ab_job" / "watch.py", "q4ab_ab_watch")
    build = _load(JOBS / "data_build_job" / "watch.py", "q4ab_build_watch")
    members = [("out/STATUS", b"done\n", "file"), ("out/ab", b"", "dir"),
               ("out/ab/runs/A_20260931/checkpoint/model_state.pt", b"weights", "file"),
               ("out/ab/runs/A_20260931/checkpoint_32768.json", b"{}", "file"),
               ("out/../escape.txt", b"x", "file"), ("/etc/evil", b"x", "file"), ("out/ab/sealed_A_train.jsonl", b"x", "file"),
               ("out/visible_G_eval.jsonl", b"x", "file"), ("out/link", b"", "symlink"), ("out/.hidden", b"x", "file"),
               ("out/a/b/c/d/e/f/g/too_deep.json", b"x", "file"), ("elsewhere/x.json", b"x", "file"),
               ("out/hset1a_copy.json", b"x", "file"), ("out/a\\b.json", b"x", "file")]
    body = _tar(members)
    written, skipped = ab.extract(body, tmp_path / "ab")
    assert written == 3
    assert (tmp_path / "ab" / "ab" / "runs" / "A_20260931" / "checkpoint" / "model_state.pt").read_bytes() == b"weights"
    assert not (tmp_path / "escape.txt").exists() and not list((tmp_path / "ab").rglob("*sealed*"))
    assert set(skipped) >= {"out/../escape.txt", "/etc/evil", "out/ab/sealed_A_train.jsonl", "out/link", "out/.hidden",
                            "out/a/b/c/d/e/f/g/too_deep.json", "out/visible_G_eval.jsonl", "out/hset1a_copy.json"}
    written, skipped = build.extract(body, tmp_path / "build")
    assert written == 1 and (tmp_path / "build" / "STATUS").is_file()      # the data-build watcher is flat only
    big = _tar([("out/huge.bin", b"x" * 10, "file")])
    old = ab.MAX_MEMBER_BYTES
    try:
        ab.MAX_MEMBER_BYTES = 5
        assert ab.extract(big, tmp_path / "big") == (0, ["out/huge.bin"])
    finally:
        ab.MAX_MEMBER_BYTES = old


def test_runner_fails_closed_without_cuda_before_torch_or_any_write(tmp_path):
    for device in ("cpu", "cuda", "", None, "cuda:x"):
        with pytest.raises(train.JobStop, match="GPU_REQUIRED"):
            train.run(RUN, DATA, tmp_path / "out", device=device)
        with pytest.raises(train.JobStop, match="GPU_REQUIRED"):
            train.reload_check(tmp_path / "run", tmp_path / "prep.json", device)
    assert not (tmp_path / "out").exists() and "torch" not in sys.modules
    assert train.stop_code(prep.PrepError("PANEL_DIGEST_MISMATCH: x")) == "PANEL_DIGEST_MISMATCH"
    assert train.stop_code(ValueError("something else")) is None
    assert train.stop_code(SystemExit(2)) is None and train.stop_code(sdg.Refusal("FORBIDDEN_SHAPE")) is None
    assert train.stop_code(train.JobStop("NUMERICAL_FAILURE", "x")) == "NUMERICAL_FAILURE"
    with pytest.raises(ValueError, match="UNKNOWN_STOP_CODE"):
        train.JobStop("NOT_A_CODE")


def test_source_hygiene_no_eval_or_sealed_door():
    for name in ("q4_ab_train.py", "q4_ab_prep.py", "read_q4_ab_results.py", "q4_ab_rules.py"):
        source = (HERE / name).read_text(encoding="utf-8")
        for forbidden in ("load_split(", "load_dataset(", "load_lesson_pairs(", "verify_package(", "\"sealed_", "_eval.jsonl\"",
                          "extractall"):
            assert forbidden not in source, (name, forbidden)
    runner = (HERE / "q4_ab_train.py").read_text(encoding="utf-8")
    assert "exist_ok=False" in runner and runner.count(".open(\"xb\")") == 1       # create-only outputs (reload.log)
    assert "retry" not in runner.lower().replace("no automatic retry", "").replace("nothing is retried", "")
