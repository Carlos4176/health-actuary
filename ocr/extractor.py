from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import re
import json


#步骤一
# OCR图像识别与数据结构化。
# 将用户上传的数据转换为结构化的JSON格式,并返回结构化数据。

# 初始化PaddleOCR，指定中文语言
ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
# 执行OCR识别并提取指定指标
def ocr_extract(image_path):
    image = Image.open(image_path).convert("RGB")
    image_np = np.array(image)
    result = ocr.predict(image_np)
    print(f"Raw result: {result}")
#根据图片给出的指标示例，提取指标和数值
    indicators = [
        "Haemoglobin",
        "RBC",
        "PCV",
        "MCV",
        "MCH",
        "MCHC",
        "RDW",
        "Neutrophils",
        "Lymphocytes",
        "Monocytes",
        "Eosinophils",
        "Basophils",
        "N:LRatio",
        "WhiteCellCount",
    ]

    extracted_data = {}
# 检查OCR结果是否为空
    if not result:
        print("No OCR result returned.")
        return {}
    if not result[0]:
        print(f"No text blocks found. Raw result: {result}")
        return {}
# 提取OCR识别的文本块
    texts = result[0].get("rec_texts", [])
    scores = result[0].get("rec_scores", [])
    recognized_lines = list(zip(texts, scores))
# 遍历识别的文本块，尝试匹配指标和数值
    for idx, (text, conf) in enumerate(recognized_lines):
        print(f"recognized: {text}, score: {conf}")

        for indicator in indicators:
            if indicator in text:
                value = None
                max_idx = min(idx + 4, len(recognized_lines) - 1)  
                for j in range(idx, max_idx + 1):
                    next_text = recognized_lines[j][0]
                    match = re.search(r"([-+]?\d*\.\d+|\d+)", next_text)
                    if match:
                        value = match.group(0)
                        break
                if value is not None:
                    extracted_data[indicator] = value
                break

    print(f"Total recognized lines: {len(recognized_lines)}")
    return extracted_data

# 测试函数
image_path = "D:/虚拟环境code/8e82006ac461468c9eca50b0f0c6bce0.png"
data = ocr_extract(image_path)
print(json.dumps(data, indent=4, ensure_ascii=False))