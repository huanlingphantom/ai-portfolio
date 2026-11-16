# W9 加分选做 · smolagents 映射表与反思

所选路径：**A（跑通）**。装的版本 `smolagents==1.26.0`（Apache-2.0），依赖 `openai`。
把 W9 手写的 `tool_agent.py` 里的两个工具（`hsk_level`、`word_count`）原样搬成 `@tool`，
用 `ToolCallingAgent` 重跑同一类问题，实跑输出见文末。

---

## 1. 五行映射表

| # | 手写循环里我写的东西（`tool_agent.py`） | smolagents 里的对应物 | 实际由谁完成 | 换过来之后变了什么 |
|---|---|---|---|---|
| 1 | `TOOLS = {"get_time": ..., "calc": ..., "hsk_level": ...}` 手写工具名→函数 的字典 | `@tool` 装饰器 + `ToolCallingAgent(tools=[...])` | `Tool.from_function`：读函数签名和 docstring，抽出 name / description / inputs | 不用手写 schema 了；但 **docstring 变成协议**——不写 `Args:` 就没有参数说明，少一个类型注解 `word: str` 就直接报错 |
| 2 | `SYS` 提示词里那 90 来字：可用工具只有这 3 个、只输出一行 JSON、一次一个、不许编造工具名 | 内置 prompt 模板（`site-packages/smolagents/prompts/toolcalling_agent.yaml`），工具清单由 `agent.tools` 自动渲染进去 | 框架负责拼 system prompt | 少写 200 字，也**看不见了**；想让它"只调一个工具"这类约束，得去覆盖模板，不是改一行字符串 |
| 3 | `parse_calls()` 三层兜底：剥 ```json 围栏 → `json.loads` 整体 → 跨行正则抓 `{...}` → 逐块解析并列调用 | 模型返回的 `ChatMessageToolCall`（`name` / `arguments` 已是对象） | openai SDK 的 function calling + 框架解析 | 正则和兜底全部不需要了；代价是**没有兜底**——模型不按格式输出，这里报错，不像手写版还能把文本里那坨 JSON 抠出来救一次 |
| 4 | `TOOLS[name](*args)`：先查白名单，再要求 `args` 是 list，再 `try/except` 把异常转成文字回喂 | `Tool.__call__` → 按 `inputs` 做类型校验/转换后再执行，由 agent 的 `_execute_tool` 调度 | 框架做参数校验与异常包装 | 白名单机制仍在（不在 `tools` 列表里就调不到），但**报错形态变了**：以前是"工具出错：xxx"一句中文，现在是框架把异常信息塞进 observation，格式不完全由我定 |
| 5 | `run()` 的 `for` 循环 + `max_calls=2`，到顶 `break` 并让模型"用已有结果回答" | `MultiStepAgent` 的 `max_steps` + 内置 `final_answer` 工具；每步的 `TaskStep.observations` 存进 memory，下一轮重渲染 | 框架计步、管上下文、决定何时收口 | 回喂不用自己拼 messages 了；但 `max_steps` 到顶是**抛 `AgentMaxStepsError`**，手写版是降级收口不报错——同一个"到顶"，一个报错一个不报 |

补充一句回喂：手写版是把 `工具结果：...` 字符串 append 进 `messages`；框架版是 `observations` 挂在 `TaskStep` 上，
下一轮由模板把整段 memory 重新渲染。结果一样，**能省掉的 token 不一样**——手写版我能只回喂结论，框架版会把历史一起带上（见下面 token 数）。

---

## 2. 同一件事，两边各写了多少

| | `tool_agent.py`（手写） | `smolagents_demo.py`（框架） |
|---|---|---|
| 文件大小 | 5,963 B / 153 行 | 1,916 B / 61 行 |
| 其中"循环/解析/容错" | 约 54 行（`parse_calls` 29 行 + `run` 25 行，含注释与空行） | 0 行 |
| 其中工具本身 | 3 个 | 2 个（同一套 CSV 查表逻辑） |
| 装配 | 手写 `SYS` + `TOOLS` 字典 | `ToolCallingAgent(tools=[...], model=..., max_steps=3)` 一行 |
| 首轮输入 token | 未单独记账（`SYS` 约 90 字 + 用户一句话） | **1,345**（模板 + 工具 schema 占大头） |

省下来的五十多行是真实的；多花的 1,000 多 input token 也是真实的。这两件事得一起看。

---

## 3. 反思（362 字，不含标点）

框架替我管的是**协议**：schema 怎么生成、`tool_calls` 怎么解析、参数类型怎么校验、步数怎么记、异常怎么包。
这五件事在 `tool_agent.py` 里是我一行行抠出来的，抠的时候正好把 Function Calling 的四步（提出→决定→执行→回喂）看清楚了；
换成 smolagents 之后，这四步还在，但**全部沉到框架里，看不见了**。

我交出去的是**控制权**，而且丢得比预想的多。最典型的是 `max_calls`：手写版到顶是"用已有结果收口"，属于降级；
框架版到顶直接抛 `AgentMaxStepsError`，属于失败。同一句"最多两步"，两种语义。解析也是——手写的三层兜底是为
`deepseek-chat` 会夹带解释文字这个毛病准备的，换到框架里这层保险没了，只能指望模型老实。prompt 更明显：
`SYS` 我能一眼看完、随手改一个字，模板得去 `site-packages` 里翻。

所以我的结论不是"框架更好"或"手写更好"，而是：**框架省的是重复劳动，不是安全责任**。
四道防线在框架里都有对应实现，位置和默认值都变了；而真正兜底的那道——`calc` 里 `ast.parse` 只放行数字和
`+ - * / ** %`、绝不裸 `eval`——换任何框架都得自己写在工具函数里，框架管不到。这条边界换框架之后依然必要，
因为模型层可以拒绝一次（轨迹 3 就是这样），但不能指望它每次都拒绝。

许可证：smolagents 为 Apache-2.0，本作业只作为依赖调用，未复制其源码；`smolagents_demo.py` 顶部已注明出处。

---

## 4. 复现

```bash
pip install "smolagents==1.26.0" openai python-dotenv
# 根目录 .env 里要有 DEEPSEEK_API_KEY
python week9/smolagents_demo.py
```

Windows 下若 `pip` 报 502，先清掉 `HTTP_PROXY/HTTPS_PROXY` 再装。

---

## 5. 运行输出（原样，未删改）

```text
问： '把'字是 HSK 几级词汇？顺便看看「愚公移山」里能命中几个生词。
┌────────────────────────────────── New run ──────────────────────────────────┐
│ '把'字是 HSK 几级词汇？顺便看看「愚公移山」里能命中几个生词。               │
└─ OpenAIModel - deepseek-chat ───────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ Calling tool: 'hsk_level' with arguments: {'word': '把'}
│ Calling tool: 'word_count' with arguments: {'text': '愚公移山'}
Observations: 把 是 3 级
Observations: 命中生词表 2 个：愚公、愚公移山
[Step 1: Duration 2.18 seconds| Input tokens: 1,345 | Output tokens: 64]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ Calling tool: 'final_answer' with arguments: {'answer': '「把」是 HSK 3
│ 级词汇。\n\n「愚公移山」这段文本按生词表匹配，去重后命中 2
│ 个生词：愚公、愚公移山（即两个词条，其中包含整个成语本身）。'}
Final answer: 「把」是 HSK 3 级词汇。
「愚公移山」这段文本按生词表匹配，去重后命中 2 个生词：愚公、愚公移山（即两个词条，其中包含整个成语本身）。
[Step 2: Duration 1.34 seconds| Input tokens: 2,831 | Output tokens: 151]
```

值得记一笔的两点：

1. **Step 1 一次并行调了两个工具**。手写版 `SYS` 里我明确写了"一次只调用一个工具"，
   smolagents 的模板没这个约束，模型就并行发了两个 `tool_calls`——这也说明"一次一个"从来不是模型的能力边界，
   是我在 prompt 里加的人为限制。
2. **`final_answer` 是框架自带的工具**，不在我传的 `tools` 列表里，但它出现在调用轨迹里。
   对照第 4 行"不在列表里就调不到"——内置工具是例外，这一点读文档时容易漏。
