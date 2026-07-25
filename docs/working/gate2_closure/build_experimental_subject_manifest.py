"""Roadmap Gate-2 item 5 — preserve the semantic subjects as DISTINCT subjects.

Item 5 verbatim (`CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:207-208`):

    "Preserve native TKS `A1-D10`, normalized indices, source hashes,
     crosswalks, and the D3DA/A124 semantic versions as distinct experimental
     subjects."

WHY THIS MATTERS, in one sentence: `D3DA` and `A124` are not names, they are the
first four hex digits of the sha256 of two DIFFERENT definition payloads
(`D3DAC0EF…` = the owner's raw workspace wording, `A124302E…` = the deployed
protected wording). The registry's own `controlling_principle 3` holds that
byte-different payloads are DIFFERENT semantic versions until a transformation
manifest proves otherwise, and no such manifest exists on disk. So any artifact,
result, or claim that silently merges them has merged two subjects.

This script does three things and asserts rather than assumes:

 1. RE-HASHES every registry source from disk and compares to the recorded
    sha256. A subject whose bytes have drifted is no longer the subject that was
    signed, and the manifest says so loudly instead of carrying a stale hash.
 2. EMITS one subject record per distinct semantic object, each with its own
    identity, hash, precedence and role — plus an explicit `must_not_conflate`
    list naming the subjects it is most likely to be confused with.
 3. RECORDS what is genuinely missing (`unavailable`) rather than papering over
    it — notably the TKS<->CAS crosswalk, which `required_run_bindings[6]`
    demands and which does not exist.

It writes a manifest and makes no claim. Preserving subjects is bookkeeping; it
licenses nothing.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

REGISTRY = "docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json"

# Subjects that are routinely confused with one another. Naming the confusion
# pairs explicitly is the whole point of item 5.
NON_CONFLATION = {
    "owner_raw_40_28_workspace": [
        "owner_deployed_40_28_protected — byte-different payload; a DIFFERENT semantic version "
        "(registry controlling_principle 3), not a reformatting of the same one",
    ],
    "owner_deployed_40_28_protected": [
        "owner_raw_40_28_workspace — see above; the A-vs-B comparison is between two versions, and "
        "no post-hoc 'it is just normalization' claim may be made without an owner-adjudicated "
        "transformation diff (registry known_conflict 2), which does not exist",
    ],
    "normalized_elements_40": [
        "owner_raw_40_28_workspace — the normalized canon is on the A0..D9 index while the owner "
        "sources are on A1..D10; future_agent_rule 2 FORBIDS remapping by position without a tested "
        "crosswalk",
    ],
    "normalized_subfoundations_28_defs": [
        "the 28 CAS Drive-by-Register entries — native F28 and CAS Drive-by-Register are separate "
        "subjects per the roadmap item 3 binding list",
    ],
}


def sha256_file(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def build(repo_root: Path) -> dict[str, Any]:
    reg_path = repo_root / REGISTRY
    reg = json.loads(reg_path.read_text(encoding="utf-8"))

    subjects: list[dict[str, Any]] = []
    drifted, missing = [], []
    for src in reg.get("sources", []):
        sid = str(src.get("id"))
        recorded = str(src.get("sha256") or "").lower()
        path = Path(str(src.get("path") or ""))
        actual = sha256_file(path)
        if actual is None:
            state = "unavailable_file_not_readable"
            missing.append(sid)
        elif recorded and actual.lower() != recorded:
            state = "DRIFTED_bytes_differ_from_signed_hash"
            drifted.append(sid)
        else:
            state = "verified_matches_signed_hash"
        subjects.append({
            "subject_id": sid,
            "role": src.get("role"),
            "precedence": src.get("precedence"),
            "path": str(path),
            "recorded_sha256": recorded or None,
            "recomputed_sha256": actual,
            "semantic_version_tag": (recorded[:4].upper() if recorded else None),
            "integrity": state,
            "must_not_conflate_with": NON_CONFLATION.get(sid, []),
        })

    crosswalk_binding = None
    for b in reg.get("required_run_bindings", []):
        if "crosswalk" in json.dumps(b).lower():
            crosswalk_binding = b
            break

    return {
        "schema_version": "cas_harness_experimental_subject_manifest.v1",
        "roadmap_item": "Gate 2 item 5 (CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:207-208)",
        "created_at": datetime.now(UTC).isoformat(),
        "registry_path": REGISTRY,
        "registry_sha256": sha256_file(reg_path),
        "registry_status": reg.get("status"),
        "subject_count": len(subjects),
        "subjects": subjects,
        "integrity_summary": {
            "verified": sum(1 for s in subjects if s["integrity"].startswith("verified")),
            "drifted": drifted,
            "unavailable": missing,
        },
        "semantic_versions": {
            "D3DA": "owner_raw_40_28_workspace — owner's raw workspace wording",
            "A124": "owner_deployed_40_28_protected — deployed protected wording",
            "rule": (
                "These are sha256 PREFIXES of two byte-different payloads, not two names for one "
                "thing. Registry controlling_principle 3: byte-different payloads are different "
                "semantic versions until a transformation manifest proves otherwise. No such "
                "manifest exists on disk, so they must be carried as two subjects everywhere."
            ),
        },
        "crosswalks": {
            "tks_to_cas_crosswalk": "unavailable — no crosswalk artifact exists on disk",
            "required_by": crosswalk_binding or "required_run_bindings entry naming tks_to_cas_crosswalk_sha256",
            "consequence": (
                "Any experiment needing A1..D10 <-> A0..D9 is blocked at the registry level, not "
                "merely inconvenienced: future_agent_rule 2 forbids remapping by position without a "
                "TESTED crosswalk. A proposal exists at "
                "docs/working/gate2_closure/item4_arms/proposed_tks_cas_crosswalk.json but is "
                "UNRATIFIED and its own owner_ratification block is unanswered."
            ),
        },
        "index_systems": {
            "A1..D10": "owner sources (raw + deployed)",
            "A0..D9": "normalized canon (elements/subfoundations/index)",
            "rule": "Never remap by position. future_agent_rule 2, registry known_conflict 1 (P0_SEMANTIC_IDENTITY).",
        },
        "licenses_nothing": (
            "This manifest is bookkeeping. Preserving subjects distinctly prevents a class of "
            "silent error; it does not support any empirical claim."
        ),
    }


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    m = build(args.repo_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")
    s = m["integrity_summary"]
    print(f"subjects: {m['subject_count']}  verified: {s['verified']}  drifted: {len(s['drifted'])}  unavailable: {len(s['unavailable'])}")
    for sid in s["drifted"]:
        print(f"  DRIFTED: {sid}")
    for sid in s["unavailable"]:
        print(f"  unavailable: {sid}")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
