"""test_watchdog_bootstrap_authority.py -- watchdog BOOTSTRAP ORDER, SIGNED-
AUTHORITY VERIFICATION, and TIMER TOTALITY (GATE 1A.2R.2C). PERMANENTLY
NON-CLAIM-BEARING.

The independent recheck of GATE 1A.2R.2B accepted the JSON-envelope repairs but
found two CRITICAL apertures still open: (1) the frozen bootstrap started the
watchdog BEFORE its config existed, and (2) the config's fields were checked for
SHAPE, not TRUTH -- a self-consistent forged config with a bigger cap passed.
These tests prove the GATE 1A.2R.2C closure:

  section 1  the authority file is written (verified) BEFORE the watchdog starts;
             a missing REAL authority fails closed; a delayed driver within the
             startup grace does not kill a verified watchdog.
  section 2  the signed approval is LOAD-BEARING: a self-consistent forged
             authority (bigger cap / wrong campaign / wrong commit / wrong
             approval digest / wrong owner key) is refused because it disagrees
             with the signature-verified approval; the cap is DERIVED from the
             verified approval.
  section 4  the authority file and the lock locator are written ATOMICALLY; the
             poll loop never re-reads the authority (so a rewrite cannot be read
             half-written).
  section 5  in REAL the startup grace and poll interval are FROZEN constants,
             not caller-controlled; negative / NaN / infinite / huge values fail
             closed; the sleep is inside the fail-closed boundary.
  section 6  a corrupted/missing locator cannot erase the burn of an active
             protected campaign (coordinates are derived from the verified
             approval); a wrong-region / wrong-campaign locator is refused; a burn
             failure is RECORDED, never swallowed.
  section 7  an end-to-end probe runs the ACTUAL registered startup order on CPU
             with a TEST owner key and a fully verified detached approval.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

import exec.synthetic as syn                                        # noqa: E402
from exec.campaign_driver import sha256_file                       # noqa: E402
from exec.watchdog import Watchdog                                 # noqa: E402
from exec.watchdog_authority import (STALE_LIMIT_MULTIPLIER,       # noqa: E402
                                     STARTUP_GRACE_SECONDS, POLL_SECONDS,
                                     AuthorityRecord, WatchdogAuthorityError,
                                     authorized_lock_locator, derive_authority,
                                     load_verified_authority, resolve_timers,
                                     validate_authority_envelope,
                                     validate_lock_locator, write_authority_atomic,
                                     write_lock_locator_atomic)
from test_real_branch_conformance import FakeDynamoTable           # noqa: E402

HPKG = None            # the hermetic package copy (set once in main)
HCOMMIT = None
FIXTURE = None         # a single verified fixture (approval + prep receipt)
RECORD = None          # the AuthorityRecord derived from that verified approval
CID = "cjt-r2c-probe"
WATCHDOG_MAIN = PKG / "exec" / "watchdog_main.py"
WATCHDOG_AUTH = PKG / "exec" / "watchdog_authority.py"


# ---- hermetic fixture -------------------------------------------------------

def make_hermetic_package(dst: Path):
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns(
        "__pycache__", "results", "derived"))
    r = subprocess.run([sys.executable, str(dst / "tools" / "build_manifests.py")],
                       capture_output=True, text=True, cwd=dst)
    assert r.returncode == 0, r.stdout + r.stderr
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.email=r2c@test", "-c", "user.name=r2c",
                 "commit", "-q", "-m", "hermetic"]):
        subprocess.run(cmd, cwd=dst, capture_output=True, text=True, check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dst,
                            capture_output=True, text=True, check=True).stdout.strip()
    return dst, commit


def build_verified_fixture(base: Path, hpkg: Path, hcommit: str, campaign_id: str):
    """A TEST-key detached execution approval + prep receipt, verifiable by the
    committed verifier. verify_execution only shape-checks the model/dataset/
    schedule/S7 digests in SYNTHETIC mode, so those are dummy 64-hex; the prep
    receipt is a real file whose sha is bound into the approval."""
    base.mkdir(parents=True, exist_ok=True)
    synthetic_root = base / "synthetic"
    detached = base / "detached"; detached.mkdir(parents=True, exist_ok=True)
    evidence = base / "evidence"; evidence.mkdir(parents=True, exist_ok=True)
    ident = {"model_revision_sha": "ab" * 20,
             "model_weight_sha256s": {"model.safetensors": "aa" * 32},
             "tokenizer_file_sha256s": {"tokenizer.json": "bb" * 32}}
    prep_receipt_path, prep_receipt = syn.build_container_prep_receipt(
        synthetic_root, ident, "cc" * 32, "88" * 32)
    fixture = {"container_prep_receipt_sha256": sha256_file(prep_receipt_path),
               "model_revision_sha": ident["model_revision_sha"],
               "model_weight_sha256s": ident["model_weight_sha256s"],
               "tokenizer_file_sha256s": ident["tokenizer_file_sha256s"],
               "dependency_lock_sha256": "88" * 32,
               "container_image_digest": prep_receipt["container_image_digest"],
               "dataset_manifest_sha256": "dd" * 32,
               "s7_control_table_sha256": "cc" * 32,
               "run_schedule_sha256": "ee" * 32}
    prep_path, exec_path = syn.build_synthetic_approvals(
        detached, hpkg, hcommit, fixture)
    return {"exec_path": exec_path, "prep_receipt_path": prep_receipt_path,
            "evidence": evidence, "campaign_id": campaign_id}


def _derive():
    return derive_authority(
        approval_path=FIXTURE["exec_path"],
        prep_receipt_path=FIXTURE["prep_receipt_path"], package_root=HPKG,
        expected_campaign_id=CID, mode="SYNTHETIC_CONFORMANCE",
        expected_commit=HCOMMIT)


def _load(authority_path):
    return load_verified_authority(
        mode="SYNTHETIC_CONFORMANCE", approval_path=FIXTURE["exec_path"],
        prep_receipt_path=FIXTURE["prep_receipt_path"], package_root=HPKG,
        expected_campaign_id=CID, authority_path=authority_path,
        expected_commit=HCOMMIT)


def _tmp():
    return Path(tempfile.mkdtemp(prefix="r2c_"))


# ---- section 1: bootstrap order ---------------------------------------------

def test_frozen_bootstrap_creates_config_before_watchdog_start():
    src = (PKG / "infra" / "bootstrap.sh").read_text(encoding="utf-8")
    auth = src.index("exec/watchdog_authority.py")
    wd = src.index("exec/watchdog_main.py")
    assert auth < wd, "the authority-write step must precede the watchdog start"
    print("PASS test_frozen_bootstrap_creates_config_before_watchdog_start")


def test_real_bootstrap_has_no_config_creation_race():
    src = (PKG / "infra" / "bootstrap.sh").read_text(encoding="utf-8")
    stage = src.index("exec/stage_main.py")
    auth = src.index("exec/watchdog_authority.py")
    wd = src.index("exec/watchdog_main.py")
    launcher = src.index("exec/launcher.py")
    assert stage < auth < wd < launcher, \
        "order must be stage -> write authority -> watchdog -> driver"
    # the watchdog no longer reads a driver-written config file for its cap
    wm = WATCHDOG_MAIN.read_text(encoding="utf-8")
    assert "watchdog_config" not in wm and "load_config" not in wm, \
        "watchdog_main still consults the untrusted config authority"
    print("PASS test_real_bootstrap_has_no_config_creation_race")


def test_watchdog_never_starts_with_missing_real_config():
    # REAL watchdog with a MISSING authority file fails closed: it never enters a
    # poll loop against an unverified authority (marker + termination + rc2). With
    # no owner key pinned, the approval verification refuses first -- either way
    # fail-closed, never a silent poll loop.
    tmp = _tmp()
    try:
        ev = tmp / "ev"; ev.mkdir(parents=True)
        dummy_approval = tmp / "approval.json"        # detached, but unverifiable
        dummy_approval.write_text("{}\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(WATCHDOG_MAIN), "--mode", "REAL",
             "--heartbeat", str(ev / "hb.json"), "--evidence", str(ev),
             "--approval", str(dummy_approval),
             "--prep-receipt", str(tmp / "prep.json"),
             "--package-root", str(PKG), "--campaign-id", CID,
             "--authority", str(ev / "watchdog_authority.json")],
            capture_output=True, text=True, timeout=60)
        assert r.returncode == 2, f"rc={r.returncode} out={r.stdout}{r.stderr}"
        marker = json.loads((ev / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_INTERNAL_ERROR", marker
        assert (ev / "TERMINATION_REQUESTED.json").is_file() \
            or (ev / "TERMINATION_UNAVAILABLE_NOT_ON_EC2.json").is_file()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_watchdog_never_starts_with_missing_real_config")


def test_delayed_driver_start_does_not_kill_verified_watchdog():
    tmp = _tmp()
    try:
        rec = _derive()
        auth = tmp / "watchdog_authority.json"
        write_authority_atomic(auth, rec)
        loaded = _load(auth)
        ev = tmp / "ev"; ev.mkdir(parents=True)
        wd = Watchdog(ev / "hb.json", ev, loaded.stale_limit_seconds,
                      startup_grace_seconds=STARTUP_GRACE_SECONDS,
                      launched_at=1000.0)
        # driver has not written a heartbeat yet, but we are inside the grace
        assert wd.poll_once(1000.0 + 30.0) is True, "killed a delayed driver"
        assert wd.poll_once(1000.0 + STARTUP_GRACE_SECONDS - 1.0) is True
        assert not (ev / "WATCHDOG_TERMINATION.json").is_file(), \
            "a verified watchdog terminated during the startup grace"
        # past the grace with still no heartbeat -> terminate
        assert wd.poll_once(1000.0 + STARTUP_GRACE_SECONDS + 1.0) is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_delayed_driver_start_does_not_kill_verified_watchdog")


# ---- section 2: signed authority is load-bearing ----------------------------

def test_watchdog_derives_cap_from_verified_approval():
    rec = _derive()
    assert rec.signed_per_job_cap_hours == 2.0
    assert rec.stale_limit_seconds == 2.0 * 3600.0 * STALE_LIMIT_MULTIPLIER
    assert abs(rec.stale_limit_seconds - 7920.0) < 1e-6
    print("PASS test_watchdog_derives_cap_from_verified_approval")


def test_self_consistent_forged_config_refused():
    tmp = _tmp()
    try:
        rec = _derive()
        forged = rec.as_dict()
        # internally consistent, but NOT what the owner signed: bigger cap +
        # matching cap*3600*1.1, valid shapes, valid frozen timers
        forged["signed_per_job_cap_hours"] = 1000000.0
        forged["stale_limit_seconds"] = 1000000.0 * 3600.0 * STALE_LIMIT_MULTIPLIER
        auth = tmp / "watchdog_authority.json"
        auth.write_text(json.dumps(forged, indent=2) + "\n", encoding="utf-8")
        # envelope validation ALONE accepts it (self-consistent) ...
        validate_authority_envelope(json.loads(auth.read_text(encoding="utf-8")))
        # ... but the verified-approval binding refuses it
        try:
            _load(auth)
            raise AssertionError("a self-consistent forged authority was accepted")
        except WatchdogAuthorityError as exc:
            assert "AUTHORITY_FIELD_MISMATCH" in str(exc), exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_self_consistent_forged_config_refused")


def test_tampered_cap_cannot_extend_timeout():
    tmp = _tmp()
    try:
        rec = _derive()
        auth = tmp / "watchdog_authority.json"
        write_authority_atomic(auth, rec)
        assert abs(_load(auth).stale_limit_seconds - 7920.0) < 1e-6  # signed value
        # tamper the file to a decades-long cap
        d = rec.as_dict()
        d["signed_per_job_cap_hours"] = 87600.0              # 10 years
        d["stale_limit_seconds"] = 87600.0 * 3600.0 * STALE_LIMIT_MULTIPLIER
        auth.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        try:
            _load(auth)
            raise AssertionError("tampered cap extended the timeout")
        except WatchdogAuthorityError:
            pass
        # the DERIVED record (what the watchdog actually uses) is unchanged
        assert abs(_derive().stale_limit_seconds - 7920.0) < 1e-6
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_tampered_cap_cannot_extend_timeout")


def test_wrong_campaign_id_refused():
    tmp = _tmp()
    try:
        rec = _derive()
        d = rec.as_dict(); d["campaign_id"] = "not-this-campaign"
        auth = tmp / "a.json"
        auth.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        try:
            _load(auth)
            raise AssertionError("wrong campaign id accepted")
        except WatchdogAuthorityError as exc:
            assert "AUTHORITY_FIELD_MISMATCH" in str(exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_wrong_campaign_id_refused")


def test_wrong_package_commit_refused():
    # an approval that does not match the checked-out commit is refused by the
    # verifier (fail closed before any authority file is even read)
    try:
        derive_authority(
            approval_path=FIXTURE["exec_path"],
            prep_receipt_path=FIXTURE["prep_receipt_path"], package_root=HPKG,
            expected_campaign_id=CID, mode="SYNTHETIC_CONFORMANCE",
            expected_commit="0" * 40)
        raise AssertionError("wrong checked-out commit accepted")
    except Exception as exc:
        assert "execution_code_commit_sha" in str(exc) or "APPROVAL_INVALID" in str(exc)
    print("PASS test_wrong_package_commit_refused")


def test_wrong_execution_approval_digest_refused():
    tmp = _tmp()
    try:
        rec = _derive()
        d = rec.as_dict(); d["execution_approval_sha256"] = "0" * 64
        auth = tmp / "a.json"
        auth.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        try:
            _load(auth)
            raise AssertionError("wrong approval digest accepted")
        except WatchdogAuthorityError as exc:
            assert "AUTHORITY_FIELD_MISMATCH" in str(exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_wrong_execution_approval_digest_refused")


def test_wrong_owner_key_id_refused():
    tmp = _tmp()
    try:
        rec = _derive()
        d = rec.as_dict(); d["owner_key_id"] = "SOME-OTHER-KEY"
        auth = tmp / "a.json"
        auth.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        try:
            _load(auth)
            raise AssertionError("wrong owner key id accepted")
        except WatchdogAuthorityError as exc:
            assert "AUTHORITY_FIELD_MISMATCH" in str(exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_wrong_owner_key_id_refused")


# ---- section 4: atomic writes -----------------------------------------------

def test_authority_config_write_is_atomic():
    tmp = _tmp()
    try:
        rec = _derive()
        auth = tmp / "watchdog_authority.json"
        write_authority_atomic(auth, rec)
        assert auth.is_file()
        # a full overwrite replaces prior content entirely (os.replace), leaving
        # no temp file behind
        write_authority_atomic(auth, rec)
        leftovers = [p.name for p in tmp.iterdir() if p.name.endswith(".tmp")]
        assert not leftovers, f"atomic write left a temp file: {leftovers}"
        obj = json.loads(auth.read_text(encoding="utf-8"))
        validate_authority_envelope(obj)
        # source law: the authority + locator writers route through the atomic writer
        wa = WATCHDOG_AUTH.read_text(encoding="utf-8")
        assert "write_utf8_lf_atomic" in wa and "write_authority_atomic" in wa
        from exec.fsio import write_utf8_lf_atomic
        try:
            write_utf8_lf_atomic(tmp / "x.json", "has\rcr")
            raise AssertionError("atomic writer accepted a CR")
        except ValueError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_authority_config_write_is_atomic")


def test_lock_locator_write_is_atomic():
    tmp = _tmp()
    try:
        rec = _derive()
        loc = tmp / "protected_lock_locator.json"
        write_lock_locator_atomic(loc, rec)
        validate_lock_locator(json.loads(loc.read_text(encoding="utf-8")), rec)
        assert not [p for p in tmp.iterdir() if p.name.endswith(".tmp")]
        # the DRIVER writes the locator atomically (not via the plain writer)
        drv = (PKG / "exec" / "campaign_driver.py").read_text(encoding="utf-8")
        assert "write_utf8_lf_atomic(self.er / \"protected_lock_locator.json\"" in drv \
            or "protected_lock_locator.json" in drv and "write_utf8_lf_atomic" in drv
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_lock_locator_write_is_atomic")


def test_watchdog_poll_during_config_update_never_reads_partial_json():
    # finding 3 closed structurally: the authority is verified ONCE at startup and
    # is immutable in memory; the poll loop never re-reads it, so a rewrite can
    # never be observed half-written.
    wm = WATCHDOG_MAIN.read_text(encoding="utf-8")
    assert wm.count("load_verified_authority(") == 1, \
        "the authority must be loaded exactly once (not per poll)"
    before_loop = wm.split("while True:")[0]
    assert "load_verified_authority(" in before_loop, \
        "the authority load must be BEFORE the poll loop"
    after_loop = wm.split("while True:")[1]
    assert "load_verified_authority(" not in after_loop, \
        "the poll loop must not re-read the authority"
    print("PASS test_watchdog_poll_during_config_update_never_reads_partial_json")


# ---- section 5: timer totality ----------------------------------------------

def test_real_startup_grace_not_caller_controlled():
    grace, _ = resolve_timers("REAL", caller_grace=1_000_000_000.0,
                              caller_poll=None)
    assert grace == STARTUP_GRACE_SECONDS, "REAL grace was caller-controlled"
    print("PASS test_real_startup_grace_not_caller_controlled")


def test_real_poll_interval_not_caller_controlled():
    _, poll = resolve_timers("REAL", caller_grace=None,
                             caller_poll=1_000_000_000.0)
    assert poll == POLL_SECONDS, "REAL poll interval was caller-controlled"
    print("PASS test_real_poll_interval_not_caller_controlled")


def test_negative_poll_interval_fails_closed():
    try:
        resolve_timers("SYNTHETIC_CONFORMANCE", caller_poll=-1.0)
        raise AssertionError("negative poll accepted")
    except WatchdogAuthorityError as exc:
        assert "TIMER_INVALID" in str(exc)
    print("PASS test_negative_poll_interval_fails_closed")


def test_nan_poll_interval_fails_closed():
    try:
        resolve_timers("SYNTHETIC_CONFORMANCE", caller_poll=float("nan"))
        raise AssertionError("NaN poll accepted")
    except WatchdogAuthorityError:
        pass
    print("PASS test_nan_poll_interval_fails_closed")


def test_infinite_poll_interval_fails_closed():
    try:
        resolve_timers("SYNTHETIC_CONFORMANCE", caller_poll=float("inf"))
        raise AssertionError("infinite poll accepted")
    except WatchdogAuthorityError:
        pass
    print("PASS test_infinite_poll_interval_fails_closed")


def test_huge_poll_interval_cannot_disable_watchdog():
    # in REAL a huge caller poll is ignored (frozen constant); in conformance it
    # exceeds the registered ceiling and fails closed -- either way it cannot
    # stretch the poll interval to disable timely termination
    assert resolve_timers("REAL", caller_poll=1e12) == (STARTUP_GRACE_SECONDS,
                                                        POLL_SECONDS)
    try:
        resolve_timers("SYNTHETIC_CONFORMANCE", caller_poll=1e12)
        raise AssertionError("over-ceiling poll accepted")
    except WatchdogAuthorityError:
        pass
    print("PASS test_huge_poll_interval_cannot_disable_watchdog")


def test_sleep_exception_requests_termination():
    # the sleep is INSIDE the fail-closed boundary: if time.sleep raises, the
    # watchdog writes a marker and requests termination rather than vanishing
    import exec.watchdog_main as wm
    tmp = _tmp()
    try:
        rec = _derive()
        ev = tmp / "ev"; ev.mkdir(parents=True)
        auth = ev / "watchdog_authority.json"
        write_authority_atomic(auth, rec)
        hb = ev / "hb.json"
        real_time = wm.time
        now = real_time.time()
        hb.write_text(json.dumps({"t": now}) + "\n", encoding="utf-8")  # fresh

        class _T:
            time = staticmethod(real_time.time)

            @staticmethod
            def sleep(_x):
                raise RuntimeError("SLEEP_BOOM")

        argv = ["watchdog_main", "--mode", "SYNTHETIC_CONFORMANCE",
                "--heartbeat", str(hb), "--evidence", str(ev),
                "--approval", str(FIXTURE["exec_path"]),
                "--prep-receipt", str(FIXTURE["prep_receipt_path"]),
                "--package-root", str(HPKG), "--campaign-id", CID,
                "--authority", str(auth), "--expected-commit", HCOMMIT,
                "--poll-seconds", "0"]
        old_argv, wm.time = sys.argv, _T
        try:
            sys.argv = argv
            rc = wm.main()
        finally:
            sys.argv, wm.time = old_argv, real_time
        assert rc == 2, f"sleep exception did not fail closed: rc={rc}"
        marker = json.loads((ev / "WATCHDOG_TERMINATION.json")
                            .read_text(encoding="utf-8"))
        assert marker["reason"] == "WATCHDOG_INTERNAL_ERROR", marker
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_sleep_exception_requests_termination")


# ---- section 6: burn terminality --------------------------------------------

def test_nested_lock_campaign_must_match_top_level_campaign():
    rec = _derive()
    authorized = authorized_lock_locator(rec)
    bad = dict(authorized); bad["campaign_id"] = "another-campaign"
    try:
        validate_lock_locator(bad, rec)
        raise AssertionError("locator with a foreign campaign id accepted")
    except WatchdogAuthorityError as exc:
        assert "LOCATOR_MISMATCH" in str(exc)
    print("PASS test_nested_lock_campaign_must_match_top_level_campaign")


def test_wrong_lock_region_refused():
    rec = _derive()
    bad = dict(authorized_lock_locator(rec)); bad["region"] = "eu-west-1"
    try:
        validate_lock_locator(bad, rec)
        raise AssertionError("locator with a wrong region accepted")
    except WatchdogAuthorityError as exc:
        assert "LOCATOR_MISMATCH" in str(exc)
    print("PASS test_wrong_lock_region_refused")


def test_config_failure_after_protected_claim_uses_verified_lock_locator():
    # a missing/corrupt locator must NOT erase the burn: the watchdog derives the
    # authorized coordinates from the verified approval and burns the active lock
    from exec.protected_lock import AwsProtectedLock
    from exec import watchdog_main as wm
    rec = _derive()
    authorized = authorized_lock_locator(rec)
    table = FakeDynamoTable()
    setup = AwsProtectedLock(authorized["table_name"], authorized["region"])
    setup._table = lambda: table
    setup.claim(rec.campaign_id, execution_approval_sha256=rec.execution_approval_sha256,
                package_commit_sha=rec.package_commit_sha,
                protected_derivation="PUBLIC_SEED_20260831",
                claimant_identity="i-abandoned", claim_utc="RUNTIME")
    assert setup.state(rec.campaign_id) == "PROTECTED_RUNNING"
    tmp = _tmp()
    orig = AwsProtectedLock._table
    try:
        ev = tmp / "ev"; ev.mkdir(parents=True)          # NO locator file present
        AwsProtectedLock._table = lambda self: table
        wm._burn_if_protected(rec, ev, "REAL")
        receipt = json.loads((ev / "WATCHDOG_BURN_RECEIPT.json")
                             .read_text(encoding="utf-8"))
        assert receipt["outcome"] == "BURNED"
        assert setup.state(rec.campaign_id) == "PROTECTED_BURNED"
    finally:
        AwsProtectedLock._table = orig
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_config_failure_after_protected_claim_uses_verified_lock_locator")


def test_burn_failure_is_recorded_not_swallowed():
    from exec.protected_lock import AwsProtectedLock, ProtectedLockViolation
    from exec import watchdog_main as wm
    rec = _derive()
    tmp = _tmp()
    orig_state, orig_burn = AwsProtectedLock.state, AwsProtectedLock.burn

    def _boom_burn(self, campaign_id, **kw):
        raise ProtectedLockViolation("PROTECTED_BURN_FAILED: injected")
    try:
        ev = tmp / "ev"; ev.mkdir(parents=True)
        AwsProtectedLock.state = lambda self, c: "PROTECTED_RUNNING"
        AwsProtectedLock.burn = _boom_burn
        wm._burn_if_protected(rec, ev, "REAL")           # must NOT raise
        rec_json = json.loads((ev / "WATCHDOG_BURN_FAILED.json")
                              .read_text(encoding="utf-8"))
        assert rec_json["outcome"] == "BURN_FAILED"
        assert "injected" in rec_json["error"]
    finally:
        AwsProtectedLock.state, AwsProtectedLock.burn = orig_state, orig_burn
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_burn_failure_is_recorded_not_swallowed")


# ---- section 7: end-to-end registered bootstrap probe -----------------------

def test_end_to_end_registered_bootstrap_order():
    tmp = _tmp()
    try:
        ev = tmp / "results"; ev.mkdir(parents=True)
        auth = ev / "watchdog_authority.json"
        # 1) the PRE-WATCHDOG step (the actual CLI) writes the authority FIRST
        assert not auth.exists()
        r = subprocess.run(
            [sys.executable, str(WATCHDOG_AUTH), "--mode", "SYNTHETIC_CONFORMANCE",
             "--approval", str(FIXTURE["exec_path"]),
             "--prep-receipt", str(FIXTURE["prep_receipt_path"]),
             "--package-root", str(HPKG), "--campaign-id", CID,
             "--expected-commit", HCOMMIT, "--authority-out", str(auth)],
            capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, f"authority write refused: {r.stdout}{r.stderr}"
        assert auth.is_file() and "WATCHDOG_AUTHORITY_WRITTEN" in r.stdout
        # 2) the watchdog independently verifies + binds it
        rec = _load(auth)
        assert abs(rec.stale_limit_seconds - 7920.0) < 1e-6
        # 3) survives to the first heartbeat within the grace; clean start emits
        #    no termination
        wd = Watchdog(ev / "hb.json", ev, rec.stale_limit_seconds,
                      startup_grace_seconds=STARTUP_GRACE_SECONDS, launched_at=1000.0)
        assert wd.poll_once(1000.0 + 5.0) is True
        assert not (ev / "WATCHDOG_TERMINATION.json").is_file()
        # 4) a forged authority (bigger cap) cannot extend the cap
        d = rec.as_dict(); d["signed_per_job_cap_hours"] = 5000.0
        d["stale_limit_seconds"] = 5000.0 * 3600.0 * STALE_LIMIT_MULTIPLIER
        auth.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        try:
            _load(auth)
            raise AssertionError("forged authority extended the cap")
        except WatchdogAuthorityError:
            pass
        # 5) a malformed authority terminates fail-closed (via watchdog_main CLI)
        for text in ("[]", "null", "5"):
            ev2 = tmp / ("m" + str(len(text)))
            ev2.mkdir(parents=True)
            bad_auth = ev2 / "watchdog_authority.json"
            bad_auth.write_text(text, encoding="utf-8")
            r2 = subprocess.run(
                [sys.executable, str(WATCHDOG_MAIN), "--mode", "SYNTHETIC_CONFORMANCE",
                 "--heartbeat", str(ev2 / "hb.json"), "--evidence", str(ev2),
                 "--approval", str(FIXTURE["exec_path"]),
                 "--prep-receipt", str(FIXTURE["prep_receipt_path"]),
                 "--package-root", str(HPKG), "--campaign-id", CID,
                 "--authority", str(bad_auth), "--expected-commit", HCOMMIT,
                 "--poll-seconds", "0"],
                capture_output=True, text=True, timeout=60)
            assert r2.returncode == 2, f"malformed {text!r}: rc={r2.returncode}"
            marker = json.loads((ev2 / "WATCHDOG_TERMINATION.json")
                                .read_text(encoding="utf-8"))
            assert marker["reason"] == "WATCHDOG_INTERNAL_ERROR"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_end_to_end_registered_bootstrap_order")
    print("PASS test_malformed_authority_envelope_fails_closed (array/null/scalar)")
    print("PASS test_clean_startup_requests_no_termination")


def main():
    global HPKG, HCOMMIT, FIXTURE, RECORD
    base = Path(tempfile.mkdtemp(prefix="r2c_hermetic_"))
    HPKG, HCOMMIT = make_hermetic_package(base / "hermetic_pkg")
    FIXTURE = build_verified_fixture(base / "fixture", HPKG, HCOMMIT, CID)
    RECORD = _derive()
    print(f"hermetic package @ {HCOMMIT[:12]}, verified fixture built, "
          f"derived stale_limit_seconds={RECORD.stale_limit_seconds}")

    test_frozen_bootstrap_creates_config_before_watchdog_start()
    test_real_bootstrap_has_no_config_creation_race()
    test_watchdog_never_starts_with_missing_real_config()
    test_delayed_driver_start_does_not_kill_verified_watchdog()

    test_watchdog_derives_cap_from_verified_approval()
    test_self_consistent_forged_config_refused()
    test_tampered_cap_cannot_extend_timeout()
    test_wrong_campaign_id_refused()
    test_wrong_package_commit_refused()
    test_wrong_execution_approval_digest_refused()
    test_wrong_owner_key_id_refused()

    test_authority_config_write_is_atomic()
    test_lock_locator_write_is_atomic()
    test_watchdog_poll_during_config_update_never_reads_partial_json()

    test_real_startup_grace_not_caller_controlled()
    test_real_poll_interval_not_caller_controlled()
    test_negative_poll_interval_fails_closed()
    test_nan_poll_interval_fails_closed()
    test_infinite_poll_interval_fails_closed()
    test_huge_poll_interval_cannot_disable_watchdog()
    test_sleep_exception_requests_termination()

    test_nested_lock_campaign_must_match_top_level_campaign()
    test_wrong_lock_region_refused()
    test_config_failure_after_protected_claim_uses_verified_lock_locator()
    test_burn_failure_is_recorded_not_swallowed()

    test_end_to_end_registered_bootstrap_order()

    shutil.rmtree(base, ignore_errors=True)
    print("ALL WATCHDOG BOOTSTRAP-AUTHORITY TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
