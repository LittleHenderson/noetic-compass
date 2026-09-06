"""Pure admission checks, including a trap on private reads in the trainer."""
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import pytest
from cas_meta2.contrast_v6 import curriculum as c, data as d

CONFIG = c.Config(train_flat=32, train_pairs_per_cell=8, validation_flat=8,
                  validation_pairs_per_cell=2, test_triplets=3)
KW = {'seed': 926603, 'config': CONFIG, 'excluded': frozenset()}


@pytest.fixture(scope='module')
def original(tmp_path_factory):
    root = tmp_path_factory.mktemp('contrast_data')
    source, bundle = root/'source', root/'bundle'
    c.write(source, **KW)
    pin = sha256((source/'manifest.json').read_bytes()).hexdigest()
    receipt = d.prepare_training_bundle(source, bundle, expected_sha256=pin, **KW)
    return source, bundle, pin, receipt


@pytest.fixture
def local(tmp_path, original):
    source, bundle, pin, receipt = original
    shutil.copytree(source, tmp_path/'source')
    shutil.copytree(bundle, tmp_path/'bundle')
    return tmp_path/'source', tmp_path/'bundle', pin


def reseal(folder, name, value):
    raw = c.canonical(value)+b'\n'
    (folder/name).write_bytes(raw)
    m = d.decode((folder/'manifest.json').read_bytes())
    m['sha256'][name] = d.digest(raw)
    (folder/'manifest.json').write_bytes(c.canonical(m)+b'\n')
    return d.digest((folder/'manifest.json').read_bytes())


def test_parent_export_matches_pin_and_excludes_private(original):
    source, bundle, pin, receipt = original
    assert {p.name for p in bundle.iterdir()} == {*d.PUBLIC_FILES, 'manifest.json'}
    assert receipt['parent_private_validation_completed'] is True
    assert receipt['private_labels_read_by_loader'] is False
    assert receipt['splits']['train']['tasks'] == 96
    assert receipt['splits']['validation']['tasks'] == 24
    assert receipt['splits']['test']['tasks'] == 9
    for name in (*d.PUBLIC_FILES, 'manifest.json'):
        assert (source/name).read_bytes() == (bundle/name).read_bytes()


def test_loader_never_reads_private_or_calls_symbolic_parser(original, monkeypatch):
    _, bundle, pin, _ = original
    opened = []
    real_open = Path.open
    def watched(path, *args, **kwargs):
        assert path.name != 'test_private.json'
        opened.append(path.name)
        return real_open(path, *args, **kwargs)
    def no_parser(*args, **kwargs):
        raise AssertionError('SYMBOLIC_PARSER_IN_TRAINER')
    monkeypatch.setattr(Path, 'open', watched)
    monkeypatch.setattr(c, 'parse_problem', no_parser)
    monkeypatch.setattr(c, 'generate', no_parser)
    loaded = d.load_training_bundle(bundle, expected_sha256=pin, **KW)
    assert set(d.PUBLIC_FILES) <= set(opened)
    assert loaded['tokenizer'].fitted_examples == 96
    assert loaded['tokenizer'].fitted_public_sha256 == d.digest(c.canonical([t['public'] for t in loaded['train']]))
    assert all(set(p) == {'problem', 'observations'} for p in loaded['test_public'])
    assert 'torch' not in sys.modules and 'boto3' not in sys.modules


@pytest.mark.parametrize('value', ['0'*64, '', None, True])
def test_external_pin_required(original, value):
    with pytest.raises(ValueError, match='EXTERNAL_MANIFEST_DIGEST_MISMATCH'):
        d.load_training_bundle(original[1], expected_sha256=value, **KW)


@pytest.mark.parametrize('name', d.PUBLIC_FILES)
def test_modified_bytes_rejected(local, name):
    _, bundle, pin = local
    with (bundle/name).open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(ValueError, match='DATA_FILE_DIGEST_MISMATCH'):
        d.load_training_bundle(bundle, expected_sha256=pin, **KW)


@pytest.mark.parametrize('field', ['seed', 'config', 'dataset_id', 'splits', 'source', 'sha256', 'neural_execution', 'extra'])
def test_even_repinned_invalid_manifest_is_rejected(local, field):
    _, bundle, _ = local
    m = d.decode((bundle/'manifest.json').read_bytes())
    if field == 'seed': m[field] = True
    elif field == 'config': m[field]['train_flat'] += 1
    elif field == 'dataset_id': m[field] = '0'*64
    elif field == 'splits': m[field]['train']['depths']['2'] += 1
    elif field == 'source': m[field] = {}
    elif field == 'sha256': m[field].pop('test_private.json')
    elif field == 'neural_execution': m[field] = True
    else: m[field] = 'unexpected'
    raw = c.canonical(m)
    (bundle/'manifest.json').write_bytes(raw)
    with pytest.raises(ValueError):
        d.load_training_bundle(bundle, expected_sha256=d.digest(raw), **KW)


def test_private_file_in_training_directory_refused(local):
    source, bundle, pin = local
    shutil.copyfile(source/'test_private.json', bundle/'test_private.json')
    with pytest.raises(ValueError, match='DATA_DIRECTORY_CONTENTS_INVALID'):
        d.load_training_bundle(bundle, expected_sha256=pin, **KW)


def test_public_test_cannot_carry_gold_even_when_repinned(local):
    source, bundle, _ = local
    publics = d.decode((bundle/'test_public.json').read_bytes())
    publics[0]['target'] = d.decode((source/'test_private.json').read_bytes())[0]['target']
    pin = reseal(bundle, 'test_public.json', publics)
    with pytest.raises(ValueError, match='PUBLIC_INPUT_FIELDS_INVALID'):
        d.load_training_bundle(bundle, expected_sha256=pin, **KW)


def test_parent_rejects_public_private_mapping_change(local, tmp_path):
    source, _, _ = local
    publics = d.decode((source/'test_public.json').read_bytes())
    publics[0], publics[1] = publics[1], publics[0]
    pin = reseal(source, 'test_public.json', publics)
    with pytest.raises(ValueError, match='PUBLIC_PRIVATE_MAPPING_MISMATCH'):
        d.prepare_training_bundle(source, tmp_path/'new', expected_sha256=pin, **KW)
    assert not (tmp_path/'new').exists()


def test_parent_rejects_private_target_change(local, tmp_path):
    source, _, _ = local
    private = d.decode((source/'test_private.json').read_bytes())
    private[0]['target']['binding'] = (private[0]['target']['binding'] + 1) % 3
    pin = reseal(source, 'test_private.json', private)
    with pytest.raises(ValueError):
        d.prepare_training_bundle(source, tmp_path/'new', expected_sha256=pin, **KW)
    assert not (tmp_path/'new').exists()


def test_no_overwrite(local):
    source, bundle, pin = local
    before = {p.name: p.read_bytes() for p in bundle.iterdir()}
    with pytest.raises(ValueError, match='NEW_TRAINING_BUNDLE_REQUIRED'):
        d.prepare_training_bundle(source, bundle, expected_sha256=pin, **KW)
    assert before == {p.name: p.read_bytes() for p in bundle.iterdir()}


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_ambiguous_json_refused(raw):
    with pytest.raises(ValueError):
        d.decode(raw)


def test_link_refused(original, monkeypatch):
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self.name == 'train.json')
    with pytest.raises(ValueError, match='DATA_LINK_REFUSED'):
        d.load_training_bundle(original[1], expected_sha256=original[2], **KW)


def test_file_size_bound(local, monkeypatch):
    monkeypatch.setattr(d, 'MAX_FILE_BYTES', 10)
    with pytest.raises(ValueError, match='DATA_FILE_BOUND'):
        d.load_training_bundle(local[1], expected_sha256=local[2], **KW)


def test_actual_training_count_not_just_manifest(local):
    _, bundle, _ = local
    tasks = d.decode((bundle/'train.json').read_bytes())
    tasks.pop()
    pin = reseal(bundle, 'train.json', tasks)
    with pytest.raises(ValueError, match='ACTUAL_TRAIN_DEPTH_COUNTS_MISMATCH'):
        d.load_training_bundle(bundle, expected_sha256=pin, **KW)


def test_registered_counts_allow_unequal_depths():
    counts = d.expected_splits(c.Config())
    assert counts['train']['depths'] == {'1': 128, '2': 256, '3': 256}
    assert counts['train']['tasks'] == 640
