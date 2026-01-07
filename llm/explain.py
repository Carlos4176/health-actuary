# llm/explain.py
from __future__ import annotations
import os
import json
from typing import Any, Dict, List, Optional, Tuple


def build_llm_payload(
    rows: List[Dict[str, Any]],
    analysis_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    把步骤三输出整理成 LLM 更容易理解的结构（减少 prompt 体积，增强可控性）
    """
    summary = analysis_result.get("summary", {})
    warnings = analysis_result.get("warnings", [])

    # 精简 summary：只保留关键字段（避免prompt过长）
    compact_summary = []
    for k, v in summary.items():
        compact_summary.append({
            "key": k,
            "name": v.get("name"),
            "unit": v.get("unit"),
            "latest": v.get("latest"),
            "trend": v.get("trend"),
            "zscore_latest": v.get("zscore_latest"),
            "out_of_range": v.get("out_of_range"),
            "out_flag": v.get("out_flag"),
            "ref_low": v.get("ref_low"),
            "ref_high": v.get("ref_high"),
            "yoy_delta": v.get("yoy_delta"),
            "monotonic_increase_last3": v.get("monotonic_increase_last3"),
        })

    # 提供最近N年原始序列（只保留 year + 若干关键指标即可，避免全量太大）
    # 你可以按产品策略挑选更重要的指标
    key_metrics = ["sbp", "dbp", "fasting_glucose", "tc", "tg", "hdl", "ldl", "alt", "ast", "creatinine", "uric_acid"]
    compact_rows = []
    for r in rows:
        item = {"year": r.get("year")}
        for m in key_metrics:
            if m in r:
                item[m] = r[m]
        compact_rows.append(item)

    return {
        "years": [r.get("year") for r in rows],
        "warnings": warnings,
        "metrics_summary": compact_summary,
        "time_series": compact_rows,
    }


def build_prompt_cn(payload: Dict[str, Any], audience: str = "child") -> str:
    """
    生成中文 Prompt（合规：不做诊断、不做处方；只做趋势解释与就医建议）
    audience:
      - "child": 给子女版
      - "elder": 给老人版
    """
    style = {
        "child": "面向28-45岁子女，理性、结构化、可执行，允许少量医学术语但要解释。",
        "elder": "面向55-75岁老人，温和鼓励、少术语、多用生活化语言，不制造恐慌。",
    }[audience]

    # 合规边界：避免“诊断/治疗”
    safety = (
        "重要：你不是医生，不能下诊断结论或开药/给处方。"
        "只能基于体检指标做：趋势解释、风险分层、生活方式建议、复查建议、以及‘建议咨询医生’。"
        "不要使用‘你得了XX病’、‘必须用XX药’等表述。"
    )

    # 让模型输出可控结构
    output_format_child = """请严格按以下结构输出（Markdown）：
# 家庭健康趋势审计报告（给子女）
## 1. 结论摘要（3-5条要点）
## 2. 需要重点关注的指标（按优先级排序）
- 指标名：当前值（参考范围）｜近5年趋势｜为什么值得关注（用人话解释）
## 3. 风险分层（绿/黄/橙/红）
说明每个等级代表什么，并把本次结果放入对应等级（可以多项）
## 4. 可能原因线索（不确定性说明）
列出“可能原因”，并明确写：这只是可能性，需要结合生活方式/病史/医生判断
## 5. 行动清单（非常具体）
- 1周内：……
- 1个月内：……
- 3个月内：……
## 6. 给家人的沟通话术（3句以内）
"""

    output_format_elder = """请严格按以下结构输出（Markdown）：
# 健康小结（给长辈）
## 1. 先说结论（安抚+鼓励，3句话以内）
## 2. 哪些指标要留意（最多5项）
每项用一句话说明：现在大概处于什么水平、要注意什么
## 3. 生活习惯小建议（不超过8条）
尽量具体、温和、可做到
## 4. 复查与就医建议
用温和语气提醒：哪些情况建议带着报告去问医生
"""

    output_format = output_format_child if audience == "child" else output_format_elder

    # 把payload压缩成json字符串喂给模型（模型更稳）
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

    prompt = f"""你是一名“家庭健康精算师”，擅长把体检指标做长期趋势审计，并用通俗中文解释。
{style}

{safe_typos_fix(safety)}

下面是用户近年的体检趋势数据（JSON）：
{payload_json}

请基于 warnings + metrics_summary + time_series 来写报告。
要求：
- 重点解释“趋势”而不是单次值。
- 对于接近参考范围边界的指标，也要轻度提示（避免空报告）。
- 输出必须符合合规边界。
{output_format}
"""
    return prompt


def safe_typos_fix(text: str) -> str:
    # 小工具：防止偶发空格/特殊字符影响提示
    return text.replace("\u00a0", " ").strip()


def call_deepseek_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.4,
    timeout: Tuple[int, int] = (10, 180),
    max_retries: int = 2,
    backoff_factor: float = 0.5,
) -> str:
    """
    DeepSeek / 其他 OpenAI-兼容接口：用 requests 调用（不依赖openai库，最稳）
    base_url 示例：
      - https://api.deepseek.com/v1
      - 或你实际的兼容地址
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个严谨、合规的健康数据解读助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # timeout = (connect_timeout, read_timeout)
    resp = session.post(url, headers=headers, json=body, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def generate_reports(
    rows: List[Dict[str, Any]],
    analysis_result: Dict[str, Any],
    api_key: str,
    base_url: str,
    model: str,
) -> Dict[str, Any]:
    """
    生成两版报告：给子女、给老人
    """
    payload = build_llm_payload(rows, analysis_result)

    prompt_child = build_prompt_cn(payload, audience="child")
    prompt_elder = build_prompt_cn(payload, audience="elder")

    report_child = call_deepseek_openai_compatible(
        api_key=api_key, base_url=base_url, model=model, prompt=prompt_child
    )
    report_elder = call_deepseek_openai_compatible(
        api_key=api_key, base_url=base_url, model=model, prompt=prompt_elder
    )

    return {
        "payload": payload,
        "report_child": report_child,
        "report_elder": report_elder,
    }
