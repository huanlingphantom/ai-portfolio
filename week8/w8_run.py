# W8 演示留痕：三问 × 四组合（use_rag 开/关 × prefer local/api），结果写 w8_answer_raw.json
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assistant_v1 import answer  # noqa: E402

QS = [
    "把字句的教学难点有哪些",
    "HSK4 词汇量要求是多少",
    "《愚公移山》可以设计什么课堂活动",
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "w8_answer_raw.json")


def main():
    rows = []
    for q in QS:
        for use_rag in (True, False):
            for prefer in ("local", "api"):
                if prefer == "api" and not os.getenv("DEEPSEEK_API_KEY"):
                    rows.append(dict(q=q, use_rag=use_rag, prefer=prefer, ok=False,
                                     text="[跳过] 未注入 DEEPSEEK_API_KEY"))
                    continue
                t0 = time.time()
                try:
                    txt = answer(q, use_rag=use_rag, prefer=prefer)
                    ok = True
                except Exception as e:  # 与 assistant_v1.py 的兜底口径一致
                    txt = "[运行失败] %s: %s" % (type(e).__name__, e)
                    ok = False
                sec = round(time.time() - t0, 1)
                rows.append(dict(q=q, use_rag=use_rag, prefer=prefer, ok=ok,
                                 sec=sec, text=txt))
                print("[%s] rag=%s prefer=%s %.1fs %s" %
                      ("OK" if ok else "FAIL", use_rag, prefer, sec, txt[:60].replace("\n", " ")))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("写出:", OUT)


if __name__ == "__main__":
    main()
