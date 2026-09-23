"""R4: assigned-never-read scan, two independent methods (stdlib only; scanned code is NOT imported).

Method 1 (symtable): for every function/class scope, a symbol that is assigned/imported/a parameter
and is never referenced in that scope, and never referenced as a FREE variable in any nested scope.
Method 2 (ast): for every function body, Name(Store) ids with no Name(Load) anywhere in that
function's subtree (so closures count as reads). Also self.<attr> stores never read as .<attr>.
"""
import ast, sys, pathlib, symtable

LAB = pathlib.Path(sys.argv[1])
FILES = sorted(LAB.glob("learner_q4_*.py")) + [LAB / "q4_smoke_job.py", LAB / "q4_checkpoint.py"]


def free_refs(table):
    out = set()
    for child in table.get_children():
        for sym in child.get_symbols():
            if sym.is_free() and sym.is_referenced():
                out.add(sym.get_name())
        out |= free_refs(child)
    return out


def walk_tables(table, path, results):
    frees = free_refs(table)
    for sym in table.get_symbols():
        name = sym.get_name()
        bound = sym.is_assigned() or sym.is_imported() or sym.is_parameter()
        if not bound or name.startswith("__") or name == "_":
            continue
        if sym.is_referenced() or name in frees:
            continue
        results.append((table.get_type().name if hasattr(table.get_type(), "name") else str(table.get_type()),
                        table.get_name(), table.get_lineno(), name, sym.is_parameter()))
    for child in table.get_children():
        walk_tables(child, path, results)


for path in FILES:
    src = path.read_text(encoding="utf-8")
    print("== %s" % path.name)
    res = []
    walk_tables(symtable.symtable(src, str(path), "exec"), path, res)
    for kind, scope, line, name, is_param in res:
        tag = "PARAM" if is_param else ("MODULE_NAME(may be exported)" if scope == "top" else "LOCAL")
        print("  [symtable] %-8s scope=%s@%d  %s  %s" % (kind, scope, line, name, tag))
    tree = ast.parse(src)
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stores = {}
            loads = set()
            for node in ast.walk(fn):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        stores.setdefault(node.id, node.lineno)
                    elif isinstance(node.ctx, (ast.Load, ast.Del)):
                        loads.add(node.id)
                elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                    loads.add(node.target.id)
            for name, line in sorted(stores.items(), key=lambda kv: kv[1]):
                if name not in loads and name != "_":
                    print("  [ast] function %s: '%s' stored at line %d, never loaded in the function subtree" % (fn.name, name, line))
    attr_store, attr_load = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.ctx, ast.Store) and isinstance(node.value, ast.Name) and node.value.id == "self":
                attr_store.setdefault(node.attr, node.lineno)
            elif isinstance(node.ctx, ast.Load):
                attr_load.add(node.attr)
    for attr, line in sorted(attr_store.items(), key=lambda kv: kv[1]):
        state = "read in this file" if attr in attr_load else "NOT read in this file"
        print("  [attr] self.%s stored line %d: %s" % (attr, line, state))
