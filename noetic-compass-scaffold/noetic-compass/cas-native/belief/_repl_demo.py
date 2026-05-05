"""REPL transcript demo for the CABS belief substrate.

This module exercises the same code paths the chat REPL uses when handling
``/beliefs``, ``/why <claim>``, and ``/forget <claim>``, but with a stubbed
predictor so the demo runs without a GPU checkpoint. Invoked as

    python cas-native/belief/_repl_demo.py

from the noetic-compass repo root. The output mirrors the BELIEF STATUS line
and command output produced by the live chat REPL.
"""

from __future__ import annotations

import sys
import tempfile
import types
from datetime import datetime, timedelta
from pathlib import Path


# Mirror chat.py's package indirection.
REPO_ROOT = Path(__file__).resolve().parents[2]
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_native.belief import BeliefStore  # noqa: E402


def _run(store: BeliefStore) -> int:
    base = datetime(2026, 5, 4, 12, 0, 0)

    # Lines 1-3: three observations of "practice makes perfect" -> ^7^O
    for i in range(3):
        b = store.record_observation(
            "practice makes perfect",
            "^7^O",
            evidence_strength=0.5,
            now=base + timedelta(minutes=i),
        )
        print(
            f"[{i + 1}] cas-native > practice makes perfect"
        )
        print(f"     BELIEF STATUS  {b.short_status()}")

    # Line 4: a different claim that won't lock yet
    b2 = store.record_observation(
        "drawn to it like a moth to a flame",
        "^2^P",
        evidence_strength=0.5,
        now=base + timedelta(minutes=5),
    )
    print("[4] cas-native > drawn to it like a moth to a flame")
    print(f"     BELIEF STATUS  {b2.short_status()}")

    # Line 5: /beliefs
    print("[5] cas-native > /beliefs")
    locked = store.list_locked()
    print(f"     Locked beliefs ({len(locked)}):")
    for b in locked:
        print(
            f"       ^4={b.vibration:.2f}  ^7={b.rhythm_count}  "
            f"{b.cas_expression}  {b.claim_text!r}"
        )

    # Line 6: /why practice makes perfect
    print("[6] cas-native > /why practice makes perfect")
    candidates = store.find_by_claim("practice makes perfect")
    for belief in candidates:
        explanation = store.explain(belief.claim_key)
        assert explanation is not None
        print(f"     status: {belief.short_status()}")
        print("     RPM stages:")
        for stage_name, info in explanation["rpm"].get("stages", {}).items():
            mark = "OK " if info.get("passed") else "BLK"
            print(f"       {mark} {stage_name}: {info.get('reason', '')}")
        print("     Inversion axes:")
        for axis, info in explanation["inversion"].items():
            mark = "OK " if info.get("clean") else "BLK"
            pl = " (placeholder)" if info.get("placeholder") else ""
            print(f"       {mark} {axis}{pl}: {info.get('reason', '')}")

    # Line 7: /forget practice makes perfect
    print("[7] cas-native > /forget practice makes perfect")
    matches = store.find_by_claim("practice makes perfect")
    for belief in matches:
        store.add_contradiction(
            belief.claim_text,
            belief.cas_expression,
            reason="/forget command issued by user",
            now=base + timedelta(minutes=10),
        )
    print(f"     recorded {len(matches)} contradiction(s); affected unlocked")

    # Line 8: /beliefs again -> should now be empty
    print("[8] cas-native > /beliefs")
    locked = store.list_locked()
    if not locked:
        print("     (no locked beliefs yet)")
    else:
        for b in locked:
            print(f"     {b.short_status()}  {b.claim_text!r}")

    # Line 9: /why on the contradicted claim shows axis N flag
    print("[9] cas-native > /why practice makes perfect")
    candidates = store.find_by_claim("practice makes perfect")
    for belief in candidates:
        print(f"     status: {belief.short_status()}")
        n_info = belief.inversion_scan_axes.get("N", {})
        print(
            f"     N-axis clean={n_info.get('clean')} "
            f"reason={n_info.get('reason', '')!r}"
        )

    # Line 10: /exit
    print("[10] cas-native > /exit")
    print("Goodbye.")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        db_path = Path(td) / "beliefs.db"
        store = BeliefStore(db_path)
        try:
            return _run(store)
        finally:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
