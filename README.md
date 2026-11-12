# 华文小助手 · AI 辅助教学作品集

《人工智能在学习环境中的应用与实践》（407P1122）16 周课程的产出仓库。每周一个目录，代码可直接运行；运行记录、验收单、反思一并留档，作为学习过程证据。

当前版本：**W8 阶段项目一 · 学科智能问答助手 v1.0** —— 标签 [`v1.0`](https://github.com/huanlingphantom/ai-portfolio/releases/tag/v1.0) ｜ [Release 说明](https://github.com/huanlingphantom/ai-portfolio/releases/tag/v1.0)

## 目录

| 目录 / 文件 | 周次 | 内容 |
|---|---|---|
| `week1/` | W1 | 环境自检、AI 任务单 |
| `week2/prompt-library/` | W2 | 教学提示词库（出题、作文批改、教案扩展、生词筛查、语法讲练、课堂活动） |
| `week3/` | W3 | 读生词表 CSV 生成造句/填空练习；扫描版 PDF 取词（OCR） |
| `week4/` | W4 | 命令行学科问答机器人（API 版）、参数体验记录、密钥安全自查表 |
| `week5/` | W5 | Ollama 本地部署：本地 vs 云端对比、思考题与作业 |
| `week6/` | W6 | `llm.py` 双引擎封装（`prefer` 切换、双向回退）+ 边界测试记录 |
| `week7/` | W7 | RAG 知识库问答：加载→分块→向量化→检索→生成；幻觉对照表、离场验收单 |
| **`week8/`** | **W8** | **阶段项目一 v1.0：`assistant_v1.py`（粘合层 + `use_rag` 开关）、四段式 README、三问十二次实测、5 行映射表、互评表** |
| `data/` | — | 学科语料：等级标准节选（词汇/汉字/语法量化指标）、生词表、课文《愚公移山》 |
| `weekpath.py` | — | 跨周模块导入 / 数据路径 / `.env` 加载的统一入口 |
| `.env.example` | — | 密钥与本地模型的占位模板（复制成 `.env` 使用，`.env` 不入库） |

## 怎么跑

先从仓库根目录装依赖，再进对应周目录运行；跨周 import 依赖根目录的 `weekpath.py`，**不要在根目录直接跑周脚本**。

```bash
# 0) 依赖（按需，W1–W3 无第三方依赖）
pip install -r week8/requirements.txt

# W8：学科智能问答助手 v1.0（需先装 Ollama 并 pull 模型，详见 week8/README.md）
cd week8
python assistant_v1.py                  # 三问三答演示（默认本地引擎 + RAG）

# W7：RAG 单问单答（先 ollama pull nomic-embed-text）
cd week7
python rag_qa.py "HSK4 词汇量要求是多少" --show

# W6：双引擎对照
cd week6
python llm.py "给《愚公移山》出一道 HSK4 阅读题" --prefer local

# W3：生成练习（无需第三方库）
python week3/vocab_tool.py
```

## 依赖

- W1–W3：无第三方依赖
- W4：`openai`、`python-dotenv`
- W5–W6：Ollama（Windows 安装包）+ `openai`、`requests`、`python-dotenv`
- W7–W8：`langchain-community`、`langchain-chroma`、`langchain-ollama`、`langchain-text-splitters`、`chromadb`，以及 `ollama pull nomic-embed-text`（274 MB）
- 完整清单见各周 `requirements.txt`（W8 的在 `week8/requirements.txt`）

## 约定

- **`.env` 不入库**：仓库只有 `.env.example`；`.gitignore` 已排除 `.env`、`.env.*`、`chroma_db/`、`__pycache__/`。
- **向量库不提交**：`chroma_db/` 是二进制中间产物，首次运行自动重建。
- **产物路径统一**：数据走 `weekpath.data_path()`，产物走 `weekpath.root_path()`，从任意目录运行都不丢文件。
- **密钥只用环境变量**：代码里一律 `os.getenv()`，不写死。

## 已知问题

按周记录，不藏：

- **W8**：`qwen2.5:0.5b` 读不懂四列数字表，「HSK4 词汇量」常回「资料中未提及」；小模型也不稳定写「出处：[n]」。要演示稳定请用 `qwen2.5:1.5b` 或 `prefer="api"`。完整六条见 [`week8/README.md`](week8/README.md#已知问题)。
- **W7**：检索引擎按余弦距离取 top-k，语料只覆盖等级标准节选，语法教学法类问题会拒答（这是边界，不是 bug）。
- **W5–W6**：本地模型响应慢于云端（1.5b 单问 10–25 秒），CPU 机器上更明显。
