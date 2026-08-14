# -*- coding: utf-8 -*-
import pymupdf
import sys

sys.stdout.reconfigure(encoding='utf-8')
doc = pymupdf.open('manuscript_tks.pdf')
print('pages:', doc.page_count)
REQ_G, REQ_O = 0.875 * 72, 0.25 * 72
bad = []
for i in range(doc.page_count):
    words = doc[i].get_text('words')
    if not words:
        continue
    x0 = min(w[0] for w in words)
    x1 = max(w[2] for w in words)
    y0 = min(w[1] for w in words)
    y1 = max(w[3] for w in words)
    odd = (i + 1) % 2 == 1
    g = x0 if odd else 432 - x1
    o = 432 - x1 if odd else x0
    if g < REQ_G - 0.5 or o < REQ_O - 0.5 or y0 < REQ_O - 0.5 or (648 - y1) < REQ_O - 0.5:
        if odd:
            key = max(words, key=lambda w: w[2])
        else:
            key = max(words, key=lambda w: w[2])
        bad.append((i + 1, round(g / 72, 3), round(o / 72, 3), key[4][:30]))
print('violations:', len(bad))
for v in bad[:20]:
    print(' ', v)
