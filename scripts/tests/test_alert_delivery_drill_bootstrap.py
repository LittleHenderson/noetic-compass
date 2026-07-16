from __future__ import annotations

import base64
import importlib._bootstrap_external as bootstrap_external
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import verify_pinned_root_ci_receipt as receipt_verifier  # noqa: E402


WORKFLOW_PATH = ROOT / ".github" / "workflows" / "alert-delivery-drill.yml"
SECURITY_CRITICAL_PATHS = (
    ".github/workflows/alert-delivery-drill.yml",
    ".production/customer-production-trusted-issuers.json",
    "scripts/assemble_customer_production_acceptance_candidate.py",
    "scripts/build_alert_delivery_gate_payload.py",
    "scripts/deliver_alert_delivery_drill.py",
    "scripts/deliver_production_runtime_alert.py",
    "scripts/verify_customer_production_acceptance.py",
    "scripts/verify_pinned_root_ci_receipt.py",
)
BOOTSTRAP_STEP = "Bootstrap immutable exact-head verification environment"
PRE_DELIVERY_STEP = (
    "Recreate immutable exact-head environment immediately before delivery"
)
DELIVERY_STEP = "Deliver the distinct non-disruptive P1 drill"
PROVIDER_VARIABLES = tuple(
    f"CAS_ALERT_DRILL_{role}_WEBHOOK_{kind}"
    for role in ("INCIDENT", "PRIMARY", "ACK", "SECONDARY")
    for kind in ("URL", "TOKEN")
)
TEST_TEMP_ROOT = None


def _git(
    repo_root: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=check,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _git_bytes(repo_root: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        timeout=60,
    ).stdout


def _bash() -> str:
    if os.name == "nt":
        candidates = (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Git"
            / "bin"
            / "bash.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Git"
            / "usr"
            / "bin"
            / "bash.exe",
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    executable = shutil.which("bash")
    if executable is None:
        raise AssertionError("bash is required to test the workflow bootstrap")
    return executable


def _workflow_run_block(step_name: str) -> str:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    marker = f"      - name: {step_name}\n"
    if workflow.count(marker) != 1:
        raise AssertionError(f"workflow step is not unique: {step_name}")
    section = workflow.split(marker, maxsplit=1)[1]
    run_marker = "        run: |\n"
    if section.count(run_marker) < 1:
        raise AssertionError(f"workflow step has no literal run block: {step_name}")
    body = section.split(run_marker, maxsplit=1)[1].split(
        "\n      - name:", maxsplit=1
    )[0]
    return textwrap.dedent(body)


def _materialize_current_source(
    parent: Path, *, exact_verifier_stub: bool = False
) -> tuple[Path, str]:
    source = parent / "source"
    source.mkdir()
    _git(source, "init", "--quiet")
    _git(source, "config", "user.name", "CAS Bootstrap Test")
    _git(
        source,
        "config",
        "user.email",
        "cas-bootstrap-test@example.invalid",
    )
    _git(source, "config", "core.autocrlf", "false")
    for repository_path in (".gitignore", *SECURITY_CRITICAL_PATHS):
        source_path = ROOT / repository_path
        target = source / repository_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
    if exact_verifier_stub:
        (source / "scripts" / "verify_pinned_root_ci_receipt.py").write_text(
            "raise SystemExit(0)\n",
            encoding="utf-8",
            newline="\n",
        )
    _git(source, "add", "--all")
    _git(source, "commit", "-m", "materialize bootstrap under test")
    head = _git(source, "rev-parse", "HEAD").stdout.strip()
    if _git(source, "status", "--porcelain=v1").stdout:
        raise AssertionError("materialized bootstrap source is not clean")
    return source, head


def _dummy_receipt_environment(
    parent: Path, *, head: str, exact_worktree: Path
) -> dict[str, str]:
    receipt_root = parent / "receipt-input" / "receipts"
    receipt_root.mkdir(parents=True, exist_ok=True)
    receipt = receipt_root / "root-ci-protected-deploy.json"
    checksum = receipt_root / "root-ci-protected-deploy.sha256"
    digest = "0" * 64
    receipt.write_text("{}\n", encoding="utf-8", newline="\n")
    checksum.write_text(
        f"{digest}  customer-production-evidence/receipts/"
        "root-ci-protected-deploy.json\n",
        encoding="ascii",
        newline="\n",
    )
    xdg_config = parent / "xdg"
    xdg_config.mkdir(exist_ok=True)
    return {
        "EXPECTED_MASTER_HEAD": head,
        "EXPECTED_DEPLOY_ID": "dep-" + ("a" * 20),
        "ROOT_CI_RECEIPT_SHA256": digest,
        "ROOT_CI_RECEIPT_PATH": receipt.as_posix(),
        "ROOT_CI_CHECKSUM_PATH": checksum.as_posix(),
        "EXACT_HEAD_WORKTREE": exact_worktree.as_posix(),
        "RUNNER_TEMP": parent.as_posix(),
        "XDG_CONFIG_HOME": xdg_config.as_posix(),
    }


def _run_workflow_block(
    block: str,
    *,
    cwd: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(environment)
    return subprocess.run(
        [_bash(), "--noprofile", "--norc", "-c", block],
        cwd=cwd,
        env=merged,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
    )


def _install_hostile_timestamp_pyc(source: Path, marker: Path) -> Path:
    stat = source.stat()
    hostile = compile(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
        str(source),
        "exec",
    )
    pyc = bootstrap_external._code_to_timestamp_pyc(
        hostile,
        int(stat.st_mtime),
        stat.st_size,
    )
    cache_path = Path(importlib.util.cache_from_source(str(source)))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(pyc)
    return cache_path


def _repository_git_path(repo_root: Path, *arguments: str) -> Path:
    path = Path(_git(repo_root, *arguments).stdout.strip())
    if not path.is_absolute():
        path = repo_root / path
    return path


def _write_filter_program(path: Path, payload: bytes) -> None:
    encoded = base64.b64encode(payload).decode("ascii")
    path.write_text(
        "import base64, sys\n"
        "sys.stdin.buffer.read()\n"
        f"sys.stdout.buffer.write(base64.b64decode({encoded!r}))\n",
        encoding="utf-8",
        newline="\n",
    )


def _python_filter_command(path: Path) -> str:
    return f'"{Path(sys.executable).as_posix()}" "{path.as_posix()}"'


class AlertDeliveryDrillBootstrapTests(unittest.TestCase):
    def test_bootstrap_critical_paths_match_the_verifier_contract(self) -> None:
        self.assertEqual(
            SECURITY_CRITICAL_PATHS,
            receipt_verifier.SECURITY_CRITICAL_REPOSITORY_PATHS,
        )
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        for repository_path in SECURITY_CRITICAL_PATHS:
            self.assertEqual(workflow.count(f"'{repository_path}'"), 2)

    def test_dirty_verifier_system_exit_cannot_satisfy_actual_bootstrap(self) -> None:
        block = _workflow_run_block(BOOTSTRAP_STEP)
        with tempfile.TemporaryDirectory(dir=TEST_TEMP_ROOT) as directory:
            parent = Path(directory)
            source, head = _materialize_current_source(parent)
            (source / "scripts" / "verify_pinned_root_ci_receipt.py").write_text(
                "raise SystemExit(0)\n",
                encoding="utf-8",
                newline="\n",
            )
            exact_worktree = parent / "v"
            environment = _dummy_receipt_environment(
                parent,
                head=head,
                exact_worktree=exact_worktree,
            )
            result = _run_workflow_block(
                block,
                cwd=source,
                environment=environment,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(exact_worktree.exists())

    def test_replacement_ref_cannot_substitute_hostile_verifier_before_python(self) -> None:
        for step_name in (BOOTSTRAP_STEP, PRE_DELIVERY_STEP):
            with self.subTest(step_name=step_name):
                block = _workflow_run_block(step_name)
                with tempfile.TemporaryDirectory(dir=TEST_TEMP_ROOT) as directory:
                    parent = Path(directory)
                    source, head = _materialize_current_source(parent)
                    marker = parent / "hostile-replacement-verifier-executed"
                    verifier_path = (
                        source / "scripts" / "verify_pinned_root_ci_receipt.py"
                    )
                    verifier_path.write_text(
                        "from pathlib import Path\n"
                        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
                        "raise SystemExit(0)\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    _git(
                        source,
                        "add",
                        "--",
                        verifier_path.relative_to(source).as_posix(),
                    )
                    _git(source, "commit", "-m", "hostile replacement commit")
                    hostile_head = _git(source, "rev-parse", "HEAD").stdout.strip()
                    _git(source, "switch", "--detach", head)
                    _git(
                        source,
                        "update-ref",
                        f"refs/replace/{head}",
                        hostile_head,
                    )
                    self.assertEqual(
                        _git(
                            source,
                            "for-each-ref",
                            "--format=%(refname)",
                            "refs/replace",
                        ).stdout.strip(),
                        f"refs/replace/{head}",
                    )

                    exact_worktree = parent / "replacement-exact-head"
                    environment = _dummy_receipt_environment(
                        parent,
                        head=head,
                        exact_worktree=exact_worktree,
                    )
                    result = _run_workflow_block(
                        block,
                        cwd=source,
                        environment=environment,
                    )
                    self.assertNotEqual(
                        result.returncode,
                        0,
                        result.stdout + result.stderr,
                    )
                    self.assertFalse(
                        exact_worktree.exists(), result.stdout + result.stderr
                    )
                    self.assertFalse(marker.exists(), result.stdout + result.stderr)

    def test_clean_smudge_filter_cannot_hide_hostile_verifier_bytes(self) -> None:
        for step_name in (BOOTSTRAP_STEP, PRE_DELIVERY_STEP):
            with self.subTest(step_name=step_name):
                block = _workflow_run_block(step_name)
                with tempfile.TemporaryDirectory(dir=TEST_TEMP_ROOT) as directory:
                    parent = Path(directory)
                    source, head = _materialize_current_source(parent)
                    marker = parent / "hostile-filter-verifier-executed"
                    repository_path = "scripts/verify_pinned_root_ci_receipt.py"
                    safe_bytes = _git_bytes(
                        source,
                        "cat-file",
                        "blob",
                        f"{head}:{repository_path}",
                    )
                    hostile_bytes = (
                        "from pathlib import Path\n"
                        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
                        "raise SystemExit(0)\n"
                    ).encode("utf-8")
                    clean_filter = parent / "clean-filter.py"
                    smudge_filter = parent / "smudge-filter.py"
                    _write_filter_program(clean_filter, safe_bytes)
                    _write_filter_program(smudge_filter, hostile_bytes)
                    _git(
                        source,
                        "config",
                        "filter.hostile.clean",
                        _python_filter_command(clean_filter),
                    )
                    _git(
                        source,
                        "config",
                        "filter.hostile.smudge",
                        _python_filter_command(smudge_filter),
                    )
                    _git(source, "config", "filter.hostile.required", "true")
                    attributes = _repository_git_path(
                        source, "rev-parse", "--git-path", "info/attributes"
                    )
                    attributes.parent.mkdir(parents=True, exist_ok=True)
                    attributes.write_text(
                        f"/{repository_path} filter=hostile\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    self.assertEqual(
                        _git(source, "status", "--porcelain=v1").stdout,
                        "",
                    )

                    exact_worktree = parent / "filter-exact-head"
                    environment = _dummy_receipt_environment(
                        parent,
                        head=head,
                        exact_worktree=exact_worktree,
                    )
                    result = _run_workflow_block(
                        block,
                        cwd=source,
                        environment=environment,
                    )
                    self.assertNotEqual(
                        result.returncode,
                        0,
                        result.stdout + result.stderr,
                    )
                    self.assertTrue(
                        exact_worktree.is_dir(), result.stdout + result.stderr
                    )
                    self.assertEqual(
                        (exact_worktree / repository_path).read_bytes(), hostile_bytes
                    )
                    expected_blob = _git(
                        exact_worktree,
                        "rev-parse",
                        f"{head}:{repository_path}",
                    ).stdout.strip()
                    filtered_blob = _git(
                        exact_worktree,
                        "hash-object",
                        f"--path={repository_path}",
                        repository_path,
                    ).stdout.strip()
                    actual_blob = _git(
                        exact_worktree,
                        "hash-object",
                        "--no-filters",
                        "--",
                        repository_path,
                    ).stdout.strip()
                    self.assertEqual(filtered_blob, expected_blob)
                    self.assertNotEqual(actual_blob, expected_blob)
                    self.assertFalse(marker.exists(), result.stdout + result.stderr)

    def test_git_environment_and_checkout_hooks_are_disabled(self) -> None:
        block = _workflow_run_block(PRE_DELIVERY_STEP)
        with tempfile.TemporaryDirectory(dir=TEST_TEMP_ROOT) as directory:
            parent = Path(directory)
            source, head = _materialize_current_source(
                parent,
                exact_verifier_stub=True,
            )
            marker = parent / "hostile-post-checkout-hook-executed"
            hook_root = parent / "hostile-hooks"
            hook_root.mkdir()
            hook = hook_root / "post-checkout"
            hook.write_text(
                "#!/bin/sh\n"
                f"printf executed > '{marker.as_posix()}'\n",
                encoding="utf-8",
                newline="\n",
            )
            hook.chmod(0o755)
            exact_worktree = parent / "sanitized-exact-head"
            environment = _dummy_receipt_environment(
                parent,
                head=head,
                exact_worktree=exact_worktree,
            ) | {
                "GIT_DIR": (parent / "bogus-git-dir").as_posix(),
                "GIT_WORK_TREE": (parent / "bogus-work-tree").as_posix(),
                "GIT_INDEX_FILE": (parent / "bogus-index").as_posix(),
                "GIT_OBJECT_DIRECTORY": (parent / "bogus-objects").as_posix(),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": (
                    parent / "bogus-alternates"
                ).as_posix(),
                "GIT_COMMON_DIR": (parent / "bogus-common-dir").as_posix(),
                "GIT_REPLACE_REF_BASE": "refs/hostile-replacements/",
                "GIT_NAMESPACE": "hostile-namespace",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": hook_root.as_posix(),
            }
            result = _run_workflow_block(
                block,
                cwd=source,
                environment=environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(exact_worktree.is_dir(), result.stdout + result.stderr)
            self.assertFalse(marker.exists(), result.stdout + result.stderr)

    def test_ignored_timestamp_valid_assembler_pyc_cannot_execute(self) -> None:
        block = _workflow_run_block(BOOTSTRAP_STEP)
        with tempfile.TemporaryDirectory(dir=TEST_TEMP_ROOT) as directory:
            parent = Path(directory)
            source, head = _materialize_current_source(parent)
            marker = parent / "hostile-assembler-executed"
            assembler = (
                source
                / "scripts"
                / "assemble_customer_production_acceptance_candidate.py"
            )
            cache_path = _install_hostile_timestamp_pyc(assembler, marker)
            relative_cache = cache_path.relative_to(source).as_posix()
            self.assertEqual(
                _git(source, "check-ignore", relative_cache, check=False).returncode,
                0,
            )
            self.assertEqual(_git(source, "status", "--porcelain=v1").stdout, "")

            vulnerable = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(source / "scripts" / "verify_pinned_root_ci_receipt.py"),
                    "--help",
                ],
                cwd=source,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertTrue(marker.is_file(), vulnerable.stdout + vulnerable.stderr)
            marker.unlink()

            exact_worktree = parent / "v"
            environment = _dummy_receipt_environment(
                parent,
                head=head,
                exact_worktree=exact_worktree,
            )
            result = _run_workflow_block(
                block,
                cwd=source,
                environment=environment,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(
                exact_worktree.is_dir(), result.stdout + result.stderr
            )
            self.assertFalse(marker.exists(), result.stdout + result.stderr)
            self.assertIn("root-CI receipt verification failed", result.stderr)

    def test_ignored_hardened_delivery_pyc_cannot_execute(self) -> None:
        pre_delivery = _workflow_run_block(PRE_DELIVERY_STEP)
        delivery = _workflow_run_block(DELIVERY_STEP)
        with tempfile.TemporaryDirectory(dir=TEST_TEMP_ROOT) as directory:
            parent = Path(directory)
            source, head = _materialize_current_source(
                parent,
                exact_verifier_stub=True,
            )
            marker = parent / "hostile-delivery-dependency-executed"
            hardened = source / "scripts" / "deliver_production_runtime_alert.py"
            cache_path = _install_hostile_timestamp_pyc(hardened, marker)
            relative_cache = cache_path.relative_to(source).as_posix()
            self.assertEqual(
                _git(source, "check-ignore", relative_cache, check=False).returncode,
                0,
            )

            vulnerable = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(source / "scripts" / "deliver_alert_delivery_drill.py"),
                    "--help",
                ],
                cwd=source,
                # Keep the vulnerable control bound to the materialized source even
                # when the parent test runner exports its own repository on PYTHONPATH.
                env=os.environ | {"PYTHONPATH": str(source)},
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertTrue(marker.is_file(), vulnerable.stdout + vulnerable.stderr)
            marker.unlink()

            exact_worktree = parent / "d"
            environment = _dummy_receipt_environment(
                parent,
                head=head,
                exact_worktree=exact_worktree,
            )
            preflight = _run_workflow_block(
                pre_delivery,
                cwd=source,
                environment=environment,
            )
            self.assertEqual(
                preflight.returncode,
                0,
                preflight.stdout + preflight.stderr,
            )
            self.assertTrue(
                exact_worktree.is_dir(), preflight.stdout + preflight.stderr
            )
            self.assertFalse(marker.exists())

            delivery_environment = environment | {
                "CAS_ALERT_DRILL_PROVIDER_MODE": "disabled",
                "GITHUB_REPOSITORY": "LittleHenderson/noetic-compass",
                "GITHUB_RUN_ID": "123456",
                "GITHUB_RUN_ATTEMPT": "1",
            }
            delivery_environment.update({name: "" for name in PROVIDER_VARIABLES})
            delivered = _run_workflow_block(
                delivery,
                cwd=source,
                environment=delivery_environment,
            )
            self.assertNotEqual(
                delivered.returncode,
                0,
                delivered.stdout + delivered.stderr,
            )
            self.assertFalse(marker.exists(), delivered.stdout + delivered.stderr)
            self.assertIn(
                "Alert-delivery drill outcome: provider_disabled",
                delivered.stdout + delivered.stderr,
                repr((delivered.returncode, delivered.stdout, delivered.stderr)),
            )


if __name__ == "__main__":
    unittest.main()
