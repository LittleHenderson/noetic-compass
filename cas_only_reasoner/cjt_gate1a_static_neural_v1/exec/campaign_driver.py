"""campaign_driver.py -- THE one campaign orchestration entry (GATE 1A.2 s.4).

Replaces the launcher stub. The 30-step ordered path runs through the typed
campaign state machine (exec/campaign_state.py); every phase transition binds
the authorizing approval or receipt digest. There is no second toy launcher:
SYNTHETIC_CONFORMANCE traverses THIS code with committed synthetic fixtures as
data, and is permanently non-claim-bearing (TEST- key, conformance status).
REAL mode additionally requires verified AWS identity, the A10G GPU gate, and
GPU_REQUIRED-guarded neural steps; none of that can run in Gate 1A.2.

Ordered path (owner section 4): 1 verify detached execution approval; 2 verify
the owner trust root (inside every signature check); 3 exact commit + clean
tree; 4 package/code manifests; 5 AWS identity; 6 container + dependency
identities; 7 model revision/weights/tokenizer; 8 regenerate data to a
NON-FROZEN output root; 9 dataset digests; 10 round-trip checker; 11 B0/B1;
12 S7 table; 13 activation extraction; 14 split-separated cache manifests;
15 four S0 layer-selection runs; 16 freeze L* in a receipt; 17 the exact
arm-by-seed schedule; 18 checkpoints + per-run receipts; 19 receipt-set
validation; 20 atomic protected claim; 21 protected regeneration + digest
check; 22 one evaluation per registered checkpoint; 23 burn on every outcome;
24 RAW_GATE1_RESULTS; 25 evidence-chain validation; 26 the frozen status
program; 27 cost reconciliation; 28 campaign receipt seal; 29 uploads;
30 termination request in a finally block.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tools"))

from exec.campaign_state import CampaignStateMachine  # noqa: E402
from exec.cost import CostAuthority  # noqa: E402
from exec.fsio import write_utf8_lf  # noqa: E402
from exec.gpu_guard import require_gpu  # noqa: E402
from exec.identity import (fetch_real_aws_identity, verify_aws_identity,  # noqa: E402
                           verify_container_identity, verify_git_state,
                           verify_gpu, verify_model_identity, verify_s7_table)
from exec.protected_eval import run_protected_evaluation  # noqa: E402
from exec.protected_lock import LocalProtectedLock  # noqa: E402
from exec.schedule import RunSchedule  # noqa: E402
from exec.shutdown import ShutdownPath  # noqa: E402
from exec.watchdog import Watchdog  # noqa: E402
from exec.arms import ARM_STRUCT, MAX_IDEAS, build_arm_head, matched_heads  # noqa: E402
from exec.layer_select import select_layer  # noqa: E402
from exec.baselines import score_split  # noqa: E402
from verify_phase_approval import (verify_container_prep,  # noqa: E402
                                   verify_execution)

ARM_IDS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7")


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _write_json(path: Path, obj) -> str:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    write_utf8_lf(path, text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CampaignDriver:
    def __init__(self, *, mode: str, package_root: Path, campaign_id: str,
                 execution_approval_path: Path, prep_approval_path: Path,
                 prep_receipt_path: Path, evidence_root: Path,
                 synthetic_root: Path = None, clock=None):
        if mode not in ("REAL", "SYNTHETIC_CONFORMANCE"):
            raise ValueError(f"unknown mode {mode!r}")
        self.mode = mode
        self.pkg = Path(package_root).resolve()
        self.campaign_id = campaign_id
        self.execution_approval_path = Path(execution_approval_path)
        self.prep_approval_path = Path(prep_approval_path)
        self.prep_receipt_path = Path(prep_receipt_path)
        self.er = Path(evidence_root)
        self.synthetic_root = Path(synthetic_root) if synthetic_root else None
        self._clock = clock or (lambda: 0.0)
        self.shutdown = ShutdownPath(mode, self.er)
        self.watchdog = Watchdog(self.er / "heartbeat.json", self.er,
                                 stale_limit_seconds=2.5 * 3600)
        self.expected_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.pkg, capture_output=True,
            text=True, check=True).stdout.strip()
        self.sm = CampaignStateMachine(
            campaign_id, self.expected_commit,
            self.er / "campaign" / "transitions.jsonl",
            utc_source=(lambda: "SYNTHETIC")
            if mode == "SYNTHETIC_CONFORMANCE" else None)
        self.approval = None
        self.prep_receipt = None
        self.cost = None
        self.evidence = {}
        self.final = {}

    # ---- phase helpers -------------------------------------------------------

    def _beat(self):
        self.watchdog.beat(self._clock())

    def _design_verified(self):
        verify_git_state(self.pkg, self.expected_commit, ".")
        r = subprocess.run([sys.executable, str(self.pkg / "tools" / "build_manifests.py"),
                            "--check"], capture_output=True, text=True, cwd=self.pkg)
        if r.returncode != 0 or "BUILD_MANIFESTS_CHECK_PASS" not in r.stdout:
            raise RuntimeError(f"MANIFEST_FIXED_POINT_FAILURE: {r.stdout}{r.stderr}")
        self.sm.transition("DESIGN_VERIFIED", binding_kind="package_manifest",
                           binding_sha256=sha256_file(self.pkg / "PACKAGE_MANIFEST.json"))

    def _authority(self):
        prep = json.loads(self.prep_approval_path.read_text(encoding="utf-8"))
        verify_container_prep(prep, self.pkg, self.expected_commit, self.mode,
                              approval_path=self.prep_approval_path)
        self.sm.transition("CONTAINER_PREP_AUTHORIZED",
                           binding_kind="container_prep_approval",
                           binding_sha256=sha256_file(self.prep_approval_path))
        if not self.prep_receipt_path.is_file():
            raise RuntimeError("MISSING_PREP_RECEIPT: identities not resolved")
        self.prep_receipt = json.loads(
            self.prep_receipt_path.read_text(encoding="utf-8"))
        self.sm.transition("IDENTITIES_RESOLVED",
                           binding_kind="container_prep_receipt",
                           binding_sha256=sha256_file(self.prep_receipt_path))
        record = json.loads(
            self.execution_approval_path.read_text(encoding="utf-8"))
        verify_execution(record, self.pkg, self.expected_commit, self.mode,
                         approval_path=self.execution_approval_path,
                         prep_receipt_path=self.prep_receipt_path)
        self.approval = record
        self.cost = CostAuthority(record)          # signed values ONLY
        # adversarial-review fix: the watchdog stale limit is the SIGNED per-job
        # cap (plus 10% grace), not a hardcoded constant
        self.watchdog.stale_limit_seconds = \
            record["per_job_wall_clock_cap_hours"] * 3600 * 1.1
        approval_sha = sha256_file(self.execution_approval_path)
        (self.er).mkdir(parents=True, exist_ok=True)
        write_utf8_lf(self.er / "execution_approval.json",
                      json.dumps(record, indent=2) + "\n")
        write_utf8_lf(self.er / "container_prep_receipt.json",
                      json.dumps(self.prep_receipt, indent=2) + "\n")
        self.evidence.update({
            "package_commit_sha": self.expected_commit,
            "execution_approval_sha256": sha256_file(
                self.er / "execution_approval.json"),
            "owner_key_id": record["owner_key_id"],
            "container_prep_receipt_sha256": sha256_file(
                self.er / "container_prep_receipt.json"),
            "model_revision_sha": record["model_revision_sha"],
            "model_weight_manifest_sha256": sha256_obj(record["model_weight_sha256s"]),
            "tokenizer_manifest_sha256": sha256_obj(record["tokenizer_file_sha256s"]),
            "container_image_digest": record["container_image_digest"],
            "dependency_lock_sha256": record["dependency_lock_sha256"],
            "dataset_manifest_sha256": record["dataset_manifest_sha256"],
            "s7_control_table_sha256": record["s7_control_table_sha256"],
            "run_schedule_sha256": record["run_schedule_sha256"],
            "protected_campaign_id": self.campaign_id})
        self.sm.transition("EXECUTION_AUTHORIZED", binding_kind="execution_approval",
                           binding_sha256=approval_sha)

    def _aws_identity(self):
        if self.mode == "REAL":
            ident = fetch_real_aws_identity()
        else:
            from exec.synthetic import synthetic_aws_identity
            ident = synthetic_aws_identity(self.approval["aws_account_id"])
        verify_aws_identity(ident, self.approval, self.mode)
        verify_gpu(self.approval, self.mode,
                   aws_identity_verified=True)
        # kept OUT of self.evidence (the evidence_chain has a frozen key set the
        # status program checks); stored for the protected-lock claimant field
        self._aws_instance_id = ident.get("instance_id")
        self.sm.transition("AWS_IDENTITY_VERIFIED", binding_kind="aws_identity",
                           binding_sha256=sha256_obj(ident))

    def _data(self):
        out_root = self.er / "regenerated_dataset"      # NON-FROZEN destination
        if self.mode == "REAL":
            r = subprocess.run(
                [sys.executable, str(self.pkg / "tools" / "generate_construction_gold.py"),
                 "--output-root", str(out_root)],
                capture_output=True, text=True, cwd=self.pkg)
            if r.returncode != 0:
                raise RuntimeError(f"DATA_REGENERATION_FAILED: {r.stderr}")
            dm_path = out_root / "DATASET_MANIFEST_CANDIDATE.json"
            data_dir = out_root / "data" / "candidate"
        else:
            from exec.synthetic import build_synthetic_dataset
            _, self._synthetic_protected = build_synthetic_dataset(
                out_root, self.campaign_id)
            dm_path = out_root / "SYNTHETIC_DATASET_MANIFEST.json"
            data_dir = out_root / "data"
        dm_sha = sha256_file(dm_path)
        if dm_sha != self.approval["dataset_manifest_sha256"]:
            raise RuntimeError(
                f"DATASET_INTEGRITY_FAILURE: dataset manifest {dm_sha} != "
                f"signed {self.approval['dataset_manifest_sha256']}")
        manifest = json.loads(dm_path.read_text(encoding="utf-8"))
        for rel, want in sorted(manifest["files"].items()):
            got = sha256_file(out_root / rel)
            if got != want:
                raise RuntimeError(f"DATASET_INTEGRITY_FAILURE: {rel}")
        r = subprocess.run(
            [sys.executable, str(self.pkg / "tools" / "independent_roundtrip_checker.py"),
             str(data_dir / "train.jsonl"), str(data_dir / "val.jsonl")],
            capture_output=True, text=True, cwd=self.pkg)
        if "ALL ROUNDTRIPS PASS" not in r.stdout:
            raise RuntimeError(f"ROUNDTRIP_FAILURE: {r.stdout}")
        self.train_records = [json.loads(x) for x in
                              (data_dir / "train.jsonl").read_text("utf-8").splitlines()]
        self.val_records = [json.loads(x) for x in
                            (data_dir / "val.jsonl").read_text("utf-8").splitlines()]
        self.surface_baselines = {
            s: {"B0": score_split(recs, "B0"), "B1": score_split(recs, "B1")}
            for s, recs in (("train", self.train_records), ("val", self.val_records))}
        if self.mode == "REAL":                        # frozen-value equality law
            frozen = json.loads((self.pkg / "SURFACE_BASELINES_CANDIDATE.json")
                                .read_text("utf-8"))["splits"]
            if self.surface_baselines != frozen:
                raise RuntimeError("SURFACE_BASELINE_MISMATCH vs frozen candidate")
        self.evidence["surface_baseline_receipt_sha256"] = _write_json(
            self.er / "surface_baseline_receipt.json",
            {"campaign_id": self.campaign_id, "splits": self.surface_baselines})
        write_utf8_lf(self.er / "dataset_manifest.json",
                      dm_path.read_text(encoding="utf-8"))
        self.dataset_manifest = manifest
        self.sm.transition("DATA_VERIFIED", binding_kind="dataset_manifest",
                           binding_sha256=dm_sha)

    def _model(self):
        model_dir = (self.synthetic_root / "model" if self.mode != "REAL"
                     else Path("/campaign/model"))
        verify_model_identity(model_dir, self.approval)
        verify_container_identity(self.prep_receipt, self.approval)
        s7 = (self.synthetic_root / "derived" / "alternative_taxonomy_table.json"
              if self.mode != "REAL"
              else self.pkg / "derived" / "alternative_taxonomy_table.json")
        verify_s7_table(s7, self.approval)
        table = json.loads(Path(s7).read_text(encoding="utf-8"))
        self.verb_to_class = table["verb_to_class"]
        write_utf8_lf(self.er / "s7_table.json",
                      Path(s7).read_text(encoding="utf-8"))
        self.sm.transition("MODEL_VERIFIED", binding_kind="model_identity",
                           binding_sha256=self.approval["s7_control_table_sha256"])

    def _load_frozen_model(self):
        """REAL-only frozen-model load, GPU-guarded. Prohibited in Gate 1A.2 (no
        model load), so it is UNREACHABLE here -- require_gpu() fails closed on a
        CUDA-less box before any transformers import. Inside the Gate 1B
        container on a verified A10G, this loads the pinned revision and the
        committed extractor/trainer run against it. Cached once per campaign."""
        require_gpu()                                  # FIRST -- fail closed
        if getattr(self, "_frozen_model", None) is None:
            from transformers import AutoModel, AutoTokenizer   # noqa: F401
            model_dir = Path("/campaign/model")
            self._frozen_tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            self._frozen_model = AutoModel.from_pretrained(str(model_dir))
        return self._frozen_model, self._frozen_tokenizer

    def _features_for(self, records, layer):
        if self.mode == "REAL":
            from exec.activation_extraction import extract_split
            model, tok = self._load_frozen_model()     # GPU-guarded; unreachable here
            cache = extract_split(records, tok, model, [layer])
            return {pid: {"h": v["layers"][layer][0], "g": v["layers"][layer][1],
                          "cand": None}
                    for pid, v in cache.items()}
        from exec.synthetic import synthetic_features
        return synthetic_features(records, layer, self.campaign_id)

    def _activations(self):
        from exec.activation_extraction import write_cache
        sched_path = (self.synthetic_root / "SYNTHETIC_RUN_SCHEDULE.json"
                      if self.mode != "REAL"
                      else self.pkg / "RUN_SCHEDULE_MANIFEST_CANDIDATE.json")
        if sha256_file(sched_path) != self.approval["run_schedule_sha256"]:
            raise RuntimeError("SCHEDULE_BINDING_FAILURE vs signed digest")
        if self.mode == "REAL":
            # frozen-candidate backstop (adversarial-review fix): in REAL mode
            # the schedule digest must ALSO equal the committed frozen schedule,
            # so a signed-but-wrong schedule cannot slip through even though the
            # approval binds it -- mirroring the dataset/baseline backstops
            frozen_sched = sha256_file(
                self.pkg / "RUN_SCHEDULE_MANIFEST_CANDIDATE.json")
            if sha256_file(sched_path) != frozen_sched:
                raise RuntimeError("SCHEDULE_NOT_FROZEN: REAL schedule differs "
                                   "from the committed frozen run schedule")
        write_utf8_lf(self.er / "run_schedule.json",
                      Path(sched_path).read_text(encoding="utf-8"))
        self.schedule = RunSchedule.load(sched_path)
        if self.schedule.seeds != self.approval["claim_bearing_seeds"]:
            raise RuntimeError("SEED_LIST_MISMATCH: schedule vs signed approval")
        cache_dir = self.er / "caches"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.features = {}
        cache_manifest = {}
        for split, records in (("train", self.train_records),
                               ("val", self.val_records)):
            per_layer = {L: self._features_for(records, L)
                         for L in (6, 12, 18, 24)}
            self.features[split] = per_layer
            cache_manifest[split] = write_cache(
                cache_dir / f"{split}_features.pt", per_layer)
        self.evidence["cache_manifest_sha256s"] = dict(cache_manifest)
        cm_sha = _write_json(cache_dir / "cache_manifest.json", cache_manifest)
        self.sm.transition("ACTIVATIONS_CACHED", binding_kind="cache_manifest",
                           binding_sha256=cm_sha)

    def _train_one(self, arm, seed, layer, records, features):
        """Mode-committed training: REAL -> exec/train_loop.run_training
        (GPU-guarded; unreachable in Gate 1A.2 because it fails closed on a
        CUDA-less box); SYNTHETIC -> the committed tiny CPU trainer. Returns a
        state_dict."""
        if self.mode == "REAL":
            from exec.train_loop import run_training
            batches = self._real_train_batches(arm, records, features)
            state_dict, _curve = run_training(
                arm, seed, self._widths()[arm], batches, batches)
            return state_dict
        from exec.synthetic import SYNTH_UPDATES
        import torch
        from exec.dataset_assembly import assemble_examples
        torch.manual_seed(seed)
        widths = self._widths()
        head = build_arm_head(arm, widths[arm]).float()
        exs = assemble_examples(records, arm, verb_to_class=self.verb_to_class)
        opt = torch.optim.AdamW(head.parameters(), lr=1e-3, weight_decay=0.01)
        loss_fn = torch.nn.CrossEntropyLoss()
        for _ in range(SYNTH_UPDATES):
            for ex in exs[:8]:
                f = features[ex["passage_id"]]
                n, c = f["h"].shape[0], f["cand"].shape[0]
                h = torch.zeros(1, MAX_IDEAS, 896); h[0, :n] = f["h"]
                mask = torch.zeros(1, MAX_IDEAS, dtype=torch.bool); mask[0, :n] = True
                p = None
                if ex["profiles"] is not None:
                    p = torch.zeros(1, MAX_IDEAS, 4)
                    p[0, :n] = torch.tensor(ex["profiles"])
                logits = head(h, f["g"].unsqueeze(0), p, mask,
                              f["cand"].unsqueeze(0),
                              torch.ones(1, c, dtype=torch.bool))
                loss = loss_fn(logits, torch.tensor([ex["answer_index"]]))
                opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
        return head.state_dict()

    def _widths(self):
        if not hasattr(self, "_width_map"):
            self._width_map = {a: w for a, (_, w, _) in matched_heads().items()}
        return self._width_map

    def _real_train_batches(self, arm, records, features):
        """REAL-mode batch iterable for exec/train_loop.run_training. Built from
        cached activations + candidate encodings; reachable only inside the
        container (run_training's require_gpu gate stops it here). Committed so
        the signature binds it; the body is a straightforward tensor assembly."""
        import torch
        from exec.dataset_assembly import assemble_examples
        exs = assemble_examples(records, arm, verb_to_class=self.verb_to_class)
        batches = []
        for ex in exs:
            f = features[ex["passage_id"]]
            n, c = f["h"].shape[0], f["cand"].shape[0]
            h = torch.zeros(1, MAX_IDEAS, 896); h[0, :n] = f["h"]
            mask = torch.zeros(1, MAX_IDEAS, dtype=torch.bool); mask[0, :n] = True
            p = None
            if ex["profiles"] is not None:
                p = torch.zeros(1, MAX_IDEAS, 4)
                p[0, :n] = torch.tensor(ex["profiles"])
            batches.append({"split": "train", "h": h, "g": f["g"].unsqueeze(0),
                            "p": p, "idea_mask": mask,
                            "cand_enc": f["cand"].unsqueeze(0),
                            "cand_mask": torch.ones(1, c, dtype=torch.bool),
                            "answer_index": torch.tensor([ex["answer_index"]])})
        return batches

    def _layer_selection(self):
        import torch
        val_acc = {}
        for (arm, seed, layer) in self.schedule.layer_selection:
            self.cost.gate_job(f"layersel_L{layer}")
            self._beat()
            sd = self._train_one(arm, seed, layer, self.train_records,
                                 self.features["train"][layer])
            head = build_arm_head(arm, self._widths()[arm])
            head.load_state_dict(sd)
            from exec.protected_scoring import build_prediction_input, predict_arm_seed
            inputs = [build_prediction_input(r, arm, self.verb_to_class)
                      for r in self.val_records]
            preds = predict_arm_seed(head, inputs, self.features["val"][layer])
            correct = sum(1 for r in self.val_records
                          if preds[r["passage_id"]]
                          == r["candidates"].index(r["answer"]))
            val_acc[layer] = correct / len(self.val_records)
            self.cost.record_job(f"layersel_L{layer}", 0.01)
        self.selected_layer = select_layer(val_acc)
        self.evidence["selected_layer_receipt_sha256"] = _write_json(
            self.er / "selected_layer_receipt.json",
            {"campaign_id": self.campaign_id, "selected_layer": self.selected_layer,
             "validation_accuracy_by_layer": {str(k): v for k, v in
                                              sorted(val_acc.items())}})
        self.sm.transition("LAYER_FROZEN", binding_kind="selected_layer_receipt",
                           binding_sha256=self.evidence["selected_layer_receipt_sha256"])

    def _training(self):
        import torch
        ckpt_dir = self.er / "checkpoints"; ckpt_dir.mkdir(parents=True, exist_ok=True)
        rec_dir = self.er / "receipts"; rec_dir.mkdir(parents=True, exist_ok=True)
        receipts, self.checkpoints = [], {}
        jobs = [(a, s, False) for (a, s) in self.schedule.expected_claim_bearing()]
        jobs += [(a, s, True) for (a, s) in self.schedule.duplicates]
        checkpoint_shas, job_receipt_shas = {}, {}
        for arm, seed, is_dup in jobs:
            job_id = (f"dup_{arm}_seed{seed}" if is_dup
                      else f"run_{arm}_seed{seed}")
            self.cost.gate_job(job_id)
            self._beat()
            sd = self._train_one(arm, seed, self.selected_layer,
                                 self.train_records,
                                 self.features["train"][self.selected_layer])
            ckpt_path = ckpt_dir / f"{arm}_seed{seed}_L{self.selected_layer}.pt"
            if not is_dup:
                torch.save(sd, ckpt_path)
                ckpt_sha = sha256_file(ckpt_path)
                self.checkpoints[(arm, seed)] = ckpt_path
            else:
                ckpt_sha = "0" * 64                     # duplicate: no claim path
            receipt = {"arm": arm, "seed": seed, "status": "SUCCESS",
                       "update_count": self.schedule.updates_per_run,
                       "selected_layer": self.selected_layer,
                       "checkpoint_sha256": ckpt_sha,
                       "cache_manifest_sha256":
                           self.evidence["cache_manifest_sha256s"]["train"],
                       "model_revision_sha": self.approval["model_revision_sha"],
                       "container_image_digest":
                           self.approval["container_image_digest"],
                       "package_commit_sha": self.expected_commit,
                       "duplicate": is_dup}
            sha = _write_json(rec_dir / f"{job_id}.json", receipt)
            if not is_dup:
                receipts.append(receipt)
                checkpoint_shas[f"{arm}_seed{seed}"] = ckpt_sha
                job_receipt_shas[f"{arm}_seed{seed}"] = sha
            self.cost.record_job(job_id, 0.01)
        self.receipts_by_key = self.schedule.validate_claim_bearing_receipts(
            receipts, selected_layer=self.selected_layer,
            expected_commit=self.expected_commit,
            expected_model_revision=self.approval["model_revision_sha"],
            expected_container_digest=self.approval["container_image_digest"])
        self.evidence["checkpoint_sha256s"] = checkpoint_shas
        self.evidence["job_receipt_sha256s"] = job_receipt_shas
        idx_sha = _write_json(self.er / "receipts_index.json",
                              {"jobs": sorted(job_receipt_shas)})
        self.sm.transition("TRAINING_COMPLETE", binding_kind="receipts_index",
                           binding_sha256=idx_sha)

    def _protected_salt(self):
        """The owner-held salt, supplied to the protected step ONLY, when the
        approval chose the salt derivation. In REAL mode it comes from the
        environment variable the launch configuration injects at the protected
        step; absent it, the salted campaign fails closed. The public-seed
        derivation returns None."""
        commitment = self.approval["protected_derivation_commitment"]
        if not commitment.startswith("SALT_SHA256:"):
            return None
        import os
        salt = os.environ.get("CJT_PROTECTED_SALT_HEX", "").strip().lower()
        if not salt:
            raise RuntimeError("PROTECTED_SALT_MISSING: the approval chose the "
                               "salt derivation but no owner salt was supplied "
                               "to the protected step")
        expect = "SALT_SHA256:" + hashlib.sha256(salt.encode("utf-8")).hexdigest()
        if expect != commitment:
            raise RuntimeError("PROTECTED_SALT_MISMATCH: sha256(salt) does not "
                               "match the signed commitment")
        return salt

    def _protected(self):
        approval_sha = self.evidence["execution_approval_sha256"]
        self.sm.transition("PROTECTED_UNOPENED", binding_kind="execution_approval",
                           binding_sha256=approval_sha)
        # ATOMIC one-use claim BEFORE any protected record is regenerated or
        # featurized (adversarial-review fix): re-pointing --evidence-root can
        # no longer un-burn because the driver claims first and the evaluator
        # refuses to run unless the lock is already RUNNING for this campaign.
        # REAL mode uses the DURABLE cross-instance DynamoDB backend (a
        # relaunched instance for the same campaign id then sees a BURNED lock);
        # SYNTHETIC_CONFORMANCE uses the local file backend.
        if self.mode == "REAL":
            from exec.protected_lock import AwsProtectedLock
            lock = AwsProtectedLock(
                table_name=f"cjt-protected-lock-{self.approval['aws_account_id']}",
                region=self.approval["region"])
        else:
            lock = LocalProtectedLock(self.er / "protected_lock")
        salt = self._protected_salt()
        lock_bindings = {
            "execution_approval_sha256": approval_sha,
            "package_commit_sha": self.expected_commit,
            "protected_derivation":
                self.approval["protected_derivation_commitment"],
            "claimant_identity": ("SYNTHETIC_CONFORMANCE"
                                  if self.mode != "REAL"
                                  else getattr(self, "_aws_instance_id",
                                               "EC2_INSTANCE")),
            "claim_utc": ("SYNTHETIC" if self.mode != "REAL"
                          else __import__("datetime").datetime.now(
                              __import__("datetime").timezone.utc).isoformat())}
        claim_receipt = lock.claim(self.campaign_id, **lock_bindings)
        self.evidence["protected_lock_receipt_sha256"] = _write_json(
            self.er / "protected_lock_receipt.json", claim_receipt)
        self.sm.transition("PROTECTED_RUNNING", binding_kind="protected_lock",
                           binding_sha256=self.evidence["protected_lock_receipt_sha256"])
        if self.mode == "REAL":
            records, _ = __import__("exec.protected_eval", fromlist=["x"]) \
                .regenerate_protected(self.pkg, salt)
        else:
            records = self._synthetic_protected
        protected_features = self._features_for(records, self.selected_layer)
        # pre-receipts written BEFORE the raw results so the results can bind
        # them without circular hashing (the FINAL sealed receipt binds results)
        pre_sha = _write_json(self.er / "campaign_pre_receipt.json",
                              {"campaign_id": self.campaign_id,
                               "chain_digest": self.sm.chain_digest(),
                               "cost_so_far": self.cost.report()})
        self.evidence["campaign_receipt_sha256"] = pre_sha
        eval_pre_sha = _write_json(
            self.er / "protected_evaluation_receipt.json",
            {"campaign_id": self.campaign_id,
             "scored_keys": [f"{a}_seed{s}" for (a, s)
                             in self.schedule.expected_claim_bearing()],
             "checkpoint_sha256s": self.evidence["checkpoint_sha256s"]})
        self.evidence["protected_evaluation_receipt_sha256"] = eval_pre_sha
        try:
            out = run_protected_evaluation(
                self.pkg, self.mode, campaign_id=self.campaign_id,
                protected_records=records, protected_features=protected_features,
                train_records=self.train_records,
                train_features=self.features["train"][self.selected_layer],
                checkpoints=self.checkpoints, receipts_by_key=self.receipts_by_key,
                widths=self._widths(), verb_to_class=self.verb_to_class,
                seeds=self.schedule.seeds, lock=lock,
                surface_baselines_trainval=self.surface_baselines,
                evidence_chain=self.evidence,
                out_path=self.er / "RAW_GATE1_RESULTS.json")
        except BaseException:
            self.sm.transition("PROTECTED_BURNED", binding_kind="protected_lock",
                               binding_sha256=self.evidence[
                                   "protected_lock_receipt_sha256"],
                               reason="FAILURE")
            raise
        self.raw_results_sha = out["results_sha256"]
        self.sm.transition("PROTECTED_BURNED", binding_kind="protected_lock",
                           binding_sha256=out["lock_receipt"]["lock_receipt_sha256"])
        self.sm.transition("RESULTS_SEALED", binding_kind="raw_results",
                           binding_sha256=self.raw_results_sha)

    def _status(self):
        cmd = [sys.executable, str(self.pkg / "tools" / "emit_gate1_status.py"),
               str(self.er / "RAW_GATE1_RESULTS.json"),
               "--evidence-root", str(self.er),
               "--out", str(self.er / "GATE1_STATUS.json")]
        if self.mode == "SYNTHETIC_CONFORMANCE":
            cmd.append("--conformance")
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=self.pkg)
        if r.returncode != 0:
            raise RuntimeError(f"STATUS_PROGRAM_REFUSED: {r.stdout}{r.stderr}")
        self.status_sha = sha256_file(self.er / "GATE1_STATUS.json")
        self.final["status"] = json.loads(
            (self.er / "GATE1_STATUS.json").read_text("utf-8"))
        self.sm.transition("STATUS_EMITTED", binding_kind="status",
                           binding_sha256=self.status_sha)

    def _seal_and_shutdown(self):
        cost_sha = _write_json(self.er / "cost_report.json", self.cost.report())
        # instantiate CAMPAIGN_MANIFEST.schema.json exactly (adversarial-review
        # fix: the sealed receipt is now a schema-valid CAMPAIGN_MANIFEST)
        manifest = {
            "campaign_id": self.campaign_id, "mode": self.mode,
            "package_commit_sha": self.expected_commit,
            "final_state": "RESULTS_SEALED",
            "transition_count": self.sm.index,
            "transition_chain_sha256": self.sm.chain_digest(),
            "container_prep_approval_sha256": sha256_file(self.prep_approval_path),
            "execution_approval_sha256": self.evidence["execution_approval_sha256"],
            "owner_key_id": self.evidence["owner_key_id"],
            "container_prep_receipt_sha256":
                self.evidence["container_prep_receipt_sha256"],
            "run_schedule_sha256": self.evidence["run_schedule_sha256"],
            "selected_layer_receipt_sha256":
                self.evidence["selected_layer_receipt_sha256"],
            "job_receipt_sha256s": dict(self.evidence["job_receipt_sha256s"]),
            "protected_lock_receipt_sha256":
                self.evidence["protected_lock_receipt_sha256"],
            "protected_evaluation_receipt_sha256":
                self.evidence["protected_evaluation_receipt_sha256"],
            "raw_results_sha256": self.raw_results_sha,
            "status_sha256": self.status_sha,
            "cost_report_sha256": cost_sha,
            "campaign_receipt_sha256": self.evidence["campaign_receipt_sha256"]}
        seal_sha = _write_json(self.er / "campaign_receipt_final.json", manifest)
        self._final_uploads = ["RAW_GATE1_RESULTS.json", "GATE1_STATUS.json",
                               "cost_report.json", "campaign_receipt_final.json"]
        self.sm.transition("SHUTDOWN_REQUESTED", binding_kind="campaign_receipt",
                           binding_sha256=seal_sha)
        self.final["campaign_receipt_sha256"] = seal_sha

    def run(self) -> dict:
        """The 30-step path. Termination is guaranteed by a real finally that
        always routes through the registered shutdown path (uploads + terminate),
        whether the campaign completed or failed at any step."""
        completed = False
        try:
            self._beat()
            self._design_verified()
            self._authority()
            self._aws_identity()
            self._data()
            self._model()
            self._activations()
            self._layer_selection()
            self._training()
            self._protected()
            self._status()
            self._seal_and_shutdown()
            completed = True
            return {"final_state": "TERMINATED", "campaign_id": self.campaign_id,
                    "chain_digest": self._terminate("CAMPAIGN_COMPLETE"),
                    "status": self.final["status"],
                    "campaign_receipt_sha256": self.final["campaign_receipt_sha256"]}
        except BaseException as exc:
            fail_sha = sha256_obj({"failure": f"{type(exc).__name__}: {exc}"})
            _write_json(self.er / "campaign_failure_receipt.json",
                        {"campaign_id": self.campaign_id,
                         "failure": f"{type(exc).__name__}: {exc}",
                         "state_at_failure": self.sm.state})
            try:
                if self.sm.state not in ("SHUTDOWN_REQUESTED", "TERMINATED"):
                    self.sm.transition("SHUTDOWN_REQUESTED",
                                       binding_kind="failure_receipt",
                                       binding_sha256=fail_sha, reason="FAILURE")
            except Exception:
                pass                                   # even a state error must
                                                       # not block termination
            raise
        finally:
            # THE registered end path ALWAYS runs (owner section 4 step 30):
            # write the final receipt, upload evidence, request termination.
            # Reached on success (completed=True) and on every failure.
            if not getattr(self, "_finalized", False):
                self._finalized = True
                reason = ("CAMPAIGN_COMPLETE" if completed
                          else "CAMPAIGN_FAILED")
                uploads = [self.er / p for p in getattr(self, "_final_uploads", [])
                           if (self.er / p).is_file()]
                dest = (f"{self.approval['s3_prefix']}{self.campaign_id}"
                        if self.approval else "results/" + self.campaign_id)
                receipt = {"campaign_id": self.campaign_id, "completed": completed,
                           "final_chain_digest": self.sm.chain_digest()}
                self.shutdown.finalize(
                    receipt, self.er / "shutdown_receipt.json", uploads, dest,
                    reason)

    def _terminate(self, reason: str) -> str:
        chain = self.sm.chain_digest()
        if self.sm.state == "SHUTDOWN_REQUESTED":
            self.sm.transition("TERMINATED", binding_kind="termination",
                               binding_sha256=chain)
        return self.sm.chain_digest()
