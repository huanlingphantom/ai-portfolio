# W7 幻觉对照实验：裸答 vs 带资料答（同一个模型，只差一份资料）
# 用法：python week07_RAG/w7_check.py
# 产出：week07_RAG/w7_结果.json（hallucination_log.md 的原始数据）
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402

weekpath.load_env()

from llm import LLM                      # noqa: E402  W6 的统一入口
import rag_qa                            # noqa: E402  W7 的检索＋生成

# 问题 / 语料里的标准答案（人工从 data/等级标准节选.txt 抄，用于判对错）
CASES = [
    ("完成中等阶段的学习，应掌握多少个词语？", "5456"),
    ("完成中等阶段的学习，应掌握多少个语法点？", "424"),
    ("完成中等阶段的学习，应掌握多少个音节？", "908"),
    ("HSK4 需要掌握多少词汇？", "3245"),
    ("高等阶段结束时应掌握多少个汉字？", "3000"),
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "w7_结果.json")
KW = dict(temperature=0.0, max_tokens=400)   # 温度压低，减少随机性，对照才稳


def nums(text):
    """把答案里的数字都抠出来（含 1,000 这种千分位写法）。"""
    return set(re.findall(r"\d[\d,]*", text.replace(",", "")))


def main():
    rows = []
    for i, (q, gold) in enumerate(CASES, 1):
        row = {"no": i, "question": q, "gold": gold}

        # 三列裸答：小模型（本地 1.5b）／云端大模型（deepseek-chat）
        t = time.time()
        row["bare"] = LLM().ask(q, prefer="local", **KW)
        row["bare_s"] = round(time.time() - t, 1)

        t = time.time()
        row["bare_api"] = LLM().ask(q, prefer="api", **KW)
        row["bare_api_s"] = round(time.time() - t, 1)

        # 两列 RAG：同一批资料，分别交给本地与云端生成
        t = time.time()
        row["rag"] = rag_qa.rag_qa(q, prefer="local", k=3)
        row["rag_s"] = round(time.time() - t, 1)

        t = time.time()
        row["rag_api"] = rag_qa.rag_qa(q, prefer="api", k=3)
        row["rag_api_s"] = round(time.time() - t, 1)

        row["chunks"] = [
            {"dist": round(float(s), 4), "head": rag_qa._head(d)}
            for d, s in rag_qa.retrieve_with_score(q, k=3)
        ]
        row["gold_in_bare"] = gold in nums(row["bare"])
        row["gold_in_bare_api"] = gold in nums(row["bare_api"])
        row["gold_in_rag"] = gold in nums(row["rag"])
        row["gold_in_rag_api"] = gold in nums(row["rag_api"])
        rows.append(row)
        print("[%d] %s | gold=%s | 裸答 %s/%s | RAG %s/%s"
              % (i, q, gold, row["gold_in_bare"], row["gold_in_bare_api"],
                 row["gold_in_rag"], row["gold_in_rag_api"]), flush=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("已写入", OUT)


if __name__ == "__main__":
    main()
