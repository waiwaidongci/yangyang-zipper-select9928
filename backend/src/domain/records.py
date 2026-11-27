"""Validate the CSV schema and enforce whole-batch split isolation."""

import math
import re
from collections import Counter

from .settings import COLUMNS, FEATURES, FIELDS, PRIORITY_RECORD, TARGET

CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
SPLITS = {"train", "holdout", "pending"}
LIMITS = dict(zip(FEATURES, (20, 20, 180, 20, 20, 20, 1000, 120, 500)))


def parse_code(value, field: str, line: int) -> str:
    if isinstance(value, str) and CODE.fullmatch(value.strip()):
        return value.strip()
    raise ValueError(f"第 {line} 条的{FIELDS[field]}须为 1 至 64 位编号，以英文字母或数字开头。")


def parse_measurement(value, field: str, line: int) -> float:
    label = FIELDS[field]
    try:
        if type(value) not in (int, float, str):
            raise ValueError
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f"第 {line} 条的{label}须为数值。") from None
    bounds = (-30, LIMITS[field]) if field == "surface_temp_c" else (0, LIMITS.get(field, 5000))
    if not math.isfinite(result) or not bounds[0] <= result <= bounds[1] or (field == TARGET and result == 0):
        lower = "大于 0" if field == TARGET else f"不低于 {bounds[0]}"
        raise ValueError(f"第 {line} 条的{label}须为有限数值，{lower}且不超过 {bounds[1]}。")
    return 0.0 if result == 0 else result


def parse_record(value, line: int) -> str | None:
    """Optional reference of a late-arriving priority submission record."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, str) and CODE.fullmatch(value.strip()):
        return value.strip()
    raise ValueError(f"第 {line} 条的{FIELDS[PRIORITY_RECORD]}须留空，或为 1 至 64 位编号，以英文字母或数字开头。")


def normalize_rows(rows: list[dict]) -> list[dict]:
    ids = set()
    batch_splits = {}
    counts = Counter()
    normalized = []
    expected_columns = set(COLUMNS)
    for line, raw in enumerate(rows, 1):
        if not isinstance(raw, dict) or raw.keys() != expected_columns:
            raise ValueError(f"第 {line} 条的列须与模板一致。")
        row_id, batch = (parse_code(raw[key], key, line) for key in ("id", "batch_id"))
        if row_id in ids:
            raise ValueError(f"第 {line} 条的试片编号 {row_id} 重复。")
        split = raw["split"].strip() if isinstance(raw["split"], str) else ""
        if split not in SPLITS:
            raise ValueError(f"第 {line} 条的记录用途须为 train、holdout 或 pending。")
        if batch_splits.setdefault(batch, split) != split:
            raise ValueError(f"拉伸批次 {batch} 同时出现在不同记录用途，请整批划分。")
        target = raw[TARGET]
        if split == "pending":
            if target is None or (isinstance(target, str) and not target.strip()):
                target = None
            else:
                target = parse_measurement(target, TARGET, line)
        else:
            target = parse_measurement(target, TARGET, line)
        ids.add(row_id)
        counts[split] += 1
        readings = {field: parse_measurement(raw[field], field, line) for field in FEATURES}
        normalized.append({"id": row_id, "batch_id": batch, "split": split, **readings, TARGET: target,
                           PRIORITY_RECORD: parse_record(raw[PRIORITY_RECORD], line)})
    if counts["train"] < 9 or sum(split == "train" for split in batch_splits.values()) < 3:
        raise ValueError("训练至少需要 9 条实测拉伸记录，且覆盖 3 个独立批次。")
    if counts["holdout"] < 2:
        raise ValueError("独立批验证至少需要 2 条留出实测记录。")
    return normalized
