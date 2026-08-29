"""CCB-P1: the programming STUDENT - a persistent, gated procedure
store plus the capabilities it licenses.

The gate is the learnable surface: Python itself can do anything,
but the STUDENT may only trace, implement, generate tests, or repair
once the ladder promoted that procedure - a typed CANNOT otherwise
(the same capability-honesty law as language and mathematics; the
self-model's 'CANNOT code' flips only skill by promoted skill).

Structural transfer is a REAL operation: a stored implementation
adapts to a renamed specification by deterministic AST renaming of
the function name and parameters - never by retraining, never by
guessing."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from typing import Dict, List, Optional

from . import repair as repair_mod
from . import sandbox, tracer
from .spec import _PREDICATES, SKILLS, boundary_inputs


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str)
        .encode("utf-8")).hexdigest()[:16]


class ProcedureStoreError(Exception):
    pass


class ProcedureStore:
    """Versioned, digest-checked, coordinator-written (the ladder's
    commit path alone, and only on PROMOTED)."""

    def __init__(self) -> None:
        self.procedures: Dict[str, Dict] = {}
        self.revision = 0
        self.history: List[Dict] = []

    def promoted_ids(self) -> List[str]:
        return sorted(self.procedures)

    def get(self, skill_id: str) -> Optional[Dict]:
        return self.procedures.get(skill_id)

    def _commit(self, record: Dict, provenance: str) -> Dict:
        if record["skill_id"] in self.procedures:
            raise ProcedureStoreError(
                f"{record['skill_id']} already promoted - "
                f"re-teaching does not overwrite")
        stored = copy.deepcopy(record)
        stored["provenance"] = provenance
        stored["record_digest"] = _digest(
            {k: v for k, v in stored.items()
             if k != "record_digest"})
        self.procedures[record["skill_id"]] = stored
        self.revision += 1
        self.history.append({"revision": self.revision,
                             "action": "PROMOTED",
                             "skill_id": record["skill_id"],
                             "provenance": provenance})
        return stored

    def _ablate(self, skill_id: str, reason: str) -> None:
        """Causal-ablation support (examiner-side): remove ONE
        procedure, recorded - never silent."""
        if skill_id not in self.procedures:
            raise ProcedureStoreError(f"no procedure {skill_id}")
        del self.procedures[skill_id]
        self.revision += 1
        self.history.append({"revision": self.revision,
                             "action": "ABLATED",
                             "skill_id": skill_id,
                             "reason": reason})

    def to_json(self) -> Dict:
        payload = {"revision": self.revision,
                   "history": self.history,
                   "procedures": self.procedures}
        payload["store_digest"] = _digest(
            {k: v for k, v in payload.items()
             if k != "store_digest"})
        return payload

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_json(), fh, indent=1, sort_keys=True)

    @classmethod
    def load(cls, path: str) -> "ProcedureStore":
        store = cls()
        if not os.path.exists(path):
            return store
        payload = json.load(open(path, encoding="utf-8"))
        claimed = payload.get("store_digest")
        actual = _digest({k: v for k, v in payload.items()
                          if k != "store_digest"})
        if claimed != actual:
            raise ProcedureStoreError(
                "procedure store digest mismatch - refusing a "
                "tampered store")
        store.revision = payload["revision"]
        store.history = payload["history"]
        store.procedures = payload["procedures"]
        return store


# ------------------------------------------------------ AST renaming
def adapt_code(code: str, old_fname: str, new_fname: str,
               param_map: Dict[str, str]) -> str:
    """Deterministic structural adaptation: rename the function and
    its parameters to a new specification's signature."""
    tree = ast.parse(code)

    class Renamer(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.name == old_fname:
                node.name = new_fname
                for arg in node.args.args:
                    if arg.arg in param_map:
                        arg.arg = param_map[arg.arg]
            self.generic_visit(node)
            return node

        def visit_Name(self, node):
            if node.id in param_map:
                node.id = param_map[node.id]
            return node

    return ast.unparse(ast.fix_missing_locations(
        Renamer().visit(tree)))


# ---------------------------------------------------------- student
class CodeStudent:
    def __init__(self, store: ProcedureStore,
                 candidate: Optional[Dict] = None) -> None:
        self.store = store
        self.candidate = candidate

    def _record(self, skill_id: str) -> Optional[Dict]:
        record = self.store.get(skill_id)
        if record is not None:
            return record
        if self.candidate is not None \
                and self.candidate.get("skill_id") == skill_id:
            return self.candidate
        return None

    def _cannot(self, skill_id: str) -> Dict:
        return {"status": "CANNOT_MISSING_SKILL",
                "missing_skill": skill_id,
                "detail": f"i have not learned "
                          f"{skill_id.replace('_', ' ')} yet"}

    # -- CODE-L0: read and trace ---------------------------------------
    def trace_predict(self, code: str, fname: str,
                      args: List) -> Dict:
        if self._record("read_and_trace") is None:
            return self._cannot("read_and_trace")
        result = tracer.trace_run(code, fname, args)
        if result["status"] != "OK":
            return {"status": "ERROR",
                    "detail": result.get("error",
                                         result["status"])}
        return {"status": "SOLVED", "prediction": result["value"],
                "trace_events": len(result["events"])}

    # -- CODE-L1/L2: implement from a typed contract -------------------
    def implement(self, skill_id: str, spec: Dict) -> Dict:
        record = self._record(skill_id)
        if record is None:
            return self._cannot(skill_id)
        code = record["formal"]["code"]
        base_fname = record["formal"]["function_name"]
        base_params = record["formal"]["params"]
        new_params = [p["name"] for p in spec["params"]]
        if len(base_params) != len(new_params):
            return {"status": "ERROR",
                    "detail": "the specification's arity does not "
                              "match my learned procedure"}
        param_map = dict(zip(base_params, new_params))
        try:
            adapted = adapt_code(code, base_fname,
                                 spec["function_name"], param_map)
        except Exception as exc:
            return {"status": "ERROR",
                    "detail": f"adaptation failed: {exc}"}
        return {"status": "SOLVED", "code": adapted,
                "adapted_from": skill_id}

    # -- CODE-L3: generate a test suite --------------------------------
    def generate_tests(self, skill_id: str, spec: Dict) -> Dict:
        if self._record("contracts_testing") is None:
            return self._cannot("contracts_testing")
        base = self._record(skill_id)
        if base is None:
            return self._cannot(skill_id)
        suite: List[Dict] = []
        for args in boundary_inputs(skill_id):
            suite.append({"args": args, "kind": "boundary"})
        for example in spec.get("public_examples", []):
            suite.append({"args": example["args"],
                          "kind": "public"})
        # NEGATIVE tests: wrong-arity calls must raise, not return
        suite.append({"args": [], "kind": "negative",
                      "expect_error": True})
        return {"status": "SOLVED", "suite": suite,
                "principle": "one passing example does not "
                             "establish correctness"}

    # -- CODE-L4: the walk-down and minimal repair ---------------------
    def diagnose_and_repair(self, skill_id: str, buggy_code: str,
                            failing_args: List,
                            battery) -> Dict:
        if self._record("debug_repair") is None:
            return self._cannot("debug_repair")
        reference = self._record(skill_id)
        if reference is None:
            return self._cannot(skill_id)
        ref_code = reference["formal"]["code"]
        fname = reference["formal"]["function_name"]
        buggy_trace = tracer.trace_run(buggy_code, fname,
                                       failing_args)
        ref_trace = tracer.trace_run(ref_code, fname, failing_args)
        diagnosis = None
        if buggy_trace["events"] and ref_trace["events"]:
            diagnosis = tracer.first_divergence(
                buggy_trace["events"], ref_trace["events"])
        focus_line = diagnosis.get("line") if diagnosis else None
        fixed = repair_mod.repair(buggy_code, battery,
                                  focus_line=focus_line)
        if fixed is None:
            return {"status": "ERROR", "diagnosis": diagnosis,
                    "detail": "no single-edit repair passes the "
                              "full battery - i cannot repair this "
                              "within my learned method"}
        changed = repair_mod.diff_lines(buggy_code,
                                        fixed["patched_code"])
        return {"status": "SOLVED", "diagnosis": diagnosis,
                "patched_code": fixed["patched_code"],
                "changed_lines": changed,
                "candidates_tried": fixed["candidates_tried"],
                "verified_by": "full_battery_pass"}
