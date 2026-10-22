"""mutation_probe.py <amended_copy_root> <work_dir> -- break one A-R1W7-11 rule at a time in a throwaway copy of the amended
package and run tests_r1w7.test_honest_ask_w7 there; each mutant must make at least one test fail. Scratch only."""
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()            # .../a11_iter1 (holds HELM_R1_W7_20261020 and deps)
WORK = Path(sys.argv[2]).resolve()
MUTANTS = {
    "e_always_true": ("r1w7/honest_ask_w7.py",
                      'out["e"] = bool(allowed) and all(RC.head_norm(RC.last_word(n)) in allowed for n in names)',
                      'out["e"] = True'),
    "c_ignores_path": ("r1w7/honest_ask_w7.py", 'and log[-1].get("path") == "wide")', ')'),
    "d_ignores_count": ("r1w7/honest_ask_w7.py", 'and slots - coef == len(names)', ''),
    "no_hook_call": ("r1w7/score_w7.py", "    HA.apply(ns, out, keys, inputs, doc, raw_by_id)", "    pass  # "),
    "k4_reads_strict": ("r1w7/merge_r1w7.py",
                        't.get("a11_consistent") is True and t.get("unexplained_asks_strict_after_a11") == 0',
                        't.get("unexplained_asks_strict") == 0'),
    "deny_list_empty": ("r1w7/honest_ask_w7.py", 'if PARTICIPLE_RX.match(h) or n in deny or', 'if False and'),
}


def main() -> int:
    bad = 0
    for name, (rel, old, new) in MUTANTS.items():
        d = WORK / name
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(SRC, d)
        f = d / "HELM_R1_W7_20261020" / rel
        s = f.read_bytes().decode("utf-8")
        assert s.count(old) == 1, (name, s.count(old))
        f.write_bytes(s.replace(old, new, 1).encode("utf-8"))
        code = ("import sys, unittest; sys.path.insert(0, %r); "
                "r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromNames("
                "['tests_r1w7.test_honest_ask_w7'])); print('RESULT', r.testsRun, len(r.failures), len(r.errors))"
                % str(d / "HELM_R1_W7_20261020"))
        p = subprocess.run([sys.executable, "-X", "utf8", "-B", "-I", "-c", code], capture_output=True, text=True,
                           cwd=str(d), timeout=600)
        line = [x for x in p.stdout.splitlines() if x.startswith("RESULT")]
        res = line[-1] if line else "NO RESULT " + p.stderr[-300:]
        killed = bool(line) and (int(line[-1].split()[2]) + int(line[-1].split()[3])) > 0
        bad += 0 if killed else 1
        print(name, res, "KILLED" if killed else "SURVIVED")
        shutil.rmtree(d)
    print("MUTANTS", len(MUTANTS), "SURVIVED", bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
