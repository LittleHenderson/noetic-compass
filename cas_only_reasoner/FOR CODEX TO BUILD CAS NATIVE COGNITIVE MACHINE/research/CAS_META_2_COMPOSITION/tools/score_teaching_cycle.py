"""Pure teacher-side export/scoring CLI; no model or provider execution."""
import argparse
import importlib.abc
import json
from pathlib import Path
import sys

FORBIDDEN = frozenset(("torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt",
                       "cas_meta", "boto3", "botocore", "tensorflow", "jax"))


def main(argv=None):
    if FORBIDDEN.intersection(sys.modules):
        raise RuntimeError("TEACHING_SCORE:FORBIDDEN_MODULE_ALREADY_LOADED")
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("TEACHING_SCORE:FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("TEACHING_SCORE:FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from cas_meta2.teaching_cycle.evaluation import export_public, score_packet, write_fresh_json, _Reader
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export-public", help="Read only pinned public files; export combined prediction inputs.")
    score = commands.add_parser("score", help="Validate the complete sealed packet before opening private targets.")
    for command in (export, score):
        for name in ("material-root", "material-sha256", "output"):
            command.add_argument("--" + name, required=True)
    for name in ("prediction-root", "campaign-summary", "campaign-root", "seal-sha256",
                 "campaign-sha256", "source-sha256", "bundle-manifest-sha256"):
        score.add_argument("--" + name, required=True)
    score.add_argument("--source-root")
    score.add_argument("--source-pins-json", help="Optional externally retained relative-path to SHA256 map.")
    args = parser.parse_args(argv)
    if args.command == "export-public":
        receipt = export_public(args.material_root, args.material_sha256, args.output)
    else:
        output = Path(args.output).absolute()
        if output.is_relative_to(Path(args.prediction_root).absolute()) or output.is_relative_to(Path(args.material_root).absolute()):
            parser.error("--output must be outside the sealed prediction packet and frozen material.")
        source_pins = None if args.source_pins_json is None else _Reader().json(args.source_pins_json)
        result = score_packet(args.prediction_root, args.material_root, args.campaign_summary, args.campaign_root,
            expected_seal_sha256=args.seal_sha256, expected_campaign_sha256=args.campaign_sha256,
            expected_material_sha256=args.material_sha256, expected_source_sha256=args.source_sha256,
            expected_bundle_manifest_sha256=args.bundle_manifest_sha256,
            source_root=args.source_root, source_pins=source_pins)
        receipt = {**write_fresh_json(output, result), "status": result["status"],
                   "native_execution": result["native_execution"], "native_retention": result["native_retention"]}
    if FORBIDDEN.intersection(sys.modules):
        raise RuntimeError("TEACHING_SCORE:FORBIDDEN_MODULE_LOADED")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
