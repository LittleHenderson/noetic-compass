"""label_source_verifier.py -- deterministic gate on source claims.

A model may quote a gloss, cite a sense id, name a frame, and propose a rule. This program
checks every such claim against the FROZEN resource and rejects anything it cannot verify
EXACTLY. The program, not the model, decides. It rejects:

  - nonexistent sense ids
  - invented quotes (a quoted gloss that is not present verbatim in the frozen resource)
  - paraphrased text presented as an exact quote
  - mismatched frame ids
  - conflicting mappings (same sense id -> different class)
  - duplicate senses placed in different classes
  - any source used after the protected results were opened (freeze-time gate)

Returns a list of Finding(ok/rejected, reason, detail). CPU-only, deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent


@dataclass
class Finding:
    ok: bool
    check: str
    detail: str
    subject: str = ""

    def as_dict(self):
        return asdict(self)


class FrozenResource:
    """Indexes a frozen sense resource by sense_id for exact verification."""

    def __init__(self, resource: dict, digest: str):
        self.digest = digest
        self.by_id = {}
        for s in resource.get("senses", []):
            sid = s.get("sense_id")
            # duplicate sense_id inside one resource is itself invalid
            if sid in self.by_id:
                raise ValueError(f"duplicate sense_id in resource: {sid}")
            self.by_id[sid] = s

    @classmethod
    def from_path(cls, path):
        res = LC.load_yaml(path)
        return cls(res, LC.sha256_file(path))


def verify_evidence_claim(claim: dict, frozen: FrozenResource,
                          expected_resource_digest: str,
                          protected_opened: bool = False) -> list[Finding]:
    """Verify one model-produced evidence claim of the shape stored in packet['evidence'].

    claim keys (all optional except sense_id): sense_id, exact_gloss, frame_or_class,
    proposed_rule_id, source_locator, model_id, model_role.
    """
    findings: list[Finding] = []
    sid = claim.get("sense_id")

    # freeze-time gate: no source may be consulted after protected data is opened
    if protected_opened:
        findings.append(Finding(False, "freeze_time", "source consulted after protected results opened", sid or ""))
        return findings

    # resource digest must match the manifest-frozen digest
    if frozen.digest != expected_resource_digest:
        findings.append(Finding(False, "resource_digest",
                                f"resource digest {frozen.digest[:12]} != expected {expected_resource_digest[:12]}", sid or ""))
        return findings

    # sense id must exist
    if sid not in frozen.by_id:
        findings.append(Finding(False, "sense_exists", f"sense_id {sid!r} not in frozen resource", sid or ""))
        return findings

    rec = frozen.by_id[sid]

    # exact quote check: the claimed gloss must appear verbatim in the frozen gloss
    if "exact_gloss" in claim and claim["exact_gloss"] is not None:
        claimed = claim["exact_gloss"]
        truth = rec.get("gloss", "")
        if claimed == truth:
            findings.append(Finding(True, "exact_quote", "gloss matches verbatim", sid))
        elif LC.normalize_text(claimed) == LC.normalize_text(truth):
            # normalized-equal but not byte-equal = paraphrase-as-exact-quote
            findings.append(Finding(False, "exact_quote", "quote differs from frozen gloss (paraphrase presented as exact)", sid))
        else:
            findings.append(Finding(False, "exact_quote", "quoted gloss is not present verbatim (invented/altered)", sid))

    # frame check
    if "frame_or_class" in claim and claim["frame_or_class"] is not None:
        if rec.get("frame") == claim["frame_or_class"]:
            findings.append(Finding(True, "frame_match", "frame matches", sid))
        else:
            findings.append(Finding(False, "frame_match", f"claimed frame {claim['frame_or_class']!r} != frozen {rec.get('frame')!r}", sid))

    return findings


def verify_packets(packets: list[dict]) -> list[Finding]:
    """Integrity checks over packets: the claim_bearing invariant holds on every packet,
    and no sense id carries two different classes."""
    findings: list[Finding] = []

    # per-packet claim_bearing invariant (ingest guard, reported not raised)
    bad = 0
    for i, p in enumerate(packets):
        try:
            LC.validate_packet(p)
        except ValueError as e:
            bad += 1
            findings.append(Finding(False, "claim_bearing_invariant", str(e), p.get("packet_id", str(i))))
    if bad == 0:
        findings.append(Finding(True, "claim_bearing_invariant", "every packet's claim_bearing matches its authority", ""))

    from collections import defaultdict
    classes_by_id = defaultdict(set)
    for p in packets:
        sense = p.get("sense") or {}
        sid = sense.get("sense_id")
        if p.get("authority") == "RESOURCE_GOLD" and sid is not None:
            classes_by_id[sid].add(p.get("cas_label"))
    conflicts = {sid: labs for sid, labs in classes_by_id.items() if len(labs) > 1}
    if conflicts:
        for sid, labs in sorted(conflicts.items()):
            findings.append(Finding(False, "no_cross_class", f"sense {sid} mapped to multiple classes {sorted(labs)}", sid))
    else:
        findings.append(Finding(True, "no_cross_class", "no sense id maps to more than one class", ""))
    return findings


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Deterministic source verifier.")
    ap.add_argument("--resource", default=str(HERE / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"))
    ap.add_argument("--packets", default=str(HERE / "reports" / "engine_packets.json"))
    args = ap.parse_args()
    frozen = FrozenResource.from_path(args.resource)
    print("resource digest:", frozen.digest)
    if Path(args.packets).exists():
        packets = LC.load_json(args.packets)
        for f in verify_packets(packets):
            print(("OK " if f.ok else "REJECT ") + f.check + ": " + f.detail)
