from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SCRIPT_PATH = SCRIPT_DIR / "build_mtc_v2_concrete_fixture.py"
SPEC = importlib.util.spec_from_file_location("build_mtc_v2_concrete_fixture", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
fixture_builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_builder
SPEC.loader.exec_module(fixture_builder)

from probe_dataset_common import load_labeled_scenarios  # noqa: E402


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "scenarios"
    / "matched_taxonomy_control_manifest_20260530.json"
)

BADGE_RE = re.compile(r"(\^[0-9])|(\bF[1-7]\|[TAfE]\b)|(\bF[1-7][TAfE]\b)")
MARKER_LIST_RE = re.compile(r"\b[A-Z][0-9]\s*:")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _payload(axis: str, *, rows_per_class: int = 3) -> dict:
    spec = fixture_builder._axis_spec(
        axis=axis,
        manifest=_manifest(),
        rows_per_class=rows_per_class,
        train_per_class=rows_per_class - 1,
        seed=12345,
    )
    return fixture_builder.build_fixture(spec)


def _prompt_ngrams(prompt: str, n: int = 5) -> set[tuple[str, ...]]:
    words = TOKEN_RE.findall(prompt.lower())
    if len(words) < n:
        return set()
    return {tuple(words[index : index + n]) for index in range(len(words) - n + 1)}


def _assert_no_split_reused_label_specific_ngrams(payload: dict, label_field: str) -> None:
    train_ngrams_by_label: defaultdict[str, set[tuple[str, ...]]] = defaultdict(set)
    test_ngrams_by_label: defaultdict[str, set[tuple[str, ...]]] = defaultdict(set)
    train_ngram_counts_by_label: defaultdict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    test_ngram_counts_by_label: defaultdict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    labels_by_ngram: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    ngram_counts: Counter[tuple[str, ...]] = Counter()

    for row in payload["records"]:
        label = row[label_field]
        ngrams = _prompt_ngrams(row["prompt"])
        target = train_ngrams_by_label if row["split"] == "train" else test_ngrams_by_label
        target_counts = (
            train_ngram_counts_by_label if row["split"] == "train" else test_ngram_counts_by_label
        )
        target[label].update(ngrams)
        for ngram in ngrams:
            target_counts[label][ngram] += 1
            labels_by_ngram[ngram].add(label)
            ngram_counts[ngram] += 1

    leaks: list[str] = []
    for label in sorted(train_ngrams_by_label):
        shared = train_ngrams_by_label[label] & test_ngrams_by_label[label]
        for ngram in sorted(shared):
            if (
                train_ngram_counts_by_label[label][ngram] >= 3
                and test_ngram_counts_by_label[label][ngram] >= 3
                and ngram_counts[ngram] >= 6
                and labels_by_ngram[ngram] == {label}
            ):
                leaks.append(f"{label}: {' '.join(ngram)}")

    assert leaks == []


def test_builds_balanced_40e_fixture_compatible_with_loader(tmp_path: Path) -> None:
    payload = _payload("40e")
    rows = payload["records"]

    class_counts = Counter(row["labels_40e"] for row in rows)
    operator_counts = Counter(row["labels_operator"] for row in rows)
    domain_counts = Counter(row["labels_domain"] for row in rows)

    assert payload["schema_version"] == "cas_harness_mtc_v2_concrete_fixture.v1"
    assert payload["seed"] == 12345
    assert payload["row_count"] == 120
    assert len(class_counts) == 40
    assert set(class_counts.values()) == {3}
    assert set(operator_counts) == set(f"^{index}" for index in range(10))
    assert set(domain_counts) == {"P", "C", "E", "O"}
    assert set(operator_counts.values()) == {12}
    assert set(domain_counts.values()) == {30}
    assert set(Counter(row["split"] for row in rows).values()) == {40, 80}

    first = rows[0]
    assert first["expected_cas_axes"]["element"] == first["labels_40e"]
    assert first["expected_cas_axes"]["operator"] == first["labels_operator"]
    assert first["expected_cas_axes"]["domain"] == first["labels_domain"]

    path = tmp_path / "mtc_v2_40e.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    scenarios = load_labeled_scenarios(path)

    assert len(scenarios) == 120
    assert {"operator", "domain", "element"}.issubset(scenarios[0].labels)


def test_builds_balanced_f28_fixture_with_expected_label_fields(tmp_path: Path) -> None:
    payload = _payload("f28")
    rows = payload["records"]

    class_counts = Counter(row["labels_f28"] for row in rows)
    drive_counts = Counter(row["labels_drive"] for row in rows)
    register_counts = Counter(row["labels_register"] for row in rows)

    assert payload["seed"] == 12345
    assert payload["row_count"] == 84
    assert len(class_counts) == 28
    assert set(class_counts.values()) == {3}
    assert set(drive_counts) == {f"F{index}" for index in range(1, 8)}
    assert set(register_counts) == {"T", "A", "f", "E"}
    assert set(drive_counts.values()) == {12}
    assert set(register_counts.values()) == {21}
    assert set(Counter(row["split"] for row in rows).values()) == {28, 56}

    first = rows[0]
    assert first["drive"] == first["labels_drive"]
    assert first["register"] == first["labels_register"]
    assert first["expected_cas_axes"]["foundation"] == first["labels_f28"]

    path = tmp_path / "mtc_v2_f28.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    scenarios = load_labeled_scenarios(path)

    assert len(scenarios) == 84
    assert {"drive", "register", "foundation"}.issubset(scenarios[0].labels)


def test_prompts_have_no_source_anchor_badges_or_marker_lists() -> None:
    for axis in ("40e", "f28"):
        payload = _payload(axis, rows_per_class=2)
        for row in payload["records"]:
            prompt = row["prompt"]
            lower = prompt.lower()

            assert "case card" not in lower
            assert "for this row" not in lower
            assert "reasoning notes:" not in lower
            assert "lenses:" not in lower
            assert "concerns:" not in lower
            assert BADGE_RE.search(prompt) is None
            assert MARKER_LIST_RE.search(prompt) is None
            for term in fixture_builder.BANNED_PROMPT_ANCHOR_TERMS:
                assert re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", lower) is None


def test_lexical_distractors_are_metadata_not_prompt_text() -> None:
    payload = _payload("40e", rows_per_class=2)

    for row in payload["records"]:
        metadata = row["metadata"]
        assert metadata["lexical_distractors"]
        assert metadata["lexical_distractor_rule"] == (
            "stored as metadata only; prompt prose stays natural"
        )
        assert row["lexical_pack_id"] == metadata["lexical_pack_id"]
        for distractor in metadata["lexical_distractors"]:
            assert distractor not in row["prompt"].lower()


def test_prompts_do_not_reuse_label_specific_phrases_across_splits() -> None:
    payload_40e = _payload("40e", rows_per_class=6)
    _assert_no_split_reused_label_specific_ngrams(payload_40e, "labels_operator")
    _assert_no_split_reused_label_specific_ngrams(payload_40e, "labels_domain")
    for row in payload_40e["records"]:
        row["control_label"] = (
            f"{row['control_semantic']['topic_40']}|{row['control_semantic']['frame_40']}"
        )
    _assert_no_split_reused_label_specific_ngrams(payload_40e, "control_label")

    payload_f28 = _payload("f28", rows_per_class=6)
    _assert_no_split_reused_label_specific_ngrams(payload_f28, "labels_drive")
    _assert_no_split_reused_label_specific_ngrams(payload_f28, "labels_register")
    for row in payload_f28["records"]:
        row["control_label"] = (
            f"{row['control_semantic']['topic_7']}|{row['control_semantic']['function_4']}"
        )
    _assert_no_split_reused_label_specific_ngrams(payload_f28, "control_label")


def test_visible_surface_semantics_are_independent_from_control_labels() -> None:
    payload = _payload("40e", rows_per_class=4)

    mismatches = [
        row
        for row in payload["records"]
        if row["control_semantic"]["topic_40"] != row["surface_semantic"]["topic_40"]
        or row["control_semantic"]["frame_40"] != row["surface_semantic"]["frame_40"]
    ]

    assert len(mismatches) >= int(len(payload["records"]) * 0.8)
    assert all(
        "independently rotated"
        in row["metadata"]["matched_control_prompt_policy"]
        for row in payload["records"]
    )


def test_seeded_output_is_deterministic() -> None:
    first = _payload("f28", rows_per_class=2)
    second = _payload("f28", rows_per_class=2)

    assert first == second
    assert first["content_sha256"] == second["content_sha256"]
