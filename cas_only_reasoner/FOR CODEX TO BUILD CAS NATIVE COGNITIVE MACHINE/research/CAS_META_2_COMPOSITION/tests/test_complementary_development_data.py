"""Guarded development-only reproduction; no final task construction or runtime."""
import ast
import builtins
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import io
import json
from pathlib import Path
import sys

import pytest

DENIED = {"torch", "numpy", "tensorflow", "jax", "jaxlib", "boto3", "botocore",
          "cas_cjt", "casformer", "transformers", "safetensors", "requests", "httpx"}


class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise AssertionError("DEVELOPMENT_FORBIDDEN_IMPORT:" + fullname)


guard = DenyImports()
sys.meta_path.insert(0, guard)
try:
    from cas_meta2.complementary_teaching import development_data as dev, data, course
    from cas_meta2.graph_teaching import final_panel, face_corpus, face_tasks, face_roles
    from tools.check_structural_supply_20260916 import shape_key
finally:
    sys.meta_path.remove(guard)

ROOT = Path(__file__).resolve().parents[1]
EXCLUSIONS = ROOT / "records/complementary_teaching_001/preparation_20260916/historical_exclusions.json"
PUBLIC_SUPPLY = ROOT / "records/learning_panel_001/supply.json"


@pytest.fixture(autouse=True)
def no_runtime_or_final_artifact_reads(monkeypatch):
    guard = DenyImports(); sys.meta_path.insert(0, guard)
    original = builtins.__import__
    def import_guard(name, *args, **kwargs):
        if name.split(".")[0] in DENIED:
            raise AssertionError("DEVELOPMENT_FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", import_guard)
    opener = io.open
    def read_guard(path, *args, **kwargs):
        if not isinstance(path, int):
            name = Path(path).name
            if name in {"data_manifest.json", "TASK_BINDINGS.json"} or Path(path).suffix in {".pt", ".whl", ".zip"}:
                raise AssertionError("FINAL_TARGET_OR_BINARY_ARTIFACT_READ:" + str(path))
        return opener(path, *args, **kwargs)
    monkeypatch.setattr(io, "open", read_guard)
    try:
        yield
        assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)
    finally:
        sys.meta_path.remove(guard)


@pytest.fixture(scope="module")
def exclusions():
    raw = EXCLUSIONS.read_bytes()
    assert sha256(raw).hexdigest() == "e00cc95d59b17fd36a8c478a0497257e5355e071348d4f4c833d9d3a470a3aa8"
    return json.loads(raw)


@pytest.fixture(scope="module")
def inventory():
    # This retained file contains topology metadata, not questions or targets.
    raw = json.loads(PUBLIC_SUPPLY.read_bytes())
    assert all(set(row) == {"authoring_examination", "candidate_pool", "current_allocation",
                           "historically_excluded", "stats", "supports_all_three_reach_classes", "topology"}
               for row in raw["rows"])
    return raw


def forbidden(*args, **kwargs):
    raise AssertionError("FINAL_OR_BOTH_SPLIT_CONSTRUCTOR_CALLED")


@pytest.fixture
def construction_guard(monkeypatch, inventory):
    selected = sorted(row["topology"] for row in inventory["rows"] if row["current_allocation"] == "development")
    seen = {"family_seeds": [], "record_families": [], "face_episodes": [], "face_content": []}
    original_family = final_panel._family
    original_task = course._record_task
    original_episode = face_tasks.compile_episode
    original_content = face_tasks.content_for
    def family(shape, seed):
        assert seed in range(2026091600, 2026091606)
        assert shape_key(shape) == selected[seed - 2026091600]
        seen["family_seeds"].append(seed)
        return original_family(shape, seed)
    def record(graph, question, options, correct, family_id):
        assert family_id in {"complementary_" + key for key in selected}
        seen["record_families"].append(family_id)
        return original_task(graph, question, options, correct, family_id)
    def episode(family, *args, **kwargs):
        assert family["split"] == face_corpus.DEVELOPMENT
        seen["face_episodes"].append(family["family_id"])
        return original_episode(family, *args, **kwargs)
    def content(family, *args, **kwargs):
        assert family["split"] == face_corpus.DEVELOPMENT
        seen["face_content"].append(family["family_id"])
        return original_content(family, *args, **kwargs)
    monkeypatch.setattr(data, "build_panels", forbidden)
    monkeypatch.setattr(final_panel, "build_final_panel", forbidden)
    monkeypatch.setattr(final_panel, "_supports_all_reach", forbidden)
    monkeypatch.setattr(face_tasks, "build_all", forbidden)
    monkeypatch.setattr(final_panel, "_family", family)
    monkeypatch.setattr(course, "_record_task", record)
    monkeypatch.setattr(data, "_record_task", record)
    monkeypatch.setattr(face_tasks, "compile_episode", episode)
    monkeypatch.setattr(face_tasks, "content_for", content)
    return seen


def source_development_reference(exclusions, inventory):
    """Execute only the development prefix of the canonical source definition.

    The unsafe supply probe is removed entirely and replaced by retained public
    topology metadata. Family loop is capped at six; earlier-skill loop retains
    only DEVELOPMENT; final panels and the full manifest are omitted. The actual
    data.build_panels symbol is never called. Constructor guards remain active.
    """
    module = ast.parse(Path(data.__file__).read_bytes())
    function = deepcopy(next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "build_panels"))
    function.name = "development_source_prefix"
    new_body = []
    for statement in function.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "manifest" for t in statement.targets):
            break
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "available" for t in statement.targets):
            statement.value = ast.Name(id="_public_eligible_shapes", ctx=ast.Load())
        elif isinstance(statement, ast.For) and isinstance(statement.target, ast.Name) and statement.target.id == "shape":
            continue
        elif isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "panels" for t in statement.targets):
            statement.value = ast.Dict(keys=[ast.Constant(name) for name in dev.PANELS],
                                       values=[ast.List(elts=[], ctx=ast.Load()) for _ in dev.PANELS])
        elif isinstance(statement, ast.For) and isinstance(statement.target, ast.Tuple):
            if isinstance(statement.target.elts[0], ast.Name) and statement.target.elts[0].id == "index":
                statement.iter = ast.parse("enumerate(sorted(available.items())[:6])", mode="eval").body
            elif isinstance(statement.target.elts[0], ast.Name) and statement.target.elts[0].id == "split":
                statement.iter = ast.parse("((face_corpus.DEVELOPMENT, 'development_earlier_skills'),)", mode="eval").body
        new_body.append(statement)
    new_body.append(ast.Return(value=ast.Name(id="panels", ctx=ast.Load())))
    function.body = new_body
    tree = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    eligible = {row["topology"] for row in inventory["rows"] if row["candidate_pool"] and row["supports_all_three_reach_classes"]}
    shapes = {shape_key(shape): shape for shape in final_panel.enumerate_patterns().values()}
    namespace = dict(vars(data))
    namespace["_public_eligible_shapes"] = {key: shapes[key] for key in eligible}
    exec(compile(tree, "<canonical-development-prefix-only>", "exec"), namespace)
    return namespace["development_source_prefix"](exclusions, topology_key=shape_key)


def test_supply_is_graph_only_and_matches_existing_public_topology_audit(exclusions, inventory, monkeypatch):
    for owner, name in ((data, "build_panels"), (final_panel, "_family"), (final_panel, "_supports_all_reach"),
                        (final_panel, "_reach_case"), (final_panel, "build_final_panel"), (face_tasks, "compile_episode")):
        monkeypatch.setattr(owner, name, forbidden)
    supply = dev.candidate_supply(exclusions, topology_key=shape_key)
    assert supply["counts"] == {"enumerated": 92, "excluded": 45, "potential": 47, "eligible": 36,
                                "potential_without_all_reach": 11, "development_families": 6, "unconstructed_eligible": 30}
    by_key = {row["topology"]: row for row in inventory["rows"]}
    assert set(by_key) == {row["topology"] for row in supply["topologies"]}
    for row in supply["topologies"]:
        old = by_key[row["topology"]]
        assert row["excluded"] is old["historically_excluded"]
        assert all(row["reach_availability"].values()) is old["supports_all_three_reach_classes"]
        assert row["stats"] == old["stats"]
        assert (row["development_index"] is not None) == (old["current_allocation"] == "development")
    assert supply["exclusions_sha256"] == course.digest(exclusions)
    assert supply["supply_sha256"] == course.digest({k: v for k, v in supply.items() if k != "supply_sha256"})
    for row in supply["source_identity"]["files"]:
        raw = (ROOT / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"]


def test_exact_development_records_and_deduplicated_membership(exclusions, inventory, construction_guard):
    before = deepcopy(exclusions)
    document = dev.build_development(exclusions, topology_key=shape_key)
    expected = source_development_reference(exclusions, inventory)
    assert exclusions == before
    for panel in dev.PANELS:
        actual = dev.panel_tasks(document, panel)
        # Full canonical equality covers original IDs, public text/choice order,
        # private target, graph/question, semantic identity and auxiliary fields.
        assert actual == expected[panel]
        assert course.digest(actual) == course.digest(expected[panel])
    assert len(document["tasks"]) == 114
    assert document["counts"]["panel_memberships"] == 120
    assert document["counts"]["duplicate_component_memberships"] == 6
    assert document["panel_record_ids"][dev.PANELS[1]] == document["panel_record_ids"][dev.PANELS[0]][2::3]
    for record_id in document["panel_record_ids"][dev.PANELS[1]]:
        assert document["memberships"][record_id] == [dev.PANELS[0], dev.PANELS[1]]
    assert sum(len(v) for v in document["memberships"].values()) == 120
    assert construction_guard["family_seeds"] == list(range(2026091600, 2026091606)) * 2
    assert len(construction_guard["record_families"]) == 36
    assert len(construction_guard["face_episodes"]) == 192
    assert len(construction_guard["face_content"]) == 192
    assert document["final_questions_constructed"] == document["final_answers_constructed"] == 0
    assert document["limitations"]["legacy_option_construction"] == "UNRESOLVED_TARGET_CONDITIONED_LEGACY_CHOICES"
    assert document["limitations"]["study_admission"] == "UNRESOLVED"
    copied = dev.panel_tasks(document, dev.PANELS[0]); copied[0]["public"]["problem"] = "mutated"
    assert document["tasks"][0]["public"]["problem"] != "mutated"


@pytest.mark.parametrize("shape,expected", [
    ({"a": ("b",)}, {"direct": True, "via": False, "absent": False}),
    ({"a": ("b",), "b": ("c",)}, {"direct": True, "via": True, "absent": True}),
    ({"a": ("b", "c")}, {"direct": True, "via": False, "absent": False}),
    ({"a": ("b", "c"), "b": ("c",)}, {"direct": True, "via": False, "absent": True}),
])
def test_topology_probe_counts_non_direct_reach_not_just_nesting(shape, expected):
    assert dev.reach_availability(shape) == expected


def test_cyclic_shape_refused():
    with pytest.raises(ValueError, match="SHAPE_CYCLE"):
        dev.reach_availability({"a": ("b",), "b": ("a",)})


@pytest.mark.parametrize("mutation", [
    lambda e: e.update(complete=False), lambda e: e.update(complete=1),
    lambda e: e.update(failures=["unknown custody"]), lambda e: e.update(extra=1),
    lambda e: e.update(actual_neural_presentations=True),
    lambda e: e["excluded_topologies"].append(e["excluded_topologies"][0]),
    lambda e: e["archives"][0].update(errors=["archive missing"]),
])
def test_bad_exclusions_refused_before_any_enumeration(exclusions, mutation, monkeypatch):
    changed = deepcopy(exclusions); mutation(changed)
    monkeypatch.setattr(final_panel, "enumerate_patterns", forbidden)
    with pytest.raises(ValueError):
        dev.build_development(changed, topology_key=shape_key)


def test_insufficient_supply_fails_before_question_construction(exclusions, monkeypatch):
    changed = deepcopy(exclusions)
    changed["excluded_topologies"] = sorted({shape_key(s) for s in final_panel.enumerate_patterns().values()})
    monkeypatch.setattr(final_panel, "_family", forbidden)
    with pytest.raises(ValueError, match="SUPPLY_BELOW_36"):
        dev.build_development(changed, topology_key=shape_key)


def test_resealed_mutations_rejected_by_development_only_reconstruction(exclusions, construction_guard, monkeypatch):
    document = dev.build_development(exclusions, topology_key=shape_key)
    assert dev.validate_development(document, exclusions=exclusions, topology_key=shape_key) is document
    # Reuse only the already enumerated public shapes during repeated rejection
    # checks, while still reconstructing every development task under guards.
    patterns = final_panel.enumerate_patterns()
    monkeypatch.setattr(final_panel, "enumerate_patterns", lambda: deepcopy(patterns))
    for mutate in (
        lambda d: d["tasks"][0].update(correct="forged target"),
        lambda d: d["tasks"][0]["public"].update(problem="forged public"),
        lambda d: d["panel_record_ids"][dev.PANELS[1]].reverse(),
        lambda d: d["memberships"][d["tasks"][0]["record_id"]].append("final_application"),
        lambda d: d.update(final_answers_constructed=False),
        lambda d: d["limitations"].update(study_admission="READY"),
    ):
        changed = deepcopy(document); mutate(changed)
        changed["data_sha256"] = course.digest({k: v for k, v in changed.items() if k != "data_sha256"})
        with pytest.raises(ValueError, match="SOURCE_RECONSTRUCTION"):
            dev.validate_development(changed, exclusions=exclusions, topology_key=shape_key)


def test_no_final_panel_interface(exclusions, construction_guard):
    document = dev.build_development(exclusions, topology_key=shape_key)
    with pytest.raises(ValueError, match="PANEL_UNKNOWN"):
        dev.panel_tasks(document, "final_application")
