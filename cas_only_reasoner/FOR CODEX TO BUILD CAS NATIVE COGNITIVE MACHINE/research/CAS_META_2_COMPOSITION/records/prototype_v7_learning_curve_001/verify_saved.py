"""Read-only verification of saved CSV and Markdown against the pinned receipt."""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_SHA = '732456f953d87fd494dc31358a1758677b63c16bea4c83506ff97caacfb2baec'


def main():
    parser = argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--render-receipt',required=True,type=Path)
    parser.add_argument('--sha256',required=True)
    args = parser.parse_args()
    path = HERE/'build.py'
    if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != BUILD_SHA:
        raise ValueError('FROZEN_RENDERER_CHANGED')
    spec = importlib.util.spec_from_file_location('_verified_learning_renderer',path)
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    receipt = b.regular(args.render_receipt)
    b.require(receipt.parent.resolve().is_relative_to(HERE.resolve())
        and b.file_hash(receipt) == args.sha256, 'EXTERNAL_RENDER_RECEIPT_PIN')
    saved = b.decode(receipt.read_bytes())
    b.require(saved['status'] == 'PINNED_TRAINING_CURVES_RENDERED_AND_VERIFIED'
        and saved['input_receipt_sha256'] == b.RECEIPT_SHA and saved['helper_sha256'] == BUILD_SHA,
        'RENDER_RECEIPT_IDENTITY')
    b.require(b.file_hash(b.EXPECTED_RECEIPT) == b.RECEIPT_SHA, 'EXTERNAL_TRAINING_RECEIPT_PIN')
    source = b.decode(b.EXPECTED_RECEIPT.read_bytes()); b.validate(source)
    names = ('learning_curve.csv','checkpoints.csv','learning_curve.md')
    b.require(set(saved['output_files_sha256']) == set(names), 'RENDER_OUTPUT_COVERAGE')
    for name in names:
        b.require(b.file_hash(receipt.parent/name) == saved['output_files_sha256'][name], 'SAVED_OUTPUT_HASH_CHANGED')
    checks = b.verify_rendered(source, *((receipt.parent/name).read_text(encoding='utf-8') for name in names))
    b.require(checks == saved['checks'] and saved['checkpoint_map'] == source['training_gate']['checkpoints']
        and saved['measured_epochs'] == sorted({row['epoch'] for row in source['curves']}), 'SAVED_RECOUNT_COPY')
    b.require(b.file_hash(receipt) == args.sha256 and b.file_hash(b.EXPECTED_RECEIPT) == b.RECEIPT_SHA,
        'VERIFICATION_INPUT_CHANGED')
    print(json.dumps({'status':'SAVED_CURVES_INDEPENDENT_RENDER_CHECK_PASSED','checks':checks,
        'render_receipt_sha256':args.sha256,'training_receipt_sha256':b.RECEIPT_SHA,
        'writes':False,'model_or_provider_calls':False},sort_keys=True,indent=2))


if __name__ == '__main__': main()
