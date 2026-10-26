# W5 本地 vs 云端 对比实验（讲义第六节）
#
# 用途：同一组学科问题，先问本机 Ollama，再问云端，记录 速度 / 质量 / 隐私。
# 只跑本地（默认）：
#     python compare_local_vs_cloud.py
# 指定模型（如 4b 量级对比，讲义作业 2）：
#     python compare_local_vs_cloud.py --model qwen3:4b
# 连云端一起跑（需先在终端执行 ollama signin，或设置 OLLAMA_API_KEY）：
#     python compare_local_vs_cloud.py --cloud gemma4:cloud
#
# 依赖：pip install requests

import argparse
import json
import os
import sys
import time

import requests

LOCAL = "http://localhost:11434"
CLOUD = "https://ollama.com"

# 5 个学科问题：都取自国际中文教学的真实场景，且都能人工判断对错
QUESTIONS = [
    "给《愚公移山》出 3 道 HSK4 阅读理解题，每题 4 个选项，并给出答案。",
    "解释「把字句」的构成条件，并举 3 个例句。",
    "把「教学目标：掌握把字句」扩写成一份 45 分钟教案的提纲。",
    "学生作文里写「我把一本书买了」，错在哪里？应该怎么改？",
    "用「愚公移山」这个成语的比喻义，造 2 个 HSK4 水平的句子。",
]


def new_session():
    """讲义第八节那个坑：机房/校园网常配系统代理，requests 会把 localhost 也送去代理，
    于是 connection refused。trust_env=False 让 requests 忽略环境里的 proxy 变量。"""
    s = requests.Session()
    s.trust_env = False
    return s


def chat(sess, base_url, model, question, timeout=120, api_key=None):
    """调 Ollama 的 /api/chat。返回 (回答文本, 统计dict)。"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    body = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "stream": False,
        # num_predict 相当于 max_tokens；本地不计费，但长度仍受它限制
        "options": {"num_predict": 512, "temperature": 0.7},
    }
    t0 = time.time()
    r = sess.post(base_url + "/api/chat", json=body, headers=headers, timeout=timeout)
    wall = time.time() - t0
    r.raise_for_status()
    d = r.json()
    text = (d.get("message") or {}).get("content", "")
    return text, {
        "wall_s": wall,
        "prompt_tokens": d.get("prompt_eval_count", 0),
        "output_tokens": d.get("eval_count", 0),
        "eval_ns": d.get("eval_duration", 0),
        "total_ns": d.get("total_duration", 0),
    }


def tok_per_s(st):
    """生成阶段的真实速度：eval_count / eval_duration（纳秒）。"""
    if st["eval_ns"] and st["output_tokens"]:
        return st["output_tokens"] / (st["eval_ns"] / 1e9)
    return 0.0


def check_service(sess):
    try:
        r = sess.get(LOCAL + "/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except requests.exceptions.ConnectionError:
        print("连不上本机 Ollama（connection refused）。对照讲义第九节排错表：")
        print("  1) 另开一个终端跑 ollama serve")
        print("  2) 确认任务栏有羊驼图标")
        print("  3) curl http://localhost:11434/api/tags 验证")
        sys.exit(2)
    except Exception as e:
        print("探测服务失败：%s" % e)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:0.5b", help="本地模型名")
    ap.add_argument("--cloud", default="", help="云端模型名，如 gemma4:cloud；留空则只跑本地")
    ap.add_argument("--cloud-direct", action="store_true",
                    help="直连 https://ollama.com（需要 OLLAMA_API_KEY）；默认走本机服务代理，"
                         "用 ollama signin 换来的密钥，不需要 API key")
    ap.add_argument("--out", default="week05_对比结果.json", help="原始结果落盘文件名")
    args = ap.parse_args()

    sess = new_session()
    tags = check_service(sess)
    print("本机已装模型：%s" % (", ".join(tags) if tags else "（无，先 ollama pull）"))
    if args.model not in tags and args.model + ":latest" not in tags:
        print("警告：%s 不在已装列表里，Ollama 可能会先自动拉取。" % args.model)

    api_key = os.getenv("OLLAMA_API_KEY")
    # 0.40 之后，云端模型的正确用法是"发给本机服务"：本机服务拿 ollama signin 换来的密钥去签名，
    # 再转发到 ollama.com。直连 https://ollama.com/api/chat 只在你有 API key 时才通（否则 401）。
    cloud_base = CLOUD if args.cloud_direct else LOCAL
    if args.cloud:
        print("云端模型 %s 走：%s" % (args.cloud, cloud_base))
        if args.cloud_direct and not api_key:
            print("提示：--cloud-direct 需要 OLLAMA_API_KEY；没有的话去掉这个参数。")

    results = []
    for i, q in enumerate(QUESTIONS, 1):
        print("\n" + "=" * 70)
        print("第 %d 题：%s" % (i, q))
        row = {"n": i, "question": q}

        try:
            text, st = chat(sess, LOCAL, args.model, q)
            row["local"] = st
            row["local_text"] = text
            print("\n--- 本地 %s（墙钟 %.2fs，%d tok，%.1f tok/s）---"
                  % (args.model, st["wall_s"], st["output_tokens"], tok_per_s(st)))
            print(text.strip() or "（空回答）")
        except Exception as e:
            row["local_error"] = str(e)
            print("\n本地调用失败：%s" % e)

        if args.cloud:
            try:
                text, st = chat(sess, cloud_base, args.cloud, q, timeout=180, api_key=api_key)
                row["cloud"] = st
                row["cloud_text"] = text
                print("\n--- 云端 %s（墙钟 %.2fs，%d tok，%.1f tok/s）---"
                      % (args.cloud, st["wall_s"], st["output_tokens"], tok_per_s(st)))
                print(text.strip() or "（空回答）")
            except Exception as e:
                row["cloud_error"] = str(e)
                print("\n云端调用失败：%s" % e)

        results.append(row)

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(path, "w", encoding="utf-8") as f:      # 中文 Windows 上必须指定编码
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 打印可直接粘进 ollama_notes.md 的表格骨架（速度列已填，质量列留给你判断）
    print("\n\n" + "=" * 70)
    print("下表可直接粘进 ollama_notes.md，质量与隐私列请自己填：\n")
    head = "| # | 学科问题 | 本地速度 | 本地质量 | 云端速度 | 云端质量 | 隐私判断 | 该用哪个 |"
    print(head)
    print("|---|---------|---------|---------|---------|---------|---------|---------|")
    for r in results:
        q = r["question"]
        if len(q) > 22:
            q = q[:22] + "…"
        ls = "%.2fs / %.0f tok/s" % (r["local"]["wall_s"], tok_per_s(r["local"])) if "local" in r else "失败"
        cs = "%.2fs / %.0f tok/s" % (r["cloud"]["wall_s"], tok_per_s(r["cloud"])) if "cloud" in r else "—"
        print("| %d | %s | %s |  | %s |  |  |  |" % (r["n"], q, ls, cs))
    print("\n原始结果已写入：%s" % path)


if __name__ == "__main__":
    main()
