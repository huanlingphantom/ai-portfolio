# W8 互评表 · 学科智能问答助手 v1.0

- **评阅对象**：GitHub 账号 `zxz061130`（题目指定的互评对象；仓库内未标注真实姓名，互评表按账号记）
- **对象仓库**：<https://github.com/zxz061130/ai-portfolio>（默认分支 `main`）
- **评阅时间**：2026-11-09
- **我的环境**：Windows 11 / Python 3.13（venv）/ Ollama `qwen2.5:1.5b` + `nomic-embed-text` / Git 2.55
- **评阅方式**：完整 clone 后照 README 与《第八次课讲义》第八节的命令逐条试跑；下面每条结论都附命令与输出原文，不采信"我这儿能跑"这类说法。
- **纪律**：本表只描述现象、不打分、不评价人；发现的问题按"对方照着改就能好"的方式写。

---

## 〇、先看仓库实况（时间线对得上不上）

| 观察项 | 实际情况 | 取法 |
|---|---|---|
| 最后一次推送 | `2026-11-04T10:44:07Z`（北京时间 11-04 18:44） | GitHub API `GET /repos/zxz061130/ai-portfolio` |
| 最新提交 | `merge: 把 W1–W7 全量并入（以本地开发版为准）` | `GET /commits` |
| 顶层目录 | `week01_环境 / week03_Python / week04_API / week05_本地部署 / week06_双引擎 / week07_RAG` 等 21 项 | `git clone` 后 `ls`，与 API tree（77 条）一致 |
| 是否存在 W8 目录 | **不存在** `week08/`、`week8/` | 文件名检索，命中 0 |
| 是否存在 `assistant_v1.py` | **不存在**；全仓文件名含 `assistant` 的条目为 0 | `git ls-files` + API tree 检索 |
| 标签 | **0 个** | `git ls-remote --tags` 返回空；`GET /tags` 长度为 0 |
| Release | **0 个** | `GET /releases` 长度为 0 |

> 说明：仓库里 W1–W7 的内容是齐的（W7 有 `rag_qa.py` 35 KB、幻觉对照表、运行记录 15 KB），但 W8 的部分在远端看不到。

---

## ① 能不能跑：`python assistant_v1.py` 有无报错、三问是否都有回答

**照做的步骤**

```bash
git clone https://github.com/zxz061130/ai-portfolio.git
cd ai-portfolio
python assistant_v1.py
```

**实际结果（报错原文）**

```
$ python assistant_v1.py
python.exe: can't open file 'C:\...\ai-portfolio\assistant_v1.py':
[Errno 2] No such file or directory
（返回码 2）
```

**现象说明**

- 不是"路径写错"或"装依赖的顺序不对"：`assistant_v1.py` 在仓库里根本不存在（见〇节）。
- 因此第 2 步的 `use_rag` 开关、`prefer` 引擎参数都**无法验证**——没有入口函数可以调；三问三答也无从开始（不是"三问三崩"，是"一问都进不去"）。
- 我另外试了仓库里已有的 W7 积木，判断是"缺 W8 粘合层"还是"整条链都缺"：

**顺带试了已有积木（W7）**：为了分清"是缺 W8 粘合层"还是"整条链都跑不起来"，我在同一份 clone 里照 README 跑了两条命令：

```
$ python week07_RAG/rag_qa.py --ingest
[嵌入] Ollama nomic-embed-text（768 维）@ 127.0.0.1:11434
[建库] 库里没有 → 重新分块并写入 chroma_db/
[分块] 17 块 ｜ 长度 min/avg/max = 61/255/484 ｜ 文件：愚公移山.txt, 生词表.csv, 等级标准节选.txt
[建库] 完成，28.69s
[自检] 库里可检索：是 ｜ 总耗时 66.87s
（返回码 0）

$ python week07_RAG/rag_qa.py "HSK 四级累计词汇量是多少？"
[复用] 已有库（OllamaEmbeddings，chunk=500/50）：chroma_db/
[检索] 向量+关键词重排 命中 3 段：《等级标准节选.txt》第10段、《等级标准节选.txt》第5段、《生词表.csv》第1段
[答] 资料中未提及。
[数字校验] ✓ 答案里的数字都能在资料里对上
[引擎] local ｜ 25.36s ｜ 回退: 否 ｜ prefer=local
（返回码 0）
```

现象：W7 积木能建库、能检索、能出答案（本机 `qwen2.5:1.5b` 这一问回了"资料中未提及"，同机我自己的助手答"1000/3245"，差别在提示词与检索重排，属模型/检索的表现，不是崩溃）。**说明缺的是 W8 那一层"接线"，不是底下的砖。**

**小结**：`python assistant_v1.py` 复现结果是 `No such file or directory`，三问一题未答。

---

## ② README 能复现吗：照着「怎么装 / 怎么用」能否跑通

**README 现状（`README.md`，3566 B）**：是一份"作品集总目录"式说明，四节为「目录（表格，21 行）/ 怎么跑（W3–W7 共 8 条命令）/ 依赖（按周列）/ 约定（3 条）」。

**照着做的结果**

| README 里的步骤 | 我执行的结果 |
|---|---|
| `pip install -r requirements.txt` | 文件存在（351 B，11 个包）。**注意**：里面列了顶层 `langchain`（无版本下限），本机 `pip install langchain langchain-community==0.4.x` 解析会长时间空转；我按周用 `--only-binary=:all:` 分批装才过（这是我机器上的现象，供参考） |
| `cp .env.example .env` + 填 key | 可执行，`.env.example` 在仓库根（1002 B） |
| `python week07_RAG/rag_qa.py --ingest` | 见①节的 W7 试跑结果 |
| `python assistant_v1.py` | **README 里没有这一步**，也没有任何 W8 的运行说明 |

**现象说明**

- 「怎么装」的依赖粒度是"按周"，没有针对 W8 的一份完整安装清单（缺 W8 需要的 `langchain-text-splitters`）；`requirements.txt` 里反而多出 W9/W15 才用的 `mcp[cli]`、`streamlit`。
- 「怎么用」覆盖到 W7 为止；照 README 走完，读者无法得到一个能问答的助手——不是命令报错，而是**没有这一节**。
- 「已知问题」一栏缺失：全文检索「已知 / 限制 / 问题」三个词，命中数均为 0。

---

## ③ Release 发了吗：远端有无 v1.0 标签、Release 页面说明是否齐全

**照做的步骤与结果**

```bash
$ git ls-remote --tags https://github.com/zxz061130/ai-portfolio.git
（输出为空）
```

```
GET https://api.github.com/repos/zxz061130/ai-portfolio/tags     → []
GET https://api.github.com/repos/zxz061130/ai-portfolio/releases → []
```

**现象说明**

- 远端没有任何标签，`v1.0` 不存在；网页 <https://github.com/zxz061130/ai-portfolio/releases> 打开后是"没有发布任何版本"的空页面。
- 顺带说明一个常见坑的排查结果：这里不是"打了 tag 但忘了 push --tags"（那样 `ls-remote` 至少能看到本地 tag 的对照物，且 `GET /tags` 会有记录），而是**标签在远端完全不存在**。

---

## ④ 有没有已知限制：README 是否诚实写了「已知问题」

**现象**

- `README.md` 无「已知问题 / 已知限制 / Known issues」段落（关键词命中 0）。
- 最接近的是「约定」三条（`.env` 不入库、脚本一律 LF、产物路径由 `weekpath.py` 解析）——这是**开发约定**，不是**能力边界**，读者看不出"什么情况下这个助手会答错、会拒答、会跑不起来"。
- 有两处与"诚实写限制"相关的事实，列出来供对方自查（只描述，不评价）：

  1. **`week04_API/.env` 已入库**（679 B）。内容是占位说明，`DEEPSEEK_API_KEY` 的值只有 12 个字符、以 `sk-` 开头，**不是真实密钥**，因此不构成泄密；但文件本身进了版本库，与仓库根 README「`.env` 永不入库」的约定、以及 `week04_API/.gitignore` 里 `.env` 那条规则不一致（该文件在两份 `.gitignore` 生效之前就已被跟踪，规则对它无效）。
  2. **`week06_双引擎/__pycache__/llm.cpython-311.pyc` 已入库**（21991 B）。提交历史里有一条 `chore: 删掉 main 上误上传的嵌套重复目录（…含一个 .pyc）`，说明清理过一次；但当下的 `__pycache__` 仍在库里，根 `.gitignore` 的 `__pycache__/` 对它同样不生效（已跟踪）。

**小结**：四维度里，①③ 无法达成（入口文件与标签都不在远端），②只覆盖到 W7、缺 W8 一节，④整段缺失。

---

## 五、如果对方要补，按这五步就能到位（不动别的代码）

1. 加 `week08/assistant_v1.py`：`answer(question, use_rag=True, prefer="local")` + 三问循环 + `try/except` 打印「运行失败：原因」。
2. 加 `week08/README.md` 四段式：功能 / 怎么装（含 `ollama pull qwen2.5:0.5b` 与 `nomic-embed-text`）/ 怎么用（`cd week08 && python assistant_v1.py`）/ 已知问题（至少写"没启动 Ollama 会报连接错误"）。
3. `git tag -a v1.0 -m "助手 v1.0" && git push origin main --tags`，再到网页端发 Release（功能/安装/用法三段）。
4. 清掉误入版本库的文件：`git rm --cached week04_API/.env week06_双引擎/__pycache__/llm.cpython-311.pyc`，确认 `git status` 无 `.env` 后提交（`__pycache__/` 规则才会开始生效）。
5. 补 `week08/answer_log.md`：≥3 个学科问题，每条写清问题原文 / 模式 / 引擎 / 输出摘要 + 一句点评；同一问题开、关 RAG 各答一次最能说明问题。

---

## 六、我这边验证用的完整命令（可复现）

```bash
# 1) 取仓库（首次 clone 遇到代理 502，重试后成功；这属于我本机网络，不是对方仓库的问题）
git clone --depth 1 https://github.com/zxz061130/ai-portfolio.git
cd ai-portfolio
git log -1 --format='%H %ad %s'
git ls-remote --tags https://github.com/zxz061130/ai-portfolio.git

# 2) 维度①：照讲义命令跑
python assistant_v1.py            # → [Errno 2] No such file or directory

# 3) 交叉核对"文件是否真的不存在"
git ls-files | grep -i assistant  # → 无输出

# 4) 维度③：远端标签与 Release
#    GET /repos/zxz061130/ai-portfolio/tags     → []
#    GET /repos/zxz061130/ai-portfolio/releases → []
```

> 最后一句按互评纪律补上：这份表只写"我照着做了什么、机器回了什么"。对方本地可能已经写完只是没推——但**以远端为准**是课程定的口径，`ls-remote` 里没有的东西，别人就复现不出来。
