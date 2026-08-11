"""Backup + extract + recover text from a .docx, non-destructively.

Reads:    Noetic_Compass_Operations_Manual_v2_CAS.docx
Writes:   Noetic_Compass_Operations_Manual_v2_CAS.docx.bak  (only if not already)
          extracted_Noetic_Compass_Operations_Manual_v2_CAS/  (mirror of zip)
          Noetic_Compass_Operations_Manual_v2_CAS_recovered.md  (plain text)

The original .docx is not modified.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
DOCX = ROOT / "Noetic_Compass_Operations_Manual_v2_CAS.docx"
BACKUP = ROOT / "Noetic_Compass_Operations_Manual_v2_CAS.docx.bak"
EXTRACT_DIR = ROOT / "extracted_Noetic_Compass_Operations_Manual_v2_CAS"
OUT_MD = ROOT / "Noetic_Compass_Operations_Manual_v2_CAS_recovered.md"

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

REQUIRED_PARTS = (
    "[Content_Types].xml",
    "word/document.xml",
    "word/styles.xml",
    "word/_rels/document.xml.rels",
)


def main() -> None:
    if not DOCX.exists():
        raise FileNotFoundError(f"missing: {DOCX}")

    # 1. Backup first — only create if not already present, so re-runs don't
    #    overwrite a known-good backup with a possibly-mutated current file.
    if BACKUP.exists():
        print(f"backup already present (not overwriting): {BACKUP.name}")
    else:
        shutil.copy2(DOCX, BACKUP)
        print(f"backup written: {BACKUP.name}")

    # 2. Verify ZIP integrity.
    try:
        with ZipFile(DOCX, "r") as z:
            bad = z.testzip()
            if bad is not None:
                print(f"ZIP integrity FAILED at: {bad}")
            else:
                print("ZIP integrity: OK")
            names = set(z.namelist())

            # 3. Extract to side folder (does not touch the .docx).
            EXTRACT_DIR.mkdir(exist_ok=True)
            z.extractall(EXTRACT_DIR)
            print(f"extracted to: {EXTRACT_DIR.name}/")

            # 4. Required-parts check.
            print()
            print("required parts:")
            for part in REQUIRED_PARTS:
                tag = "FOUND" if part in names else "MISSING"
                print(f"  {tag}  {part}")
    except BadZipFile as e:
        print(f"NOT A VALID ZIP — real corruption: {e}")
        raise

    # 5. Recover plain text from word/document.xml.
    document_xml = EXTRACT_DIR / "word" / "document.xml"
    if not document_xml.exists():
        raise FileNotFoundError(
            "word/document.xml is missing — cannot recover body text"
        )

    # ET.parse on the path side-steps the XML-declaration-vs-str-encoding pitfall
    # of ET.fromstring(read_text(...)).
    tree = ET.parse(document_xml)
    root = tree.getroot()

    paragraphs: list[str] = []
    n_breaks = 0
    n_tabs = 0
    for para in root.iter(f"{W_NS}p"):
        chunks: list[str] = []
        # Walk the paragraph in document order so runs and breaks interleave
        # the way they appear visually.
        for node in para.iter():
            tag = node.tag
            if tag == f"{W_NS}t" and node.text:
                chunks.append(node.text)
            elif tag == f"{W_NS}tab":
                chunks.append("\t")
                n_tabs += 1
            elif tag == f"{W_NS}br":
                chunks.append("\n")
                n_breaks += 1
        line = "".join(chunks).rstrip()
        if line.strip():
            paragraphs.append(line)

    recovered = "\n\n".join(paragraphs)

    # 6. Write recovered text. UTF-8, no BOM.
    OUT_MD.write_text(recovered, encoding="utf-8")
    print()
    print(f"recovered text written: {OUT_MD.name}")
    print(f"  paragraphs: {len(paragraphs)}")
    print(f"  characters: {len(recovered)}")
    print(f"  inline breaks <w:br>: {n_breaks}")
    print(f"  inline tabs  <w:tab>: {n_tabs}")


if __name__ == "__main__":
    main()
