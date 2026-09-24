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
# Revision 2 (verification V1): both checkers also run code from these four files while grading. Written here
# independently of the module's own `SHARED_GRADER_FILES`.
SHARED_GRADER_FILES = ("answers.py", "focal.py", "source.py", "course.py")

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
    """Read, never run: `main` would import torch on the laptop. Inputs are checked BEFORE torch is imported."""
    tree = ast.parse((EVAL / "t4_larger_question_checks.py").read_bytes())
    top_imports = {alias.name.split(".")[0] for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                   for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])}
    assert not top_imports & {"torch", "cas_meta2", "cncm", "eval_paths"}
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    body = ast.unparse(main)
    order = ["if args.list_inputs:", "OUTPUT_EXISTS", "RowWriter(rows_path)", "verify_inputs(requested)",
             "import torch", "GPU_REQUIRED: torch is not importable", "if not torch.cuda.is_available():",
             "GPU_REQUIRED: CUDA is not available", "T4_REFERENCE_ENVIRONMENT_DIFFERS",
             "Context(torch, device, started, rows, requested)", "preflight(ctx, requested)",
             "PREFLIGHT_OVER_WALL_LIMIT", "for name in requested:"]
    positions = [body.index(text) for text in order]
    assert positions == sorted(positions)
    assert body.count("finish('GPU_REQUIRED', 2") == 2 and "finish('PREFLIGHT_OVER_WALL_LIMIT', 5" in body


# ---------------------------------------------------------------------------------------------- T4 script, rev 1
_T4 = []


def _t4():
    """The T4 script as a module. Its top level imports no torch and no project code (tested above)."""
    if not _T4:
        import importlib.util
        spec = importlib.util.spec_from_file_location("t4_larger_question_checks_static",
                                                      EVAL / "t4_larger_question_checks.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _T4.append(module)
    return _T4[0]


def test_t4_runs_the_checks_in_the_order_d_c_b_a():
    t4 = _t4()
    assert t4.CHECK_ORDER == ("d", "c", "b", "a") and set(t4.CHECKS) == set(t4.CHECK_ORDER)
    main = next(node for node in ast.parse((EVAL / "t4_larger_question_checks.py").read_bytes()).body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    assert "requested = [name for name in CHECK_ORDER if name in chosen]" in ast.unparse(main)
    tree = ast.parse((EVAL / "t4_larger_question_checks.py").read_bytes())
    for name in ("check_a", "check_b", "check_c", "_learner_pair"):
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        assert "ctx.emit(" in ast.unparse(function), name
    emit = ast.unparse(_method(EVAL / "t4_larger_question_checks.py", "RowWriter", "emit"))
    assert emit.index("write(") < emit.index("flush()") < emit.index("os.fsync(")


def test_t4_outputs_are_create_only_and_flushed_row_by_row():
    import json
    import tempfile
    t4 = _t4()
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        rows = folder / "result.json.rows.jsonl"
        writer = t4.RowWriter(rows)
        writer.emit("d", {"row": "one"})
        writer.emit("a", {"row": "two"})
        lines = rows.read_text(encoding="utf-8").splitlines()  # readable BEFORE close: every row is flushed
        assert [json.loads(line)["check"] for line in lines] == ["d", "a"] and writer.count == {"d": 1, "a": 1}
        writer.close()
        assert isinstance(_raises(t4.RowWriter, rows), FileExistsError)
        summary = folder / "result.json"
        t4._publish(summary, {"verdict": "X"})
        assert json.loads(summary.read_text(encoding="utf-8")) == {"verdict": "X"}
        assert not (folder / "result.json.partial").exists()
        assert isinstance(_raises(t4._publish, summary, {"verdict": "Y"}), FileExistsError)
        assert json.loads(summary.read_text(encoding="utf-8")) == {"verdict": "X"}


def test_t4_required_inputs_name_every_file_with_its_pin():
    from cas_meta2.typed_teaching import matched_contract, worker_contract
    t4 = _t4()
    rows = {row["path"]: (row["bytes"], row["sha256"]) for row in t4.REQUIRED_INPUTS}
    assert len(rows) == len(t4.REQUIRED_INPUTS) == 3 + 2 + 6 + 1
    for path, pin in worker_contract.MATERIAL.items():
        assert rows[path] == (pin["bytes"], pin["sha256"]), path
    assert rows[matched_contract.DEVELOPMENT_PATH] == (matched_contract.DEVELOPMENT_PIN["bytes"],
                                                       matched_contract.DEVELOPMENT_PIN["sha256"])
    for name, digest in worker_contract.WHEELS.items():
        path = worker_contract.WHEEL_PREFIX + name
        raw = (CNCM / path).read_bytes()
        assert rows[path] == (len(raw), digest) and hashlib.sha256(raw).hexdigest() == digest, name
    for (seed, phase), pin in t4.CHECKPOINTS.items():
        assert rows[t4._checkpoint_path(seed, phase)] == pin
    fixture = fixtures.FIXTURE_PATH.relative_to(CNCM).as_posix()
    assert rows[fixture] == (len(fixtures.FIXTURE_PATH.read_bytes()), FIXTURE_FILE_SHA256)
    assert t4.REQUIRED_SOURCE_TREES == tuple(worker_contract_prefixes())
    assert set(t4.WHEEL_MODULES) == {"casformer", "cas_cjt"}
    assert sorted(t4.EVAL_PATHS_FILES) == sorted(path.name for path in EVAL.glob("*.py")
                                                 if path.name != "colour_refinement_census.py")
    # The committed git blobs carry exactly these bytes (the records/ files are outside this sparse checkout).
    top = _git("rev-parse", "--show-toplevel")
    if top is None:
        print("NOTE: no git; blob sizes not re-checked")
        return
    prefix = CNCM.resolve().relative_to(pathlib.Path(top.decode().strip()).resolve()).as_posix()
    for path, (size, digest) in rows.items():
        assert _git_blob_sha256("HEAD:%s/%s" % (prefix, path)) == (size, digest), path


def worker_contract_prefixes():
    tree = ast.parse((TYPED / "worker_contract.py").read_bytes())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "input_inventory")
    loop = next(node for node in ast.walk(function) if isinstance(node, ast.For)
                and isinstance(node.target, ast.Name) and node.target.id == "prefix")
    return ast.literal_eval(loop.iter)


def _git(*args):
    import subprocess
    try:
        done = subprocess.run(["git", "-C", str(CNCM), *args], capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _git_blob_sha256(spec):
    """`(bytes, sha256)` of one git blob, streamed in chunks (checkpoints are hashed, never loaded)."""
    import subprocess
    process = subprocess.Popen(["git", "-C", str(CNCM), "cat-file", "blob", spec], stdout=subprocess.PIPE)
    digest, size = hashlib.sha256(), 0
    while True:
        chunk = process.stdout.read(1 << 16)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    assert process.wait() == 0, spec
    return size, digest.hexdigest()


def test_t4_list_inputs_needs_no_torch_and_no_project_code():
    import json
    import subprocess
    script = EVAL / "t4_larger_question_checks.py"
    code = ("import json, runpy, sys\n"
            "sys.modules['torch'] = None\n"
            "sys.argv = ['t4', '--list-inputs']\n"
            "try:\n"
            "    runpy.run_path(%r, run_name='__main__')\n"
            "except SystemExit as stop:\n"
            "    status = stop.code\n"
            "loaded = sorted(n for n in sys.modules if n.split('.')[0] in ('cas_meta2', 'cncm', 'eval_paths'))\n"
            "print('@@' + json.dumps({'status': status, 'loaded': loaded}))\n" % str(script))
    done = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=120)
    listing, marker = done.stdout.split("@@")
    assert json.loads(marker) == {"status": 0, "loaded": []}, done.stderr
    listed = json.loads(listing)
    t4 = _t4()
    assert [row["path"] for row in listed["required_inputs"]] == [row["path"] for row in t4.REQUIRED_INPUTS]
    assert [row["path"] for row in listed["required_source_trees"]] == list(t4.REQUIRED_SOURCE_TREES)


def test_t4_verify_inputs_refuses_a_missing_or_changed_file_by_name():
    import tempfile
    t4 = _t4()
    first = t4.REQUIRED_INPUTS[0]["path"]
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        error = _raises(t4.verify_inputs, ["d"], root)
        assert isinstance(error, t4.SetupRefused) and str(error) == "INPUT_MISSING:" + first
        (root / first).parent.mkdir(parents=True)
        (root / first).write_bytes(b"{}")
        error = _raises(t4.verify_inputs, ["d"], root)
        assert isinstance(error, t4.SetupRefused) and str(error) == "INPUT_MISMATCH:" + first


def test_t4_preflight_plan_and_projection():
    t4 = _t4()
    ids = ["r%03d" % index for index in range(564)]
    larger, refused = ["f%02d" % index for index in range(37)], ["x%d" % index for index in range(4)]
    work = t4.planned_work(ids, larger, refused, list(t4.CHECK_ORDER), learner_ok=True)
    assert work == {"pp_course_calls": 3384, "pp_fixture_calls": 185 + 4, "container_builds": 6 + 5 + 3,
                    "learner_course_calls": 2 * 564 + 2 * 71, "learner_fixture_calls": 74, "learner_builds": 4}
    assert "learner_course_calls" not in t4.planned_work(ids, larger, refused, ["d"], learner_ok=False)
    timings = {"pp_course": 0.45, "pp_fixture": 0.6, "learner_course": 0.5, "container_build": 2.0,
               "learner_build": 3.0}
    remaining = 3384 * 0.45 + 189 * 0.6 + 1270 * 0.5 + 74 * 0.65 + 14 * 2.0 + 4 * 3.0
    projection = t4.project_total(250.0, timings, work)
    assert abs(projection["projected_total_seconds"] - (250.0 + 1.15 * remaining)) < 1e-9
    assert projection["projected_total_seconds"] <= t4.WALL_SECONDS
    assert t4.project_total(250.0, {**timings, "pp_course": 0.8}, work)["projected_total_seconds"] > t4.WALL_SECONDS
    sample_step = max(1, len(ids) // t4.PREFLIGHT_COURSE_CALLS)
    assert len(ids[::sample_step][:t4.PREFLIGHT_COURSE_CALLS]) + len(t4.PREFLIGHT_FIXTURE_IDS) == 20


def test_t4_check_d_switch_off_pair_uses_a_scoped_restored_substitute():
    """Fakes only: `_build_pair` must pass the switch OFF to both constructors and restore the builder."""
    import types
    t4 = _t4()
    seen = []

    def build(torch, framework, device, *, analogy_focus_comparison=True):
        seen.append(analogy_focus_comparison)
        return types.SimpleNamespace(analogy_focus_comparison=analogy_focus_comparison)

    fake = types.SimpleNamespace(_build_container=build)

    class Learner:
        def __init__(self, torch, framework, encoder, **kwargs):
            self.module = fake._build_container(torch, framework, "cuda")  # resolved at call time, as in PL

    fake.PointerCourseLearner = Learner
    ctx = types.SimpleNamespace(PL=fake, LL=types.SimpleNamespace(LargerQuestionPointerLearner=Learner),
                                torch=None, device="cuda", learner_kwargs=lambda run_id: {},
                                encoder=lambda: None, framework=lambda torch, device, seed: None)
    t4._build_pair(ctx, False)
    assert seen == [False, False] and fake._build_container is build
    t4._build_pair(ctx, True)
    assert seen == [False, False, True, True] and fake._build_container is build
    check_d = ast.unparse(next(node for node in ast.parse((EVAL / "t4_larger_question_checks.py").read_bytes()).body
                               if isinstance(node, ast.FunctionDef) and node.name == "check_d"))
    assert "_learner_pair(ctx, 'ON_FRESH_%d' % FRESH_SEED, True, ctx.ids)" in check_d
    assert "ctx.ids[::D_OFF_COURSE_STRIDE]" in check_d and t4.D_OFF_COURSE_STRIDE == 8


def test_t4_reference_digests_equal_the_committed_t4_item1_job():
    """Check a's reference, re-read from git objects of commit 41071a3f (origin/research/helm-integration-20260923).

    Needs that commit in the local object store (`git fetch origin research/helm-integration-20260923`).
    Without git at all (an AWS bundle) the test is a no-op.
    """
    import json
    t4 = _t4()
    reference = t4.T4_REFERENCE
    if _git("rev-parse", "--show-toplevel") is None:
        print("NOTE: no git; T4 reference not re-read")
        return
    assert _git("cat-file", "-e", reference["commit"] + "^{commit}") is not None, "fetch the integration branch"
    top = pathlib.Path(_git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    prefix = CNCM.resolve().relative_to(top).as_posix()
    seen = {"OFF": {}, "control": {}}
    for name, file_sha256 in reference["files_sha256"].items():
        raw = _git("cat-file", "blob", "%s:%s/%s/%s" % (reference["commit"], prefix, reference["folder"], name))
        assert raw is not None and hashlib.sha256(raw).hexdigest() == file_sha256, name
        document = json.loads(raw)
        assert document["complete"] is True and document["torch"] == reference["torch"]
        assert document["tool_sha256_lf"] == reference["tool_sha256_lf"]
        assert document["course_digest"] == reference["course_digest"]
        arm = "OFF" if "_OFF_" in name else "control"
        if arm == "OFF":
            assert document["source_sha256_lf"] == t4.T4_REFERENCE_SOURCE_LF_SHA256
        for row in document["results"]:
            assert row["records"] == 564
            if row["checkpoint"] is None:
                continue
            key = next(key for key in t4.CHECKPOINTS if t4._checkpoint_path(*key) == row["checkpoint"])
            assert row["checkpoint_sha256"] == t4.CHECKPOINTS[key][1]
            seen[arm][key] = row["overall_digest"]
    assert seen["OFF"] == seen["control"] == t4.T4_REFERENCE_OVERALL_DIGEST
    for path, digest in t4.T4_REFERENCE_SOURCE_LF_SHA256.items():
        assert scope.lf_sha256(CNCM / path) == digest, path
    tool = _git("cat-file", "blob", "%s:%s/%s" % (reference["commit"], prefix, reference["tool"]))
    assert hashlib.sha256(tool.replace(b"\r\n", b"\n")).hexdigest() == reference["tool_sha256_lf"]
    # Same quantity: the reference tool and this path write the per-record and overall digests the same way.
    tool = tool.decode("utf-8")
    assert '["%08x" % (v & 0xFFFFFFFF) for v in t.detach().float().contiguous().view(torch.int32).cpu().tolist()]' \
        in tool
    assert 'hashlib.sha256(json.dumps(bits, sort_keys=True, separators=(",", ":")).encode()).hexdigest()' in tool
    assert 'hashlib.sha256("\\n".join("%s %s" % (r, per_record[r]) for r in ids).encode()).hexdigest()' in tool
    assert "rows = PL.GraphForward(torch, model, reading, device).head_logits(plan, indicators)" in tool
    ours = (EVAL / "larger_question_learner.py").read_text(encoding="utf-8")
    assert '"%08x" % (value & 0xFFFFFFFF)' in ours and ".detach().float().contiguous().view(torch.int32)" in ours
    assert 'json.dumps(bits, sort_keys=True, separators=(",", ":")).encode()).hexdigest()' in ours
    assert t4._overall_digest(["b", "a"], {"a": "1", "b": "2"}) == hashlib.sha256(b"b 2\na 1").hexdigest()


def test_grade_and_target_check_the_grader_pins_on_every_call():
    packet = PACKETS["F06"]
    good = scope.target(packet)["admissible_answers"][0]
    assert scope.grade(packet, good)["grader_pins_checked"] == sorted([*D1_ANCHORS, *SHARED_GRADER_FILES])
    saved = scope.D1_ACCEPTED_LF_SHA256
    try:
        scope.D1_ACCEPTED_LF_SHA256 = {**saved, "checker_v2.py": "0" * 64}
        for call in (lambda: scope.grade(packet, good), lambda: scope.target(packet)):
            error = _raises(call)
            assert isinstance(error, scope.LargerPathRefusal) and error.code == "SOURCE_DRIFT"
            assert error.detail == "D1_ANCHOR:checker_v2.py"
    finally:
        scope.D1_ACCEPTED_LF_SHA256 = saved
    bank = fixtures.frozen_training_bank()
    public = {"focus_world_id": bank["worlds"][0]["world_id"], "worlds": bank["worlds"], "bank": bank["bank"]}
    original = fixtures._packet(public, "definition", None, {}, "CUBE_FACE_1")
    saved = scope.PROTECTED_SOURCE_LF_SHA256
    try:
        scope.PROTECTED_SOURCE_LF_SHA256 = {**saved, "checker.py": "0" * 64}
        error = _raises(scope.grade, original, {})
        assert isinstance(error, scope.LargerPathRefusal) and error.code == "SOURCE_DRIFT"
        assert error.detail == "checker.py"
    finally:
        scope.PROTECTED_SOURCE_LF_SHA256 = saved
    assert scope.verify_grader_pins(scope.ORIGINAL) == {name: scope.PROTECTED_SOURCE_LF_SHA256[name]
                                                        for name in ("checker.py", *SHARED_GRADER_FILES)}


def test_grader_pins_also_cover_the_files_both_checkers_run():
    """V1: a drifted `answers.py`, `focal.py`, `source.py` or `course.py` refuses grading on both routes."""
    assert tuple(scope.SHARED_GRADER_FILES) == SHARED_GRADER_FILES
    # Every typed_teaching module either checker imports is pinned inside `grade` for its route.
    for name, route in (("checker.py", scope.ORIGINAL), ("checker_v2.py", scope.LARGER)):
        imported = set()
        for node in ast.parse((TYPED / name).read_bytes()).body:
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                imported |= ({alias.name + ".py" for alias in node.names} if node.module is None
                             else {node.module + ".py"})
        assert imported == {"answers.py", "focal.py", "source.py"}, name
        assert imported | {"course.py", name} <= set(scope.verify_grader_pins(route)), name
    larger = PACKETS["F06"]
    good = scope.target(larger)["admissible_answers"][0]
    bank = fixtures.frozen_training_bank()
    public = {"focus_world_id": bank["worlds"][0]["world_id"], "worlds": bank["worlds"], "bank": bank["bank"]}
    original = fixtures._packet(public, "definition", None, {}, "CUBE_FACE_1")
    assert scope.route(larger) == scope.LARGER and scope.route(original) == scope.ORIGINAL
    saved = scope.PROTECTED_SOURCE_LF_SHA256
    for drifted in SHARED_GRADER_FILES:
        try:
            scope.PROTECTED_SOURCE_LF_SHA256 = {**saved, drifted: "0" * 64}
            calls = (lambda: scope.grade(larger, good), lambda: scope.target(larger),
                     lambda: scope.grade(original, {}), lambda: scope.target(original))
            for call in calls:
                error = _raises(call)
                assert isinstance(error, scope.LargerPathRefusal) and error.code == "SOURCE_DRIFT", drifted
                assert error.detail == drifted, (drifted, error.detail)
        finally:
            scope.PROTECTED_SOURCE_LF_SHA256 = saved
    assert scope.grade(larger, good)["correct"] is True


# The claim-status legend of `docs/CAS_HARNESS_SPEC_SHEET.md`, as the project CLAUDE.md lists it.
SPEC_SHEET_LEGEND = ("REAL", "VALIDATED", "LICENSED", "NOT LICENSED", "NOT_LICENSED", "GREY", "VACUOUS", "WITHDRAWN",
                     "ENGINEERED-NOT-VALIDATED", "ENGINEERED_NOT_VALIDATED", "FLAG_FOR_HUMAN_REVIEW")


def test_kind_scope_records_the_coordinator_claim_ruling():
    """Rulings 2026-09-23 on review F6 and on verification V4. The builder records them; it does not decide them."""
    expected = {"role_set": ("OUT_OF_SCOPE", "OUT_OF_SCOPE"), "definition": ("OUT_OF_SCOPE", "OUT_OF_SCOPE"),
                "context": ("OUT_OF_SCOPE", "OUT_OF_SCOPE"),
                "analogy": ("CHECKER_V2_D1_ACCEPTED", "CHECKER_V2_D1_ACCEPTED"),
                "correspondence": ("CHECKER_V2_D1_ACCEPTED", "CHECKER_V2_D1_ACCEPTED"),
                "parts": ("DIAGNOSTIC_ONLY", "DIAGNOSTIC_ONLY"),
                "edge_account": ("DIAGNOSTIC_ONLY", "DIAGNOSTIC_ONLY"),
                "reach": ("DIAGNOSTIC_ONLY", "CLAIM_BEARING_IN_HSET2_REACH_GOLD_CROSS_CHECKED_BY_INDEPENDENT_RULES")}
    assert {kind: (row["claim_status_at_5_nodes"], row["claim_status_at_6_nodes"])
            for kind, row in scope.KIND_SCOPE.items()} == expected
    # V4: nothing is left NOT_RULED, and the 5-node reason is written into the rows it applies to.
    for kind, row in scope.KIND_SCOPE.items():
        assert "NOT_RULED" not in row["claim_status_at_5_nodes"] + row["claim_status_at_6_nodes"], kind
        basis = row["claim_status_basis"]
        assert type(basis) is str and basis, kind
        if kind in ("parts", "edge_account", "reach"):
            assert "V4" in basis and "DIAGNOSTIC ONLY at 5 nodes" in basis and "reach W = 2 on TEST_NEW_5" in basis
            assert "read the answer off the input" in basis
        # The claim words are local labels, and say so; none of them is a spec-sheet legend word.
        assert row["claim_status_vocabulary"] == scope.CLAIM_STATUS_VOCABULARY == \
            "LOCAL_LABELS_NOT_THE_SPEC_SHEET_LEGEND", kind
        for word in (row["claim_status_at_5_nodes"], row["claim_status_at_6_nodes"]):
            assert word not in SPEC_SHEET_LEGEND, (kind, word)
    text = (EVAL / "larger_question_scope.py").read_text(encoding="utf-8")
    assert "THE CLAIM-STATUS WORDS ARE LOCAL LABELS." in text and "docs/CAS_HARNESS_SPEC_SHEET.md" in text


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
