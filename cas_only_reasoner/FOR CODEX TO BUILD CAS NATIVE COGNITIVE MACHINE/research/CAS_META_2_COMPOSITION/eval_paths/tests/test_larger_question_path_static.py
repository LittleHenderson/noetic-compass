"""Torch-free checks of the larger-question path (v0.1). Pure Python: no torch, no learner, no course load.

Run either way:
    python -B -m pytest -q eval_paths/tests/test_larger_question_path_static.py     (from research/CAS_META_2_COMPOSITION)
    python -B eval_paths/tests/test_larger_question_path_static.py

What these checks can and cannot show. They show that the routing, the slot plans, the decoder, the checker and
the fixtures behave as the report says, WITHOUT a model. They cannot show that a trained container produces an
answer: that needs torch and a GPU, and is `t4_larger_question_checks.py`, to run on AWS.
"""
import ast
import hashlib
import itertools
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
EVAL = HERE.parent
RESEARCH = EVAL.parent
CNCM = RESEARCH.parents[1]
sys.path.insert(0, str(RESEARCH))

from cas_meta2.typed_teaching import answers, checker, checker_v2, course, slots, slots_v2, source  # noqa: E402
from eval_paths import larger_question_fixtures as fixtures  # noqa: E402
from eval_paths import larger_question_scope as scope  # noqa: E402

TYPED = RESEARCH / "cas_meta2" / "typed_teaching"
# The committed fixture file's sha256, as written by `larger_question_fixtures.py --write`.
FIXTURE_FILE_SHA256 = "7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3"
# The D-1 ACCEPTED anchors, copied from `records/helm_eval_design_20260923/d1_acceptance/D1_ACCEPTANCE_RESULT.md`
# on `research/helm-integration-20260923`, independently of the module's own copy.
D1_ANCHORS = {"checker_v2.py": "d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258",
              "answers_v2.py": "b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5",
              "slots_v2.py": "7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb"}

DOCUMENT, PACKETS = fixtures.load()
ROWS = {row["fixture_id"]: row for row in DOCUMENT["fixtures"]}
LARGER_IDS = sorted(key for key, row in ROWS.items() if "expected_refusal" not in row)
REFUSED_IDS = sorted(key for key, row in ROWS.items() if "expected_refusal" in row)


def _raises(function, *args):
    try:
        function(*args)
    except Exception as error:  # noqa: BLE001 - the test reads the error type and message
        return error
    return None


def _focus(packet):
    return next(w for w in packet["source"]["worlds"] if w["world_id"] == packet["source"]["focus_world_id"])


def _world(packet, world_id):
    return next(w for w in packet["source"]["worlds"] if w["world_id"] == world_id)


def _values(target):
    return sorted(source.canonical(answer["value"]) for answer in target["admissible_answers"])


# ---------------------------------------------------------------------------------------------- sources
def test_protected_sources_match_pins_and_d1_anchors():
    observed = scope.verify_source_pins()
    assert set(observed) == set(scope.PROTECTED_SOURCE_LF_SHA256)
    assert {name: observed[name] for name in D1_ANCHORS} == D1_ANCHORS == scope.D1_ACCEPTED_LF_SHA256


def test_no_protected_file_mentions_this_folder():
    for name in scope.PROTECTED_SOURCE_LF_SHA256:
        assert b"eval_paths" not in (TYPED / name).read_bytes(), name


def test_eval_paths_is_outside_the_training_inventory():
    """The launcher chain: typed_pointer_launch -> pointer_contract -> practice -> matched -> worker_contract."""
    launch = (RESEARCH / "aws" / "typed_pointer_launch.py").read_text(encoding="utf-8")
    assert "from cas_meta2.typed_teaching import pointer_contract as contract" in launch
    assert "rows = contract.input_inventory(PROJECT if root is None else root)" in launch
    pointer = (TYPED / "pointer_contract.py").read_text(encoding="utf-8")
    assert "rows = [*practice.input_inventory(root), *_checkpoint_rows(root)]" in pointer
    practice = (TYPED / "practice_contract.py").read_text(encoding="utf-8")
    assert "input_inventory, material_inputs = matched.input_inventory, matched.material_inputs" in practice
    matched = (TYPED / "matched_contract.py").read_text(encoding="utf-8")
    assert "rows = baseline.input_inventory(root)" in matched
    tree = ast.parse((TYPED / "worker_contract.py").read_bytes())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "input_inventory")
    loops = [node for node in ast.walk(function) if isinstance(node, ast.For)
             and isinstance(node.target, ast.Name) and node.target.id == "prefix"]
    assert len(loops) == 1
    prefixes = ast.literal_eval(loops[0].iter)
    assert prefixes == ("cncm", "research/CAS_META_2_COMPOSITION/cas_meta2")
    ours = [path.relative_to(CNCM).as_posix() for path in EVAL.rglob("*") if path.is_file()]
    assert ours and all(path.startswith("research/CAS_META_2_COMPOSITION/eval_paths/") for path in ours)
    assert not any(path.startswith(prefix + "/") for path in ours for prefix in prefixes)


# ---------------------------------------------------------------------------------------------- fixtures
def test_fixture_file_reproduces_byte_for_byte():
    raw = fixtures.FIXTURE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_FILE_SHA256
    assert b"\r\n" not in raw
    document, packets = fixtures.build()
    assert fixtures.render(document) == raw
    assert {key: fixtures.packet_sha256(value) for key, value in packets.items()} == \
        {key: fixtures.packet_sha256(value) for key, value in PACKETS.items()}


def test_every_fixture_packet_is_a_valid_closed_packet_with_no_supports():
    assert len(PACKETS) == len(ROWS) == 41
    for key, packet in PACKETS.items():
        assert course.validate_model_packet(packet) == packet
        assert packet["record"]["supports"] == [], key
        assert fixtures.packet_sha256(packet) == ROWS[key]["packet_sha256"]


def test_every_kind_is_covered_at_five_and_at_six_nodes():
    covered = {(ROWS[key]["kind"], len(_focus(PACKETS[key])["nodes"])) for key in LARGER_IDS}
    for kind in answers.RULES:
        assert (kind, 5) in covered and (kind, 6) in covered, kind
    rules = {ROWS[key]["rule"] for key in LARGER_IDS if ROWS[key]["kind"] == "reach"}
    assert rules == set(answers.RULES["reach"])


def test_fixture_shapes_are_recorded_for_custody():
    for name, row in DOCUMENT["shapes"].items():
        n, edges = fixtures.SHAPES[name]
        assert row["canonical_form"] == fixtures.canonical_form(n, edges)
    for key in LARGER_IDS:
        for world in PACKETS[key]["source"]["worlds"]:
            assert len(world["nodes"]) <= 6
    used = {row["shape"] for key, row in DOCUMENT["worlds"].items()
            if any(ROWS[f]["focus"] == key for f in LARGER_IDS)}
    assert all(DOCUMENT["shapes"][shape]["max_degree"] <= 4 for shape in used)


# ---------------------------------------------------------------------------------------------- routing
def test_routes_of_the_fixtures():
    for key in LARGER_IDS:
        assert scope.route(PACKETS[key]) == scope.LARGER, key
    for key in REFUSED_IDS:
        error = _raises(scope.route, PACKETS[key])
        assert isinstance(error, scope.LargerPathRefusal) and error.code == ROWS[key]["expected_refusal"], key
        assert str(error).startswith("LARGER_PATH_REFUSED:" + error.code)


def test_every_historical_course_packet_takes_the_original_route():
    """Registry packets carry exactly the frozen training bank (`course.py:86-87`, `:156-163`)."""
    bank = fixtures.frozen_training_bank()
    shape = scope.packet_shape({"source": {"worlds": bank["worlds"]}})
    assert shape == {"world_count": 64, "max_nodes": 4, "max_degree": 3}
    focus = bank["worlds"][0]
    public = {"focus_world_id": focus["world_id"], "worlds": bank["worlds"], "bank": bank["bank"]}
    packet = fixtures._packet(public, "definition", None, {}, "CUBE_FACE_1")
    assert scope.route(packet) == scope.ORIGINAL
    assert scope.compile_plan(packet) == (scope.ORIGINAL, slots.compile_slots(packet))


def test_malformed_packets_are_left_to_the_original_validators():
    for packet in ({}, {"source": {}}, {"source": {"worlds": "x"}}, {"source": {"worlds": [{"nodes": []}]}}):
        assert scope.route(packet) == scope.ORIGINAL
        assert _raises(slots.compile_slots, packet) is not None


def test_refusal_comes_first_on_every_entry_point():
    for key in REFUSED_IDS:
        packet, code = PACKETS[key], ROWS[key]["expected_refusal"]
        for call in (lambda: scope.compile_plan(packet), lambda: scope.decode(packet, {}),
                     lambda: scope.grade(packet, {}), lambda: scope.target(packet)):
            error = _raises(call)
            assert isinstance(error, scope.LargerPathRefusal) and error.code == code, key


def test_without_the_new_route_seven_node_questions_would_be_answered_silently():
    """The frozen compiler and checker accept a 7-node parts question: the refusal is this path's policy."""
    packet = PACKETS["R01"]
    plan = slots.compile_slots(packet)
    assert len(plan["slots"]) == 7
    target = checker.derive_target(packet["source"], packet["record"]["query"])
    assert len(target["admissible_answers"]) == 1
    for module in (checker, checker_v2):
        error = _raises(module.derive_target, PACKETS["R02"]["source"], PACKETS["R02"]["record"]["query"])
        assert str(error) == "TYPED_CHECKER_ISOMORPHISM_BOUND"


# ---------------------------------------------------------------------------------------------- slot plans
def test_frozen_compiler_refuses_exactly_the_larger_correspondence_questions():
    for key in LARGER_IDS:
        packet, query = PACKETS[key], PACKETS[key]["record"]["query"]
        sizes = [len(_focus(packet)["nodes"])]
        if query["kind"] == "correspondence":
            sizes.append(len(_world(packet, query["arguments"]["target_world_id"])["nodes"]))
        new = slots_v2.compile_slots(packet)
        if query["kind"] == "correspondence" and max(sizes) > 4:
            assert str(_raises(slots.compile_slots, packet)) == "TYPED_PERMUTATION_BOUND", key
            assert new["profile"]["schema"] == "cas.typed-teaching-slot-profile/0.2"
            expected = ROWS[key]["design_facts"]["syntactic_candidates"]
            assert len(new["correspondence_candidates"]) == expected == (1 + math.factorial(sizes[0])
                                                                         if len(set(sizes)) == 1 else 1)
        else:
            assert source.canonical(slots.compile_slots(packet)) == source.canonical(new), key
            assert new["profile"]["schema"] == "cas.typed-teaching-slot-profile/0.1"
        assert scope.compile_plan(packet) == (scope.LARGER, new)


def test_kind_scope_table_matches_behaviour():
    by_kind = {}
    for key in LARGER_IDS:
        if ROWS[key]["bank"] == "MAIN" and len(_focus(PACKETS[key])["nodes"]) >= 5:
            by_kind.setdefault(ROWS[key]["kind"], []).append(key)
    assert set(by_kind) == set(scope.KIND_SCOPE)
    for kind, keys in by_kind.items():
        claim = scope.KIND_SCOPE[kind]
        for key in keys:
            packet = PACKETS[key]
            public, query = packet["source"], packet["record"]["query"]
            compiled = _raises(slots.compile_slots, packet)
            if claim["old_slot_compiler_at_5_6"] == "COMPILES":
                assert compiled is None, key
            else:
                assert str(compiled) == "TYPED_PERMUTATION_BOUND", key
            frozen = _raises(checker.derive_target, public, query)
            if claim["old_checker_at_5_6"] == "GRADES":
                assert frozen is None, key
            else:
                assert str(frozen) == "TYPED_CHECKER_ISOMORPHISM_BOUND", key
            assert _raises(checker_v2.derive_target, public, query) is None, key
            if claim["checker_v2_versus_frozen"] == "IDENTICAL_CODE_PATH":
                a = checker.derive_target(public, query)
                b = checker_v2.derive_target(public, query)
                assert a["admissible_answers"] == b["admissible_answers"] and a["witnesses"] == b["witnesses"]


# ---------------------------------------------------------------------------------------------- gold
def test_checker_v2_gold_equals_the_independent_plain_graph_answers():
    for key in LARGER_IDS:
        target = scope.target(PACKETS[key])
        assert target["checker_profile"]["schema"] == "cas.typed-teaching-semantic-profile/0.2"
        expected = sorted(source.canonical(value) for value in ROWS[key]["expected_values"])
        assert _values(target) == expected, key


def test_genuine_no_match_and_no_path_cases():
    for key, candidates in (("F07", 121), ("F20", 721)):
        target = scope.target(PACKETS[key])
        assert _values(target) == [source.canonical({"pairs": [], "status": "NO_MATCH"})]
        assert target["coverage"]["reason"] == "NO_EDGE_PRESERVING_BIJECTION"
        assert target["coverage"]["permutations_checked"] == candidates - 1
        assert ROWS[key]["design_facts"]["same_degree_counts"] is True
    for key in ("F05", "F18"):
        assert _values(scope.target(PACKETS[key])) == [source.canonical({"world_id": None})]
        assert ROWS[key]["design_facts"]["same_degree_decoys_in_bank"], key
    decisions = {row["world_id"]: row for row in scope.target(PACKETS["F18"])["coverage"]["decisions"]}
    twin = DOCUMENT["worlds"]["W6B_P2"]["world_id"]
    assert decisions[twin]["reason"] == "SAME_DECLARED_DOMAIN"
    for key in ("F12", "F25"):
        packet = PACKETS[key]
        target = scope.target(packet)
        assert _values(target) == [source.canonical({"state": "ABSENT", "via": None})]
        part = packet["record"]["query"]["arguments"]["part"]
        assert part in {node["ref"] for node in _focus(packet)["nodes"]}
        assert part not in target["witnesses"][0]["evidence"]["reachable_nodes_including_start"]


def test_colour_refinement_census_at_five_and_six_nodes():
    """Class counts match the known totals (267 and 5647 weakly connected DAG classes), and D-1's 105."""
    from eval_paths import colour_refinement_census as census
    five, six = census.census(5), census.census(6)
    assert (five["weakly_connected_classes"], five["classes_with_every_degree_at_most_4"],
            five["degree_colliding_classes"], five["same_degree_non_isomorphic_pairs"]) == (267, 267, 105, 116)
    assert (six["weakly_connected_classes"], six["classes_with_every_degree_at_most_4"],
            six["degree_colliding_classes"], six["same_degree_non_isomorphic_pairs"]) == (5647, 5074, 3996, 12588)
    assert five["pairs_colour_refinement_cannot_separate"] == six["pairs_colour_refinement_cannot_separate"] == 0
    # The 64-answer cap of checker v2 never binds on a connected in-scope shape: at most 24 and 48 self-maps.
    assert (five["most_self_maps_of_any_kept_shape"], six["most_self_maps_of_any_kept_shape"]) == (24, 48)
    assert six["most_self_maps_of_any_kept_shape"] <= checker_v2.MAX_ADMISSIBLE_ANSWERS


def test_same_degree_pairs_differ_in_wiring():
    for pair in DOCUMENT["same_degree_pairs"]:
        a, b = fixtures.SHAPES[pair["left"]], fixtures.SHAPES[pair["right"]]
        assert pair["degree_multisets_equal"] is True and fixtures.degree_multiset(*a) == fixtures.degree_multiset(*b)
        assert pair["isomorphic"] is False and not fixtures.isomorphisms(a, b)
        assert pair["colour_refinement_distinguishes"] == fixtures.colour_refinement_distinguishes(a, b) is True


# ---------------------------------------------------------------------------------------------- decoding
def _oracle_scores(plan, value, strength=10.0):
    """Scores that favour exactly one answer VALUE, built from the plan's own aliases and symbols."""
    alias = {node["ref"]: node["alias"] for world in plan["aliases"]["worlds"] for node in world["nodes"]}
    world_alias = {world["world_id"]: world["alias"] for world in plan["aliases"]["worlds"]}
    scores = {}
    for slot in plan["slots"]:
        field, coordinates = slot["field"], slot["coordinates"]
        if field == "role":
            wanted = "PRESENT" if coordinates[0] in value["roles"] else "ABSENT"
        elif field == "whole":
            wanted = alias[value["whole"]]
        elif field in ("kind_ref", "function_ref", "setting_ref"):
            wanted = world_alias[value[field].split("/decl/")[0]]
        elif field == "participant":
            wanted = "PRESENT" if coordinates[0] in value["participants"] else "ABSENT"
        elif field == "world_id":
            wanted = "NO_MATCH" if value["world_id"] is None else world_alias[value["world_id"]]
        elif field == "node":
            wanted = "PRESENT" if coordinates[0] in value["nodes"] else "ABSENT"
        elif field == "edge":
            wanted = "PRESENT" if {"source": coordinates[0], "target": coordinates[1]} in value["edges"] else "ABSENT"
        elif field == "reach":
            wanted = value["state"] if value["state"] != "VIA" else "VIA_" + alias[value["via"]]
        elif field == "mode":
            wanted = value["status"]
        elif field == "mapping_target":
            pairs = {pair["source"]: pair["target"] for pair in value["pairs"]}
            wanted = alias[pairs[coordinates[0]]] if coordinates[0] in pairs else None
        else:
            raise AssertionError(field)
        assert wanted is None or wanted in slot["symbols"], (field, wanted)
        scores[slot["slot_id"]] = {symbol: (strength if symbol == wanted else 0.0) for symbol in slot["symbols"]}
    return scores


def test_every_admissible_answer_can_be_decoded_from_the_slot_plan():
    """The heads' output space can express every gold answer at 5 and 6 nodes, and it grades as correct."""
    for key in LARGER_IDS:
        packet = PACKETS[key]
        path, plan = scope.compile_plan(packet)
        for answer in scope.target(packet)["admissible_answers"][:2]:
            decoded_path, _decisions, decoded = scope.decode(packet, _oracle_scores(plan, answer["value"]))
            assert decoded_path == path == scope.LARGER
            assert decoded == answer, key
            grade = scope.grade(packet, decoded)
            assert grade["correct"] is True and grade["checker_module"].endswith("checker_v2"), key


def test_arbitrary_scores_decode_to_well_formed_answers_that_grade():
    for key in LARGER_IDS:
        packet = PACKETS[key]
        _, plan = scope.compile_plan(packet)
        scores = {}
        for slot in plan["slots"]:
            row = {}
            for symbol in slot["symbols"]:
                raw = hashlib.sha256((key + "|" + slot["slot_id"] + "|" + symbol).encode()).digest()
                row[symbol] = int.from_bytes(raw[:4], "big") / 2 ** 32 * 6.0 - 3.0
            scores[slot["slot_id"]] = row
        _, _, answer = scope.decode(packet, scores)
        answers.validate_answer(packet["source"], packet["record"]["query"], answer)
        grade = scope.grade(packet, answer)
        assert type(grade["correct"]) is bool and grade["route"] == scope.LARGER


# ---------------------------------------------------------------------------------------------- learner copy
def _method(path, class_name, method_name):
    tree = ast.parse(pathlib.Path(path).read_bytes())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


def _without_docstring(body):
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) \
            and isinstance(first.value.value, str):
        return body[1:]
    return body


def test_graph_larger_is_the_original_graph_with_only_the_slot_module_swapped():
    original = _without_docstring(_method(TYPED / "pointer_learner.py", "PointerCourseLearner", "_graph").body)
    copy = _without_docstring(_method(EVAL / "larger_question_learner.py", "LargerQuestionPointerLearner",
                                      "_graph_larger").body)
    assert len(original) == len(copy)
    swapped = [index for index, (a, b) in enumerate(zip(original, copy)) if ast.dump(a) != ast.dump(b)]
    assert len(swapped) == 1
    a, b = original[swapped[0]], copy[swapped[0]]
    assert isinstance(a, ast.ImportFrom) and a.level == 1 and a.module is None and [n.name for n in a.names] == ["slots"]
    assert isinstance(b, ast.Assign) and ast.unparse(b) == "slots = scope.slot_module(scope.LARGER)"


def test_learner_module_binds_every_name_the_copied_body_reads():
    method = _method(TYPED / "pointer_learner.py", "PointerCourseLearner", "_graph")
    read = {node.id for node in ast.walk(method) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    stored = {node.id for node in ast.walk(method) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
    import builtins
    free = read - stored - {"self", "packet", "torch", "slots"} - set(dir(builtins))
    assert "GraphForward" in free and "require" in free and "PREDICTION_FIELD_SET" in free
    tree = ast.parse((EVAL / "larger_question_learner.py").read_bytes())
    bound = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module in ("cas_meta2.typed_teaching.pointer_learner",
                                                                 "cas_meta2.typed_teaching"):
            bound |= {alias.asname or alias.name for alias in node.names}
    assert free <= bound, free - bound


def test_subclass_dispatch_and_inference_only_guards():
    graph = _method(EVAL / "larger_question_learner.py", "LargerQuestionPointerLearner", "_graph")
    text = ast.unparse(graph)
    assert text.index("path = scope.route(packet)") < text.index("super()._graph(packet)")
    assert "if path == scope.ORIGINAL:" in text and "self._graph_larger(packet)" in text
    for name in ("stage_batch", "train_sealed_batch"):
        body = ast.unparse(_method(EVAL / "larger_question_learner.py", "LargerQuestionPointerLearner", name))
        assert "raise scope.LargerPathRefusal('INFERENCE_ONLY'" in body


def test_container_path_calls_the_original_steps_in_the_original_order():
    def calls(function):
        """Called names in SOURCE order (line, column), not `ast.walk`'s breadth-first order."""
        rows = []
        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                target = node.func
                name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
                rows.append((node.lineno, node.col_offset, name))
        return [name for _, _, name in sorted(rows)]
    order = ["compile_slots", "read_packet", "GraphForward", "head_logits", "_scalar_scores", "_logit_rows",
             "score_decisions", "assemble_answer"]
    original = [name for name in calls(_method(TYPED / "pointer_learner.py", "PointerCourseLearner", "_graph"))
                if name in order]
    tree = ast.parse((EVAL / "larger_question_learner.py").read_bytes())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "predict_packet")
    ours = [name for name in calls(function) if name in order]
    assert original == ours == order


def test_this_module_imported_no_torch_and_no_learner():
    assert "torch" not in sys.modules
    for name in ("pointer_learner", "pointer_contract", "pointer_inputs"):
        assert "cas_meta2.typed_teaching." + name not in sys.modules


def test_t4_script_fails_closed_without_cuda_before_any_work():
    """Read, never run: running it here would import torch on the laptop."""
    tree = ast.parse((EVAL / "t4_larger_question_checks.py").read_bytes())
    top_imports = {alias.name.split(".")[0] for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                   for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])}
    assert not top_imports & {"torch", "cas_meta2", "cncm", "eval_paths"}
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    body = ast.unparse(main)
    assert body.index("import torch") < body.index("GPU_REQUIRED: torch is not importable")
    assert body.index("if not torch.cuda.is_available():") < body.index("GPU_REQUIRED: CUDA is not available")
    assert body.index("GPU_REQUIRED: CUDA is not available") < body.index("Context(torch, device, started)")
    assert body.count("return 2") == 2


if __name__ == "__main__":
    failures = 0
    tests = [(name, value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    for name, test in tests:
        try:
            test()
            print("PASS", name)
        except Exception as error:  # noqa: BLE001
            failures += 1
            print("FAIL", name, type(error).__name__, str(error)[:300])
    print("%d passed, %d failed" % (len(tests) - failures, failures))
    sys.exit(1 if failures else 0)
