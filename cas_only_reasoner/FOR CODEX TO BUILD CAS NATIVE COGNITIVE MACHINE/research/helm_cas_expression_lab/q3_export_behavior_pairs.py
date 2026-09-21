"""Export Q3 as behaviour-pair records conforming to the delivered package schema -- and, by default, CHECK
instead of write.

The package (`_handoffs/FABLE_HELM_CAS_v1/schemas/behavior_pair.schema.json`) wants ONE record per example
carrying `model_input` and `target` together. Q3 keeps those in separate files on purpose (the visibility
boundary). So this export is the EVALUATOR's joined view, under `<data>/sealed_view/`. A learner may not open
`sealed_view/` any more than `sealed_*`.

TWO MODES.
  default (check)  rebuild all 12 files IN MEMORY and compare each file's record count and sha256 with the
                   committed `sealed_view/EXPORT_REPORT.json`. Prints EXPORT_MATCH or EXPORT_DRIFT per file, exits
                   non-zero on any drift, and writes NOTHING. This is how a fresh checkout proves it regenerates
                   the declared export; the expected digests are never replaced by whatever today's code produces.
  --write          write the 12 files and the report. Used once per data version, then committed (report only --
                   the .jsonl files are derived and git-ignored).

IT FAILS CLOSED. It refuses to run when: the data's manifest cites a contract digest other than
OPERATION_CONTRACTS.json's (CONTRACT_DIGEST_MISMATCH); `jsonschema` is not installed (VALIDATOR_MISSING -- a
record that was never validated is never called valid); the package schema is absent; any input file's sha256
differs from the manifest; or any row fails the strict reference re-check in `q3_load.load_split`.

Field mapping, exact:
  split            train -> TRAIN, dev -> DEVELOPMENT, eval -> ENGINEERING_EVAL  (PROTECTED_FINAL: none exists)
  task_mode        R, G -> RECONSTRUCTION ; A, C -> OPERATION
  target.status    sealed outcome INVALID_INPUT -> INVALID_INPUT ; otherwise VALID
  structure_family R, G: the strict shape key ; A: the (operator, source_domain, target_domain) cell ; C: "depth-<n>"
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


def _record(fam, split, v, s, manifest, contract_digest):
    if fam in ("R", "G"):
        family_key, typed, inter = s["shape_key"], {"canonical_ast": s["target_canonical_ast"]}, {"ast_size": s["ast_size"], "depth": s.get("depth")}
        bindings, context = {}, {"expression_language": "CAS v7.7 notation"}
    elif fam == "A":
        family_key = s["cell"] or "refusal:" + str(s.get("refusal_kind"))
        typed = {"admissible": s["target"]}
        inter = {"trace": s["trace"], "swapped_target": s.get("swapped_target"), "order_flip": s.get("order_flip"), "case_family": s.get("case_family")}
        o = v["observation"]
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
    """Returns ({file name: bytes}, {file name: invalid count}). Raises q3_load.Q3LoadError or SystemExit when it must refuse."""
    contract_digest = q3_load.check_contract_binding(data_dir)
    try:
        import jsonschema
    except ImportError:
        raise SystemExit("EXPORT_REFUSED:VALIDATOR_MISSING: install jsonschema -- unvalidated records are never reported as valid")
    if not SCHEMA.is_file():
        raise SystemExit("EXPORT_REFUSED:PACKAGE_SCHEMA_MISSING:%s" % SCHEMA.relative_to(PACKAGE).as_posix())
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    manifest = q3_load.manifest_of(data_dir)
    bodies, invalid = {}, {}
    for fam in q3_load.FAMILIES:
        for split in q3_load.SPLITS:
            rows, bad = [], 0
            for v, s in q3_load.load_split(data_dir, fam, split):          # sha-checked, strictly parsed, re-checked against the reference
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
    parser.add_argument("--data", default=str(HERE / "data" / "q3_v0_3"))
    parser.add_argument("--write", action="store_true", help="write the files and the report (default: check against the committed report, write nothing)")
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
    if args.write:
        out.mkdir(exist_ok=True)
        for name, body in bodies.items():
            (out / name).write_bytes(body)
        report = {"schema": "helm-cas-expression-lab.q3-behavior-pair-export/0.2", "source": "data/" + data_dir.name,
                  "source_manifest_schema": manifest["schema"], "contract_sha256": contract_digest,
                  "package_schema": SCHEMA.relative_to(PACKAGE).as_posix(), "validator": "jsonschema Draft 2020-12", "files": files,
                  "boundary": "sealed_view/ is the evaluator's joined view; a learner may open visible_* only",
                  "how_to_verify": "python q3_export_behavior_pairs.py   (no flag: rebuilds in memory and compares with this report; writes nothing)"}
        with open(out / "EXPORT_REPORT.json", "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, indent=1, sort_keys=True))
        print("Q3_EXPORT_WRITTEN")
        return 0
    report_path = out / "EXPORT_REPORT.json"
    if not report_path.is_file():
        print("EXPORT_DRIFT: no committed report at %s" % report_path.relative_to(PACKAGE).as_posix())
        return 1
    committed = json.loads(report_path.read_text(encoding="utf-8"))
    drift = 0
    if committed.get("contract_sha256") != contract_digest:
        print("EXPORT_DRIFT: the committed report was made for contract %s" % str(committed.get("contract_sha256"))[:16])
        drift += 1
    for name in sorted(set(files) | set(committed.get("files", {}))):
        same = files.get(name) == committed.get("files", {}).get(name)
        print("  %s %s" % ("EXPORT_MATCH" if same else "EXPORT_DRIFT", name))
        drift += 0 if same else 1
    print("Q3_EXPORT_CHECK_PASS" if not drift else "Q3_EXPORT_CHECK_FAIL: %d difference(s); the committed report was NOT changed" % drift)
    return 0 if not drift else 1


if __name__ == "__main__":
    sys.exit(main())
