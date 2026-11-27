"""Inspection channels, collection costs and run parameters."""

POINTS = {
    "hinge_gap_mm": ("拉片铰位间隙（mm）", 3),
    "crimp_depth_mm": ("铆口压合深度（mm）", 4),
    "return_angle_deg": ("拉片回弹角（°）", 5),
    "laser_gap_mm": ("激光复测铰位间隙（mm）", 9),
    "pin_diameter_mm": ("销轴直径（mm）", 5),
    "jaw_slip_mm": ("夹具滑移（mm）", 6),
    "plating_um": ("电镀厚度（μm）", 8),
    "surface_temp_c": ("片面温度（°C）", 2),
    "tab_mass_g": ("拉片质量（g）", 3),
}
FEATURES = tuple(POINTS)
TARGET = "break_force_n"
PRIORITY_RECORD = "priority_record"
COLUMNS = ("id", "batch_id", "split", *FEATURES, TARGET, PRIORITY_RECORD)
FIELDS = {
    "id": "试片编号", "batch_id": "拉伸批次", "split": "记录用途",
    **{feature: point[0] for feature, point in POINTS.items()}, TARGET: "破坏峰值（N）",
    PRIORITY_RECORD: "优先送检记录",
}
RESAMPLE_SEED = 261125
VERIFICATION_SEED = 261126
SETTINGS = [
    {"key": "alpha", "label": "Elastic Net 惩罚强度", "default": 2.2, "min": 0.1, "max": 100, "step": 0.1},
    {"key": "l1_ratio", "label": "L1 惩罚占比", "default": 0.65, "min": 0.05, "max": 0.95, "step": 0.05},
    {"key": "resamples", "label": "训练批重采样次数", "default": 32, "min": 8, "max": 64, "step": 1},
    {"key": "min_frequency", "label": "最低入选频率", "default": 0.7, "min": 0.5, "max": 1, "step": 0.05},
    {"key": "budget_seconds", "label": "单片布点时长预算（秒）", "default": 12, "min": 1, "max": 45, "step": 1},
    {"key": "retest_force_n", "label": "破坏力复测提示线（N）", "default": 108, "min": 1, "max": 5000, "step": 1},
    {"key": "verification_draws", "label": "每批抽签验证片数", "default": 2, "min": 0, "max": 20, "step": 1},
]
SPEC = {
    "columns": list(COLUMNS),
    "fields": FIELDS,
    "settings": SETTINGS,
    "modules": {
        "datasets": "拉伸批次台账", "runs": "测点预算与筛选", "results": "入选点位与批次验算", "reviews": "实验室复核",
    },
    "limitation": "筛选与估计用于安排破坏试验复测。独立批误差反映当前批次，点位调整须由实验室复核。",
    "dataset_name": "20261125-旅行箱拉片拉伸台账.csv",
    "recommendation": "先查看独立批误差，再复核预算内点位与待检试片名单。",
}


def parse_settings(settings: dict) -> dict[str, float | int]:
    if settings.keys() - {item["key"] for item in SETTINGS}:
        raise ValueError("存在本项目未定义的运行参数。")
    parsed = {}
    for spec in SETTINGS:
        key = spec["key"]
        value = settings.get(key, spec["default"])
        if type(value) not in (int, float) or not spec["min"] <= value <= spec["max"]:
            raise ValueError(f'{spec["label"]}须为 {spec["min"]} 至 {spec["max"]} 之间的数值。')
        if spec["step"] == 1:
            if value != int(value):
                raise ValueError(f'{spec["label"]}须为整数。')
            value = int(value)
        parsed[key] = value
    return parsed
