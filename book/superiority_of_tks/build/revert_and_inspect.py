# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
ALLOW = BS + 'allowbreak{}'

src = Path('body.tex').read_text(encoding='utf-8')
n = src.count('---' + ALLOW)
src = src.replace('---' + ALLOW, '---')
Path('body.tex').write_text(src, encoding='utf-8')
print('reverted dash allowbreaks:', n)

for probe in ['repeated experiences', 'unavailability.', 'philosophy---',
              'a financial problem---']:
    i = src.find(probe)
    if i == -1:
        print(f'--- {probe!r}: NOT FOUND')
        continue
    print(f'--- {probe!r}:')
    print(repr(src[max(0, i - 220):i + 80]))
