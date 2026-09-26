"""AWS-only bounded public tests and exact-source package build."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = json.loads((ROOT / "payload_manifest.json").read_bytes())["source_commit"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main(bucket, region):
    started = time.monotonic()
    out = ROOT / "aws-output"
    out.mkdir(exist_ok=False)
    repo = ROOT / "repo"
    record = {"schema": "helm.validation.terminal-test-receipt/1", "status": "FAILED",
              "source_commit": SOURCE, "commands": [], "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "expected_tests": 69, "scope": "Public source regressions and exact-commit package build; no CUDA/model/training acceptance."}

    def command(name, argv, *, cwd=ROOT, input=None, limit=180, allow_failure=False):
        row = {"name": name, "argv": argv, "cwd": str(cwd)}
        record["commands"].append(row)
        wall = min(limit, 900 - (time.monotonic() - started))
        if wall <= 0:
            raise TimeoutError("VALIDATION_WORKER_DEADLINE")
        at = time.monotonic()
        with (out / (name + ".stdout")).open("wb") as stdout, (out / (name + ".stderr")).open("wb") as stderr:
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, env=os.environ)
            try:
                process.communicate(input=input, timeout=wall)
                row["returncode"] = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                row["timeout"] = True
                raise TimeoutError("VALIDATION_COMMAND_DEADLINE:" + name)
        row["elapsed_seconds"] = time.monotonic() - at
        for suffix in ("stdout", "stderr"):
            raw = (out / (name + "." + suffix)).read_bytes()
            row[suffix] = {"sha256": sha(raw), "bytes": len(raw), "file": name + "." + suffix}
        if row["returncode"] and not allow_failure:
            raise RuntimeError("COMMAND_FAILED:" + name)
        return row["returncode"]

    try:
        raw = (ROOT / "payload_manifest.json").read_bytes()
        manifest = json.loads(raw)
        if manifest["schema"] != "helm.validation.payload/1" or manifest["source_commit"] != SOURCE or manifest["expected_tests"] != 69:
            raise ValueError("EXACT_HELM_VALIDATION_MANIFEST")
        record["payload_manifest_sha256"] = sha(raw)
        record["test_checkout_boundary"] = manifest["test_checkout_boundary"]
        for row in manifest["files"]:
            path = ROOT / row["path"]
            if not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError("UNSAFE_PACKAGE_PATH")
            raw = path.read_bytes()
            if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
                raise ValueError("PAYLOAD_FILE_CHANGED:" + row["path"])
        record["environment"] = {"python": sys.version}
        pip = next((ROOT / "wheelhouse").glob("pip-*.whl"))
        deps = ROOT / "deps"
        os.environ.update({"PYTHONPATH": str(pip), "PYTHONDONTWRITEBYTECODE": "1",
                           "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                           "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1",
                           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
            os.environ.pop(name, None)
        command("offline_install", [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                "--require-hashes", "--find-links", str(ROOT / "wheelhouse"), "--target", str(deps),
                "-r", str(ROOT / "requirements.lock")], limit=180)
        os.environ["PYTHONPATH"] = str(deps)
        sys.path.insert(0, str(deps))
        command("environment", [sys.executable, "-m", "pip", "freeze", "--path", str(deps)], limit=30)
        dpkg_version = "-f=" + "$" + "{Version}"
        command("git_package_before", ["dpkg-query", "-W", dpkg_version, "git"], limit=30, allow_failure=True)
        if (out / "git_package_before.stdout").read_text().strip() != manifest["git_version"]:
            sources = ROOT / "git-bootstrap.sources"
            sources.write_text("Types: deb\nURIs: https://archive.ubuntu.com/ubuntu\nSuites: noble noble-updates\nComponents: main\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\nTypes: deb\nURIs: https://security.ubuntu.com/ubuntu\nSuites: noble-security\nComponents: main\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n")
            os.environ["DEBIAN_FRONTEND"] = "noninteractive"
            apt = ["apt-get", "-o", "Acquire::Retries=0", "-o", "Acquire::https::Timeout=20",
                   "-o", "Dir::Etc::sourcelist=" + str(sources), "-o", "Dir::Etc::sourceparts=-"]
            command("git_dependency_index", apt + ["update"], limit=120)
            packages = [str(ROOT / "system-packages" / row["filename"]) for row in manifest["git_packages"]]
            command("git_pinned_install", apt + ["install", "-y", "--no-install-recommends", *packages], limit=120)
        command("git_package_after", ["dpkg-query", "-W", dpkg_version, "git"], limit=30)
        if (out / "git_package_after.stdout").read_text().strip() != manifest["git_version"]:
            raise ValueError("PINNED_GIT_VERSION_REQUIRED")
        command("os_package_inventory", ["dpkg-query", "-W", "-f=" + "$" + "{Package}\t" + "$" + "{Version}\n"], limit=30)
        g = ["git", "-c", "core.longpaths=true", "-c", "core.autocrlf=false"]
        command("git_commit_exists", g + ["cat-file", "-e", SOURCE + "^{commit}"], cwd=repo, limit=30)
        command("git_index", g + ["read-tree", SOURCE], cwd=repo, limit=30)
        command("git_index_names", g + ["ls-files", "-z"], cwd=repo, limit=30)
        # Original tree/index, missing paths explicitly skipped; only selected
        # exact public blobs are materialized. No historical source altered.
        command("git_skip_unselected", g + ["update-index", "--skip-worktree", "-z", "--stdin"],
                cwd=repo, input=(out / "git_index_names.stdout").read_bytes(), limit=30)
        command("git_include_selected", g + ["update-index", "--no-skip-worktree", "-z", "--stdin"],
                cwd=repo, input=b"".join(name.encode() + b"\0" for name in manifest["allowlisted_paths"]), limit=30)
        command("git_head", g + ["rev-parse", "HEAD"], cwd=repo, limit=30)
        if (out / "git_head.stdout").read_text().strip() != SOURCE:
            raise ValueError("GIT_SOURCE_IDENTITY")
        cncm = repo / manifest["cncm_prefix"]
        command("focused_tests", [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--junitxml=" + str(out / "pytest.xml"), *manifest["test_files"]],
                cwd=cncm, limit=480, allow_failure=True)
        junit = ET.parse(out / "pytest.xml").getroot()
        suites = [junit] if junit.tag == "testsuite" else list(junit.findall("testsuite"))
        record["tests"] = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                           for key in ("tests", "failures", "errors", "skipped")}
        record["test_cases"] = [{"classname": c.attrib.get("classname"), "name": c.attrib.get("name"),
                                "seconds": c.attrib.get("time"), "status":
                                "FAIL" if c.find("failure") is not None or c.find("error") is not None
                                else "SKIP" if c.find("skipped") is not None else "PASS"}
                               for s in suites for c in s.findall("testcase")]
        # JUnit aggregate includes successful unittest subtests. Require all 69
        # collected cases plus zero failed/errored/skipped cases or subtests.
        if (len(record["test_cases"]) != 69 or
                any(record["tests"][key] for key in ("failures", "errors", "skipped")) or
                any(case["status"] != "PASS" for case in record["test_cases"])):
            raise ValueError("EXPECTED_69_CASES_PASS_WITHOUT_SKIPS")
        record["collected_test_cases"] = len(record["test_cases"])
        record["subtests"] = record["tests"]["tests"] - record["collected_test_cases"]
        if record["commands"][-1].get("returncode") != 0:
            raise ValueError("PYTEST_NONZERO")
        package = cncm / ("research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_" + SOURCE[:8])
        package.parent.mkdir(parents=True, exist_ok=True)
        command("package_build", [sys.executable, "-B",
                "research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py",
                "--package", str(package), "--source-sha", SOURCE], cwd=cncm, limit=180)
        package_receipt = json.loads((package / "receipt.json").read_bytes())
        package_raw = (package / "source.zip").read_bytes()
        if package_receipt["source_sha"] != SOURCE or sha(package_raw) != package_receipt["archive_sha256"] or len(package_raw) != package_receipt["archive_bytes"]:
            raise ValueError("EXACT_SOURCE_PACKAGE_IDENTITY")
        (out / "package").mkdir()
        for name in ("source.zip", "receipt.json"):
            shutil.copyfile(package / name, out / "package" / name)
        record["package"] = {"source_commit": SOURCE, "archive_sha256": sha(package_raw),
                             "archive_bytes": len(package_raw), "manifest_sha256": package_receipt["manifest_sha256"],
                             "member_count": package_receipt["member_count"]}
        command("rerun_admission_dry_run", [sys.executable, "-B",
                "records/typed_pointer_001/admission_cm2x_rerun_001/prepare_cm2x_rerun.py",
                "--source-sha", SOURCE, "--dry-run"], cwd=cncm, limit=180)
        record["admission_dry_run"] = "PASS"
        record["status"] = "PASS_HELM_VALIDATION_AND_PACKAGE_ONLY"
    except BaseException as exc:
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
    finally:
        record["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record["elapsed_seconds"] = time.monotonic() - started
        receipt = (json.dumps(record, indent=2) + "\n").encode()
        (out / "terminal_test_receipt.json").write_bytes(receipt)
        inventory = [{"path": p.relative_to(out).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                     for p in sorted(out.rglob("*")) if p.is_file()]
        (out / "output_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
        archive = ROOT / "outputs.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            for path in sorted(out.rglob("*")):
                if path.is_file():
                    stream.add(path, arcname=path.relative_to(out).as_posix(), recursive=False)
        raw = archive.read_bytes()
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError("OUTPUT_ARCHIVE_BOUND")
        terminal = {"status": record["status"], "sha256": sha(raw), "bytes": len(raw),
                    "source_commit": SOURCE, "test_receipt_sha256": sha(receipt),
                    "tests": record.get("tests"), "collected_test_cases": record.get("collected_test_cases"),
                    "subtests": record.get("subtests"), "admission_dry_run": record.get("admission_dry_run"), "package": record.get("package")}
        import boto3
        from botocore.config import Config
        client = boto3.client("s3", region_name=region, endpoint_url="https://s3." + region + ".amazonaws.com",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"total_max_attempts": 1},
                          connect_timeout=5, read_timeout=30))
        client.put_object(Bucket=bucket, Key="outputs/outputs.tar.gz", Body=raw)
        client.put_object(Bucket=bucket, Key="outputs/terminal.json", Body=json.dumps(terminal).encode())
        print(json.dumps(terminal), flush=True)
    return 0 if record["status"] == "PASS_HELM_VALIDATION_AND_PACKAGE_ONLY" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.bucket, args.region))
