"""Compare frozen models on independent batches and prepare the retest list."""

from collections import defaultdict
from math import fsum, sqrt

from .elastic import Fit
from .settings import TARGET


def summarize(batch: str | None, rows: list[dict]) -> dict:
    errors = {}
    for model in ("full", "selected"):
        residuals = [row[f"{model}_prediction_n"] - row["actual_n"] for row in rows]
        errors[f"{model}_mae_n"] = fsum(abs(value) for value in residuals) / len(rows)
        errors[f"{model}_rmse_n"] = sqrt(fsum(value ** 2 for value in residuals) / len(rows))
    return {"scope": "overall" if batch is None else "batch", "batch_id": batch, "rows": len(rows), **errors,
            "mae_delta_n": errors["selected_mae_n"] - errors["full_mae_n"],
            "rmse_delta_n": errors["selected_rmse_n"] - errors["full_rmse_n"]}


def validate_batches(rows: list[dict], full: Fit, selected: Fit) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    observed = []
    for row in rows:
        detail = {"id": row["id"], "batch_id": row["batch_id"], "actual_n": row[TARGET],
                  "full_prediction_n": full.predict(row), "selected_prediction_n": selected.predict(row)}
        observed.append(detail)
        groups[row["batch_id"]].append(detail)
    summary = [summarize(None, observed)]
    summary.extend(summarize(batch, batch_rows) for batch, batch_rows in sorted(groups.items()))
    return summary, observed


def retest_queue(rows: list[dict], trimmed: Fit, threshold: float) -> list[dict]:
    predictions = [(trimmed.predict(row) if trimmed.features else None, row) for row in rows]
    predictions.sort(key=lambda pair: (pair[0] if pair[0] is not None else 0, pair[1]["id"]))
    result = []
    for order, (estimate, row) in enumerate(predictions, 1):
        if estimate is None:
            action = "等待确认测点方案"
        elif estimate < threshold:
            action = "优先做破坏试验"
        else:
            action = "按常规顺序破坏试验"
        result.append({"position": order, "id": row["id"], "batch_id": row["batch_id"],
                       "estimated_force_n": estimate, "retest_force_n": threshold, "action": action})
    return result
