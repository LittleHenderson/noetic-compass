"""Finalize an already approved PCBA authority receipt by computing its hash."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_authority import PcbaAuthorityReceipt  # noqa: E402


def finalize_receipt(*, receipt_path: Path, output_path: Path, artifact_root: Path) -> PcbaAuthorityReceipt:
    receipt = PcbaAuthorityReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    receipt.receipt_hash = None
    receipt.finalize()
    if not receipt.verify(artifact_root=artifact_root):
        raise ValueError(
            "Receipt could not be verified after finalization; check approval fields and artifact hashes."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(receipt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipt",
        default=r"..\docs\working\pcba_semantics_review_request_20260617.json",
    )
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--artifact-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root used to verify receipt artifact_refs.",
    )
    args = parser.parse_args()
    receipt_path = Path(args.receipt)
    output_path = Path(args.out) if args.out else receipt_path

    receipt = finalize_receipt(
        receipt_path=receipt_path,
        output_path=output_path,
        artifact_root=Path(args.artifact_root),
    )
    print(receipt.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
