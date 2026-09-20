"""Pure admission of the complete complementary training course.

This preserves the authored curriculum and separates private correction from
three-field public packets. Registry binding requires a separately versioned
scoped encoder profile and is NOT execution admission. No numerical runtime,
final panel, provider or checkpoint is opened. The legacy globally sorted
encoder is refused: pure scoped frames retain support/query graph ownership,
while numerical scope binding and the course worker remain unverified.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re

from cas_meta2.codec import validate_public
from cas_meta2.complementary_teaching import course
from cas_meta2.graph_teaching import face_corpus, ordered_encoder

from .canonical import canonical_json, digest
from .model import ContractError
from . import rpa_learning_adapter as base

ROOT = Path(__file__).resolve().parents[1]
PREPARED_SCHEMA = "cncm.rpa-course-prepared/0.1"
BOUND_SCHEMA = "cncm.rpa-course-bound/0.1"
RENDERING_SCHEMA = "cncm.rpa-course-public/0.1"
SOURCE_PROFILE_SCHEMA = "cncm.rpa-course-source-profile/0.1"
PACKET_ID_SCHEMA = "cncm.rpa-course-input/0.1"
MAX_COURSE_BYTES = 32 * 1024 * 1024
MAX_PRESENTATIONS = 1152
OPERATIONS = frozenset({"FACE_APPLY", "ROLE_FROM_CONTENT", "LIST_PARTS", "REACHED_VIA"})
INVENTORY_DECLARATION = base.INVENTORY_DECLARATION
HEADER = "Course presentation: " + RENDERING_SCHEMA
_NODE = re.compile(r"node ([A-Za-z][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*) kind=idea\Z")
_REL = re.compile(r"rel ([A-Za-z][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*) --contains--> ([A-Za-z][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*)\Z")
_PREPARED_FIELDS = {"schema_version", "source_profile", "seed", "condition", "counts",
                    "batches", "presentations", "readiness", "prepared_course_digest"}
_PRESENTATION_FIELDS = {"presentation_id", "prepared_id", "operation", "public",
                        "encoded_options", "source_selector", "teacher_sidecar"}
_READINESS = {
    "status": "NOT_YET_EXECUTION_ADMITTED",
    "source_reconstruction": "CANONICAL_TRAINING_CONSTRUCTORS",
    "target_check": "SOURCE_COMPILER_CONSISTENCY_NOT_INDEPENDENT_WORLD_TRUTH",
    "source_authorship_authenticated": False,
    "world_truth_established": False,
    "scope_binding_status": "SCOPED_PROFILE_REQUIRED_NOT_BOUND",
    "support_query_scope_binding_verified": False,
    "course_aware_predictor_verified": False,
    "fresh_origin_worker_factory_verified": False,
    "numeric_encoder_calls": 0, "neural_calls": 0, "optimizer_updates": 0,
    "boundary": "All source text is retained. Binding requires the separately versioned scoped encoder and checks its frame maps purely; numerical scope binding, the course predictor and fresh worker construction remain unverified.",
}


def require(value, reason):
    if not value:
        raise ContractError(reason)


def _same(a, b):
    return canonical_json(a) == canonical_json(b)


def _closed(value, fields, reason):
    require(type(value) is dict and set(value) == set(fields), reason)


def _bounded(value):
    return base.cube._bounded(value, MAX_COURSE_BYTES, "course")


def _hex(value):
    require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value), "COURSE_DIGEST_INVALID")


def source_profile():
    """Pin code only; no final/development target data files are read.

    The canonical constructors derive training source from face_corpus.py.
    Pinning the full pure source package covers its transitive/dynamic imports;
    it does not execute the package's numerical or evaluation entry points.
    """
    research = ROOT / "research/CAS_META_2_COMPOSITION/cas_meta2"
    paths = set(research.rglob("*.py"))
    paths.update(ROOT / name for name in (
        "cncm/rpa_course_adapter.py", "cncm/rpa_learning_adapter.py",
        "cncm/rpa_cube_adapter.py", "cncm/rpa_model.py", "cncm/model.py",
        "cncm/canonical.py", "cncm/__init__.py"))
    require(0 < len(paths) <= 512, "COURSE_SOURCE_FILE_BOUND")
    rows = []
    for path in sorted(paths, key=lambda p: p.relative_to(ROOT).as_posix()):
        require(path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(ROOT), "COURSE_SOURCE_SCOPE")
        raw = path.read_bytes()
        require(len(raw) <= 2 * 1024 * 1024, "COURSE_SOURCE_FILE_SIZE")
        rows.append({"path": path.relative_to(ROOT).as_posix(),
                     "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    body = {"schema_version": SOURCE_PROFILE_SCHEMA, "files": rows,
            "data_files": [], "source_kind": "AUTHORED_CODE_GENERATED_TRAINING_FAMILIES",
            "inventory_contract": "Each generated family graph is the complete declared contains snapshot; this is not a completeness claim about the wider world or arbitrary narratives.",
            "final_target_files_read": False}
    return {**body, "profile_digest": digest(body)}


def _check_profile(expected):
    _hex(expected)
    profile = source_profile()
    require(profile["profile_digest"] == expected, "COURSE_SOURCE_PROFILE_CHANGED")
    return profile


def _check_options(public, options):
    validate_public(public)
    require(type(options) is list and len(options) == 3
            and len({canonical_json(v) for v in options}) == 3, "COURSE_THREE_DISTINCT_CHOICES")
    for option in options:
        require(type(option) is str or
                type(option) is list and all(type(v) is str for v in option),
                "COURSE_OPTION_TYPE")
        require(0 < len(str(option)) <= 256, "COURSE_OPTION_LOSSY_OR_EMPTY")
    for index, row in enumerate(public["observations"]):
        require(type(row["slot"]) is int and row["slot"] == index
                and row["tag"] == str(options[index])
                and _same(row["values"], [0.0] * 8), "COURSE_VISIBLE_OPTION_MISMATCH")


def _structural(line):
    return _NODE.fullmatch(line) is not None or _REL.fullmatch(line) is not None


def _render(operation, source_problem):
    """Escape framing, retain all original lines and newline state losslessly."""
    require(operation in OPERATIONS and type(source_problem) is str
            and "\r" not in source_problem and len(source_problem) <= 8192,
            "COURSE_SOURCE_TEXT")
    lines = [HEADER, "Operation: " + operation, INVENTORY_DECLARATION]
    for line in source_problem.split("\n"):
        if _structural(line):
            lines.append(line)
        else:
            require(not line.startswith(("node ", "rel ")), "COURSE_UNSUPPORTED_STRUCTURE")
            lines.append("text " + canonical_json(line))
    return "\n".join(lines) + "\n"


def _parse_public(public, options):
    """Check a closed framing language, without source or target reconstruction."""
    _check_options(public, options)
    problem = public["problem"]
    require(problem.endswith("\n") and "\r" not in problem, "COURSE_RENDERING_NEWLINES")
    lines = problem[:-1].split("\n")
    require(len(lines) >= 5 and lines[0] == HEADER, "COURSE_RENDERING_SCHEMA")
    require(lines[1].startswith("Operation: "), "COURSE_OPERATION_HEADER")
    operation = lines[1].removeprefix("Operation: ")
    require(operation in OPERATIONS, "COURSE_OPERATION_UNKNOWN")
    require(lines[2] == INVENTORY_DECLARATION
            and lines.count(INVENTORY_DECLARATION) == 1, "COURSE_COMPLETENESS_DECLARATION")
    restored, structural = [], 0
    for line in lines[3:]:
        if _structural(line):
            structural += 1
            restored.append(line)
            continue
        require(line.startswith("text "), "COURSE_FRAMING_ROW")
        try:
            decoded = json.loads(line[5:])
        except (ValueError, TypeError) as error:
            raise ContractError("COURSE_FRAMING_JSON") from error
        require(type(decoded) is str and "\n" not in decoded and "\r" not in decoded
                and canonical_json(decoded) == line[5:] and not _structural(decoded)
                and not decoded.startswith(("node ", "rel ")), "COURSE_FRAMING_CANONICAL")
        restored.append(decoded)
    require(0 < structural <= 256, "COURSE_STRUCTURE_BOUND")
    original = "\n".join(restored)
    require(_render(operation, original) == problem, "COURSE_NONCANONICAL_RENDERING")
    if operation == "ROLE_FROM_CONTENT":
        require(re.search(r"\bCUBE_FACE_[1-6]\b", original) is None,
                "COURSE_HIDDEN_ROLE_CUE")
    return operation, original


def _public_id(public, options, profile, model_context):
    return "rpa-course-input-" + digest({
        "schema_version": PACKET_ID_SCHEMA, "public": public,
        "encoded_options": options, "ordered_profile": profile,
        "model_context": model_context})


def _scoped_encoder():
    from cas_meta2.graph_teaching import scoped_ordered_encoder
    return scoped_ordered_encoder


def _identity(tokenizer, ordered_profile, model_context):
    # The cube adapter intentionally accepts only its existing encoder profile.
    # This separate contract must not pass a scoped profile through that parser.
    require(type(tokenizer) is base.LosslessPublicTokenizer
            and set(vars(tokenizer)) == {"vocabulary", "fitted_public_sha256",
                "fitted_examples", "max_length"}, "COURSE_EXACT_TOKENIZER_REQUIRED")
    wire = tokenizer.to_dict()
    require(len(canonical_json(wire).encode()) <= base.MAX_TOKENIZER_BYTES,
            "COURSE_TOKENIZER_BYTE_BOUND")
    checked = base.LosslessPublicTokenizer.from_dict(wire)
    require(checked.max_length == 1024, "COURSE_TOKEN_CEILING")
    require(type(ordered_profile) is dict, "COURSE_SCOPED_PROFILE_REQUIRED")
    encoder = _scoped_encoder()
    require(ordered_profile.get("profile_id") == encoder.PROFILE_ID,
            "COURSE_SCOPED_PROFILE_REQUIRED")
    expected = encoder.profile_identity(checked,
        d_model=ordered_profile.get("d_model"), seed=ordered_profile.get("permutation_seed"),
        projection_sha256=ordered_profile.get("projection_sha256"))
    require(_same(expected, ordered_profile), "COURSE_SCOPED_PROFILE_MISMATCH")
    encoder.validate_checkpoint_identity({"encoder_identity": expected}, expected)
    _closed(model_context, {"model_id", "checkpoint_sha256"}, "COURSE_MODEL_CONTEXT")
    require(type(model_context["model_id"]) is str and re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}", model_context["model_id"]), "COURSE_MODEL_ID")
    _hex(model_context["checkpoint_sha256"])
    return checked, deepcopy(expected), deepcopy(model_context)


def _tokenization(public, tokenizer):
    tokenizer.check_round_trip(public)
    encoded = tokenizer.encode_public(public)
    frames = _scoped_encoder().compile_frames(public, tokenizer)
    wire = [{"kind": f.kind, "ordinal": f.ordinal, "scope_anchor": f.scope_anchor,
             "token_ids": list(f.token_ids)} for f in frames]
    return {"encoded_token_count": len(encoded["ids"]), "ordered_frame_count": len(frames),
            "text_round_trip": True, "scoped_frame_digest": digest(wire)}


def validate_prediction_packet(packet, *, tokenizer, ordered_profile, model_context):
    """Pure syntax/identity validation only; this is not GPU execution admission."""
    _closed(packet, {"record_id", "public", "encoded_options"}, "COURSE_PUBLIC_FIELDS")
    _bounded(packet)
    checked, profile, context = _identity(tokenizer, ordered_profile, model_context)
    _parse_public(packet["public"], packet["encoded_options"])
    _tokenization(packet["public"], checked)
    require(packet["record_id"] == _public_id(packet["public"], packet["encoded_options"],
        profile, context), "COURSE_STALE_PUBLIC_ID")
    return deepcopy(packet)


def _source_task(task, selector, position):
    op = task["op"]
    require(op in OPERATIONS, "COURSE_SOURCE_OPERATION")
    common = {"arm", "correct", "encoded_correct_index", "encoded_options", "family_id",
              "op", "public", "public_input_sha256", "record_id", "semantic_question_id",
              "task_profile", "teaching_role"}
    _closed(task, common | ({"face_role"} if op in {"FACE_APPLY", "ROLE_FROM_CONTENT"}
                           else {"graph", "question"}), "COURSE_SOURCE_TASK_FIELDS")
    _check_options(task["public"], task["encoded_options"])
    require(task["public_input_sha256"] == course.public_identity(task), "COURSE_SOURCE_PUBLIC_PIN")
    index = task["encoded_correct_index"]
    require(type(index) is int and 0 <= index < 3
            and _same(task["encoded_options"][index], task["correct"]),
            "COURSE_SOURCE_TARGET_INDEX")
    if op == "ROLE_FROM_CONTENT":
        require(task["face_role"] is None, "COURSE_PRIVATE_FACE_VISIBLE")
    public = deepcopy(task["public"])
    public["problem"] = _render(op, public["problem"])
    parsed_op, restored = _parse_public(public, task["encoded_options"])
    require(parsed_op == op and restored == task["public"]["problem"], "COURSE_TEXT_NOT_LOSSLESS")
    public_body = {"operation": op, "public": public, "encoded_options": deepcopy(task["encoded_options"])}
    return {
        "presentation_id": "course-presentation-%04d" % position,
        "prepared_id": "rpa-course-prepared-" + digest(public_body),
        **public_body,
        "source_selector": {**selector, "source_record_id": task["record_id"],
            "family_id": task["family_id"], "semantic_question_id": task["semantic_question_id"],
            "teaching_role": task["teaching_role"]},
        "teacher_sidecar": {"expected_answer": deepcopy(task["correct"]),
            "encoded_correct_index": index, "operation": op,
            "basis": "RECONSTRUCTED_CANONICAL_TRAINING_SOURCE"},
    }


@lru_cache(maxsize=9)
def _prepare_cached(seed, condition, profile_json):
    """Private cache is copied at the public boundary and keyed by actual source pins."""
    profile = json.loads(profile_json)
    built = [family for family in face_corpus.families() if family["split"] == face_corpus.TRAINING]
    require(len(built) == face_corpus.TRAINING_FAMILIES, "COURSE_TRAINING_FAMILY_COUNT")
    schedule = course.compile_complementary_course(seed, condition, built=built)
    require(schedule["counts"]["decisions"] == 1152
            and schedule["counts"]["optimizer_updates"] == 160
            and schedule["counts"]["rounds"] == 16, "COURSE_FULL_SCHEDULE_REQUIRED")
    batches, presentations = [], []
    for batch in schedule["batches"]:
        ids = []
        for slot, task in enumerate(batch["tasks"]):
            selector = {key: batch[key] for key in ("cursor", "round", "phase", "depth")}
            selector["slot"] = slot
            row = _source_task(task, selector, len(presentations))
            presentations.append(row)
            ids.append(row["presentation_id"])
        batches.append({key: batch[key] for key in ("cursor", "round", "phase", "depth")}
                       | {"presentation_ids": ids})
    body = {"schema_version": PREPARED_SCHEMA, "source_profile": profile,
        "seed": seed, "condition": condition, "counts": deepcopy(schedule["counts"]),
        "batches": batches, "presentations": presentations, "readiness": deepcopy(_READINESS)}
    body["prepared_course_digest"] = digest(body)
    _bounded(body)
    return body


def prepare_course(*, seed, condition, expected_source_profile_digest):
    """Reconstruct only canonical training presentations, with caller-pinned code."""
    require(type(seed) is int and seed in course.SEEDS, "COURSE_SEED")
    require(type(condition) is str and condition in course.CONDITIONS, "COURSE_CONDITION")
    profile = _check_profile(expected_source_profile_digest)
    prepared = deepcopy(_prepare_cached(seed, condition, canonical_json(profile)))
    require(source_profile() == profile, "COURSE_SOURCE_CHANGED_DURING_PREPARATION")
    return prepared


def _reprepare(prepared):
    _bounded(prepared)
    _closed(prepared, _PREPARED_FIELDS, "COURSE_PREPARED_FIELDS")
    require(prepared["schema_version"] == PREPARED_SCHEMA, "COURSE_PREPARED_SCHEMA")
    expected = prepare_course(seed=prepared["seed"], condition=prepared["condition"],
        expected_source_profile_digest=prepared["source_profile"]["profile_digest"])
    require(_same(expected, prepared), "COURSE_DIFFERS_FROM_SOURCE_RECONSTRUCTION")
    return expected


def _training_publics(prepared):
    # Stable public-only order gives ALT and MIXED the exact same fit identity.
    unique = {canonical_json(row["public"]): row["public"]
              for row in prepared["presentations"]}
    return [deepcopy(unique[key]) for key in sorted(unique)]


def fit_training_tokenizer(prepared):
    """Fit only source-reconstructed training publics, never private targets."""
    checked = _reprepare(prepared)
    result = base.LosslessPublicTokenizer.fit_train(_training_publics(checked), max_length=1024)
    _check_profile(checked["source_profile"]["profile_digest"])
    return result


def _bind_checked(prepared, *, tokenizer, ordered_profile, model_context):
    checked, profile, context = _identity(tokenizer, ordered_profile, model_context)
    expected_tokenizer = base.LosslessPublicTokenizer.fit_train(
        _training_publics(prepared), max_length=1024)
    require(_same(checked.to_dict(), expected_tokenizer.to_dict()),
            "COURSE_TOKENIZER_NOT_EXACT_TRAINING_ONLY_FIT")
    registry, teachers, refs, by_id, frame_checks = [], {}, [], {}, []
    for row in prepared["presentations"]:
        record_id = _public_id(row["public"], row["encoded_options"], profile, context)
        packet = {"record_id": record_id, "public": deepcopy(row["public"]),
                  "encoded_options": deepcopy(row["encoded_options"])}
        target = {"record_id": record_id, **deepcopy(row["teacher_sidecar"])}
        if record_id in by_id:
            require(_same(by_id[record_id], packet) and _same(teachers[record_id], target),
                    "COURSE_DUPLICATE_PUBLIC_TARGET_CONFLICT")
        else:
            _parse_public(packet["public"], packet["encoded_options"])
            frame_checks.append(_tokenization(packet["public"], checked))
            by_id[record_id] = packet
            registry.append(packet)
            teachers[record_id] = target
        refs.append({"presentation_id": row["presentation_id"], "record_id": record_id,
                     "prepared_id": row["prepared_id"],
                     "source_selector": deepcopy(row["source_selector"])})
    body = {"schema_version": BOUND_SCHEMA,
        "prepared_course_digest": prepared["prepared_course_digest"],
        "source_profile_digest": prepared["source_profile"]["profile_digest"],
        "seed": prepared["seed"], "condition": prepared["condition"],
        "registry": registry, "teacher_registry": teachers, "presentations": refs,
        "batches": deepcopy(prepared["batches"]), "counts": deepcopy(prepared["counts"]),
        "binding": {"ordered_profile": profile, "model_context": context,
                    "tokenizer_digest": checked.digest,
                    "identity_evidence": base.IDENTITY_EVIDENCE,
                    "checkpoint_context_scope": base.CHECKPOINT_SCOPE,
                    "worker_observed": False, "projection_bytes_verified": False,
                    "checkpoint_bytes_verified": False, "cached_vectors_verified": False,
                    "scoped_frames_pure_checked": True,
                    "max_encoded_tokens": max(r["encoded_token_count"] for r in frame_checks),
                    "max_ordered_frames": max(r["ordered_frame_count"] for r in frame_checks)},
        "readiness": {**deepcopy(_READINESS),
            "scope_binding_status": "SCOPED_FRAME_MAPS_PURE_CHECKED_CUDA_PENDING"}}
    body["bound_course_digest"] = digest(body)
    _bounded(body)
    return body


def bind_course(prepared, *, tokenizer, ordered_profile, model_context):
    """Bind a fresh training-only identity; preserve schedule, deduplicate cache only."""
    checked = _reprepare(prepared)
    result = _bind_checked(checked, tokenizer=tokenizer, ordered_profile=ordered_profile,
                          model_context=model_context)
    _check_profile(checked["source_profile"]["profile_digest"])
    return result


def check_course_targets(bound, *, prepared, tokenizer, ordered_profile, model_context):
    """Check the entire source/binding join; never called from public validation."""
    expected = bind_course(prepared, tokenizer=tokenizer, ordered_profile=ordered_profile,
                           model_context=model_context)
    require(_same(bound, expected), "COURSE_BOUND_SOURCE_MISMATCH")
    return deepcopy(expected["teacher_registry"])
