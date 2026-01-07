# data/mock_generator.py
from __future__ import annotations

import numpy as np
from typing import Dict, List, Any
from datetime import datetime

from data.reference_ranges import REFERENCE_RANGES


def _clamp(x: float, low: float | None, high: float | None) -> float:
    if low is not None:
        x = max(x, low)
    if high is not None:
        x = min(x, high)
    return x


def generate_mock_health_data(
    years: int = 5,
    start_year: int | None = None,
    severity: float = 0.6,
    seed: int = 42,
    clamp_to_reference: bool = True,
) -> List[Dict[str, Any]]:
    """
    生成模拟体检数据（用于冷启动/测试/演示）
    - years: 年数
    - start_year: 起始年份（默认：当前年份-years+1）
    - severity: 趋势“变坏”的强度 0~1（越大越明显）
    - seed: 随机种子（保证可复现）
    - clamp_to_reference: 是否将数值轻度夹逼在参考范围内
    """
    rng = np.random.default_rng(seed)

    if start_year is None:
        start_year = datetime.now().year - years + 1

    year_list = list(range(start_year, start_year + years))
    t = np.linspace(0, 1, years)  # 时间进度 0..1

    # 基线（更像中老年）
    base = {
        "weight_kg": 70 + rng.normal(0, 2),
        "sbp": 125 + rng.normal(0, 4),
        "dbp": 80 + rng.normal(0, 3),
        "resting_heart_rate": 72 + rng.normal(0, 2),

        "fasting_glucose": 5.4 + rng.normal(0, 0.2),

        "tc": 4.9 + rng.normal(0, 0.2),
        "tg": 1.2 + rng.normal(0, 0.2),
        "hdl": 1.2 + rng.normal(0, 0.1),
        "ldl": 2.8 + rng.normal(0, 0.2),

        "alt": 22 + rng.normal(0, 3),
        "ast": 20 + rng.normal(0, 3),

        "creatinine": 78 + rng.normal(0, 6),
        "uric_acid": 340 + rng.normal(0, 25),
    }

    # 趋势（慢性“变坏”方向 + 随机波动）
    # severity 控制总体上升幅度
    trend = {
        "weight_kg": 2.5 * severity,
        "sbp": 10.0 * severity,
        "dbp": 6.0 * severity,
        "resting_heart_rate": 2.0 * severity,

        "fasting_glucose": 0.8 * severity,

        "tc": 0.7 * severity,
        "tg": 0.8 * severity,
        "hdl": -0.1 * severity,     # HDL 可能略降（变坏）
        "ldl": 0.7 * severity,

        "alt": 10.0 * severity,
        "ast": 7.0 * severity,

        "creatinine": 10.0 * severity,
        "uric_acid": 60.0 * severity,
    }

    # 噪声（每年上下波动）
    noise = {
        "weight_kg": 0.4,
        "sbp": 2.0,
        "dbp": 1.5,
        "resting_heart_rate": 1.2,

        "fasting_glucose": 0.15,

        "tc": 0.15,
        "tg": 0.15,
        "hdl": 0.06,
        "ldl": 0.12,

        "alt": 3.0,
        "ast": 2.5,

        "creatinine": 3.0,
        "uric_acid": 12.0,
    }

    rows: List[Dict[str, Any]] = []
    keys = list(base.keys())

    for i, y in enumerate(year_list):
        row: Dict[str, Any] = {"year": y}

        for k in keys:
            val = base[k] + trend[k] * t[i] + rng.normal(0, noise[k])

            if clamp_to_reference:
                # 根据参考范围做轻度夹逼，避免离谱
                rr = REFERENCE_RANGES.get(k, {})
                val = _clamp(val, rr.get("low"), rr.get("high"))

            # 保留小数（血压/心率取整更合理）
            if k in ("sbp", "dbp", "resting_heart_rate"):
                row[k] = int(round(val))
            else:
                row[k] = float(round(val, 2))

        rows.append(row)

    return rows


if __name__ == "__main__":
    data = generate_mock_health_data(years=5, severity=0.7)
    for r in data:
        print(r)
