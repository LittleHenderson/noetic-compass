"""THE INTERLOCK. Call this before a replay-training job loads or trains anything.

Owner ruling 2026-09-02: the trigger passed its bench test but was "a correctly functioning
checker standing beside the machinery, not an interlock inside it". This module is the wiring.
It implements the owner's five launcher requirements:

    1. Verify the manifest's scope, job id, schema and digest.
    2. Run the structural-forgery trigger BEFORE loading or training the model.
    3. Abort on REFUSED, WATCH_UNRESOLVED, NECESSARY or URGENT.
    4. Require explicit owner acknowledgement if WATCH is allowed.
    5. Store the manifest digest, trigger status and trigger receipt inside the final receipt.

USAGE FROM A LAUNCHER

    from replay_training_gate import require_clearance, bind_into_receipt, TrainingBlocked

    clearance = require_clearance(              # raises TrainingBlocked on any blocking code
        job_id="CMB-RP1",
        pipeline_config=<dict EMITTED BY THE PIPELINE>,
        corpus_path=<the memory snapshot being replayed>,
        declared_owner="...", source_commit="<40 hex>",
    )
    ... load the model, train ...
    receipt = bind_into_receipt(receipt, clearance)   # refuses to produce a receipt without it

WHY THE MANIFEST IS DERIVED HERE AND NOT ACCEPTED FROM THE CALLER

The trigger already refuses a declared flag that disagrees with the pipeline config. This goes
one step further: the launcher never writes a manifest at all. It hands over the config its
pipeline EMITTED, and the manifest is derived from it, digested, and written for the record.
There is no hand-editable boolean anywhere on the path. "The pipeline is the fact; the manifest
is a claim about it" -- so the claim is generated from the fact rather than asserted beside it.

WHAT THIS DOES NOT DO. It does not design, authorize, or enable CMB-RP1. CMB-RP1 does not exist.
This is the reusable interlock any replay-training launcher must call, built so that when
CMB-RP1 is designed the wiring is not invented under time pressure.

THE LIMIT, STATED PLAINLY. This interlock defends against MISTAKE, not against a launcher that
deliberately lies about itself. `bind_into_receipt` re-reads the trigger's own receipt file and
checks that its state, digest and exit code agree with the clearance handed over -- so a forged
clearance must also forge that file -- but a launcher that controls its own source can always
skip the call entirely. You cannot stop code from lying about whether it ran a check.

What the interlock DOES buy: the correct path is the easy path; a receipt without a clearance is
visibly incomplete and an auditor can grep for it; and every blocking state provably stops the
trainer, which `validate_gate.py` demonstrates by asserting the trainer function never executed
rather than merely that an exception was raised. The remaining assurance is procedural, not
technical: the run receipt must carry the clearance, and an auditor must check it.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHK = os.path.join(HERE, "check_structural_trigger.py")

SCHEMA_VERSION = "1.0"
DEV_SCOPE = "DEVELOPMENT_REPLAY"

# The trigger's frozen ladder. Only these permit a launch; everything else aborts.
PERMITTING_CODES = (0,)
STATE_MEANING = {
    0: "clear or legitimately dormant",
    5: "WATCH -- needs an owner acknowledgement bound to this job",
    10: "unknown or refused -- block",
    20: "defence necessary -- block",
    30: "urgent defence requirement -- block",
}


class TrainingBlocked(RuntimeError):
    """Raised when the trigger does not permit this job. Never catch this to continue."""

    def __init__(self, state, code, detail, receipt):
        super().__init__(f"REPLAY TRAINING BLOCKED -- {state} (exit {code}): {detail}")
        self.state, self.code, self.receipt = state, code, receipt


def digest_of(m):
    return hashlib.sha256(json.dumps(
        {k: v for k, v in m.items() if not k.startswith("_") and k != "config_digest"},
        sort_keys=True).encode()).hexdigest()


def derive_manifest(*, job_id, pipeline_config, declared_owner, source_commit, timestamp,
                    memory_count=None, writes_per_day=None):
    """Build a DEVELOPMENT_REPLAY manifest FROM the pipeline's own emitted config.

    The three declared flags are read out of the pipeline config, never taken from an argument,
    so a launcher cannot assert a value its pipeline does not support.
    """
    if not isinstance(pipeline_config, dict):
        raise TypeError("pipeline_config must be the object your pipeline emitted")
    mft = pipeline_config.get("memory_feeds_training")
    if not isinstance(mft, bool):
        raise ValueError(
            "pipeline config has no boolean 'memory_feeds_training'. The pipeline must EMIT "
            "this, and it must reflect whether replayed memories actually enter training "
            "batches. It may not be supplied by hand.")
    m = {
        "schema_version": SCHEMA_VERSION,
        "scope": DEV_SCOPE,
        "job_id": job_id,
        "config_digest": "",
        "declared_owner": declared_owner,
        "timestamp": timestamp,
        "source_commit": source_commit,
        "derivation": "derived_from_pipeline_config",
        "memory_feeds_training": mft,
        "untrusted_write_path": bool(pipeline_config.get("untrusted_write_path", False)),
        "observable_thresholds": bool(pipeline_config.get("observable_thresholds", False)),
        "memory_count": (memory_count if memory_count is not None
                         else pipeline_config.get("memory_count", 0)),
        "writes_per_day": (writes_per_day if writes_per_day is not None
                           else pipeline_config.get("writes_per_day", 0)),
    }
    m["config_digest"] = digest_of(m)
    return m


def require_clearance(*, job_id, pipeline_config, declared_owner, source_commit, timestamp,
                      corpus_path=None, watch_ack=None, memory_count=None,
                      writes_per_day=None, event="pre-training", artifact_dir=None):
    """Step 1-4. Returns a clearance dict on success; raises TrainingBlocked otherwise.

    CALL THIS BEFORE LOADING OR TRAINING ANYTHING. Its whole value is that it runs first.
    """
    manifest = derive_manifest(
        job_id=job_id, pipeline_config=pipeline_config, declared_owner=declared_owner,
        source_commit=source_commit, timestamp=timestamp,
        memory_count=memory_count, writes_per_day=writes_per_day)

    out = artifact_dir or tempfile.mkdtemp(prefix="replay_gate_")
    os.makedirs(out, exist_ok=True)
    mp = os.path.join(out, f"{job_id}_JOB_MANIFEST.json")
    pp = os.path.join(out, f"{job_id}_pipeline_config.json")
    rp = os.path.join(out, f"{job_id}_trigger_receipt.json")
    for path, obj in ((mp, manifest), (pp, pipeline_config)):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, indent=2, sort_keys=True)

    argv = [sys.executable, CHK, "--manifest", mp,
            "--expected-scope", DEV_SCOPE, "--job-id", job_id,
            "--pipeline-config", pp, "--job", event, "--receipt-out", rp]
    if corpus_path:
        argv += ["--corpus", corpus_path]
    if watch_ack is not None:
        ap = os.path.join(out, f"{job_id}_watch_ack.json")
        with open(ap, "w", encoding="utf-8", newline="\n") as f:
            json.dump(watch_ack, f, indent=2, sort_keys=True)
        argv += ["--watch-ack", ap]

    proc = subprocess.run(argv, capture_output=True, text=True)
    code = proc.returncode
    receipt = {}
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            receipt = json.load(f)
    state = receipt.get("state") or "NO_STATE"

    clearance = {
        "gate": "STRUCTURAL_FORGERY_DEFENCE",
        "job_id": job_id, "scope": DEV_SCOPE, "event": event,
        "trigger_state": state, "trigger_exit_code": code,
        "manifest_digest": manifest["config_digest"],
        "manifest_path": mp, "trigger_receipt_path": rp,
        "trigger_receipt": receipt,
        "pipeline_derived_memory_feeds_training": manifest["memory_feeds_training"],
        "console": proc.stdout,
    }

    if code not in PERMITTING_CODES:
        raise TrainingBlocked(state, code,
                              STATE_MEANING.get(code, "undocumented exit code"), clearance)
    return clearance


def bind_into_receipt(run_receipt, clearance):
    """Step 5. A run receipt is not complete without the clearance that permitted the run.

    Refuses a clearance that did not actually come from a permitting trigger result, so a
    launcher cannot fabricate one to satisfy the field.
    """
    if not isinstance(clearance, dict) or clearance.get("gate") != "STRUCTURAL_FORGERY_DEFENCE":
        raise TrainingBlocked("NO_CLEARANCE", 10,
                              "receipt built without a structural-forgery clearance", {})
    if clearance.get("trigger_exit_code") not in PERMITTING_CODES:
        raise TrainingBlocked(clearance.get("trigger_state", "?"),
                              clearance.get("trigger_exit_code", 10),
                              "clearance present but not permitting", clearance)
    # Re-verify against the trigger's OWN receipt file rather than trusting the dict handed to
    # us. A fabricated clearance now has to also forge the file the trigger wrote, and agree
    # with it on state and manifest digest. See the LIMIT note in the module docstring: this
    # raises the cost of a bypass, it does not make one impossible.
    rp = clearance.get("trigger_receipt_path")
    if not rp or not os.path.exists(rp):
        raise TrainingBlocked("NO_TRIGGER_RECEIPT", 10,
                              "clearance cites no trigger receipt on disk", clearance)
    with open(rp, encoding="utf-8") as f:
        on_disk = json.load(f)
    if on_disk.get("state") != clearance.get("trigger_state"):
        raise TrainingBlocked("RECEIPT_MISMATCH", 10,
                              f"clearance says {clearance.get('trigger_state')!r} but the "
                              f"trigger receipt says {on_disk.get('state')!r}", clearance)
    if on_disk.get("manifest_digest") != clearance.get("manifest_digest"):
        raise TrainingBlocked("RECEIPT_MISMATCH", 10,
                              "clearance manifest digest does not match the trigger receipt",
                              clearance)
    if on_disk.get("exit_code") not in PERMITTING_CODES:
        raise TrainingBlocked(on_disk.get("state", "?"), on_disk.get("exit_code", 10),
                              "the trigger receipt on disk is not a permitting result",
                              clearance)
    run_receipt = dict(run_receipt)
    run_receipt["structural_forgery_clearance"] = {
        k: clearance[k] for k in
        ("gate", "job_id", "scope", "event", "trigger_state", "trigger_exit_code",
         "manifest_digest", "pipeline_derived_memory_feeds_training", "trigger_receipt")
    }
    return run_receipt
