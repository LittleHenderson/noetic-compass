from __future__ import annotations

import json

from cas_forex.jsonl_tail import read_jsonl_tail


def test_read_jsonl_tail_reads_newest_valid_records_across_blocks(tmp_path):
    path = tmp_path / "large-audit.jsonl"
    rows = [
        json.dumps({"id": index, "payload": "x" * 3000})
        for index in range(6)
    ]
    path.write_text("\n".join([*rows, "{malformed", ""]), encoding="utf-8")

    result = read_jsonl_tail(path, limit=3, chunk_size=4096)

    assert [row["id"] for row in result] == [3, 4, 5]


def test_read_jsonl_tail_returns_empty_for_missing_file(tmp_path):
    assert read_jsonl_tail(tmp_path / "missing.jsonl", limit=10) == []
