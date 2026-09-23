"""Print the frozen checker and slot-compiler profile digests of ONE package tree (used by D-1 test A1).

    python -B frozen_profiles.py --root <CNCM root> --out profiles.json

Run it on the ORIGINAL tree (Helm 2.0 source 20208c92); `d1_acceptance_run.py --frozen-profile-json` then requires
the v2 tree's frozen modules to report the same two digests. Non-neural, imports only the typed-teaching package.
"""
import argparse
import json
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(pathlib.Path(args.root).resolve() / "research" / "CAS_META_2_COMPOSITION"))
    from cas_meta2.typed_teaching import checker, slots
    out = {"root": str(pathlib.Path(args.root).resolve()),
           "checker_profile_digest": checker.checker_profile()["profile_digest"],
           "checker_profile_schema": checker.checker_profile()["schema"],
           "slot_profile_digest": slots.profile()["profile_digest"],
           "slot_profile_schema": slots.profile()["schema"]}
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
