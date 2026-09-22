"""Read-only atlas for two frozen, genuine Helm development predictions.

Only saved DEVELOPMENT records are exported. The original prediction is never
replaced by a checker answer. The historical pure checker is replayed separately;
no learner, torch import, checkpoint decode, model run, or protected final target
is needed. Frozen source anchors are outside the caller's resealable document.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import threading
import types
from urllib.parse import quote, unquote, urlsplit, parse_qs

from .canonical import canonical_json, digest
from .model import ContractError
from .rpa_model import AtlasContext, AtlasNode, AtlasLink, AtlasSnapshot, NodeKind, NodeStatus, LinkType, require

SCHEMA = "cas.rpa.recorded-helm/0.1"
ADDRESS_SCHEMA = "cas.rpa.recorded-helm-address/0.1"
NAVIGATION_SCHEMA = "cas.rpa.recorded-helm-navigation/0.1"
SAVED_VIEW_SCHEMA = "cas.rpa.recorded-helm-saved-view/0.1"
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "records/rpa_recorded_helm_20260922"
SELECTION_SHA256 = "d181782419e3480a7f8b39e2bc3bce7eaa28cde21c44bb9abcd0c021bfcd7daf"
MAX_BYTES = 4 * 1024 * 1024
MAX_JSON_NODES = 100000
MAX_DEPTH = 64
PRESENT = "recorded-run"
_LOCK = threading.RLock()
_CHECKER_CACHE = None
_BOUNDARY = {
    "source": "FROZEN_RETAINED_DEVELOPMENT_RECORDS",
    "present": "ARCHIVED_RUN_RECORD_NOT_LIVE_HELM",
    "prediction": "ORIGINAL_SAVED_MODEL_OUTPUT_NOT_REGENERATED",
    "checker_replay": "DETERMINISTIC_DECLARED_SOURCE_SEMANTICS_NOT_MODEL_INFERENCE",
    "selection": "POSTHOC_ILLUSTRATIVE_CORRECT_AND_WRONG_EXAMPLES_NOT_A_BENCHMARK",
    "model": "HELM_2_EXPERIMENTAL_NOT_CERTIFIED_NO_UPGRADE_CLAIM",
    "runtime": "NOT_CONNECTED", "new_learning": "NOT_RUN",
    "protected_final_targets": "NOT_EXPORTED_OR_READ_BY_ADAPTER",
    "profiles": "NOT_ASSIGNED", "ohm": "NOT_RECORDED",
    "source_authentication": "RETAINED_LOCAL_HASH_BINDINGS_NOT_EXTERNAL_AUTHENTICATION",
    "authority": "INSPECTION_ONLY",
}


def _bounded(value, maximum=MAX_BYTES):
    stack, active, count, text_total = [(value, 0, False)], set(), 0, 0
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        count += 1
        require(count <= MAX_JSON_NODES and depth <= MAX_DEPTH, "recorded atlas JSON structural bound")
        if type(item) in (dict, list):
            require(len(item) <= MAX_JSON_NODES and id(item) not in active, "recorded atlas cyclic/oversized container")
            active.add(id(item))
            stack.append((item, depth, True))
            if type(item) is dict:
                require(all(type(k) is str for k in item), "recorded atlas JSON text keys required")
                text_total += sum(len(k) for k in item)
                children = item.values()
            else:
                children = item
            stack.extend((child, depth + 1, False) for child in children)
        else:
            require(type(item) in (str, int, float, bool, type(None)), "recorded atlas JSON values required")
            if type(item) is str:
                text_total += len(item)
            if type(item) is int:
                require(item.bit_length() <= 4096, "recorded atlas integer bound")
        require(text_total <= maximum, "recorded atlas aggregate text bound")
    try:
        raw = canonical_json(value).encode("utf-8")
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise ContractError("recorded atlas invalid JSON values") from exc
    require(len(raw) <= maximum, "recorded atlas JSON byte bound")
    return raw


def _decode(raw, maximum=MAX_BYTES):
    require(type(raw) in (bytes, str) and len(raw) <= maximum, "recorded atlas wire bound/type")
    try:
        body = raw if type(raw) is bytes else raw.encode("utf-8")
        require(len(body) <= maximum, "recorded atlas wire byte bound")
        def unique(rows):
            result = {}
            for key, value in rows:
                require(key not in result, "duplicate JSON field")
                result[key] = value
            return result
        def integer(token):
            require(len(token.lstrip("-")) <= 1234, "JSON integer token bound")
            value = int(Decimal(token))
            require(value.bit_length() <= 4096, "JSON integer bit bound")
            return value
        def constant(value):
            raise ContractError("nonfinite JSON constant")
        def floating(token):
            require(len(token) <= 128, "JSON floating token bound")
            value = float(token)
            require(math.isfinite(value), "nonfinite JSON float")
            return value
        result = json.loads(body.decode("utf-8"), object_pairs_hook=unique,
                            parse_int=integer, parse_float=floating, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("invalid recorded atlas JSON: " + str(exc)[:160]) from exc
    _bounded(result, maximum)
    return result


def _read_pinned(relative, pin):
    path = SOURCE_ROOT / relative
    require(path.resolve().is_relative_to(SOURCE_ROOT.resolve()) and not path.is_symlink(),
            "retained source escaped its directory")
    with path.open("rb") as stream:
        raw = stream.read(pin["bytes"] + 1)
    require(len(raw) == pin["bytes"] and sha256(raw).hexdigest() == pin["sha256"],
            "frozen retained source pin mismatch: " + relative)
    return raw


def _retained():
    selection_path = SOURCE_ROOT / "source_selection.json"
    require(not selection_path.is_symlink() and selection_path.resolve().is_relative_to(SOURCE_ROOT.resolve()),
            "source selection escaped its directory")
    with selection_path.open("rb") as stream:
        raw = stream.read(65537)
    require(len(raw) <= 65536 and sha256(raw).hexdigest() == SELECTION_SHA256,
            "external source selection anchor mismatch")
    selection = _decode(raw, 65536)
    require(selection["schema_version"] == "cas.rpa.recorded-helm-source-selection/0.1" and
            selection["exposure"]["split"] == "development" and
            selection["exposure"]["main_or_final_target_files_opened"] is False,
            "development exposure contract mismatch")
    records = _decode(_read_pinned("selected_records.json", selection["selected_files"]["selected_records.json"]))
    identity = _decode(_read_pinned("saved_identity.json", selection["selected_files"]["saved_identity.json"]))
    manifest = _decode(_read_pinned("artifact_manifest.json", selection["selected_files"]["artifact_manifest.json"]))
    manifest_pins = {row["name"]: row for row in manifest["artifacts"]}
    for name, pin in selection["original_files"].items():
        require(manifest_pins[name]["sha256"] == pin["sha256"] and manifest_pins[name]["bytes"] == pin["bytes"],
                "independent original artifact manifest binding mismatch")
    final = identity["final_checkpoint"]
    require(final["sha256"] == manifest_pins["final.pt"]["sha256"] and final["bytes"] == manifest_pins["final.pt"]["bytes"],
            "checkpoint metadata/manifest binding mismatch")
    disclosure = identity["development_disclosure"]
    require(disclosure["policy"]["split"] == "development" and disclosure["final_questions_constructed"] == 0
            and disclosure["main_targets_constructed"] == 0, "protected material refused")
    require(identity["saved_development_scores"]["public_seal"]["sha256"] ==
            selection["original_files"]["development_p10_predictions.json"]["sha256"],
            "saved scoring/prediction seal mismatch")
    return selection, records, identity


def _checker(selection):
    """Compile the original four pure checker modules from verified bytes."""
    global _CHECKER_CACHE
    with _LOCK:
        sources = [(row, _read_pinned(row["saved_path"], row)) for row in selection["checker_sources"]]
        if _CHECKER_CACHE is not None:
            return _CHECKER_CACHE
        name = "_rpa_recorded_helm_checker_" + SELECTION_SHA256
        package = types.ModuleType(name)
        package.__path__ = [str(SOURCE_ROOT / "pinned_checker")]
        sys.modules[name] = package
        created = [name]
        try:
            for row, raw in sources:
                leaf = Path(row["saved_path"]).stem
                module = types.ModuleType(name + "." + leaf)
                module.__file__ = str(SOURCE_ROOT / row["saved_path"])
                module.__package__ = name
                sys.modules[module.__name__] = module
                setattr(package, leaf, module)
                created.append(module.__name__)
                exec(compile(raw, module.__file__, "exec"), module.__dict__)
            _CHECKER_CACHE = package.checker
            return _CHECKER_CACHE
        except Exception:
            for key in reversed(created):
                sys.modules.pop(key, None)
            raise


def _label_map(packet):
    worlds = packet["source"]["worlds"]
    focus_id = packet["record"]["query"]["focus_world_id"]
    world = next(row for row in worlds if row["world_id"] == focus_id)
    labels = {row["ref"]: row["label"] for row in world["nodes"]}
    return world, labels


def _answer_text(answer, labels):
    value = answer["value"]
    if answer["kind"] == "parts":
        names = [labels[key] for key in value["nodes"]]
        return ", ".join(names) if names else "(no nodes)"
    require(answer["kind"] == "reach", "only retained development parts/reach examples are exposed")
    return value["state"] + (" via " + labels[value["via"]] if value.get("via") is not None else "")


def build_recorded_atlas():
    selection, records, identity = _retained()
    checker = _checker(selection)
    context = AtlasContext("retained-helm-development", "Helm 2.0-experimental",
        identity["worker"]["job"], "Archived 2026-09-20 run; no live clock claim", 1)
    model = identity["final_checkpoint"]
    node_rows, edges, examples = [], [], []
    def node(node_id, item_id, label, role, version, fields=(), status=NodeStatus.UNKNOWN):
        node_rows.append(AtlasNode(node_id, item_id, label, context, status,
            tuple(sorted({"item_id": item_id, "version_id": version, "role": role,
                          "description": label, **dict(fields)}.items())),
            kind=NodeKind.STATE if node_id == PRESENT else NodeKind.EVIDENCE))
    def part(left, right, explanation):
        body = {"source": left, "target": right, "projection": explanation}
        edges.append(AtlasLink("link-" + digest(body), left, right, LinkType.CONTAINS_PART, projection=explanation))
    node(PRESENT, "helm-run-" + digest(identity["worker"]["job"]), "Saved Helm development run",
         "recorded_run", "revision-1470",
         (("present_basis", "ARCHIVED_RUN_RECORD_NOT_LIVE_HELM"),), NodeStatus.OBSERVED)
    node("model-checkpoint", "checkpoint-" + model["sha256"], "Saved final model checkpoint",
         "model", "revision-1470", (("checkpoint_sha256", model["sha256"]),))
    for row in records:
        key, packet, pred, saved = row["example_id"], row["packet"], row["prediction"], row["saved_check"]
        record, query = packet["record"], packet["record"]["query"]
        require(key in {"correct", "wrong"} and pred["record_id"] == record["record_id"] ==
                saved["record_id"] == selection["selected_record_ids"][key], "retained record binding mismatch")
        require(digest(packet) == pred["packet_digest"] == row["admission"]["packet_sha256"],
                "original model packet digest mismatch")
        require(pred["prediction_id"] == saved["prediction_id"] and pred["answer"]["query_id"] == query["query_id"],
                "original prediction/check query mismatch")
        require(pred["model_revision"] == model["metadata"]["model_revision"] == 1470 and
                pred["run_context_digest"] == model["run_identity_digest"], "checkpoint/prediction identity mismatch")
        replay = checker.check_answer(packet["source"], query, pred["answer"])
        expected_check = {**replay, "record_id": record["record_id"], "prediction_id": pred["prediction_id"]}
        require(canonical_json(saved) == canonical_json(expected_check), "saved checker differs from original source replay")
        require(saved["correct"] is (key == "correct"), "illustrative correctness label mismatch")
        target = checker.derive_target(packet["source"], query)
        require(target["target_digest"] == saved["target_digest"], "replayed target digest mismatch")
        world, labels = _label_map(packet)
        if query["kind"] == "parts":
            question = "Which nodes does " + labels[query["arguments"]["whole"]] + " directly contain?"
        else:
            question = "How is " + labels[query["arguments"]["part"]] + " reached from " + labels[query["arguments"]["whole"]] + "?"
        example = {**deepcopy(row), "question_display": question, "focus_world": deepcopy(world),
                   "prediction_display": _answer_text(pred["answer"], labels),
                   "checker_replay": {"status": "MATCHES_ORIGINAL_SAVED_CHECKER",
                                      "record": replay, "admissible_answers": target["admissible_answers"],
                                      "answer_displays": [_answer_text(a, labels) for a in target["admissible_answers"]],
                                      "scope": "DETERMINISTIC_DEVELOPMENT_CHECK_ONLY_NOT_MODEL_INFERENCE"}}
        examples.append(example)
        suffix = record["record_id"].split("-")[-1]
        node("task-" + key, "task-" + suffix, ("Correct" if key == "correct" else "Incorrect") + " saved development answer",
             "task", "development-p10", (("record_id", record["record_id"]),))
        node("input-" + key, "input-" + suffix, "Original task input", "input", "development-p10",
             (("packet_sha256", pred["packet_digest"]),))
        node("prediction-" + key, pred["prediction_id"], "Original Helm prediction", "prediction", "revision-1470",
             (("prediction_id", pred["prediction_id"]),))
        node("checker-" + key, "check-" + saved["check_digest"], "Original saved checker result", "checker", "development-p10",
             (("check_digest", saved["check_digest"]),), NodeStatus.VERIFIED if saved["correct"] else NodeStatus.REJECTED)
        part(PRESENT, "task-" + key, "selected DEVELOPMENT example")
        for child in ("input-" + key, "prediction-" + key, "checker-" + key, "model-checkpoint"):
            part("task-" + key, child, "retained task record association; not a model execution trace")
    atlas = AtlasSnapshot(tuple(node_rows), tuple(edges), PRESENT, PRESENT)
    body = {"schema_version": SCHEMA, "source_selection": selection, "source_selection_sha256": SELECTION_SHA256,
            "identity": identity, "examples": examples, "atlas": atlas.to_dict(), "boundary": dict(_BOUNDARY)}
    _bounded(body)
    return {**body, "document_sha256": digest(body)}


build_demo = build_recorded_atlas


def validate_recorded_atlas(document):
    _bounded(document)
    require(type(document) is dict and document.get("schema_version") == SCHEMA, "recorded atlas schema mismatch")
    expected = build_recorded_atlas()
    require(canonical_json(document) == canonical_json(expected),
            "recorded atlas differs from externally anchored saved records")
    return AtlasSnapshot.from_dict(expected["atlas"])


def load_recorded_atlas(raw):
    document = _decode(raw)
    validate_recorded_atlas(document)
    return document


def _address(document, atlas, node_id):
    require(type(node_id) is str and node_id in atlas.node_map(), "recorded address node missing")
    node = atlas.node_map()[node_id]
    return {"schema_version": ADDRESS_SCHEMA, "document_sha256": document["document_sha256"],
            "node_id": node_id, "item_id": node.idea_id, "version_id": dict(node.fields)["version_id"],
            "context_sha256": digest(node.context.to_dict())}


def exact_address(document, node_id):
    return _address(document, validate_recorded_atlas(document), node_id)


def address_text(address):
    require(type(address) is dict and set(address) == {"schema_version", "document_sha256", "node_id",
            "item_id", "version_id", "context_sha256"} and address["schema_version"] == ADDRESS_SCHEMA,
            "recorded address fields invalid")
    from .rpa_model import identifier
    for key in ("node_id", "item_id", "version_id"):
        identifier(address[key], key)
    for key in ("document_sha256", "context_sha256"):
        require(type(address[key]) is str and len(address[key]) == 64 and
                all(c in "0123456789abcdef" for c in address[key]), "recorded address hash invalid")
    return "cas-rpa-helm://" + address["document_sha256"] + "/" + quote(address["node_id"], safe="") + \
           "?context=" + address["context_sha256"] + "&version=" + quote(address["version_id"], safe="") + \
           "&item=" + quote(address["item_id"], safe="")


def parse_address(value):
    require(type(value) is str and len(value) <= 2048, "recorded address text bound")
    try:
        parts = urlsplit(value)
        query = parse_qs(parts.query, strict_parsing=True)
        require(set(query) == {"context", "version", "item"} and all(len(v) == 1 for v in query.values()),
                "recorded address query invalid")
        result = {"schema_version": ADDRESS_SCHEMA, "document_sha256": parts.netloc,
                  "node_id": unquote(parts.path[1:]), "context_sha256": query["context"][0],
                  "version_id": query["version"][0], "item_id": query["item"][0]}
        require(address_text(result) == value, "recorded address not canonical")
        return result
    except ValueError as exc:
        raise ContractError("invalid recorded address") from exc


def resolve_address(document, address):
    atlas = validate_recorded_atlas(document)
    address = parse_address(address) if type(address) is str else address
    _bounded(address, 4096)
    require(type(address) is dict and type(address.get("node_id")) is str, "recorded address node required")
    require(canonical_json(address) == canonical_json(_address(document, atlas, address["node_id"])),
            "recorded address binding mismatch")
    return atlas.node_map()[address["node_id"]]


def _cursor(document, atlas, cursor):
    _bounded(cursor, 8192)
    require(type(cursor) is dict and set(cursor) == {"schema_version", "document_sha256", "path",
            "focus_node_id", "reference_node_id"}, "recorded navigation fields")
    require(cursor["schema_version"] == NAVIGATION_SCHEMA and cursor["document_sha256"] == document["document_sha256"],
            "recorded navigation snapshot mismatch")
    path = cursor["path"]
    require(type(path) is list and 1 <= len(path) <= 32 and all(type(p) is str for p in path),
            "recorded navigation path bound")
    require(len(set(path)) == len(path) and path[0] == PRESENT, "recorded navigation cycle/root")
    nodes = atlas.node_map()
    require(all(p in nodes for p in path) and all(type(cursor[k]) is str and cursor[k] in nodes
            for k in ("focus_node_id", "reference_node_id")), "recorded navigation node missing")
    edges = {(e.source_id, e.target_id) for e in atlas.links if e.relation is LinkType.CONTAINS_PART}
    require(all(pair in edges for pair in zip(path, path[1:])), "recorded breadcrumb must follow containment")
    require(all(any(left == node_id for left, _ in edges) for node_id in path[1:]), "recorded leaf has no interior")
    return cursor


def start_navigation(document):
    validate_recorded_atlas(document)
    return {"schema_version": NAVIGATION_SCHEMA, "document_sha256": document["document_sha256"],
            "path": [PRESENT], "focus_node_id": PRESENT, "reference_node_id": PRESENT}


def inspect_node(document, cursor, node_id):
    atlas = validate_recorded_atlas(document)
    _cursor(document, atlas, cursor)
    return deepcopy(_cursor(document, atlas, {**cursor, "focus_node_id": node_id}))


def select_reference(document, cursor, node_id):
    atlas = validate_recorded_atlas(document)
    _cursor(document, atlas, cursor)
    return deepcopy(_cursor(document, atlas, {**cursor, "reference_node_id": node_id}))


def enter_node(document, cursor, node_id):
    atlas = validate_recorded_atlas(document)
    _cursor(document, atlas, cursor)
    require(any(e.source_id == cursor["path"][-1] and e.target_id == node_id and e.relation is LinkType.CONTAINS_PART
                for e in atlas.links), "recorded entry requires direct containment")
    return deepcopy(_cursor(document, atlas, {**cursor, "path": cursor["path"] + [node_id], "focus_node_id": node_id}))


def return_to(document, cursor, index):
    atlas = validate_recorded_atlas(document)
    _cursor(document, atlas, cursor)
    require(type(index) is int and 0 <= index < len(cursor["path"]), "recorded breadcrumb index invalid")
    path = cursor["path"][:index + 1]
    return deepcopy(_cursor(document, atlas, {**cursor, "path": path, "focus_node_id": path[-1]}))


def _panels(document):
    model = document["identity"]["final_checkpoint"]
    identity = document["identity"]
    model_panel = {"kind": "model", "title": "Original saved model identity",
                   "value": "Helm 2.0-experimental · revision 1470 · checkpoint " + model["sha256"],
                   "record": {"worker": identity["worker"], "final_checkpoint": model,
                              "model_identity": identity["model_identity"]}}
    availability = {"kind": "availability", "title": "Saved evidence limits",
                    "value": "CAS profile: Not assigned\nCAS-Ohm measurement: Not available\n"
                             "Original prediction: Available\nChecker result: Available\nInternal thought trace: Not recorded\n"
                             "Model weights: Retained Git bytes were hashed at selection; not included, decoded or run in this view.",
                    "record": {"checkpoint": identity["checkpoint_availability"], "boundary": document["boundary"]}}
    panels = {PRESENT: [{"kind": "task", "title": "Recorded run",
                        "value": "Two illustrative DEVELOPMENT answers from the saved Helm 2.0-experimental run.",
                        "record": {"selection": document["source_selection"], "identity": identity["worker"]}},
                       model_panel, availability],
              "model-checkpoint": [model_panel, availability]}
    for example in document["examples"]:
        key = example["example_id"]
        task = {"kind": "task", "title": "Original development task", "value": example["question_display"],
                "record": example["packet"]["record"]}
        original_input = {"kind": "input", "title": "Original saved model input",
                          "value": "Complete saved public packet: 64 retained training-bank worlds and one development focus world. "
                                   "The focus graph below contains the original supplied declarations.",
                          "record": example["packet"]}
        world = example["focus_world"]
        names = {row["ref"]: row["label"] for row in world["nodes"]}
        focus_source = {"kind": "input", "title": "Original focus-world graph",
                        "value": "; ".join(names[edge["source"]] + " contains " + names[edge["target"]]
                                           for edge in world["contains"]),
                        "record": world}
        prediction = {"kind": "prediction", "title": "Original Helm prediction",
                      "value": example["prediction_display"], "record": example["prediction"]}
        saved_check = {"kind": "checker", "title": "Original saved checker result",
                       "value": "CORRECT" if example["saved_check"]["correct"] else "INCORRECT",
                       "record": example["saved_check"]}
        replay = {"kind": "checker", "title": "Independent replay of saved checker",
                  "value": "Matches original saved check. Declared-source answer: " +
                           " | ".join(example["checker_replay"]["answer_displays"]),
                  "record": example["checker_replay"]}
        full = [task, original_input, focus_source, prediction, saved_check, replay, model_panel, availability]
        panels["task-" + key] = full
        panels["input-" + key] = [task, original_input, focus_source, availability]
        panels["prediction-" + key] = [task, prediction, saved_check, model_panel, availability]
        panels["checker-" + key] = [task, prediction, saved_check, replay, availability]
    return deepcopy(panels)


def view_payload(document):
    atlas = validate_recorded_atlas(document)
    addresses = {n.node_id: _address(document, atlas, n.node_id) for n in atlas.nodes}
    items = [{"node_id": n.node_id, "item_id": n.idea_id, "version_id": dict(n.fields)["version_id"],
              "label": n.label, "role": dict(n.fields)["role"], "cas_description": None} for n in atlas.nodes]
    return {"document": deepcopy(document), "atlas": atlas.to_dict(), "items": items,
            "identity": deepcopy(document["identity"]), "addresses": addresses,
            "address_texts": {key: address_text(value) for key, value in addresses.items()},
            "initial_navigation": {"schema_version": NAVIGATION_SCHEMA, "document_sha256": document["document_sha256"],
                                   "path": [PRESENT], "focus_node_id": PRESENT, "reference_node_id": PRESENT},
            "profiles": {}, "calculations": {}, "record_panels": _panels(document),
            "saved_view_schema": SAVED_VIEW_SCHEMA,
            "presentation": {
                "title": "Helm · saved development answers",
                "subtitle": "Original predictions, a real error, and the checker/model records that identify them.",
                "family_label": "CAS-RPA / RECORDED HELM DEVELOPMENT",
                "present_heading": "Archived run · fixed in this saved view",
                "present_status": "Saved run snapshot",
                "present_basis": "Original retained run record; not a live Helm state",
                "boundary_summary": "These are actual saved DEVELOPMENT predictions, including an incorrect answer. No model is run by this viewer.",
                "boundary_details": "Two post-selected development examples from Helm 2.0-experimental. "
                                    "Original predictions and saved checker records are retained; the separate deterministic checker replay "
                                    "does not run the model. No CAS profile, CAS-Ohm quantity, internal thought trace, live state or new learning is supplied.",
                "empty_ohm_text": "No CAS-Ohm quantities were recorded for this task.",
                "saved_view_schema": SAVED_VIEW_SCHEMA,
                "cas_empty_text": "This is a typed Helm task record. No CAS compiler expression was recorded.",
                "status_labels": {"observed": "Archived run record", "unknown": "Saved evidence",
                                  "verified": "Saved checker: correct", "rejected": "Saved checker: incorrect"},
            }}


def navigation_view(document, cursor):
    atlas = validate_recorded_atlas(document)
    _cursor(document, atlas, cursor)
    scope = cursor["path"][-1]
    links = [e for e in atlas.links if e.source_id == scope and e.relation is LinkType.CONTAINS_PART]
    keys = {scope} | {e.target_id for e in links}
    return {"document_sha256": document["document_sha256"], "current_state_id": PRESENT,
            "scope_id": scope, "breadcrumb": list(cursor["path"]), "focus_node_id": cursor["focus_node_id"],
            "reference_node_id": cursor["reference_node_id"],
            "nodes": [atlas.node_map()[key].to_dict() for key in sorted(keys)],
            "links": [e.to_dict() for e in links], "record_panels": _panels(document)[cursor["focus_node_id"]],
            "profile_status": "NOT_ASSIGNED", "ohm_status": "NOT_RECORDED", "authority": "INSPECTION_ONLY"}
