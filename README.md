Health Actuary MVP（家庭健康精算师）

📊 一个将体检数据转化为「可理解、可行动健康建议」的 AI 健康趋势分析工具

面向 子女 \& 长辈 的双版本健康报告生成系统

✨ 项目简介
Health Actuary（家庭健康精算师） 是一个基于 Python + FastAPI + 前端 Web 的健康分析 MVP。
它可以：
📷 接收体检报告图片（OCR）
🧮 提取 \& 结构化健康指标
📈 分析多年趋势与风险信号
🤖 调用大模型生成「可读健康报告」
👨‍👩‍👧 同时输出：
给子女的 理性分析版报告
给长辈的 安抚 + 行动建议版报告
当前版本为 MVP（最小可行产品），已跑通完整流程。

🧠 核心能力
多年度趋势分析
血压 / 血糖 / 血脂 / 尿酸 / 肝肾功能等
规则 + AI 混合决策
数值区间判断（参考范围）
连续上升 / 下降趋势识别
大模型自然语言总结
双受众报告生成

子女版：风险、逻辑、未来概率
长辈版：通俗、安抚、可执行建议

🧱 项目结构
HA health actuary/

├── analysis/        # 指标计算、趋势分析、风险规则

├── api/             # FastAPI 后端接口

├── data/            # Mock 数据 \& 指标参考区间

├── llm/             # 大模型调用与报告生成

├── ocr/             # OCR 图片解析模块

├── outputs/         # 运行产物（已在 .gitignore 中忽略）

├── main.py          # 本地一键运行入口

├── .gitignore

└── README.md


🚀 快速开始（本地运行）

1️⃣ 环境要求
Python 大于 3.10
Node.js 大于18
Git
2️⃣ 克隆项目
git clone https://github.com/Carlos4176/health-actuary.git
cd health-actuary
3️⃣ 创建虚拟环境、安装依赖
python -m venv venv
venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
4️⃣ API Key
DEEPSEEK\_API\_KEY=your\_API\_KEY
⚠️ .env 已被 .gitignore 忽略，不会上传
5️⃣ 后端FastAPI
uvicorn api.app:app --reload
http://localhost:8000/docs
6️⃣ 前端
cd HA health actuary-frontend
npm install
npm run dev
http://localhost:5173

🧪 当前支持的模式
✅ Mock 数据（用于调试 / 演示）
🚧 OCR 图片上传（已接入，待优化识别率）
🚧 多报告图片合并解析（规划中）
📌 当前状态
✔️ 完整流程已跑通
✔️ 前后端联调成功
✔️ 大模型报告生成成功
⏳ 正在向「产品化 / 商业化」演进
🛣️ Roadmap（下一步计划）
&nbsp;OCR 精度提升（多模板）
&nbsp;用户账号系统
&nbsp;历史数据长期存储
&nbsp;PDF 报告导出
&nbsp;支付 / 订阅系统
&nbsp;合规与隐私设计

⚠️ 免责声明
本项目仅用于 健康信息整理与趋势分析，
不能替代医生诊断或医疗建议。
如有异常指标，请务必咨询专业医生。

👤 作者
Carlos Guo
GitHub: @Carlos4176


🌱 致谢
感谢大模型与开源社区提供的基础能力支持。

