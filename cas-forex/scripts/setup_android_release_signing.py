"""Create local Android release-signing files for CAS Forex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.mobile_apk_artifact import (
    DEFAULT_RELEASE_KEY_ALIAS,
    DEFAULT_RELEASE_KEY_DNAME,
    DEFAULT_RELEASE_KEY_VALIDITY_DAYS,
    DEFAULT_RELEASE_KEYSTORE_FILENAME,
    setup_android_release_signing,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", default=REPO_ROOT)
    parser.add_argument("--store-file", default=DEFAULT_RELEASE_KEYSTORE_FILENAME)
    parser.add_argument("--alias", default=DEFAULT_RELEASE_KEY_ALIAS)
    parser.add_argument("--dname", default=DEFAULT_RELEASE_KEY_DNAME)
    parser.add_argument("--validity-days", type=int, default=DEFAULT_RELEASE_KEY_VALIDITY_DAYS)
    parser.add_argument("--keytool", default=None, help="Optional path to keytool.")
    parser.add_argument("--force", action="store_true", help="Replace existing local signing files.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    report = setup_android_release_signing(
        workspace_root=args.workspace_root,
        store_file=args.store_file,
        key_alias=args.alias,
        dname=args.dname,
        validity_days=args.validity_days,
        force=args.force,
        keytool_path=args.keytool,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["summary"])
        print(f"status: {report['status']}")
        print(f"keystore properties: {report['keystore_properties_path']}")
        print(f"keystore file: {report['store_file_path']}")
        print(f"release build: {report['build_command']}")
    return 0 if report.get("status") in {"created", "already_exists"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
