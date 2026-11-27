"""Draw locked verification lots from non-priority pending pieces and estimate miss risk.

每批从未优先送检的拉片里等概率抽签，约定抽几片做破坏试验。抽签顺序按批次种子锁定，
重试不改换试片。晚到的送检记录若证明某片在抽签前已获优先，就归回优先组，保留实测；
抽中的片退出后沿原顺序补足，剩余不足就全验。有效样本没测齐就暂停报数，测齐才出结果。
漏检风险按有效样本里实测低于原提示线的比例估计，无样本时不报数。
"""

from collections import defaultdict
from random import Random

from .elastic import Fit
from .settings import PRIORITY_RECORD, TARGET, VERIFICATION_SEED

DRAW_SAMPLE = "验证样本"
DRAW_RESERVE = "候补"
DRAW_RETURNED = "归回优先组"

RISK_READY = "测齐出结果"
RISK_PAUSED = "暂停报数"
RISK_EMPTY = "无样本不报数"


def locked_order(ids: list[str], batch_id: str) -> list[str]:
    """Seeded shuffle of the original pool; retries never swap pieces."""
    order = sorted(ids)
    Random(f"{VERIFICATION_SEED}:{batch_id}").shuffle(order)
    return order


def risk_row(batch_id: str | None, samples: list[dict], threshold: float) -> dict:
    measured = [row for row in samples if row["actual_n"] is not None]
    below = sum(row["actual_n"] < threshold for row in measured)
    total = len(samples)
    if total == 0:
        status, risk = RISK_EMPTY, None
    elif len(measured) < total:
        status, risk = RISK_PAUSED, None
    else:
        status, risk = RISK_READY, below / total
    return {"scope": "overall" if batch_id is None else "batch", "batch_id": batch_id,
            "samples": total, "measured": len(measured), "below_line": below,
            "miss_risk": risk, "retest_force_n": threshold, "status": status}


def verification_report(rows: list[dict], trimmed: Fit, threshold: float,
                        draws: int) -> tuple[list[dict], list[dict]]:
    """Lottery per pending batch plus per-batch and overall miss-risk rows."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["batch_id"]].append(row)
    draw_rows, risk_rows, all_samples = [], [], []
    for batch_id in sorted(groups):
        pool = {}
        for row in groups[batch_id]:
            estimate = trimmed.predict(row) if trimmed.features else None
            if estimate is not None and estimate < threshold:
                continue  # 估计已优先送检，不参与抽签
            pool[row["id"]] = (row, estimate)
        taken = 0
        samples = []
        for position, piece_id in enumerate(locked_order(list(pool), batch_id), 1):
            row, estimate = pool[piece_id]
            if row[PRIORITY_RECORD]:
                status = DRAW_RETURNED  # 晚到记录证明抽签前已获优先，退出候补
            elif taken < draws:
                status = DRAW_SAMPLE
                taken += 1
            else:
                status = DRAW_RESERVE
            detail = {"batch_id": batch_id, "draw_order": position, "id": piece_id,
                      "estimated_force_n": estimate, "status": status, "actual_n": row[TARGET]}
            draw_rows.append(detail)
            if status == DRAW_SAMPLE:
                samples.append(detail)
        risk_rows.append(risk_row(batch_id, samples, threshold))
        all_samples.extend(samples)
    return draw_rows, [risk_row(None, all_samples, threshold), *risk_rows]
