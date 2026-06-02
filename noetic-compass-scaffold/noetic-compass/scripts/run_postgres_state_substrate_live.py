"""Run the live Postgres StateStore tests against a throwaway *embedded* Postgres.

This is the no-Docker / no-admin local counterpart to the
``.github/workflows/postgres-state-substrate.yml`` CI job. It downloads a
self-contained EnterpriseDB PostgreSQL **binaries** zip (no installer, no admin
rights, no service registration), runs ``initdb`` into a temp dir, starts the
server on a throwaway port, points ``NC_TEST_POSTGRES_URL`` at a throwaway database,
runs ``tests/test_state_substrate_postgres.py``, and tears the server down again.

This is exactly the path that was used on 2026-06-02 to turn the Postgres backend's
contract-conformance claim from *declared* into *verified* (10/10 tests observed
passing, 3 consecutive runs, against PostgreSQL 16.4) on a Windows box with no Docker
and no admin rights.

Usage (from the repo's ``noetic-compass`` dir, with psycopg already installed)::

    python scripts/run_postgres_state_substrate_live.py

Honesty: this proves *single-instance* durability (survives the server's own
close/reopen) and fence-MINT monotonicity against a real server. It does NOT prove
survival of *host loss* -- that needs synchronous replication + failover and is out
of scope for a single embedded instance (see ``postgres_store.py`` honesty boundary).

If you already have a Postgres reachable, you do not need this script at all -- just
set ``NC_TEST_POSTGRES_URL`` and run pytest directly::

    set NC_TEST_POSTGRES_URL=postgresql://user:pw@host:5432/dbname
    python -m pytest tests/test_state_substrate_postgres.py -v
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

# A self-contained binaries zip (no installer). Override with --binaries-url to pin a
# different version / platform. The default targets Windows x64; on Linux/macOS pass a
# matching EDB binaries URL or just use a system/Docker Postgres + NC_TEST_POSTGRES_URL.
DEFAULT_BINARIES_URL = (
    "https://get.enterprisedb.com/postgresql/"
    "postgresql-16.4-1-windows-x64-binaries.zip"
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _download(url: str, dest: Path) -> None:
    print(f"[live] downloading {url}")
    t = time.time()
    urllib.request.urlretrieve(url, dest)
    print(f"[live] downloaded {dest.stat().st_size} bytes in {time.time() - t:.1f}s")


def _extract(zip_path: Path, into: Path) -> Path:
    print(f"[live] extracting {zip_path.name}")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(into)
    bindir = into / "pgsql" / "bin"
    if not bindir.is_dir():
        raise SystemExit(f"[live] expected {bindir} after extract; archive layout changed")
    return bindir


def _wait_ready(bindir: Path, datadir: Path, timeout_s: float = 30.0) -> None:
    pg_ctl = bindir / ("pg_ctl.exe" if os.name == "nt" else "pg_ctl")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = subprocess.run(
            [str(pg_ctl), "-D", str(datadir), "status"],
            capture_output=True,
            text=True,
        )
        if "server is running" in (r.stdout or ""):
            return
        time.sleep(0.5)
    raise SystemExit("[live] server did not report ready in time")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binaries-url", default=DEFAULT_BINARIES_URL)
    ap.add_argument(
        "--bindir",
        default=None,
        help=(
            "path to an already-extracted PostgreSQL 'bin' dir (containing "
            "initdb/pg_ctl/createdb). When given, download + extract are SKIPPED -- "
            "useful for repeat runs and CI binary caching."
        ),
    )
    ap.add_argument(
        "--keep",
        action="store_true",
        help="keep the temp server dir + leave the server running for manual poking",
    )
    ap.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="extra args passed through to pytest (e.g. -v -k contract)",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]  # noetic-compass dir
    testfile = repo_root / "tests" / "test_state_substrate_postgres.py"
    if not testfile.is_file():
        raise SystemExit(f"[live] cannot find {testfile}; run from the noetic-compass dir")

    # Driver must be importable -- fail loudly and early, not mid-run.
    try:
        import psycopg  # noqa: F401
    except ModuleNotFoundError:
        raise SystemExit(
            "[live] psycopg is not installed; run: "
            'python -m pip install "psycopg[binary]"'
        )

    work = Path(tempfile.mkdtemp(prefix="nc_pg_live_"))
    datadir = work / "pgdata"
    port = _free_port()
    bindir = None
    started = False
    pg_ctl = None

    try:
        if args.bindir:
            bindir = Path(args.bindir)
            if not bindir.is_dir():
                raise SystemExit(f"[live] --bindir {bindir} is not a directory")
            print(f"[live] reusing pre-extracted binaries at {bindir}")
        else:
            zip_path = work / "pg-binaries.zip"
            _download(args.binaries_url, zip_path)
            bindir = _extract(zip_path, work)

        exe = ".exe" if os.name == "nt" else ""
        initdb = bindir / f"initdb{exe}"
        pg_ctl = bindir / f"pg_ctl{exe}"
        createdb = bindir / f"createdb{exe}"

        print("[live] initdb (trust auth, throwaway cluster)")
        subprocess.run(
            [str(initdb), "-D", str(datadir), "-U", "postgres", "-A", "trust",
             "--encoding=UTF8"],
            check=True,
            capture_output=True,
            text=True,
        )

        print(f"[live] starting server on 127.0.0.1:{port}")
        logfile = work / "pg.log"
        # IMPORTANT (Windows deadlock): do NOT capture pg_ctl's stdout/stderr with
        # pipes here. ``pg_ctl ... start`` forks a long-lived ``postgres`` daemon that
        # INHERITS any pipe handles the parent opened; the parent's pipe read then
        # never sees EOF (the daemon holds the write end for its whole lifetime) and
        # ``subprocess.run`` hangs forever. The server's own diagnostics already go to
        # ``-l logfile``, so we send the launcher's streams to DEVNULL -- nothing to
        # inherit, nothing to deadlock on.
        with open(os.devnull, "wb") as devnull:
            subprocess.run(
                [str(pg_ctl), "-D", str(datadir),
                 "-o", f"-p {port} -c listen_addresses=127.0.0.1",
                 "-l", str(logfile), "-w", "start"],
                check=True,
                stdout=devnull,
                stderr=devnull,
            )
        started = True
        _wait_ready(bindir, datadir)

        dbname = "nc_harness_test"
        subprocess.run(
            [str(createdb), "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", dbname],
            check=True,
            capture_output=True,
            text=True,
        )

        dsn = f"postgresql://postgres@127.0.0.1:{port}/{dbname}"
        print(f"[live] NC_TEST_POSTGRES_URL={dsn}")

        env = dict(os.environ)
        env["NC_TEST_POSTGRES_URL"] = dsn
        pytest_args = args.pytest_args or ["-v"]
        # argparse.REMAINDER may capture a leading "--"; drop it.
        if pytest_args and pytest_args[0] == "--":
            pytest_args = pytest_args[1:]
        cmd = [sys.executable, "-m", "pytest", str(testfile), *pytest_args]
        print(f"[live] running: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, cwd=str(repo_root))
        return result.returncode

    finally:
        if started and pg_ctl is not None and not args.keep:
            print("[live] stopping server")
            subprocess.run(
                [str(pg_ctl), "-D", str(datadir), "-m", "immediate", "stop"],
                capture_output=True,
                text=True,
            )
        if args.keep:
            print(f"[live] --keep set; server dir left at {work}")
        else:
            # Best-effort cleanup; on Windows a just-stopped server can briefly hold
            # file handles, so ignore residual-file errors.
            import shutil

            shutil.rmtree(work, ignore_errors=True)
            print(f"[live] cleaned up {work}")


if __name__ == "__main__":
    raise SystemExit(main())
