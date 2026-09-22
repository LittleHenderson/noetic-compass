"""For every .py file changed on MY side of merge 078d00ed (merge-base..d50abbbc), list every function and method
defined at d50abbbc and report any that no longer exists at the same path in the working tree.

Scope is deliberately wider than tests: production code too, and nested functions/methods, by qualified name.
"""
import ast
import pathlib
import subprocess
import sys

repo = pathlib.Path(sys.argv[1])


def git(*args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout


def names(text):
    out = set()

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = prefix + child.name
                out.add(q)
                walk(child, q + ".")
            else:
                walk(child, prefix)

    walk(ast.parse(text), "")
    return out


base = git("merge-base", "d50abbbc", "04547c55").decode().strip()
changed = [p for p in git("diff", "--name-only", base, "d50abbbc").decode().splitlines() if p.endswith(".py")]
missing, checked, gone_files = {}, 0, []
for p in changed:
    try:
        left = git("show", "d50abbbc:" + p).decode("utf-8")
    except subprocess.CalledProcessError:
        continue                                     # deleted on my side: nothing to lose
    wt = repo / p
    if not wt.is_file():
        gone_files.append(p)
        continue
    lost = sorted(names(left) - names(wt.read_text(encoding="utf-8")))
    checked += 1
    if lost:
        missing[p] = lost

print("merge-base", base[:8], "| .py files changed on my side:", len(changed), "| compared:", checked)
print("files gone from working tree:", gone_files)
print("files with functions missing now:", len(missing))
for p, lost in missing.items():
    print("  ", p)
    for n in lost:
        print("      -", n)
