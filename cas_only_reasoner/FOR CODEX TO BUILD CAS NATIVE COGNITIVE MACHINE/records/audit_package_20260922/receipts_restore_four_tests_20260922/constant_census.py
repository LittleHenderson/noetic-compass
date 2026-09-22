import ast, pathlib, subprocess
P = "noetic-compass-scaffold/noetic-compass/tests/test_offline_help_text_canon.py"
def consts(text):
    out = {}
    for n in ast.parse(text).body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = ast.dump(n.value)
    return out
old = consts(subprocess.run(["git", "show", "7f32129d:" + P], capture_output=True, check=True).stdout.decode("utf-8"))
new = consts(pathlib.Path(P).read_text(encoding="utf-8"))
for k in sorted(set(old) | set(new)):
    state = "same" if old.get(k) == new.get(k) else ("MISSING NOW" if k not in new else ("NEW" if k not in old else "DIFFERS"))
    print(k, state)
