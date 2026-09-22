"""Show a unified diff of named test function bodies across revisions (git objects) and the working tree."""
import ast
import difflib
import pathlib
import subprocess
import sys

path, names, revs = sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(",")


def source(rev):
    if rev == "WT":
        return pathlib.Path(path).read_text(encoding="utf-8")
    return subprocess.run(["git", "show", rev + ":" + path], capture_output=True, check=True).stdout.decode("utf-8")


def body(text, name):
    for n in ast.walk(ast.parse(text)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return ast.get_source_segment(text, n)
    return None


for name in names:
    bodies = {r: body(source(r), name) for r in revs}
    print("=" * 20, name)
    for a, b in zip(revs, revs[1:]):
        if bodies[a] == bodies[b]:
            print("  %s == %s" % (a, b))
        else:
            print("  %s != %s" % (a, b))
            for line in difflib.unified_diff((bodies[a] or "").splitlines(), (bodies[b] or "").splitlines(), a, b, lineterm="", n=0):
                print("    " + line)
