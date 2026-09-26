"""Launch one frozen replication seed through the unchanged c45 launcher."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_replication as admission

def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    cut = args.index("--")
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True, choices=admission.SEEDS)
    parser.add_argument("--plan-sha256", required=True)
    selected = parser.parse_args(args[:cut])
    admission.load_plan(selected.plan_sha256)
    study = json.loads((admission.HERE / "admission" / str(selected.seed) / "study.json").read_bytes())
    expected = study["job_record"]["launch_argv"]
    if args != expected:
        raise ValueError("EXACT_FROZEN_LAUNCH_ARGUMENTS_REQUIRED")
    admission.verify_source_and_package()
    with admission.seed_context(selected.seed):
        return admission.launch.main(args[cut + 1:])

if __name__ == "__main__":
    raise SystemExit(main())
