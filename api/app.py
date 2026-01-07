from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional
import json
import time
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 你的项目根目录 = api/ 的上一级
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# 静态文件挂载：/static -> outputs/
# 前端访问趋势图：/static/trend_weight_kg.png
app = FastAPI(title="Health Actuary API", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(OUTPUT_DIR)) , name="static")

# 允许前端跨域（开发阶段先放开，生产再收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改成你的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_analysis(data: list[dict[str, Any]]) -> dict[str, Any]:
    from analysis.stats import run_analysis

    # 你的 run_analysis 现在支持 output_dir 参数（你已经跑通）
    return run_analysis(data, output_dir=str(OUTPUT_DIR))


def _run_llm_reports(
    data: list[dict[str, Any]],
    analysis_result: dict[str, Any],
    audience: Literal["both", "child", "elder"] = "both",
) -> dict[str, str]:
    """
    你之前 main.py 里已经能调用 llm.explain.generate_reports 并产出两份报告
    这里直接复用。
    """
    from llm.explain import generate_reports

    reports = generate_reports(
        data=data,
        analysis=analysis_result,
        audience=audience,  # 你如果没这个参数，就删掉这一行，并在 generate_reports 内部默认 both
    )
    # 期望返回结构：{"report_child": "...", "report_elder": "..."}
    # 如果你 generate_reports 返回的是别的结构，这里按你实际改一下 key 即可。
    return reports


def _save_payload(payload: dict[str, Any], out_dir: Path) -> Path:
    path = out_dir / "report.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _as_public_urls(figures: dict[str, str]) -> dict[str, str]:
    """
    analysis.stats.run_analysis 里 figures 的 value 可能是绝对路径
    这里统一转换成 /static/xxx.png，便于前端直接访问。
    """
    urls: dict[str, str] = {}
    for k, p in figures.items():
        try:
            name = Path(p).name
        except Exception:
            name = str(p).split("\\")[-1].split("/")[-1]
        urls[k] = f"/static/{name}"
    return urls


@app.get("/health")
def health():
    return {"ok": True, "output_dir": str(OUTPUT_DIR)}


@app.post("/analyze")
async def analyze(
    mode: Literal["mock", "ocr"] = Form("mock"),
    years: int = Form(5),
    severity: float = Form(1.2),
    clamp_to_reference: bool = Form(False),
    audience: Literal["both", "child", "elder"] = Form("both"),
    file: Optional[UploadFile] = File(None),
):
    """
    mode=mock:
      - 生成模拟体检数据（years/severity/clamp_to_reference）
    mode=ocr:
      - 上传图片 file（png/jpg/pdf截图等），走 OCR -> 结构化数据
        （你步骤一 ocr_extract 目前是从 image_path 读，这里会先保存成临时文件再传进去）

    返回：
      - data: 年度体检数据
      - warnings: 预警列表
      - figures: 指标->图片URL
      - report_child/report_elder: 文字报告
      - artifacts: report.json 的路径
    """
    request_id = uuid.uuid4().hex[:10]
    started = time.time()

    # 1) 拿数据
    if mode == "mock":
        from data.mock_generator import generate_mock_health_data

        data = generate_mock_health_data(
            years=years,
            severity=severity,
            clamp_to_reference=clamp_to_reference,
        )

    elif mode == "ocr":
        if file is None:
            return {"error": "mode=ocr 时必须上传 file"}

        # 保存上传文件到临时目录（outputs/uploads）
        up_dir = OUTPUT_DIR / "uploads"
        up_dir.mkdir(exist_ok=True)
        suffix = Path(file.filename or "").suffix or ".png"
        tmp_path = up_dir / f"{request_id}{suffix}"

        content = await file.read()
        tmp_path.write_bytes(content)

        # 调用你的步骤一 OCR
        from ocr.extractor import ocr_extract

        # 你现在 ocr_extract(image_path) 返回 extracted_data（键值对）
        # 但是 run_analysis 需要 list[{"year":..., ...}]
        # 所以这里需要做一个“适配”：
        extracted = ocr_extract(str(tmp_path))

        # 简单适配：把 OCR 结果当作“当年一次体检”
        # 你后面会升级为：识别“日期/年份”，或支持多页多份报告
        # 注意：OCR 输出目前多是字符串，这里尽量转 float/int
        def to_num(x: Any) -> Any:
            try:
                if isinstance(x, str) and x.strip() == "":
                    return x
                if isinstance(x, str) and "." in x:
                    return float(x)
                if isinstance(x, str):
                    return int(float(x))
                return x
            except Exception:
                return x

        item = {"year": int(years)}
        for k, v in extracted.items():
            item[k] = to_num(v)

        data = [item]

    else:
        return {"error": f"unknown mode: {mode}"}

    # 2) 分析 + 画图
    analysis_result = _run_analysis(data)

    # 3) LLM 报告
    reports = _run_llm_reports(data, analysis_result, audience=audience)

    # 4) 汇总输出（把 figures 转 URL）
    figures_abs = analysis_result.get("figures", {})
    figures_url = _as_public_urls(figures_abs)

    payload = {
        "request_id": request_id,
        "mode": mode,
        "elapsed_sec": round(time.time() - started, 3),
        "data": data,
        "warnings": analysis_result.get("warnings", []),
        "figures": figures_url,
        "report_child": reports.get("report_child", ""),
        "report_elder": reports.get("report_elder", ""),
    }

    report_path = _save_payload(payload, OUTPUT_DIR)

    return {
        **payload,
        "artifacts": {
            "report_json": str(report_path),
        },
    }
