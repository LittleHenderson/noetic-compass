"""Probe the Rust engine directly: does the compiler's Rust path really run, or does it fall back to Python?

The compiler (lines 5197-5217) calls cas_engine.multiply_cognitive_states / divide_cognitive_states and, on ANY
exception, silently falls back to the Python rules. It passes `left.explicit_drive or 4` as the drive, and
`explicit_drive` is a True/False flag on a fresh state. This script measures, for every operator pair and every
Domain pair, whether the Rust call succeeds, what it returns, and whether the drive argument changes the answer.
Run on the cloud machine with the venv that has cas_engine installed.
"""
import json
import sys

import cas_engine as R


def call(fn, *args):
    try:
        return list(fn(*args))
    except Exception as exc:  # noqa: BLE001 - we are measuring exactly which calls raise
        return "ERROR: %s" % exc


out = {"times": {}, "divide": {}}
for name, fn in (("times", R.multiply_cognitive_states), ("divide", R.divide_cognitive_states)):
    raised, ok, drive_sensitive, examples = 0, 0, 0, []
    for a in range(10):
        for b in range(10):
            for dl in range(4):
                for dr in range(4):
                    base = call(fn, a, dl, 4, b, dr, 4)
                    if isinstance(base, str):
                        raised += 1
                        if len(examples) < 6:
                            examples.append([a, dl, b, dr, base])
                        continue
                    ok += 1
                    # same states, every drive pair: does the (operator, domain) answer move?
                    answers = {tuple(r[:2]) for r in (call(fn, a, dl, x, b, dr, y) for x in range(1, 8) for y in range(1, 8))
                               if not isinstance(r, str)}
                    if len(answers) > 1:
                        drive_sensitive += 1
    out[name] = {"calls": raised + ok, "rust_ok": ok, "rust_raised_so_python_fallback": raised,
                 "op_or_domain_depends_on_drive": drive_sensitive, "first_errors": examples}

# What the compiler actually passes as the drive for a fresh state: `explicit_drive or 4`.
sys.path.insert(0, sys.argv[1])
from api.notation import compiler as C  # noqa: E402

art = C.compile_expression("^2^C_{F2}")
v = art.result
out["fresh_state_explicit_drive"] = repr(v.explicit_drive)
out["drive_value_passed_to_rust"] = repr(v.explicit_drive or 4)
r1 = C.compile_expression("^2^C_{F2} * ^3^C_{F5}").result
out["after_one_times_explicit_drive"] = repr(r1.explicit_drive)
out["synthesize_drives_F2_F5"] = R.synthesize_drives(2, 5)
out["rust_drive_for_inputs_True_True"] = call(R.multiply_cognitive_states, 2, 1, True, 3, 1, True)
print(json.dumps(out, indent=1))
