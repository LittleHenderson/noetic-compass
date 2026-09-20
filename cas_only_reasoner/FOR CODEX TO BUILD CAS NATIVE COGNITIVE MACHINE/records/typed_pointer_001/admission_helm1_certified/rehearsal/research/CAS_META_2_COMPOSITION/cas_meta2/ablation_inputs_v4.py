"""Read pinned retrospective inputs without deserializing models or exposing gold.

This is an input boundary, not an OS sandbox or a completed GPU runner.
"""
from hashlib import sha256
import json
from pathlib import Path
import stat
import zipfile

ARCHIVE_SHA256 = 'bbb538f9a6cad0ecde46106f542edac9dd64e3188568cb96b2ca550ff854ee93'
ARCHIVE_BYTES = 6444247
CHECKPOINTS = frozenset('candidate_' + family + '_' + state + '.pt'
                        for family in ('cas', 'generic') for state in ('initial', 'best'))
PUBLIC_MEMBERS = CHECKPOINTS | {'tokenizer.json', 'checkpoints.json', 'training_receipt.json',
                               'dataset/test_public.json'}
ALL_MEMBERS = PUBLIC_MEMBERS | {'predictions.jsonl', 'predictions_seal.json',
                               'dataset/test_private.json', 'dataset/dataset_manifest.json'}


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('ABLATION_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('ABLATION_NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_prediction_inputs(archive, names):
    """Return only requested public-side bytes from the exact preserved archive.

    Validate the entire compressed artifact identity, but never decompress or
    parse private targets or earlier predictions. No extraction or torch import.
    Each invocation checks the same open file before opening its ZIP directory.
    """
    names = tuple(names)
    if not names or len(names) != len(set(names)) or not set(names) <= PUBLIC_MEMBERS:
        raise ValueError('ABLATION_PREDICTION_MEMBER_FORBIDDEN')
    path = Path(archive).absolute()
    if any(part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction())
           for part in (path, *path.parents)):
        raise ValueError('ABLATION_INPUT_LINK_REFUSED')
    with path.open('rb') as stream:
        if stream.seek(0, 2) != ARCHIVE_BYTES:
            raise ValueError('ABLATION_ARCHIVE_SIZE_MISMATCH')
        stream.seek(0)
        digest = sha256()
        while block := stream.read(1024 * 1024):
            digest.update(block)
        if digest.hexdigest() != ARCHIVE_SHA256:
            raise ValueError('ABLATION_ARCHIVE_DIGEST_MISMATCH')
        stream.seek(0)
        with zipfile.ZipFile(stream) as bundle:
            entries = bundle.infolist()
            expected = ALL_MEMBERS | {'input_manifest.json'}
            if len(entries) != len(expected) or {entry.filename for entry in entries} != expected:
                raise ValueError('ABLATION_ARCHIVE_MEMBERS_MISMATCH')
            for entry in entries:
                if (entry.file_size > 16 * 1024**2 or entry.flag_bits & 1
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise ValueError('ABLATION_ARCHIVE_MEMBER_UNSAFE')
            manifest = _json(bundle.read('input_manifest.json'))
            if (manifest['schema'] != 'cas-meta2-decoder-ablation-inputs/0.1'
                    or manifest['purpose'] != 'RETROSPECTIVE_DECODER_DIAGNOSTIC'
                    or manifest['training_permitted'] is not False
                    or manifest['fresh_held_out_claim_permitted'] is not False
                    or manifest['source_release_accepted'] is not False
                    or manifest['previously_exposed_test_data'] is not True
                    or manifest['task_count'] != 72
                    or set(manifest['members']) != ALL_MEMBERS):
                raise ValueError('ABLATION_MANIFEST_BOUNDARY_MISMATCH')
            result = {}
            for name in names:
                raw = bundle.read(name)
                record = manifest['members'][name]
                if len(raw) != record['bytes'] or sha256(raw).hexdigest() != record['sha256']:
                    raise ValueError('ABLATION_MEMBER_DIGEST_MISMATCH')
                result[name] = raw
    return result
