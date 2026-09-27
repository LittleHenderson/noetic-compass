"""Run the frozen public CPU engineering acceptance once, then retain evidence."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LANE = ROOT / "research/cas_closed_loop_1"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    out = ROOT / "aws-output"
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    record = {"schema": "cas.cpu.aws.worker/1", "start_utc": utc(), "status": "RUNNING",
              "commands": [], "paid_job": True, "model_invocations": 0}
    def save():
        (out / "worker.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    def command(name, argv, limit=450, allow_failure=False):
        remaining = min(limit, int(900 - (time.monotonic() - started)))
        if remaining <= 0:
            raise TimeoutError("WORKER_WALL_LIMIT")
        row = {"name": name, "argv": argv, "start_utc": utc()}
        record["commands"].append(row)
        save()
        with (out / (name + ".stdout")).open("wb") as stdout, (out / (name + ".stderr")).open("wb") as stderr:
            process = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr,
                                       env=os.environ.copy(), start_new_session=True)
            try:
                row["returncode"] = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
                row["returncode"] = process.wait()
                row["timeout"] = True
                raise
            finally:
                row["end_utc"] = utc()
                save()
        if row["returncode"] != 0 and not allow_failure:
            raise RuntimeError("COMMAND_FAILED:" + name)
    try:
        if sys.version_info[:2] != (3, 12):
            raise RuntimeError("PYTHON_312_REQUIRED")
        manifest = json.loads((ROOT / "payload_manifest.json").read_text())
        if manifest["schema"] != "cas.cpu.payload/2":
            raise ValueError("SUPERSEDED_LANE_A_PAYLOAD")
        for row in manifest["files"]:
            path = ROOT / row["path"]
            if not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError("UNSAFE_PACKAGE_PATH")
            raw = path.read_bytes()
            if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("PACKAGE_FILE_CHANGED:" + row["path"])
        record["manifest"] = manifest
        record["environment"] = {"python": sys.version, "platform": platform.platform()}
        pip = next((ROOT / "wheelhouse").glob("pip-*.whl"))
        deps = ROOT / "deps"
        os.environ["PYTHONPATH"] = str(pip)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        os.environ["GIT_NO_LAZY_FETCH"] = "1"
        os.environ["GIT_NO_REPLACE_OBJECTS"] = "1"
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
        os.environ["GIT_CONFIG_GLOBAL"] = "/dev/null"
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
            os.environ.pop(name, None)
        command("offline_install", [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                "--require-hashes", "--find-links", str(ROOT / "wheelhouse"), "--target", str(deps),
                "-r", str(ROOT / "requirements.lock")], limit=180)
        os.environ["PYTHONPATH"] = str(deps)
        sys.path.insert(0, str(deps))
        command("environment", [sys.executable, "-m", "pip", "freeze", "--path", str(deps)], limit=30)
        command("git_package_before", ["dpkg-query", "-W", "-f=${Version}", "git"], limit=30, allow_failure=True)
        before = (out / "git_package_before.stdout").read_text().strip()
        if before != manifest["git_version"]:
            sources = ROOT / "git-bootstrap.sources"
            sources.write_text("Types: deb\nURIs: https://archive.ubuntu.com/ubuntu\nSuites: noble noble-updates\nComponents: main\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\n"
                               "Types: deb\nURIs: https://security.ubuntu.com/ubuntu\nSuites: noble-security\nComponents: main\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n")
            os.environ["DEBIAN_FRONTEND"] = "noninteractive"
            apt = ["apt-get", "-o", "Acquire::Retries=0", "-o", "Acquire::https::Timeout=20",
                   "-o", "Dir::Etc::sourcelist=" + str(sources), "-o", "Dir::Etc::sourceparts=-"]
            command("git_dependency_index", apt + ["update"], limit=120)
            packages = [str(ROOT / "system-packages" / row["filename"]) for row in manifest["git_packages"]]
            command("git_pinned_install", apt + ["install", "-y", "--no-install-recommends", *packages], limit=120)
        command("git_package_after", ["dpkg-query", "-W", "-f=${Version}", "git"], limit=30)
        if (out / "git_package_after.stdout").read_text().strip() != manifest["git_version"]:
            raise ValueError("PINNED_GIT_PACKAGE_REQUIRED")
        command("os_package_inventory", ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"], limit=30)
        command("git_version", ["git", "--version"], limit=30)
        command("git_longpaths", ["git", "config", "core.longpaths", "true"], limit=30)
        command("runtime_commit_exists", ["git", "cat-file", "-e", "8182ad52b4468f18f140837dffee0e7debcfe786"], limit=30)
        command("committed_artifact_check", [sys.executable, str(LANE / "check_artifacts.py"),
                "--git-ref", manifest["source_commit"]], limit=60)
        command("instance_runtime_bootstrap", [sys.executable, str(LANE / "bootstrap_runtime.py")], limit=90)
        record["instance_git_preflight"] = {"status": "PASS", "source_commit": manifest["source_commit"],
                "runtime_commit": manifest["runtime_commit"], "git_package_version": manifest["git_version"],
                "object_store": "EXPLICITLY_PARTIAL_PUBLIC_OBJECT_STORE"}
        command("source_check", [sys.executable, str(LANE / "run_closed_loop.py"), "check"], limit=60)
        command("artifact_check", [sys.executable, str(LANE / "check_artifacts.py")], limit=60)
        command("focused_tests", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--junitxml=" + str(out / "pytest.xml"),
                str(LANE / "test_native_step_adapter.py"), str(LANE / "test_closed_loop.py"),
                str(LANE / "test_artifacts.py"),
                str(LANE / "aws_validation/test_launch_transport.py")], allow_failure=True)
        root = ET.parse(out / "pytest.xml").getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
        record["tests"] = totals
        if totals != {"tests": manifest["expected_tests"], "failures": 0, "errors": 0, "skipped": 0}:
            raise ValueError("PREDECLARED_TEST_COUNTS_REQUIRED_WITHOUT_SKIPS")
        command("retained_replay", [sys.executable, str(LANE / "run_closed_loop.py"), "replay",
                "--directory", str(LANE / "evidence"), "--expected-bundle-digest",
                "eae7eb1bedb67af537187d409c89fca9e55a1580d52bf14be9b01e560a198d2c"], limit=90)
        witness = out / "witness"
        command("witness", [sys.executable, str(LANE / "run_closed_loop.py"), "demo",
                "--output", str(witness)], limit=120)
        result = json.loads((out / "witness.stdout").read_text())
        retained = result["bundle_digest"]
        (out / "caller_retained_digest.txt").write_text(retained + "\n")
        command("fresh_process_replay", [sys.executable, str(LANE / "run_closed_loop.py"), "replay",
                "--directory", str(witness), "--expected-bundle-digest", retained], limit=90)
        replay = json.loads((out / "fresh_process_replay.stdout").read_text())
        if (result["output"] != "3" or result["host_entries"] != 12 or result["native_events"] != 18
                or replay["status"] != "EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT"):
            raise ValueError("ENGINEERING_WITNESS_EXPECTATIONS_DIFFER")
        record["witness"] = result
        record["fresh_process_replay"] = replay
        record["negative_controls"] = "PASS_IN_FOCUSED_SUITE"
        record["status"] = "PASS_ENGINEERING_VALIDATION_ONLY"
    except BaseException as exc:
        record["status"] = "FAILED"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
        (out / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        record["end_utc"] = utc()
        record["seconds"] = time.monotonic() - started
        # Detailed cloud-init configuration logs can contain encoded user-data;
        # retain command output only. Host console collection redacts its tokens.
        for name in ("/var/log/cloud-init-output.log",):
            if Path(name).is_file():
                shutil.copyfile(name, out / Path(name).name)
        save()
        archive = ROOT / "outputs.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            stream.add(out, arcname="outputs")
        raw = archive.read_bytes()
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError("OUTPUT_ARCHIVE_LIMIT")
        terminal = {"status": record["status"], "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw), "start_utc": record["start_utc"], "end_utc": record["end_utc"]}
        # Upload evidence first. A terminal receipt never claims absent evidence.
        import boto3
        from botocore.config import Config
        client = boto3.client("s3", region_name=args.region,
                             config=Config(retries={"total_max_attempts": 1},
                                           connect_timeout=5, read_timeout=30))
        client.put_object(Bucket=args.bucket, Key="outputs/outputs.tar.gz", Body=raw)
        client.put_object(Bucket=args.bucket, Key="outputs/terminal.json", Body=json.dumps(terminal).encode())
    return 0 if record["status"] == "PASS_ENGINEERING_VALIDATION_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
