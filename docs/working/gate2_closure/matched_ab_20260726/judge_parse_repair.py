"""Apparatus-level JSON parse repair for the matched A/B judge.

WHY THIS EXISTS, and why it is not a scientific change:

The judge runs at temperature `0.0`. A malformed response is therefore
reproduced byte-identically on every retry, so the driver's retry loop cannot
recover — it burns all attempts on the same broken text and hard-stops. That is
exactly what happened on the first real run (`judge pass K_A failed at offset 0:
JSONDecodeError`). The failure is in TRANSPORT (the model wrapped/truncated its
JSON), not in judgement.

WHAT THIS REPAIRS — syntax only, never content:
  * markdown fences around the object,
  * prose before/after the object,
  * trailing commas,
  * truncation mid-object (balance the open brackets, dropping any partial
    trailing row so no row is ever half-invented).

WHAT IT NEVER DOES: change a row's `id`, change a chosen label, add a row, or
guess an answer. Every repaired payload still goes through the unmodified June
`validate_preds`, which checks that the rows returned are exactly the rows asked
about and that each choice is in the allowed set. A repair that produced a wrong
row count or an invalid label fails validation exactly as before.

Both judge passes use this identically, so it cannot favour an arm.
Every repair is logged to `judge_repairs.jsonl` for the record.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR_LOG = HERE / "judge_repairs.jsonl"


def _strip_wrapping(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _drop_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _scan_brackets(text: str) -> tuple[list[str], bool]:
    """Return (unclosed openers, whether we ended inside a string)."""
    opens: list[str] = []
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            opens.append(ch)
        elif ch in "}]":
            if opens:
                opens.pop()
    return opens, in_str


def _close_truncated(text: str) -> str:
    """Balance brackets on a truncated object, discarding any partial trailing row.

    ORDER MATTERS: truncate back to the last COMPLETE element first, THEN
    rescan for unclosed brackets. Scanning before truncating counts openers
    that the truncation removes, producing too many closers.
    """
    _, in_str = _scan_brackets(text)
    repaired = text
    if in_str:
        # cut back before the unterminated string rather than inventing content
        cut = repaired.rfind('"')
        if cut > 0:
            repaired = repaired[:cut]
    # drop any partial trailing element back to the last COMPLETE one
    last_complete = repaired.rfind("}")
    if last_complete > 0:
        repaired = repaired[: last_complete + 1]
    repaired = _drop_trailing_commas(repaired)
    # rescan AFTER truncation so the closers match what actually remains
    opens, _ = _scan_brackets(repaired)
    for opener in reversed(opens):
        repaired += "}" if opener == "{" else "]"
    return repaired


def robust_extract_json(raw_text: str, june_extract, *, context: dict | None = None):
    """Try June's extractor first; repair only if it fails. Log every repair."""
    try:
        return june_extract(raw_text)
    except Exception as exc:
        first_error = f"{type(exc).__name__}: {exc}"

    text = _strip_wrapping(raw_text)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object found in judge response")
    text = text[start:]

    attempts = []
    end = text.rfind("}")
    if end > 0:
        attempts.append(("sliced", text[: end + 1]))
        attempts.append(("sliced_no_trailing_comma", _drop_trailing_commas(text[: end + 1])))
    attempts.append(("closed_truncated", _close_truncated(text)))

    for label, candidate in attempts:
        try:
            payload = json.loads(candidate)
        except Exception:
            continue
        try:
            with REPAIR_LOG.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({
                    "repair": label,
                    "context": context or {},
                    "original_len": len(raw_text),
                    "repaired_len": len(candidate),
                    "first_error": str(first_error),
                    "rows_recovered": len(payload.get("rows", [])) if isinstance(payload, dict) else None,
                }, sort_keys=True) + "\n")
        except Exception:
            pass
        return payload

    raise ValueError(f"judge JSON unrepairable: {first_error}")
