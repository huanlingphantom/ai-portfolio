# W8 互评表 · 学科智能问答助手 v1.0

- **评阅对象**：指定对象 `github:zxz061130/ai-portfolio`（另核查其自述的"正本"仓库 `github:cxy94/ai-portfolio`，原因见下）
- **核查时间**：2026-11-12（课后复核，按届时远端状态）
- **我的环境**：Windows 11 / Python 3.13（venv）/ Ollama `qwen2.5:0.5b` + `qwen2.5:1.5b` + `nomic-embed-text` / Git 2.55
- **纪律**：只写"我执行了什么命令、机器回了什么"，不打分、不评价人；发现的问题按"照着改就能好"的方式写。

## 〇、先交代一件事：指定仓库里只有"提交包副本"

指定仓库 `zxz061130/ai-portfolio` 的最新提交是 `3a6cb6b`（2026-11-09 17:59，"Add files via upload"），新增的是 `第八周提交包/` 六个文件加一个证据目录。这个目录里的 `00_提交清单.md` 开头写着：

> 本文件夹是**汇总副本**，正式提交以仓库 `cxy94/ai-portfolio` 为准（已 push，含标签 v1.0）。

所以我把核查分成两条线：**A 线 = 指定仓库 `zxz061130`**（课程分配给我的对象），**B 线 = 正本 `cxy94`**（对方文档自述的正式仓库）。两条线的现象分开写，不做合并判断。

| 事实 | A 线 `zxz061130` | B 线 `cxy94` |
|---|---|---|
| 最后一次推送 | 2026-11-09T09:59Z | 2026-11-12T04:42Z |
| `week08_assistant_v1/` 目录 | **不存在** | 存在（6 个文件） |
| 根 `README.md` | 3566 B，**未含 W8 一行** | 4235 B，目录表已加 `week08_assistant_v1/` |
| 标签 | **0 个** | `v1.0` → `aea5129` |
| Release | **0 个** | `v1.0 学科智能问答助手`，2026-11-11T14:28Z |

---

## ① 能不能跑：`python assistant_v1.py` 有无报错、三问是否都有回答

### A 线 · 指定仓库

照 `第八周提交包/02_README.md` 的「怎么用」原样执行：

```
$ python week08_assistant_v1/assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"
python.exe: can't open file '...\_peer3\week08_assistant_v1\assistant_v1.py':
[Errno 2] No such file or directory
（返回码 2）
```

不是路径笔误：该仓库 `git ls-files` 里没有 `week08_assistant_v1/` 这一层，代码只以副本形式放在 `第八周提交包/01_assistant_v1.py`。改跑副本：

```
$ python 第八周提交包/01_assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"
[嵌入] Ollama nomic-embed-text（768 维）@ 127.0.0.1:11434
[建库] 库里没有 → 重新分块并写入 chroma_db/
[分块] 17 块 ｜ 长度 min/avg/max = 61/255/484 ｜ 文件：愚公移山.txt, 生词表.csv, 等级标准节选.txt
[建库] 完成，9.19s
问：HSK 4 级累计需要掌握多少词汇、多少汉字？
模式：RAG（先查再答） ｜ 引擎：local ｜ prefer=local ｜ 回退：否 ｜ 7.68s
检索：命中 5 段 —— 《等级标准节选.txt》第10段、《生词表.csv》第1段、《等级标准节选.txt》第12段、《等级标准节选.txt》第5段、《等级标准节选.txt》第6段
答：资料中未提及。
（返回码 0）
```

结论（A 线）：按 README 写的那条命令跑不起来（文件不存在）；副本能跑，检索也命中了量化表所在的第 5 段，但本机 0.5b 仍答"资料中未提及"。

### B 线 · 正本仓库

同一个问题，三种跑法（都在仓库根目录执行）：

```
$ python week08_assistant_v1/assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"
（返回码 0）
模式：RAG ｜ 引擎：local ｜ 0.23s
检索：命中 5 段 —— ……《等级标准节选.txt》第5段……
答：资料中未提及。

$ python week08_assistant_v1/assistant_v1.py "同上" --no-rag
（返回码 0）
模式：纯对话（不给资料） ｜ 引擎：local ｜ 3.71s
答：……词汇量：10000 …… 因此词汇数量为 10000/100 = 100个词汇，汉字 10000/10 = 1000个汉字。

$ LOCAL_MODEL=qwen2.5:1.5b python week08_assistant_v1/assistant_v1.py "同上"
（返回码 0）
模式：RAG ｜ 引擎：local ｜ 14.49s
答：HSK 4 级累计需要掌握的词汇数量为 3245 个，累计汉字数量为 1200 个。
出处：（本次答案未标出处，或资料里没有依据）
```

`--demo` 五问（三问 + 开/关 RAG 对照）全部返回，返回码 0，无一崩溃：

| # | 问题 | 模式 | 回答摘要 | 出处 |
|---|---|---|---|---|
| 1 | 把字句的教学难点有哪些？该怎么给 HSK 3 级学生讲？ | RAG | 「资料中未提及」 | 无 |
| 2 | HSK 4 级累计需要掌握多少词汇、多少汉字？ | RAG | 3245 个词 / 1200 个字 | 无 |
| 3 | 《愚公移山》可以设计什么课堂活动？ | RAG | 分角色朗读、辩论"愚公愚不愚"、成语接龙 | 无 |
| 4 | （同 2） | RAG | 3245 / 1200（与第 2 问一致） | 无 |
| 5 | （同 2） | 纯对话 | 1000 个词 / 1000 个字（与资料不符） | 无 |

现象小结（B 线）：**能跑、三问都有回答、`use_rag` 与 `prefer` 都生效**（同一问题第 2/4 问与第 5 问结论不同即可证明开关起作用）。两处与文档有出入要记下：一是按 README 指定的 0.5b，第 2 问答"未提及"，换成 1.5b 才给出 3245/1200；二是 1.5b 下 5 条答案**都没写出处**——这一条对方 README「已知问题」第 3 条其实已经写了。

---

## ② README 能复现吗：照着「怎么装 / 怎么用」能否跑通

### A 线

- 根 `README.md`（3566 B）是作品集目录表，**没有 W8 那一行**；W8 的说明只存在于 `第八周提交包/02_README.md`。
- `02_README.md`「怎么装」第 1 步 `pip install -r week08_assistant_v1/requirements.txt`——这个路径在 A 线仓库里不存在，照抄会在第 1 步就报 `No such file`（我实测的最后一步报错见①）。
- 「怎么用」三条命令全部指向 `week08_assistant_v1/assistant_v1.py`，同样指向不存在的路径。

### B 线

- 根 `README.md` 已把 `week08_assistant_v1/` 列进目录表（W8 一行写明了 `assistant_v1.py`、四段式 README、三问三答证据）。
- `week08_assistant_v1/README.md` 四段式齐全：功能 / 怎么装（3 步，含两条 `ollama pull`）/ 怎么用（3 条可直接粘贴的命令 + 常用开关说明）/ 已知问题（3 条）。另有"三块积木怎么接"的调用链图和 5 行映射表。
- 我照「怎么装」的三步 + 「怎么用」的第 1、2 条走通，得到上面①里 B 线的输出；`requirements.txt`（637 B）能直接 `pip install -r` 解析。
- 一处小出入：README 第 2 步让你拉 `qwen2.5:0.5b`，但同一条"已知问题"又说 0.5b 会放弃答数字——我实测确实如此，**换 1.5b 才复现出 answer_log 里的 3245/1200**。建议把「怎么装」里的默认模型直接写成 1.5b，或把 `LOCAL_MODEL` 的说明提到更显眼的位置。

---

## ③ Release 发了吗：远端有无 v1.0 标签、Release 页面说明是否齐全

```
# A 线
$ git ls-remote --tags https://github.com/zxz061130/ai-portfolio.git
（输出为空）
GET /repos/zxz061130/ai-portfolio/tags     → []
GET /repos/zxz061130/ai-portfolio/releases → []

# B 线
GET /repos/cxy94/ai-portfolio/tags     → ['v1.0']（指向 aea5129）
GET /repos/cxy94/ai-portfolio/releases → [('v1.0', 'v1.0 学科智能问答助手', 2026-11-11T14:28:36Z)]
```

- A 线：标签与 Release 都不存在。对方 `00_提交清单.md` 里写的是"标签 v1.0 已 push --tags"，但那条证据指向的是 B 线仓库（证据文件 `git_提交与标签.txt` 里 `origin` 就是 `cxy94`），A 线这边没有对应物。
- B 线：Release 页面已发，正文 1542 字符，含「功能 / 安装 / 用法 / 这一版做了什么 / 对照证据 / 已知问题」六段，命令可直接复制。
- B 线 Release 正文第一段是一行操作提示：「用法：仓库 → Releases → *Draft a new release* → 选 v1.0 → 把下面整段粘进说明框」——这是给自己看的粘贴指引，跟着一起贴到了正式页面顶部。不影响阅读，但读者第一眼看到的是操作步骤而不是版本说明，建议删掉这一行。

---

## ④ 有没有已知限制：README 是否诚实写了「已知问题」

- **B 线：有。** `week08_assistant_v1/README.md` 的「已知问题」3 条：首次运行 1–3 分钟；Ollama 没起会整条失败；0.5b 会漏标出处、会把提示词占位符原样抄出来、会放弃答数字。这三条我都撞到了其中两条（0.5b 答"未提及"、1.5b 漏标出处），说明写得准。证据目录里另有一份 `200字_为什么如实写已知问题.md`。
- **A 线：副本里有，根 README 里没有。** 读者从仓库首页点进来，看不到 W8 的任何限制说明。
- 两仓共同的一处：`week04_API/.env` 已入库（679 B）。内容是占位文本，`DEEPSEEK_API_KEY` 的值只有 12 个字符、以 `sk-` 开头，**不是真实密钥**，所以不构成泄密；但文件本身进了版本库，与根 README「`.env` 永不入库」的约定相反，且因为早已被跟踪，两份 `.gitignore` 里的 `.env` 规则对它都不生效。建议 `git rm --cached week04_API/.env` 后提交一次。
- A 线另有 `week06_双引擎/__pycache__/llm.cpython-311.pyc` 入库（B 线已无）；同样因已跟踪，`__pycache__/` 规则对它无效。

---

## 五、如果对方要改，按这五步就到位

1. **先定一个"交作业的仓库"**：若 B 线 `cxy94` 才是正式仓库，请把 `00_提交清单.md` 里"正式提交以 cxy94 为准"这句改成课程要求的仓库地址（或反过来，在 A 线补齐 `week08_assistant_v1/` 整目录），避免评阅人/老师按分配表打开时看到的是副本。
2. **A 线补目录或改路径**：把 `第八周提交包/01_assistant_v1.py` 等放回 `week08_assistant_v1/`，或把 README 里所有 `week08_assistant_v1/` 改成 `第八周提交包/`。
3. **A 线补 tag 与 Release**：`git tag -a v1.0 -m "..."` + `git push --tags`，再在网页端发 Release（B 线已有的说明可直接复用）。
4. **清掉误入版本库的文件**：`git rm --cached week04_API/.env`（两仓都要），A 线再加 `week06_双引擎/__pycache__/llm.cpython-311.pyc`。
5. **默认模型写 1.5b**：README「怎么装」第 2 步与 `.env.example` 的 `LOCAL_MODEL` 统一成 `qwen2.5:1.5b`；否则读者按 0.5b 装完，第一次问 HSK4 就会得到"资料中未提及"，和 answer_log 对不上。

---

## 六、我执行过的完整命令（可复现）

```bash
# 取两仓
git clone --depth 1 https://github.com/zxz061130/ai-portfolio.git   # A 线
git clone --depth 1 https://github.com/cxy94/ai-portfolio.git       # B 线

# A 线：照 README 跑 → No such file；改跑副本 → 能跑，回“资料中未提及”
python week08_assistant_v1/assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"
python 第八周提交包/01_assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"

# B 线：三问 + 开/关对照 + 换 1.5b
python week08_assistant_v1/assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"
python week08_assistant_v1/assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？" --no-rag
LOCAL_MODEL=qwen2.5:1.5b python week08_assistant_v1/assistant_v1.py "HSK 4 级累计需要掌握多少词汇、多少汉字？"
LOCAL_MODEL=qwen2.5:1.5b python week08_assistant_v1/assistant_v1.py --demo --out _demo_out.md

# 远端标签与 Release（两仓各查一次）
git ls-remote --tags https://github.com/zxz061130/ai-portfolio.git
GET /repos/zxz061130/ai-portfolio/releases
GET /repos/cxy94/ai-portfolio/releases/tags/v1.0
```

> 说明：本次核查期间 GitHub 走代理偶发 `CONNECT tunnel failed, response 502`，重试后克隆成功；502 出现在我这一侧，与对方仓库无关。
