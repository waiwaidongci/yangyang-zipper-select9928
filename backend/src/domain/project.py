"""Entry points for dataset import, seeding and background execution."""

from collections import defaultdict

from .elastic import fit
from .evaluation import retest_queue, validate_batches
from .fixtures import demo_rows
from .records import normalize_rows
from .reports import point_table, resampling_table, retest_table, validation_tables
from .selection import point_plan
from .settings import FEATURES, SPEC, parse_settings

__all__ = ["SPEC", "demo_rows", "normalize_rows", "analyze"]


def analyze(rows: list[dict], settings: dict) -> dict:
    options = parse_settings(settings)
    cohorts = defaultdict(list)
    for row in sorted(normalize_rows(rows), key=lambda row: (row["batch_id"], row["id"])):
        cohorts[row["split"]].append(row)
    train = cohorts["train"]
    plan, trace = point_plan(train, options)
    chosen = tuple(point.feature for point in plan if point.status == "selected")
    used = sum(point.cost for point in plan if point.status == "selected")
    full = fit(train, FEATURES, options["alpha"], options["l1_ratio"])
    trimmed = fit(train, chosen, options["alpha"], options["l1_ratio"])
    comparison, observed = validate_batches(cohorts["holdout"], full, trimmed)
    queue = retest_queue(cohorts["pending"], trimmed, options["retest_force_n"])
    overall = comparison[0]
    warnings = []
    if not chosen:
        warnings.append("当前频率和布点预算下没有入选测点。独立批对照使用训练均值，待检件暂停排序建议。")
    if overall["mae_delta_n"] > 0.5:
        warnings.append("筛选模型的独立批汇总 MAE 比全测点高逾 0.5 N，请复核省时与误差的取舍。")
    if len(comparison) == 2:
        warnings.append("独立验证目前仅覆盖一个批次，建议结合其他生产批次复核。")
    if not queue:
        warnings.append("本次台账未含待检试片，待检清单为空。")
    return {
        "summary": (f"用 {len(train)} 片历史试片完成 {options['resamples']} 轮整批重采样。"
                    f"{len(chosen)} 个测点入选，每片布点 {used}/{options['budget_seconds']} 秒。"
                    f"冻结训练模型后，对照 {len(comparison) - 1} 个独立批共 {overall['rows']} 片的误差。"),
        "metrics": {"入选测点数": len(chosen), "布点时间（秒/片）": used, "预算（秒/片）": options["budget_seconds"],
                    "独立批全测点 MAE（N）": round(overall["full_mae_n"], 6),
                    "独立批筛选测点 MAE（N）": round(overall["selected_mae_n"], 6),
                    "独立批 MAE 增量（N）": round(overall["mae_delta_n"], 6),
                    "优先做破坏试验件数": sum(row["action"] == "优先做破坏试验" for row in queue)},
        "tables": [point_table(plan, full, trimmed, options["budget_seconds"], options["resamples"]),
                   *validation_tables(comparison, observed), retest_table(queue), resampling_table(trace)],
        "warnings": warnings,
    }
