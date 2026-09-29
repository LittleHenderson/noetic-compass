"""Versioned authored binding sidecar; the historical cube stays unchanged."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

SCIENTIFIC_SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
SCHEMA = "helm.cube-binding-sidecar/1"
PUBLIC_PROFILE = "helm.cube-parts-public/1"
ROLE_SCHEME = "AUTHORED_CONTAINS_ENDPOINTS_V1_NOT_A_FITTED_ROLE_SCHEME"
BUNDLE_FIELDS = {"schema_version", "context", "sources", "cube_nodes", "branches",
                 "views", "mappings", "lesson_family_id", "learner_view_requirement",
                 "relation_profiles"}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def bounded_copy(value):
    """Reject cycles/non-JSON/oversize trees before copying candidate input."""
    count, active = 0, set()
    def walk(item, depth):
        nonlocal count
        count += 1
        require(count <= 30000 and depth <= 20, "CB1_TREE_BOUND")
        require(type(item) in (dict, list, str, int, bool, type(None)), "CB1_JSON_TYPE")
        if type(item) in (dict, list):
            require(id(item) not in active, "CB1_INPUT_CYCLE")
            active.add(id(item))
            if type(item) is dict:
                require(all(type(k) is str for k in item), "CB1_JSON_KEY")
            for child in (item.values() if type(item) is dict else item):
                walk(child, depth + 1)
            active.remove(id(item))
        elif type(item) is str:
            require(len(item) <= 16384, "CB1_STRING_BOUND")
    walk(value, 0)
    require(len(canonical(value).encode()) <= 1024 * 1024, "CB1_BYTE_BOUND")
    return deepcopy(value)


def public_runtime():
    """Use the incumbent cas_meta2 package; never copy or execute a second learner.

    File pins are compatibility checks. The admitted worker still owns loaded
    source attestation; these checks are not a runtime or cloud admission.
    """
    pins = json.loads(Path(__file__).with_name("SOURCE_PINS.json").read_text())
    modules = {}
    for short, row in pins["modules"].items():
        module = importlib.import_module(row["module"])
        raw = Path(module.__file__).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == row["sha256"], "CB1_SOURCE_MISMATCH:" + short)
        modules[short] = module
    return modules


def checked_cube(bundle, runtime):
    value = bounded_copy(bundle)
    require(type(value) is dict and set(value) <= BUNDLE_FIELDS, "CB1_PUBLIC_BUNDLE_FIELDS")
    require(value.get("schema_version") == "cas.cube-bundle/0.1", "CB1_CUBE_CODEC")
    require(3 <= len(value.get("cube_nodes", [])) <= 10, "CB1_TYPED_NODE_BOUND")
    require(0 < len(value.get("branches", [])) <= 90, "CB1_BRANCH_BOUND")
    # containment_graph historically normalizes all predicates to contains.
    require(all(b.get("predicate") == "contains" for b in value["branches"]), "CB1_PREDICATE")
    runtime["cube_node"].validate_bundle(value)
    return value


def binding_sidecar(bundle, *, packet_sha256, node_mapping, runtime):
    """Authored-only metadata. Never feed this envelope to the learner/readout fit."""
    value = checked_cube(bundle, runtime)
    nodes = sorted(value["cube_nodes"], key=lambda n: n["node_id"])
    branches = sorted(value["branches"], key=lambda b: b["branch_id"])
    frames = []
    for branch in branches:
        frames.append({"frame_ref": branch["branch_id"], "predicate": "contains",
            "context_ref": branch["context_id"], "commonality": deepcopy(branch["commonality"]),
            "bindings": [{"occurrence_ref": branch["branch_id"] + "/" + role,
                          "role": role, "filler_ref": branch[field],
                          "filler_revision": next(n["revision"] for n in nodes if n["node_id"] == branch[field])}
                         for role, field in (("source", "source_node_id"), ("target", "target_node_id"))]})
    body = {"schema": SCHEMA, "scientific_source": SCIENTIFIC_SOURCE,
        "cube_schema": "cas.cube-node/0.1", "public_profile": PUBLIC_PROFILE,
        "role_scheme": ROLE_SCHEME, "origin": "AUTHORED_STRUCTURE_NOT_NEURAL_INFERENCE",
        "bundle_sha256": digest(value), "packet_sha256": packet_sha256,
        "context": deepcopy(value["context"]), "node_mapping": deepcopy(node_mapping),
        "nodes": [{"node_ref": n["node_id"], "revision": n["revision"], "core": deepcopy(n["core"]),
            "faces": {key: {"meaning": runtime["cube_node"].FACE_ROLES[key],
                            "authored_availability": n["faces"][key]["availability"],
                            "learner_visibility": "MASKED",
                            "known_empty_direct_inventory": (key == "face_5" and
                                value["context"]["contains_inventory_complete"] is True and
                                not any(b["source_node_id"] == n["node_id"] for b in branches))}
                      for key in runtime["cube_node"].FACE_KEYS}} for n in nodes],
        "frames": frames, "view_maps": deepcopy(value["mappings"]),
        "fit_features": "NOT_EXPORTED; AUDIT_IDS_AND_AUTHOR_ANNOTATIONS_ARE_NOT_ROLES",
        "neural_capture": "NOT_RUN", "promotion": False}
    return {**body, "sidecar_sha256": digest(body)}
