"""Pure controlled-clause recognition: no legacy construction or neural calls."""
import builtins
from copy import deepcopy
from hashlib import sha256
import importlib.util
from itertools import permutations
import json
import sys

import pytest

from cas_meta2.typed_teaching import answers, focal, source


DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def no_numeric_or_legacy_construction(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def families():
    return source.training_families(expected_source_profile_digest=source.source_profile()["profile_digest"])


@pytest.fixture(scope="module")
def bank(families):
    return source.freeze_bank(families)


@pytest.fixture(scope="module")
def public(families, bank):
    return source.compile_source(families[0], bank=bank)["public"]


def query(public, text, focus=None):
    return answers.compile_query(public, kind="role_set", arguments={"focal_excerpt": text},
                                 focus_world_id=focus)


def line(name, payload):
    return focal.PREFIXES[name] + json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=False, allow_nan=False)


def payload(text):
    name = next(name for name, prefix in focal.PREFIXES.items() if text.startswith(prefix))
    return name, json.loads(text[len(focal.PREFIXES[name]):])


def test_module_import_is_guarded_before_initialization(monkeypatch):
    # Re-execute the actual source, rather than retrieve its already loaded
    # module. The qualified alias keeps relative imports in the guarded package.
    alias = "cas_meta2.typed_teaching._focal_guarded_initialization"
    assert alias not in sys.modules
    spec = importlib.util.spec_from_file_location(alias, focal.__file__)
    assert spec is not None and spec.loader is not None
    fresh = importlib.util.module_from_spec(spec)
    assert "GRAMMAR_SCHEMA" not in vars(fresh)
    original, seen = builtins.__import__, []
    def guard(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        seen.append(name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guard)
    sys.modules[alias] = fresh
    try:
        spec.loader.exec_module(fresh)
        assert seen  # Its import statements ran under the guard.
        assert fresh.grammar_profile.__module__ == alias
        assert fresh.grammar_profile() == focal.grammar_profile()
        assert fresh.grammar_profile()["static_account_roles"] == [5, 6]
        assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)
    finally:
        if sys.modules.get(alias) is fresh:
            del sys.modules[alias]
    assert alias not in sys.modules


@pytest.mark.parametrize("family_index", [0, 21, 43, 63])
@pytest.mark.parametrize("template", range(1, 7))
def test_public_authored_clauses_cover_six_roles_without_target_menu(families, bank, family_index, template):
    public = source.compile_source(families[family_index], bank=bank)["public"]
    before = source.canonical(public)
    text = focal.render_excerpt(public, template=template)
    q = query(public, text)
    checked = focal.derive_roles(public, q)
    assert checked["roles"] == ([5, 6] if template == 6 else [template])
    assert checked["status"] == ("AMBIGUOUS" if template == 6 else "UNIQUE")
    assert answers.answer_space(public, q)["inventory"]["role_ids"] == [1, 2, 3, 4, 5, 6]
    assert len(text.encode("utf-8")) <= answers.MAX_EXCERPT_BYTES
    assert "template" not in text and "face" not in text and "correct" not in text
    assert checked["witnesses"][0]["clause_sha256"] == sha256(text.encode()).hexdigest()
    assert checked["witnesses"][0]["source_digest"] == q["source_digest"]
    assert source.canonical(public) == before


def test_independent_recognition_does_not_call_authoring_or_private_helpers(public, monkeypatch):
    text = focal.render_excerpt(public, template=6)
    q = query(public, text)
    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE_OR_AUTHORING_ACCESS")
    for name in ("render_excerpt",):
        monkeypatch.setattr(focal, name, forbidden)
    for name in ("training_families", "compile_source", "source_profile", "_material"):
        monkeypatch.setattr(source, name, forbidden)
    assert focal.derive_roles(public, q)["roles"] == [5, 6]


def test_background_all_facts_do_not_classify_unmentioned_roles(public):
    neutral = line("reference", {"world_id": public["focus_world_id"]})
    result = focal.derive_roles(public, query(public, neutral))
    assert result["roles"] == [] and result["status"] == "INSUFFICIENT"
    assert len(public["worlds"]) == 64
    definition = focal.render_excerpt(public, template=1)
    assert focal.derive_roles(public, query(public, neutral + "\n" + definition))["roles"] == [1]


def test_combination_uses_role_union_and_preserves_each_clause_witness(public):
    texts = [focal.render_excerpt(public, template=template) for template in (1, 2, 3, 4, 5, 6)]
    checked = focal.derive_roles(public, query(public, "\n".join(texts)))
    assert checked["roles"] == [1, 2, 3, 4, 5, 6] and checked["status"] == "AMBIGUOUS"
    assert [row["clause_index"] for row in checked["witnesses"]] == list(range(6))
    assert focal.derive_roles(public, query(public, "\n".join(reversed(texts))))["roles"] == checked["roles"]


@pytest.mark.parametrize("template,mutate", [
    (1, lambda p: p.update(kind_ref=p["kind_ref"].replace("/kind", "/setting"))),
    (2, lambda p: p.update(participants=p["participants"][:-1])),
    (3, lambda p: p.update(target_world_id=p["source_world_id"])),
    (4, lambda p: p.update(pairs=p["pairs"][:-1])),
    (5, lambda p: p.update(nodes=[])),
    (6, lambda p: p.update(edges=p["edges"][:-1])),
])
def test_false_claims_refuse_instead_of_becoming_unlabelled(public, template, mutate):
    name, value = payload(focal.render_excerpt(public, template=template))
    mutate(value)
    with pytest.raises(focal.FocalContractError):
        focal.derive_roles(public, query(public, line(name, value)))


def test_correct_role_header_cannot_validate_wrong_edge_or_mapping(public):
    name, value = payload(focal.render_excerpt(public, template=6))
    edge = value["edges"][0]
    edge["source"], edge["target"] = edge["target"], edge["source"]
    value["edges"].sort(key=lambda e: (e["source"], e["target"]))
    with pytest.raises(focal.FocalContractError, match="FALSE_COMPLETE_ACCOUNT"):
        focal.derive_roles(public, query(public, line(name, value)))
    name, value = payload(focal.render_excerpt(public, template=4))
    value["pairs"][0]["target"], value["pairs"][1]["target"] = value["pairs"][1]["target"], value["pairs"][0]["target"]
    with pytest.raises(focal.FocalContractError, match="FALSE_MAPPING"):
        focal.derive_roles(public, query(public, line(name, value)))


def test_analogy_checks_domains_and_exact_graphs_independently(public):
    worlds = {w["world_id"]: w for w in public["worlds"]}
    focus = worlds[public["focus_world_id"]]
    different_shape = next(w for w in worlds.values() if len(w["nodes"]) != len(focus["nodes"])
                           and w["declarations"]["domain"] != focus["declarations"]["domain"])
    text = line("analogy", {"source_world_id": focus["world_id"], "target_world_id": different_shape["world_id"]})
    with pytest.raises(focal.FocalContractError, match="FALSE_SAME_PATTERN"):
        focal.derive_roles(public, query(public, text))
    same_domain = next(w for w in worlds.values() if w["world_id"] != focus["world_id"]
                       and w["declarations"]["domain"] == focus["declarations"]["domain"])
    text = line("analogy", {"source_world_id": focus["world_id"], "target_world_id": same_domain["world_id"]})
    with pytest.raises(focal.FocalContractError, match="FALSE_DIFFERENT_DOMAINS"):
        focal.derive_roles(public, query(public, text))


def test_isomorphism_helper_agrees_with_independent_permutation_reference(public):
    def exhaustive(a, b):
        an, bn = [n["ref"] for n in a["nodes"]], [n["ref"] for n in b["nodes"]]
        if len(an) != len(bn):
            return False
        be = {(e["source"], e["target"]) for e in b["contains"]}
        for order in permutations(bn):
            mapping = dict(zip(an, order))
            if {(mapping[e["source"]], mapping[e["target"]]) for e in a["contains"]} == be:
                return True
        return False
    worlds = public["worlds"]
    for left in worlds[:8]:
        for right in worlds[::4]:
            assert (focal._bijection(left, right) is not None) == exhaustive(left, right)


@pytest.mark.parametrize("bad", ["", "free text about a machine", "Source reference: {}\n", "Source reference: NaN",
    'Source reference: {"world_id":"a","world_id":"b"}', 'Source reference: {"world_id": "a"}',
    'Source reference: {"world_id":"a","template":1}', 'Source reference: {"world_id":[]}'])
def test_malformed_or_noncanonical_clauses_refuse(public, bad):
    with pytest.raises(ValueError):
        focal.derive_roles(public, query(public, bad))


def test_explicit_bounds_bad_scope_and_wrong_query_kind(public):
    text = line("reference", {"world_id": public["focus_world_id"]})
    with pytest.raises(ValueError, match="CLAUSE_BOUND"):
        focal.derive_roles(public, query(public, "\n".join([text] * 17)))
    with pytest.raises(ValueError, match="EXCERPT_BOUND"):
        query(public, "x" * (answers.MAX_EXCERPT_BYTES + 1))
    with pytest.raises(ValueError, match="ENCODING"):
        query(public, "\ud800")
    with pytest.raises(ValueError, match="ROLE_QUERY_REQUIRED"):
        focal.derive_roles(public, answers.compile_query(public, kind="definition"))
    other = next(w["world_id"] for w in public["worlds"] if w["world_id"] != public["focus_world_id"])
    with pytest.raises(ValueError, match="CLAUSE_FOCUS"):
        focal.derive_roles(public, query(public, line("reference", {"world_id": other})))
    copied = deepcopy(query(public, text))
    copied["face"] = 6
    with pytest.raises(ValueError, match="QUERY_FIELDS"):
        focal.derive_roles(public, copied)


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", 0, 7, None])
def test_author_template_has_exact_integer_domain(public, bad):
    with pytest.raises(focal.FocalContractError, match="TEMPLATE"):
        focal.render_excerpt(public, template=bad)


def test_author_refuses_missing_partner_and_unused_partner(public, families):
    alone = source.compile_source(families[0], bank=source.freeze_bank([families[0]]))["public"]
    for template in (3, 4):
        with pytest.raises(focal.FocalContractError, match="NO_SUITABLE"):
            focal.render_excerpt(alone, template=template)
    with pytest.raises(focal.FocalContractError, match="UNUSED_COMPARISON"):
        focal.render_excerpt(public, template=1, comparison_world_id=public["focus_world_id"])


def test_explicit_focus_is_bound_by_query_without_changing_public_current_focus(public):
    before = source.canonical(public)
    other = next(w["world_id"] for w in public["worlds"] if w["world_id"] != public["focus_world_id"])
    text = focal.render_excerpt(public, template=6, focus_world_id=other)
    assert focal.derive_roles(public, query(public, text, focus=other))["roles"] == [5, 6]
    with pytest.raises(focal.FocalContractError, match="CLAUSE_FOCUS"):
        focal.derive_roles(public, query(public, text))
    assert source.canonical(public) == before


def test_largest_dag_account_fits_and_never_asserts_process(families):
    family = deepcopy(families[0])
    family["labels"] = tuple("node" + str(i) for i in range(10))
    family["branches"] = tuple({"source": a, "target": b}
        for i, a in enumerate(family["labels"]) for b in family["labels"][i + 1:])
    public = source.compile_source(family, bank=source.freeze_bank([family]))["public"]
    text = focal.render_excerpt(public, template=6)
    assert len(text.encode()) < answers.MAX_EXCERPT_BYTES
    assert len(payload(text)[1]["edges"]) == 45
    assert focal.derive_roles(public, query(public, text))["roles"] == [5, 6]
    assert public["worlds"][0]["branch_order"]["process_order"] is None
    profile = focal.grammar_profile()
    assert profile["process_order_inferred"] is False
    assert profile["interaction_facts_inferred"] is False
    assert "NOT_UNRESTRICTED" in profile["recognition_scope"]
    profile["clauses"][0]["roles"].append(6)
    assert focal.grammar_profile()["clauses"][0]["roles"] == [1]
