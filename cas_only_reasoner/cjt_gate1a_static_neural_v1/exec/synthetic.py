"""synthetic.py -- SYNTHETIC_CONFORMANCE fixtures (GATE 1A.2 section 12).

PERMANENTLY NON-CLAIM-BEARING. This module builds every fixture the synthetic
campaign needs -- tiny datasets, fake model identities, a fake AWS identity, a
synthetic schedule, TEST-key approvals, deterministic pseudo-features -- so the
REAL campaign driver (exec/campaign_driver.py) can traverse its complete
lifecycle on CPU. There is no second toy launcher: the same orchestration code
runs, with these fixtures as its DATA. Nothing here can emit a neural claim;
the status program refuses a TEST- key outside conformance mode, and
conformance status is always SOFTWARE_CONFORMANCE_ONLY.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tools"))

from exec.fsio import write_utf8_lf  # noqa: E402
from exec.prng import HashPRNG  # noqa: E402

TEST_KEY_SEED_STRING = "CJT_GATE1A2_TEST_OWNER_KEY_v1_NOT_A_SECRET"
SYNTH_SEEDS = [11, 23, 47]
SYNTH_ARMS = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]
SYNTH_UPDATES = 5
D_MODEL = 896

REGISTERED_VERBS = ["drawn", "pulled", "felt", "captured", "withdrew", "repelled",
                    "recoiled", "backed", "broke", "lay", "split", "made",
                    "brought", "thought", "reminded", "summoned"]


def test_private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    seed = hashlib.sha256(TEST_KEY_SEED_STRING.encode("utf-8")).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def sign_record(record: dict):
    from verify_phase_approval import canonical_signing_bytes
    r = dict(record)
    r["ed25519_signature"] = ""
    r["ed25519_signature"] = test_private_key().sign(
        canonical_signing_bytes(r)).hex()
    return r


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def build_synthetic_dataset(root: Path, campaign_id: str):
    """Tiny construction-gold dataset via the REAL generator machinery, with
    post-acceptance contiguous ids. Sizes: train 32, val 8, protected 1000
    (the frozen status law requires exactly 1000 protected passages)."""
    import generate_construction_gold as gen
    from independent_roundtrip_checker import check_record
    sizes = {"train": 32, "val": 8, "protected": 1000}
    rng = HashPRNG(f"SYNTHETIC_CONFORMANCE|{campaign_id}")
    manifest = {"manifest_id": "SYNTHETIC_DATASET_MANIFEST",
                "non_claim_bearing": True, "campaign_id": campaign_id,
                "splits": {}, "files": {}}
    bodies = {}
    for split in ("train", "val", "protected"):
        records, idx, qcycle = [], 0, 0
        while len(records) < sizes[split]:
            rec = gen.build_passage(rng, split, idx,
                                    gen.QTYPES[qcycle % len(gen.QTYPES)])
            idx += 1
            if rec is None:
                continue
            ok, _ = check_record(rec)
            if not ok:
                continue
            rec["passage_id"] = f"{split[0]}{len(records):06d}"  # contiguous
            records.append(rec)
            qcycle += 1
        body = "\n".join(gen.canonical_line(r) for r in records) + "\n"
        bodies[split] = body.encode("utf-8")
        manifest["splits"][split] = {
            "passages": len(records),
            "content_sha256": sha256_bytes(bodies[split])}
        if split != "protected":                        # protected NEVER written
            write_utf8_lf(root / "data" / f"{split}.jsonl", body)
            manifest["files"][f"data/{split}.jsonl"] = \
                manifest["splits"][split]["content_sha256"]
    mtext = json.dumps(manifest, indent=2) + "\n"
    write_utf8_lf(root / "SYNTHETIC_DATASET_MANIFEST.json", mtext)
    protected_records = [json.loads(x) for x in
                         bodies["protected"].decode("utf-8").splitlines()]
    return manifest, protected_records


def synthetic_features(records, layer: int, campaign_id: str):
    """Deterministic pseudo-features: {pid: {h (N,896), g (896,), cand (C,896)}}.
    torch.Generator seeded from a sha256 of (campaign, layer, pid, part) --
    replay-identical on the same torch build (conformance is same-box)."""
    import torch

    def vec(tag, n_rows):
        g = torch.Generator().manual_seed(
            int(hashlib.sha256(
                f"{campaign_id}|L{layer}|{tag}".encode()).hexdigest()[:15], 16))
        return torch.randn(n_rows, D_MODEL, generator=g)

    out = {}
    for r in records:
        pid = r["passage_id"]
        out[pid] = {"h": vec(f"{pid}|h", len(r["clauses"])),
                    "g": vec(f"{pid}|g", 1)[0],
                    "cand": vec(f"{pid}|cand", len(r["candidates"]))}
    return out


def build_synthetic_model_identity(root: Path):
    """Fake model/tokenizer files + resolved identities, hashed for real."""
    model_dir = root / "model"
    files = {"model.safetensors": b"SYNTHETIC WEIGHTS -- NOT A MODEL\n",
             "config.json": b'{"synthetic": true}\n'}
    tok_files = {"tokenizer.json": b'{"synthetic_tokenizer": true}\n',
                 "vocab.json": b'{"a": 0}\n'}
    weight_map, tok_map = {}, {}
    for fname, data in files.items():
        (model_dir / fname).parent.mkdir(parents=True, exist_ok=True)
        (model_dir / fname).write_bytes(data)
        weight_map[fname] = sha256_bytes(data)
    for fname, data in tok_files.items():
        (model_dir / fname).write_bytes(data)
        tok_map[fname] = sha256_bytes(data)
    revision = "ab" * 20
    write_utf8_lf(model_dir / "REVISION_SHA", revision + "\n")
    return {"model_dir": model_dir, "model_revision_sha": revision,
            "model_weight_sha256s": weight_map,
            "tokenizer_file_sha256s": tok_map}


def build_synthetic_taxonomy(root: Path):
    table = {"table_id": "SYNTHETIC_ALTERNATIVE_TAXONOMY",
             "verb_to_class": {v: i % 4 for i, v in enumerate(REGISTERED_VERBS)}}
    p = root / "derived" / "alternative_taxonomy_table.json"
    write_utf8_lf(p, json.dumps(table, indent=2) + "\n")
    return p, table["verb_to_class"], sha256_file(p)


def build_synthetic_schedule(root: Path):
    sched = {"manifest_id": "SYNTHETIC_RUN_SCHEDULE", "non_claim_bearing": True,
             "arms": SYNTH_ARMS, "claim_bearing_seeds": SYNTH_SEEDS,
             "duplicate_run_policy": {"arm": "S0", "seed": 11, "count": 1},
             "layer_selection_runs": {"arm": "S0", "seed": 11,
                                      "candidate_layers": [6, 12, 18, 24]},
             "updates_per_run": SYNTH_UPDATES,
             "parameter_count_tolerance": 0.01,
             "cache_version": "SYNTHETIC_CACHE_V1",
             "checkpoint_naming_rule": "checkpoints/{arm}_seed{seed}_L{layer}.pt",
             "optimizer": {"name": "AdamW", "learning_rate": 0.001,
                           "betas": [0.9, 0.999], "weight_decay": 0.01,
                           "schedule": "cosine decay, 5% linear warmup",
                           "batch_size": 8, "gradient_clip_norm": 1.0},
             "early_stop": "NONE",
             "expected_run_counts": {"layer_selection": 4, "claim_bearing": 24,
                                     "duplicate": 1, "total": 29}}
    p = root / "SYNTHETIC_RUN_SCHEDULE.json"
    write_utf8_lf(p, json.dumps(sched, indent=2) + "\n")
    return p


def synthetic_aws_identity(account_id: str = "000000000000"):
    return {"synthetic": True, "account_id": account_id, "region": "us-east-1",
            "instance_id": "i-0synthetic0000000", "instance_type": "g5.xlarge",
            "gpu_name": "SYNTHETIC NVIDIA A10G (no device exists)"}


def build_synthetic_approvals(detached_dir: Path, package_root: Path,
                              expected_commit: str, fixture: dict):
    """TEST-key prep + execution approvals, written OUTSIDE the package root
    (detachment law). fixture carries the resolved synthetic identities."""
    common = {
        "decision": "APPROVED",
        "gate0_anchor_sha": "83f57d6f724505f2c2c68593b2625c36c3e07a4d",
        "gate1a1r_anchor_sha": "a6140e0ccc28ccb9b1a6e07e6f578e5fc0a0583c",
        "execution_code_commit_sha": expected_commit,
        "package_manifest_sha256": sha256_file(package_root / "PACKAGE_MANIFEST.json"),
        "gate1b_code_manifest_sha256": sha256_file(
            package_root / "GATE1B_CODE_MANIFEST.json"),
        "gate1a2_execution_manifest_sha256": sha256_file(
            package_root / "GATE1A2_EXECUTION_MANIFEST.json"),
        "aws_account_id": "000000000000",
        "region": "us-east-1",
        "owner_key_id": "TEST-GATE1A2-CONFORMANCE-KEY-v1",
        "signed_utc": "2026-08-31T12:00:00+00:00",
        "ed25519_signature": "",
    }
    prep = sign_record({**common,
        "record_id": "OWNER_CONTAINER_PREP_APPROVAL_GATE1B",
        "phase": "GATE_1B_CONTAINER_PREP",
        "permitted_operations": [
            "MODEL_DOWNLOAD_AND_REVISION_RESOLUTION", "TOKENIZER_AND_WEIGHT_HASHING",
            "DEPENDENCY_LOCK_RESOLUTION", "CONTAINER_CONSTRUCTION",
            "S7_TABLE_CONSTRUCTION", "IDENTITY_RECEIPT_GENERATION"],
        "prep_cost_ceiling_usd": 5.0,
        "prep_wall_clock_ceiling_hours": 1.0,
        "receipt_destination": "results/synthetic/prep"})
    prep_path = detached_dir / "container_prep_approval.json"
    write_utf8_lf(prep_path, json.dumps(prep, indent=2) + "\n")
    execution = sign_record({**common,
        "record_id": "OWNER_PHASE_APPROVAL_GATE1B",
        "phase": "GATE_1B_EXECUTION",
        "package_commit_sha": expected_commit,
        "artifact_digests": json.loads(
            (package_root / "PACKAGE_MANIFEST.json").read_text("utf-8"))["sha256"],
        "container_prep_receipt_sha256": fixture["container_prep_receipt_sha256"],
        "model_revision_sha": fixture["model_revision_sha"],
        "model_weight_sha256s": fixture["model_weight_sha256s"],
        "tokenizer_file_sha256s": fixture["tokenizer_file_sha256s"],
        "dependency_lock_sha256": fixture["dependency_lock_sha256"],
        "container_image_digest": fixture["container_image_digest"],
        "dataset_manifest_sha256": fixture["dataset_manifest_sha256"],
        "s7_control_table_sha256": fixture["s7_control_table_sha256"],
        "status_program_sha256": sha256_file(
            package_root / "tools" / "emit_gate1_status.py"),
        "run_schedule_sha256": fixture["run_schedule_sha256"],
        "claim_bearing_seeds": SYNTH_SEEDS,
        "protected_derivation_commitment": "PUBLIC_SEED_20260831",
        "salted_protected_manifest_sha256": "NOT_APPLICABLE_PUBLIC_SEED",
        "cas_mapping_rules_sha256": "ab" * 32,          # synthetic (non-claim-bearing)
        "cas_mapping_rules_status": "OWNER_APPROVED",
        "s7_path_a_ratified": True,
        "instance_type": "g5.xlarge",
        "required_gpu_type": "NVIDIA A10G",
        "s3_prefix": "s3://synthetic-conformance-bucket/gate1a2/",
        "max_hourly_rate_usd": 1.5,
        "cost_ceiling_usd": 120.0,
        "per_job_wall_clock_cap_hours": 2.0})
    exec_path = detached_dir / "execution_approval.json"
    write_utf8_lf(exec_path, json.dumps(execution, indent=2) + "\n")
    return prep_path, exec_path


def build_container_prep_receipt(root: Path, identity: dict,
                                 taxonomy_sha256: str, dep_lock_sha256: str):
    receipt = {"receipt_id": "CONTAINER_PREP_RECEIPT",
               "non_claim_bearing": True,
               "model_revision_sha": identity["model_revision_sha"],
               "model_weight_sha256s": identity["model_weight_sha256s"],
               "tokenizer_file_sha256s": identity["tokenizer_file_sha256s"],
               "dependency_lock_sha256": dep_lock_sha256,
               "container_image_digest": "sha256:" + "77" * 32,
               "s7_control_table_sha256": taxonomy_sha256}
    p = root / "CONTAINER_PREP_RECEIPT.json"
    write_utf8_lf(p, json.dumps(receipt, indent=2) + "\n")
    return p, receipt
