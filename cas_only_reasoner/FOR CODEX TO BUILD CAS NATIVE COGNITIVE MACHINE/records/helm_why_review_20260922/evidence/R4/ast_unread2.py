"""R4: assigned-never-read scan by pure ast walk (scanned code is NOT imported or executed).

Per function (FunctionDef/AsyncFunctionDef/Lambda): bindings = parameters + Name(Store) + import
aliases + nested def names, collected in the function's WHOLE subtree; reads = Name(Load/Del)
anywhere in that subtree (so closure and comprehension reads count). Report bindings never read.
Module level: top-level bindings never read anywhere in the file (may still be exported API).
Attributes: self.<attr> stores never read as .<attr> in the file (other files may read them).
"""
import ast, sys, pathlib

LAB = pathlib.Path(sys.argv[1])
FILES = sorted(LAB.glob("learner_q4_*.py")) + [LAB / "q4_smoke_job.py", LAB / "q4_checkpoint.py"]


def bindings_and_reads(root, include_nested_defs=True):
    binds, reads = {}, set()
    for node in ast.walk(root):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                binds.setdefault(node.id, node.lineno)
            else:
                reads.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                binds.setdefault((a.asname or a.name).split(".")[0], node.lineno)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            reads.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not root:
            binds.setdefault(node.name, node.lineno)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            binds.setdefault(node.name, node.lineno)
    return binds, reads


total = 0
for path in FILES:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    print("== %s" % path.name)
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = fn.args
            params = {p.arg: p.lineno for p in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]}
            binds, reads = bindings_and_reads(fn)
            name = getattr(fn, "name", "<lambda>")
            for var, line in sorted({**params, **binds}.items(), key=lambda kv: kv[1]):
                if var in reads or var in ("self", "_") or var.startswith("_") and var in params and False:
                    continue
                kind = "PARAMETER" if var in params else "LOCAL"
                print("  UNREAD %-9s %-20s line %-4d in %s()" % (kind, var, line, name))
                total += 1
    # module level
    top_binds = {}
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top_binds.setdefault(stmt.name, stmt.lineno)
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for al in stmt.names:
                top_binds.setdefault((al.asname or al.name).split(".")[0], stmt.lineno)
        else:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    top_binds.setdefault(node.id, node.lineno)
    _, all_reads = bindings_and_reads(tree)
    attr_reads = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)}
    for var, line in sorted(top_binds.items(), key=lambda kv: kv[1]):
        if var not in all_reads and var != "annotations":
            print("  MODULE-LEVEL name never read in this file: %-22s line %d (may be exported API)" % (var, line))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store)
                and isinstance(node.value, ast.Name) and node.value.id == "self" and node.attr not in attr_reads):
            print("  ATTR self.%s stored line %d never read as .%s in this file" % (node.attr, node.lineno, node.attr))
print("TOTAL function-level unread bindings:", total)
