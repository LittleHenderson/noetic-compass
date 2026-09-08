"""Export one exact, untrained v2 lesson under an enforced pure-Python guard."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ROOT / "records/teaching_cycle_001"
DEFAULT_OUTPUT = ALLOWED / "lesson_v2_001"
TRAIN = ALLOWED / "material_001/teaching/train.json"
TRAIN_SHA256 = "e51015ba0ee3ac05ed8526f51a468d48641d5df4f0c33c3a96f989d04ebb54c5"
FORBIDDEN = frozenset(("torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt",
                      "cas_meta", "boto3", "botocore", "tensorflow", "jax"))
SOURCES = (
    "tools/export_teaching_cycle_lesson.py", "cas_meta2/teaching_cycle/guided_application.py",
    "cas_meta2/teaching_cycle/lesson_contract.py", "cas_meta2/teaching_cycle/gpu_adapter.py",
    "cas_meta2/policy.py", "cas_meta2/features_v2.py", "cas_meta2/codec.py",
)


def require(condition, reason):
    if not condition:
        raise ValueError("TEACHING_LESSON_EXPORT:" + reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("PURE_EXPORT_FORBIDDEN_IMPORT:" + fullname)


def enable_guard():
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_MODULE_ALREADY_LOADED")
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("PURE_EXPORT_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)


def source_hashes():
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def source_link(filename, symbol):
    """Read source locations without importing the CUDA-only policy module."""
    path = ROOT / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parts = symbol.split(".")
    body = tree.body
    for part in parts:
        node = next(item for item in body if isinstance(item, (ast.FunctionDef, ast.ClassDef))
                    and item.name == part)
        body = node.body
    return f"[{symbol}](<{path.as_posix()}:{node.lineno}>)"


def render_markdown(case, records, token_lengths, head):
    demo = records[0]["demonstration"]
    adapter, policy = "cas_meta2/teaching_cycle/gpu_adapter.py", "cas_meta2/policy.py"
    sections = [
        "# One complete guided teaching lesson — version 2",
        "This is an exact export of prepared teaching material. It has not been delivered to a neural model. "
        "Seven complete stage inputs are shown below; there are no model predictions or learning results here.",
        "## The shared relationship",
        "The required source must reach the correct input role. The source tag identifies what to use; "
        "the slot identifies where it is. Moving the source to another slot changes the binding, not the rule.",
        "This role table is teacher/audit explanation, not an extra student input. "
        "The exact student inputs are the seven text blocks and the observation rows below.",
        "| Role | Technical | Context | Analogy |\n|---|---|---|---|",
    ]
    sections[-1] += "\n" + "\n".join(
        f"| {row['role']} | {row['technical']} | {row['context']} | {row['analogy']} |"
        for row in records[0]["alignment"])
    sections += [
        "## What the student actually receives",
        "Each stage supplies exactly one `public` object: `problem` contains that stage's text, and "
        "`observations` contains the same three rows shown here. The model receives no family ID, stage label, "
        "alignment metadata, or practice target through this public-input path.",
        "The solved demonstration uses a different slot arrangement from this practice task. Its answer "
        "is explained in the public text. The practice answer stays in the separate training target.",
        "### Observation rows shared by all seven stages",
        "```json\n" + json.dumps(records[0]["public"]["observations"], indent=2, allow_nan=False) + "\n```",
    ]
    for index, record in enumerate(records):
        sections += [
            f"### {index + 1}. {record['stage']}",
            f"Exact `public.problem` text; full public input length: {token_lengths[index]} tokens.",
            "```text\n" + record["public"]["problem"] + "\n```",
        ]
    sections += [
        "## Training-only targets and audit metadata",
        "This section is not part of `public`. Do not feed this Markdown document or the full lesson record "
        "to the student as its problem. The adapter extracts only each record's `public` object for prediction.",
        f"Practice family: `{case['family_id']}`. Fixed child: `A`. "
        f"Requested source: `{case['requested_tag']}`. Correct practice target: `BIND{case['target_binding']}`.",
        f"The separate solved demonstration has answer `BIND{demo['target_binding']}`. "
        "This sample was selected because those answers differ; the renderer was not changed for this sample. "
        "Across the curriculum, demonstration and practice answers can also coincide.",
        "The same practice target supervises all seven stage presentations. A training loss can correct a wrong "
        "prediction; no prediction or correction has actually been executed by this exporter.",
        "## Intended parameter update path — source inspection, not an executed update",
        "1. " + source_link(adapter, "validate_records") + " checks each full record against the registered "
        "training plan, then returns separate public inputs and binding targets.",
        "2. " + source_link(adapter, "BindingLearner._logits") + " calls "
        + source_link(policy, "encode_batch") + " with the lossless tokenizer on CUDA, supplies a single "
        "beginning-of-sequence token, and selects only the `BINDING_TOKEN_IDS` logits at decoder position zero.",
        "3. " + source_link(policy, "_ProgramGenerator.embed") + " combines word, input-kind, slot, numeric "
        "and position representations. The candidate's encoder processes them. "
        + source_link(policy, "_ProgramGenerator.decode") + " combines the token head with the learned "
        "`binding_query`/`binding_key` observation pointer.",
        "4. " + source_link(adapter, "BindingLearner.teach") + " computes cross-entropy against the private "
        "practice binding, calls `loss.backward()`, checks the admitted parameter scope, and calls "
        "`AdamW.step()`. It records nonzero gradients, changed parameter names and before/after tensor identities.",
        "5. " + source_link(adapter, "build_matched_learners") + " creates separate CAS and generic candidates. "
        "Its default optimizer receives `model.parameters()`. The admitted scope is the candidate's actual "
        "`requires_grad` names; it is not limited to a standalone binding head. Encoder/control parameters, "
        "embeddings, decoder and pointer can be eligible. Exact touched names require real training receipts.",
        "Accepted weights and the native executor are not loaded or updated by this adapter. "
        "The lesson selects an input for fixed child `A`; it does not prove the child's neural effect.",
        "## What the labels do not establish",
        "`Guided Noetic ^6` in stage five is a textual decomposition lesson. It is not an invocation of native "
        "Noetic ^6 execution. A stage label, a valid mapping, a complete export, or a valid trace does not "
        "demonstrate language understanding, metaphor understanding, native reasoning, or learning.",
        "## What the separate evaluation splits test",
        "The prepared curriculum contains 256 training families and 64 development families. Development "
        "uses fresh instances for readiness/checkpoint selection; it is not the final mastery test.",
        "- `test_fresh`: 64 fresh numeric instances with familiar tags, contexts and task forms.\n"
        "- `test_context`: 64 unseen irrelevant context combinations made from familiar words.\n"
        "- `test_names`: 64 unseen color-plus-shape tag combinations made from familiar words.",
        "These are not unseen program compositions. The fixed-child input-binding skill remains the target. "
        "Final evaluation receives unassisted public problems, not solved lesson text or training targets.",
        "## Export identity",
        f"Repository HEAD inspected: `{head}`. Exact working-source hashes and canonical lesson hashes "
        "are in `receipt.json`; this is not a source-freeze or a training receipt.",
    ]
    return "\n\n".join(sections) + "\n"


def export(destination=DEFAULT_OUTPUT):
    enable_guard()
    sys.path.insert(0, str(ROOT))
    from cas_meta2.codec import canonical_sha256
    from cas_meta2.teaching_cycle.guided_application import make_cycle, validate_cycle, fit_tokenizer
    output = Path(destination).absolute()
    require(output.is_relative_to(ALLOWED) and not output.exists(), "FRESH_RECORD_DIRECTORY_REQUIRED")
    require(not any(path.is_symlink() or getattr(path, "is_junction", lambda: False)()
                    for path in (output, *output.parents)), "LINK_PATH_REJECTED")
    before = source_hashes()
    train_bytes = TRAIN.read_bytes()
    require(sha256(train_bytes).hexdigest() == TRAIN_SHA256, "PREPARED_TRAIN_BYTES_CHANGED")
    head = git("rev-parse", "HEAD").decode().strip()
    prefix = git("rev-parse", "--show-prefix").decode().strip()
    git_train_path = prefix + TRAIN.relative_to(ROOT).as_posix()
    require(git("show", head + ":" + git_train_path) == train_bytes, "TRAIN_BYTES_NOT_COMMITTED")
    training_cases = json.loads(train_bytes)
    selected = None
    for index, case in enumerate(training_cases):
        records = make_cycle(case, assistance="full", curriculum="aligned")
        if records[0]["demonstration"]["target_binding"] != case["target_binding"]:
            selected = index, case, records
            break
    require(selected is not None, "NO_CONTRASTING_SAMPLE")
    index, case, records = selected
    validate_cycle(case, records)
    tokenizer = fit_tokenizer(training_cases)
    lengths = [len(tokenizer.encode_public(record["public"])["ids"]) for record in records]
    require(all(tokenizer.check_round_trip(record["public"]) for record in records), "LOSSLESS_ROUND_TRIP_FAILED")
    require(all(record["public"]["observations"] == records[0]["public"]["observations"]
                for record in records), "SHARED_OBSERVATIONS_CHANGED")
    public_inputs = [record["public"] for record in records]
    full_record = {"schema": "cas-teaching-lesson-export/2", "status": "EXPORTED_NOT_TRAINED",
                   "case": case, "records": records, "boundary": "Teacher/audit record; not a student public input."}
    artifacts = {
        "LESSON.md": render_markdown(case, records, lengths, head).encode("utf-8"),
        "lesson.json": json_bytes(full_record),
        "student_public.json": json_bytes(public_inputs),
    }
    after = source_hashes()
    require(before == after and TRAIN.read_bytes() == train_bytes, "SOURCE_CHANGED_DURING_EXPORT")
    receipt = {
        "schema": "cas-teaching-lesson-export-receipt/2", "status": "EXPORTED_NOT_TRAINED",
        "created_utc": datetime.now(timezone.utc).isoformat(), "command": [sys.executable, *sys.argv],
        "python": sys.version, "cwd": str(Path.cwd()), "repository_head": head,
        "committed_training_path": git_train_path, "training_file_sha256": TRAIN_SHA256,
        "selected_training_index": index, "selection_rule": "first demo binding different from practice binding",
        "case_family_id": case["family_id"], "case_canonical_sha256": canonical_sha256(case),
        "lesson_canonical_sha256": canonical_sha256(full_record),
        "records_canonical_sha256": canonical_sha256(records),
        "student_public_canonical_sha256": canonical_sha256(public_inputs),
        "tokenizer_canonical_sha256": canonical_sha256(tokenizer.to_dict()),
        "stage_canonical_sha256": {record["stage"]: canonical_sha256(record) for record in records},
        "public_input_tokens_by_stage": dict(zip((record["stage"] for record in records), lengths)),
        "full_stages_exported": len(records), "delivered_neural_cycles": 0, "optimizer_steps": 0,
        "source_files_sha256": after, "source_unchanged_during_export": True,
        "pure_import_guard": sorted(FORBIDDEN), "network_and_sqlite_audit_guard": True,
        "artifacts": {name: {"sha256": sha256(payload).hexdigest(), "bytes": len(payload)}
                      for name, payload in artifacts.items()},
        "boundary": "Pure lesson export only. No neural, NumPy, SQLite, network or provider execution.",
    }
    artifacts["receipt.json"] = json_bytes(receipt)
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in artifacts.items():
        with (output / name).open("xb") as stream:
            stream.write(payload)
    require(all((output / name).read_bytes() == payload for name, payload in artifacts.items()), "OUTPUT_READBACK_FAILED")
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_MODULE_LOADED")
    print(json.dumps({"status": receipt["status"], "full_stages_exported": len(records),
                      "delivered_neural_cycles": 0, "receipt": str(output / "receipt.json")}))
    return receipt


if __name__ == "__main__":
    export(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT)
