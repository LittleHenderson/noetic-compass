#!/usr/bin/env python3
"""Write Grok-1 model provenance for CAS Harness Evidence Packets."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_REVISION = "a3e24db6da7a408247df40a55ed6ac63cb250aa3"
HASHED_EXTENSIONS = {".json", ".py", ".safetensors"}
REQUIRED_FILES = {
    "config.json",
    "configuration_grok1.py",
    "modeling_grok1.py",
    "model.safetensors.index.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--expected-shards", type=int, default=17)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_dir = args.model_dir
    if not model_dir.is_dir():
        raise SystemExit(f"model_dir does not exist: {model_dir}")

    missing = sorted(file_name for file_name in REQUIRED_FILES if not (model_dir / file_name).is_file())
    shard_paths = sorted(model_dir.glob("model-*.safetensors"))
    if len(shard_paths) != args.expected_shards:
        missing.append(f"expected {args.expected_shards} safetensors shards, found {len(shard_paths)}")
    if missing:
        raise SystemExit("model provenance cannot be sealed; missing: " + ", ".join(missing))

    artifacts: list[dict[str, Any]] = []
    for path in sorted(model_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file():
            continue
        if path.name not in REQUIRED_FILES and path.suffix not in HASHED_EXTENSIONS:
            continue
        artifacts.append(
            {
                "file": path.name,
                "byte_count": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    payload: dict[str, Any] = {
        "schema_version": "cas_harness_model_provenance.v1",
        "created_at": datetime.now(tz=UTC).isoformat(),
        "model_family": "grok-1",
        "model_publisher_of_record": "xai-org",
        "original_checkpoint": "xai-org/grok-1",
        "original_checkpoint_format": "jax/orbax",
        "consumed_checkpoint": "TevunahAi/Grok-1-BF16",
        "consumed_checkpoint_format": "huggingface-bf16-safetensors",
        "conversion_path": "jax/orbax->huggingface-bf16-safetensors",
        "conversion_authority": "third-party (TevunahAi), not xAI",
        "conversion_audit_status": "unverified-by-cas-harness",
        "consumed_checkpoint_commit": args.revision,
        "consumed_checkpoint_revision_pinned": True,
        "license": "Apache-2.0",
        "parameter_count_claimed": "316.5B total, approximately 78B active per token",
        "architecture_claimed": "Decoder-only Top-2 MoE, 8 experts, GQA, 64 layers",
        "tokenizer_source": "hpcai-tech/grok-1 tokenizer files copied into consumed checkpoint directory",
        "local_model_dir": str(model_dir),
        "artifact_hashes": artifacts,
        "artifact_count": len(artifacts),
        "safetensors_shard_count": len(shard_paths),
        "important_limit": (
            "CAS Harness audited the consumed Hugging Face BF16 conversion that ran on this pod, "
            "not the original xAI JAX checkpoint directly."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"hashed_files={len(artifacts)}")
    return 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(32 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
