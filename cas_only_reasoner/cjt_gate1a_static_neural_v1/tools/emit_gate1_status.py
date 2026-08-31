"""emit_gate1_status.py -- the COMMITTED deterministic Gate 1 status authority.

GATE1_THRESHOLDS_v3 (owner audit 2026-08-31 section 4). Three repairs over v2:

1. STRICT EVIDENCE VALIDATION. The program validates raw results against
   RAW_GATE1_RESULTS.schema.json's constraints with its own dependency-free
   validator and REFUSES malformed or contradictory evidence
   (STATUS_INPUT_INVALID) -- exactly 1000 unique ordered protected ids, exactly
   arms S0-S7, exactly seeds 11/23/47, every correctness vector exactly 1000
   integer 0/1 entries, one identical passage-order digest across all arms,
   finite claim-A fractions, B0/B1 present, no extra fields anywhere.

2. ALL-CONTROLS LICENSE LAW. The auxiliary-value claim (renamed from "Claim B /
   CAS-specific" under owner PATH A) is licensed ONLY if S3 clears the frozen
   margin + bootstrap-CI + 3/3-seed gates against EVERY control: S0, S1, S2,
   S4, S5, S6, AND S7. The v2 program could license while S3 lost to the plain,
   attention-only, and profile-only arms; that exact counterexample is now a
   permanent failing fixture in test_status_fixtures.py.

3. SURFACE BASELINES CONSUMED. B0 (class-blind floor) and B1 (full surface
   parser -- the TASK CEILING) are required inputs; the program labels question
   types where B0 is near ceiling and always reports B1 as the ceiling row.

v4 (GATE 1A.2 section 10) adds the EVIDENCE-CHAIN GATE: the raw results must
carry the complete evidence chain (schema RAW_GATE1_RESULTS_v2), and this
program validates it -- field formats, checkpoint/job key sets against the
frozen arm x seed grid, receipt-file digests under --evidence-root, baseline
arithmetic (overall == correct/total; per-question sums; the exact question-
type set) -- BEFORE reading any accuracy or correctness vector. A well-shaped
but unbound result file is refused (EVIDENCE_UNBOUND), never scored. Mode law:
--conformance requires a TEST- owner key id and replaces every claim status
with SOFTWARE_CONFORMANCE_ONLY; WITHOUT --conformance a TEST- key id is
refused outright, so a synthetic campaign can never receive a scientific
status.

Deterministic bootstrap (frozen procedure): indices come from the SHA-256
counter stream domain "GATE1_BOOT|<seed>|<control-arm>", read as consecutive
big-endian 16-bit integers v, REJECTING v >= 65000 and mapping accepted v to
v % 1000 (65000 = (2^16 // 1000) * 1000, so the mapping is exactly uniform --
no modulo bias). Pure integer arithmetic; identical on every CPython >= 3.8.
No wall-clock anywhere. boot_n is overridable ONLY by test fixtures; the CLI
always runs the frozen default 10000.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys

SEEDS = ("11", "23", "47")
ARMS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7")
CONTROLS = ("S0", "S1", "S2", "S4", "S5", "S6", "S7")   # ALL of them (v3 law)
N_PROTECTED = 1000
MARGIN = 0.03
BOOT_N = 10000
BOOT_SEED = 20260831
CLAIM_A_MIN = 0.80
CLAIM_A_MARGIN = 0.15
B0_NEAR_CEILING = 0.95

LICENSED = "TASK_ALIGNED_LABEL_AUXILIARY_VALUE_LICENSED"

HONEST_CEILING_DISCLOSURES = [
    "the CAS stream is informationally redundant given the text by construction "
    "(the labels are regex-recoverable from the clauses); any S3 gain is an "
    "optimization/bottleneck effect of the frozen encoder, never new information",
    "no task-aligned non-CAS taxonomy exists on this dataset because the answer "
    "function is defined over the CAS classes; S7 is ONE alternative taxonomy "
    "(not an equally task-aligned control), so the words 'CAS-specific' are "
    "PROHIBITED on this dataset regardless of result -- see "
    "GATE1A_SCOPE_AND_CLAIM_BOUNDARY.md",
    "the task is exactly surface-solvable: B1 (the full surface parser) is the "
    "task ceiling; a positive result means task-aligned labels helped a frozen "
    "encoder reach a surface-computable function",
]


QTYPE_SET = {"Q_ATTRACT", "Q_AVERT", "Q_PART", "Q_TRIGGER"}

EVIDENCE_HEX64 = ("execution_approval_sha256", "container_prep_receipt_sha256",
                  "model_weight_manifest_sha256", "tokenizer_manifest_sha256",
                  "dependency_lock_sha256", "dataset_manifest_sha256",
                  "s7_control_table_sha256", "run_schedule_sha256",
                  "selected_layer_receipt_sha256", "protected_lock_receipt_sha256",
                  "protected_evaluation_receipt_sha256",
                  "surface_baseline_receipt_sha256", "campaign_receipt_sha256")
EVIDENCE_KEYS = frozenset(list(EVIDENCE_HEX64) + [
    "package_commit_sha", "owner_key_id", "model_revision_sha",
    "container_image_digest", "cache_manifest_sha256s", "checkpoint_sha256s",
    "job_receipt_sha256s", "protected_campaign_id"])

# receipt files hashed against the chain when --evidence-root is given
EVIDENCE_FILES = (("execution_approval_sha256", "execution_approval.json"),
                  ("container_prep_receipt_sha256", "container_prep_receipt.json"),
                  ("dataset_manifest_sha256", "dataset_manifest.json"),
                  ("run_schedule_sha256", "run_schedule.json"),
                  ("selected_layer_receipt_sha256", "selected_layer_receipt.json"),
                  ("protected_lock_receipt_sha256", "protected_lock_receipt.json"),
                  ("protected_evaluation_receipt_sha256",
                   "protected_evaluation_receipt.json"),
                  ("surface_baseline_receipt_sha256", "surface_baseline_receipt.json"),
                  ("campaign_receipt_sha256", "campaign_pre_receipt.json"))


class StatusInputInvalid(ValueError):
    pass


class EvidenceUnbound(ValueError):
    pass


def _fail(msg):
    raise StatusInputInvalid(f"STATUS_INPUT_INVALID: {msg}")


def _efail(msg):
    raise EvidenceUnbound(f"EVIDENCE_UNBOUND: {msg}")


def _is_hex(s, n):
    return isinstance(s, str) and len(s) == n and \
        all(c in "0123456789abcdef" for c in s)


def validate_evidence(results, evidence_root, conformance: bool):
    """The provenance gate: runs BEFORE any metric is read. Raises
    EvidenceUnbound on any missing, malformed, or mismatched binding."""
    import hashlib
    from pathlib import Path
    if not isinstance(results, dict) or "evidence_chain" not in results:
        _efail("results carry no evidence_chain; a well-shaped but unbound "
               "result file never receives a scientific status")
    ec = results["evidence_chain"]
    if not isinstance(ec, dict) or set(ec) != EVIDENCE_KEYS:
        missing = sorted(EVIDENCE_KEYS - set(ec)) if isinstance(ec, dict) else "-"
        _efail(f"evidence_chain key set mismatch (missing {missing})")
    if not _is_hex(ec["package_commit_sha"], 40):
        _efail("package_commit_sha malformed")
    if not _is_hex(ec["model_revision_sha"], 40):
        _efail("model_revision_sha malformed")
    for f in EVIDENCE_HEX64:
        if not _is_hex(ec[f], 64):
            _efail(f"{f} malformed or placeholder: {ec[f]!r}")
    if not (isinstance(ec["container_image_digest"], str)
            and ec["container_image_digest"].startswith("sha256:")
            and _is_hex(ec["container_image_digest"][7:], 64)):
        _efail("container_image_digest malformed")
    key_id = ec["owner_key_id"]
    if not isinstance(key_id, str) or len(key_id) < 4:
        _efail("owner_key_id malformed")
    if conformance and not key_id.startswith("TEST-"):
        _efail("conformance mode requires a TEST- key id")
    if not conformance and key_id.startswith("TEST-"):
        _efail("a TEST- key id can never receive a scientific status; "
               "run --conformance or use an owner-pinned key")
    expected_keys = {f"{a}_seed{s}" for a in ARMS for s in SEEDS}
    for map_field in ("checkpoint_sha256s", "job_receipt_sha256s"):
        m = ec[map_field]
        if not isinstance(m, dict) or set(m) != expected_keys:
            _efail(f"{map_field} keys must be exactly the scheduled arm x seed "
                   f"grid ({len(expected_keys)} keys)")
        for k, v in m.items():
            if not _is_hex(v, 64):
                _efail(f"{map_field}[{k}] malformed")
    cm = ec["cache_manifest_sha256s"]
    if not isinstance(cm, dict) or not cm \
            or not all(_is_hex(v, 64) for v in cm.values()):
        _efail("cache_manifest_sha256s malformed")
    if evidence_root is None:
        _efail("no --evidence-root given: receipt files cannot be verified, "
               "so the results are UNBOUND")
    root = Path(evidence_root)
    for field, fname in EVIDENCE_FILES:
        f = root / fname
        if not f.is_file():
            _efail(f"receipt file missing: {fname}")
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        if got != ec[field]:
            _efail(f"{fname} sha {got[:16]}... != chain {ec[field][:16]}...")
    for k, want in sorted(ec["job_receipt_sha256s"].items()):
        f = root / "receipts" / f"run_{k}.json"
        if not f.is_file():
            _efail(f"job receipt missing: receipts/run_{k}.json")
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        if got != want:
            _efail(f"job receipt run_{k}.json digest mismatch")
    return True


def _is_binary_int(x):
    return type(x) is int and x in (0, 1)               # bool is NOT accepted


def _is_fraction(x):
    return type(x) in (int, float) and not isinstance(x, bool) \
        and math.isfinite(x) and 0.0 <= x <= 1.0


def _check_baseline(node, path):
    if not isinstance(node, dict) or set(node) != {"overall", "correct", "total",
                                                   "per_question_type"}:
        _fail(f"{path} must have exactly overall/correct/total/per_question_type")
    if not _is_fraction(node["overall"]):
        _fail(f"{path}.overall not a finite fraction")
    if type(node["correct"]) is not int or type(node["total"]) is not int \
            or node["total"] < 1 or not 0 <= node["correct"] <= node["total"]:
        _fail(f"{path} correct/total invalid")
    # ARITHMETIC LAW (v4): the stated fractions must EQUAL correct/total, the
    # per-question rows must sum to the split totals, and the question-type set
    # must be exactly the four registered types -- inconsistent arithmetic is
    # fabricated evidence, refused
    if node["overall"] != node["correct"] / node["total"]:
        _fail(f"{path}.overall != correct/total (inconsistent arithmetic)")
    if set(node["per_question_type"]) != QTYPE_SET:
        _fail(f"{path} question-type set != the four registered types")
    qc = qn = 0
    for qt, q in node["per_question_type"].items():
        if not isinstance(q, dict) or set(q) != {"accuracy", "correct", "total"} \
                or not _is_fraction(q["accuracy"]):
            _fail(f"{path}.per_question_type[{qt}] invalid")
        if type(q["correct"]) is not int or type(q["total"]) is not int \
                or q["total"] < 1 or q["accuracy"] != q["correct"] / q["total"]:
            _fail(f"{path}.per_question_type[{qt}] inconsistent arithmetic")
        qc += q["correct"]; qn += q["total"]
    if qc != node["correct"] or qn != node["total"]:
        _fail(f"{path} per-question totals do not sum to the split totals")


def validate(results):
    """The executable form of RAW_GATE1_RESULTS.schema.json. Raises on ANY defect."""
    if not isinstance(results, dict):
        _fail("top level is not an object")
    if set(results) != {"schema", "evidence_chain", "protected_passage_ids",
                        "arms", "claim_a", "surface_baselines"}:
        _fail(f"top-level keys must be exactly the six registered ones; got "
              f"{sorted(results) if isinstance(results, dict) else type(results)}")
    if results["schema"] != "RAW_GATE1_RESULTS_v2":
        _fail("schema field mismatch")
    ids = results["protected_passage_ids"]
    if not isinstance(ids, list) or len(ids) != N_PROTECTED:
        _fail(f"protected_passage_ids must be exactly {N_PROTECTED} ids")
    import re as _re
    if len(set(ids)) != N_PROTECTED or ids != sorted(ids) \
            or not all(isinstance(i, str) and _re.match(r"^p[0-9]{6}$", i)
                       for i in ids):
        _fail("protected ids must be unique, pattern p######, and in strictly "
              "ascending (frozen generation) order")
    order_digest = hashlib.sha256(
        json.dumps(ids, separators=(",", ":")).encode("utf-8")).hexdigest()
    arms = results["arms"]
    if not isinstance(arms, dict) or set(arms) != set(ARMS):
        _fail(f"arms must be exactly {ARMS}")
    for a in ARMS:
        node = arms[a]
        if not isinstance(node, dict) or set(node) != {"per_seed_correct",
                                                       "passage_order_digest"}:
            _fail(f"arm {a} must have exactly per_seed_correct + passage_order_digest")
        if node["passage_order_digest"] != order_digest:
            _fail(f"arm {a} passage_order_digest does not bind the frozen id order")
        psc = node["per_seed_correct"]
        if not isinstance(psc, dict) or set(psc) != set(SEEDS):
            _fail(f"arm {a} seeds must be exactly {SEEDS}")
        for s in SEEDS:
            vec = psc[s]
            if not isinstance(vec, list) or len(vec) != N_PROTECTED:
                _fail(f"arm {a} seed {s} vector must have exactly {N_PROTECTED} entries")
            if not all(_is_binary_int(v) for v in vec):
                _fail(f"arm {a} seed {s} entries must be exactly integer 0 or 1")
    ca = results["claim_a"]
    if not isinstance(ca, dict) or set(ca) != {"probe_protected_accuracy",
                                               "shuffled_control_accuracy"}:
        _fail("claim_a must have exactly its two registered fields")
    for k, v in ca.items():
        if not _is_fraction(v):
            _fail(f"claim_a.{k} must be a finite fraction in [0, 1]")
    sb = results["surface_baselines"]
    if not isinstance(sb, dict) or set(sb) != {"train", "val", "protected"}:
        _fail("surface_baselines must cover exactly train/val/protected")
    for split, node in sb.items():
        if not isinstance(node, dict) or set(node) != {"B0", "B1"}:
            _fail(f"surface_baselines.{split} must have exactly B0 and B1")
        _check_baseline(node["B0"], f"surface_baselines.{split}.B0")
        _check_baseline(node["B1"], f"surface_baselines.{split}.B1")


class _BootStream:
    """Frozen bootstrap index stream (see module docstring for the exact law)."""

    def __init__(self, control_arm: str):
        self._domain = f"GATE1_BOOT|{BOOT_SEED}|{control_arm}".encode("utf-8")
        self._counter = 0
        self._buf = b""
        self._pos = 0
        self._limit = (65536 // N_PROTECTED) * N_PROTECTED   # 65000: exact-uniform

    def index(self) -> int:
        while True:
            if self._pos + 2 > len(self._buf):
                self._buf = hashlib.sha256(
                    self._domain + b"|" + str(self._counter).encode("ascii")).digest()
                self._counter += 1
                self._pos = 0
            v = (self._buf[self._pos] << 8) | self._buf[self._pos + 1]
            self._pos += 2
            if v < self._limit:
                return v % N_PROTECTED


def per_passage_scores(arm):
    vecs = [arm["per_seed_correct"][s] for s in SEEDS]
    n = len(vecs[0])
    return [(vecs[0][i] + vecs[1][i] + vecs[2][i]) / 3.0 for i in range(n)]


def mean(xs):
    return sum(xs) / len(xs)


def gate(s3, ctrl, ctrl_name, boot_n):
    """One hard gate: margin + bootstrap CI + per-seed 3/3 consistency."""
    a, b = per_passage_scores(s3), per_passage_scores(ctrl)
    n = len(a)
    diff = [a[i] - b[i] for i in range(n)]
    md = mean(diff)
    stream = _BootStream(ctrl_name)
    boots = []
    for _ in range(boot_n):
        total = 0.0
        for _ in range(n):
            total += diff[stream.index()]
        boots.append(total / n)
    boots.sort()
    lo = boots[int(0.025 * boot_n)]
    hi = boots[int(0.975 * boot_n) - 1]
    per_seed = all(
        mean(s3["per_seed_correct"][s]) > mean(ctrl["per_seed_correct"][s])
        for s in SEEDS)
    passed = (md >= MARGIN) and (lo > 0.0) and per_seed
    return {"mean_diff": md, "ci95": [lo, hi], "per_seed_positive_3of3": per_seed,
            "margin_met": md >= MARGIN, "passed": passed}


def emit(results, boot_n: int = BOOT_N, evidence_root=None,
         conformance: bool = False):
    """The only claim-status authority. boot_n != BOOT_N is permitted ONLY inside
    test fixtures; the CLI always uses the frozen default. Order is law:
    the EVIDENCE CHAIN is validated before any accuracy or correctness vector
    is read; unbound results are refused (EVIDENCE_UNBOUND)."""
    validate_evidence(results, evidence_root, conformance)   # provenance FIRST
    validate(results)                                    # then evidence shape
    arms = results["arms"]
    gates = {f"S3_vs_{c}": gate(arms["S3"], arms[c], c, boot_n) for c in CONTROLS}
    simpler_fail = [c for c in ("S0", "S1", "S2") if not gates[f"S3_vs_{c}"]["passed"]]
    g6, g7 = gates["S3_vs_S6"], gates["S3_vs_S7"]
    if all(gates[f"S3_vs_{c}"]["passed"] for c in CONTROLS):
        b = LICENSED
    elif simpler_fail:
        b = "COUPLER_NOT_SUPERIOR_TO_SIMPLER_ARMS"
    elif g6["passed"] and not g7["passed"]:
        b = "GENERIC_SEMANTIC_STRUCTURE_DETECTED"
    elif g7["passed"] and not g6["passed"]:
        b = "CAPACITY_EFFECT_DETECTED"
    elif (not g6["passed"] and not g7["passed"]
          and (gates["S3_vs_S4"]["passed"] or gates["S3_vs_S5"]["passed"])):
        b = "SIDE_CHANNEL_ONLY"
    else:
        b = "STATIC_CAS_COUPLING_NOT_SUPPORTED"
    ca = results["claim_a"]
    a_ok = (ca["probe_protected_accuracy"] >= CLAIM_A_MIN
            and (ca["probe_protected_accuracy"] - ca["shuffled_control_accuracy"])
            >= CLAIM_A_MARGIN)
    prot = results["surface_baselines"]["protected"]
    near_ceiling = sorted(
        qt for qt, q in prot["B0"]["per_question_type"].items()
        if q["accuracy"] >= B0_NEAR_CEILING)
    if conformance:
        # SYNTHETIC_CONFORMANCE law (GATE 1A.2 section 12): the machinery runs
        # end to end, but the ONLY status it can ever emit is software
        # conformance -- never a neural or auxiliary-value claim
        a_status = b_status = "SOFTWARE_CONFORMANCE_ONLY"
    else:
        a_status = "CLAIM_A_LICENSED" if a_ok else "CLAIM_A_NOT_LICENSED"
        b_status = b
    return {
        "status_law": "GATE1_THRESHOLDS_v4",
        "mode": "SYNTHETIC_CONFORMANCE" if conformance else "REAL",
        "non_claim_bearing": bool(conformance),
        "claim_a_status": a_status,
        "claim_b_status": b_status,
        "cas_specific_language":
            "PROHIBITED_ON_THIS_DATASET_REGARDLESS_OF_RESULT (owner PATH A; the "
            "answer function is defined over the CAS classes, so no equally "
            "task-aligned non-CAS control exists here)",
        "gates": gates,
        "simpler_arm_failures": simpler_fail,
        "arm_means": {k: mean(per_passage_scores(v)) for k, v in sorted(arms.items())},
        "surface_floor_B0_protected": prot["B0"]["overall"],
        "task_ceiling_B1_protected": prot["B1"]["overall"],
        "b0_near_ceiling_question_types": near_ceiling,
        "b0_near_ceiling_note":
            ("arm differences living entirely in these question types sit on a "
             "near-ceiling surface floor and are so labeled"
             if near_ceiling else "none"),
        "honest_ceiling_disclosures": HONEST_CEILING_DISCLOSURES,
        "emitted_by": "tools/emit_gate1_status.py (deterministic; the only "
                      "claim-status authority)",
    }


def main():
    """CLI: emit_gate1_status.py <results.json> [--out STATUS.json]

    Adversarial-review fix (same defect class that refuted the ff6f40f9
    freeze): the status output is receipt-pinned authority material, and shell
    redirection of stdout is platform-dependent (cmd yields CRLF, Windows
    PowerShell 5.1 yields UTF-16LE+BOM). --out persists the status through the
    ONE canonical writer (exec/fsio.write_utf8_lf: UTF-8, LF, every platform);
    Gate 1B step 8 MUST use --out and pin THAT file's digest, never a redirect.
    """
    args = [a for a in sys.argv[1:]]
    out_path = evidence_root = None
    conformance = False
    if "--conformance" in args:
        conformance = True
        args.remove("--conformance")
    for flag in ("--out", "--evidence-root"):
        if flag in args:
            i = args.index(flag)
            try:
                value = args[i + 1]
            except IndexError:
                print("usage: emit_gate1_status.py <results.json> "
                      "--evidence-root DIR [--out STATUS.json] [--conformance]")
                return 2
            if flag == "--out":
                out_path = value
            else:
                evidence_root = value
            del args[i:i + 2]
    if len(args) != 1:
        print("usage: emit_gate1_status.py <results.json> "
              "--evidence-root DIR [--out STATUS.json] [--conformance]")
        return 2
    results = json.loads(open(args[0], encoding="utf-8").read())
    try:
        out = emit(results, evidence_root=evidence_root, conformance=conformance)
    except (EvidenceUnbound, StatusInputInvalid) as exc:
        print(f"REFUSED: {exc}")
        return 1
    text = json.dumps(out, indent=2) + "\n"
    if out_path is not None:
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from exec.fsio import write_utf8_lf
        write_utf8_lf(out_path, text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
