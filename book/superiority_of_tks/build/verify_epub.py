# -*- coding: utf-8 -*-
"""Spot-check the EPUB against MANUSCRIPT.md (current source of truth)."""
import re
import sys
import zipfile
import html as H
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BOOK = Path(__file__).resolve().parent.parent

z = zipfile.ZipFile(BOOK / 'Reality_Engineering.epub')
ep = ' '.join(re.sub(r'<[^>]+>', ' ', z.read(n).decode('utf-8', 'ignore'))
              for n in sorted(z.namelist()) if n.endswith(('.xhtml', '.html')))
ep = H.unescape(re.sub(r'\s+', ' ', ep))

def norm(t):
    t = t.replace('’', "'").replace('‘', "'")
    t = t.replace('“', '"').replace('”', '"')
    t = t.replace('—', '-').replace('–', '-').replace('---', '-').replace('--', '-')
    return re.sub(r'\s+', ' ', t)


ep = norm(ep)
src = (BOOK / 'MANUSCRIPT.md').read_text(encoding='utf-8')
clean = re.sub(r'[`*_#\[\]|>]', ' ', src)
sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean)
         if 70 < len(s.strip()) < 200 and '\n' not in s.strip()
         and '  ' not in s.strip() and '\\' not in s and '{' not in s]
step = max(1, len(sents) // 24)
sample = sents[::step][:24]
misses = [s for s in sample if norm(s) not in ep]
print(f'{len(sample) - len(misses)}/{len(sample)} sampled sentences found in EPUB')
for m in misses[:6]:
    print('MISS:', m[:100])
