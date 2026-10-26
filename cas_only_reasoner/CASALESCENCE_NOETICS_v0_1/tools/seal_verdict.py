"""Mechanical checks, shuffle, ids and seal for the verdict passages. Plain Python; reads no passage for content.

Usage: seal_verdict.py <writer_state.json> <verdict_dir> <guide.md> <plan.md> <chunk_size>
"""
import datetime
import hashlib
import json
import random
import re
import sys
from pathlib import Path

FORBIDDEN = ['cause', 'effect', 'trigger', 'positive', 'negative', 'vibration', 'rhythm', 'idea', 'mind', 'noetic', 'resonate', 'resonance']
SEED = 20261005


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))


def main(state_path, out_dir, guide_path, plan_path, chunk_size):
    out = Path(out_dir)
    assert not (out / 'SEAL.json').exists(), 'ALREADY_SEALED'
    state = json.loads(Path(state_path).read_text(encoding='utf-8'))
    rows = [row for start in sorted(state['chunks'], key=int) for row in state['chunks'][start]]
    kept, dropped, seen = [], [], set()
    for row in rows:
        text = row['text'].strip()
        words = len(text.split())
        reason = None
        if any(re.search(r'\b' + w + r'\w*\b', text, flags=re.I) for w in FORBIDDEN):
            reason = 'forbidden word'
        elif words < 30 or words > 120:
            reason = 'length %d words' % words
        elif text in seen:
            reason = 'exact repeat'
        if reason:
            dropped.append({'kind': row['kind'], 'reason': reason})
        else:
            seen.add(text)
            kept.append({'kind': row['kind'], 'setting': row['setting'], 'text': text})
    random.Random(SEED).shuffle(kept)
    for index, row in enumerate(kept, 1):
        row['id'] = 'V%03d' % index
    dump(out / 'passages_sealed.json', [{'id': r['id'], 'text': r['text']} for r in kept])
    dump(out / 'passages_kinds_HIDDEN_FROM_LABELERS.json', [{'id': r['id'], 'kind': r['kind'], 'setting': r['setting'], 'text': r['text']} for r in kept])
    team = out / 'team_a'
    team.mkdir(exist_ok=True)
    size = int(chunk_size)
    chunks = []
    for number, start in enumerate(range(0, len(kept), size), 1):
        name = 'chunk_%02d.json' % number
        dump(team / name, [{'id': r['id'], 'text': r['text']} for r in kept[start:start + size]])
        chunks.append({'file': name, 'first': kept[start]['id'], 'last': kept[min(start + size, len(kept)) - 1]['id'],
                       'passages': len(kept[start:start + size])})
    kinds = {}
    for r in kept:
        kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
    tools = Path(__file__).resolve().parent
    seal = {'schema': 'casalescence/label-agreement-verdict-seal/1',
            'sealed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'writer': {'provider': state.get('provider'), 'model': state.get('model')},
            'passages_written': len(rows), 'passages_dropped': dropped, 'passages_kept': len(kept),
            'kept_by_writer_kind': dict(sorted(kinds.items())),
            'passages_sealed_sha256': sha(out / 'passages_sealed.json'),
            'guide': {'file': Path(guide_path).name, 'sha256': sha(guide_path)},
            'plan': {'file': Path(plan_path).name, 'sha256': sha(plan_path)},
            'tools_sha256': {name: sha(tools / name) for name in ('verdict.py', 'label_outside.py', 'write_verdict_passages.py', 'seal_verdict.py')},
            'team_a_chunks': chunks, 'shuffle_seed': SEED,
            'no_label_existed_when_sealed': not any(team.glob('labels_*.json')) and not (out / 'labels_team_b.json').exists()}
    dump(out / 'SEAL.json', seal)
    print(json.dumps({k: seal[k] for k in ('passages_written', 'passages_kept', 'kept_by_writer_kind', 'passages_sealed_sha256',
                                           'no_label_existed_when_sealed')}, indent=1))
    print('dropped:', len(dropped), [d['reason'] for d in dropped][:12], '| chunks:', len(chunks))


if __name__ == '__main__':
    main(*sys.argv[1:6])
