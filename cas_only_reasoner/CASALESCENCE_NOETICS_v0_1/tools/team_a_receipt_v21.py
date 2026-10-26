"""Team A's prompts, labels file and receipt for label-agreement attempt 2, version 2.1.
Plain Python, standard library only. No model, no network, no key.

Plan: 09_LABEL_AGREEMENT_PLAN_v2_1.md, section 10. Team A is one Claude sub-agent for each chunk of passages. A
workflow script starts them. This tool does the parts that must be the same every time; the seal tool hashes it.

MODES
  prompt   Writes, for every chunk, the one text its sub-agent is given: team A's fixed task message with its three
           places filled in, then the labeling guide, then the labeler instructions. Nothing else. The workflow
           script hands that file to the sub-agent unchanged.
  receipt  Run it after the sub-agents have stopped. It
           1. checks that the chunk files, read in order, are the passage file, and that every chunk's prompt file
              is still the text this tool builds from the task message, the guide and the instructions on disk;
           2. joins the chunks' try logs, line for line and in chunk order, into team A's try log;
           3. runs the checker's own "take" over ALL passages with nothing new handed in. That logs no try. The
              checker writes team A's labels file from the try log: one final row for each final passage;
           4. writes the receipt. "complete" is true only when that take run ends with exit code 0 (the checker
              gives 0 only when every passage is final) and every chunk's own labels file holds the same rows.

FILES
  <set folder> is the folder seal_v21.py wrote: passages_practice.json or passages_sealed.json, and team_a/ with
  chunk_NN.json and TASK_MESSAGE.txt. All other files are named from ONE name, L, team A's labels file:
    L.chunk_NN.prompt.txt           the prompt of chunk NN (prompt mode writes it)
    L.chunk_NN.work.json            the sub-agent's working file
    L.chunk_NN.json + .tries.jsonl  that chunk's labels file and try log (the sub-agent's take command writes them)
    L, L.tries.jsonl                team A's labels file and try log (receipt mode writes them)
    L.receipt.json                  the receipt
  L must start with "labels" and end with ".json". A second labeling of the same passages takes a new name L.

THE RECEIPT
  Read by the scorer and the seal tool: guide_sha256, instructions_sha256, checker_sha256, passages_sha256,
  task_message_sha256, tool_sha256, labels_sha256, complete.
  For the record: every chunk file, prompt file, chunk labels file and chunk try log with its sha256; the session
  ids the workflow script names with --session NN=ID (stored as given, not checked); the take command, its exit
  code and its last line.
  WHAT THIS TOOL CANNOT SEE: whether a sub-agent was really given its prompt file and nothing else, and whether it
  ran the checker in another way. The transcripts show that. The receipt says so.

USAGE
  team_a_receipt_v21.py prompt  <set folder> <L> [--guide G --instructions I --checker C --python PY]
  team_a_receipt_v21.py receipt <set folder> <L> [the same options] [--session NN=ID ...]
  --python is the interpreter named in the take command of the prompts; give the same one in both modes.
  Exit codes: 0 done (receipt: "complete": true), 1 receipt written with "complete": false, 2 refused.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOOL = 'team_a_receipt_v21/1'
PLACES = ('<CHUNK FILE>', '<WORKING FILE>', '<TAKE COMMAND>')      # the three places of TEAM_A_TASK in seal_v21.py
PASSAGE_FILES = ('passages_practice.json', 'passages_sealed.json')  # the two names seal_v21.py gives a passage file
NL = chr(10)
NOT_SEEN = ('This tool cannot see whether a sub-agent was given its prompt file unchanged and nothing else, or whether '
            'it ran the checker in another way than its take command. The transcripts show that.')


def refuse(message):
    print('REFUSED: ' + message)
    sys.exit(2)


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else Path(data).read_bytes()).hexdigest()


def write(path, data):
    """Write bytes to a .partial file, then rename. The line ends stay as they are in the bytes: LF."""
    partial = Path(str(path) + '.partial')
    partial.write_bytes(data)
    os.replace(partial, path)


def read_json(path, what):
    try:
        return json.loads(Path(path).read_bytes().decode('utf-8'))
    except (OSError, ValueError) as error:
        refuse('cannot read %s (%s): %s' % (what, path, type(error).__name__))


def shown(path):
    """A path as it stands in a prompt: whole, with forward slashes; in double quotes only when it holds a space."""
    text = Path(path).resolve().as_posix()
    return '"%s"' % text if ' ' in text else text


def layout(args):
    """Everything this tool reads, found from the set folder and the name L. Refuses what does not fit."""
    folder, labels = Path(args.set_folder).resolve(), Path(args.labels).resolve()
    if not labels.name.startswith('labels') or labels.suffix != '.json' or not labels.parent.is_dir():
        refuse('the labels file name must start with "labels" and end with ".json", in a folder that exists (given: %s)' % labels)
    found = [folder / name for name in PASSAGE_FILES if (folder / name).is_file()]
    if len(found) != 1:
        refuse('%s must hold exactly one of %s' % (folder, ' and '.join(PASSAGE_FILES)))
    task = folder / 'team_a' / 'TASK_MESSAGE.txt'
    for path in (task, Path(args.guide), Path(args.instructions), Path(args.checker)):
        if not path.is_file():
            refuse('cannot find %s' % path)
    files = sorted((p for p in (folder / 'team_a').glob('chunk_*.json') if re.fullmatch(r'chunk_\d+\.json', p.name)),
                   key=lambda p: int(p.stem[6:]))
    passages, parts = read_json(found[0], 'the passage file'), [read_json(p, 'a chunk file') for p in files]
    rows = [row for part in parts for row in (part if isinstance(part, list) else [None])]
    if (not rows or rows != passages or not all(isinstance(r, dict) and set(r) == {'id', 'text'} and isinstance(r['id'], str) for r in rows)
            or len({r['id'] for r in rows}) != len(rows) or not all(parts)):
        refuse('the %d chunk files of %s, read in order, are not the passages of %s (a list of {"id", "text"}, every '
               'passage once, no empty chunk)' % (len(files), folder / 'team_a', found[0].name))
    task_text = task.read_bytes().decode('utf-8')
    if [task_text.count(place) for place in PLACES] != [1, 1, 1]:
        refuse('%s must hold each of %s exactly once' % (task, ', '.join(PLACES)))
    frame = (NL + '=== LABELING GUIDE ===' + NL + Path(args.guide).read_bytes().decode('utf-8').strip() + NL + NL
             + '=== LABELER INSTRUCTIONS ===' + NL + Path(args.instructions).read_bytes().decode('utf-8').strip() + NL)
    python, chunks = args.python.replace(chr(92), '/'), []
    for path, part in zip(files, parts):
        base = '%s.chunk_%s' % (labels, path.stem[6:])
        work, chunk_labels = Path(base + '.work.json'), Path(base + '.json')
        command = ' '.join(['"%s"' % python if ' ' in python else python, '-B', shown(args.checker), 'take',
                            shown(path), shown(work), shown(chunk_labels)])
        text = task_text
        for place, value in zip(PLACES, (shown(path), shown(work), command)):
            text = text.replace(place, value)
        chunks.append({'number': path.stem[6:], 'file': path, 'ids': [r['id'] for r in part], 'work': work, 'labels': chunk_labels,
                       'tries': Path(base + '.json.tries.jsonl'), 'prompt': Path(base + '.prompt.txt'),
                       'text': (text + frame).encode('utf-8'), 'take_command': command})
    return {'labels': labels, 'passages_file': found[0], 'passages': passages, 'task': task, 'chunks': chunks}


def run_prompt(args):
    lay = layout(args)
    for chunk in lay['chunks']:
        if chunk['prompt'].is_file() and chunk['prompt'].read_bytes() != chunk['text']:
            refuse('%s exists and is not the prompt this tool builds now (another guide, instructions, task message, checker '
                   'path or --python). One name L, one set of files: use a new labels file name.' % chunk['prompt'])
    for chunk in lay['chunks']:
        if not chunk['prompt'].is_file():
            write(chunk['prompt'], chunk['text'])
        print(json.dumps({'chunk': chunk['number'], 'passages': len(chunk['ids']), 'prompt_file': str(chunk['prompt']),
                          'prompt_sha256': sha(chunk['text']), 'working_file': str(chunk['work']),
                          'chunk_labels_file': str(chunk['labels']), 'take_command': chunk['take_command']}))
    return 0


def run_receipt(args):
    lay = layout(args)
    labels, log = lay['labels'], Path(str(lay['labels']) + '.tries.jsonl')
    sessions = dict(item.split('=', 1) for item in args.session if '=' in item)
    numbers = [chunk['number'] for chunk in lay['chunks']]
    if len(sessions) != len(args.session) or set(sessions) - set(numbers):
        refuse('--session takes NN=ID, with NN one of the chunk numbers %s' % ', '.join(numbers))
    joined = b''
    for chunk in lay['chunks']:
        if not chunk['prompt'].is_file() or chunk['prompt'].read_bytes() != chunk['text']:
            refuse('the prompt file of chunk %s (%s) is missing, or is not the prompt this tool builds from the task message, the '
                   'guide and the instructions on disk, with this checker path and --python' % (chunk['number'], chunk['prompt'].name))
        part = chunk['tries'].read_bytes() if chunk['tries'].is_file() else b''
        try:
            events = [json.loads(line) for line in part.decode('utf-8').splitlines()]
        except ValueError:
            events = None
        if events is None or (part and not part.endswith(b'\n')) or not all(isinstance(e, dict) and e.get('passage_id') in chunk['ids'] for e in events):
            refuse('%s is not a whole try log of chunk %s: a line is cut off, or is for a passage of another chunk' % (chunk['tries'].name, chunk['number']))
        joined += part
    if log.is_file() and set(log.read_bytes().splitlines()) - set(joined.splitlines()):
        refuse('%s holds a try that is in no chunk try log. Records are handed in chunk by chunk, never to the team file.' % log.name)
    write(log, joined)
    with tempfile.TemporaryDirectory() as scratch:      # the take step with nothing new handed in: an empty list of records
        nothing = Path(scratch) / 'nothing_handed_in.json'
        nothing.write_bytes(b'[]')
        command = [sys.executable, '-B', str(Path(args.checker).resolve()), 'take', str(lay['passages_file']), str(nothing), str(labels)]
        done = subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=600)
    if done.returncode not in (0, 1) or not labels.is_file() or log.read_bytes() != joined:
        refuse('the checker\'s take run did not end as expected (exit code %d). Last output: %s' % (done.returncode, (done.stdout + done.stderr).strip()[-300:]))
    rows = read_json(labels, 'team A\'s labels file')
    final = {row['passage_id']: row for row in rows}
    not_final = [p['id'] for p in lay['passages'] if p['id'] not in final]
    listed, differ = [], []
    for chunk in lay['chunks']:
        own = read_json(chunk['labels'], 'a chunk labels file') if chunk['labels'].is_file() else None
        if own is not None and own != [final[pid] for pid in chunk['ids'] if pid in final]:
            differ.append(chunk['number'])
        listed.append({'chunk': chunk['number'], 'chunk_file': chunk['file'].name, 'chunk_sha256': sha(chunk['file']),
                       'passages': len(chunk['ids']), 'passages_final': sum(1 for pid in chunk['ids'] if pid in final),
                       'prompt_file': chunk['prompt'].name, 'prompt_sha256': sha(chunk['text']),
                       'labels_file': chunk['labels'].name, 'labels_sha256': sha(chunk['labels']) if own is not None else None,
                       'tries_file': chunk['tries'].name, 'tries_sha256': sha(chunk['tries']) if chunk['tries'].is_file() else None,
                       'session_id': sessions.get(chunk['number'])})
    complete = done.returncode == 0 and not not_final and not differ
    failed = sum(1 for row in rows if row.get('labeler_failed') is True)
    receipt = {'tool': TOOL, 'team': 'A', 'written_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'guide_sha256': sha(args.guide), 'instructions_sha256': sha(args.instructions), 'checker_sha256': sha(args.checker),
               'passages_sha256': sha(lay['passages_file']), 'task_message_sha256': sha(lay['task']), 'tool_sha256': sha(__file__),
               'labels_file': labels.name, 'labels_sha256': sha(labels), 'tries_file': log.name, 'tries_sha256': sha(joined),
               'complete': complete, 'take_command': ' '.join(command[1:4] + ['<passage file>', '<an empty list of records>', '<L>']),
               'take_exit_code': done.returncode, 'take_last_line': (done.stdout.strip().splitlines() or [''])[-1],
               'passages': len(lay['passages']), 'passages_by_state': {'LABELED': len(rows) - failed, 'NOT_LABELED': failed, 'NOT_FINAL': len(not_final)},
               'passages_not_final': not_final, 'chunks_whose_own_labels_file_differs': differ, 'chunks': listed,
               'guide': str(args.guide), 'instructions': str(args.instructions), 'passages_file': str(lay['passages_file']),
               'sessions_are_as_the_workflow_script_named_them': True, 'not_checked_by_this_tool': NOT_SEEN}
    write(Path(str(labels) + '.receipt.json'), (json.dumps(receipt, indent=1, ensure_ascii=False) + NL).encode('utf-8'))
    print(json.dumps({key: receipt[key] for key in ('labels_file', 'labels_sha256', 'complete', 'take_exit_code', 'take_last_line',
                                                    'passages', 'passages_by_state', 'chunks_whose_own_labels_file_differs')}))
    return 0 if complete else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description='Team A prompts, labels file and receipt, label agreement version 2.1.')
    parser.add_argument('mode', choices=['prompt', 'receipt'])
    parser.add_argument('set_folder', help='the folder seal_v21.py wrote')
    parser.add_argument('labels', help='L: the name of team A\'s labels file')
    parser.add_argument('--guide', default=str(ROOT / '02_LABELING_GUIDE_v2_1.md'))
    parser.add_argument('--instructions', default=str(ROOT / 'label_v21' / 'LABELER_INSTRUCTIONS.txt'))
    parser.add_argument('--checker', default=str(HERE / 'check_labels_v21.py'))
    parser.add_argument('--python', default=sys.executable, help='the interpreter named in the take command of the prompts')
    parser.add_argument('--session', nargs='*', default=[], help='receipt mode: NN=ID, the session id of the sub-agent of chunk NN')
    args = parser.parse_args(argv)
    return {'prompt': run_prompt, 'receipt': run_receipt}[args.mode](args)


if __name__ == '__main__':
    sys.exit(main())
