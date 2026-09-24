"""Q4-SDG-1 A-versus-B 0.2: torch-free preparation -- shared panels, teaching pools, edits, the B package check.

NON-NEURAL. Imports no torch. Used three ways:
  * by q4_ab_train.py on the AWS T4 machine, before any model exists;
  * by the laptop (`measure`) to compute the digests frozen in q4_ab_rules.py, from VISIBLE files only;
  * by the AWS CPU data-build job (`package-digests`) to compare two builds of the B package byte for byte.

CUSTODY. Q3 rows come only through q4_error_panel.visible_rows (pinned manifest, hashed visible files, a data folder
with no eval or sealed file). Targets are RECOMPILED from the visible text with the pinned compiler; no sealed file of
Q3 or of the B package is ever opened here, except by `package-digests`, which hashes the bytes of the two B builds
the data-build machine has just generated (it never parses them).

PANELS (review M2). SP1 = FAMILIAR_STRUCTURE_NEW_CONTENT: 256 visible G train rows, drawn (seeded) from the rows the
error-panel diagnostic never showed, allocated to the G-train shapes in proportion to their rows (largest remainder),
reserved before any arm and never taught to either arm. SP2 = the visible G dev split (256), with the 48 rows the
diagnostic inspected flagged. A pool = G train minus SP1 (and minus any row whose content equals a panel row).
B pool = the pinned package's A/B/C train rows minus any row whose content equals an SP1 or SP2 row. The
one-field-edit panel EDIT64 = SP1 rows 0, 4, 8, ... (64 rows).

  python -B q4_ab_prep.py measure --run-dir <run_001> --data-dir data/q3_v0_7
  python -B q4_ab_prep.py package-digests --build <dir> --rebuild <dir> --verify-exit <code> --out <file>
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import platform
import random
import re
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import q4_ab_rules as rules  # noqa: E402
import q4_error_panel as ep  # noqa: E402
import q4_sdg_curriculum as sdg  # noqa: E402
from learner_q4_decoder import allowed_next  # noqa: E402

DIGESTS_SCHEMA = "helm-cas-expression-lab.q4-sdg-ab-package-digests/0.2"
EXPECTED_PACKAGE_FILES = tuple(sorted("%s_%s_%s.jsonl" % (kind, lesson, split) for kind in ("visible", "sealed")
                                      for lesson in ("A", "B", "C") for split in ("train", "dev", "feedback")))
_HEX64 = re.compile(r"[0-9a-f]{64}")


class PrepError(ValueError):
    """Fail closed. The message starts with one of q4_ab_rules.STOP_CODES."""


def _stop(code, detail=""):
    if code not in rules.STOP_CODES:
        raise ValueError("UNKNOWN_STOP_CODE: %s" % code)
    return PrepError("%s: %s" % (code, detail) if detail else code)


# ------------------------------------------------------------------------------------------------------------
# Q3 side
# ------------------------------------------------------------------------------------------------------------
def load_q3(run_dir, data_dir):
    """The original run's records (plan, weights, updates, predictions) and the visible G train/dev rows."""
    try:
        records = ep.read_run(run_dir)
    except (ep.PanelError, OSError, ValueError) as error:
        if "CUSTODY_REFUSED" in str(error):
            raise _stop("CUSTODY_REFUSED", str(error)) from None
        raise _stop("RUN_001_RECORDS_INCONSISTENT", str(error)) from None
    try:
        train, dev = ep.visible_rows(data_dir, records["plan"])
    except (ep.PanelError, ValueError) as error:
        code = "CUSTODY_REFUSED" if "CUSTODY_REFUSED" in str(error) else "Q3_DATA_NOT_PINNED"
        raise _stop(code, str(error)) from None
    return records, train, dev


def compile_rows(visible, compiler, panel, split):
    return [ep.compiled_row(v, compiler, panel, {"split": split, "index": i}) for i, v in enumerate(visible)]


def inspection(train, dev, compiler):
    """The rows the error-panel diagnostic showed (it must reproduce its frozen digest)."""
    rows, selection = ep.select_panels(train, dev, compiler)
    dev_ids = sorted(r["record_id"] for r in rows if r["origin"]["split"] == "dev")
    train_ids = sorted(r["record_id"] for r in rows if r["origin"]["split"] == "train")
    return {"selection_digest": selection["digest"], "dev_ids": dev_ids, "train_ids": train_ids,
            "dev_digest": rules.sha(rules.canonical(dev_ids)), "train_digest": rules.sha(rules.canonical(train_ids))}


def sp1_allocation(available):
    """Rows per shape: SP1_SIZE x (the shape's available rows / all available rows), by the largest-remainder rule.

`available` maps shape key -> number of available rows. Floors first; the rows left over go one each to the shapes
with the largest fractional parts (ties: smaller key first). A shape never gets more rows than half of its available
rows (rounded down), so every shape keeps rows for arm A's teaching; rows refused by that cap go, one at a time, to
the next shapes in the same remainder order that still have room.
"""
    total = sum(available.values())
    if total < 2 * rules.SP1_SIZE:
        raise _stop("PANEL_DIGEST_MISMATCH", "too few rows for SP1")
    quota = {k: rules.SP1_SIZE * n for k, n in available.items()}          # numerators over `total`
    alloc = {k: min(q // total, available[k] // 2) for k, q in quota.items()}
    order = sorted(available, key=lambda k: (-(quota[k] % total), k))
    while sum(alloc.values()) < rules.SP1_SIZE:
        progressed = False
        for key in order:
            if sum(alloc.values()) >= rules.SP1_SIZE:
                break
            if alloc[key] < available[key] // 2:
                alloc[key] += 1
                progressed = True
        if not progressed:
            raise _stop("PANEL_DIGEST_MISMATCH", "SP1 allocation cannot be filled")
    return alloc


def select_sp1(train_rows, excluded_ids):
    """SP1: rows not excluded (the diagnostic's inspected train rows), allocated per shape by sp1_allocation;
    within a shape, a seeded shuffle of the rows in file order; shapes in sorted key order."""
    by_shape = collections.defaultdict(list)
    for row in train_rows:
        if row["record_id"] not in excluded_ids:
            by_shape[row["q3_tree_shape_key"]].append(row)
    if not set(by_shape) <= set(sdg.G_TRAIN_SHAPES):
        raise _stop("PANEL_DIGEST_MISMATCH", "SP1 shapes are not G-train shapes")
    alloc = sp1_allocation({key: len(rows) for key, rows in by_shape.items()})
    rng = random.Random(rules.SP1_SEED)
    chosen = []
    for key in sorted(by_shape):
        pool = list(by_shape[key])
        rng.shuffle(pool)
        chosen += [dict(row, panel="SP1") for row in pool[:alloc[key]]]
    return chosen


def edit_panel_rows(sp1):
    """EDIT64: SP1 rows 0, EDIT_STRIDE, 2 x EDIT_STRIDE, ... (SP1 is in shape-key blocks, so this is proportional)."""
    return sp1[::rules.EDIT_STRIDE]


def edit_items(rows, compiler):
    """Every leaf x field of every edit-panel row: the first compilable cyclic edit (q4_error_panel.one_field_edits)."""
    items = []
    for row in rows:
        edits, why = ep.one_field_edits(row, compiler)
        if why:
            raise _stop("PANEL_DIGEST_MISMATCH", "edit panel row %s: %s" % (row["record_id"], why))
        for edit in edits:
            items.append({"row": row["record_id"], "path": edit["path"], "field": edit["field"],
                          "from": edit["from"], "to": edit.get("to"), "position": edit.get("position"),
                          "observation": edit.get("observation"), "old_token": edit.get("old_token"),
                          "new_token": edit.get("new_token")})
    return items


def edit_digest(items):
    return rules.sha(rules.canonical([[e["row"], e["path"], e["field"], e["to"], e["observation"]] for e in items]))


def edit_kinds(items):
    """(row, position, kind) of every MEASURABLE edit, in edit order: kind 'value' or 'presence' (q4_ab_rules)."""
    return [(e["row"], e["position"], rules.edit_kind(e["field"], e["from"], e["to"])) for e in items
            if e["to"] is not None]


def rows_digest(rows):
    return rules.sha(rules.canonical([[r["record_id"], r["content_sha256"]] for r in rows]))


def ids_digest(rows):
    return rules.sha(rules.canonical([r["record_id"] for r in rows]))


def teaching_pool(rows, excluded_ids, panel_contents):
    """Rows in their given order, minus excluded ids and minus any row whose target equals a panel row's target."""
    kept, dropped = [], []
    for row in rows:
        (dropped if row["record_id"] in excluded_ids or row["content_sha256"] in panel_contents else kept).append(row)
    return kept, dropped


def stream_indices(n, seed, count):
    """The run's presentation order: one random.Random(seed); a fresh shuffle of range(n) for every epoch.

Epoch 0 is exactly q4_smoke_job's `order = list(range(n)); random.Random(seed).shuffle(order)`.
"""
    if type(n) is not int or n < 1 or type(count) is not int or count < 0:
        raise ValueError("INVALID_STREAM")
    rng, out = random.Random(seed), []
    while len(out) < count:
        perm = list(range(n))
        rng.shuffle(perm)
        out.extend(perm)
    return out[:count]


def class_counts(rows, field):
    """Counts of one leaf field over every leaf of every row's target tree (all values listed, zeros included)."""
    index = sdg.FIELDS.index(field)
    counts = {str(value): 0 for value in sdg.VALUES[field]}
    for row in rows:
        for leaf in sdg.leaves_of(row["target_ast"]):
            counts[str(sdg.leaf_cell(leaf)[index])] += 1
    return counts


def near_twin_distances(panel_rows, pool_rows):
    """Per panel row: the smallest token (Hamming) distance to a pool row of the same token length (None if none)."""
    by_length = collections.defaultdict(list)
    for row in pool_rows:
        by_length[len(row["target_tokens"])].append(tuple(row["target_tokens"]))
    out = {}
    for row in panel_rows:
        tokens, best = tuple(row["target_tokens"]), None
        for other in by_length.get(len(tokens), ()):
            distance = 0
            for a, b in zip(tokens, other):
                if a != b:
                    distance += 1
                    if best is not None and distance >= best:
                        break
            if best is None or distance < best:
                best = distance
                if best == 0:
                    break
        out[row["record_id"]] = best
    return out


def with_allowed(row):
    """The grammar mask at every gold prefix (the same mask free decoding uses), computed once."""
    return dict(row, allowed=[allowed_next(tuple(row["target_tokens"][:i])) for i in range(len(row["target_tokens"]))])


def check_frozen_digests(measured):
    """Every measured panel digest must equal the one frozen in q4_ab_rules.py (PANEL_DIGEST_MISMATCH otherwise)."""
    frozen = rules.frozen_record()["digests"]
    for key, value in measured.items():
        if frozen[key] != value:
            raise _stop("PANEL_DIGEST_MISMATCH", "%s: measured %s, frozen %s" % (key, value, frozen[key]))


def prepare_q3(run_dir, data_dir, compiler, *, strict=True):
    """Everything on the Q3 side. strict=True: every frozen digest must match (the AWS runner); False: measure."""
    records, train, dev = load_q3(run_dir, data_dir)
    if compiler.engine != rules.B_PACKAGE["engine"] and strict:
        raise _stop("COMPILER_ENGINE_NOT_PYTHON", compiler.engine)
    train_rows = compile_rows(train, compiler, "G_TRAIN", "train")
    dev_rows = compile_rows(dev, compiler, "SP2", "dev")
    seen = inspection(train, dev, compiler)
    sp1 = select_sp1(train_rows, set(seen["train_ids"]))
    inspected = set(seen["dev_ids"])
    sp2 = [dict(row, inspected=row["record_id"] in inspected) for row in dev_rows]
    edit_rows = edit_panel_rows(sp1)
    items = edit_items(edit_rows, compiler)
    panel_contents = {r["content_sha256"] for r in sp1} | {r["content_sha256"] for r in sp2}
    a_pool, a_dropped = teaching_pool(train_rows, {r["record_id"] for r in sp1}, panel_contents)
    kinds = edit_kinds(items)
    measured = {"diagnostic_selection": seen["selection_digest"], "inspected_dev": seen["dev_digest"],
                "inspected_train": seen["train_digest"], "sp1": rows_digest(sp1), "sp2": rows_digest(sp2),
                "panel_targets": rules.panel_targets_digest(
                    [(r["record_id"], r["target_tokens"], r["slot_kinds"]) for r in sp1 + sp2]),
                "edit_panel": edit_digest(items), "edit_kinds": rules.edit_kinds_digest(kinds),
                "a_pool": ids_digest(a_pool), "a_pool_rows": len(a_pool),
                "edit_count": sum(1 for e in items if e["to"] is not None),
                "value_edit_count": sum(1 for k in kinds if k[2] == "value"),
                "presence_edit_count": sum(1 for k in kinds if k[2] == "presence"),
                "sp1_noetic_null": str(rules.most_frequent_rate(class_counts(sp1, "noetic"))),
                "a_pool_noetic_null": str(rules.most_frequent_rate(class_counts(a_pool, "noetic")))}
    if strict:
        check_frozen_digests(measured)
    return {"records": records, "train": train, "dev": dev, "train_rows": train_rows, "sp1": sp1, "sp2": sp2,
            "edit_rows": edit_rows, "edit_items": items, "a_pool": a_pool, "a_dropped": a_dropped,
            "panel_contents": panel_contents, "inspection": seen, "measured": measured}


# ------------------------------------------------------------------------------------------------------------
# B side: the pinned package
# ------------------------------------------------------------------------------------------------------------
def read_pin_entry(pins_path=None):
    """The B package's pin in Q4_SDG_DATA_PINS.json, which must describe exactly the frozen package."""
    path = Path(pins_path) if pins_path is not None else sdg.PINS
    try:
        pins = sdg._strict(path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8"), path.name)
    except (OSError, UnicodeError, ValueError) as error:
        raise _stop("B_PACKAGE_NOT_PINNED", "pin file unreadable (%s)" % type(error).__name__) from None
    versions = pins.get("data_versions") if type(pins) is dict else None
    entry = versions.get(rules.B_PACKAGE["schema"]) if type(versions) is dict else None
    if type(entry) is not dict:
        raise _stop("B_PACKAGE_NOT_PINNED", rules.B_PACKAGE["schema"])
    for key in ("engine", "size", "seed", "feedback_seed", "data_dir"):
        if entry.get(key) != rules.B_PACKAGE[key]:
            raise _stop("B_PIN_NOT_THE_FROZEN_PACKAGE", "%s is %r" % (key, entry.get(key)))
    if type(entry.get("manifest_sha256")) is not str or not _HEX64.fullmatch(entry["manifest_sha256"]):
        raise _stop("B_PIN_NOT_THE_FROZEN_PACKAGE", "manifest_sha256")
    files = entry.get("files")
    if type(files) is not dict or tuple(sorted(files)) != EXPECTED_PACKAGE_FILES or any(
            type(v) is not dict or set(v) != {"sha256", "records"} or not _HEX64.fullmatch(str(v["sha256"]))
            or type(v["records"]) is not int for v in files.values()):
        raise _stop("B_PIN_NOT_THE_FROZEN_PACKAGE", "files")
    return entry


def check_package(data_dir, entry):
    """A (re)built package must be the pinned one: manifest sha256, declared file hashes, engine, seeds, size."""
    try:
        manifest = sdg.manifest_of(data_dir)
        digest = sdg.manifest_sha(data_dir)
    except (sdg.LessonError, OSError, ValueError) as error:
        raise _stop("B_PACKAGE_MISMATCH", str(error)) from None
    if digest != entry["manifest_sha256"]:
        raise _stop("B_PACKAGE_MISMATCH", "manifest sha256 %s, pinned %s" % (digest, entry["manifest_sha256"]))
    try:
        sdg.check_pin(data_dir)
    except sdg.LessonError as error:
        raise _stop("B_PACKAGE_MISMATCH", str(error)) from None
    declared = {name: {"sha256": v["sha256"], "records": v["records"]} for name, v in manifest.get("files", {}).items()}
    if (manifest.get("schema") != rules.B_PACKAGE["schema"] or manifest.get("seed") != rules.B_PACKAGE["seed"]
            or manifest.get("feedback_seed") != rules.B_PACKAGE["feedback_seed"]
            or manifest.get("size_train_pool_declared") != rules.B_PACKAGE["size"]
            or manifest.get("compiler", {}).get("engine") != rules.B_PACKAGE["engine"] or declared != entry["files"]):
        raise _stop("B_PACKAGE_MISMATCH", "manifest fields differ from the pin")
    return manifest


def b_rows(data_dir, compiler, split):
    """Visible B rows of one split (lessons A, B, C; pinned door), targets recompiled from the visible text.

The compiled target must also equal the tree the canonical surface spells (sdg.parse_surface). The sidecar files
(sealed_*) of the package are never opened.
"""
    rows = []
    for lesson in sdg.LESSONS:
        try:
            visible = sdg.load_visible_lessons(data_dir, lesson, split, pinned=True)
        except sdg.LessonError as error:
            raise _stop("B_PACKAGE_MISMATCH", str(error)) from None
        for i, v in enumerate(visible):
            row = ep.compiled_row(v, compiler, "B_" + split.upper(), {"split": split, "lesson": lesson, "index": i})
            if sdg.parse_surface(v["observation"]) != row["target_ast"]:
                raise _stop("B_PACKAGE_MISMATCH", "surface and compiler disagree on %s" % v["record_id"])
            row["lesson_family"] = lesson
            rows.append(row)
    return rows


def prepare_b(data_dir, compiler, panel_contents):
    train = b_rows(data_dir, compiler, "train")
    dev = b_rows(data_dir, compiler, "dev")
    pool, dropped = teaching_pool(train, set(), panel_contents)
    return {"b_train_rows": train, "b_pool": pool, "b_dropped": dropped, "b_dev": dev}


def package_digests(build, rebuild, verify_exit):
    """Data-build machine: are two builds byte-identical, and what should the pin say? Hashes bytes; parses no row."""
    b1, b2 = Path(build), Path(rebuild)
    names1 = sorted(p.name for p in b1.iterdir() if p.is_file())
    names2 = sorted(p.name for p in b2.iterdir() if p.is_file())
    all_files, identical = {}, names1 == names2
    for name in sorted(set(names1) | set(names2)):
        x = (b1 / name).read_bytes() if (b1 / name).is_file() else None
        y = (b2 / name).read_bytes() if (b2 / name).is_file() else None
        same = x is not None and x == y
        identical = identical and same
        all_files[name] = {"sha256": None if x is None else rules.sha(x), "bytes": None if x is None else len(x),
                           "rebuild_sha256": None if y is None else rules.sha(y), "identical": same}
    manifest = sdg.manifest_of(b1)
    declared = {name: {"sha256": v["sha256"], "records": v["records"]} for name, v in manifest["files"].items()}
    matches_disk = all(all_files.get(name, {}).get("sha256") == v["sha256"] for name, v in declared.items())
    entry = {"manifest_sha256": sdg.manifest_sha(b1), "engine": manifest["compiler"]["engine"],
             "size": manifest["size_train_pool_declared"], "seed": manifest["seed"],
             "feedback_seed": manifest["feedback_seed"], "files": declared, "counts": manifest["counts"]}
    ok = (identical and matches_disk and verify_exit == 0 and tuple(sorted(declared)) == EXPECTED_PACKAGE_FILES
          and all(entry[k] == rules.B_PACKAGE[k] for k in ("engine", "size", "seed", "feedback_seed")))
    return {"schema": DIGESTS_SCHEMA, "label": rules.LABEL, "experiment": rules.EXPERIMENT,
            "status": "REBUILD_BYTE_IDENTICAL_AND_VERIFIED" if ok else "PACKAGE_NOT_PINNABLE",
            "rebuild_byte_identical": identical, "manifest_files_match_disk": matches_disk,
            "verify_exit_code": verify_exit, "pin_entry": entry, "all_files": all_files,
            "frozen_b_package": rules.B_PACKAGE,
            "runtime": {"python": platform.python_version(), "platform": platform.platform()}}


# ------------------------------------------------------------------------------------------------------------
# The prep record written to prep.json (JSON only; the reader reads it)
# ------------------------------------------------------------------------------------------------------------
def panel_row_record(row, twins=None):
    record = {"id": row["record_id"], "observation": row["observation"], "content_sha256": row["content_sha256"],
              "shape": row["shape_text"], "shape_key": row["q3_tree_shape_key"], "depth": row["depth"],
              "leaf_count": row["leaf_count"], "target_tokens": list(row["target_tokens"]),
              "slot_kinds": list(row["slot_kinds"])}
    if "inspected" in row:
        record["inspected"] = row["inspected"]
    if "lesson_family" in row:
        record["lesson_family"] = row["lesson_family"]
    if twins is not None:
        record["near_twin_distance"] = {arm: twins[arm].get(row["record_id"]) for arm in sorted(twins)}
    return record


def prep_record(q3prep, bprep=None, b_manifest_sha256=None):
    twins = {"A": near_twin_distances(q3prep["sp1"] + q3prep["sp2"], q3prep["a_pool"])}
    if bprep is not None:
        twins["B"] = near_twin_distances(q3prep["sp1"] + q3prep["sp2"], bprep["b_pool"])
    partners = ep.matched_partners(q3prep["sp1"])
    pools = {"A": {"rows": len(q3prep["a_pool"]), "ids": [r["record_id"] for r in q3prep["a_pool"]],
                   "dropped_ids": [r["record_id"] for r in q3prep["a_dropped"]],
                   "noetic_counts": class_counts(q3prep["a_pool"], "noetic"),
                   "field_counts": {f: class_counts(q3prep["a_pool"], f) for f in sdg.FIELDS},
                   "target_tokens": sum(len(r["target_tokens"]) for r in q3prep["a_pool"]),
                   "source_bytes": sum(len(r["observation"].encode("utf-8")) for r in q3prep["a_pool"])}}
    if bprep is not None:
        pool = bprep["b_pool"]
        pools["B"] = {"rows": len(pool), "ids": [r["record_id"] for r in pool],
                      "dropped_ids": [r["record_id"] for r in bprep["b_dropped"]],
                      "noetic_counts": class_counts(pool, "noetic"),
                      "field_counts": {f: class_counts(pool, f) for f in sdg.FIELDS},
                      "target_tokens": sum(len(r["target_tokens"]) for r in pool),
                      "source_bytes": sum(len(r["observation"].encode("utf-8")) for r in pool),
                      "lesson_rows": dict(sorted(collections.Counter(r["lesson_family"] for r in pool).items())),
                      "package_manifest_sha256": b_manifest_sha256}
    panels = {"SP1": [panel_row_record(r, twins) for r in q3prep["sp1"]],
              "SP2": [panel_row_record(r, twins) for r in q3prep["sp2"]]}
    if bprep is not None:
        panels["B_DEV"] = [panel_row_record(r) for r in bprep["b_dev"]]
    return {"schema": rules.SCHEMA, "label": rules.LABEL, "experiment": rules.EXPERIMENT,
            "frozen": rules.frozen_record(), "frozen_sha256": rules.frozen_sha256(), "measured": q3prep["measured"],
            "inspected_dev_ids": q3prep["inspection"]["dev_ids"],
            "inspected_train_ids": q3prep["inspection"]["train_ids"], "panels": panels,
            "sp1_noetic_counts": class_counts(q3prep["sp1"], "noetic"),
            "sp1_field_counts": {f: class_counts(q3prep["sp1"], f) for f in sdg.FIELDS},
            "edit_panel_ids": [r["record_id"] for r in q3prep["edit_rows"]], "edits": q3prep["edit_items"],
            "sp1_partners": [[a, b] for a, b in sorted(partners.items())], "pools": pools,
            "custody": "targets recompiled from visible text with the pinned compiler; no sealed or eval file of Q3 "
                       "or of the B package opened by this preparation"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    measure = sub.add_parser("measure", help="laptop: compute the digests frozen in q4_ab_rules.py (no torch)")
    measure.add_argument("--run-dir", required=True)
    measure.add_argument("--data-dir", required=True)
    digests = sub.add_parser("package-digests", help="data-build machine: compare two builds, emit the pin entry")
    digests.add_argument("--build", required=True)
    digests.add_argument("--rebuild", required=True)
    digests.add_argument("--verify-exit", type=int, required=True)
    digests.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.mode == "measure":
        compiler = sdg.Compiler()
        q3prep = prepare_q3(args.run_dir, args.data_dir, compiler, strict=False)
        report = dict(q3prep["measured"], compiler_engine=compiler.engine,
                      sp1_shapes=dict(sorted(collections.Counter(r["shape_text"] for r in q3prep["sp1"]).items())),
                      a_pool_dropped=len(q3prep["a_dropped"]),
                      edits_without_compilable_value=sum(1 for e in q3prep["edit_items"] if e["to"] is None),
                      a_noetic_counts=class_counts(q3prep["a_pool"], "noetic"),
                      sp1_noetic_counts=class_counts(q3prep["sp1"], "noetic"),
                      train_rows_per_shape=dict(sorted(collections.Counter(
                          r["shape_text"] for r in q3prep["train_rows"]).items())))
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0
    record = package_digests(args.build, args.rebuild, args.verify_exit)
    with Path(args.out).open("xb") as stream:
        stream.write((json.dumps(record, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    print(record["status"])
    return 0 if record["status"] == "REBUILD_BYTE_IDENTICAL_AND_VERIFIED" else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as error:
        print("Q4_AB_PREP_FAILED: %s" % error, file=sys.stderr)
        sys.exit(1)
