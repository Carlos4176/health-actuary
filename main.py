import json
import os
from pathlib import Path
from pprint import pprint

USE_MOCK_DATA = True


def get_data():
    if USE_MOCK_DATA:
        from data.mock_generator import generate_mock_health_data

        return generate_mock_health_data(
            years=5,
            severity=1.2,
            clamp_to_reference=False,
        )
    else:
        from ocr.extractor import ocr_extract

        image_path = r""
        return ocr_extract(image_path)


def step1_get_data():
    return get_data()


def step2_analyze(data, output_dir: str):
    from analysis.stats import run_analysis

    return run_analysis(data, output_dir=output_dir)


def step3_llm_report(data, analysis_result):
    from llm.explain import generate_reports

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL")
    model = os.getenv("DEEPSEEK_MODEL")  

    if not api_key:
        print("\n[跳过步骤四] 未检测到环境变量 DEEPSEEK_API_KEY")
        return None

    return generate_reports(
        rows=data,
        analysis_result=analysis_result,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def step4_save_reports(data, analysis_result, reports, output_dir: str):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    analysis_payload = {k: v for k, v in analysis_result.items() if k != "dataframe"}
    payload = {
        "data": data,
        "analysis": analysis_payload,
        "report_child": reports["report_child"],
        "report_elder": reports["report_elder"],
    }
    (out_dir / "report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "report_child.md").write_text(reports["report_child"], encoding="utf-8")
    (out_dir / "report_elder.md").write_text(reports["report_elder"], encoding="utf-8")
    print(
        "\nSaved:",
        out_dir / "report.json",
        out_dir / "report_child.md",
        out_dir / "report_elder.md",
    )


def step5_print_outputs(analysis_result):
    print("\n=== WARNINGS ===")
    for w in analysis_result["warnings"]:
        print("-", w)

    print("\n=== FIGURES SAVED ===")
    for k, p in analysis_result["figures"].items():
        print(k, "->", p)


def run_pipeline():
    total_steps = 5
    current_step = 0

    def _progress(message: str) -> None:
        nonlocal current_step
        current_step += 1
        bar_len = 24
        filled = int(bar_len * current_step / total_steps)
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"[{bar}] {current_step}/{total_steps} {message}")

    output_dir = os.path.join(os.path.dirname(__file__), "outputs")

    _progress("step1 get data")
    data = step1_get_data()
    print("data =")
    pprint(data, width=120, sort_dicts=False)

    _progress("step2 analyze + charts")
    result = step2_analyze(data, output_dir)

    _progress("step3 llm report")
    reports = step3_llm_report(data, result)
    if reports is None:
        return

    print("\n=== REPORT (CHILD) ===\n")
    print(reports["report_child"])

    print("\n=== REPORT (ELDER) ===\n")
    print(reports["report_elder"])

    _progress("step4 save reports")
    step4_save_reports(data, result, reports, output_dir)

    _progress("step5 print outputs")
    step5_print_outputs(result)


if __name__ == "__main__":
    run_pipeline()
