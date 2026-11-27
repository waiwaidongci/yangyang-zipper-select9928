"""Describe the lab's scalar result tables for JSON and approved CSV downloads."""

from .elastic import Fit
from .selection import Candidate
from .settings import FIELDS

BATCH_LABELS = {"scope": "汇总范围", "batch_id": "留出批次", "rows": "试片数",
                "full_mae_n": "全测点 MAE（N）",
                "selected_mae_n": "筛选测点 MAE（N）", "mae_delta_n": "MAE 增量（N）",
                "full_rmse_n": "全测点 RMSE（N）", "selected_rmse_n": "筛选测点 RMSE（N）",
                "rmse_delta_n": "RMSE 增量（N）"}


def table(key: str, title: str, labels: dict[str, str], rows: list[dict]) -> dict:
    formatted = [
        {name: round(value, 6) if type(value) is float else value for name, value in row.items()}
        for row in rows
    ]
    return {"key": key, "title": title, "columns": list(labels), "labels": labels, "rows": formatted}


def point_table(plan: list[Candidate], full: Fit, trimmed: Fit, budget: int, resamples: int) -> dict:
    labels = {"rank": "频率排序", "feature": "测点列名", "point": "测点",
              "hits": "入选轮数", "resamples": "重采样总轮数", "frequency": "入选频率",
              "mean_abs_coef_n": "平均标准化绝对系数（N）", "cost_seconds": "单片布点秒数",
              "status": "预算筛选状态", "budget_seconds": "总预算（秒）", "used_seconds": "累计用时（秒）",
              "full_coef_n": "全测点拟合标准化系数（N）", "selected_coef_n": "筛选后拟合标准化系数（N）"}
    full_weights = dict(zip(full.features, full.coefficients))
    trimmed_weights = dict(zip(trimmed.features, trimmed.coefficients))
    rows = []
    used = 0
    for rank, point in enumerate(plan, 1):
        if point.status == "selected":
            used += point.cost
        rows.append({"rank": rank, "feature": point.feature, "point": FIELDS[point.feature],
                     "hits": point.hits, "resamples": resamples, "frequency": point.frequency,
                     "mean_abs_coef_n": point.mean_abs_coef, "cost_seconds": point.cost, "status": point.status,
                     "budget_seconds": budget, "used_seconds": used, "full_coef_n": full_weights[point.feature],
                     "selected_coef_n": trimmed_weights.get(point.feature)})
    return table("point_selection", "拉片测点入选频率与耗时预算", labels, rows)


def validation_tables(summary: list[dict], observed: list[dict]) -> list[dict]:
    return [table("holdout_batches", "独立批次误差对照", BATCH_LABELS, summary),
            table("holdout_predictions", "独立批试片预测核对", {
                "id": FIELDS["id"], "batch_id": FIELDS["batch_id"], "actual_n": "实测破坏力（N）",
                "full_prediction_n": "全测点估计（N）", "selected_prediction_n": "筛选测点估计（N）",
            }, observed)]


def retest_table(rows: list[dict]) -> dict:
    return table("retest_queue", "待检拉片破坏试验顺序", {
        "position": "顺序", "id": FIELDS["id"], "batch_id": FIELDS["batch_id"],
        "estimated_force_n": "筛选测点估计（N）", "retest_force_n": "优先复测线（N）", "action": "试验安排",
    }, rows)


def resampling_table(rows: list[dict]) -> dict:
    return table("resample_trace", "整批重采样明细", {
        "iteration": "轮次", "batch_ids": "入样训练批次", "rows": "样本数", "active_points": "非零系数测点",
    }, rows)
