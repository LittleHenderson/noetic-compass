"""The lab's ONE door for reading Q3 records. Nothing downstream calls json.loads on a data file directly.

Why this exists. Until 2026-09-21 every consumer parsed the .jsonl files raw. The strict checks lived in
`reference_ops.py` and were re-applied to loaded records only by the pytest file, so a hand-edited data file
would have been exported as VALID unless someone also ran the tests. (An outside reviewer pointed at the same
class of gap in the frozen engine: its state vector can be loaded without re-running its constructor's checks.)

Two doors, deliberately separate:
  load_visible(data_dir, family, split)   the LEARNER's door: the visible file only. Refuses a file that carries
                                          a withheld field.
  load_split(data_dir, family, split)     the EVALUATOR's door: visible + sealed, joined, and RE-CHECKED against
                                          the strict reference. A `learner*` file may not call it (tested).

Both refuse, with a named code: a file whose sha256 is not the one in the manifest; NaN / Infinity; duplicate
JSON keys; a row that is not an object; a missing or duplicate record id. `check_contract_binding` refuses a
data set whose manifest cites a contract digest other than the one in OPERATION_CONTRACTS.json.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reference_ops as ref  # noqa: E402

FAMILIES, SPLITS = ("R", "G", "A", "C"), ("train", "dev", "eval")
CASE_FAMILIES = ("op0_same_domain", "op0_cross_domain", "nonidentity_same_domain", "nonidentity_cross_domain")


class Q3LoadError(ValueError):
    """A data file that must not be used. The message starts with a code, e.g. 'FILE_HASH_MISMATCH: ...'."""


def strict_loads(text, where="<text>"):
    """json.loads that refuses what json.loads silently accepts: NaN / Infinity and duplicate object keys."""
    def constant(name):
        raise Q3LoadError("NONFINITE_NUMBER: %s in %s" % (name, where))

    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise Q3LoadError("DUPLICATE_JSON_KEYS: %s in %s" % (sorted({k for k in keys if keys.count(k) > 1}), where))
        return dict(items)
    try:
        return json.loads(text, parse_constant=constant, object_pairs_hook=pairs)
    except json.JSONDecodeError as error:
        raise Q3LoadError("MALFORMED_JSON: %s in %s" % (error.msg, where))


def manifest_of(data_dir):
    return strict_loads((pathlib.Path(data_dir) / "manifest.json").read_text(encoding="utf-8"), "manifest.json")


def check_contract_binding(data_dir, contract_path=None):
    contract = strict_loads(pathlib.Path(contract_path or HERE / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"), "OPERATION_CONTRACTS.json")
    cited = manifest_of(data_dir).get("operation_contracts_digest")
    if cited != contract["contract_digest"]:
        raise Q3LoadError("CONTRACT_DIGEST_MISMATCH: the data cites %s, OPERATION_CONTRACTS.json is %s -- rebuild the data"
                          % (str(cited)[:16], contract["contract_digest"][:16]))
    return cited


def _rows(data_dir, name, manifest):
    path = pathlib.Path(data_dir) / name
    if name not in manifest["files"]:
        raise Q3LoadError("FILE_NOT_IN_MANIFEST: %s" % name)
    body = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(body).hexdigest() != manifest["files"][name]["sha256"]:
        raise Q3LoadError("FILE_HASH_MISMATCH: %s differs from the manifest" % name)
    rows, seen = [], set()
    for number, line in enumerate(body.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = strict_loads(line, "%s line %d" % (name, number))
        if not isinstance(row, dict):
            raise Q3LoadError("ROW_NOT_AN_OBJECT: %s line %d" % (name, number))
        rid = row.get("record_id")
        if not isinstance(rid, str) or not rid:
            raise Q3LoadError("MISSING_RECORD_ID: %s line %d" % (name, number))
        if rid in seen:
            raise Q3LoadError("DUPLICATE_RECORD_ID: %s in %s" % (rid, name))
        seen.add(rid)
        rows.append(row)
    if len(rows) != manifest["files"][name]["records"]:
        raise Q3LoadError("RECORD_COUNT_MISMATCH: %s has %d rows, manifest says %d" % (name, len(rows), manifest["files"][name]["records"]))
    return rows


def load_visible(data_dir, family, split):
    """The learner's door. Returns the visible rows; refuses any row that carries a withheld or undeclared field."""
    manifest = manifest_of(data_dir)
    rows = _rows(data_dir, "visible_%s_%s.jsonl" % (family, split), manifest)
    allowed, withheld = set(manifest["visibility"][family]["visible"]), set(manifest["visibility"][family]["withheld"])
    for row in rows:
        if set(row) & withheld or not set(row) <= allowed:
            raise Q3LoadError("WITHHELD_OR_UNDECLARED_FIELD_IN_VISIBLE_FILE: %s %s" % (row["record_id"], sorted(set(row) - allowed)))
    return rows


def refuses(observation):
    """Does the strict reference refuse this family-A observation? (wrong key set, type, range, bool, float, string...)"""
    try:
        if not isinstance(observation, dict) or set(observation) != {"operator", "source", "target"}:
            return True
        ref.is_admissible(observation["operator"], tuple(observation["source"]), tuple(observation["target"]))
        return False
    except (ref.InvalidInput, TypeError, ValueError):
        return True


def _check_A(visible, sealed):
    o, rid = visible["observation"], visible["record_id"]
    if sealed.get("outcome") == "INVALID_INPUT":
        if not refuses(o):
            raise Q3LoadError("SEALED_SAYS_INVALID_BUT_REFERENCE_ACCEPTS: %s" % rid)
        return
    if refuses(o):
        raise Q3LoadError("REFERENCE_REFUSES_A_ROW_SEALED_AS_VALID: %s" % rid)
    s, t = tuple(o["source"]), tuple(o["target"])
    target, swapped = ref.is_admissible(o["operator"], s, t), ref.is_admissible(o["operator"], t, s)
    if sealed.get("target") is not target or sealed.get("swapped_target") is not swapped or sealed.get("order_flip") is not (target != swapped):
        raise Q3LoadError("SEALED_TARGET_DISAGREES_WITH_REFERENCE: %s" % rid)
    same = s[0] == t[0]
    family = ("op0_same_domain" if same else "op0_cross_domain") if o["operator"] == 0 else ("nonidentity_same_domain" if same else "nonidentity_cross_domain")
    if "case_family" in sealed and sealed["case_family"] != family:
        raise Q3LoadError("CASE_FAMILY_WRONG: %s" % rid)


def _check_C(visible, sealed):
    if not isinstance(visible["observation"], str) or isinstance(sealed.get("target"), bool) or sealed.get("target") not in range(10):
        raise Q3LoadError("FAMILY_C_ROW_MALFORMED: %s" % visible["record_id"])


def _check_reconstruction(visible, sealed):
    if not isinstance(visible["observation"], str) or not isinstance(sealed.get("target_canonical_ast"), (dict, list, str)):
        raise Q3LoadError("RECONSTRUCTION_ROW_MALFORMED: %s" % visible["record_id"])


def load_split(data_dir, family, split):
    """The evaluator's door. Returns [(visible_row, sealed_row), ...] in file order, every pair re-checked."""
    manifest = manifest_of(data_dir)
    visible = load_visible(data_dir, family, split)
    sealed = {r["record_id"]: r for r in _rows(data_dir, "sealed_%s_%s.jsonl" % (family, split), manifest)}
    if set(sealed) != {v["record_id"] for v in visible}:
        raise Q3LoadError("VISIBLE_AND_SEALED_IDS_DIFFER: %s %s" % (family, split))
    check = {"A": _check_A, "C": _check_C}.get(family, _check_reconstruction)
    pairs = []
    for v in visible:
        s = sealed[v["record_id"]]
        if s.get("family") != family or v.get("family") != family:
            raise Q3LoadError("WRONG_FAMILY: %s" % v["record_id"])
        check(v, s)
        pairs.append((v, s))
    return pairs
