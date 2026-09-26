"""Operational two-seed admission; exact c45 training/scoring package is unchanged."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "research/CAS_META_2_COMPOSITION")]
from aws import typed_pointer_launch as launch
from aws import budget
SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
SEEDS = (20260917, 20260919)
ARCHIVE_SHA = "38761e9595c321eeab09a368a699a993b7db7616c4f2f15fb716dc78a9066119"
MANIFEST_SHA = "f083fb087ce2eac2394b81856a2aea8f239e7b7d327d27a71160e4dcb6bc2b5d"
REFERENCE = ROOT / "records/typed_pointer_001/admission_cm2x_rerun_001/seeds/20260918"
PACKAGE = ROOT / "research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_c45f775f"

def require(ok, reason):
    if not ok:
        raise ValueError("REPLICATION_STOPPED:" + reason)

def digest(raw):
    return sha256(raw).hexdigest()

def canonical(value):
    return launch.canonical(value)

def load_plan(expected_hash):
    raw = (HERE / "PLAN.json").read_bytes()
    require(digest(raw) == expected_hash, "PLAN_HASH")
    plan = json.loads(raw)
    require(plan["experiment"] == "HELM-CM2X-REPLICATION-2", "CAMPAIGN")
    require(plan["source_commit"] == SOURCE and plan["package_sha256"] == ARCHIVE_SHA
            and plan["manifest_sha256"] == MANIFEST_SHA, "REFERENCE_BINDINGS")
    require(plan["seeds"] == list(SEEDS) and [j["seed"] for j in plan["jobs"]] == list(SEEDS), "SEED_ORDER")
    require(plan["sequential"] is True and plan["automatic_retries"] == 0, "SEQUENCING")
    require(plan["science"]["passes"] == 20 and plan["science"]["required_artifacts"] == 128
            and plan["science"]["mandatory_pass10_state"] is True
            and plan["science"]["best_checkpoint_selection"] is False, "EVIDENCE_BOUND")
    require(digest((HERE / "OWNER_DIRECTIVE.txt").read_bytes()) == plan["owner_directive_sha256"], "OWNER_DIRECTIVE")
    require(Decimal(plan["budget"]["total_planned_all_services_ceiling_usd"]) <= Decimal("45.00"), "CAMPAIGN_CAP")
    for row in plan["jobs"]:
        require(launch.contract.parse_job(row["job"])[1] == row["seed"], "JOB_SEED")
        require(row["job"].split("-")[-3] == SOURCE[:8], "JOB_SOURCE")
        require(row["all_services_cap_usd"] == "20.00" and row["ledger_reservation_usd"] == "19.20", "SEED_CAP")
    return plan

@contextmanager
def seed_context(seed):
    """Select the original launcher's experiment seed gate only; never alter DESIGN or worker source."""
    require(type(seed) is int and seed in SEEDS, "UNAUTHORIZED_SEED")
    prior = launch.contract.RUN_MODEL_SEED
    require(prior == 20260918, "AMBIENT_SEED_OVERRIDE")
    original_design = canonical(launch.contract.DESIGN)
    launch.contract.RUN_MODEL_SEED = seed
    try:
        yield
    finally:
        launch.contract.RUN_MODEL_SEED = prior
        require(canonical(launch.contract.DESIGN) == original_design, "DESIGN_CHANGED")

def verify_source_and_package():
    """Original committed inventory checks remain enabled, including object IDs, bytes and sizes."""
    input_hash = launch.frozen_inputs_hash(SOURCE)
    receipt = json.loads((PACKAGE / "receipt.json").read_bytes())
    require(receipt["source_sha"] == SOURCE and receipt["archive_sha256"] == ARCHIVE_SHA
            and receipt["manifest_sha256"] == MANIFEST_SHA, "PACKAGE_RECEIPT")
    with (PACKAGE / "source.zip").open("rb") as stream:
        observed = __import__("hashlib").file_digest(stream, "sha256").hexdigest()
    require(observed == ARCHIVE_SHA and (PACKAGE / "source.zip").stat().st_size == receipt["archive_bytes"], "PACKAGE_BYTES")
    require(digest(canonical(receipt["manifest"])) == MANIFEST_SHA, "MANIFEST_BYTES")
    with ZipFile(PACKAGE / "source.zip") as archive:
        shipped = archive.read(launch.shared.MANIFEST_NAME)
    require(digest(shipped) == MANIFEST_SHA, "SHIPPED_MANIFEST")
    require(receipt["manifest"]["source_sha"] == SOURCE, "SHIPPED_SOURCE")
    return input_hash, receipt

def assert_only_seed_difference(config, reference, seed):
    require(config["source_sha"] == reference["source_sha"] == SOURCE, "CONFIG_SOURCE")
    require(config["inputs"] == reference["inputs"] and config["inputs_sha256"] == reference["inputs_sha256"], "INPUTS_CHANGED")
    expected = deepcopy(reference["design"])
    expected["model_seed"] = seed
    # Compare the exact serialized worker design, as the original authority does.
    # planned_work.relations is tuples in Python and lists in its JSON receipt.
    require(canonical(config["design"]) == canonical(expected), "SCIENTIFIC_DESIGN_CHANGED")
    require(launch.contract.parse_job(config["job"])[1] == seed, "CONFIG_JOB_SEED")
    require(config["bucket"] == config["job"] + "-" + launch.shared.RESOURCE_PLAN["account"], "CONFIG_BUCKET")

def build_records(plan, plan_hash, seed):
    require(seed in SEEDS, "UNAUTHORIZED_SEED")
    row = next(x for x in plan["jobs"] if x["seed"] == seed)
    job = row["job"]
    require(not (ROOT / row["receipt_dir"]).exists(), "RECEIPT_ALREADY_EXISTS")
    inputs_hash, package_receipt = verify_source_and_package()
    reference = json.loads((REFERENCE / "authority.json").read_bytes())["worker_config"]
    with seed_context(seed):
        config = launch.worker_config(job, source_sha=SOURCE)
        assert_only_seed_difference(config, reference, seed)
        evidence = launch.evidence_contract()
        require(evidence["required_count"] == 128, "REQUIRED_COUNT_CHANGED")
        required_keys = set(launch.run_evidence.contract_keys(evidence))
        require("results/evidence/main_checkpoint_1470.pt" in required_keys
                and "results/evidence/main_checkpoint_1470.json" in required_keys, "PASS10_STATE_NOT_REQUIRED")
        bound = budget.validate_plan(launch.reservation_plan_for(config["design"]), launch.RESERVATION_USD)
        require(bound <= Decimal("19.20"), "LEDGER_BOUND")
        owner = {"schema": launch.OWNER_SCHEMA, "candidate": launch.CANDIDATE, "job": job,
                 "model_seed": seed, "bounds": launch.BOUNDS,
                 "owner_instruction_raw": "Prepare and execute exactly two new 20-pass training jobs: first 20260917, second 20260919.",
                 "owner_message_full_raw": (HERE / "OWNER_DIRECTIVE.txt").read_text(encoding="utf-8"),
                 "owner_directive_sha256": plan["owner_directive_sha256"],
                 "replication_plan_sha256": plan_hash, "answered_date": "2026-09-26",
                 "transcribed_by_agent": True, "is_owner_signature": False,
                 "authority_note": "Owner directive transcription, not an owner signature.",
                 "campaign_cap_usd": "45.00", "seed_all_services_cap_usd": "20.00",
                 "automatic_retries": 0, "cleanup_required": True, "best_checkpoint_selection": False,
                 "reference_job_unchanged": plan["reference_job"]}
        owner_raw = canonical(owner)
        identity = {"job": job, "source_sha": SOURCE, "archive_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA}
        request = {"schema": launch.REQUEST_SCHEMA, **identity, "launch_authorized": False}
        authority = {"schema": launch.AUTHORITY_SCHEMA, **identity, **launch.BOUNDS,
                     "candidate": launch.CANDIDATE, "owner_authorization_sha256": digest(owner_raw),
                     "inputs_sha256": inputs_hash, "design_sha256": digest(canonical(launch.DESIGN)),
                     "evidence_contract_sha256": launch.run_evidence.contract_digest(evidence), "worker_config": config}
        launch.validate_request(request)
        launch.validate_authority(authority)
        probe = HERE / (".owner_probe_" + str(seed) + ".json")
        with probe.open("xb") as stream:
            stream.write(owner_raw)
        try:
            launch.validate_owner(probe, authority)
        finally:
            probe.unlink()
    target = HERE / "admission" / str(seed)
    study = {"schema": "helm.cm2x-replication.seed-admission/1", "status": "FROZEN_BEFORE_BOTH_NEW_RUNS",
             "source_sha": SOURCE, "source_checkout": str(ROOT), "model_seed": seed, "job": job,
             "replication_plan_sha256": plan_hash, "required_artifacts": 128, "automatic_retries": 0,
             "package_sha256": ARCHIVE_SHA, "manifest_sha256": MANIFEST_SHA,
             "legacy_run_model_seed_label": 20260918, "effective_model_seed": seed,
             "seed_selection_boundary": "Only the original local launcher request-admission constant is selected; its DESIGN and all packaged source bytes stay unchanged. Existing worker uses design.model_seed.",
             "job_record": {"receipt_dir": str(ROOT / row["receipt_dir"]), "reservation_usd": "19.20",
                "all_services_cap_usd": "20.00", "launch_command": ["python", "-B", str(HERE / "launch_replication.py")],
                "launch_argv": ["--seed", str(seed), "--plan-sha256", plan_hash, "--",
                    "--execute", "--request", str(target / "request.json"), "--request-sha256", digest(canonical(request)),
                    "--authority", str(target / "authority.json"), "--authority-sha256", digest(canonical(authority)),
                    "--owner-authorization", str(target / "owner.json"), "--receipt-dir", str(ROOT / row["receipt_dir"]),
                    "--ledger-path", str(launch.CANONICAL_LEDGER)]}}
    return {"owner.json": owner_raw, "request.json": canonical(request), "authority.json": canonical(authority),
            "study.json": canonical(study)}

def prepare(plan_hash, write=False):
    plan = load_plan(plan_hash)
    require(not (HERE / "admission").exists(), "ADMISSION_ALREADY_EXISTS")
    records = {seed: build_records(plan, plan_hash, seed) for seed in SEEDS}
    if write:
        target = HERE / "admission"
        target.mkdir()
        for seed, files in records.items():
            directory = target / str(seed)
            directory.mkdir()
            for name, raw in files.items():
                with (directory / name).open("xb") as stream:
                    stream.write(raw)
    print(json.dumps({"status": "FROZEN" if write else "DRY_RUN_PASS_NO_TRAINING",
                      "source": SOURCE, "seeds": list(SEEDS), "package_sha256": ARCHIVE_SHA,
                      "records": {str(seed): {name: digest(raw) for name, raw in files.items()} for seed, files in records.items()}}))
    return records

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-sha256", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    prepare(args.plan_sha256, args.write)
