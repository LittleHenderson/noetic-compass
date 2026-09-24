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
    assert "TO_BE_MEASURED" not in json.dumps(frozen)


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
class FakeModel:
    """NOT Q4. `reads_input=True` decodes the true tree of whatever text it is given (a perfect reader);
    False ignores its input and always writes the same one-state tree. Only for wiring the runner to the reader."""

    def __init__(self, reads_input):
        self.reads_input, self.texts, self.tokens = reads_input, [], {}

    def encode(self, sequence):
        text = bytes(b - 1 for b in sequence.byte_ids).decode("utf-8")
        if text not in self.tokens:
            self.tokens[text] = ast_to_tokens(sdg.parse_surface(text))
            self.texts.append(text)
        return Bottleneck((float(self.texts.index(text)) if self.reads_input else 0.0, 1.0))

    def next_logits(self, bottleneck, prefix):
        if self.reads_input:
            want = self.tokens[self.texts[int(bottleneck.values[0])]]
        else:
            want = ast_to_tokens(sdg.leaf_ast(0, "P"))
        logits = [0.0] * len(TOKENS)
        choice = want[len(prefix)] if len(prefix) < len(want) and tuple(want[:len(prefix)]) == tuple(prefix) else None
        allowed = allowed_next(tuple(prefix))
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
    """evaluate() of the RUNNER on the full shared panels, for a blind and a reading fake, per arm's teach rows."""
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
            teach = [prep.with_allowed(dict(pools[arm][i], panel="TEACH_FIT"))
                     for i in prep.stream_indices(len(pools[arm]), rules.SEEDS[0], min(4, len(pools[arm])))]
            out["teach"][arm] = teach
            for reads in (False, True):
                out["records"][(arm, reads)] = train.evaluate(FakeModel(reads), dict(shared, TEACH_FIT=teach), edits,
                                                              record["sp1_partners"], _NoDeadline())
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


def write_results(root, fake, *, reads=None, exact=None, stage0="REPRODUCED_16_OF_16", missing=(), reload_bad=(),
                  init_bad=(), inconsistent=(), job_status="COMPLETE", fires_at_zero=False, frozen_override=None):
    """A complete synthetic results folder. `reads[(arm, seed)]` = the final-checkpoint model reads its input;
    `exact[(arm, seed)]` = {panel: ids} made exact at the final checkpoint."""
    root = Path(root)
    record = json.loads(rules.canonical(fake["prep"]))
    if frozen_override:
        record["frozen"] = dict(record["frozen"], **frozen_override)
    _write(root / "prep.json", record)
    _write(root / "stage0.json", {"status": stage0, "reinit_update_1": {"reproduced": True}})
    _write(root / "job_result.json", {"status": job_status, "stop_code": None if job_status == "COMPLETE" else "JOB_WALL_LIMIT"})
    frozen = rules.frozen_sha256()
    for arm, seed in rules.RUN_ORDER:
        if (arm, seed) in missing:
            continue
        folder = root / "runs" / ("%s_%d" % (arm, seed))
        teach = fake["teach"][arm]
        init = "init-%d" % seed + ("-other" if (arm, seed) in init_bad else "")
        _write(folder / "run_manifest.json", {"arm": arm, "seed": seed, "frozen_sha256": frozen, "init_state_sha256": init,
                                              "teach_fit": [prep.panel_row_record(r) for r in teach]})
        for point in rules.CHECKPOINTS:
            use = (reads or {}).get((arm, seed), False) if point == rules.FINAL else (fires_at_zero and point == 0)
            body = json.loads(fake["bytes"][(arm, use)])
            if point == rules.FINAL:
                for panel, ids in ((exact or {}).get((arm, seed)) or {}).items():
                    _make_exact(body, panel, ids, record["panels"][panel])
                if (arm, seed) in inconsistent:
                    body["panels"]["SP1"]["rows"][0]["exact"] = 1 - body["panels"]["SP1"]["rows"][0]["exact"]
            body.update(arm=arm, seed=seed, checkpoint=point, frozen_sha256=frozen)
            _write(folder / ("checkpoint_%05d.json" % point), body)
        _write(folder / "run_result.json", {"status": "COMPLETE", "updates": rules.UPDATES, "frozen_sha256": frozen,
                                            "presentations": rules.UPDATES})
        _write(folder / "reload_check.json", {"status": "RELOAD_MISMATCH" if (arm, seed) in reload_bad else "RELOAD_REPRODUCED"})
    return root


S1, S2, S3 = rules.SEEDS


def test_runner_records_satisfy_the_reader_and_the_rule_separates_the_fakes(fake_records):
    blind, reading = fake_records["records"][("A", False)], fake_records["records"][("A", True)]
    assert blind["panels"]["SP1"]["distinct_free_outputs"] == 1 and blind["panels"]["SP1"]["exact"] == 0
    assert reading["panels"]["SP1"]["exact"] == 256 and reading["panels"]["SP2"]["exact"] == 256
    assert len(reading["edits"]["values"]) == rules.EDIT_COUNT
    for arm in rules.ARMS:
        assert reader.input_use(fake_records["records"][(arm, False)], arm, fake_records["prep"])["label"] == "INPUT_USE_NOT_DETECTED"
        detected = reader.input_use(fake_records["records"][(arm, True)], arm, fake_records["prep"])
        noetic_positions = sum(fake_records["prep"]["sp1_noetic_counts"].values())
        assert detected["label"] == "INPUT_USE_DETECTED" and detected["T1"]["correct"] == detected["T1"]["n"] == noetic_positions == 799
    t1 = reader.input_use(blind, "A", fake_records["prep"])["T1"]
    assert t1["correct"] == fake_records["prep"]["sp1_noetic_counts"]["0"] == 88 and not t1["passes"]   # always N0


def test_reader_b_reads_a_does_not(tmp_path, fake_records):
    reads = {("B", s): True for s in rules.SEEDS}
    exact = {("B", s): {"SP1": set(r["id"] for r in fake_records["prep"]["panels"]["SP1"]),
                        "SP2": set(r["id"] for r in fake_records["prep"]["panels"]["SP2"])} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path, fake_records, reads=reads, exact=exact))
    assert v["job"] == "JOB_COMPLETE" and v["stage0"] == "STAGE0_REPRODUCED"
    assert v["arms"]["A"]["label"] == "ARM_A_DOES_NOT_SHOW_INPUT_USE" and v["arms"]["B"]["label"] == "ARM_B_SHOWS_INPUT_USE"
    assert v["architecture"] == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED"
    assert v["lessons"] == {"SP1": "LESSONS_HELP_SP1", "SP2U": "LESSONS_HELP_SP2U", "SP2ALL": "LESSONS_HELP_SP2ALL"}
    assert v["pairs"]["SP2U_PAIR1"]["b_B_exact_A_not"] == 208 and v["calibration"] == "INPUT_USE_RULE_SILENT_AT_INITIALISATION"
    assert all(v["runs"]["%s_%d" % k]["validity"] == "RUN_VALID" for k in rules.RUN_ORDER)


def test_reader_no_arm_reads_input_justifies_the_architecture_change(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path, fake_records))
    assert v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED"
    assert set(v["lessons"].values()) == {"LESSONS_EFFECT_NOT_SHOWN_SP1", "LESSONS_EFFECT_NOT_SHOWN_SP2U",
                                          "LESSONS_EFFECT_NOT_SHOWN_SP2ALL"}


def test_reader_two_of_three_seeds_are_enough_and_one_is_not(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path / "two", fake_records, reads={("A", S1): True, ("A", S3): True}))
    assert v["arms"]["A"]["label"] == "ARM_A_SHOWS_INPUT_USE" and v["architecture"] == "ARCHITECTURE_CHANGE_NOT_JUSTIFIED"
    v = reader.verdict(write_results(tmp_path / "one", fake_records, reads={("A", S1): True}))
    assert v["arms"]["A"]["label"] == "ARM_A_DOES_NOT_SHOW_INPUT_USE" and v["architecture"] == "ARCHITECTURE_CHANGE_JUSTIFIED"
    v = reader.verdict(write_results(tmp_path / "gap", fake_records, reads={("A", S1): True}, missing={("A", S3)}))
    assert v["arms"]["A"]["label"] == "ARM_A_INPUT_USE_UNDETERMINED"
    assert v["architecture"] == "ARCHITECTURE_DECISION_INCOMPLETE" and v["runs"]["A_%d" % S3]["validity"] == "RUN_INCOMPLETE"
    assert v["lessons"]["SP1"] == "LESSONS_COMPARISON_INCOMPLETE_SP1"


def test_reader_lessons_need_all_three_pairs_and_the_sign_test(tmp_path, fake_records):
    sp1 = [r["id"] for r in fake_records["prep"]["panels"]["SP1"]]
    exact = {("B", S1): {"SP1": set(sp1[:7])}, ("B", S2): {"SP1": set(sp1[:7])}, ("B", S3): {"SP1": set(sp1[:6])}}
    v = reader.verdict(write_results(tmp_path / "a", fake_records, exact=exact))
    assert [v["pairs"]["SP1_PAIR%d" % i]["outcome"] for i in (1, 2, 3)] == ["B_BEATS_A", "B_BEATS_A", "NO_PAIRED_DIFFERENCE"]
    assert v["pairs"]["SP1_PAIR3"]["p_B_beats_A"] == 1 / 64 and v["lessons"]["SP1"] == "LESSONS_EFFECT_NOT_SHOWN_SP1"
    exact = {("A", s): {"SP1": set(sp1[:10])} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path / "b", fake_records, exact=exact))
    assert v["lessons"]["SP1"] == "LESSONS_HURT_SP1"


def test_reader_inspected_dev_rows_count_only_in_sp2all(tmp_path, fake_records):
    flagged = {r["id"] for r in fake_records["prep"]["panels"]["SP2"] if r["inspected"]}
    exact = {("B", s): {"SP2": flagged} for s in rules.SEEDS}
    v = reader.verdict(write_results(tmp_path, fake_records, exact=exact))
    assert v["lessons"]["SP2ALL"] == "LESSONS_HELP_SP2ALL" and v["lessons"]["SP2U"] == "LESSONS_EFFECT_NOT_SHOWN_SP2U"
    assert v["pairs"]["SP2U_PAIR1"]["b_B_exact_A_not"] == 0 and v["pairs"]["SP2U_PAIR1"]["rows"] == 208


def test_reader_refusals_and_invalid_runs(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path / "s0", fake_records, stage0="NOT_REPRODUCED_1_OF_16_DIFFER"))
    assert v["stage0"] == "STAGE0_NOT_REPRODUCED" and v["no_verdict"] == "NO_VERDICT_STAGE0"
    assert v["architecture"] == "ARCHITECTURE_NOT_EVALUATED" and "LESSONS_NOT_EVALUATED_SP1" in v["labels"]
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


def test_reader_labels_are_the_declared_ones(tmp_path, fake_records):
    v = reader.verdict(write_results(tmp_path, fake_records, reads={("B", S1): True}, missing={("A", S2)}))
    patterns = [p.replace("<A|B>", "(A|B)").replace("<STOP_CODE>", "[A-Z0-9_]+").replace("<REASON>", "[A-Z0-9_]+")
                .replace("<PANEL>", "(SP1|SP2U|SP2ALL)").replace("<i>", "[123]") for group in reader.LABELS.values() for p in group]
    import re
    for label in v["labels"]:
        core = label.split(":")[-1]
        assert any(re.fullmatch(p, core) for p in patterns), label


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


def test_t2_boundaries(fake_records):
    record = json.loads(fake_records["bytes"][("A", True)])
    values = record["edits"]["values"]
    need = -(-len(values) // 10)                            # ceil(E / 10) rises are required
    for i, value in enumerate(values):
        value[1] = value[0] + (0.02 if i < need else 0.0)
    assert reader.input_use(record, "A", fake_records["prep"])["T2"]["passes"]
    values[need - 1][1] = values[need - 1][0] + 0.009       # just under the frozen delta: not a rise
    assert not reader.input_use(record, "A", fake_records["prep"])["T2"]["passes"]


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
    blobs = {ab.LAB + "q4_ab_rules.py": (HERE / "q4_ab_rules.py").read_bytes(), ab.SPEC: b"Status: PROPOSED",
             ab.LAB + "Q4_SDG_DATA_PINS.json": json.dumps({"data_versions": {sdg.SCHEMA: entry}}).encode()}
    with pytest.raises(SystemExit, match="FROZEN_BEFORE_LAUNCH"):
        ab.check_frozen(blobs)
    blobs[ab.SPEC] = b"**Status: PROPOSED_FOR_REVIEW**" + bytes([10]) + b"It becomes FROZEN_BEFORE_LAUNCH after review."
    with pytest.raises(SystemExit, match="FROZEN_BEFORE_LAUNCH"):
        ab.check_frozen(blobs)                                   # the word alone is not the status line
    blobs[ab.SPEC] = b"# Spec" + bytes([10, 10]) + b"**Status: FROZEN_BEFORE_LAUNCH** (reviewed)"
    assert ab.check_frozen(blobs)[1] == entry
    spec = (HERE / "Q4_SDG_AB_SPEC_v0_2.md").read_bytes()
    assert ab.FROZEN_STATUS_LINE.search(spec) is None or b"PROPOSED_FOR_REVIEW" not in spec
    long_url = "https://bucket.example/" + "x" * 1600
    for module, extra in ((build, {"PACKAGE_URL": long_url}), (ab, {"TORCH_VERSION": "2.11.0", "NUMPY_VERSION": "2.5.2",
                                                                   "JOB_WALL_SECONDS": 11400})):
        template = (Path(module.__file__).parent / "job.sh.template").read_text(encoding="utf-8")
        values = dict({"MAX_SECONDS": 1, "MAX_MINUTES": 1, "BUNDLE_URL": long_url, "RESULTS_URL": long_url,
                       "PROGRESS_URL": long_url, "BUNDLE_SHA256": "0" * 64, "PYTHON_VERSION": "3.14.7"}, **extra)
        assert "__" not in module.fill(template, values)
        with pytest.raises(SystemExit, match="placeholder"):
            module.fill(template, {k: v for k, v in values.items() if k != "RESULTS_URL"})


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
