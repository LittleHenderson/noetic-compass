"""For every test file changed on my side of the merge, compare each test function body at d50abbbc with the
body in the working tree. A surviving name with a different body means the merge kept another version."""
import ast
import pathlib
import subprocess


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, check=True).stdout.decode("utf-8")


def tests(text):
    tree = ast.parse(text)
    return {n.name: ast.get_source_segment(text, n) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")}


files = [p for p in git("diff", "--name-only", "c3855275", "d50abbbc").splitlines()
         if p.endswith(".py") and pathlib.PurePosixPath(p).name.startswith("test")]
total = 0
for p in files:
    left = tests(git("show", "d50abbbc:" + p))
    now = tests(pathlib.Path(p).read_text(encoding="utf-8"))
    total += len(left)
    missing = sorted(set(left) - set(now))
    differs = sorted(n for n in left if n in now and left[n] != now[n])
    print(pathlib.PurePosixPath(p).name, "| my-side test fns:", len(left), "| missing:", missing, "| body differs:", differs)
print("total my-side test functions compared:", total)
