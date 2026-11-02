# W6 边界测试驱动：跑一条路径，把"谁答的、多久、多少钱、有没有回退"打出来。
#
# 用法：
#   python test_paths.py --prefer local --label "① 正常本地"
#   python test_paths.py --prefer local --label "② 关掉 Ollama"
#   python test_paths.py --prefer api   --label "③ prefer=api"
#
# 它不做判断，只如实记录；判断（是否符合预期）写进 week06_test_log.md。
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import weekpath  # noqa: E402

    weekpath.load_env()
except ImportError:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    except ImportError:
        pass

from llm import LLM  # noqa: E402

QUESTION = "给《愚公移山》出一道 HSK4 阅读理解题，4 个选项，并给出答案。"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefer", default="local", choices=["local", "api"])
    ap.add_argument("--question", default=QUESTION)
    ap.add_argument("--label", default="")
    ap.add_argument("--max-tokens", type=int, default=300)
    args = ap.parse_args()

    llm = LLM()
    print("=" * 66)
    print("测试条件：%s" % (args.label or ("prefer=" + args.prefer)))
    print("问题：%s" % args.question)
    print("num_predict/max_tokens：%d" % args.max_tokens)
    print("-" * 66)

    t0 = time.time()
    try:
        text = llm.ask(args.question, prefer=args.prefer, max_tokens=args.max_tokens)
    except Exception as e:
        print("[两条路都失败] %s: %s" % (type(e).__name__, e))
        print("距离发起：%.2fs" % (time.time() - t0))
        print("实际引擎：无")
        return

    st = llm.last_stats
    print("-" * 66)
    print("实际引擎：%s（%s）" % (st.get("engine", "?"), st.get("model", "?")))
    print("总耗时：%.2fs" % llm.last_elapsed)
    print("输出 tokens：%d" % st.get("output_tokens", 0))
    print("估算费用：%.6f 元" % st.get("cost", 0.0))
    print("是否回退：%s" % (llm.last_fallback or "否"))
    print("-" * 66)
    print("答案：")
    print(text.strip()[:600])
    print("=" * 66)


if __name__ == "__main__":
    main()
