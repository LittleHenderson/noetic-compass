"""The frozen read-only check of prereg amendment A4.2, run on the T4 against the repaired source R.

Written by the coordinator BEFORE the builder's change existed. For the switch OFF and ON it builds the container the
same way the preservation and probe tools do, then requires:
  - getattr(model, "analogy_focus_comparison") is a bool equal to the construction argument;
  - setattr of analogy_focus_comparison and of analogy_seed each raises AttributeError, and the value is unchanged;
  - delattr of either raises AttributeError;
  - after model.__dict__["analogy_focus_comparison"] = not value, getattr still returns the construction value.
Forward passes are not run. GPU required (GPU_REQUIRED, exit 3, if CUDA is absent).

    python -B switch_read_only_check.py --package-root <R tree> --out stage0_read_only_check.json
"""
import argparse
import json
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED")
        sys.exit(3)
    package = pathlib.Path(args.package_root).resolve()
    sys.dont_write_bytecode = True
    for p in (package, package / "research" / "CAS_META_2_COMPOSITION"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from cas_meta2.typed_teaching import pointer_learner as PL
    from cncm.typed_matched_worker import _framework
    device = torch.device("cuda")
    results = {}
    for value in (False, True):
        framework = _framework(torch, device, 20260917)
        model = PL._build_container(torch, framework, device, analogy_focus_comparison=value)
        row = {"construction_value": value}
        got = getattr(model, "analogy_focus_comparison")
        row["getattr_is_bool_equal"] = type(got) is bool and got is value
        for name in ("analogy_focus_comparison", "analogy_seed"):
            before = getattr(model, name)
            try:
                setattr(model, name, (not value) if name == "analogy_focus_comparison" else 12345)
                row["setattr_raises_" + name] = False
            except AttributeError:
                row["setattr_raises_" + name] = True
            row["unchanged_after_setattr_" + name] = getattr(model, name) == before
            try:
                delattr(model, name)
                row["delattr_raises_" + name] = False
            except AttributeError:
                row["delattr_raises_" + name] = True
            row["present_after_delattr_" + name] = getattr(model, name, "MISSING") == before
        model.__dict__["analogy_focus_comparison"] = not value
        row["dict_write_does_not_change_getattr"] = getattr(model, "analogy_focus_comparison") is value
        row["analogy_seed"] = getattr(model, "analogy_seed")
        row["analogy_head_present"] = hasattr(model, "analogy_head")
        row["parameter_count"] = sum(t.numel() for t in model.parameters())
        row["pass"] = all(v for k, v in row.items() if k.startswith(("getattr_", "setattr_", "unchanged_", "delattr_",
                                                                       "present_", "dict_write_")))
        results["ON" if value else "OFF"] = row
    out = {"schema": "claude.a4-read-only-check/0.1", "package_root": str(package),
           "device": torch.cuda.get_device_name(0), "torch": torch.__version__, "results": results,
           "pass": all(r["pass"] for r in results.values())}
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({"pass": out["pass"], "OFF": results["OFF"]["pass"], "ON": results["ON"]["pass"]}))
    sys.exit(0 if out["pass"] else 2)


if __name__ == "__main__":
    main()
