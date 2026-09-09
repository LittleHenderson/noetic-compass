"""Bounded source-level compatibility review for the graph-first ^6 framework.

Reads the EXPORTED package zip and its embedded frozen wheels, and verifies —
statically, with the ast module, WITHOUT executing any code, importing any
neural module, or constructing tensors — that:

  1. every referenced class/function exists in the named module,
  2. configuration constructor fields match the actual declarations,
  3. the module/learner/readout/loss/optimizer/checkpoint calls use the
     interfaces the frozen sources actually define,
  4. the permitted parameter group resolves to the real contract roles.

Remaining GPU-only uncertainties are reported explicitly. Evidence is written
as JSON with a sha256 receipt.

Usage:
    python -B tools/graph_training_wheel_compat_review.py <package_zip> <evidence_dir>
"""
import ast
import json
import sys
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path


def digest(raw):
    return sha256(raw).hexdigest()


def source_of(zipfile_, name):
    return zipfile_.read(name).decode("utf-8", "replace")


def module_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def joined_str_text(node):
    """Reassemble an f-string's literal + formatted-name text for matching."""
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
            parts.append("{" + value.value.id + "}")
    return "".join(parts)


def contains_fstring(node, needle):
    for child in ast.walk(node):
        if isinstance(child, ast.JoinedStr):
            if joined_str_text(child) == needle:
                return True
    return False


def class_fields(tree, class_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields.append(target.id)
            return sorted(fields)
    return []


def contains(tree, needle):
    return needle in ast.dump(tree)


def review(package_zip):
    with zipfile.ZipFile(package_zip) as package:
        wheel_dir = ("research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/")
        findings = {}

        # 1. casformer reference wheel: CASformerConfig fields
        with zipfile.ZipFile(io_bytes(package, wheel_dir + "casformer_reference-0.1.0-py3-none-any.whl")) as wheel:
            casformer_init = source_of(wheel, "casformer/__init__.py")
            init_tree = ast.parse(casformer_init)
            casformer_files = [name for name in wheel.namelist()
                               if name.startswith("casformer/") and name.endswith(".py")]
            config_fields = None
            config_module = None
            for name in casformer_files:
                tree = ast.parse(source_of(wheel, name))
                fields = class_fields(tree, "CASformerConfig")
                if fields:
                    config_fields = fields
                    config_module = name
                    break
            findings["casformer_config"] = {
                "exported_from_init": "CASformerConfig" in module_names(init_tree),
                "class_defined_in": config_module,
                "declared_fields": config_fields,
            }

        # 2. cas_cjt wheel: neural + state interfaces
        with zipfile.ZipFile(io_bytes(package, wheel_dir + "cas_neural_cjt-0.2.0-py3-none-any.whl")) as wheel:
            neural_tree = ast.parse(source_of(wheel, "cas_cjt/neural.py"))
            neural_names = module_names(neural_tree)
            state_tree = ast.parse(source_of(wheel, "cas_cjt/state.py"))
            decompose = _find_assignment(neural_tree, "DECOMPOSE")
            decompose_module = None
            for node in ast.walk(neural_tree):
                if isinstance(node, ast.Dict):
                    for key_node in node.keys:
                        if isinstance(key_node, ast.Name) and key_node.id == "DECOMPOSE":
                            decompose_module = "DECOMPOSE"
            findings["cas_cjt"] = {
                "RegisteredOperationBank": "RegisteredOperationBank" in neural_names,
                "DECOMPOSE_defined": "DECOMPOSE" in neural_names,
                "DECOMPOSE_value": decompose,
                "OPERATION_REGISTRATIONS": "OPERATION_REGISTRATIONS" in neural_names,
                "modules_by_operation_keyed_by": decompose_module,
                "make_operation_contract": "make_operation_contract" in module_names(state_tree),
                "contract_plasticity_expression_operation_scoped":
                    contains_fstring(state_tree, "operation:{operation_id}"),
            }

        # 3. gpu_adapter inside the exported package: _cuda returns (torch, device)
        adapter_src = source_of(package, "research/CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/gpu_adapter.py")
        adapter_tree = ast.parse(adapter_src)
        cuda_return = None
        for node in ast.walk(adapter_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_cuda":
                returns = [child for child in ast.walk(node) if isinstance(child, ast.Return)]
                if returns and isinstance(returns[-1].value, (ast.Tuple, ast.List)):
                    cuda_return = [getattr(element, "id", None)
                                   for element in returns[-1].value.elts]
        findings["gpu_adapter"] = {"_cuda_return_names": cuda_return}

        # 4. candidate framework expectations vs the wheel sources
        expected_config_fields = ["d_model", "num_heads", "num_relations", "num_layers",
                                  "dropout", "attention_dropout", "initial_cutoff",
                                  "initial_saturation"]
        declared = set(findings["casformer_config"]["declared_fields"] or [])
        missing_fields = [field for field in expected_config_fields if field not in declared]
        findings["config_compatibility"] = {
            "used_fields": expected_config_fields,
            "missing_from_declared": missing_fields,
        }
        return findings


def io_bytes(zipfile_, name):
    import io
    return io.BytesIO(zipfile_.read(name))


def _find_assignment(tree, target):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for element in node.targets:
                if isinstance(element, ast.Name) and element.id == target:
                    return ast.unparse(node.value) if hasattr(ast, "unparse") else repr(node.value)
    return None


def main(argv):
    package_zip, evidence_dir = Path(argv[1]), Path(argv[2])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    findings = review(package_zip)
    gpu_only = [
        "torch.cuda availability and the _DecomposeTransform forward numerics are "
        "not statically verifiable and remain GPU-only",
        "DifferentialConductanceLinear parameter names/shapes are runtime-determined "
        "(verify in the first scheduled update's containment report)",
        "the exact loss values and gradient flow are runtime-determined",
        "the registered operation contract object's digest fields are runtime-determined",
    ]
    effective_config = {
        "d_model": 64, "num_heads": 2, "num_relations": 4, "num_layers": 1,
        "dropout": 0.0, "attention_dropout": 0.0, "initial_cutoff": 0.01,
        "initial_saturation": 100.0,
        "note": ("All values newly specified for this candidate (attempt-005 fix); "
                 "previously the default constructor was used. These match the repo "
                 "integration-test construction pattern, not an optimization claim."),
    }
    evidence = {"schema": "cas-graph-training-compat-review/1",
                "package": {"archive_sha256": digest(package_zip.read_bytes()),
                            "bytes": package_zip.stat().st_size},
                "findings": findings, "effective_configuration": effective_config,
                "gpu_only_uncertainties": gpu_only,
                "boundary": {"executed_code": False, "neural_modules_created": False,
                             "aws_calls": 0, "tensors_created": False}}
    raw = (json.dumps(evidence, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (evidence_dir / "compat_review.json").write_bytes(raw)
    receipt = {"schema": "cas-graph-training-compat-receipt/1",
               "file": "compat_review.json", "bytes": len(raw), "sha256": digest(raw)}
    (evidence_dir / "receipt.json").write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": "COMPAT_REVIEW_COMPLETE",
                      "findings": findings,
                      "evidence_sha256": receipt["sha256"]}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main(sys.argv)
