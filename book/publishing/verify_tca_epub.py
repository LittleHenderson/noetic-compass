# -*- coding: utf-8 -*-
import html as H
import re
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent

z = zipfile.ZipFile(HERE / 'Thinking_in_Cognitive_Architecture.epub')
print('mimetype ok:', z.read('mimetype') == b'application/epub+zip',
      '| integrity:', z.testzip() is None)
opf = [n for n in z.namelist() if n.endswith('.opf')][0]
meta = z.read(opf).decode('utf-8', 'ignore')
print('title:', re.findall(r'<dc:title[^>]*>([^<]*)', meta),
      '| creator:', re.findall(r'<dc:creator[^>]*>([^<]*)', meta))

imgs = alts = 0
ep_parts = []
for n in z.namelist():
    if n.endswith(('.xhtml', '.html')):
        h = z.read(n).decode('utf-8', 'ignore')
        tags = re.findall(r'<img[^>]*>', h)
        imgs += len(tags)
        alts += sum(1 for t in tags if re.search(r'alt="[^"]+"', t))
        ep_parts.append(re.sub(r'<[^>]+>', ' ', h))
print('imgs:', imgs, 'with alt:', alts)


def norm(t):
    t = t.replace('’', "'").replace('‘', "'")
    t = t.replace('“', '"').replace('”', '"')
    t = t.replace('—', '-').replace('–', '-')
    t = t.replace('---', '-').replace('--', '-')
    return re.sub(r'\s+', ' ', t)


ep = norm(H.unescape(' '.join(ep_parts)))
src = (HERE / 'latex' / 'manuscript_preprocessed.md').read_text(encoding='utf-8')
clean = re.sub(r'[`*_#\[\]|>]', ' ', src)
sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean)
         if 70 < len(s.strip()) < 200 and '\n' not in s.strip()
         and '  ' not in s.strip() and chr(92) not in s and '{' not in s]
step = max(1, len(sents) // 24)
sample = sents[::step][:24]
misses = [s for s in sample if norm(s) not in ep]
print(f'{len(sample) - len(misses)}/{len(sample)} sampled sentences found in EPUB')
for m in misses[:5]:
    print('MISS:', m[:90])
