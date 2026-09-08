"""Pure checks of solved-demonstration/separate-application teaching material."""
import ast
from collections import Counter
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import re

import pytest

from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle import guided_application as guided, lesson_contract as v1
from cas_meta2.teaching_cycle.data import build_dataset


@pytest.fixture(scope="module")
def cases():
    return build_dataset()["splits"]["train"]


def test_v1_remains_the_original_answer_showing_renderer(cases):
    row = v1.make_cycle(cases[0])[0]
    assert row["schema"] == "cas-meta2-teaching-cycle-data/1"
    assert f"Worked answer: BIND{cases[0]['target_binding']}" in row["public"]["problem"]
    assert "demonstration" not in row


def test_demonstration_is_self_contained_and_same_through_all_seven_stages(cases):
    for case in cases:
        rows = guided.make_cycle(case)
        assert guided.validate_cycle(case, rows)
        assert tuple(row["stage"] for row in rows) == guided.STAGES
        assert all(row["schema"] == guided.SCHEMA for row in rows)
        assert all(row["demonstration"] == rows[0]["demonstration"] for row in rows)
        for row in rows:
            demo = row["demonstration"]
            assert guided.recover_demonstration(row["public"])["target_binding"] == demo["target_binding"]
            assert guided.recover_binding(row["public"]) == case["target_binding"]
            # The only BIND answer in public is explicitly the demonstration answer.
            assert re.findall(r"BIND[012]", row["public"]["problem"]) == [f"BIND{demo['target_binding']}"]
            assert "Apply the same rule to the actual observations" in row["public"]["problem"]
            assert row["public"]["observations"] == case["observations"]


def test_copying_or_fixed_inversion_of_demo_answer_is_not_a_solution(cases):
    pairs = Counter()
    layouts = set()
    for case in cases:
        demo = guided.make_cycle(case)[0]["demonstration"]
        pairs[(demo["target_binding"], case["target_binding"])] += 1
        layouts.add(tuple(demo["source_permutation"]))
    assert layouts == set(permutations((0, 1, 2)))
    assert len(pairs) == 9 and min(pairs.values()) >= 10
    correct_if_copied = sum(count for (demo, practice), count in pairs.items() if demo == practice)
    assert 0.20 <= correct_if_copied / len(cases) <= 0.45
    best_fixed_remap = max(sum(pairs[(demo, mapping[demo])] for demo in range(3))
                          for mapping in permutations((0, 1, 2)))
    assert best_fixed_remap / len(cases) <= 0.50


def test_layout_does_not_depend_on_requested_answer_or_family_id(cases):
    case = cases[0]
    permutations_seen = []
    for slot in range(3):
        variant = deepcopy(case)
        variant["target_binding"] = slot
        variant["requested_tag"] = next(row["tag"] for row in case["observations"] if row["slot"] == slot)
        variant["family_id"] = canonical_sha256({key: variant[key] for key in
                                                ("fixed_child", "requested_tag", "observations")})
        permutations_seen.append(guided.make_cycle(variant)[0]["demonstration"]["source_permutation"])
    assert permutations_seen[0] == permutations_seen[1] == permutations_seen[2]


@pytest.mark.parametrize("change", ["demo_target", "demo_tag", "public_answer", "practice", "mapping", "layout"])
def test_symbolic_and_canonical_checks_reject_changed_teaching(cases, change):
    case = cases[0]
    rows = guided.make_cycle(case)
    row = rows[0]
    if change == "demo_target":
        row["demonstration"]["target_binding"] = (row["demonstration"]["target_binding"] + 1) % 3
    elif change == "demo_tag":
        row["demonstration"]["observations"][0]["tag"] = "other parcel"
    elif change == "public_answer":
        target = row["demonstration"]["target_binding"]
        row["public"]["problem"] = row["public"]["problem"].replace(f"BIND{target}", f"BIND{(target + 1) % 3}")
    elif change == "practice":
        row["public"]["observations"][0]["values"][0] += 1.0
    elif change == "mapping":
        row["alignment"][0]["analogy"] = "unrelated role"
    else:
        row["demonstration"]["source_permutation"] = [0, 0, 0]
    with pytest.raises(guided.TeachingDataError):
        guided.validate_cycle(case, rows)


def test_both_controls_receive_the_same_solved_example(cases):
    case = cases[0]
    aligned = guided.make_cycle(case, curriculum="aligned")
    ordinary = guided.make_cycle(case, curriculum="ordinary")
    assert guided.validate_cycle(case, ordinary)
    for left, right in zip(aligned, ordinary):
        assert left["demonstration"] == right["demonstration"]
        assert left["public"]["problem"].split(" Worked demonstration,", 1)[1] == \
            right["public"]["problem"].split(" Worked demonstration,", 1)[1]
        assert right["delivery_kind"] == "ordinary_presentations"
        assert right["alignment"] == []


@pytest.mark.parametrize("assistance", ["faded", "none"])
def test_faded_and_none_do_not_solve_the_practice_or_demo(cases, assistance):
    rows = guided.make_cycle(cases[0], assistance=assistance)
    assert guided.validate_cycle(cases[0], rows)
    assert all(row["demonstration"] is None and "BIND" not in row["public"]["problem"] for row in rows)
    assert ("Role hint:" in rows[0]["public"]["problem"]) == (assistance == "faded")


def test_all_training_views_fit_lossless_public_input_and_no_heldout_fit(cases):
    tokenizer = guided.fit_tokenizer(cases)
    assert tokenizer.max_length == 512 and "[UNK]" not in tokenizer.vocabulary
    for case in cases:
        for record in guided.make_cycle(case):
            assert len(tokenizer.encode_public(record["public"])["ids"]) <= 512
            assert tokenizer.check_round_trip(record["public"])
    heldout = deepcopy(cases[0])
    heldout["split"] = "test_fresh"
    with pytest.raises(guided.TeachingDataError, match="TRAINING_CASE_REQUIRED"):
        guided.fit_tokenizer([heldout])
    with pytest.raises(guided.TeachingDataError, match="TEACHING_CYCLE_TRAIN_ONLY"):
        guided.make_cycle(heldout)


def test_worker_module_has_no_teacher_data_import():
    tree = ast.parse(Path(guided.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "data"
            assert all(alias.name != "data" for alias in node.names)
    assert not hasattr(guided, "build_dataset")
