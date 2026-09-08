"""Build the pinned second-slice input package without GPU or provider access."""
import argparse
import importlib.abc
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
FORBIDDEN = {"torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt", "cas_meta",
             "boto3", "botocore", "jax", "tensorflow"}


def main(argv=None):
    if FORBIDDEN.intersection(sys.modules):
        raise RuntimeError("PRIOR_BUILD_V2:FORBIDDEN_MODULE_ALREADY_LOADED")
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("PRIOR_BUILD_V2:FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("PRIOR_BUILD_V2:FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent-result", "complete-marker", "archive", "extracted-root",
                 "inspection-report", "evaluation-report", "parent-sha256",
                 "complete-sha256", "archive-sha256", "inspection-sha256",
                 "evaluation-sha256", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = vars(parser.parse_args(argv))
    from cas_meta2.teaching_cycle import continuation_package_v2 as package
    output = package._safe(args["output_dir"])
    package.require(output.is_relative_to(RECORDS), "OUTPUT_OUTSIDE_TEACHING_RECORDS")
    result = package.build_package(**args)
    package.require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_RUNTIME_LOADED")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
