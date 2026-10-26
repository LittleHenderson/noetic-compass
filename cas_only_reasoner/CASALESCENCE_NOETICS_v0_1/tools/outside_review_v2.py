"""Ask an outside model for one review round. The question comes from a text file. BLOCKER/MAJOR only.

Sends only the question and the named documents. Never prints or stores a key.
Stores the model name the service put in its reply, the token usage and the sha256 of every file sent.

Usage: outside_review_v2.py <model> <ask.txt> <output.md> <file1> [<file2> ...]
"""
import datetime
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = 'https://api.deepseek.com/chat/completions'
KEY_NAME = 'DEEPSEEK_API_KEY'
NL = chr(10)


def read_key():
    key = os.environ.get(KEY_NAME)
    if key:
        return key
    with open(os.path.join(os.path.expanduser('~'), '.cas_llm_keys.env'), encoding='utf-8') as stream:
        for line in stream:
            line = line.strip()
            if line.startswith('export '):
                line = line[7:].strip()
            if line.startswith(KEY_NAME + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('KEY_NOT_FOUND')


def main(model, ask_path, out_path, *files):
    if not files:
        raise SystemExit('NO_FILES')
    ask = Path(ask_path).read_text(encoding='utf-8').strip()
    sent = []
    parts = []
    for name in files:
        raw = Path(name).read_bytes()
        sent.append({'file': Path(name).name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        parts.append('===== DOCUMENT: %s =====' % Path(name).name + NL + raw.decode('utf-8'))
    body = json.dumps({'model': model, 'max_tokens': 32000,
                       'messages': [{'role': 'user', 'content': ask + NL + NL + (NL + NL).join(parts)}]}).encode('utf-8')
    request = urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + read_key()})
    try:
        with urllib.request.urlopen(request, timeout=1500) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as error:
        print(json.dumps({'http_error': error.code, 'body': error.read().decode('utf-8', 'replace')[:600]}))
        raise SystemExit(2)
    choice = data['choices'][0]
    text = choice['message'].get('content') or ''
    record = {'asked_for_model': model, 'answered_by_model': data.get('model'), 'finish_reason': choice.get('finish_reason'),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
              'usage': {k: v for k, v in (data.get('usage') or {}).items() if isinstance(v, int)},
              'ask_sha256': hashlib.sha256(Path(ask_path).read_bytes()).hexdigest(), 'files_sent': sent}
    header = ['# Outside review', '', 'Asked for model: `%s`. Answered by model: `%s`. Finish reason: `%s`.' % (
        model, record['answered_by_model'], record['finish_reason']), '', 'Files sent:', '']
    header += ['- `%s` (%d bytes, sha256 `%s`)' % (s['file'], s['bytes'], s['sha256']) for s in sent]
    Path(out_path).write_text(NL.join(header) + NL + NL + '## Reply, word for word' + NL + NL + text + NL, encoding='utf-8', newline=NL)
    Path(out_path + '.receipt.json').write_text(json.dumps(record, indent=1) + NL, encoding='utf-8', newline=NL)
    print(json.dumps({k: record[k] for k in ('asked_for_model', 'answered_by_model', 'finish_reason', 'usage')}))
    if not text.strip():
        raise SystemExit('EMPTY_REPLY')


if __name__ == '__main__':
    main(*sys.argv[1:])
