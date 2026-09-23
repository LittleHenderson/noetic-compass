"""AWS preflight (runs FIRST on the machine, before any real job). Fails fast and cheap if anything the jobs need is
missing: CUDA, the two wheels, a bundled file, the course load, one Helm forward on an analogy record and on one
record of every kind. Records every file opened (an audit hook), so the NEXT bundle can be built from a measured
list. Forward passes only; nothing is trained or saved.

    python -B records/helm_eval_design_20260923/aws_probe_job/preflight.py --out out/preflight.json
"""
import argparse
import json
import os
import pathlib
import sys
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
OPENED = set()


def hook(event, args):
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        try:
            rel = pathlib.Path(os.fsdecode(args[0])).resolve().relative_to(PACKAGE).as_posix()
            OPENED.add(rel)
        except (ValueError, OSError):
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.addaudithook(hook)
    t0 = time.monotonic()
    report = {"schema": "claude.aws-probe-preflight/0.1", "steps": {}}

    def step(name, fn):
        s = time.monotonic()
        value = fn()
        report["steps"][name] = {"ok": True, "seconds": round(time.monotonic() - s, 3), "value": value}
        print("PREFLIGHT %s ok (%.1f s): %s" % (name, time.monotonic() - s, str(value)[:200]), flush=True)
        return value

    try:
        import torch
        step("cuda", lambda: {"available": torch.cuda.is_available(), "device": torch.cuda.get_device_name(0),
                              "torch": torch.__version__, "cuda": torch.version.cuda})
        if not torch.cuda.is_available():
            raise SystemExit("GPU_REQUIRED")
        torch.use_deterministic_algorithms(True, warn_only=True)
        sys.dont_write_bytecode = True
        for p in (PACKAGE, PACKAGE / "research" / "CAS_META_2_COMPOSITION"):
            sys.path.insert(0, str(p))
        import casformer, cas_cjt  # noqa: E401 -- the two wheels
        step("wheels", lambda: {"casformer": casformer.__file__, "cas_cjt": cas_cjt.__file__})
        from cas_meta2.typed_teaching import pointer_contract as contract, pointer_inputs, pointer_learner as PL, slots
        from cncm.typed_matched_worker import _framework
        device = torch.device("cuda", 0)
        holder = {}

        def load():
            holder["frozen"] = contract.load_material(PACKAGE)[0]
            return holder["frozen"]["course_digest"]
        step("course_load", load)
        frozen = holder["frozen"]
        packets = dict(contract.public_packets(frozen))
        model = PL._build_container(torch, _framework(torch, device, 20260917), device)
        model.eval()
        step("container", lambda: sum(int(p.numel()) for p in model.parameters()))
        tagger = PL.role_tagger(str(PACKAGE))
        by_kind = {}
        for rid in sorted(packets):
            by_kind.setdefault(packets[rid]["record"]["query"]["kind"], rid)

        def forward_each_kind():
            out = {}
            with torch.no_grad():
                for kind, rid in sorted(by_kind.items()):
                    plan = slots.compile_slots(packets[rid])
                    reading = pointer_inputs.read_packet(packets[rid]); reading["_device"] = device
                    ind = tagger.indicators(packets[rid]) if reading["query"]["kind_name"] == "role_set" else [0] * PL.CLAUSE_COUNT
                    rows = PL.GraphForward(torch, model, reading, device).head_logits(plan, ind)
                    out[kind] = len(rows)
            return out
        step("forward_every_kind", forward_each_kind)
        for ck in ("receipt_20260917", "receipt_20260918", "receipt_20260919"):
            for name in ("initial.pt", "final.pt"):
                path = PACKAGE / "records/typed_pointer_001" / ck / "checkpoints" / name
                report["steps"].setdefault("checkpoints", {"ok": True, "value": {}})["value"][ck + "/" + name] = path.is_file()
        if not all(report["steps"]["checkpoints"]["value"].values()):
            raise SystemExit("CHECKPOINT_MISSING")
        report["verdict"] = "PREFLIGHT_PASS"
    except BaseException as error:  # noqa: BLE001 -- the report must record ANY failure, then fail the job
        report["verdict"] = "PREFLIGHT_FAIL"
        report["error"] = "%s: %s" % (type(error).__name__, str(error)[:500])
    report["opened_files"] = sorted(OPENED)
    report["seconds"] = round(time.monotonic() - t0, 3)
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(report, indent=1, sort_keys=True, default=str))
    print(report["verdict"], report.get("error", ""), flush=True)
    sys.exit(0 if report["verdict"] == "PREFLIGHT_PASS" else 1)


if __name__ == "__main__":
    main()
