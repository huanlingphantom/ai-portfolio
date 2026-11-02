# W7 RAG 学科知识库问答器
# 依赖：pip install langchain-community langchain-chroma langchain-ollama langchain-text-splitters chromadb
# 准备：ollama pull nomic-embed-text
#
# 四步：加载 → 分块 → 向量化 → 检索＋生成
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  数据路径 + 加载 .env

weekpath.load_env()

from langchain_community.document_loaders import TextLoader  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402
from langchain_ollama import OllamaEmbeddings  # noqa: E402
from langchain_chroma import Chroma  # noqa: E402

CORPUS = weekpath.data_path("等级标准节选.txt")      # 不再依赖当前工作目录
PERSIST = weekpath.root_path("chroma_db")            # .gitignore 已排除

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_retrievers = {}      # k -> retriever，换 k 不用重建库


def _add_heading_context(splits, full_text):
    """给每块补上「它属于哪一节」的抬头，再拿去向量化。

    不补的话，那张纯数字的总表（"中等 四级 116/724 300/1200 1000/3245"）
    向量里几乎只有数字，问「四级（中等）本级新增词汇量」时实测排 6 块里的最后一名。
    补上「一、语言量化指标总表（词汇 …）」之后才有语义锚点。
    """
    import re
    heads = [(m.start(), m.group(0).strip())
             for m in re.finditer(r"^[一二三四五六七八九十]+、.*$", full_text, re.M)]
    for d in splits:
        # 块内自己就带标题的，以块内第一条为准（否则会把"注：…"这种尾巴块
        # 错标成上一节的标题）；块内没有标题，才回溯到它前面最近的那一节。
        inner = re.search(r"^[一二三四五六七八九十]+、.*$", d.page_content, re.M)
        if inner:
            head = inner.group(0).strip()
        else:
            start = d.metadata.get("start_index", 0)
            head = "《国际中文教育中文水平等级标准》"
            for pos, h in heads:
                if pos <= start:
                    head = h
        d.page_content = "【%s】\n%s" % (head, d.page_content)
    return splits


def get_vectorstore(rebuild=False):
    """② 分块 + ③ 向量化 + 入库。库已存在就复用，rebuild=True 强制重来。"""
    emb = OllamaEmbeddings(model="nomic-embed-text")   # 本地嵌入，数据不出本机
    if not rebuild and os.path.exists(PERSIST) and os.listdir(PERSIST):
        return Chroma(persist_directory=PERSIST, embedding_function=emb)

    docs = TextLoader(CORPUS, encoding="utf-8").load()   # ① 加载
    if rebuild and os.path.exists(PERSIST):
        # 先删旧库：Chroma.from_documents 是"追加"进同名 collection，
        # 不删就会变成新旧两套块混在一起，检索结果一半是旧数据。
        import shutil
        shutil.rmtree(PERSIST)
    splits = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True).split_documents(docs)
    splits = _add_heading_context(splits, docs[0].page_content)
    print("[建库] 原文 %d 字 → %d 块（chunk_size=%d，overlap=%d）"
          % (len(docs[0].page_content), len(splits), CHUNK_SIZE, CHUNK_OVERLAP))
    return Chroma.from_documents(splits, emb, persist_directory=PERSIST)


def get_retriever(k=3, rebuild=False):
    """④ 检索器。延迟构建：import 本模块不会触发 embedding 计算。"""
    if k not in _retrievers or rebuild:
        _retrievers[k] = get_vectorstore(rebuild=rebuild).as_retriever(
            search_kwargs={"k": k})
    return _retrievers[k]


def retrieve(question, k=3, rebuild=False):
    """把问题向量化，取最相似的 top-k 段拼成上下文。"""
    return "\n".join(d.page_content for d in
                     get_retriever(k=k, rebuild=rebuild).invoke(question))


def retrieve_with_score(question, k=3, rebuild=False):
    """调参/取证用：返回 [(文档, 相似度距离)]。
    Chroma 的距离是「越小越像」，nomic-embed-text 用余弦距离，0 = 完全相同。"""
    vs = get_vectorstore(rebuild=rebuild)
    return vs.similarity_search_with_score(question, k=k)


def build_prompt(question, ctx):
    return ("根据以下资料回答问题，资料中没有的内容就如实说“资料中未提及”：\n"
            "%s\n\n问题：%s" % (ctx, question))


def rag_qa(question, prefer="local", k=3, rebuild=False):
    """检索 → 拼提示词 → 交给 W6 的统一入口 llm.ask()（双向回退全部继承）。"""
    from llm import LLM          # week06 的模块，靠 weekpath 才能 import 到

    llm = LLM()
    ctx = retrieve(question, k=k, rebuild=rebuild)
    return llm.ask(build_prompt(question, ctx), prefer=prefer)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="W7 RAG 问答器")
    p.add_argument("question", nargs="*", help="问题，默认问 HSK4 词汇量")
    p.add_argument("--prefer", default="local", choices=["local", "api"],
                   help="本地优先还是云端优先（双向回退不变）")
    p.add_argument("-k", type=int, default=3, help="检索段数，默认 3")
    p.add_argument("--rebuild", action="store_true", help="换语料后强制重建向量库")
    p.add_argument("--show", action="store_true", help="只打印检索结果与相似度，不生成")
    args = p.parse_args()

    q = " ".join(args.question) or "HSK4 需要掌握多少词汇？"

    if args.show:
        for i, (doc, score) in enumerate(
                retrieve_with_score(q, args.k, rebuild=args.rebuild), 1):
            print("--- 片段 %d｜距离 %.4f ---" % (i, score))
            print(doc.page_content.strip()[:220])
        sys.exit(0)

    ctx = retrieve(q, k=args.k, rebuild=args.rebuild)
    print("【检索片段】\n", ctx[:300], "\n---")
    print(rag_qa(q, prefer=args.prefer, k=args.k))
