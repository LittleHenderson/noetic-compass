"""Retain the source-bound, no-neural-work encoder counterexamples."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cas_meta2.graph_teaching.ordered_encoder_probe import algebraic_audit, write_json, witness_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to((ROOT / "records").resolve()):
        raise ValueError("AUDIT_OUTPUT_MUST_STAY_IN_RECORDS")
    output.mkdir(parents=True, exist_ok=True)
    receipt = write_json(output / "algebraic_audit.json", algebraic_audit(ROOT))
    write_json(output / "public_witnesses.json", witness_cases())
    print(receipt)


if __name__ == "__main__":
    main()
