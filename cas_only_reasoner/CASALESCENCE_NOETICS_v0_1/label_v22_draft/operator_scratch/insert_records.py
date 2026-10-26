"""Insert the label-agreement v2.1 result into a copy of the spec sheet and of CHANGELOG.md.

Usage: insert_records.py <spec_sheet_path> <changelog_path>
Idempotent: a file that already holds the new text is left as it is. Keeps the file's line endings and BOM.
Fails (exit 1) without writing if an anchor is missing."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTION = (HERE / 'spec_7_23.md').read_text(encoding='utf-8')
ROW = (HERE / 'spec_row.md').read_text(encoding='utf-8')
ENTRY = (HERE / 'changelog_entry.md').read_text(encoding='utf-8')

SECTION_ANCHOR = '## 8. THE TWO CLAIMS'
SECTION_NEEDS = '### 7.22 Option B usefulness test'
ROW_ANCHOR = '| 2026-10-06 | **OPTION B USEFULNESS TEST'
ENTRY_ANCHOR = '## 2026-10-06 PDT - Option B usefulness test'


def load(path):
    raw = Path(path).read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw[3:].decode('utf-8') if bom else raw.decode('utf-8')
    crlf = '\r\n' in text
    return text.replace('\r\n', '\n'), bom, crlf


def save(path, text, bom, crlf):
    if crlf:
        text = text.replace('\n', '\r\n')
    data = text.encode('utf-8')
    if bom:
        data = b'\xef\xbb\xbf' + data
    tmp = Path(str(path) + '.partial')
    tmp.write_bytes(data)
    tmp.replace(path)


def insert_before_line(text, anchor, new, label):
    lines = text.split('\n')
    hits = [i for i, line in enumerate(lines) if line.startswith(anchor)]
    if len(hits) != 1:
        sys.exit('FAILED: %s anchor found %d times: %r' % (label, len(hits), anchor))
    i = hits[0]
    block = new.rstrip('\n').split('\n')
    return '\n'.join(lines[:i] + block + lines[i:])


spec_path, log_path = sys.argv[1], sys.argv[2]

spec, bom, crlf = load(spec_path)
changed = False
if '### 7.23 Noetic role labels, attempt 2' not in spec:
    if SECTION_NEEDS not in spec:
        sys.exit('FAILED: section 7.22 is not in ' + spec_path)
    spec = insert_before_line(spec, SECTION_ANCHOR, SECTION.rstrip('\n') + '\n', 'section')
    changed = True
if '| 2026-10-07 | **NOETIC ROLE LABELS, ATTEMPT 2' not in spec:
    spec = insert_before_line(spec, ROW_ANCHOR, ROW, 'change-log row')
    changed = True
if changed:
    save(spec_path, spec, bom, crlf)
print('spec sheet:', 'updated' if changed else 'already holds the result', '| crlf' if crlf else '| lf', '| bom' if bom else '')

log, bom, crlf = load(log_path)
if '## 2026-10-07 PDT - Noetics label agreement, attempt 2' not in log:
    log = insert_before_line(log, ENTRY_ANCHOR, ENTRY, 'changelog entry')
    save(log_path, log, bom, crlf)
    print('changelog: updated', '| crlf' if crlf else '| lf')
else:
    print('changelog: already holds the result')
