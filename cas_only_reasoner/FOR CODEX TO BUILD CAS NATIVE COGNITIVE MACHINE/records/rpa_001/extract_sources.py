"""Read-only source extraction for the user-provided CAS-RPA PDFs."""
from hashlib import sha256
import json
from pathlib import Path
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
OUT = HERE / "_scratch"
OUT.mkdir(exist_ok=True)
rows = []
for name in ("CAS_Recursive_Possibility_Atlas_v0_1", "CAS_RPA_Map_Overview"):
    path = Path("C:/Users/wakil/Downloads") / (name + ".pdf")
    raw = path.read_bytes()
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    (OUT / (name + ".txt")).write_text(
        "\n\n".join(f"--- PDF PAGE {i+1} ---\n{text}" for i, text in enumerate(pages)),
        encoding="utf-8")
    rows.append({"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest(),
                 "pages": len(pages)})
(HERE / "source_identity.json").write_bytes((json.dumps(rows, indent=2)+"\n").encode("utf-8"))
print(json.dumps(rows))
