"""Export Q3 as behaviour-pair records conforming to the delivered package schema -- and, by default, CHECK
instead of write.

The package (`_handoffs/FABLE_HELM_CAS_v1/schemas/behavior_pair.schema.json`) wants ONE record per example
carrying `model_input` and `target` together. Q3 keeps those in separate files on purpose (the visibility
boundary). So this export is the EVALUATOR's joined view, under `<data>/sealed_view/`. A learner may not open
`sealed_view/` any more than `sealed_*`.

TWO MODES.
  default (check)  rebuild all 12 files IN MEMORY and compare each file's record count and sha256 with the
                   committed `sealed_view/EXPORT_REPORT.json`, whose own sha256 must equal the pin in
                   `Q3_DATA_PINS.json` (OUTSIDE the data folder). Any behavior_pairs_*.jsonl present on disk is
                   hashed too. Prints EXPORT_MATCH or EXPORT_DRIFT per file, exits non-zero on any drift, writes
                   NOTHING. The expected digests are never replaced by whatever today's code produces.
  --write          write the 12 files and the report, and record the report's sha256 in the pins file. Used once
                   per data version, then committed (report and pins; the .jsonl files are derived, git-ignored).

IT FAILS CLOSED. It refuses when: the manifest is not the pinned one; the manifest cites a contract digest other
than OPERATION_CONTRACTS.json's; `jsonschema` is not installed (a record that was never validated is never called
valid); the package schema is absent; or `q3_load.load_dataset` refuses anything -- a file hash, a row's keys, a
recomputed answer, a record id, a shared held-out group, an undeclared file.

WHAT WAS VERIFIED HOW is written into the report per family (`verification`): A and C targets are recomputed from
the reference; R and G targets are structure-checked here and recompiled only by the test suite.

Field mapping, exact:
  split            train -> TRAIN, dev -> DEVELOPMENT, eval -> ENGINEERING_EVAL  (PROTECTED_FINAL: none exists)
  task_mode        R, G -> RECONSTRUCTION ; A, C -> OPERATION
  target.status    sealed outcome INVALID_INPUT -> INVALID_INPUT ; otherwise VALID
  structure_family R: the strict shape key ; G: the bare tree-shape key ; A: the cell ; C: "depth-<n>"
  contract_sha256  OPERATION_CONTRACTS.json's contract_digest
  oracle_receipt   sha256 of the sealed row (the oracle's own output, canonical JSON)
"""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
sys.path.insert(0, str(HERE))
import q3_load  # noqa: E402

SCHEMA = PACKAGE / "_handoffs/FABLE_HELM_CAS_v1/schemas/behavior_pair.schema.json"
SPLIT_MAP = {"train": "TRAIN", "dev": "DEVELOPMENT", "eval": "ENGINEERING_EVAL"}
MODE_MAP = {"R": "RECONSTRUCTION", "G": "RECONSTRUCTION", "A": "OPERATION", "C": "OPERATION"}
OP_MAP = {"R": "cas.compile_expression/canonical-ast", "G": "cas.compile_expression/canonical-ast",
          "A": "cas.op.is_admissible/1.0", "C": "cas.op.compose/1.0"}


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _shown(path):
    try:
        return path.relative_to(PACKAGE).as_posix()
    except ValueError:
        return path.as_posix()


def _record(fam, split, v, s, manifest, contract_digest):
    if fam in ("R", "G"):
        family_key = s["tree_shape_key"] if fam == "G" else s["shape_key"]
        typed, inter = {"canonical_ast": s["target_canonical_ast"]}, {"ast_size": s["ast_size"], "depth": s["depth"], "strict_shape_key": s["shape_key"]}
        bindings, context = {}, {"expression_language": "CAS v7.7 notation; Noetics spelled ^0..^9"}
    elif fam == "A":
        refusal = s["outcome"] == "INVALID_INPUT"
        family_key = "refusal:" + s["refusal_kind"] if refusal else s["cell"]
        typed = {"admissible": s["target"]}
        inter = {"trace": s["trace"]} if refusal else {"trace": s["trace"], "swapped_target": s["swapped_target"], "order_flip": s["order_flip"], "case_family": s["case_family"]}
        o = v["observation"] if isinstance(v["observation"], dict) else {}
        bindings = {"operator": o.get("operator"), "source": o.get("source"), "target": o.get("target")}
        context = {"note": "roles are positional: source then target; swapping them is a different question"}
    else:
        family_key, typed, inter = "depth-%d" % s["depth"], {"result_noetic": s["target"]}, {"trace": s["trace"]}
        bindings, context = {"chain": v["observation"]}, {"note": "explicit parentheses; grouping is irrelevant for this operation"}
    return {
        "schema_version": "fable.behavior-pair/1.0", "record_id": v["record_id"], "operation_id": OP_MAP[fam],
        "contract_sha256": contract_digest, "structure_family": family_key, "split": SPLIT_MAP[split],
        "model_input": {"task_mode": MODE_MAP[fam], "representation": v["observation"], "bindings": bindings, "context": context},
        "target": {"status": "INVALID_INPUT" if s.get("outcome") == "INVALID_INPUT" else "VALID",
                   "typed_result": typed, "intermediate_reference": json.dumps(inter, sort_keys=True, ensure_ascii=False)},
        "provenance": {"generator_version": manifest["schema"], "seed": manifest["seed"], "semantic_source": s["oracle"],
                       "oracle_receipt_sha256": hashlib.sha256(_canon(s)).hexdigest()},
    }


def build(data_dir):
    """Returns (bodies, invalid counts, manifest, contract digest). Raises q3_load.Q3LoadError or SystemExit when it must refuse."""
    try:
        import jsonschema
    except ImportError:
        raise SystemExit("EXPORT_REFUSED:VALIDATOR_MISSING: install jsonschema -- unvalidated records are never reported as valid")
    if not SCHEMA.is_file():
        raise SystemExit("EXPORT_REFUSED:PACKAGE_SCHEMA_MISSING:%s" % _shown(SCHEMA))
    data = q3_load.load_dataset(data_dir)               # pinned manifest, contract binding, every row, every cross-file check
    contract_digest = q3_load.check_contract_binding(data_dir)
    manifest = q3_load.manifest_of(data_dir)
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    bodies, invalid = {}, {}
    for fam in q3_load.FAMILIES:
        for split in q3_load.SPLITS:
            rows, bad = [], 0
            for v, s in data[fam][split]:
                rec = _record(fam, split, v, s, manifest, contract_digest)
                errors = list(validator.iter_errors(rec))
                if errors:
                    bad += 1
                    if bad <= 2:
                        print("  INVALID %s/%s %s: %s" % (fam, split, rec["record_id"], errors[0].message[:140]))
                rows.append(rec)
            name = "behavior_pairs_%s_%s.jsonl" % (fam, split)
            bodies[name] = ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")
            invalid[name] = bad
    return bodies, invalid, manifest, contract_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(HERE / "data" / "q3_v0_7"))
    parser.add_argument("--write", action="store_true", help="write the files, the report and the report's pin (default: check, write nothing)")
    args = parser.parse_args()
    data_dir = pathlib.Path(args.data)
    out = data_dir / "sealed_view"
    try:
        bodies, invalid, manifest, contract_digest = build(data_dir)
    except q3_load.Q3LoadError as error:
        print("EXPORT_REFUSED:%s" % error)
        return 2
    files = {name: {"records": body.count(b"\n"), "sha256": hashlib.sha256(body).hexdigest()} for name, body in bodies.items()}
    total, bad = sum(f["records"] for f in files.values()), sum(invalid.values())
    print("behaviour-pair export of %s: %d records in %d files; invalid under the package schema: %d" % (data_dir.name, total, len(files), bad))
    if bad:
        print("Q3_EXPORT_FAIL")
        return 1
    pins = json.loads(q3_load.PINS.read_text(encoding="utf-8"))
    pin = pins["data_versions"][manifest["schema"]]
    if args.write:
        out.mkdir(exist_ok=True)
        (out / ".gitignore").write_text("behavior_pairs_*.jsonl\n", encoding="utf-8", newline="\n")
        for name, body in bodies.items():
            (out / name).write_bytes(body)
        report = {"schema": "helm-cas-expression-lab.q3-behavior-pair-export/0.3", "source": "data/" + data_dir.name,
                  "source_manifest_schema": manifest["schema"], "source_manifest_sha256": q3_load.manifest_sha(data_dir), "contract_sha256": contract_digest,
                  "package_schema": _shown(SCHEMA), "validator": "jsonschema Draft 2020-12", "files": files,
                  "verification": {f: q3_load.verification_level(f) for f in q3_load.FAMILIES},
                  "boundary": "sealed_view/ is the evaluator's joined view; a learner may open visible_* only",
                  "how_to_verify": "python q3_export_behavior_pairs.py   (no flag: rebuilds in memory and compares with this report; writes nothing)"}
        body = json.dumps(report, indent=1, sort_keys=True).encode("utf-8")
        (out / "EXPORT_REPORT.json").write_bytes(body)
        pin["export_report_sha256"] = hashlib.sha256(body).hexdigest()
        q3_load.PINS.write_bytes((json.dumps(pins, indent=1, sort_keys=True) + "\n").encode("utf-8"))
        print("Q3_EXPORT_WRITTEN (report pinned in %s)" % q3_load.PINS.name)
        return 0
    report_path, drift = out / "EXPORT_REPORT.json", 0
    if not report_path.is_file():
        print("EXPORT_DRIFT: no committed report at %s" % _shown(report_path))
        return 1
    report_bytes = report_path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(report_bytes).hexdigest() != pin.get("export_report_sha256"):
        print("EXPORT_DRIFT: EXPORT_REPORT.json is not the pinned report")
        drift += 1
    try:
        committed = q3_load.strict_loads(report_bytes, "EXPORT_REPORT.json")
        if not isinstance(committed, dict) or not isinstance(committed.get("files"), dict):
            print("EXPORT_DRIFT: the committed report must be an object with a files object")
            return 1
    except q3_load.Q3LoadError as error:
        print("EXPORT_DRIFT: the committed report is unreadable (%s)" % error)
        return 1
    for field, value in (("contract_sha256", contract_digest), ("source_manifest_sha256", q3_load.manifest_sha(data_dir)), ("source_manifest_schema", manifest["schema"])):
        if committed.get(field) != value:
            print("EXPORT_DRIFT: report field %s is %s" % (field, str(committed.get(field))[:20]))
            drift += 1
    for name in sorted(set(files) | set(committed["files"])):
        same = files.get(name) == committed["files"].get(name)
        on_disk = out / name
        if same and on_disk.is_file() and hashlib.sha256(on_disk.read_bytes()).hexdigest() != files[name]["sha256"]:
            same = False                                       # a derived file on disk that is not what the data produces
        print("  %s %s" % ("EXPORT_MATCH" if same else "EXPORT_DRIFT", name))
        drift += 0 if same else 1
    print("Q3_EXPORT_CHECK_PASS" if not drift else "Q3_EXPORT_CHECK_FAIL: %d difference(s); the committed report was NOT changed" % drift)
    return 0 if not drift else 1


def pin_manifest(data_dir):
    """Run once, deliberately, when a data version is built: full content checks, then record the manifest's sha256."""
    data_dir = pathlib.Path(data_dir)
    q3_load.load_dataset(data_dir, pinned=False)
    manifest = q3_load.manifest_of(data_dir)
    pins = json.loads(q3_load.PINS.read_text(encoding="utf-8")) if q3_load.PINS.is_file() else {"schema": "helm-cas-expression-lab.q3-data-pins/0.1", "why": "kept OUTSIDE the data folders: a forged copy of the data carries its own manifest, never this pin", "data_versions": {}}
    pins["data_versions"][manifest["schema"]] = {"data_dir": "data/" + data_dir.name, "manifest_sha256": q3_load.manifest_sha(data_dir)}
    q3_load.PINS.write_bytes((json.dumps(pins, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    print("pinned %s: manifest sha256 %s" % (manifest["schema"], q3_load.manifest_sha(data_dir)[:16]))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--pin-manifest":
        try:
            sys.exit(pin_manifest(sys.argv[2]))
        except q3_load.Q3LoadError as error:
            print("PIN_REFUSED:%s" % error)
            sys.exit(2)
    sys.exit(main())
