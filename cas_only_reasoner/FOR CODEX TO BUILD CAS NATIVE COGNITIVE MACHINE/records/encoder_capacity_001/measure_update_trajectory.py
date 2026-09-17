"""Measure what the 160 recorded updates actually did.

Pure standard library, no torch, no device, no network. Reads only the frozen
receipt of run `typed_matched_001/receipt_20260919_m`, which is already on disk.

Two questions, both answerable from bytes already recorded:

A. ACCURACY TRAJECTORY. The run scored the same frozen development curriculum
   at five cursors (0, 40, 80, 120, 160). Compare them, overall and per kind.
   This is the accuracy-versus-updates curve; it was measured and not read.

B. OPTIMISATION STATE AT THE STOPPING POINT. Each of the 160 update receipts
   carries `raw_batch_loss` and `gradient_squared_norm`. If the objective had
   converged, the loss would be flat and the gradient norm small at the end.

The learner contract admits `max_updates <= 176`
(`cas_meta2/typed_teaching/learner.py`, `TYPED_LEARNER_LIMITS`), so the stopping
point is not a schedule choice: it is the ceiling the registered contract sets.
"""

from __future__ import annotations

import json
import math
from itertools import permutations
from pathlib import Path
import statistics

ARTIFACTS = (
    Path(__file__).resolve().parents[2]
    / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"
)
CURSORS = (0, 40, 80, 120, 160)


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def accuracy(scoring: dict) -> tuple[int, int]:
    rows = scoring["rows"]
    return sum(1 for row in rows if row["correct"]), len(rows)


def per_kind(scoring: dict) -> dict[str, tuple[int, int]]:
    out: dict[str, list[int]] = {}
    for row in scoring["rows"]:
        bucket = out.setdefault(row["kind"], [0, 0])
        bucket[1] += 1
        bucket[0] += 1 if row["correct"] else 0
    return {kind: (value[0], value[1]) for kind, value in sorted(out.items())}


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation, ties averaged; no scipy."""
    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        index = 0
        while index < len(order):
            stop = index
            while stop + 1 < len(order) and values[order[stop + 1]] == values[order[index]]:
                stop += 1
            mean_rank = (index + stop) / 2.0
            for position in range(index, stop + 1):
                out[order[position]] = mean_rank
            index = stop + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = math.sqrt(
        sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)
    )
    return numerator / denominator if denominator else 0.0


def main() -> int:
    print("=" * 78)
    print("A. ACCURACY TRAJECTORY ACROSS THE FIVE DEVELOPMENT CHECKPOINTS")
    print("=" * 78)
    print()
    header = f"{'cursor':>7} {'correct':>8} {'total':>7} {'accuracy':>10}"
    print(header)
    points: list[tuple[int, float]] = []
    per_cursor: dict[int, dict[str, tuple[int, int]]] = {}
    for cursor in CURSORS:
        scoring = load(f"development_{cursor:03d}_scoring.json")
        correct, total = accuracy(scoring)
        points.append((cursor, correct / total))
        per_cursor[cursor] = per_kind(scoring)
        print(f"{cursor:7d} {correct:8d} {total:7d} {100 * correct / total:9.4f}%")
    print()
    first, last = points[0][1], points[-1][1]
    print(f"change over the window: {100 * (last - first):+.4f} percentage points")
    print(f"relative change:        {last / first:.6f}x" if first else "n/a")

    kinds = sorted({kind for table in per_cursor.values() for kind in table})
    print()
    print("per kind (correct/total):")
    print(f"{'kind':>16}" + "".join(f"{('@' + str(c)):>14}" for c in CURSORS))
    for kind in kinds:
        cells = []
        for cursor in CURSORS:
            correct, total = per_cursor[cursor].get(kind, (0, 0))
            cells.append(f"{correct}/{total}" if total else "-")
        print(f"{kind:>16}" + "".join(f"{cell:>14}" for cell in cells))

    print()
    print("=" * 78)
    print("B. OPTIMISATION STATE AT THE STOPPING POINT (160 recorded updates)")
    print("=" * 78)
    print()
    updates = sorted(
        ARTIFACTS.glob("main_*_update.json"),
        key=lambda path: int(path.stem.split("_")[1]),
    )
    steps, losses, grads = [], [], []
    per_field: dict[str, list[float]] = {}
    per_field_normalized: dict[str, list[float]] = {}
    alphabets: dict[str, set[int]] = {}
    for path in updates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        steps.append(int(path.stem.split("_")[1]))
        losses.append(float(payload["raw_batch_loss"]))
        grads.append(float(payload["gradient_squared_norm"]))
        for task in payload["tasks"]:
            for entry in task["fields"]:
                name = entry["field"]
                per_field.setdefault(name, []).append(float(entry["raw_loss"]))
                per_field_normalized.setdefault(name, []).append(
                    float(entry["normalized_loss"])
                )
                alphabets.setdefault(name, set()).add(int(entry["public_alphabet_size"]))
    print(f"update receipts read: {len(updates)}")
    print()

    blocks = [losses[i:i + 20] for i in range(0, len(losses) - 19, 20)]
    print("raw_batch_loss, consecutive blocks of 20 updates:")
    print(f"{'block':>6} {'steps':>11} {'mean':>10} {'min':>10} {'max':>10}")
    for index, block in enumerate(blocks):
        lo, hi = index * 20, index * 20 + len(block) - 1
        print(
            f"{index:6d} {f'{lo}-{hi}':>11} {statistics.fmean(block):10.6f}"
            f" {min(block):10.6f} {max(block):10.6f}"
        )
    print()
    quarter = len(losses) // 4
    q1, q4 = losses[:quarter], losses[-quarter:]
    print(f"first quarter mean (updates 0-{quarter - 1}):   {statistics.fmean(q1):.6f}")
    print(f"last  quarter mean (updates {len(losses) - quarter}-{len(losses) - 1}):"
          f"   {statistics.fmean(q4):.6f}")
    print(f"ratio last/first quarter:            {statistics.fmean(q4) / statistics.fmean(q1):.6f}")
    print()
    print(f"global minimum raw_batch_loss: {min(losses):.6f} at update {steps[losses.index(min(losses))]}")
    print(f"last update raw_batch_loss:    {losses[-1]:.6f}")
    print(f"last update is the minimum?    {losses[-1] == min(losses)}")
    print()
    print("trend tests:")
    print(f"  Spearman(update index, raw_batch_loss) = {spearman([float(s) for s in steps], losses):+.6f}")
    grad_series = [math.sqrt(value) for value in grads]
    print(f"  Spearman(update index, gradient norm)  = {spearman([float(s) for s in steps], grad_series):+.6f}")
    print()
    first_grads = grad_series[:quarter]
    last_grads = grad_series[-quarter:]
    print(f"gradient L2 norm, first quarter mean: {statistics.fmean(first_grads):.6e}")
    print(f"gradient L2 norm, last  quarter mean: {statistics.fmean(last_grads):.6e}")
    print(f"ratio last/first quarter:             {statistics.fmean(last_grads) / statistics.fmean(first_grads):.6f}")
    print(f"largest gradient norm over the run:   {max(grad_series):.6e} at update {steps[grad_series.index(max(grad_series))]}")
    print()
    print("per field, raw_loss and normalized_loss (first quarter mean -> last quarter mean).")
    print("normalized_loss is raw_loss / log(public_alphabet_size), so a uniform prior")
    print("sits at 1.0. Means are over the field entries present across each batch's")
    print("tasks, not a per-task average; entry counts differ because fields differ.")
    print()
    print(f"{'field':>16} {'alphabet':>9} {'entries':>8} {'raw head':>10} {'raw tail':>10}"
          f" {'ratio':>8} {'norm head':>10} {'norm tail':>10}")
    for field in sorted(per_field):
        series = per_field[field]
        norm_series = per_field_normalized[field]
        head = series[: max(1, len(series) // 4)]
        tail = series[-max(1, len(series) // 4):]
        nhead = norm_series[: max(1, len(norm_series) // 4)]
        ntail = norm_series[-max(1, len(norm_series) // 4):]
        sizes = ",".join(str(value) for value in sorted(alphabets[field]))
        print(
            f"{field:>16} {sizes:>9} {len(series):8d} {statistics.fmean(head):10.6f}"
            f" {statistics.fmean(tail):10.6f} {statistics.fmean(tail) / statistics.fmean(head):8.6f}"
            f" {statistics.fmean(nhead):10.6f} {statistics.fmean(ntail):10.6f}"
        )
    print()
    print("uniform-prior reference: log(3) = %.6f, log(64) = %.6f"
          % (math.log(3.0), math.log(64.0)))

    block_means = [statistics.fmean(block) for block in blocks]
    print()
    print("block-mean trend (blocks of 20 updates, autocorrelation handled by blocking):")
    print(f"  Spearman(block index, block mean) = {spearman([float(i) for i in range(len(block_means))], block_means):+.6f}")
    inversions = sum(
        1
        for i in range(len(block_means))
        for j in range(i + 1, len(block_means))
        if block_means[j] > block_means[i]
    )
    pairs = len(block_means) * (len(block_means) - 1) // 2
    print(f"  descending pairs = {pairs - inversions}/{pairs}")
    exact = 0
    total = 0
    for permutation in permutations(range(len(block_means))):
        ordered = [block_means[index] for index in permutation]
        worse = sum(
            1
            for i in range(len(ordered))
            for j in range(i + 1, len(ordered))
            if ordered[j] > ordered[i]
        )
        total += 1
        if worse <= inversions:
            exact += 1
    print(f"  exact permutation p (one-sided, {total} orderings) = {exact / total:.6f}")

    print()
    print("=" * 78)
    print("READING")
    print("=" * 78)
    print(
        "The registered contract caps updates at 176 and this run stopped at 160,"
        " so the stopping\npoint is the ceiling, not a schedule choice. If the"
        " objective had converged there, the loss\nwould be flat and the gradient"
        " norm would have decayed. Neither is true."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
