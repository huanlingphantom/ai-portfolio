# W9 调用轨迹记录器：把「决定 → 执行 → 回喂 → 再生成」每一轮的原文都留下来
# 用法（在 week09_工具调用 目录）：
#   python trace_demo.py              # 跑全部 4 条
#   python trace_demo.py 1            # 只跑第 1 条
# 产物：轨迹记录.json（原始数据）+ 轨迹记录.md（可读版），都在 week09_工具调用 目录
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tool_agent as ta  # noqa: E402  SYS / TOOLS / parse_calls / get_client / MODEL

HERE = os.path.dirname(os.path.abspath(__file__))

CASES = [
    ("复合问句（课堂演示用句）",
     "请依次查询两件事：1. '把'字的 HSK 等级是多少？2. 现在的时间是多少？"),
    ("单工具·算术",
     "帮我算一下 35*24 等于多少"),
    ("越权表达式（安全边界）",
     "用 calc 计算这个表达式：__import__('os').system('echo hacked')"),
    ("口语式复合问句（预期失败案例）",
     "'把'字是几级？现在几点？"),
]


def run_traced(question, max_calls=2):
    """与 tool_agent.run() 同构，但每一轮的模型原文与工具返回都记下来。"""
    msgs = [{"role": "system", "content": ta.SYS}, {"role": "user", "content": question}]
    rounds = []
    final = None
    for i in range(max_calls):
        t0 = time.time()
        txt = ta.get_client().chat.completions.create(
            model=ta.MODEL, messages=msgs).choices[0].message.content
        raw = txt
        calls = [c for c in ta.parse_calls(txt)
                 if isinstance(c.get("tool"), str) and c.get("tool") in ta.TOOLS]
        ignored = [c for c in ta.parse_calls(txt) if c not in calls]
        step = {"round": i + 1, "model_raw": raw, "parsed_calls": calls,
                "ignored_calls": ignored, "tool_results": [], "sec": round(time.time() - t0, 2)}
        if not calls:
            step["note"] = "本轮没有有效工具调用 → 视为最终回答"
            rounds.append(step)
            final = txt
            break
        results = []
        for call in calls:
            args = call.get("args") or []
            if not isinstance(args, list):
                results.append("工具参数格式错误：%r" % (args,))
                continue
            try:
                results.append("%s%r → %s" % (call["tool"], args, ta.TOOLS[call["tool"]](*args)))
            except Exception as e:
                results.append("工具执行失败：%s" % e)
        step["tool_results"] = results
        rounds.append(step)
        msgs += [{"role": "assistant", "content": txt},
                 {"role": "user", "content": "工具返回：%s。请据此作答。" % "；".join(results)}]
    if final is None:
        t0 = time.time()
        final = ta.get_client().chat.completions.create(
            model=ta.MODEL, messages=msgs).choices[0].message.content
        rounds.append({"round": len(rounds) + 1, "model_raw": final, "parsed_calls": [],
                       "ignored_calls": [], "tool_results": [],
                       "note": "max_calls 用尽 → 强制收口", "sec": round(time.time() - t0, 2)})
    return {"question": question, "rounds": rounds, "final": final}


def main():
    pick = sys.argv[1] if len(sys.argv) > 1 else None
    out = []
    for idx, (name, q) in enumerate(CASES, 1):
        if pick and str(idx) != pick:
            continue
        print("=" * 70)
        print("[%d] %s" % (idx, name))
        print("问：", q)
        rec = run_traced(q)
        rec["name"] = name
        rec["model"] = ta.MODEL
        for r in rec["rounds"]:
            print("  第%d轮 模型原文：%s" % (r["round"], r["model_raw"].replace("\n", " ⏎ ")[:160]))
            if r["tool_results"]:
                for x in r["tool_results"]:
                    print("  工具返回：", x)
        print("  最终回答：", rec["final"].replace("\n", " ")[:200])
        out.append(rec)

    path = os.path.join(HERE, "轨迹记录.json")
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path, encoding="utf-8"))
        except Exception:
            old = []
    keep = [x for x in old if x.get("question") not in {r["question"] for r in out}]
    json.dump(keep + out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n已写入", path)


if __name__ == "__main__":
    main()
