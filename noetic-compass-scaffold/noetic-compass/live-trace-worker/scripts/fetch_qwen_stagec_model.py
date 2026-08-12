#!/usr/bin/env python3
"""Acquire the exact Stage C Qwen snapshot during an image build.

This file is a build helper, not a runtime downloader.  It writes the seven
admitted Hugging Face artifacts as ordinary files, bounds every download by
its frozen byte length, and verifies SHA-256 before the temporary file is
renamed into the snapshot.  The Stage C batch image does not retain or invoke
this helper.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
HF_CACHE_RELATIVE_SNAPSHOT = (
    "hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/" + REVISION
)
USER_AGENT = "cas-harness-stagec-image-builder/1.0"
CHUNK_BYTES = 1 << 20


@dataclass(frozen=True, slots=True)
class Artifact:
    byte_length: int
    sha256: str


ARTIFACTS: Mapping[str, Artifact] = {
    "config.json": Artifact(
        659,
        "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45",
    ),
    "generation_config.json": Artifact(
        242,
        "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
    ),
    "merges.txt": Artifact(
        1_671_839,
        "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
    ),
    "model.safetensors": Artifact(
        988_097_824,
        "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
    ),
    "tokenizer.json": Artifact(
        7_031_645,
        "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    ),
    "tokenizer_config.json": Artifact(
        7_305,
        "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
    ),
    "vocab.json": Artifact(
        2_776_833,
        "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    ),
}


class Response(Protocol):
    def __enter__(self) -> BinaryIO: ...

    def __exit__(self, *args: object) -> object: ...


OpenUrl = Callable[[urllib.request.Request, float], Response]


def _validate_contract(artifacts: Mapping[str, Artifact]) -> None:
    if len(artifacts) != 7:
        raise RuntimeError("the frozen Qwen snapshot must contain exactly 7 files")
    for name, artifact in artifacts.items():
        if Path(name).name != name or name in {"", ".", ".."}:
            raise RuntimeError(f"invalid artifact name: {name!r}")
        if type(artifact.byte_length) is not int or artifact.byte_length <= 0:
            raise RuntimeError(f"invalid byte length for {name}")
        if re.fullmatch(r"[0-9a-f]{64}", artifact.sha256) is None:
            raise RuntimeError(f"invalid SHA-256 for {name}")


def _artifact_url(name: str) -> str:
    model_path = "/".join(urllib.parse.quote(part, safe="") for part in MODEL_ID.split("/"))
    filename = urllib.parse.quote(name, safe="")
    return f"https://huggingface.co/{model_path}/resolve/{REVISION}/{filename}"


def _default_open(request: urllib.request.Request, timeout: float) -> Response:
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - fixed HTTPS host/revision


def _chunks(handle: BinaryIO) -> Iterator[bytes]:
    while True:
        chunk = handle.read(CHUNK_BYTES)
        if not chunk:
            return
        yield chunk


def _require_regular_file(path: Path) -> os.stat_result:
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode):
        raise RuntimeError(f"artifact is not a regular file: {path.name}")
    return observed


def verify_snapshot(
    snapshot: Path,
    *,
    artifacts: Mapping[str, Artifact] = ARTIFACTS,
) -> dict[str, tuple[int, str]]:
    """Re-hash an exact seven-file snapshot and reject aliases or extras."""

    _validate_contract(artifacts)
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise RuntimeError("snapshot destination is not a real directory")
    observed_names = {path.name for path in snapshot.iterdir()}
    expected_names = set(artifacts)
    if observed_names != expected_names:
        missing = sorted(expected_names - observed_names)
        extras = sorted(observed_names - expected_names)
        raise RuntimeError(
            f"snapshot membership mismatch; missing={missing!r}; extras={extras!r}"
        )

    observations: dict[str, tuple[int, str]] = {}
    for name in sorted(artifacts):
        expected = artifacts[name]
        path = snapshot / name
        observed = _require_regular_file(path)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in _chunks(handle):
                digest.update(chunk)
        actual_digest = digest.hexdigest()
        if observed.st_size != expected.byte_length:
            raise RuntimeError(
                f"{name} byte length mismatch: {observed.st_size} != "
                f"{expected.byte_length}"
            )
        if actual_digest != expected.sha256:
            raise RuntimeError(
                f"{name} SHA-256 mismatch: {actual_digest} != {expected.sha256}"
            )
        observations[name] = (observed.st_size, actual_digest)
    return observations


def fetch_snapshot(
    snapshot: Path,
    *,
    artifacts: Mapping[str, Artifact] = ARTIFACTS,
    open_url: OpenUrl = _default_open,
    timeout_seconds: float = 120.0,
) -> dict[str, tuple[int, str]]:
    """Download, size-bound, hash, and atomically admit one exact snapshot."""

    _validate_contract(artifacts)
    if snapshot.exists() or snapshot.is_symlink():
        raise RuntimeError("snapshot destination must not already exist")
    snapshot.mkdir(parents=True, mode=0o755)

    try:
        for name in sorted(artifacts):
            expected = artifacts[name]
            destination = snapshot / name
            partial = snapshot / f".{name}.partial"
            request = urllib.request.Request(
                _artifact_url(name),
                headers={"User-Agent": USER_AGENT},
                method="GET",
            )
            digest = hashlib.sha256()
            byte_length = 0
            with open_url(request, timeout_seconds) as response, partial.open(
                "xb"
            ) as handle:
                final_url = getattr(response, "geturl", lambda: request.full_url)()
                if not str(final_url).lower().startswith("https://"):
                    raise RuntimeError(f"{name} download left HTTPS")
                for chunk in _chunks(response):
                    byte_length += len(chunk)
                    if byte_length > expected.byte_length:
                        raise RuntimeError(f"{name} exceeded its frozen byte length")
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if byte_length != expected.byte_length:
                raise RuntimeError(
                    f"{name} byte length mismatch: {byte_length} != "
                    f"{expected.byte_length}"
                )
            actual_digest = digest.hexdigest()
            if actual_digest != expected.sha256:
                raise RuntimeError(
                    f"{name} SHA-256 mismatch: {actual_digest} != {expected.sha256}"
                )
            partial.replace(destination)
            _require_regular_file(destination)
            print(
                f"verified {name} {byte_length} bytes sha256={actual_digest}",
                flush=True,
            )
    except BaseException:
        for path in snapshot.iterdir():
            if path.is_file() and not path.is_symlink():
                path.unlink()
        snapshot.rmdir()
        raise

    return verify_snapshot(snapshot, artifacts=artifacts)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    observations = fetch_snapshot(args.snapshot)
    total = sum(byte_length for byte_length, _ in observations.values())
    print(
        f"QWEN STAGE C SNAPSHOT VERIFIED: {len(observations)} files / {total} bytes",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
