# 官方 RAG 流水线 ↔ 我的 rag_qa.py 映射表

对照对象：LangChain 官方 RAG 教程（<https://docs.langchain.com/oss/python/langchain/rag>，只读 2-Step RAG 段）
与 Datawhale llm-universe（<https://github.com/datawhalechina/llm-universe>，C3/C4）。
我的代码：`week07_RAG/rag_qa.py` + `week08_助手v1.0/assistant_v1.py`。

| 官方流水线 | llm-universe 对应章节 | 我的代码（函数 / 参数） |
|---|---|---|
| Load + Split 加载与分块 | C3 数据处理：读取、清洗与切片 | `TextLoader(CORPUS, encoding="utf-8")` 读 `data/等级标准节选.txt`；`RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, add_start_index=True)`；再用 `_add_heading_context()` 给每块补「【一、语言量化指标总表…】」抬头，让纯数字表块也能被检索到 |
| Embed + Store 向量化入库 | C3 词向量及向量知识库、搭建并使用向量数据库 | `OllamaEmbeddings(model="nomic-embed-text")`（274 MB，本地跑）+ `Chroma(persist_directory=.../chroma_db)` 持久化；`rebuild=True` 时先 `shutil.rmtree` 再建——`from_documents` 是**追加**写入，不删库会得到 12 块而不是 6 块 |
| Retrieve 检索 | C4 基于 LangChain 搭建检索问答链 | `retrieve(question, k=3)` → `similarity_search_with_score` 取 top-3（返回余弦**距离**，越小越像）；`assistant_v1.answer()` 里 `use_rag=True` 才走这一步，`False` 直接问 |
| Prompt + Generate 拼词与生成 | C4 将 LLM 接入 LangChain | `build_prompt()` 拼「指令 + 带 `[1][2][3]` 编号的资料 + 问题」，要求末尾写「出处：[n]」；再交 `LLM().ask(prefer="local"\|"api")` 生成 |
| Deploy + Evaluate 部署与评估 | C4 Streamlit 部署知识库助手；C5 系统评估与优化 | 评估已在 `week07_RAG/hallucination_log.md` 落地（同一问题裸答 vs RAG 答，5 组 × 4 列，带命中判定）；部署留到 W15 用 Streamlit |

## 两条迁移心得

1. **组件可替换，应用逻辑不动**：官方明确 loaders / splitters / embeddings / vector stores 都能单独换。我把云端 embeddings 换成本地 `nomic-embed-text`、英文语料换成 HSK 等级标准节选，`answer()` 一行没改——只改了两个构造参数。
2. **评估闭环不一定要框架**：llm-universe 的 C5 用 RAGAS 一类工具算指标；我暂时用「关键词命中 + 逐条留痕」的土办法，结论一样清楚（裸答 0/5、RAG·1.5b 4/5、RAG·云端 5/5），也更容易看出错在哪一步。

> 许可证提醒：llm-universe 仓库未附 LICENSE，按默认规则保留所有权利——只读思路、署名引用，未复制其代码。
