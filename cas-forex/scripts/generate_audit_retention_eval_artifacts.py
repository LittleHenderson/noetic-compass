"""Generate audit-retention / evidence-integrity eval artifacts.

Target receipt: `governance_regulatory_proof_claim__audit_retention_proof_pass`.

WHAT THIS RUN IS. A measured probe of the evidence and audit machinery that
actually exists in this repository:

  1. `cas_forex/evidence_store.py`  — local hash-chained JSONL evidence store.
  2. `cas_forex/operator_audit.py`  — append-only operator action log.
  3. `noetic-compass-scaffold/.../api/routes/evidence.py` — the only implemented
     `/verify` endpoint in the tree (a model-provenance verifier).

Every case in sections A, B and C is BEHAVIOURAL: real files on disk, real
appends, real tamper, real HTTP calls through a real TestClient. Section D is
STRUCTURAL only, and says so per case — those are absence assertions that pin
today's shape and are designed to FAIL the day the corresponding machinery is
built.

WHAT THIS RUN IS NOT, and deliberately so. It does not establish that audit
records are RETAINED. No retention window is enforced anywhere in `cas-forex`;
no code in `cas-forex` expires, purges, rotates or locks a record. This run
therefore cannot and does not close `audit_retention_proof_pass`, which
`docs/working/cjt_ungating_external_gate_checklist_20260617.md` classifies as
needing external legal/regulatory review and AUDITED retention proof. See the
report's "Out of scope, deliberately" section.

Gap discipline follows `generate_csb_red_team_artifacts.py`: a property the book
leans on that the code does not enforce is recorded as a gap with a disposition.
It is never waived and never converted into a pass.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

CAS_FOREX_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = WORKSPACE_ROOT / "noetic-compass-scaffold" / "noetic-compass"

sys.path.insert(0, str(CAS_FOREX_ROOT))

from cas_forex.operator_audit import (  # noqa: E402
    OperatorAuditLog,
    build_entry,
)
from cas_forex.pcba_readiness import (  # noqa: E402
    REQUIRED_EVIDENCE,
    PcbaProductionFeature,
    collect_local_pcba_evidence,
)
from cas_forex.evidence_store import EvidenceStore  # noqa: E402
from cas_forex.schemas.evidence import (  # noqa: E402
    EvidenceReceipt,
    ForexEvidencePacket,
)
from cas_forex.time_utils import utc_now  # noqa: E402

REVIEWER_ID = "claude_opus5_local_reviewer_20260725"
WORKING_DIR = WORKSPACE_ROOT / "docs" / "working"
DATE_TAG = "20260725"
RUN_ID = "audit-retention-eval"

CONCURRENCY_TRIALS = 5
CONCURRENCY_THREADS = 2
CONCURRENCY_APPENDS_PER_THREAD = 25


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------


def _case(case_id: str, category: str, kind: str, description: str,
          expected: str, observed: str, passed: bool,
          evidence: dict[str, Any], generated_at: str) -> dict[str, Any]:
    """One eval case. `kind` is 'behavioural' or 'structural' — never blurred."""
    return {
        "case_id": case_id,
        "category": category,
        "measurement_kind": kind,
        "description": description,
        "expected": expected,
        "observed": observed,
        "passed": passed,
        "evidence": evidence,
        "record_type": "case",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


def _gap(case_id: str, kind: str, description: str, hoped: str, observed: str,
         disposition: str, evidence: dict[str, Any],
         generated_at: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": "known_gap",
        "measurement_kind": kind,
        "description": description,
        "hoped": hoped,
        "observed": observed,
        "is_gap": observed != hoped,
        "disposition": disposition,
        "evidence": evidence,
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


def _packet(note: str, trace_id: str | None = None,
            packet_id: str | None = None) -> ForexEvidencePacket:
    return ForexEvidencePacket(
        packet_id=packet_id or str(uuid.uuid4()),
        trace_id=trace_id or str(uuid.uuid4()),
        notes=[note],
    )


def _seed_store(store: EvidenceStore, n: int, prefix: str = "seed") -> list[EvidenceReceipt]:
    receipts = []
    for i in range(n):
        packet = _packet(f"{prefix}-{i}")
        packet.finalize()
        receipts.append(store.append(packet))
    return receipts


def _lines(path: Path) -> list[str]:
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("".join(ln + "\n" for ln in lines), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Section A — EvidenceStore, behavioural
# ---------------------------------------------------------------------------


def section_a(generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    tmp = Path(tempfile.mkdtemp(prefix="audit_retention_a_"))

    try:
        # --- A1 false-positive control: an untouched store must verify clean --
        p = tmp / "pristine.jsonl"
        store = EvidenceStore(p, run_id="pristine")
        _seed_store(store, 5)
        ok = store.verify_chain()
        cases.append(_case(
            "evstore_pristine_verifies", "false_positive_control", "behavioural",
            "An untouched 5-record store must verify clean. A chain checker that "
            "flags an honest store is useless.",
            "verify_chain=True", f"verify_chain={ok}", ok is True,
            {"records": store.record_count, "path": str(p)}, generated_at,
        ))

        # --- A2 false-positive control: appending more must not break it ------
        _seed_store(store, 3, prefix="more")
        ok2 = store.verify_chain()
        cases.append(_case(
            "evstore_append_keeps_chain_valid", "false_positive_control", "behavioural",
            "Legitimate continued appends must not be read as tamper.",
            "verify_chain=True and record_count=8",
            f"verify_chain={ok2} record_count={store.record_count}",
            ok2 is True and store.record_count == 8,
            {"records": store.record_count}, generated_at,
        ))

        # --- A3 ordering and linkage -----------------------------------------
        recs = [json.loads(ln) for ln in _lines(p)]
        seqs = [r["event_seq"] for r in recs]
        seq_ok = seqs == list(range(len(recs)))
        link_ok = recs[0]["previous_record_hash"] is None and all(
            recs[i]["previous_record_hash"] == recs[i - 1]["record_hash"]
            for i in range(1, len(recs))
        )
        cases.append(_case(
            "evstore_ordering_and_linkage", "chain_property", "behavioural",
            "event_seq must be exactly 0..N-1 and each record's "
            "previous_record_hash must equal the prior record's record_hash.",
            "contiguous seq and unbroken back-links",
            f"seq_contiguous={seq_ok} backlinks_ok={link_ok}",
            seq_ok and link_ok,
            {"event_seqs": seqs}, generated_at,
        ))

        # --- A4 cross-process persistence (real second interpreter) ----------
        cp = tmp / "crossproc.jsonl"
        cstore = EvidenceStore(cp, run_id="crossproc")
        _seed_store(cstore, 5)
        probe = (
            "import sys, json;"
            f"sys.path.insert(0, {str(CAS_FOREX_ROOT)!r});"
            "from cas_forex.evidence_store import EvidenceStore;"
            f"s=EvidenceStore({str(cp)!r}, run_id='crossproc');"
            "print(json.dumps({'count': s.record_count, 'valid': s.verify_chain()}))"
        )
        out = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=180,
        )
        try:
            payload = json.loads(out.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            payload = {"count": -1, "valid": False, "stderr": out.stderr[-400:]}
        cp_ok = payload.get("count") == 5 and payload.get("valid") is True
        cases.append(_case(
            "evstore_cross_process_persistence", "durability", "behavioural",
            "Write 5 packets, exit the process, re-open the store in a FRESH "
            "interpreter. The proof must outlive the request (Ch25:71).",
            "count=5 valid=True",
            f"count={payload.get('count')} valid={payload.get('valid')}",
            cp_ok, {"subprocess_stdout": out.stdout.strip()[-300:],
                    "returncode": out.returncode}, generated_at,
        ))

        # --- A5 no overwrite on duplicate identity ---------------------------
        dp = tmp / "dupe.jsonl"
        dstore = EvidenceStore(dp, run_id="dupe")
        shared_trace, shared_packet = "trace-dupe", "packet-dupe"
        for i in range(3):
            pk = _packet(f"dupe-{i}", trace_id=shared_trace, packet_id=shared_packet)
            pk.finalize()
            dstore.append(pk)
        n_lines = len(_lines(dp))
        loaded = len(dstore.load_trace(shared_trace))
        dupe_ok = n_lines == 3 and loaded == 3 and dstore.verify_chain() is True
        cases.append(_case(
            "evstore_no_overwrite_on_duplicate_identity", "chain_property", "behavioural",
            "Three packets sharing packet_id AND trace_id must all persist; a "
            "later write must never replace an earlier record.",
            "3 lines, 3 loaded, chain valid",
            f"lines={n_lines} loaded={loaded} valid={dstore.verify_chain()}",
            dupe_ok, {"path": str(dp)}, generated_at,
        ))

        # --- A6..A11 negative controls: tamper MUST be detected --------------
        def tamper_case(case_id: str, description: str,
                        mutate: Callable[[Path, Path], dict[str, Any]]) -> None:
            tp = tmp / f"{case_id}.jsonl"
            tstore = EvidenceStore(tp, run_id=case_id)
            _seed_store(tstore, 5)
            assert tstore.verify_chain() is True, "pre-tamper store must be clean"
            detail = mutate(tp, tp.with_suffix(tp.suffix + ".state"))
            after = EvidenceStore(tp, run_id=case_id).verify_chain()
            cases.append(_case(
                case_id, "negative_control_tamper", "behavioural", description,
                "verify_chain=False (detected)", f"verify_chain={after}",
                after is False, detail, generated_at,
            ))

        def _content_tamper(jsonl: Path, _state: Path) -> dict[str, Any]:
            lines = _lines(jsonl)
            rec = json.loads(lines[2])
            rec["packet"]["notes"] = ["TAMPERED"]
            lines[2] = json.dumps(rec, sort_keys=True)
            _write_lines(jsonl, lines)
            return {"edited_record_index": 2, "field": "packet.notes"}

        tamper_case(
            "evstore_content_tamper_detected",
            "Edit `notes` inside a middle record, leaving both hashes stale.",
            _content_tamper,
        )

        def _resealed_tamper(jsonl: Path, _state: Path) -> dict[str, Any]:
            lines = _lines(jsonl)
            rec = json.loads(lines[2])
            pk = ForexEvidencePacket.model_validate(rec["packet"])
            pk.notes = ["RESEALED_TAMPER"]
            pk.packet_hash_sha256 = pk.compute_hash()
            rec["packet"] = pk.model_dump(mode="json")
            rec["packet_hash"] = pk.packet_hash_sha256
            body = dict(rec)
            body.pop("record_hash", None)
            rec["record_hash"] = EvidenceStore._sha256(body)
            lines[2] = json.dumps(rec, sort_keys=True)
            _write_lines(jsonl, lines)
            return {"edited_record_index": 2,
                    "note": "packet hash AND record hash recomputed; record is "
                            "internally consistent. Detection must come from the "
                            "forward link in record 3."}

        tamper_case(
            "evstore_resealed_tamper_detected",
            "Edit a middle record AND recompute both its hashes so the record is "
            "internally self-consistent. The forward link must still catch it.",
            _resealed_tamper,
        )

        def _tail_truncate(jsonl: Path, _state: Path) -> dict[str, Any]:
            lines = _lines(jsonl)
            _write_lines(jsonl, lines[:-1])
            return {"removed": "last line", "state_sidecar": "left in place"}

        tamper_case(
            "evstore_tail_truncation_detected",
            "Delete the newest record and leave the .state sidecar alone.",
            _tail_truncate,
        )

        def _mid_delete(jsonl: Path, _state: Path) -> dict[str, Any]:
            lines = _lines(jsonl)
            del lines[2]
            _write_lines(jsonl, lines)
            return {"removed": "interior line index 2"}

        tamper_case(
            "evstore_mid_chain_deletion_detected",
            "Delete an interior record — the suppression a regulator cares about.",
            _mid_delete,
        )

        def _drop_jsonl(jsonl: Path, _state: Path) -> dict[str, Any]:
            jsonl.unlink()
            return {"removed": "the .jsonl, .state kept"}

        tamper_case(
            "evstore_jsonl_deleted_state_kept_detected",
            "Delete the record file but leave the sidecar checkpoint.",
            _drop_jsonl,
        )

        def _drop_state(_jsonl: Path, state: Path) -> dict[str, Any]:
            state.unlink()
            return {"removed": "the .state sidecar, .jsonl kept"}

        tamper_case(
            "evstore_state_deleted_jsonl_kept_detected",
            "Delete the sidecar checkpoint but leave the record file.",
            _drop_state,
        )

        def _torn_write(jsonl: Path, _state: Path) -> dict[str, Any]:
            lines = _lines(jsonl)
            lines[3] = lines[3][: len(lines[3]) // 2]
            _write_lines(jsonl, lines)
            return {"truncated_line_index": 3, "note": "half a JSON object"}

        tamper_case(
            "evstore_torn_write_detected",
            "Truncate one line mid-JSON, simulating a crash during append.",
            _torn_write,
        )

        # --- GAP A12: total wipe verifies clean -------------------------------
        wp = tmp / "wipe.jsonl"
        wstore = EvidenceStore(wp, run_id="wipe")
        _seed_store(wstore, 5)
        before = (wstore.record_count, wstore.verify_chain())
        wp.unlink()
        wp.with_suffix(wp.suffix + ".state").unlink()
        wiped = EvidenceStore(wp, run_id="wipe")
        after_valid = wiped.verify_chain()
        gaps.append(_gap(
            "evstore_total_wipe_undetected", "behavioural",
            "Delete BOTH the .jsonl and the .state sidecar, then verify. A total "
            "history erasure is the exact move Chapter 26:75 says a regulator is "
            "protected against ('a decision the vendor would rather not surface').",
            "detected (verify_chain=False)",
            f"undetected (verify_chain={after_valid}, record_count={wiped.record_count})",
            "GAP, NOT WAIVED. Detection is impossible in principle for a purely "
            "local chain: nothing outside the two files records that a history "
            "ever existed. Closing this needs an external anchor (S3 Object Lock, "
            "a notary, or a co-signed head-hash feed). Disposition: the artifact "
            "must not claim erasure resistance, and Chapter 26's "
            "'any decision the board ever made' must be narrowed to state that "
            "the local trail detects EDITS, not ERASURE. The product UI already "
            "says 'WORM Evidence Anchoring — UNAVAILABLE, local hash chain only' "
            "(ui/src/pages/SettingsPage.tsx:477); the book does not.",
            {"before_count": before[0], "before_valid": before[1],
             "after_count": wiped.record_count, "after_valid": after_valid},
            generated_at,
        ))

        # --- GAP A13: wiped-and-rebuilt shorter history verifies clean --------
        rp = tmp / "rebuild.jsonl"
        rstore = EvidenceStore(rp, run_id="rebuild")
        _seed_store(rstore, 5)
        rp.unlink()
        rp.with_suffix(rp.suffix + ".state").unlink()
        rebuilt = EvidenceStore(rp, run_id="rebuild")
        _seed_store(rebuilt, 2, prefix="rebuilt")
        rebuilt_valid = rebuilt.verify_chain()
        gaps.append(_gap(
            "evstore_rewrite_shorter_undetected", "behavioural",
            "Wipe a 5-record history, then write a fresh 2-record history to the "
            "same path and verify.",
            "detected (verify_chain=False)",
            f"undetected (verify_chain={rebuilt_valid}, record_count={rebuilt.record_count})",
            "GAP, NOT WAIVED. Same root cause as the total wipe: no external "
            "commitment to expected length or head hash. Disposition: recorded as "
            "a limit on the audit-retention claim. The receipt stays unsigned.",
            {"original_count": 5, "rebuilt_count": rebuilt.record_count,
             "rebuilt_valid": rebuilt_valid}, generated_at,
        ))

        # --- GAP A14: concurrent writers lose records -------------------------
        trials: list[dict[str, Any]] = []
        for t in range(CONCURRENCY_TRIALS):
            cpath = tmp / f"concurrent_{t}.jsonl"
            cstore2 = EvidenceStore(cpath, run_id=f"conc{t}")
            errors: list[str] = []

            def worker(tag: str, store_ref: EvidenceStore = cstore2,
                       err: list[str] = errors) -> None:
                for i in range(CONCURRENCY_APPENDS_PER_THREAD):
                    try:
                        pk = _packet(f"{tag}-{i}")
                        pk.finalize()
                        store_ref.append(pk)
                    except Exception as exc:  # noqa: BLE001
                        err.append(f"{type(exc).__name__}: {exc}")

            threads = [threading.Thread(target=worker, args=(f"w{w}",))
                       for w in range(CONCURRENCY_THREADS)]
            for th in threads:
                th.start()
            for th in threads:
                th.join()
            expected_n = CONCURRENCY_THREADS * CONCURRENCY_APPENDS_PER_THREAD
            on_disk = len(_lines(cpath))
            trials.append({
                "trial": t,
                "expected": expected_n,
                "on_disk": on_disk,
                "lost": expected_n - on_disk,
                "exceptions_raised": len(errors),
                "verify_chain": EvidenceStore(cpath, run_id=f"conc{t}").verify_chain(),
            })
        total_expected = sum(x["expected"] for x in trials)
        total_on_disk = sum(x["on_disk"] for x in trials)
        loss_pct = round(100.0 * (total_expected - total_on_disk) / total_expected, 2)
        broken_chains = sum(1 for x in trials if x["verify_chain"] is not True)
        lossy_trials = sum(1 for x in trials if x["lost"] > 0)
        gaps.append(_gap(
            "evstore_concurrent_writers_corrupt_chain", "behavioural",
            f"{CONCURRENCY_THREADS} threads x {CONCURRENCY_APPENDS_PER_THREAD} "
            f"appends against one store path, {CONCURRENCY_TRIALS} trials. Measures "
            f"two distinct things: whether the chain still verifies, and whether "
            f"records reach disk at all.",
            "chain valid in every trial and no records lost",
            (f"chain INVALID in {broken_chains}/{CONCURRENCY_TRIALS} trials; "
             f"record loss in {lossy_trials}/{CONCURRENCY_TRIALS} trials "
             f"({total_expected - total_on_disk}/{total_expected} records, "
             f"{loss_pct}%); no exception raised in any trial"),
            "GAP, NOT WAIVED — and the headline is CHAIN CORRUPTION, not record "
            "loss. EvidenceStore reads its head state, then appends, with no lock. "
            "Two writers interleave, read the same head, and write records that "
            "share an event_seq and a previous_record_hash. The result is a store "
            "whose own verify_chain() returns False — permanently, with no repair "
            "path — even when every record reached disk. Record loss also occurs "
            "when the interleaving is tighter, but it is intermittent; the chain "
            "corruption was reproduced in every trial. In both cases append() "
            "returns a normal receipt, so the caller believes the write succeeded. "
            "Disposition: this is the most operationally severe finding in Section "
            "A, because a single concurrent moment permanently invalidates the "
            "whole evidence chain and is indistinguishable, after the fact, from "
            "deliberate tampering. `operator_audit.py:33-36` carries an explicit "
            "single-writer warning; `evidence_store.py` carries none and must. "
            "Until it does, no claim may be made that every decision reaches the "
            "store or that a False chain verdict implies tampering. Not fixed here "
            "— this run measures, it does not patch. CALIBRATION WARNING: the LOSS "
            "rate is timing-dependent and varies substantially between runs on the "
            "same host; do not treat the percentage as a stable figure. Read the "
            "per-trial numbers in the raw JSONL, not the average.",
            {"trials": trials, "total_expected": total_expected,
             "total_on_disk": total_on_disk, "loss_pct": loss_pct},
            generated_at,
        ))

        # --- GAP A15: mutable after finalize ----------------------------------
        mp = _packet("finalize-mutability")
        mp.finalize()
        pre_valid = mp.verify_hash()
        raised = None
        try:
            mp.notes = ["MUTATED_AFTER_FINALIZE"]
        except Exception as exc:  # noqa: BLE001
            raised = f"{type(exc).__name__}: {exc}"
        post_valid = mp.verify_hash()
        gaps.append(_gap(
            "packet_mutable_after_finalize", "behavioural",
            "schemas/evidence.py:33 says the packet is 'Immutable after "
            "finalization'. Assign to a field after finalize() and see.",
            "assignment raises",
            ("assignment raised" if raised else
             f"assignment silently accepted; verify_hash {pre_valid} -> {post_valid}"),
            "GAP, NOT WAIVED — but LOW severity and precisely characterised. The "
            "packet is tamper-EVIDENT, not immutable: the edit lands, and "
            "verify_hash() flips to False, so a persisted copy is caught. "
            "Disposition: the docstring overstates. It should read 'tamper-evident "
            "after finalization'. An in-memory packet edited before append is NOT "
            "caught, because EvidenceStore re-seals an unsealed packet at append "
            "time (evidence_store.py:27-28).",
            {"raised": raised, "verify_hash_before": pre_valid,
             "verify_hash_after": post_valid}, generated_at,
        ))

        # --- GAP A16: hash timing, decision time vs log time ------------------
        call_sites = _finalize_before_append_sites()
        seal_at_persist = [s for s in call_sites if s["finalize_in_same_function"]]
        gaps.append(_gap(
            "packet_sealed_at_log_time_not_decision_time", "structural",
            "Chapter 25:105 states as a rule: 'hash the packet at decision time, "
            "not at log time... A seal applied after the fact seals nothing.' "
            "AST-walk every EvidenceStore.append() call site and check whether "
            "finalize() is called in the same function body.",
            "0 call sites seal at persistence time",
            f"{len(seal_at_persist)}/{len(call_sites)} call sites call finalize() "
            f"inside the persistence function, immediately before append",
            "GAP, NOT WAIVED. By the book's own sentence these seals seal nothing "
            "— they cover whatever reached the persistence function, not what the "
            "decision produced. Disposition: this is a BOOK finding. Chapter 25:105 "
            "states a rule that no code path in this repository obeys, and the "
            "chapter does not say so. Either the Bench Note gains an explicit "
            "'not yet implemented in the reference codebase' line, or the call "
            "sites move finalize() to the decision site. Recorded here; not fixed "
            "by this run.",
            {"call_sites": call_sites}, generated_at,
        ))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return cases, gaps


def _finalize_before_append_sites() -> list[dict[str, Any]]:
    """Find every `.append(` on an evidence store and report whether
    `.finalize()` is called in the same function body."""
    sites: list[dict[str, Any]] = []
    pkg = CAS_FOREX_ROOT / "cas_forex"
    for py in sorted(pkg.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            src = ast.get_source_segment(py.read_text(encoding="utf-8"), fn) or ""
            has_store_append = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "append"
                and isinstance(n.func.value, ast.Attribute)
                and "store" in n.func.value.attr.lower()
                for n in ast.walk(fn)
            ) or any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "append"
                and isinstance(n.func.value, ast.Name)
                and "store" in n.func.value.id.lower()
                for n in ast.walk(fn)
            )
            if not has_store_append:
                continue
            has_finalize = "finalize()" in src
            sites.append({
                "file": str(py.relative_to(CAS_FOREX_ROOT)).replace("\\", "/"),
                "function": fn.name,
                "line": fn.lineno,
                "finalize_in_same_function": has_finalize,
            })
    return sites


# ---------------------------------------------------------------------------
# Section B — OperatorAuditLog, behavioural
# ---------------------------------------------------------------------------


def section_b(generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    tmp = Path(tempfile.mkdtemp(prefix="audit_retention_b_"))

    try:
        # --- B1 false-positive control: honest entries round-trip -------------
        lp = tmp / "op.jsonl"
        log = OperatorAuditLog(lp)
        for i in range(5):
            log.append(build_entry(
                action_kind="GATE_FLIP", summary=f"gate flipped {i}",
                target_id=f"gate-{i}", payload={"i": i}, reversible=True,
            ))
        stats = log.stats()
        recent = log.list_recent(limit=50)
        b1 = stats["total"] == 5 and len(recent) == 5
        cases.append(_case(
            "opaudit_append_read_roundtrip", "false_positive_control", "behavioural",
            "Five honest entries must append and read back intact.",
            "total=5 recent=5", f"total={stats['total']} recent={len(recent)}",
            b1, {"by_kind": stats["by_kind"]}, generated_at,
        ))

        # --- B2 negative control: advisory summary MUST be rejected ----------
        rejected = False
        detail = ""
        try:
            log.append(build_entry(
                action_kind="OTHER", summary="This is a good entry to take now",
                target_id="advice-1",
            ))
        except ValueError as exc:
            rejected = True
            detail = str(exc)
        after_total = log.stats()["total"]
        cases.append(_case(
            "opaudit_advisory_phrase_rejected", "negative_control_guard", "behavioural",
            "An advisory summary ('good entry') must be refused and NOT written. "
            "This is a real enforced property of the log.",
            "ValueError raised and total stays 5",
            f"raised={rejected} total={after_total}",
            rejected and after_total == 5,
            {"error": detail}, generated_at,
        ))

        # --- B3 false-positive control: a clean summary must NOT be rejected --
        fp_ok = True
        fp_detail = ""
        try:
            log.append(build_entry(
                action_kind="OTHER",
                summary="Operator archived the strategy; risk cap unchanged.",
                target_id="clean-1",
            ))
        except ValueError as exc:
            fp_ok = False
            fp_detail = str(exc)
        cases.append(_case(
            "opaudit_clean_summary_not_rejected", "false_positive_control", "behavioural",
            "A factual, observational summary must be accepted. A guard that "
            "rejects honest records is a false-positive failure.",
            "accepted", "accepted" if fp_ok else f"rejected: {fp_detail}",
            fp_ok, {"total": log.stats()["total"]}, generated_at,
        ))

        # --- GAP B4 tamper undetected -----------------------------------------
        tp = tmp / "tamper.jsonl"
        tlog = OperatorAuditLog(tp)
        for i in range(5):
            tlog.append(build_entry(
                action_kind="GATE_FLIP", summary=f"entry {i}",
                target_id=f"g{i}", payload={"i": i},
            ))
        lines = _lines(tp)
        rec = json.loads(lines[2])
        original_summary = rec["summary"]
        rec["summary"] = "FORGED SUMMARY"
        rec["payload"] = {"i": 999}
        lines[2] = json.dumps(rec, ensure_ascii=False)
        _write_lines(tp, lines)
        served = [e for e in OperatorAuditLog(tp).list_recent(limit=50)
                  if e.summary == "FORGED SUMMARY"]
        gaps.append(_gap(
            "opaudit_in_place_edit_undetected", "behavioural",
            "Edit one entry's summary and payload in place, then read it back "
            "through the public API.",
            "detected by some API",
            (f"undetected — forged row served as genuine "
             f"({len(served)} match)" if served else "detected"),
            "GAP, NOT WAIVED. OperatorAuditEntry has no hash, no previous-hash, "
            "no sequence number, and OperatorAuditLog exposes no verify method. "
            "The log is append-only BY CONVENTION of its own writer, with no "
            "integrity mechanism at all. Disposition: this log must never be "
            "described as tamper-evident, and it is not the evidence behind any "
            "audit claim. If an operator-action audit trail is ever offered as "
            "regulator-facing evidence it needs the EvidenceStore chain treatment.",
            {"original_summary": original_summary,
             "served_forged_rows": len(served)}, generated_at,
        ))

        # --- GAP B5 deletion undetected ---------------------------------------
        dp = tmp / "delete.jsonl"
        dlog = OperatorAuditLog(dp)
        for i in range(5):
            dlog.append(build_entry(action_kind="GATE_FLIP", summary=f"e{i}",
                                    target_id=f"d{i}"))
        pre_total = dlog.stats()["total"]
        dl = _lines(dp)
        del dl[1]
        _write_lines(dp, dl)
        post_total = OperatorAuditLog(dp).stats()["total"]
        gaps.append(_gap(
            "opaudit_deletion_undetected", "behavioural",
            "Remove one line from the operator audit log.",
            "detected",
            f"undetected — stats total silently {pre_total} -> {post_total}",
            "GAP, NOT WAIVED. Same root cause as B4: no chain, no expected count. "
            "Disposition: recorded as a limit. The operator audit log carries no "
            "retention or integrity property and backs no audit claim.",
            {"before": pre_total, "after": post_total}, generated_at,
        ))

        # --- GAP B6 torn write silently dropped -------------------------------
        wp = tmp / "torn.jsonl"
        wlog = OperatorAuditLog(wp)
        for i in range(4):
            wlog.append(build_entry(action_kind="GATE_FLIP", summary=f"t{i}",
                                    target_id=f"t{i}"))
        pre = wlog.stats()["total"]
        wl = _lines(wp)
        wl[2] = wl[2][: len(wl[2]) // 2]
        _write_lines(wp, wl)
        post_log = OperatorAuditLog(wp)
        post = post_log.stats()["total"]
        gaps.append(_gap(
            "opaudit_torn_write_silently_dropped", "behavioural",
            "Truncate one line mid-JSON (crash during append) and read the log.",
            "read APIs raise or report the loss",
            f"silently skipped — total {pre} -> {post}, no error, no dropped-record counter",
            "GAP, NOT WAIVED. operator_audit.py:326-331 `continue`s on "
            "JSONDecodeError by design (documented as 'tolerate corrupt lines'). "
            "Tolerance is reasonable for a cockpit feed and wrong for evidence: "
            "a lost record is indistinguishable from a record never written. "
            "Disposition: if this log is ever promoted to evidence, the read path "
            "needs a skipped-line counter surfaced in stats(). Recorded, not fixed.",
            {"before": pre, "after": post,
             "list_recent_len": len(post_log.list_recent(limit=50))}, generated_at,
        ))

        # --- GAP B7 entry_id collision within one second ----------------------
        ep = tmp / "collide.jsonl"
        elog = OperatorAuditLog(ep)
        a = build_entry(action_kind="GATE_FLIP", summary="flip on",
                        target_id="same-target", payload={"state": "on"})
        b = build_entry(action_kind="GATE_FLIP", summary="flip off",
                        target_id="same-target", payload={"state": "off"})
        elog.append(a)
        elog.append(b)
        collided = a.entry_id == b.entry_id
        gaps.append(_gap(
            "opaudit_entry_id_collision_same_second", "behavioural",
            "Append two DIFFERENT actions on the same target_id inside one second. "
            "Timestamps are second-resolution (operator_audit.py:189) and entry_id "
            "is sha256(action_kind|target_id|timestamp).",
            "distinct entry_ids",
            (f"COLLISION — both entries carry entry_id {a.entry_id}"
             if collided else "distinct"),
            "GAP, NOT WAIVED. Both rows persist, so nothing is lost on disk. The "
            "damage is downstream: the docstring (operator_audit.py:114-117) tells "
            "callers the id exists so they can dedupe on retry, and a consumer "
            "doing that drops a real, distinct operator action. Disposition: "
            "entry_id needs microsecond resolution or a payload digest. Recorded, "
            "not fixed by this run.",
            {"entry_id_a": a.entry_id, "entry_id_b": b.entry_id,
             "summary_a": a.summary, "summary_b": b.summary,
             "rows_on_disk": len(_lines(ep))}, generated_at,
        ))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return cases, gaps


# ---------------------------------------------------------------------------
# Section C — the one implemented /verify, behavioural
# ---------------------------------------------------------------------------


def section_c(generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Returns (cases, gaps, status). status == 'ran' or a plain reason string."""
    cases: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    if not (SCAFFOLD_ROOT / "api" / "routes" / "evidence.py").is_file():
        return cases, gaps, (
            "NOT RUN: noetic-compass-scaffold/noetic-compass/api/routes/evidence.py "
            "is absent from this checkout. The /verify probes cannot be executed."
        )

    sys.path.insert(0, str(SCAFFOLD_ROOT))
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.evidence import _ARTIFACT_BINDINGS, router  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return cases, gaps, f"NOT RUN: import failed — {type(exc).__name__}: {exc}"

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    trace_dir = SCAFFOLD_ROOT / ".tmp" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    # The endpoint enforces a path allowlist (`_verify_allowed_roots`, evidence.py:204)
    # restricting hashable artifacts to the project/scaffold roots. The declared
    # corpus therefore has to live inside one of those roots for the hash
    # comparison to be exercised at all. That guard is itself probed as C3b.
    corpus_dir = SCAFFOLD_ROOT / ".tmp" / f"audit_retention_c_{uuid.uuid4().hex[:8]}"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    outside_dir = Path(tempfile.mkdtemp(prefix="audit_retention_outside_"))
    corpus = corpus_dir / "corpus.txt"
    corpus.write_text("audit-retention eval corpus\n", encoding="utf-8")
    corpus_sha = hashlib.sha256(corpus.read_bytes()).hexdigest()
    outside_corpus = outside_dir / "corpus.txt"
    outside_corpus.write_text("audit-retention eval corpus\n", encoding="utf-8")
    outside_sha = hashlib.sha256(outside_corpus.read_bytes()).hexdigest()

    tid = f"audit-retention-eval-{uuid.uuid4().hex[:10]}"
    tid_missing = f"audit-retention-never-existed-{uuid.uuid4().hex[:10]}"
    trace_path = trace_dir / f"{tid}.json"

    def write_trace(declare_corpus: bool = True,
                    declare_commit: bool = True,
                    corpus_outside_root: bool = False) -> None:
        trace: dict[str, Any] = {
            "input": {"prompt": "audit retention probe"},
            "output": {"text": "probe"},
            "model_checkpoint_id": "audit-retention-probe",
        }
        if declare_corpus:
            trace["corpus_path"] = str(
                outside_corpus if corpus_outside_root else corpus)
            trace["corpus_sha256"] = (
                outside_sha if corpus_outside_root else corpus_sha)
        if declare_commit:
            trace["code_commit_sha"] = "0" * 40
        trace_path.write_text(json.dumps(trace), encoding="utf-8")

    try:
        # --- C1 positive: declared artifact present -> all_match --------------
        write_trace(declare_corpus=True, declare_commit=False)
        get_r = client.get(f"/evidence/{tid}")
        ver_r = client.post(f"/evidence/{tid}/verify")
        overall = ver_r.json().get("overall")
        corpus_check = next(
            (c for c in ver_r.json().get("checks", []) if c["artifact"] == "corpus"),
            None,
        )
        c1 = (get_r.status_code == 200 and ver_r.status_code == 200
              and corpus_check is not None and corpus_check["match"] is True)
        cases.append(_case(
            "verify_declared_artifact_matches", "false_positive_control", "behavioural",
            "A trace declaring corpus_sha256 + corpus_path, with the file present "
            "and unmodified, must verify clean.",
            "GET 200 and corpus check match=true",
            f"GET {get_r.status_code}, overall={overall}, corpus_match="
            f"{corpus_check['match'] if corpus_check else None}",
            c1, {"overall": overall, "checks": ver_r.json().get("checks")},
            generated_at,
        ))

        # --- C2 negative control: artifact tampered -> mismatch ---------------
        corpus.write_text("TAMPERED corpus\n", encoding="utf-8")
        ver_t = client.post(f"/evidence/{tid}/verify").json()
        ct = next((c for c in ver_t.get("checks", []) if c["artifact"] == "corpus"), None)
        c2 = ct is not None and ct["match"] is False
        cases.append(_case(
            "verify_tampered_artifact_detected", "negative_control_tamper", "behavioural",
            "Modify the declared corpus file on disk and re-verify.",
            "corpus check match=false",
            f"overall={ver_t.get('overall')} corpus_match={ct['match'] if ct else None}",
            c2, {"overall": ver_t.get("overall"), "corpus_check": ct}, generated_at,
        ))

        # --- C3 negative control: artifact deleted -> mismatch ----------------
        corpus.unlink()
        ver_d = client.post(f"/evidence/{tid}/verify").json()
        cd = next((c for c in ver_d.get("checks", []) if c["artifact"] == "corpus"), None)
        c3 = cd is not None and cd["match"] is False
        cases.append(_case(
            "verify_deleted_artifact_detected", "negative_control_tamper", "behavioural",
            "Delete the declared corpus file and re-verify.",
            "corpus check match=false",
            f"overall={ver_d.get('overall')} corpus_match={cd['match'] if cd else None}"
            f" notes={cd.get('notes') if cd else None}",
            c3, {"overall": ver_d.get("overall"), "corpus_check": cd}, generated_at,
        ))

        # --- C3b negative control: artifact outside the allowed roots ---------
        # Found while building C1: the endpoint refuses to hash a path outside
        # the project/scaffold roots. That is a real path-traversal defence and
        # deserves its own case.
        write_trace(declare_corpus=True, declare_commit=False,
                    corpus_outside_root=True)
        ver_o = client.post(f"/evidence/{tid}/verify").json()
        co = next((c for c in ver_o.get("checks", []) if c["artifact"] == "corpus"), None)
        c3b = (co is not None and co["match"] is False
               and "outside allowed roots" in (co.get("notes") or ""))
        cases.append(_case(
            "verify_path_outside_allowed_roots_refused", "negative_control_path",
            "behavioural",
            "Declare a corpus that exists and hashes correctly but sits OUTSIDE "
            "the project/scaffold roots. The verifier must refuse to hash it "
            "rather than following the operator-supplied path anywhere on disk.",
            "corpus check match=false with an 'outside allowed roots' note",
            f"match={co['match'] if co else None} notes={co.get('notes') if co else None}",
            c3b, {"declared_path": str(outside_corpus), "corpus_check": co},
            generated_at,
        ))

        # --- C4 structural: verifier scope is model provenance ----------------
        bindings = tuple(b[0] for b in _ARTIFACT_BINDINGS)
        expected_bindings = ("weights", "tokenizer", "english_bpe", "corpus")
        cases.append(_case(
            "verify_scope_is_model_provenance", "scope_pin", "structural",
            "STRUCTURAL. Pin the verifier's check set. Chapter 26:43 presents "
            "/verify as the endpoint that resolves a BOARD DECISION. Its actual "
            "check set is ML model-provenance artifacts. This case fails the day "
            "a decision artifact is added — at which point the behavioural "
            "decision-level cases become writable.",
            f"bindings == {expected_bindings}", f"bindings == {bindings}",
            bindings == expected_bindings, {"bindings": list(bindings)}, generated_at,
        ))

        # --- GAP C5: deleted trace vs never-existed ---------------------------
        corpus.write_text("audit-retention eval corpus\n", encoding="utf-8")
        write_trace(declare_corpus=True, declare_commit=False)
        alive = client.get(f"/evidence/{tid}")
        trace_path.unlink()
        gone_get = client.get(f"/evidence/{tid}")
        gone_post = client.post(f"/evidence/{tid}/verify")
        never_get = client.get(f"/evidence/{tid_missing}")
        never_post = client.post(f"/evidence/{tid_missing}/verify")
        indistinguishable = (
            gone_get.status_code == never_get.status_code
            and gone_get.text == never_get.text
            and gone_post.status_code == never_post.status_code
            and gone_post.text == never_post.text
        )
        gaps.append(_gap(
            "verify_deleted_trace_indistinguishable_from_nonexistent", "behavioural",
            "Create a trace, confirm it resolves, delete the trace file, then "
            "compare the responses for the deleted id and for an id that never "
            "existed. Chapter 26:75 promises a regulator can pull 'any trace ID, "
            "including one from a decision the vendor would rather not surface'.",
            "distinguishable (deleted != never existed)",
            (f"INDISTINGUISHABLE — both return {gone_get.status_code} "
             f"{gone_get.text}" if indistinguishable else "distinguishable"),
            "GAP, NOT WAIVED — the single most important finding for this receipt. "
            "There is no index, manifest, or external anchor enumerating which "
            "trace IDs ought to exist, so a vendor who deletes a record is "
            "indistinguishable from a vendor who never made it. Disposition: "
            "Chapter 26:43 and :75 must be narrowed. The unsuppressible-audit-trail "
            "claim is not backed by anything in this repository and cannot be "
            "closed by local code — it requires an external anchor.",
            {"alive_status": alive.status_code,
             "deleted_get": [gone_get.status_code, gone_get.text],
             "never_existed_get": [never_get.status_code, never_get.text],
             "deleted_post": [gone_post.status_code, gone_post.text],
             "never_existed_post": [never_post.status_code, never_post.text]},
            generated_at,
        ))

        # --- GAP C6: self-declared scope --------------------------------------
        write_trace(declare_corpus=False, declare_commit=False)
        ver_s = client.post(f"/evidence/{tid}/verify").json()
        artifacts = [c["artifact"] for c in ver_s.get("checks", [])]
        gaps.append(_gap(
            "verify_scope_is_self_declared", "behavioural",
            "Strip the corpus declaration from the trace file and re-verify.",
            "verifier still checks corpus (or reports the omission as a failure)",
            f"overall={ver_s.get('overall')} with checks {artifacts} — the corpus "
            f"check simply disappears",
            "GAP, NOT WAIVED. Documented behaviour (evidence.py:729-730: artifacts "
            "whose expected SHA is absent are skipped entirely), so this is not a "
            "bug — but it is a real limit: an operator who controls the trace file "
            "produces a clean verdict by removing the declaration. Disposition: a "
            "verify verdict is only as strong as the declaration set, and the "
            "declaration set is not itself anchored. Any regulator-facing use needs "
            "a required-artifact list held outside the trace.",
            {"overall": ver_s.get("overall"), "checks": ver_s.get("checks")},
            generated_at,
        ))

        # --- GAP C7: code_commit check cannot fail ----------------------------
        write_trace(declare_corpus=False, declare_commit=False)
        ver_c = client.post(f"/evidence/{tid}/verify").json()
        commit_check = next(
            (c for c in ver_c.get("checks", []) if c["artifact"] == "code_commit"), None)
        cannot_fail = commit_check is not None and commit_check["match"] is True
        gaps.append(_gap(
            "verify_code_commit_check_cannot_fail", "behavioural",
            "Verify a trace that omits code_commit_sha. _packet_from_trace "
            "(evidence.py:622-627) fills the expected value from _git_head_sha(), "
            "and the verifier then compares it to git HEAD in the same process.",
            "the check is capable of failing",
            (f"tautology — match={commit_check['match']} always, expected and "
             f"actual both come from git HEAD" if cannot_fail else "capable of failing"),
            "GAP, NOT WAIVED. This is exactly the 'engineered to pass' shape this "
            "eval is forbidden to produce, so it is recorded and EXCLUDED from the "
            "pass count rather than counted. Disposition: when a trace omits its "
            "commit, the check should be omitted or reported as unverifiable, not "
            "auto-satisfied. No case in this artifact is built on it.",
            {"check": commit_check, "overall": ver_c.get("overall")}, generated_at,
        ))

        # --- GAP C8: packet timestamp is not sealed ---------------------------
        write_trace(declare_corpus=True, declare_commit=False)
        first = client.get(f"/evidence/{tid}").json()
        time.sleep(1.2)
        second = client.get(f"/evidence/{tid}").json()
        drifted = first.get("generated_at") != second.get("generated_at")
        has_packet_hash = "hash" in first or "packet_hash" in first
        gaps.append(_gap(
            "verify_packet_timestamp_not_sealed", "behavioural",
            "Chapter 25:117 says /verify returns 'the decision timestamp, sealed "
            "inside the hash'. GET the same packet twice ~1.2s apart and compare.",
            "identical generated_at, covered by a packet-level hash",
            (f"regenerated on every read: {first.get('generated_at')} vs "
             f"{second.get('generated_at')}; packet-level hash field present="
             f"{has_packet_hash}"),
            "GAP, NOT WAIVED. The implemented packet's generated_at is documented "
            "as 'the timestamp the packet was assembled' (evidence.py:71) and there "
            "is no packet-level hash field at all, so no timestamp is sealed by "
            "anything. Disposition: BOOK finding — Chapter 25:117 describes a "
            "property the implemented packet does not have. Chapter 25:198's "
            "design-only clause covers the CSB packet; it does not cover a claim "
            "about what the shipped /verify returns.",
            {"first_generated_at": first.get("generated_at"),
             "second_generated_at": second.get("generated_at"),
             "packet_top_level_keys": sorted(first.keys()),
             "drifted": drifted}, generated_at,
        ))

    finally:
        try:
            if trace_path.exists():
                trace_path.unlink()
        except OSError:
            pass
        shutil.rmtree(corpus_dir, ignore_errors=True)
        shutil.rmtree(outside_dir, ignore_errors=True)

    return cases, gaps, "ran"


# ---------------------------------------------------------------------------
# Section D — structural absence pins (behaviour is impossible here)
# ---------------------------------------------------------------------------


_RETENTION_PATTERNS = (
    "retention_days", "retain_until", "retainuntil", "objectlock",
    "object_lock", "purge_older", "delete_older", "expire_records",
    "rotate_evidence", "min_retention", "retention_policy", "worm_store",
)


def _scan_sources() -> list[tuple[Path, str]]:
    """Every cas-forex source file EXCEPT this script.

    Excluding self is mandatory: this file quotes the very tokens the absence
    scans look for, so a scan that included it would report its own text as a
    finding. The first run of this script did exactly that on two cases.
    """
    out: list[tuple[Path, str]] = []
    self_name = Path(__file__).name
    for sub in ("cas_forex", "api", "scripts"):
        base = CAS_FOREX_ROOT / sub
        if not base.is_dir():
            continue
        for py in sorted(base.rglob("*.py")):
            if py.name == self_name:
                continue
            try:
                out.append((py, py.read_text(encoding="utf-8", errors="ignore")))
            except OSError:
                continue
    return out


def section_d(generated_at: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    sources = _scan_sources()

    # --- D1 no retention construct anywhere in cas-forex --------------------
    hits: list[str] = []
    for py, raw in sources:
        text = raw.lower()
        for pat in _RETENTION_PATTERNS:
            if pat in text:
                hits.append(f"{py.relative_to(CAS_FOREX_ROOT)}::{pat}")
    cases.append(_case(
        "no_retention_construct_in_cas_forex", "retention_absence", "structural",
        "STRUCTURAL. Assert, rather than assume, that no expiry / purge / "
        "rotation / object-lock / retention-policy construct exists in "
        "cas-forex/{cas_forex,api,scripts}. This case FAILS the moment retention "
        "code is added or an unenforced window is declared — which is the point.",
        "zero hits", f"{len(hits)} hits", len(hits) == 0,
        {"patterns": list(_RETENTION_PATTERNS), "hits": hits[:20]}, generated_at,
    ))

    # --- D2 worm_retained is structurally False -----------------------------
    default_false = EvidenceReceipt.model_fields["worm_retained"].default is False
    true_assignments: list[str] = []
    for py, raw in sources:
        for i, line in enumerate(raw.splitlines(), 1):
            if "worm_retained=True" in line.replace(" ", ""):
                true_assignments.append(f"{py.relative_to(CAS_FOREX_ROOT)}:{i}")
    d2 = default_false and not true_assignments
    cases.append(_case(
        "worm_retained_is_structurally_false", "retention_absence", "structural",
        "STRUCTURAL. EvidenceReceipt.worm_retained must default to False and no "
        "`worm_retained=True` assignment may exist. This pins "
        "'WORM UNAVAILABLE' as a fact about the code, not a UI string.",
        "default False, zero True assignments",
        f"default_false={default_false} true_assignments={len(true_assignments)}",
        d2, {"anchor_scheme_default": EvidenceReceipt.model_fields["anchor_scheme"].default,
             "true_assignments": true_assignments}, generated_at,
    ))

    # --- D3 no Circuit Registry ---------------------------------------------
    reg_hits: list[str] = []
    for py, raw in sources:
        for token in ("CircuitRegistry", "circuit_registry", "ccdl_version"):
            if token in raw:
                reg_hits.append(f"{py.relative_to(CAS_FOREX_ROOT)}::{token}")
    cases.append(_case(
        "no_circuit_registry_implementation", "unimplemented_mechanism", "structural",
        "STRUCTURAL. Chapter 25:166-172 publishes a Circuit Registry that is "
        "'immutable and append-only — you add versions; you never overwrite or "
        "delete them'. Assert no CircuitRegistry / circuit_registry / ccdl_version "
        "symbol exists in cas-forex. Fails the day one is added, at which point "
        "the registry's retention property becomes behaviourally testable.",
        "zero hits", f"{len(reg_hits)} hits", len(reg_hits) == 0,
        {"hits": reg_hits[:20]}, generated_at,
    ))

    # --- D4 the Chapter 25 seven-field packet does not exist -----------------
    forex_fields = set(ForexEvidencePacket.model_fields)
    ch25_fields = {"input", "cas_trace", "test_points", "decision", "trace_id",
                   "ccdl_version", "hash"}
    forex_missing = sorted(ch25_fields - forex_fields)
    cases.append(_case(
        "ch25_seven_field_packet_unimplemented", "unimplemented_mechanism", "structural",
        "STRUCTURAL. Chapter 25:73-83 publishes a seven-field CSB Evidence Packet. "
        "Assert which of those fields ForexEvidencePacket actually has. Nothing in "
        "the repository emits an object carrying TP1-TP4 test_points, a decision, "
        "a ccdl_version and a packet-level hash, so the Chapter 25 packet cannot "
        "be exercised at all — not partially, not in simulation.",
        "6 of 7 fields absent (only trace_id present)",
        f"absent: {forex_missing}",
        forex_missing == sorted(ch25_fields - {"trace_id"}),
        {"forex_packet_fields": sorted(forex_fields),
         "chapter_25_fields": sorted(ch25_fields)}, generated_at,
    ))

    # --- D5 the receipt cannot be closed by local code ----------------------
    required = REQUIRED_EVIDENCE[PcbaProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM]
    local_keys = set(collect_local_pcba_evidence().keys())
    in_required = "audit_retention_proof_pass" in required
    not_local = "audit_retention_proof_pass" not in local_keys
    cases.append(_case(
        "receipt_not_self_certifiable", "authority", "structural",
        "STRUCTURAL. `audit_retention_proof_pass` must be a required key of the "
        "governance feature AND must NOT be a key `collect_local_pcba_evidence()` "
        "can ever return. No local run — including this one — can close it.",
        "required=true and locally-emittable=false",
        f"required={in_required} locally_emittable={not not_local}",
        in_required and not_local,
        {"required_evidence": required,
         "governance_keys_locally_emittable": sorted(
             set(required) & local_keys)}, generated_at,
    ))

    # --- D6 operator log has no integrity field -----------------------------
    from cas_forex.operator_audit import OperatorAuditEntry  # noqa: PLC0415

    entry_fields = set(OperatorAuditEntry.__dataclass_fields__)
    integrity_fields = {"hash", "entry_hash", "previous_hash",
                        "previous_entry_hash", "sequence", "event_seq"}
    has_verify = any(hasattr(OperatorAuditLog, m)
                     for m in ("verify", "verify_chain", "verify_log"))
    d6 = not (entry_fields & integrity_fields) and not has_verify
    cases.append(_case(
        "operator_log_has_no_integrity_mechanism", "integrity_absence", "structural",
        "STRUCTURAL companion to gaps B4-B6. Assert OperatorAuditEntry carries no "
        "hash / previous-hash / sequence field and OperatorAuditLog exposes no "
        "verify method — pinning the operator log as append-only by convention.",
        "no integrity field and no verify method",
        f"integrity_fields_present={sorted(entry_fields & integrity_fields)} "
        f"has_verify_method={has_verify}",
        d6, {"entry_fields": sorted(entry_fields)}, generated_at,
    ))

    return cases


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    text = "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_None._"
    out = ["| Case | Category | Kind | Expected | Observed | Passed |",
           "|---|---|---|---|---|---:|"]
    for r in rows:
        out.append(
            f"| `{r['case_id']}` | `{r['category']}` | `{r['measurement_kind']}` | "
            f"{r['expected']} | {r['observed']} | `{str(r['passed']).lower()}` |"
        )
    return "\n".join(out)


def main() -> int:
    generated_at = utc_now().isoformat()

    a_cases, a_gaps = section_a(generated_at)
    b_cases, b_gaps = section_b(generated_at)
    c_cases, c_gaps, c_status = section_c(generated_at)
    d_cases = section_d(generated_at)

    all_cases = a_cases + b_cases + c_cases + d_cases
    all_gaps = a_gaps + b_gaps + c_gaps
    real_gaps = [g for g in all_gaps if g["is_gap"]]

    passed = sum(1 for c in all_cases if c["passed"])
    failures = [c for c in all_cases if not c["passed"]]
    behavioural = [c for c in all_cases if c["measurement_kind"] == "behavioural"]
    structural = [c for c in all_cases if c["measurement_kind"] == "structural"]
    result = "PASS" if not failures else "FAIL"

    raw = WORKING_DIR / f"audit_retention_eval_raw_{DATE_TAG}.jsonl"
    raw_hash = _write_jsonl(raw, all_cases + all_gaps)

    report = WORKING_DIR / f"audit_retention_eval_report_{DATE_TAG}.md"

    gap_body = ""
    for g in real_gaps:
        gap_body += (
            f"### `{g['case_id']}`  ({g['measurement_kind']})\n\n"
            f"{g['description']}\n\n"
            f"- Hoped: {g['hoped']}\n"
            f"- **Observed: {g['observed']}**\n"
            f"- **Disposition:** {g['disposition']}\n\n"
        )
    if not real_gaps:
        gap_body = "None.\n\n"

    fail_body = ""
    if failures:
        for f in failures:
            fail_body += (f"- `{f['case_id']}` ({f['measurement_kind']}): expected "
                          f"{f['expected']}, observed {f['observed']}\n")
    else:
        fail_body = ("None. Every case listed above returned the expected result. "
                     "Note that the substantive findings of this run are the "
                     "unenforced properties below, not the case table.\n")

    body = f"""# Local Evidence-Chain Retention And Integrity Probe

Generated: `{generated_at}`
Reviewer identity: `{REVIEWER_ID}`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Target receipt: `governance_regulatory_proof_claim__audit_retention_proof_pass`
Receipt disposition after this run: **STAYS UNSIGNED.**
Result: `{result}`
Cases passed: `{passed}/{len(all_cases)}`  (behavioural `{len(behavioural)}`, structural `{len(structural)}`)
Unenforced properties found: `{len(real_gaps)}`
`/verify` section status: `{c_status}`

## What This Run Establishes

Three pieces of machinery were exercised on real files, real appends and real
HTTP calls:

1. **`cas-forex/cas_forex/evidence_store.py`** — the local hash-chained JSONL
   evidence store. Append-only ordering, unbroken back-links, cross-process
   persistence (verified in a second Python interpreter) and no-overwrite on
   duplicate identity all hold, measured. Content tamper, re-sealed tamper, tail
   truncation, mid-chain deletion, torn writes and either-file-alone deletion
   are all **detected**, measured. Every one of those positive results holds
   **only for a single writer**: concurrent appends corrupted the chain in every
   trial run (see `evstore_concurrent_writers_corrupt_chain`), which also means a
   `False` verdict from `verify_chain()` does not by itself imply tampering.
2. **`cas-forex/cas_forex/operator_audit.py`** — append and read work, and the
   advisory-phrase guard genuinely refuses an advisory summary while accepting a
   factual one. The log has **no integrity mechanism at all**.
3. **`noetic-compass-scaffold/noetic-compass/api/routes/evidence.py`** — the only
   implemented `/verify` in the repository. It genuinely detects deletion and
   tampering of *declared* artifacts.

## Out Of Scope, Deliberately

This run does **not** establish that audit records are retained. Read that
sentence as the limit on everything below it.

- **No retention window is enforced anywhere in `cas-forex`.** Not a short one,
  not a long one. A scan of `cas_forex/`, `api/` and `scripts/` for expiry,
  purge, rotation, object-lock and retention-policy constructs returns zero hits.
  The word `retention` appears in the codebase only as the receipt-key string in
  `pcba_readiness.py:141` and `cjt_readiness.py:60`. No retention window is
  stated in the book or in `cas-forex/docs/legal/` either — the privacy draft
  explicitly defers the retention schedule. The honest framing is therefore not
  "a documented window is unenforced"; it is that the book asserts *unbounded*
  retention and unsuppressible retrieval, and **no code anywhere enforces any
  retention property at all**.
- **The only retention-enforcing code in the repository is not here and is not
  a board.** `noetic-compass-scaffold/.../api/services/cas_harness_evidence_anchor.py`
  writes S3 Object Lock with `ObjectLockRetainUntilDate`. It exists on `master`
  and is **absent from this checkout** (`codex/cascompass-legal-live-source`); it
  belongs to the CAS Harness ML audit path, not to any CCB; and the enforcement
  is AWS's, not this repository's. It was not exercised: it needs boto3, live
  credentials, and a bucket with Object Lock enabled.
  `api/services/production/worm_writes.py` states in its own docstring that
  nothing in it is wired into the live app, and its stub store's `assert_ready`
  always raises. Testing it would measure a stub.
- **Chapter 25's seven-field Evidence Packet does not exist.** Nothing in the
  repository emits an object carrying TP1-TP4 `test_points`, a `decision`, a
  `ccdl_version` and a packet-level `hash`. It cannot be exercised at all — not
  partially, not in simulation — because the type does not exist. Any case
  claiming to test it would have to construct the object itself, which tests the
  test.
- **There is no decision-level `/verify`.** The implemented one verifies ML
  model-provenance artifacts (`weights`, `tokenizer`, `english_bpe`, `corpus`)
  for a CAS-Native generation trace.
- **There is no Circuit Registry.** Chapter 25:170-172's "you never overwrite or
  delete them" is untestable, as are the rollback / canary / version-pinning
  claims that depend on it.
- **"Every decision leaves a record" is untestable in the direction that
  matters.** The CSB has no runtime. You cannot show that no decision is dropped
  when no decision is ever made. Everything below tests the store's behaviour
  *given writes*, not that all decisions reach the store.
- **This receipt is external by classification.**
  `docs/working/cjt_ungating_external_gate_checklist_20260617.md:72` says the
  governance claim needs external legal/regulatory review and *audited* retention
  proof. "Audited" means a third party. No local run can supply that.
  `docs/working/pcba_owner_claim_review_20260725.md:67` already lists
  `audit_retention_proof_pass` as not signable by authorization. Nothing in this
  artifact changes that, and this artifact must not be described as proving that
  audit records are retained.

## Measurement Kinds

Every case is tagged. `behavioural` means a real run against real files or a
real HTTP client. `structural` means an absence or shape assertion over source
and models — it pins today's shape and is written to FAIL the day the
corresponding machinery is built. The two are never described as each other.
Section D is structural precisely because the machinery it asks about does not
exist to be run.

## Pass/Fail Thresholds

- Every negative control (tamper, deletion, truncation, advisory phrase) must be
  detected or refused.
- Every false-positive control (untouched store, honest entry, present artifact)
  must be accepted.
- Structural pins must hold exactly.
- The gap list below is **not** part of the pass count. Gaps are findings.
- `verify_code_commit_check_cannot_fail` is explicitly excluded from the pass
  count: it is a check that cannot fail, and counting it would be exactly the
  "engineered to pass" defect this eval exists to avoid.

## Case Corrections Made During This Run

The first execution of this script reported three failures. All three were
defects in the CASES, not findings about the code, and all three were corrected.
They are disclosed here rather than silently fixed:

1. `worm_retained_is_structurally_false` and `no_circuit_registry_implementation`
   scanned `cas-forex/scripts/` including this script itself, which quotes the
   very tokens it searches for (`worm_retained=True`, `CircuitRegistry`,
   `circuit_registry`, `ccdl_version`). The scans reported this file's own text
   as evidence. Fixed by excluding the running script from the source scan
   (`_scan_sources`). No production file matched either pattern before or after
   the fix.
2. `verify_declared_artifact_matches` declared a corpus in the system temp
   directory and got `match=false`, note `"path is outside allowed roots"`. That
   was not a verifier defect — the endpoint enforces a path allowlist restricted
   to the project and scaffold roots (`evidence.py:204`, `:233`). The fixture was
   moved inside an allowed root so the hash comparison is actually exercised, and
   the guard that caused the original failure was promoted to its own negative
   control, `verify_path_outside_allowed_roots_refused`. The eval is stronger
   after the correction, not weaker.

No case was weakened to make it pass, and no finding was reclassified.

## Section A — EvidenceStore (behavioural)

{_table(a_cases)}

## Section B — OperatorAuditLog (behavioural)

{_table(b_cases)}

## Section C — the implemented `/verify` (behavioural + one scope pin)

Status: `{c_status}`

{_table(c_cases)}

## Section D — structural absence pins

{_table(d_cases)}

## Failures Observed

{fail_body}
## Unenforced Properties

These are properties the book's prose leans on that the code does not enforce.
They are recorded as findings, never as passes, and none was closed by weakening
the probe.

{gap_body}## Book Findings

The following are defects in the BOOK, not in the code, and are recorded with
file and line:

- `book/CAS_PCBA_Engineer/Chapter_26_Governance.md:43` and `:75` — "They pull any
  decision the board ever made, by its trace ID" and "any trace ID, including one
  from a decision the vendor would rather not surface." Measured: a deleted trace
  and a trace that never existed return byte-identical responses. The
  unsuppressible-audit-trail claim is not backed by anything in the repository.
- `book/CAS_PCBA_Engineer/Chapter_25_Production_Deployment.md:105` — the Bench
  Note states as a rule "hash the packet at decision time, not at log time... A
  seal applied after the fact seals nothing." No code path obeys it; every
  `EvidenceStore.append` call site seals inside the persistence function.
- `book/CAS_PCBA_Engineer/Chapter_25_Production_Deployment.md:117` — "The
  decision timestamp, sealed inside the hash." Measured: `generated_at` is
  regenerated on every read and there is no packet-level hash field at all.
- `book/CAS_PCBA_Engineer/Chapter_26_Governance.md:53` and `:56` — Platinum
  requires "Every decision emits a `/verify`-able evidence packet" and "no
  evidence packets" is a Not-Certified condition. Nothing in the toolchain can
  apply either gate. Same class of defect as `csb_fuse_action_downgrade` in the
  CSB red-team report, and it should be dispositioned the same way: documented
  in-chapter as a manual check the toolchain does not perform.
- Omission, load-bearing for this receipt: the product UI already states "WORM
  Evidence Anchoring — UNAVAILABLE, local hash chain only"
  (`cas-forex/ui/src/pages/SettingsPage.tsx:477`) and `EvidenceReceipt` carries
  `worm_retained=False` / `anchor_scheme='local-jsonl-hash-chain'`. Neither
  Chapter 25 nor Chapter 26 tells the reader that the evidence trail is same-host
  storage with no durable retention. That is the single most important limit on
  the audit-retention claim, and it is currently unstated.

## Mitigations And Limits

- The allowed claim is exactly what was measured: the local evidence chain
  detects **edits**, not **erasure**.
- This evidence does not unlock live trading, does not create a broker `ACCEPT`
  path, and does not support any legal, regulatory, privacy or governance claim.
- Nothing here was fixed. This run measures. Every gap above is left standing
  with a disposition so the next phase can act on it.
- The correct outcome of this investigation is a gap report plus a narrowing of
  Chapter 26 — not a signed receipt.

## Raw Evidence

- Path: `docs\\working\\{raw.name}`
- SHA-256: `{raw_hash}`
- JSONL records: `{len(all_cases) + len(all_gaps)}` ({len(all_cases)} cases, {len(all_gaps)} gap probes)
"""
    report.write_text(body, encoding="utf-8", newline="\n")

    print(f"result             : {result}")
    print(f"cases              : {passed}/{len(all_cases)} "
          f"(behavioural {len(behavioural)}, structural {len(structural)})")
    print(f"unenforced found   : {len(real_gaps)}")
    print(f"/verify section    : {c_status}")
    for g in real_gaps:
        print(f"   GAP  {g['case_id']}: hoped {g['hoped']} | observed {g['observed'][:160]}")
    for f in failures:
        print(f"   FAIL {f['case_id']}: expected {f['expected']}, observed {f['observed']}")
    print(f"\nreport : {report}")
    print(f"raw    : {raw}")
    print(f"sha256 : {raw_hash}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
