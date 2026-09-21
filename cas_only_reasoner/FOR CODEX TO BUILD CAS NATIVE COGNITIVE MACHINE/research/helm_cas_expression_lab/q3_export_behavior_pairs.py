"""Export Q3 v0.2 as behaviour-pair records conforming to the delivered package schema, and validate them.

The package (`_handoffs/FABLE_HELM_CAS_v1/schemas/behavior_pair.schema.json`) wants ONE record per
example carrying `model_input` and `target` together. Q3 keeps those in separate files on purpose
(the visibility boundary). So this export is the EVALUATOR's joined view: it reads visible_* and
sealed_* and writes `behavior_pairs_<family>_<split>.jsonl` under `data/q3_v0_2/sealed_view/`. A
learner may not open `sealed_view/` any more than `sealed_*` -- the test that forbids `learner*`
files from touching `sealed_` covers it by name.

Field mapping, exact:
  split            train -> TRAIN, dev -> DEVELOPMENT, eval -> ENGINEERING_EVAL  (PROTECTED_FINAL: none exists)
  task_mode        R, G -> RECONSTRUCTION ; A, C -> OPERATION
  target.status    sealed outcome INVALID_INPUT -> INVALID_INPUT ; otherwise VALID
  structure_family R, G: the strict shape key ; A: the (operator, source_domain, target_domain) cell ;
                   C: "depth-<n>"
  contract_sha256  OPERATION_CONTRACTS.json's contract_digest
  oracle_receipt   sha256 of the sealed row (the oracle's own output, canonical JSON)

Validation uses `jsonschema` when installed and reports per-file counts. Deterministic; `$0`.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
DATA = HERE / "data" / "q3_v0_2"
OUT = DATA / "sealed_view"
SCHEMA = PACKAGE / "_handoffs/FABLE_HELM_CAS_v1/schemas/behavior_pair.schema.json"
SPLIT_MAP = {"train": "TRAIN", "dev": "DEVELOPMENT", "eval": "ENGINEERING_EVAL"}
MODE_MAP = {"R": "RECONSTRUCTION", "G": "RECONSTRUCTION", "A": "OPERATION", "C": "OPERATION"}
OP_MAP = {"R": "cas.compile_expression/canonical-ast", "G": "cas.compile_expression/canonical-ast",
          "A": "cas.op.is_admissible/1.0", "C": "cas.op.compose/1.0"}


def _rows(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def export():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    contract_digest = manifest["operation_contracts_digest"]
    OUT.mkdir(exist_ok=True)
    written, validation = {}, {}
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")) if SCHEMA.exists() else None
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema) if schema else None
    except ImportError:
        validator = None
    for fam in ("R", "G", "A", "C"):
        for split in ("train", "dev", "eval"):
            vis = _rows(DATA / ("visible_%s_%s.jsonl" % (fam, split)))
            seal = {r["record_id"]: r for r in _rows(DATA / ("sealed_%s_%s.jsonl" % (fam, split)))}
            out_rows, errors = [], 0
            for v in vis:
                s = seal[v["record_id"]]
                if fam in ("R", "G"):
                    family_key, typed, inter = s["shape_key"], {"canonical_ast": s["target_canonical_ast"]}, {"ast_size": s["ast_size"], "depth": s.get("depth")}
                    bindings, context = {}, {"expression_language": "CAS v7.7 notation"}
                elif fam == "A":
                    family_key = s["cell"] or "refusal:" + str(s.get("refusal_kind"))
                    typed = {"admissible": s["target"]}
                    inter = {"trace": s["trace"], "swapped_target": s.get("swapped_target"), "order_flip": s.get("order_flip")}
                    o = v["observation"]
                    bindings, context = {"operator": o.get("operator"), "source": o.get("source"), "target": o.get("target")}, {"note": "roles are positional: source then target; swapping them is a different question"}
                else:
                    family_key, typed, inter = "depth-%d" % s["depth"], {"result_noetic": s["target"]}, {"trace": s["trace"]}
                    bindings, context = {"chain": v["observation"]}, {"note": "explicit parentheses; grouping is irrelevant for this operation"}
                rec = {
                    "schema_version": "fable.behavior-pair/1.0", "record_id": v["record_id"], "operation_id": OP_MAP[fam],
                    "contract_sha256": contract_digest, "structure_family": family_key, "split": SPLIT_MAP[split],
                    "model_input": {"task_mode": MODE_MAP[fam], "representation": v["observation"], "bindings": bindings, "context": context},
                    "target": {"status": "INVALID_INPUT" if s.get("outcome") == "INVALID_INPUT" else "VALID",
                               "typed_result": typed, "intermediate_reference": (json.dumps(inter, sort_keys=True, ensure_ascii=False) if inter else None)},
                    "provenance": {"generator_version": manifest["schema"], "seed": manifest["seed"], "semantic_source": s["oracle"],
                                   "oracle_receipt_sha256": hashlib.sha256(_canon(s)).hexdigest()},
                }
                if validator is not None:
                    errs = list(validator.iter_errors(rec))
                    if errs:
                        errors += 1
                        if errors <= 2:
                            print("  INVALID %s/%s %s: %s" % (fam, split, rec["record_id"], errs[0].message[:140]))
                out_rows.append(rec)
            path = OUT / ("behavior_pairs_%s_%s.jsonl" % (fam, split))
            body = ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in out_rows) + "\n").encode("utf-8")
            path.write_bytes(body)
            written[path.name] = {"records": len(out_rows), "sha256": hashlib.sha256(body).hexdigest()}
            validation[path.name] = {"invalid": errors, "validator": ("jsonschema" if validator else "none")}
    report = {"schema": "helm-cas-expression-lab.q3-behavior-pair-export/0.1", "source": "data/q3_v0_2", "package_schema": str(SCHEMA.relative_to(PACKAGE)),
              "files": written, "validation": validation, "boundary": "sealed_view/ is the evaluator's joined view; a learner may open visible_* only"}
    (OUT / "EXPORT_REPORT.json").write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    total = sum(w["records"] for w in written.values())
    bad = sum(v["invalid"] for v in validation.values())
    print("behaviour-pair export: %d records in %d files; invalid under the package schema: %d (%s)" % (total, len(written), bad, validation[next(iter(validation))]["validator"]))
    print("Q3_EXPORT_PASS" if bad == 0 else "Q3_EXPORT_FAIL")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(export())
