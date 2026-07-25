"""Gate 2 item 8 — READ-ONLY fixture -> evidence-packet trace shim.

Roadmap item 8: "Replay the strongest saved Pythia/TKS fixtures through the current
live Evidence Packet path **without overwriting the historical record**."

The whole risk in item 8 is that a replay quietly becomes a rewrite. This module is
built so that cannot happen:

  * Fixtures are opened READ-ONLY. There is no write path to any fixture, ever.
  * The output is a DERIVED VIEW, never a restatement. Every transformation the shim
    performs -- every path rewrite, every field it had to choose -- is emitted as an
    explicit caveat, so a reader can tell what came from the fixture and what came
    from the shim.
  * Every claim-state string in the source fixture is copied VERBATIM into the
    caveats, with booleans rendered as their values (`false`), never as bare key
    names. A replay that silently dropped a `NOT_LICENSED` or an
    `execution_mode: SHADOW` would be laundering a claim, which is precisely the
    failure item 8 exists to prevent.
  * `claim_levels[].level` is constrained to the four locked values. The assessment
    found that inventing a fifth level would pass the server and break the UI, so the
    shim refuses rather than invents.

It replays evidence. It licenses nothing.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

LOCKED_CLAIM_LEVELS = (
    "cas_hard_trace",
    "source_copy_evidence",
    "derived_trace",
    "neural_attribution_estimate",
)

# Every field whose value is a claim-state assertion. Each MUST survive into caveats
# verbatim, or the replay would present a weaker-than-original claim as clean.
CLAIM_STATE_FIELDS = (
    "licensing_status", "claim_status", "execution_mode", "verdict", "verdict_influence",
    "claim_eligible", "official_pass_authorized", "maximum_producer_status",
    "cryptographic_model_origin_proven", "external_reproduction_verified",
    "status", "reserved_interpretation", "receiver_status", "technical_only_notice",
    "mathematical_consistency_verified", "rfc3161_protocol_anchor_verified",
    "provider_state_cryptographically_authenticated",
)

PINNED_MODEL = "EleutherAI/pythia-160m"
PINNED_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"


class ReplayRefusal(RuntimeError):
    """Raised when a fixture cannot be replayed without inventing something.

    A refusal is NOT a failed replay. It means the shim declined to fabricate a field
    it had no source for, which is the correct behaviour.
    """


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _walk_claim_states(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Collect every claim-state field anywhere in the fixture, at any depth."""
    found: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if k in CLAIM_STATE_FIELDS and not isinstance(v, (dict, list)):
                found.append((path, v))
            else:
                found.extend(_walk_claim_states(v, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_walk_claim_states(v, f"{prefix}[{i}]"))
    return found


def _render(value: Any) -> str:
    """Booleans render as their VALUE, never as a bare key name."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_trace(
    *, fixture_path: Path, path_rewrites: dict[str, str] | None = None,
    claim_level: str = "source_copy_evidence",
) -> dict[str, Any]:
    """Map ONE fixture to an evidence_packet.v1-shaped trace dict. Read-only."""
    if claim_level not in LOCKED_CLAIM_LEVELS:
        raise ReplayRefusal(
            f"claim_level {claim_level!r} is not one of the four locked values "
            f"{LOCKED_CLAIM_LEVELS}. The shim refuses to invent a fifth level: it would "
            "pass the server and break the UI."
        )
    raw = fixture_path.read_bytes()          # READ ONLY. No write path exists here.
    fixture = json.loads(raw.decode("utf-8"))

    caveats: list[str] = []

    # 1. Every claim-state string, verbatim.
    states = _walk_claim_states(fixture)
    if not states:
        caveats.append(
            "SOURCE FIXTURE CARRIES NO CLAIM-STATE FIELD. Absence of a claim state is not "
            "a licence; this replay asserts nothing about the fixture's standing."
        )
    for path, value in sorted(states):
        caveats.append(f"source claim state (verbatim): {path} = {_render(value)}")

    # 2. Schema version of the source.
    schema = fixture.get("schema_version")
    caveats.append(f"source schema_version: {schema if schema else 'unavailable'}")

    # 3. Model identity — from the fixture's own provenance where present.
    prov = fixture.get("provenance") or {}
    model_id = prov.get("model_id") or fixture.get("model") or PINNED_MODEL
    caveats.append(f"model revision pinned by the shim: {PINNED_REVISION}")
    if not (prov.get("model_id") or fixture.get("model")):
        caveats.append(
            f"SHIM CHOICE: the fixture named no model, so model_checkpoint_id was set to "
            f"{PINNED_MODEL} by the shim. This is an editorial act, not a fixture fact."
        )

    # 4. Path rewrites — every one disclosed.
    for old, new in (path_rewrites or {}).items():
        caveats.append(f"PATH REWRITTEN BY SHIM: {old} -> {new} (pod path remapped to local recovery)")

    # 5. Provenance of the replay itself.
    caveats.append(f"source fixture sha256: {sha256_file(fixture_path)}")
    caveats.append(f"source fixture path: {str(fixture_path).replace(chr(92), '/')}")
    caveats.append(
        "This trace is a DERIVED VIEW produced by item8_fixture_to_evidence_packet_shim.py. "
        "It is not a restatement of the original and it upgrades no claim."
    )

    return {
        "schema_version": "evidence_packet_trace.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "model_checkpoint_id": model_id,
            "model_revision": PINNED_REVISION,
            "source_fixture": str(fixture_path).replace("\\", "/"),
            "source_fixture_sha256": sha256_file(fixture_path),
            "source_schema_version": schema,
        },
        "claim_levels": [{"level": claim_level,
                          "why": "A replayed historical fixture is source-copy evidence: the numbers are "
                                 "real and were measured, but this path re-presents them rather than "
                                 "re-deriving them."}],
        "caveats": caveats,
        "replayed_payload": fixture,
        "licenses_nothing": (
            "Replaying a fixture through the live path demonstrates the PATH works. It revives no "
            "verdict, and any withdrawn claim in the payload stays withdrawn."
        ),
    }


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True,
                    help="MUST be under docs/working/gate2_closure/ or a scratch dir. "
                         "The shim refuses to write anywhere near a tracked historical record.")
    ap.add_argument("--claim-level", default="source_copy_evidence", choices=LOCKED_CLAIM_LEVELS)
    args = ap.parse_args()

    out = args.output.resolve()
    safe = ("gate2_closure" in out.as_posix()) or ("Temp" in out.as_posix()) or ("tmp" in out.as_posix())
    if not safe:
        raise ReplayRefusal(
            f"REFUSING to write to {out}. Output must be under gate2_closure/ or a scratch dir; "
            "item 8's whole point is that the historical record is not overwritten."
        )
    trace = build_trace(fixture_path=args.fixture, claim_level=args.claim_level)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2, sort_keys=True), encoding="utf-8")
    print(f"replayed {args.fixture.name} -> {out.name}")
    print(f"  claim_level : {trace['claim_levels'][0]['level']}")
    print(f"  caveats     : {len(trace['caveats'])}")
    for c in trace["caveats"]:
        if c.startswith("source claim state"):
            print(f"    {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
