from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_metadata(payload: bytes) -> dict[str, object]:
    fields: dict[str, object] = {}
    requirements: list[str] = []
    for line in payload.decode("utf-8").splitlines():
        if line.startswith("Name: "):
            fields["name"] = line.removeprefix("Name: ")
        elif line.startswith("Version: "):
            fields["version"] = line.removeprefix("Version: ")
        elif line.startswith("Requires-Python: "):
            fields["requires_python"] = line.removeprefix("Requires-Python: ")
        elif line.startswith("Requires-Dist: "):
            requirements.append(line.removeprefix("Requires-Dist: "))
    fields["requires_dist"] = requirements
    return fields


def inspect_wheel(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        wheel_name = next(name for name in names if name.endswith(".dist-info/WHEEL"))
        metadata_name = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        wheel_fields: dict[str, str] = {}
        for line in archive.read(wheel_name).decode("utf-8").splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                wheel_fields[key.lower().replace("-", "_")] = value
        result: dict[str, object] = {
            "archive_type": "wheel",
            "bytes": path.stat().st_size,
            "filename": path.name,
            "member_count": len(names),
            "metadata": selected_metadata(archive.read(metadata_name)),
            "sha256": sha256_file(path),
            "wheel": wheel_fields,
        }
        manifest_names = [name for name in names if name.endswith("/SOURCE_MANIFEST.json")]
        if manifest_names:
            payload = archive.read(manifest_names[0])
            document = json.loads(payload)
            result["embedded_source_manifest"] = {
                "aggregate_sha256": document["aggregate_sha256"],
                "file_count": document["file_count"],
                "member": manifest_names[0],
                "sha256": sha256_bytes(payload),
            }
        return result


def inspect_sdist(path: Path) -> dict[str, object]:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        manifest_member = next(
            member
            for member in members
            if member.name.endswith("/SOURCE_MANIFEST.json")
        )
        extracted = archive.extractfile(manifest_member)
        if extracted is None:
            raise RuntimeError("source manifest member has no payload")
        payload = extracted.read()
        document = json.loads(payload)
        return {
            "archive_type": "sdist",
            "bytes": path.stat().st_size,
            "embedded_source_manifest": {
                "aggregate_sha256": document["aggregate_sha256"],
                "file_count": document["file_count"],
                "member": manifest_member.name,
                "sha256": sha256_bytes(payload),
            },
            "filename": path.name,
            "member_count": len(members),
            "sha256": sha256_file(path),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v01-wheel", required=True, type=Path)
    parser.add_argument("--v02-wheel", required=True, type=Path)
    parser.add_argument("--v02-sdist", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--requirements-lock", required=True, type=Path)
    args = parser.parse_args()

    source_payload = args.source_manifest.read_bytes()
    source_document = json.loads(source_payload)
    result = {
        "artifacts": [
            inspect_wheel(args.v01_wheel),
            inspect_wheel(args.v02_wheel),
            inspect_sdist(args.v02_sdist),
        ],
        "requirements_lock": {
            "bytes": args.requirements_lock.stat().st_size,
            "filename": args.requirements_lock.name,
            "sha256": sha256_file(args.requirements_lock),
        },
        "schema_version": "cas.casformer.release-artifacts/0.2",
        "source_manifest": {
            "aggregate_sha256": source_document["aggregate_sha256"],
            "bytes": len(source_payload),
            "file_count": source_document["file_count"],
            "sha256": sha256_bytes(source_payload),
        },
        "status": "PASS",
    }
    expected = result["source_manifest"]
    for artifact in result["artifacts"][1:]:
        embedded = artifact["embedded_source_manifest"]
        if (
            embedded["aggregate_sha256"] != expected["aggregate_sha256"]
            or embedded["file_count"] != expected["file_count"]
            or embedded["sha256"] != expected["sha256"]
        ):
            result["status"] = "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
