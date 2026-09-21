"""The lab's ONE door for reading Q3 records (loader 0.2). Nothing downstream calls json.loads on a data file directly.

Why this exists. Until 2026-09-21 every consumer parsed the .jsonl files raw, and the strict checks were re-applied
to loaded records only by the pytest file. Loader 0.1 closed that for family A. An attacker then showed (60+ forged
copies) that everything else in 0.1 was a SHAPE check. 0.2 answers each finding by name:

  * WHO MAY SEE WHAT IS FIXED IN CODE. 0.1 read the list of learner-visible fields from the manifest -- the very file
    a forger edits -- so answers could be put into the learner's file and still pass. The visible and sealed key sets
    are now constants here; a manifest that says otherwise is refused (VISIBILITY_POLICY_EDITED), and every row must
    carry EXACTLY its key set (ROW_KEYS_WRONG).
  * EVERY TARGET THE LAB CAN RECOMPUTE IS RECOMPUTED. Family A against the strict reference (answer, swapped answer,
    order-flip, case family, cell, refusal fields). Family C by parsing the chain and evaluating it with the reference
    compose (target AND depth). Families R and G cannot be recompiled here (the compiler lives outside this sparse
    worktree), so the loader checks what needs no compiler -- the canonical text equals the canonical form of the AST,
    the node count, the strict-shape key, the bare tree-shape key and the depth -- and SAYS SO: `verification_level`.
  * RECORD IDS ARE RE-DERIVED from the manifest's seed and the row's position (RECORD_ID_NOT_POSITIONAL).
  * THE DATA SET IS CHECKED AS A WHOLE by `load_dataset`: ids and observations disjoint across splits, A cells / R strict
    shapes / G bare tree shapes disjoint, G eval deeper than every G train row, every A case family present in dev and
    eval, counts equal to the manifest, no undeclared .jsonl file in the folder, baselines.json hashed.
  * THE MANIFEST IS PINNED OUTSIDE THE DATA FOLDER (`Q3_DATA_PINS.json`, beside this file). A forged copy of the data
    carries its own forged manifest; it cannot carry the pin. `check_pins` refuses it (MANIFEST_NOT_THE_PINNED_ONE).
  * No exception other than Q3LoadError escapes for a malformed manifest, a missing file or undecodable bytes.

Two doors, deliberately separate:
  load_visible(data_dir, family, split)   the LEARNER's door: the visible file only.
  load_split / load_dataset               the EVALUATOR's doors. A `learner*` file may not call them (tested).
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reference_ops as ref  # noqa: E402

FAMILIES, SPLITS = ("R", "G", "A", "C"), ("train", "dev", "eval")
CASE_FAMILIES = ("op0_same_domain", "op0_cross_domain", "nonidentity_same_domain", "nonidentity_cross_domain")
PINS = HERE / "Q3_DATA_PINS.json"

# Fixed in code on purpose. The manifest must agree with these; it cannot change them.
VISIBLE_KEYS = {"R": {"record_id", "family", "mode", "observation"}, "G": {"record_id", "family", "mode", "observation"},
                "A": {"record_id", "family", "mode", "operation_id", "observation"}, "C": {"record_id", "family", "mode", "operation_id", "observation"}}
_RECON = {"record_id", "family", "target_canonical_ast", "target_ast", "ast_size", "shape_key", "tree_shape_key", "depth", "validity", "oracle"}
SEALED_KEYS = {"R": _RECON, "G": _RECON,
               "A_valid": {"record_id", "family", "outcome", "target", "cell", "order_flip", "case_family", "swapped_target", "oracle", "trace"},
               "A_refusal": {"record_id", "family", "outcome", "target", "cell", "order_flip", "refusal_kind", "oracle", "trace"},
               "C": {"record_id", "family", "outcome", "target", "depth", "oracle", "trace"}}
REFUSAL_KINDS = {"bad_operator", "bad_domain", "bad_noetic", "float", "missing_key", "bool", "extra_key", "float_equal_to_int", "string"}
VERIFICATION_LEVEL = {"A": "RECOMPUTED_FROM_THE_REFERENCE", "C": "RECOMPUTED_FROM_THE_REFERENCE",
                      "R": "STRUCTURE_CHECKED__TARGET_NOT_RECOMPILED (the compiler is outside this worktree; the test suite recompiles a sample)",
                      "G": "STRUCTURE_CHECKED__TARGET_NOT_RECOMPILED (the compiler is outside this worktree; the test suite recompiles a sample)"}


class Q3LoadError(ValueError):
    """A data file that must not be used. The message starts with a code, e.g. 'FILE_HASH_MISMATCH: ...'."""


def verification_level(family):
    return VERIFICATION_LEVEL[family]


def _lf(path):
    try:
        return pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")
    except OSError as error:
        raise Q3LoadError("DATA_FILE_MISSING: %s (%s)" % (pathlib.Path(path).name, type(error).__name__))


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
    body = _lf(pathlib.Path(data_dir) / "manifest.json")
    try:
        manifest = strict_loads(body.decode("utf-8"), "manifest.json")
        files, seed, visibility = manifest["files"], manifest["seed"], manifest["visibility"]
        assert isinstance(files, dict) and isinstance(seed, int) and not isinstance(seed, bool) and isinstance(visibility, dict)
        assert all(isinstance(v, dict) and isinstance(v.get("sha256"), str) for v in files.values())
    except Q3LoadError:
        raise
    except Exception as error:
        raise Q3LoadError("MANIFEST_MALFORMED: %s" % type(error).__name__)
    for family in FAMILIES:                                   # the manifest may DESCRIBE the policy; it may not change it
        declared = visibility.get(family, {})
        withheld = (SEALED_KEYS["A_valid"] | SEALED_KEYS["A_refusal"]) if family == "A" else SEALED_KEYS[family]
        if set(declared.get("visible", [])) != VISIBLE_KEYS[family] or set(declared.get("withheld", [])) != withheld - {"record_id", "family"}:
            raise Q3LoadError("VISIBILITY_POLICY_EDITED: the manifest's field lists for family %s are not the ones fixed in q3_load.py" % family)
    return manifest


def manifest_sha(data_dir):
    return hashlib.sha256(_lf(pathlib.Path(data_dir) / "manifest.json")).hexdigest()


def check_pins(data_dir):
    """The manifest must be the one pinned OUTSIDE the data folder, for this data version."""
    manifest = manifest_of(data_dir)
    pins = strict_loads(_lf(PINS).decode("utf-8"), PINS.name)
    pin = pins.get("data_versions", {}).get(manifest.get("schema"))
    if not pin:
        raise Q3LoadError("NO_PIN_FOR_THIS_DATA_VERSION: %s" % manifest.get("schema"))
    if manifest_sha(data_dir) != pin["manifest_sha256"]:
        raise Q3LoadError("MANIFEST_NOT_THE_PINNED_ONE: %s" % manifest.get("schema"))
    return pin


def check_contract_binding(data_dir, contract_path=None):
    contract = strict_loads(_lf(contract_path or HERE / "OPERATION_CONTRACTS.json").decode("utf-8"), "OPERATION_CONTRACTS.json")
    cited = manifest_of(data_dir).get("operation_contracts_digest")
    if cited != contract["contract_digest"]:
        raise Q3LoadError("CONTRACT_DIGEST_MISMATCH: the data cites %s, OPERATION_CONTRACTS.json is %s -- rebuild the data"
                          % (str(cited)[:16], contract["contract_digest"][:16]))
    return cited


def _record_id(seed, family, split, index):
    return hashlib.sha256(("%d:%s:%s:%d" % (seed, family, split, index)).encode("utf-8")).hexdigest()[:24]


def _rows(data_dir, name, manifest, family, split):
    if name not in manifest["files"]:
        raise Q3LoadError("FILE_NOT_IN_MANIFEST: %s" % name)
    body = _lf(pathlib.Path(data_dir) / name)
    if hashlib.sha256(body).hexdigest() != manifest["files"][name]["sha256"]:
        raise Q3LoadError("FILE_HASH_MISMATCH: %s differs from the manifest" % name)
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        raise Q3LoadError("NOT_UTF8: %s" % name)
    rows, seen = [], set()
    for number, line in enumerate(text.split("\n"), 1):      # split on the newline byte only
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
        if rid != _record_id(manifest["seed"], family, split, len(rows)):
            raise Q3LoadError("RECORD_ID_NOT_POSITIONAL: %s line %d" % (name, number))
        seen.add(rid)
        rows.append(row)
    if len(rows) != manifest["files"][name].get("records"):
        raise Q3LoadError("RECORD_COUNT_MISMATCH: %s has %d rows, manifest says %s" % (name, len(rows), manifest["files"][name].get("records")))
    return rows


def load_visible(data_dir, family, split):
    """The learner's door. Every row carries EXACTLY the visible key set fixed in this file."""
    manifest = manifest_of(data_dir)
    rows = _rows(data_dir, "visible_%s_%s.jsonl" % (family, split), manifest, family, split)
    for row in rows:
        if set(row) != VISIBLE_KEYS[family]:
            raise Q3LoadError("ROW_KEYS_WRONG: visible %s has %s" % (row["record_id"], sorted(set(row) ^ VISIBLE_KEYS[family])))
        if row["family"] != family:
            raise Q3LoadError("WRONG_FAMILY: %s" % row["record_id"])
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


def case_family(operator, source, target):
    same = source[0] == target[0]
    if operator == 0:
        return "op0_same_domain" if same else "op0_cross_domain"
    return "nonidentity_same_domain" if same else "nonidentity_cross_domain"


def _check_A(visible, sealed):
    o, rid = visible["observation"], visible["record_id"]
    if sealed.get("outcome") == "INVALID_INPUT":
        if set(sealed) != SEALED_KEYS["A_refusal"]:
            raise Q3LoadError("ROW_KEYS_WRONG: sealed refusal %s" % rid)
        if not refuses(o):
            raise Q3LoadError("SEALED_SAYS_INVALID_BUT_REFERENCE_ACCEPTS: %s" % rid)
        if sealed["target"] is not None or sealed["cell"] is not None or sealed["order_flip"] is not None or sealed["refusal_kind"] not in REFUSAL_KINDS:
            raise Q3LoadError("REFUSAL_ROW_CARRIES_AN_ANSWER_OR_AN_UNKNOWN_KIND: %s" % rid)
        return
    if sealed.get("outcome") != "CORRECT_IF_MATCH" or set(sealed) != SEALED_KEYS["A_valid"]:
        raise Q3LoadError("ROW_KEYS_WRONG: sealed A row %s (outcome %r)" % (rid, sealed.get("outcome")))
    if refuses(o):
        raise Q3LoadError("REFERENCE_REFUSES_A_ROW_SEALED_AS_VALID: %s" % rid)
    s, t = tuple(o["source"]), tuple(o["target"])
    target, swapped = ref.is_admissible(o["operator"], s, t), ref.is_admissible(o["operator"], t, s)
    if sealed["target"] is not target or sealed["swapped_target"] is not swapped or sealed["order_flip"] is not (target != swapped):
        raise Q3LoadError("SEALED_TARGET_DISAGREES_WITH_REFERENCE: %s" % rid)
    if sealed["case_family"] != case_family(o["operator"], s, t):
        raise Q3LoadError("CASE_FAMILY_WRONG: %s" % rid)
    if sealed["cell"] != "%d:%s>%s" % (o["operator"], s[0], t[0]):
        raise Q3LoadError("CELL_WRONG: %s" % rid)


_TOKEN = re.compile(r"\s*(compose\(|\)|,|\d)")


def evaluate_chain(text):
    """Parse a family-C chain -- only `compose(x, y)` and single digits -- and return (value, nesting depth)."""
    tokens, position = [], 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            if text[position:].strip() == "":
                break
            raise Q3LoadError("C_CHAIN_UNPARSEABLE: %r" % text[:60])
        tokens.append(match.group(1))
        position = match.end()

    def parse(i):
        if i < len(tokens) and tokens[i].isdigit():
            return int(tokens[i]), 0, i + 1
        if i < len(tokens) and tokens[i] == "compose(":
            a, da, i = parse(i + 1)
            if i >= len(tokens) or tokens[i] != ",":
                raise Q3LoadError("C_CHAIN_UNPARSEABLE: %r" % text[:60])
            b, db, i = parse(i + 1)
            if i >= len(tokens) or tokens[i] != ")":
                raise Q3LoadError("C_CHAIN_UNPARSEABLE: %r" % text[:60])
            return ref.compose(a, b), 1 + da + db, i + 1
        raise Q3LoadError("C_CHAIN_UNPARSEABLE: %r" % text[:60])
    value, depth, end = parse(0)
    if end != len(tokens):
        raise Q3LoadError("C_CHAIN_UNPARSEABLE: %r" % text[:60])
    return value, depth


def _check_C(visible, sealed):
    rid = visible["record_id"]
    if set(sealed) != SEALED_KEYS["C"] or sealed.get("outcome") != "CORRECT_IF_MATCH":
        raise Q3LoadError("ROW_KEYS_WRONG: sealed C row %s" % rid)
    if not isinstance(visible["observation"], str):
        raise Q3LoadError("FAMILY_C_ROW_MALFORMED: %s" % rid)
    value, depth = evaluate_chain(visible["observation"])
    if type(sealed["target"]) is not int or sealed["target"] != value:
        raise Q3LoadError("C_TARGET_DISAGREES_WITH_REFERENCE: %s" % rid)
    if type(sealed["depth"]) is not int or sealed["depth"] != depth:
        raise Q3LoadError("C_DEPTH_WRONG: %s" % rid)


def _check_reconstruction(visible, sealed):
    import q3_behaviour_records as q3            # canonical / strict_shape / tree_shape live with the generator
    rid = visible["record_id"]
    if set(sealed) != _RECON or sealed.get("validity") != "VALID":
        raise Q3LoadError("ROW_KEYS_WRONG: sealed %s row %s" % (sealed.get("family"), rid))
    ast = sealed["target_ast"]
    if not isinstance(visible["observation"], str) or not isinstance(ast, dict) or not isinstance(sealed["target_canonical_ast"], str):
        raise Q3LoadError("RECONSTRUCTION_ROW_MALFORMED: %s" % rid)
    if q3.canonical(ast) != sealed["target_canonical_ast"]:
        raise Q3LoadError("CANONICAL_TEXT_IS_NOT_THE_CANONICAL_FORM_OF_THE_AST: %s" % rid)
    if "CO-" in sealed["target_canonical_ast"] or q3.to_lab_spelling(q3.to_compiler_spelling(ast)) != ast:
        raise Q3LoadError("TARGET_SPELLING_NOT_THE_LAB_FORM: %s" % rid)
    if type(sealed["ast_size"]) is not int or sealed["ast_size"] != q3._ast_size(ast):
        raise Q3LoadError("AST_SIZE_WRONG: %s" % rid)
    if sealed["shape_key"] != q3._sha_json(q3.strict_shape(q3.to_compiler_spelling(ast)))[:16]:
        raise Q3LoadError("SHAPE_KEY_WRONG: %s" % rid)
    if sealed["family"] == "G":
        shape = q3.tree_shape(ast)
        if sealed["tree_shape_key"] != q3._sha_json(shape)[:16] or type(sealed["depth"]) is not int or sealed["depth"] != q3.tree_depth(shape):
            raise Q3LoadError("TREE_SHAPE_OR_DEPTH_WRONG: %s" % rid)


def load_split(data_dir, family, split):
    """The evaluator's door for ONE file pair. Returns [(visible_row, sealed_row), ...] in file order, every pair re-checked."""
    manifest = manifest_of(data_dir)
    visible = load_visible(data_dir, family, split)
    sealed = _rows(data_dir, "sealed_%s_%s.jsonl" % (family, split), manifest, family, split)
    if [r["record_id"] for r in sealed] != [v["record_id"] for v in visible]:
        raise Q3LoadError("VISIBLE_AND_SEALED_IDS_DIFFER: %s %s" % (family, split))
    check = {"A": _check_A, "C": _check_C}.get(family, _check_reconstruction)
    pairs = []
    for v, s in zip(visible, sealed):
        if s.get("family") != family:
            raise Q3LoadError("WRONG_FAMILY: %s" % v["record_id"])
        check(v, s)
        pairs.append((v, s))
    return pairs


def load_dataset(data_dir, pinned=True):
    """The evaluator's door for the WHOLE data set. Everything load_split checks, plus what only shows across files."""
    data_dir = pathlib.Path(data_dir)
    if pinned:
        check_pins(data_dir)
    check_contract_binding(data_dir)
    manifest = manifest_of(data_dir)
    declared = set(manifest["files"])
    on_disk = {p.name for p in data_dir.glob("*.jsonl")}
    if on_disk - declared:
        raise Q3LoadError("UNDECLARED_FILE_ON_DISK: %s" % sorted(on_disk - declared))
    if "baselines.json" not in declared or hashlib.sha256(_lf(data_dir / "baselines.json")).hexdigest() != manifest["files"]["baselines.json"]["sha256"]:
        raise Q3LoadError("BASELINES_NOT_THE_HASHED_ONES")
    strict_loads(_lf(data_dir / "baselines.json").decode("utf-8"), "baselines.json")
    data = {f: {s: load_split(data_dir, f, s) for s in SPLITS} for f in FAMILIES}
    for f in FAMILIES:
        keys = {s: {json.dumps(v["observation"], sort_keys=True) for v, _ in data[f][s]} for s in SPLITS}
        ids = {s: {v["record_id"] for v, _ in data[f][s]} for s in SPLITS}
        for a, b in (("train", "dev"), ("train", "eval"), ("dev", "eval")):
            if keys[a] & keys[b] or ids[a] & ids[b]:
                raise Q3LoadError("SPLITS_NOT_DISJOINT: family %s, %s and %s share %d observation(s)" % (f, a, b, len(keys[a] & keys[b])))
        if any(not data[f][s] for s in SPLITS):
            raise Q3LoadError("EMPTY_SPLIT: family %s" % f)
        if manifest.get("counts") and any(manifest["counts"].get("%s_%s" % (f, s)) != len(data[f][s]) for s in SPLITS):
            raise Q3LoadError("COUNTS_DIFFER_FROM_MANIFEST: family %s" % f)
    group = {"A": lambda sd: sd.get("cell"), "R": lambda sd: sd["shape_key"], "G": lambda sd: sd["tree_shape_key"]}
    for f, key in group.items():
        held = {s: {key(sd) for _, sd in data[f][s]} - {None} for s in SPLITS}
        for a, b in (("train", "dev"), ("train", "eval"), ("dev", "eval")):
            if held[a] & held[b]:
                raise Q3LoadError("HELD_OUT_GROUPS_SHARED: family %s, %s and %s" % (f, a, b))
    if not min(sd["depth"] for _, sd in data["G"]["eval"]) > max(sd["depth"] for _, sd in data["G"]["train"]):
        raise Q3LoadError("G_EVAL_NOT_DEEPER_THAN_TRAIN")
    for s in ("dev", "eval"):
        for fam in CASE_FAMILIES:
            if sum(1 for _, sd in data["A"][s] if sd.get("case_family") == fam) < 16:
                raise Q3LoadError("CASE_FAMILY_UNDER_16_ROWS: %s in %s" % (fam, s))
    return data
