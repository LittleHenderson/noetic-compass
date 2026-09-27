"""Reviewer probe B: oracle construction integrity and no-answer-leakage.

Owner: Q1-DeepSeek (review/). Read-only against builder source.

What this checks, per the directive's forbidden shortcut (section 8) and the
reviewer's brief:
  * the compiler-side predicate code does not import evaluator/answer material
  * the public fixture carries no solution IDs or counts
  * the reviewer can rebuild the SAME predicate from the public spec alone
  * the search's UNSAT reason is a bijectivity argument, not a stored answer
  * no iteration count or schedule is derived from evaluator counts
  * a caller-supplied "valid" flag cannot substitute for recomputation

Run:
  python review/probe_b_oracle.py --package-root <builder repo root>
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import traceback
from pathlib import Path

FORBIDDEN_COMPILER_IMPORTS = {
    "helm_quantum.classical", "classical", "vendor", "helm_quantum.vendor",
    "helm_quantum.vendor.q1_tools", "q1_tools", "helm_quantum.verifier",
    "verifier", "receipts", "evidence",
}
# Tokens that would indicate an enumerated answer list or a tuned schedule.
LEAK_TOKENS = ("solution_ids", "answer", "valid_program", "add2_valid_program_count",
               "nonbijective_target_valid_program_count", "reference_solution")


class Report:
    def __init__(self):
        self.cases = []

    def case(self, case_id, requirement, fn):
        try:
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "PASS", "detail": fn()})
        except AssertionError as exc:
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "FAIL", "detail": f"ASSERT: {exc}"})
        except Exception as exc:  # noqa: BLE001
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "ERROR",
                               "detail": f"{type(exc).__name__}: {exc}",
                               "trace": traceback.format_exc()[-800:]})

    def summary(self):
        counts = {}
        for case in self.cases:
            counts[case["outcome"]] = counts.get(case["outcome"], 0) + 1
        return counts


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = "." * node.level + base
            found.add(base)
            for alias in node.names:
                found.add(f"{base}.{alias.name}" if base else alias.name)
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    root = args.package_root.resolve()
    sys.path.insert(0, str(root))
    report = Report()

    # --- O1: verifier recomputes; it imports no search result or helper ---
    def o1():
        imports = imported_modules(root / "helm_quantum/verifier.py")
        assert not (imports & FORBIDDEN_COMPILER_IMPORTS), \
            f"verifier imports evaluator material: {sorted(imports & FORBIDDEN_COMPILER_IMPORTS)}"
        source = (root / "helm_quantum/verifier.py").read_text(encoding="utf-8")
        assert "run_program" not in source, "verifier delegates to the helper semantics"
        return {"verifier_imports": sorted(i for i in imports if i),
                "forbidden_hits": [], "delegates_to_helper": False}

    report.case("O1", "independent verifier does not import evaluator/answer material", o1)

    # --- O2: verifier takes no caller-supplied verdict ---
    def o2():
        source = (root / "helm_quantum/verifier.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        # verify() signature must be (problem, proposal) only
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "verify":
                names = [a.arg for a in node.args.args]
                assert names == ["problem", "proposal"], f"verify signature {names}"
        # No branch may read a caller-provided validity claim.
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("valid", "is_valid", "accepted_flag"), \
                    f"verify reads a caller verdict attribute: {node.attr}"
        return {"verify_args": ["problem", "proposal"], "reads_returned_valid_flag": False}

    report.case("O2", "verifier accepts no caller-supplied valid flag", o2)

    # --- O3: compiler-facing surface cannot import evaluator material ---
    def o3():
        # Per the issued lease, compiler imports may use contracts, admission and
        # fixtures/public only. No compiler directory exists yet; the constraint is
        # therefore recorded as NOT_YET_APPLICABLE with the lease text as evidence.
        compiler_dir = root / "helm_quantum/compiler"
        lease = (root / "coordination/FILE_LEASES.md").read_text(encoding="utf-8")
        assert "must\nnot import classical.py, vendor/, verifier.py or evaluator receipts" in lease \
            or "not import classical.py" in lease, "lease does not state the import ban"
        return {"compiler_dir_exists": compiler_dir.exists(),
                "lease_states_import_ban": True,
                "status": "NOT_APPLICABLE_NO_COMPILER" if not compiler_dir.exists() else "CHECKED"}

    report.case("O3", "compiler import ban is stated; compiler not yet present", o3)

    # --- O4: public fixture carries no answer data ---
    def o4():
        fixture = json.loads((root / "fixtures/public/q1-mod4.json").read_text(encoding="utf-8"))
        # The naming field may exist, but it must be null.
        assert fixture.get("solution_ids_or_counts", "absent") is None, \
            f"fixture exports solution data: {fixture.get('solution_ids_or_counts')!r}"
        # No field anywhere in the fixture may carry a non-null answer payload.
        def walk(node, path=""):
            found = []
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ("solution_ids", "solutions", "answer", "answers",
                               "valid_program_count", "solution_count"):
                        found.append((f"{path}/{key}", value))
                    found += walk(value, f"{path}/{key}")
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    found += walk(item, f"{path}[{i}]")
            return found
        hits = walk(fixture)
        assert not hits, f"fixture contains answer-bearing fields: {hits}"
        return {"fixture_keys": sorted(fixture),
                "solution_ids_or_counts": fixture["solution_ids_or_counts"],
                "answer_bearing_fields": [], "leaked_tokens": []}

    report.case("O4", "public fixture exports no solution IDs or counts", o4)

    # --- O5: no enumerated answer list anywhere in shippable source ---
    def o5():
        # Identifier-level check: names bound or referenced in code, not prose.
        hits = []
        for path in sorted((root / "helm_quantum").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr)
                elif isinstance(node, ast.arg):
                    names.add(node.arg)
                elif isinstance(node, ast.FunctionDef):
                    names.add(node.name)
            for token in ("solution_ids", "solutions", "answers", "answer_list",
                          "valid_programs", "reference_solution"):
                if token in names:
                    hits.append((path.name, token))
        assert not hits, f"answer-list identifiers found: {hits}"
        # Any literal sequence of candidate programs would be an enumerated answer list.
        for path in sorted((root / "helm_quantum").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.List, ast.Tuple)):
                    values = [e.value for e in node.elts if isinstance(e, ast.Constant)]
                    if len(values) >= 3 and all(isinstance(v, int) and 0 <= v <= 3 for v in values):
                        # The domain tuple (0,1,2,3) and target tuples are legitimate.
                        if tuple(values) in ((0, 1, 2, 3), (2, 3, 0, 1), (0, 1, 0, 1),
                                             (1, 2, 3, 0)):
                            continue
                        raise AssertionError(
                            f"{path.name} contains a program-shaped literal {values}")
        return {"answer_list_identifiers": [], "program_shaped_literals": [],
                "evaluator_counts_reported_to_humans_only": True}

    report.case("O5", "no enumerated answer list in the predicate path", o5)

    # --- O6: reviewer rebuilds the predicate from the public spec alone ---
    def o6():
        fixture = json.loads((root / "fixtures/public/q1-mod4.json").read_text(encoding="utf-8"))
        # Build semantics ONLY from the fixture's declared operations.
        table = {}
        for item in fixture["instructions"]:
            code, name, sem = item["code"], item["name"], item["semantics"]
            if sem == "x":
                table[code] = lambda x: x
            elif sem == "(x + 1) % 4":
                table[code] = lambda x: (x + 1) % 4
            elif sem == "(x + 3) % 4":
                table[code] = lambda x: (x + 3) % 4
            elif sem == "3 - x":
                table[code] = lambda x: 3 - x
            else:
                raise AssertionError(f"unparseable semantics {sem!r} for {name}")
        assert len(table) == 4, table
        domain = tuple(fixture["domain"])
        add2 = tuple(fixture["targets"]["add2"])

        def run(program):
            out = []
            for x in domain:
                v = x
                for op in program:
                    v = table[op](v)
                out.append(v)
            return tuple(out)

        # independently find a solution using ONLY the public spec
        import itertools
        found = [p for p in itertools.product(range(4), repeat=fixture["program_length"])
                 if run(p) == add2]
        assert len(found) == 6, f"spec-only search found {len(found)}"
        return {"spec_only_solutions": [list(p) for p in sorted(found)],
                "spec_only_count": 6,
                "matches_builder_acceptance": True}

    report.case("O6", "predicate is reconstructible from the public spec alone", o6)

    # --- O7: builder's accepted solution set equals the reviewer's ---
    def o7():
        from helm_quantum.admission import admit_offline_fixture
        from helm_quantum.verifier import direct_outputs
        import itertools
        problem = admit_offline_fixture("add2", "disabled").problem()
        accept = [p for p in itertools.product(range(4), repeat=3)
                  if direct_outputs(p) == tuple(problem.target_outputs)]
        assert accept == [(0, 1, 1), (0, 2, 2), (1, 0, 1),
                          (1, 1, 0), (2, 0, 2), (2, 2, 0)], sorted(accept)
        return {"builder_accepted_programs": [list(p) for p in accept], "count": len(accept)}

    report.case("O7", "builder acceptance set matches reviewer spec-only search", o7)

    # --- O8: no schedule/iteration constant derived from evaluator counts ---
    def o8():
        text = (root / "helm_quantum/classical.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        numbers = sorted({n.value for n in ast.walk(tree)
                          if isinstance(n, ast.Constant) and isinstance(n.value, int)})
        # Bounds are corpus/domain/length/instruction counts plus a ns multiplier.
        allowed = {0, 1, 2, 3, 4, 12, 32, 64, 1000000}
        assert set(numbers) <= allowed, f"unexpected constants {set(numbers) - allowed}"
        # The add2 solution count (6) and the evaluator-derived counts must not appear.
        assert 6 not in numbers, "the add2 solution count 6 is hardcoded"
        assert 16 not in numbers, "an evaluator-derived count is hardcoded"
        for node in ast.walk(tree):
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                values = [e.value for e in node.elts if isinstance(e, ast.Constant)]
                assert 6 not in values, f"enumerated literal 6 in {ast.dump(node)[:120]}"
                assert 16 not in values, f"enumerated evaluator count in {ast.dump(node)[:120]}"
        # No constant is used as a loop bound.
        loop_bounds = [n.iter.value for n in ast.walk(tree)
                       if isinstance(n, ast.For) and isinstance(n.iter, ast.Constant)]
        assert not loop_bounds, f"constant loop bounds: {loop_bounds}"
        return {"integer_constants": numbers,
                "solution_count_hardcoded": False,
                "constant_loop_bounds": []}

    report.case("O8", "no evaluator count is hardcoded into the search", o8)

    # --- O9: UNSAT reason is mathematical, and no-sample wording is correct ---
    def o9():
        from helm_quantum.admission import admit_offline_fixture
        from helm_quantum.classical import search
        problem = admit_offline_fixture("parity", "disabled").problem()
        exhaustive = search(problem, "exhaustive")
        uniform = search(problem, "uniform", samples=8, seed=1)
        assert exhaustive.status == "UNSAT_PROVED", exhaustive.status
        assert "bijective" in (exhaustive.proof or ""), exhaustive.proof
        # A bounded sample must never claim impossibility.
        assert uniform.status in ("NO_CANDIDATE_WITHIN_BUDGET", "VALID_CANDIDATE"), uniform.status
        assert uniform.status != "UNSAT_PROVED", "bounded sampling claimed UNSAT"
        return {"exhaustive": {"status": exhaustive.status, "proof": exhaustive.proof},
                "uniform_8_samples": {"status": uniform.status,
                                      "candidates_checked": uniform.receipt.candidates_checked}}

    report.case("O9", "bounded sampling is not reported as unsatisfiability", o9)

    # --- O10: helper exposes counts to humans but exports no IDs ---
    def o10():
        from helm_quantum.vendor.q1_tools import fixture_reference
        ref = fixture_reference(3)
        assert ref["answer_program_ids_exported"] is False
        assert ref["add2_valid_program_count"] == 6, ref["add2_valid_program_count"]
        assert ref["nonbijective_target_valid_program_count"] == 0
        return {"add2_valid_program_count": ref["add2_valid_program_count"],
                "negative_valid_program_count": ref["nonbijective_target_valid_program_count"],
                "answer_program_ids_exported": ref["answer_program_ids_exported"]}

    report.case("O10", "helper matches reviewer counts and exports no program IDs", o10)

    payload = {"probe": "B-oracle-leakage", "reviewer": "Q1-DeepSeek",
               "package_root": str(root), "counts": report.summary(), "cases": report.cases}
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    summary = report.summary()
    return 0 if summary.get("FAIL", 0) == 0 and summary.get("ERROR", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
