"""label_source_verifier.py -- deterministic gate on source claims (Phase 0C schema).

A model may quote a gloss, cite a sense id, name a frame, and propose a rule. This program
checks every such claim against the FROZEN resource and rejects anything it cannot verify
EXACTLY. The program, not the model, decides.

PHASE 0C schema repair: the Phase 0B evidence schema overloaded one field
(`frame_or_class`) with two meanings (source frame id vs proposed CAS class) and omitted
`sense_id` from the evidence block even though this verifier read it. Fixed: the evidence
block now carries SEPARATE fields, all REQUIRED and all verified:

    sense_id            -- the frozen sense identifier
    source_locator      -- "<resource_id>#<sense_id>"; must resolve to the cited sense
    exact_gloss         -- byte-identical quote of the frozen gloss
    source_frame_id     -- the resource's frame id (null only if the resource has none)
    proposed_cas_class  -- one of ^2/^3/^6/^8, or "NONE" (advisory only)
    proposed_rule_id    -- a rule id that EXISTS in the rule table, or "NONE" (advisory only)
    model_id            -- exact remote model identifier
    model_revision      -- exact model revision/version string
    model_role          -- one of the three allowed roles
    evidence_timestamp  -- when the evidence was produced
    resource_digest     -- the frozen resource digest the model was shown

Rejections: nonexistent sense ids; invented quotes; paraphrase-as-exact-quote
(normalized-equal but not byte-equal); locator that does not resolve to the cited sense;
mismatched frame ids; nonexistent proposed rule ids; disallowed model roles; incomplete
model identity receipts; missing required fields; conflicting mappings (same sense id ->
different class); duplicate senses in a resource; any source consulted after protected
results opened (freeze-time gate); resource digest mismatch.

Model proposals remain NON-authoritative in every case: a claim that VERIFIES is still only
evidence; it changes audit priority, never the label.

Returns a list of Finding(ok/rejected, reason, detail). CPU-only, deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent

REQUIRED_EVIDENCE_FIELDS = (
    "sense_id",
    "source_locator",
    "exact_gloss",
    "source_frame_id",
    "proposed_cas_class",
    "proposed_rule_id",
    "model_id",
    "model_revision",
    "model_role",
    "evidence_timestamp",
    "resource_digest",
)
ALLOWED_MODEL_ROLES = ("source_locator", "adversarial_critic", "counterexample_generator")


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
        self.resource_id = resource.get("resource_id")
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
                          rule_ids=None,
                          protected_opened: bool = False) -> list[Finding]:
    """Verify one model-produced evidence claim (Phase 0C schema, all fields required)."""
    findings: list[Finding] = []
    sid = claim.get("sense_id")

    # freeze-time gate: no source may be consulted after protected data is opened
    if protected_opened:
        findings.append(Finding(False, "freeze_time", "source consulted after protected results opened", sid or ""))
        return findings

    # required-field completeness (keys must be PRESENT; see docstring for null policy)
    missing = [f for f in REQUIRED_EVIDENCE_FIELDS if f not in claim]
    if missing:
        findings.append(Finding(False, "evidence_completeness", f"missing required fields: {missing}", sid or ""))
        return findings

    # resource digest: the frozen resource must be the manifest-frozen one, AND the model
    # must have been shown that same digest
    if frozen.digest != expected_resource_digest:
        findings.append(Finding(False, "resource_digest",
                                f"resource digest {frozen.digest[:12]} != expected {expected_resource_digest[:12]}", sid or ""))
        return findings
    if claim.get("resource_digest") != expected_resource_digest:
        findings.append(Finding(False, "resource_digest",
                                "claim's resource_digest does not match the frozen resource", sid or ""))
        return findings

    # sense id must exist
    if sid not in frozen.by_id:
        findings.append(Finding(False, "sense_exists", f"sense_id {sid!r} not in frozen resource", sid or ""))
        return findings
    rec = frozen.by_id[sid]

    # locator must RESOLVE to the cited sense (not just look plausible)
    expected_locator = f"{frozen.resource_id}#{sid}"
    if claim.get("source_locator") == expected_locator:
        findings.append(Finding(True, "locator_resolves", "locator resolves to the cited sense", sid))
    else:
        findings.append(Finding(False, "locator_resolves",
                                f"locator {claim.get('source_locator')!r} != {expected_locator!r}", sid))

    # exact quote check: byte-identical, with paraphrase-as-exact detection
    claimed = claim.get("exact_gloss")
    truth = rec.get("gloss", "")
    if claimed == truth:
        findings.append(Finding(True, "exact_quote", "gloss matches verbatim", sid))
    elif claimed is not None and LC.normalize_text(claimed) == LC.normalize_text(truth):
        findings.append(Finding(False, "exact_quote", "quote differs from frozen gloss (paraphrase presented as exact)", sid))
    else:
        findings.append(Finding(False, "exact_quote", "quoted gloss is not present verbatim (invented/altered)", sid))

    # source frame id must match the resource record (both may be null)
    if rec.get("frame") == claim.get("source_frame_id"):
        findings.append(Finding(True, "frame_match", "source_frame_id matches the frozen record", sid))
    else:
        findings.append(Finding(False, "frame_match",
                                f"claimed source_frame_id {claim.get('source_frame_id')!r} != frozen {rec.get('frame')!r}", sid))

    # proposed CAS class: advisory, but must be well-formed
    pcc = claim.get("proposed_cas_class")
    if pcc in LC.CAS_CLASSES or pcc == "NONE":
        findings.append(Finding(True, "proposed_cas_class", f"well-formed advisory class {pcc!r}", sid))
    else:
        findings.append(Finding(False, "proposed_cas_class", f"malformed proposed_cas_class {pcc!r}", sid))

    # proposed rule id: advisory, but must EXIST in the rule table (or be "NONE")
    prid = claim.get("proposed_rule_id")
    if rule_ids is not None:
        if prid == "NONE" or prid in set(rule_ids):
            findings.append(Finding(True, "proposed_rule_exists", f"advisory rule id {prid!r} exists", sid))
        else:
            findings.append(Finding(False, "proposed_rule_exists", f"proposed_rule_id {prid!r} not in rule table", sid))

    # model role allow-list
    if claim.get("model_role") in ALLOWED_MODEL_ROLES:
        findings.append(Finding(True, "model_role_allowed", f"role {claim.get('model_role')!r} allowed", sid))
    else:
        findings.append(Finding(False, "model_role_allowed", f"role {claim.get('model_role')!r} not allowed", sid))

    # model identity receipt completeness
    receipt_ok = all(isinstance(claim.get(f), str) and claim.get(f).strip()
                     for f in ("model_id", "model_revision", "evidence_timestamp"))
    if receipt_ok:
        findings.append(Finding(True, "model_identity_receipt", "model identity receipt complete", sid))
    else:
        findings.append(Finding(False, "model_identity_receipt",
                                "model_id / model_revision / evidence_timestamp incomplete", sid))

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
        findings.append(Finding(True, "claim_bearing_invariant", "every packet's claim_bearing matches its authority+approval state", ""))

    from collections import defaultdict
    classes_by_id = defaultdict(set)
    for p in packets:
        sense = p.get("sense") or {}
        sid = sense.get("sense_id")
        if p.get("authority") in ("RESOURCE_RULE_DERIVED", "RESOURCE_GOLD") and sid is not None:
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

    ap = argparse.ArgumentParser(description="Deterministic source verifier (Phase 0C schema).")
    ap.add_argument("--resource", default=str(HERE / "dev_resource" / "DEV_SENSE_RESOURCE_v1.yaml"))
    ap.add_argument("--packets", default=str(HERE / "reports" / "engine_packets.json"))
    args = ap.parse_args()
    frozen = FrozenResource.from_path(args.resource)
    print("resource digest:", frozen.digest)
    if Path(args.packets).exists():
        packets = LC.load_json(args.packets)
        for f in verify_packets(packets):
            print(("OK " if f.ok else "REJECT ") + f.check + ": " + f.detail)
