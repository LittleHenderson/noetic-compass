"""Completeness check: did every part, circuit and family survive the render?"""
import re

import pymupdf

SRC = (r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_Component_Companion"
       r"\CAS_Component_Mathematics.html")
PDF = (r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_Component_Companion"
       r"\CAS_Component_Mathematics.pdf")

html = open(SRC, encoding="utf-8").read()
doc = pymupdf.open(PDF)
text = re.sub(r"\s+", " ", "\n".join(p.get_text() for p in doc))

# part names as they appear in the source's .part blocks
names = re.findall(r'class="part"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,60})', html)
names = [re.sub(r"&[a-z]+;", " ", n).strip() for n in names]
names = [n for n in names if n]
print(f"source .part blocks: {len(names)}")

flat = re.sub(r"\s+", " ", text)
missing = [n for n in names if n.split(" / ")[0][:24] not in flat]
print(f"parts whose name is missing from the PDF: {len(missing)}")
for n in missing[:10]:
    print("   MISSING:", n)

for label, pat in (("circuits", r"class=\"circuit"), ("families", r"class=\"fam"),
                   ("rule rows", r"class=\"row2"), ("verbs", r"class=\"verbs"),
                   ("examples", r"class=\"ex")):
    print(f"source {label:9}: {len(re.findall(pat, html))}")

print(f"PDF pages: {doc.page_count}")
print(f"PDF text chars: {len(flat)}")
for token in ("^8^C_{F2}|A", "XNOR", "ISO", "ENG", "PED", "greyscale"):
    print(f"  contains {token!r}: {token in flat}")
