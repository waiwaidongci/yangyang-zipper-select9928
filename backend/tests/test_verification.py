"""Spec checks for the verification lottery (domain.verification) and ledger changes.

Run from the repository root:

    PYTHONPATH=backend python3 backend/tests/test_verification.py
"""

from src.domain.elastic import Fit
from src.domain.project import analyze
from src.domain.records import normalize_rows
from src.domain.settings import COLUMNS, FEATURES, PRIORITY_RECORD, TARGET
from src.domain.verification import (DRAW_RESERVE, DRAW_RETURNED, DRAW_SAMPLE, RISK_EMPTY,
                                     RISK_PAUSED, RISK_READY, locked_order, verification_report)

THRESHOLD = 108.0
# estimate = 100 + 10 * hinge_gap_mm
TRIMMED = Fit(features=("hinge_gap_mm",), centers=(0.0,), scales=(1.0,),
              coefficients=(10.0,), intercept=100.0)


def piece(piece_id, batch, gap, actual=None, record=None):
    return {"id": piece_id, "batch_id": batch, "hinge_gap_mm": gap,
            TARGET: actual, PRIORITY_RECORD: record}


def test_locked_order_is_stable_and_uniform_per_batch():
    ids = ["P01", "P02", "P03", "P04", "P05"]
    first = locked_order(ids, "B1")
    assert locked_order(ids, "B1") == first, "重试不得改换抽签顺序"
    assert locked_order(list(reversed(ids)), "B1") == first, "顺序只取决于批次与试片集合"
    assert sorted(first) == ids
    assert locked_order(ids, "B2") != first or len(set(first)) != len(ids), "不同批次应独立抽签"


def test_pool_excludes_estimate_priority():
    rows = [piece("LOW", "B1", 0.5),  # 估计 105 < 108，优先送检
            piece("HIGH", "B1", 1.0)]  # 估计 110，进入抽签池
    draws, risks = verification_report(rows, TRIMMED, THRESHOLD, 2)
    assert [row["id"] for row in draws] == ["HIGH"]
    assert draws[0]["status"] == DRAW_SAMPLE
    assert risks[1]["batch_id"] == "B1" and risks[1]["samples"] == 1


def test_late_record_returns_to_priority_and_replenishes():
    rows = [piece(f"P{i:02d}", "B1", 1.0) for i in range(1, 5)]
    order = locked_order([row["id"] for row in rows], "B1")
    draws, _ = verification_report(rows, TRIMMED, THRESHOLD, 2)
    assert [row["id"] for row in draws if row["status"] == DRAW_SAMPLE] == order[:2]
    assert [row["id"] for row in draws if row["status"] == DRAW_RESERVE] == order[2:]
    # 晚到的送检记录：队首试片证明抽签前已获优先，归回优先组并保留实测
    late = [dict(row, **{PRIORITY_RECORD: "JL-2026", TARGET: 99.5}) if row["id"] == order[0]
            else dict(row) for row in rows]
    draws, risks = verification_report(late, TRIMMED, THRESHOLD, 2)
    by_id = {row["id"]: row for row in draws}
    assert by_id[order[0]]["status"] == DRAW_RETURNED
    assert by_id[order[0]]["actual_n"] == 99.5, "归回优先组须保留实测"
    assert [row["id"] for row in draws if row["status"] == DRAW_SAMPLE] == order[1:3], "退出后沿原顺序补足"
    assert [row["draw_order"] for row in draws] == [1, 2, 3, 4]
    assert risks[1]["samples"] == 2


def test_short_pool_tests_everything():
    rows = [piece(f"P{i:02d}", "B1", 1.0) for i in range(3)]
    draws, risks = verification_report(rows, TRIMMED, THRESHOLD, 20)
    assert [row["status"] for row in draws] == [DRAW_SAMPLE] * 3, "剩余不足就全验"
    assert risks[1]["samples"] == 3


def test_risk_reporting_gate_and_formula():
    rows = [piece(f"P{i:02d}", "B1", 1.0) for i in range(4)]
    order = locked_order([row["id"] for row in rows], "B1")
    # 没测齐：暂停报数
    partial = [dict(row, **{TARGET: 120.0}) if row["id"] == order[0] else dict(row) for row in rows]
    _, risks = verification_report(partial, TRIMMED, THRESHOLD, 2)
    assert risks[0]["status"] == RISK_PAUSED and risks[0]["miss_risk"] is None
    assert risks[1]["status"] == RISK_PAUSED
    # 测齐才出结果：有效样本里实测低于原提示线的比例
    measured = [dict(row, **{TARGET: 101.0 if row["id"] == order[1] else 120.0})
                if row["id"] in order[:2] else dict(row) for row in rows]
    _, risks = verification_report(measured, TRIMMED, THRESHOLD, 2)
    assert risks[0]["status"] == RISK_READY and risks[0]["miss_risk"] == 0.5
    assert risks[1]["below_line"] == 1 and risks[1]["measured"] == 2
    # 严格低于提示线才计漏检
    edge = [dict(row, **{TARGET: THRESHOLD}) if row["id"] in order[:2] else dict(row) for row in rows]
    _, risks = verification_report(edge, TRIMMED, THRESHOLD, 2)
    assert risks[0]["miss_risk"] == 0.0


def test_no_samples_reports_nothing():
    rows = [piece("LOW", "B1", 0.5)]  # 全批优先，抽签池为空
    draws, risks = verification_report(rows, TRIMMED, THRESHOLD, 2)
    assert draws == []
    assert risks[0]["status"] == RISK_EMPTY and risks[0]["miss_risk"] is None
    assert risks[1]["status"] == RISK_EMPTY and risks[1]["samples"] == 0
    # 约定抽零片同样无样本
    rows = [piece("HIGH", "B1", 1.0)]
    draws, risks = verification_report(rows, TRIMMED, THRESHOLD, 0)
    assert draws[0]["status"] == DRAW_RESERVE
    assert risks[0]["status"] == RISK_EMPTY


def ledger_row(piece_id, batch, split, target, record=None):
    row = {"id": piece_id, "batch_id": batch, "split": split,
           **{feature: 1.0 for feature in FEATURES}, TARGET: target, PRIORITY_RECORD: record}
    return row


def ledger(pending):
    rows = [ledger_row(f"T{batch}-{i}", f"B-T{batch}", "train", 100.0 + i)
            for batch in range(1, 4) for i in range(1, 4)]
    rows += [ledger_row(f"V1-{i}", "B-V1", "holdout", 101.0 + i) for i in range(1, 3)]
    return rows + pending


def test_pending_rows_may_carry_late_measurements():
    pending = [ledger_row("P1", "B-P1", "pending", ""),
               ledger_row("P2", "B-P1", "pending", "97.5", "JL-01")]
    normalized = normalize_rows(ledger(pending))
    by_id = {row["id"]: row for row in normalized}
    assert by_id["P1"][TARGET] is None
    assert by_id["P2"][TARGET] == 97.5, "待检试片允许补录实测"
    assert by_id["P2"][PRIORITY_RECORD] == "JL-01"
    assert normalize_rows(normalized) == normalized, "重复规范化须幂等"


def test_priority_record_validation():
    pending = [ledger_row("P1", "B-P1", "pending", "", "JL-2026.11_25")]
    assert normalize_rows(ledger(pending))[0][PRIORITY_RECORD] is None  # 训练行未填
    bad = ledger_row("P1", "B-P1", "pending", "", "记录 01")
    try:
        normalize_rows(ledger([bad]))
    except ValueError as error:
        assert "优先送检记录" in str(error)
    else:
        raise AssertionError("非法优先送检记录须被拒绝")


def test_analyze_end_to_end_with_verification():
    pending = [ledger_row(f"P{i:02d}", "B-P1", "pending", "") for i in range(1, 5)]
    result = analyze(ledger(pending), {"resamples": 8, "verification_draws": 2})
    keys = [table["key"] for table in result["tables"]]
    assert keys == ["point_selection", "holdout_batches", "holdout_predictions", "retest_queue",
                    "verification_draws", "verification_risk", "resample_trace"]
    risk = result["tables"][5]
    assert risk["rows"][0]["scope"] == "overall"
    assert result["metrics"]["抽签验证样本数"] == risk["rows"][0]["samples"]
    assert "漏检风险（总体）" in result["metrics"]
    again = analyze(ledger(pending), {"resamples": 8, "verification_draws": 2})
    assert again["tables"][4]["rows"] == result["tables"][4]["rows"], "重试不改换试片"


def run_all():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} 项检查全部通过")


if __name__ == "__main__":
    run_all()
