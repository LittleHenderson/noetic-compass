"""Synthetic byte-only failure packets; no native or learning claims."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
import pytest

pytestmark = pytest.mark.not_gpu
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def area():
    with tempfile.TemporaryDirectory(prefix='ablation_inspector_test_', dir=ROOT / 'records') as directory:
        yield Path(directory)


def packet(path, *, unsafe=False):
    source = json.loads((ROOT / 'records/aws_ablation_v4_source_001/source.receipt.json').read_bytes())
    name, raw = ('../escape' if unsafe else 'cloud_job/failure.json'), b'{"synthetic_failure":true}\n'
    row = {'path': name, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
    index_raw = json.dumps(row, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    record = {'job': 'cas-meta2-20260906025939-e933c868', 'source_sha': source['source_sha'],
        'baseline_sha': source['baseline_sha'], 'archive_sha256': source['archive_sha256'],
        'experiment': source['launch_manifest']['experiment'], 'returncode': 1, 'partial_evidence': False,
        'smoke_only': False, 'original_file_count': 1, 'included_full_file_count': 1,
        'omitted_full_file_count': 0, 'original_bytes': len(raw), 'index_entries_omitted': 0,
        'index_entries': [row], 'original_file_index_sha256': sha256(index_raw).hexdigest()}
    with zipfile.ZipFile(path, 'x') as archive:
        archive.writestr(name, raw)
        archive.writestr('artifact_collection_receipt.json', json.dumps(record))
    return sha256(path.read_bytes()).hexdigest()


def invoke(area, digest, extract=False):
    command = [sys.executable, '-B', '-m', 'tools.inspect_ablation_packet_v4',
        '--packet', str(area / 'packet.zip'), '--sha256', digest, '--output', str(area / 'inspection')]
    if extract: command += ['--extract', str(area / 'packet_extracted')]
    return subprocess.run(command, cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '',
        'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True, timeout=60)


def test_failure_packet_is_hashed_and_extracted_without_promotion(area):
    result = invoke(area, packet(area / 'packet.zip'), extract=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads((area / 'inspection/inspection_receipt.json').read_bytes())
    assert receipt['status'] == 'RETROSPECTIVE_FAILED_OR_PARTIAL_RUN'
    assert receipt['archive_safety_and_all_included_bytes_checked'] is True
    assert receipt['original_full_index_verified'] is True
    assert receipt['extraction']['files_verified'] == 2
    assert receipt['learning_accepted'] is False and receipt['stored_semantic_audit_completed'] is False
    assert (area / 'packet_extracted/cloud_job/failure.json').read_bytes() == b'{"synthetic_failure":true}\n'


def test_wrong_external_packet_hash_is_refused(area):
    packet(area / 'packet.zip')
    result = invoke(area, '0' * 64)
    assert result.returncode != 0 and 'PACKET_SIZE_OR_SHA_MISMATCH' in result.stderr
    assert not (area / 'inspection').exists()


def test_unsafe_member_is_refused_before_extraction(area):
    result = invoke(area, packet(area / 'packet.zip', unsafe=True), extract=True)
    assert result.returncode != 0 and 'DOT_OR_EMPTY_MEMBER_COMPONENT' in result.stderr
    assert not (area / 'packet_extracted').exists()
