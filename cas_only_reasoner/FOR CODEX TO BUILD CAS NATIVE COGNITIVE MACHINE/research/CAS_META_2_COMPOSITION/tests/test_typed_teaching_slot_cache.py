"""Exact public-plan reuse; no teacher, model, provider or curriculum rebuild."""
import builtins
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

import pytest

from cas_meta2.typed_teaching import answers, course, slots, source

ROOT = Path(__file__).resolve().parents[3]
COURSE_PATH = ROOT / "records/typed_course_001/checks_002/public_course.json"
COURSE_SHA = "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987"
DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def pure_guard(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.endswith(".checker") or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE_OR_FULL_COURSE_CONSTRUCTION")
    monkeypatch.setattr(builtins, "__import__", guarded)
    for name in ("compile_course", "prepare_course", "derive_targets_from_seal", "_worked_target"):
        monkeypatch.setattr(course, name, forbidden)
    monkeypatch.setattr(course.focal, "derive_roles", forbidden)
    monkeypatch.setattr(course.focal, "render_excerpt", forbidden)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)
    assert "cas_meta2.typed_teaching.checker" not in sys.modules


@pytest.fixture(scope="module")
def frozen():
    raw = COURSE_PATH.read_bytes()
    assert sha256(raw).hexdigest() == COURSE_SHA
    return json.loads(raw)


def packet_from_row(frozen, row):
    # Same exact retained public projection as course.model_packet. Both
    # compilers independently validate these bytes; no source generation.
    return {"source": deepcopy(course._public(frozen["bank"], row["source_world_id"])), "record": deepcopy(row)}


@pytest.fixture(scope="module")
def packet(frozen):
    row = next(r for r in frozen["registry"] if r["query"]["kind"] == "correspondence")
    result = packet_from_row(frozen, row)
    assert result == course.model_packet(frozen, row["record_id"])
    return result


def test_all_564_cached_and_uncached_plans_are_exact(frozen, record_property):
    started = time.perf_counter()
    kinds, ordered = set(), []
    for row in frozen["registry"]:
        packet = packet_from_row(frozen, row)
        uncached = slots._compile_slots_uncached(packet)
        cached = slots.compile_slots(packet)
        assert source.canonical(uncached) == source.canonical(cached)
        assert uncached == cached and type(uncached) is type(cached) is dict
        kinds.add(cached["kind"])
        ordered.append([row["record_id"], cached["plan_digest"]])
    assert len(ordered) == 564 and kinds == set(answers.RULES)
    record_property("exact_registry_comparisons", 564)
    record_property("retained_presentations", len(frozen["presentations"]))
    record_property("all_eight_kinds", sorted(kinds))
    record_property("comparison_seconds", time.perf_counter() - started)
    record_property("ordered_plan_digests_sha256", source.digest(ordered))
    record_property("cache_info", slots.slot_cache_info())


def test_decoder_and_validation_share_cache(packet, monkeypatch):
    cache = slots._SlotCache()
    monkeypatch.setattr(slots, "_SLOT_CACHE", cache)
    plan = slots.compile_slots(packet)
    scores = {s["slot_id"]: {symbol: 0.0 for symbol in s["symbols"]} for s in plan["slots"]}
    decisions = slots.score_decisions(packet, scores)
    slots.assemble_answer(packet, decisions)
    slots.validate_plan(packet, plan)
    assert cache.info()["compiles"] == 1 and cache.info()["hits"] == 3


def test_output_and_input_mutations_cannot_poison_cache(packet):
    cache = slots._SlotCache()
    mutable = deepcopy(packet)
    first = cache.compile(mutable)
    original = source.canonical(first)
    first["slots"][0]["symbols"].append("BAD")
    first["profile"]["status"] = "BAD"
    mutable["record"]["instruction"] = "BAD"
    assert source.canonical(cache.compile(packet)) == original
    with pytest.raises(ValueError):
        cache.compile(mutable)
    assert source.canonical(cache.compile(packet)) == original


@pytest.mark.parametrize("mutation", ["instruction", "bank_label", "private_extra", "stale_id"])
def test_entire_packet_invalidation_and_error_not_cached(packet, mutation):
    cache = slots._SlotCache()
    cache.compile(packet)
    altered = deepcopy(packet)
    if mutation == "instruction": altered["record"]["instruction"] = "changed"
    elif mutation == "bank_label": altered["source"]["worlds"][0]["nodes"][0]["label"] = "Changed"
    elif mutation == "private_extra": altered["record"]["correct"] = True
    else: altered["record"]["record_id"] = "typed-input-" + "a" * 64
    for _ in range(2):
        with pytest.raises(ValueError): cache.compile(altered)
    assert cache.info()["hits"] == 0 and cache.info()["compiles"] == 3 and cache.info()["entries"] == 1


@pytest.mark.parametrize("mutation", ["tuple", "float", "custom_dict", "cycle", "depth", "nonstring_key"])
def test_aliases_and_unbounded_tree_refused_before_lookup(packet, mutation):
    cache = slots._SlotCache()
    cache.compile(packet)
    altered = deepcopy(packet)
    if mutation == "tuple": altered["source"]["worlds"] = tuple(altered["source"]["worlds"])
    elif mutation == "float": altered["record"]["extra"] = 1.0
    elif mutation == "custom_dict":
        class Custom(dict): pass
        altered["record"] = Custom(altered["record"])
    elif mutation == "cycle": altered["record"]["cycle"] = altered
    elif mutation == "nonstring_key": altered["record"][0] = None
    else:
        nested = None
        for _ in range(34): nested = [nested]
        altered["record"]["deep"] = nested
    before = cache.info()
    with pytest.raises(ValueError): cache.compile(altered)
    assert cache.info() == before


@pytest.mark.parametrize("size", [5000, 16384])
def test_long_valid_focal_excerpt_preserves_uncached_admission(frozen, size):
    row = next(r for r in frozen["registry"] if r["query"]["kind"] == "role_set")
    packet = packet_from_row(frozen, row)
    packet["record"]["query"] = answers.compile_query(packet["source"], kind="role_set", arguments={"focal_excerpt": "x" * size})
    packet["record"]["record_id"] = "typed-input-" + source.digest({k: v for k, v in packet["record"].items() if k != "record_id"})
    uncached = slots._compile_slots_uncached(packet)
    cache = slots._SlotCache()
    assert cache.compile(packet) == uncached
    assert cache.compile(packet) == uncached and cache.info()["hits"] == 1


def revised_profile(original):
    result = original()
    result["synthetic_cache_profile_revision"] = 1
    result["profile_digest"] = source.digest({k: v for k, v in result.items() if k != "profile_digest"})
    return result


def test_profile_change_recompiles_and_lru_evicts(packet, monkeypatch):
    cache = slots._SlotCache(max_entries=1)
    original = slots.profile
    first = cache.compile(packet)
    changed = revised_profile(original)
    monkeypatch.setattr(slots, "profile", lambda: deepcopy(changed))
    second = cache.compile(packet)
    assert second["profile"] == changed and first != second
    assert cache.info()["evictions"] == 1 and cache.info()["entries"] == 1 and cache.info()["compiles"] == 2
    monkeypatch.setattr(slots, "profile", original)
    assert cache.compile(packet) == first and cache.info()["evictions"] == 2


def test_profile_change_during_compile_is_not_retained(packet, monkeypatch):
    original, original_profile = slots._compile_slots_uncached, slots.profile
    def changing(value):
        result = original(value)
        changed = revised_profile(original_profile)
        monkeypatch.setattr(slots, "profile", lambda: changed)
        return result
    monkeypatch.setattr(slots, "_compile_slots_uncached", changing)
    cache = slots._SlotCache()
    with pytest.raises(ValueError, match="CACHE_CONTEXT_CHANGED"): cache.compile(packet)
    assert cache.info()["entries"] == 0


def test_byte_limit_bypasses_without_admission_change(packet):
    cache = slots._SlotCache(max_serialized_bytes=1)
    result = cache.compile(packet)
    assert result == slots._compile_slots_uncached(packet)
    assert cache.info()["entries"] == 0 and cache.info()["retained_serialized_bytes"] == 0
    assert cache.info()["oversize_bypasses"] == 1


@pytest.mark.parametrize("kwargs", [{"max_entries": True}, {"max_entries": 0}, {"max_entries": 1025},
    {"max_serialized_bytes": 1.0}, {"max_serialized_bytes": 0}, {"max_serialized_bytes": 256 * 1024 ** 2 + 1}])
def test_cache_bounds(kwargs):
    with pytest.raises(ValueError): slots._SlotCache(**kwargs)


def test_full_byte_comparison_protects_digest_key(packet):
    cache = slots._SlotCache()
    cache.compile(packet)
    key = next(iter(cache.entries))
    raw, profile, plan, size = cache.entries[key]
    cache.entries[key] = (raw + b" ", profile, plan, size)
    with pytest.raises(ValueError, match="CACHE_COLLISION"): cache.compile(packet)


def test_cache_clear_releases_and_resets_counts(packet, monkeypatch):
    monkeypatch.setattr(slots, "_SLOT_CACHE", slots._SlotCache())
    slots.compile_slots(packet)
    slots.clear_slot_cache()
    info = slots.slot_cache_info()
    assert info["entries"] == info["retained_serialized_bytes"] == info["compiles"] == info["hits"] == 0
