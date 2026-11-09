# 学科智能问答助手 v1.0

一个面向 HSK3–4 教学的问答助手：把 W2 提示词库（人设）、W6 双引擎（`llm.py`，本地优先·云端兜底）、W7 知识库（`rag_qa.py`，先查资料再回答）三块积木用一个粘合层 `assistant_v1.py` 串起来。

## 功能

- 基于 RAG 的学科问答：先检索《国际中文教育中文水平等级标准》节选，再让模型带着资料回答，并按要求标出「出处：[n]」。
- 一个 `use_rag` 布尔开关切换两种模式：`True` = 基于资料，`False` = 纯对话（同一套代码，只差一个参数）。
- 引擎可切：`prefer="local"` 走本机 Ollama，`prefer="api"` 走 DeepSeek 云端；本地不可用时自动回退（W6 逻辑）。
- 三问三答的演示入口内置在 `python assistant_v1.py` 里，任一问报错只打印「运行失败：原因」，不中断其余两问。

## 怎么装

1. 装依赖（建议 Python 3.10+，先建虚拟环境）：

   ```bash
   pip install -r requirements.txt
   ```

2. 拉本地模型（两个都要，缺 `nomic-embed-text` 会在建库时失败）：

   ```bash
   ollama pull qwen2.5:0.5b
   ollama pull nomic-embed-text
   ```

   确认 Ollama 已在后台运行：`ollama list` 能列出上面两个模型即正常。

3. 配云端密钥（只用本地引擎可跳过，但 `prefer="api"` 和本地失败回退时需要）：

   ```bash
   cp .env.example .env      # Windows: copy .env.example .env
   ```

   编辑 `.env`，把 `DEEPSEEK_API_KEY=` 后面填成自己的 key。`.env` 已在 `.gitignore` 里，不要提交。

4. 知识库首次运行会自动建库（读仓库根目录的 `data/等级标准节选.txt` → 分块 → 向量化 → 存 `chroma_db/`），约十几秒；之后直接复用。语料改过要重建：`python ../week7/rag_qa.py --rebuild`。

## 怎么用

在 `week8` 目录下运行（**不要**在仓库根目录直接跑，跨周 import 靠根目录的 `weekpath.py` 定位）：

```bash
cd week8
python assistant_v1.py
```

预期输出形如：

```
Q: 把字句的教学难点有哪些
A: ...（回答正文）...
----------------------------------------
Q: HSK4 词汇量要求是多少
A: ...1000 个（累计 3245）... 出处：[2]
----------------------------------------
```

自己提问 / 换模式：

```python
from assistant_v1 import answer
print(answer("HSK4 词汇量要求是多少", use_rag=True,  prefer="local"))  # 基于资料
print(answer("HSK4 词汇量要求是多少", use_rag=False, prefer="api"))    # 纯对话
```

`answer_log.md` 里有三问 × 四组合的实测记录（含耗时与点评），可直接对照。

## 已知问题

- **未启动 Ollama 时本地模式会报错**：`ConnectionError: Failed to connect to Ollama`。先 `ollama serve`/打开 Ollama 应用，或改用 `prefer="api"`。
- **没 pull `nomic-embed-text` 时建库失败**：报 `model "nomic-embed-text" not found`。执行 `ollama pull nomic-embed-text` 后重试。
- **小模型会无视格式指令**：`qwen2.5:0.5b` 常常不写「出处：[n]」，也可能把 7 列数字表读错；要稳定出处标注请用 `prefer="api"`（实测 deepseek-chat 5/5 都写）。
- **知识库只覆盖一份语料**：`data/等级标准节选.txt`（GF 0025—2021 的一至六级指标 + HSK4 词汇量说明）。问语法教学法、课文活动设计这类语料外的问题时，检索到的片段帮助有限，`use_rag=True` 的回答质量不一定优于纯对话。
- **0.5b 可能答不出表格题**：`qwen2.5:0.5b` 读不懂「音节/汉字/词汇/语法」四列数字表，问「HSK4 词汇量」时常回「资料中未提及」（实测）；换 `qwen2.5:1.5b` 或 `prefer="api"` 即可答出「新增 1000 / 累计 3245」。在 `.env` 里改 `LOCAL_MODEL=qwen2.5:1.5b` 即可，无需改代码。
- **首次运行慢**：要建向量库并加载 embedding 模型，之后才快；首次 10–20 秒属正常。
