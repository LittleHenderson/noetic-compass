"""Continuation-bundle checker — byte-level, standard library only.

Preparation tooling for the neural-learning plan v1 (`docs/working/
helm_neural_learning_plan_v1_draft_2026_10_06.md` §2 and §6; roadmap §7.3).
A resumable episode is a *bundle*: a manifest naming every member the plan
requires (model state, bound identities, constraint rows, cursor and path
totals, admission and schema identities, optimizer / schedule / RNG state or an
explicit declaration of their absence, and the launch binding) with the
SHA-256 of each file. This tool answers three questions a restart claim needs
and nothing more:

    complete   does the bundle hold every required member, or declare its absence?
    verify     does every member on disk hash to what the manifest says?
    compare    are two bundles exact-equal member by member, and where not?

It never decodes a checkpoint, never loads a model, never runs inference. A
bundle that passes here is *consistent*; whether the model inside it learned
anything is the experiment's question, not this tool's. Exactness is byte
equality; there is no tolerance here by design.

Manifest format (JSON):

    {
      "bundle_version": "helm.bundle/1",
      "plan": {"id": "...", "version": "v1", "sha256": "..."},
      "binding": {"source_revision": "...", "seed": 0, "operator_record": "...", "approval": "..."},
      "members": {
        "model_state":   {"path": "endpoint.pt", "sha256": "..."},
        "optimizer_state": {"absent": "no optimizer: pure direction updates"},
        ...
      }
    }

Exit codes: 0 ok; 2 incomplete or mismatched; 3 unreadable input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

BUNDLE_VERSION = "helm.bundle/1"

#: Plan v1 §2: every member a restart claim is defined over. Each is either a
#: file with a digest or an explicit `absent` declaration.
REQUIRED_MEMBERS = (
    "model_state",
    "bound_identities",         # configuration, topology, decoder, semantic lineage
    "constraint_rows",          # original rows and controls
    "parameter_reference",      # the original parameter reference
    "cursor",                   # accepted/refused-step cursor
    "path_totals",              # cumulative, rounding, nominal
    "admission_identities",     # teaching admission and schema identities
    "optimizer_state",
    "schedule_state",
    "rng_state",
)
#: Members whose absence may be declared (plan v1 §2 item 6); every other
#: member must be a file.
DECLARABLE_ABSENT = ("optimizer_state", "schedule_state", "rng_state")
REQUIRED_BINDING = ("source_revision", "seed", "operator_record", "approval")


class BundleError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Finding:
    member: str
    kind: str          # missing | undeclared | unreadable | mismatch | extra | differs | only_in_a | only_in_b | absent_vs_present
    detail: str = ""


@dataclass
class Report:
    ok: bool
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "findings": [f.__dict__ for f in self.findings]}

    def render(self) -> str:
        if self.ok and not self.findings:
            return "ok"
        return "\n".join(f"{f.kind:<18} {f.member}: {f.detail}".rstrip() for f in self.findings) or ("ok" if self.ok else "failed")


def load_manifest(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise BundleError("E-BUNDLE-003", f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("bundle_version") != BUNDLE_VERSION:
        raise BundleError("E-BUNDLE-001", f"{path}: not a {BUNDLE_VERSION} manifest")
    if not isinstance(data.get("members"), dict):
        raise BundleError("E-BUNDLE-001", f"{path}: no members")
    return data


def complete(manifest: dict) -> Report:
    """Every required member present as a file or declared absent; binding present."""
    findings: list[Finding] = []
    members = manifest["members"]
    for name in REQUIRED_MEMBERS:
        entry = members.get(name)
        if entry is None:
            findings.append(Finding(name, "missing", "required member not in manifest"))
        elif "absent" in entry:
            if name not in DECLARABLE_ABSENT:
                findings.append(Finding(name, "undeclared", "this member may not be declared absent"))
            elif not str(entry["absent"]).strip():
                findings.append(Finding(name, "undeclared", "absence must say why"))
        elif "path" not in entry or "sha256" not in entry:
            findings.append(Finding(name, "missing", "entry needs path and sha256"))
    binding = manifest.get("binding") or {}
    for key in REQUIRED_BINDING:
        if key not in binding or binding[key] in (None, ""):
            findings.append(Finding(f"binding.{key}", "missing", "launch binding incomplete"))
    plan = manifest.get("plan") or {}
    if not plan.get("version") or not plan.get("sha256"):
        findings.append(Finding("plan", "missing", "the frozen plan version and its digest must be bound"))
    return Report(not findings, findings)


def verify(manifest: dict, root: Path) -> Report:
    """Every file member hashes to its recorded digest."""
    findings: list[Finding] = []
    for name, entry in manifest["members"].items():
        if "absent" in entry:
            continue
        path = root / entry.get("path", "")
        if not path.is_file():
            findings.append(Finding(name, "unreadable", f"{path} is not a file"))
            continue
        actual = sha256_file(path)
        if actual != entry.get("sha256"):
            findings.append(Finding(name, "mismatch", f"manifest {str(entry.get('sha256'))[:16]}… disk {actual[:16]}…"))
    return Report(not findings, findings)


def compare(a: dict, b: dict) -> Report:
    """Exact equality member by member, by recorded digest (verify each first)."""
    findings: list[Finding] = []
    names = sorted(set(a["members"]) | set(b["members"]))
    for name in names:
        ea, eb = a["members"].get(name), b["members"].get(name)
        if ea is None:
            findings.append(Finding(name, "only_in_b"))
        elif eb is None:
            findings.append(Finding(name, "only_in_a"))
        elif ("absent" in ea) != ("absent" in eb):
            findings.append(Finding(name, "absent_vs_present", "one bundle declares it absent, the other carries it"))
        elif "absent" in ea:
            continue
        elif ea.get("sha256") != eb.get("sha256"):
            findings.append(Finding(name, "differs", f"{str(ea.get('sha256'))[:16]}… vs {str(eb.get('sha256'))[:16]}…"))
    return Report(not findings, findings)


def build_manifest(root: Path, members: dict[str, str | None], *, plan: dict, binding: dict) -> dict:
    """Write a manifest for files under `root`; a None path declares absence (the value is the reason)."""
    out: dict = {"bundle_version": BUNDLE_VERSION, "plan": dict(plan), "binding": dict(binding), "members": {}}
    for name, spec in members.items():
        if isinstance(spec, tuple) and spec[0] is None:
            out["members"][name] = {"absent": spec[1]}
        elif spec is None:
            raise BundleError("E-BUNDLE-002", f"{name}: a None path needs a reason; pass (None, 'why')")
        else:
            out["members"][name] = {"path": spec, "sha256": sha256_file(root / spec)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="continuation-bundle checker (byte-level)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("complete"); c.add_argument("manifest")
    v = sub.add_parser("verify"); v.add_argument("manifest"); v.add_argument("--root", default=None)
    k = sub.add_parser("compare"); k.add_argument("manifest_a"); k.add_argument("manifest_b")
    k.add_argument("--root-a", default=None); k.add_argument("--root-b", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "complete":
            report = complete(load_manifest(Path(args.manifest)))
        elif args.cmd == "verify":
            m = Path(args.manifest)
            report = verify(load_manifest(m), Path(args.root) if args.root else m.parent)
        else:
            ma, mb = Path(args.manifest_a), Path(args.manifest_b)
            a, b = load_manifest(ma), load_manifest(mb)
            ra = verify(a, Path(args.root_a) if args.root_a else ma.parent)
            rb = verify(b, Path(args.root_b) if args.root_b else mb.parent)
            report = compare(a, b)
            report.findings = ra.findings + rb.findings + report.findings
            report.ok = report.ok and ra.ok and rb.ok
    except BundleError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(report.to_dict(), indent=1) if args.json else report.render())
    return 0 if report.ok else 2


if __name__ == "__main__":
    sys.exit(main())
