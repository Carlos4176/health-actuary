# analysis/stats.py
from __future__ import annotations

import os
import math
from typing import Any, Dict, List, Tuple

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

from data.reference_ranges import REFERENCE_RANGES


def setup_cn_font() -> None:
    candidates = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "Arial Unicode MS"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rcParams["font.sans-serif"] = [name] + [n for n in candidates if n != name]
            mpl.rcParams["axes.unicode_minus"] = False
            return
    mpl.rcParams["font.sans-serif"] = candidates
    mpl.rcParams["axes.unicode_minus"] = False


setup_cn_font()


def _zscore(series: pd.Series) -> float | None:
    """返回最后一个点相对历史的 z-score（用全序列均值/标准差）。"""
    if series.dropna().shape[0] < 3:
        return None
    mean = series.mean()
    std = series.std(ddof=0)
    if std == 0 or math.isnan(std):
        return None
    return float((series.iloc[-1] - mean) / std)


def _is_out_of_range(value: float, low: float | None, high: float | None) -> Tuple[bool, str]:
    if low is not None and value < low:
        return True, "LOW"
    if high is not None and value > high:
        return True, "HIGH"
    return False, "OK"


def _trend_direction(series: pd.Series) -> str:
    """粗略趋势：最后值与第一值比较。"""
    if series.dropna().shape[0] < 2:
        return "NA"
    delta = series.iloc[-1] - series.iloc[0]
    if abs(delta) < 1e-9:
        return "FLAT"
    return "UP" if delta > 0 else "DOWN"


def _monotonic_increase_last_n(series: pd.Series, n: int = 3) -> bool:
    s = series.dropna()
    if s.shape[0] < n:
        return False
    tail = s.iloc[-n:]
    return bool(tail.is_monotonic_increasing and tail.iloc[-1] > tail.iloc[0])


def run_analysis(
    rows: List[Dict[str, Any]],
    output_dir: str = "outputs",
) -> Dict[str, Any]:
    """
    输入：List[Dict] 每年一条数据
    输出：
      - summary: 每个指标的 zscore / 趋势 / 是否超范围
      - warnings: 文本预警列表
      - figures: 保存的图路径
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

    summary: Dict[str, Any] = {}
    warnings: List[str] = []
    figures: Dict[str, str] = {}

    # 找出有哪些可分析指标（排除 year）
    metric_keys = [c for c in df.columns if c != "year"]

    for key in metric_keys:
        rr = REFERENCE_RANGES.get(key, {"name": key, "unit": "", "low": None, "high": None})
        name = rr.get("name", key)
        unit = rr.get("unit", "")
        low = rr.get("low")
        high = rr.get("high")

        s = df[key].astype(float)

        latest_val = float(s.iloc[-1])
        z = _zscore(s)
        trend = _trend_direction(s)
        yoy = float((s.iloc[-1] - s.iloc[-2])) if len(s) >= 2 else None
        out, out_flag = _is_out_of_range(latest_val, low, high)
        monot3 = _monotonic_increase_last_n(s, n=3)

        summary[key] = {
            "name": name,
            "unit": unit,
            "latest": latest_val,
            "zscore_latest": None if z is None else round(z, 2),
            "trend": trend,
            "yoy_delta": None if yoy is None else round(yoy, 2),
            "out_of_range": out,
            "out_flag": out_flag,
            "ref_low": low,
            "ref_high": high,
            "monotonic_increase_last3": monot3,
        }

        # 预警规则（MVP：简单直接）
        if out:
            if out_flag == "HIGH":
                warnings.append(f"{name}（最新 {latest_val}{unit}）高于参考范围上限{'' if high is None else str(high)+unit}。")
            elif out_flag == "LOW":
                warnings.append(f"{name}（最新 {latest_val}{unit}）低于参考范围下限{'' if low is None else str(low)+unit}。")

        if z is not None and abs(z) >= 2:
            warnings.append(f"{name} 的最新值相对近{len(s)}年明显偏离（Z={z:.2f}），建议关注变化原因。")

        if monot3 and trend == "UP":
            warnings.append(f"{name} 最近3年呈持续上升趋势，建议结合生活方式与复查频率评估。")

        # 画趋势图（每个指标一张）
        fig_path = os.path.join(output_dir, f"trend_{key}.png")
        plt.figure(figsize=(7, 4))
        plt.plot(df["year"], s, marker="o")
        plt.title(f"{name} 趋势 ({len(df)}年)")
        plt.xlabel("年份")
        plt.ylabel(f"{name} ({unit})" if unit else name)

        if low is not None:
            plt.axhline(y=low, linestyle="--")
        if high is not None:
            plt.axhline(y=high, linestyle="--")

        plt.tight_layout()
        plt.savefig(fig_path, dpi=160)
        plt.close()

        figures[key] = fig_path

    return {
        "dataframe": df,       # 方便你调试/扩展
        "summary": summary,
        "warnings": warnings,
        "figures": figures,
    }
