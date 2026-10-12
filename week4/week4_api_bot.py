# W4 命令行学科问答机器人（API 版）
# 依赖：pip install openai python-dotenv
#
# 运行：
#   python week4_api_bot.py "把字句的教学难点有哪些"
#   python week4_api_bot.py "用一句话说明什么是把字句" --temperature 0.0 --max_tokens 15
#   python week4_api_bot.py "把字句的教学难点有哪些" --repeat 10      # 连问 10 次并汇总费用
#   python week4_api_bot.py --help
#
# 在讲义原版基础上只加了三件事（不加参数时行为与原版完全一致）：
#   1) 命令行可调 --temperature / --max_tokens / --model  → 支撑第六节「第 3 步 参数体验」
#   2) 每次调用打印 token 用量与估算费用                    → 支撑第六节「第 4 步 算这次花了多少钱」
#   3) --repeat N 连问 N 次并汇总                           → 支撑「跑十次的费用」
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  加载 .env + 解析路径

weekpath.load_env()

import openai  # noqa: E402

BASE_URL = "https://api.deepseek.com/v1"   # 通义：https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL = "deepseek-chat"                    # 通义：qwen-plus（模型名踩坑见 W4作业实录.md）

# 单价：元 / 百万 tokens。抄自 DeepSeek 官方价格页（2026-10-12 抄录），平台调价时只改这里。
# 空闲时段单价 = 高峰时段的一半；高峰 = 北京时间周一至周五 9:00-12:00、14:00-18:00（不含法定节假日）
PRICE = {
    "hit":  {"peak": 0.04, "off": 0.02},   # 输入 · 缓存命中
    "miss": {"peak": 2.00, "off": 1.00},   # 输入 · 缓存未命中
    "out":  {"peak": 8.00, "off": 4.00},   # 输出
}

_client = None


def get_client():
    """按需创建客户端：这样"没配密钥"能在 __main__ 里被友好提示，
    而不是在 import 阶段就抛出看不懂的 OpenAIError。"""
    global _client
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY")
        _client = openai.OpenAI(base_url=BASE_URL, api_key=key,
                                timeout=60.0, max_retries=1)
    return _client


def is_peak(ts=None):
    """现在是不是高峰时段（按本机北京时间判断）。周六周日整天都算空闲时段。"""
    t = time.localtime(ts) if ts else time.localtime()
    if t.tm_wday >= 5:                              # 5=周六 6=周日
        return False
    hm = t.tm_hour * 60 + t.tm_min
    return (9 * 60 <= hm < 12 * 60) or (14 * 60 <= hm < 18 * 60)


def usage_of(resp):
    """把响应里的用量拆成 输入/命中/未命中/输出 四个数，缺字段就退回 0 / 推算。"""
    u = resp.usage
    prompt = getattr(u, "prompt_tokens", 0) or 0
    out = getattr(u, "completion_tokens", 0) or 0
    hit = getattr(u, "prompt_cache_hit_tokens", None)
    miss = getattr(u, "prompt_cache_miss_tokens", None)
    if hit is None:                                  # 非 DeepSeek 平台可能没有这两个字段
        hit = 0
        miss = prompt
    if miss is None:
        miss = max(prompt - hit, 0)
    return {"prompt": prompt, "hit": hit, "miss": miss, "out": out}


def cost_of(tok, peak=None):
    """费用 = 命中×命中价 + 未命中×未命中价 + 输出×输出价（单位：元）。"""
    k = "peak" if (is_peak() if peak is None else peak) else "off"
    return (tok["hit"] * PRICE["hit"][k]
            + tok["miss"] * PRICE["miss"][k]
            + tok["out"] * PRICE["out"][k]) / 1_000_000


def ask(question, temperature=0.7, max_tokens=800, model=None):
    """问一次。返回 (回答文本, 用量 dict, 耗时秒)。"""
    t0 = time.time()
    r = get_client().chat.completions.create(
        model=model or MODEL,
        messages=[{"role": "user", "content": question}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return r.choices[0].message.content, usage_of(r), time.time() - t0


def friendly_error(e):
    """把 SDK 抛出的异常翻译成人话（对照讲义第八节「常见报错速查」）。"""
    if isinstance(e, openai.AuthenticationError):
        return "401 认证失败：密钥错误 / 已失效 / 首尾带了空格。\n" \
               "  处理：重新复制密钥，注意 .env 里 KEY= 后面不要有空格和引号。"
    if isinstance(e, openai.RateLimitError):
        return "429 限流或余额不足。\n  处理：充值；或临时改用课堂共享密钥；或降低并发后重试。"
    if isinstance(e, openai.APITimeoutError):
        return "APITimeoutError 请求超时：网络不通或答案太长。\n" \
               "  处理：换网络；调大 timeout；把 max_tokens 调小。"
    if isinstance(e, openai.APIConnectionError):
        return "APIConnectionError 域名不可达（校园网常见）。\n" \
               "  处理：换手机热点验证是否网络策略问题；或改用 Gitee 附录里的替代平台。"
    if isinstance(e, openai.APIStatusError):
        return "HTTP %s 服务端拒绝：%s\n  处理：对照讲义第八节报错速查表。" % (
            e.status_code, type(e).__name__)
    return "%s：%s" % (type(e).__name__, e)


def log_line(question, answer, tok, cost, seconds, args, model):
    """一次问答的完整留痕：一行元信息 + Q/A。追加写入代码包根目录 chat_log.txt。"""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    head = ("[%s] model=%s temperature=%s max_tokens=%s 用时=%.1fs "
            "输入=%d(命中%d/未命中%d) 输出=%d 费用=￥%.6f"
            % (stamp, model, args.temperature, args.max_tokens, seconds,
               tok["prompt"], tok["hit"], tok["miss"], tok["out"], cost))
    path = weekpath.root_path("chat_log.txt")
    with open(path, "a", encoding="utf-8") as f:     # 必须带 encoding，否则中文 Windows 上报 UnicodeEncodeError
        f.write(head + "\nQ: %s\nA: %s\n\n" % (question, answer))


def build_parser():
    p = argparse.ArgumentParser(description="命令行学科问答机器人（W4）")
    p.add_argument("question", nargs="*", default=[],
                   help="要问的问题；不填则用示例问题")
    p.add_argument("-t", "--temperature", type=float, default=0.7,
                   help="发散度 0~2：0 最稳，1.5 开始离谱（默认 0.7）")
    p.add_argument("-m", "--max_tokens", type=int, default=800,
                   help="输出上限，调小可看硬截断（默认 800）")
    p.add_argument("--model", default=MODEL, help="模型名（默认 %s）" % MODEL)
    p.add_argument("-n", "--repeat", type=int, default=1,
                   help="同一问题重复问几次，用于统计费用（默认 1）")
    p.add_argument("--no-log", action="store_true", help="本次不写 chat_log.txt")
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("错误：未设置 DEEPSEEK_API_KEY。")
        print("  处理：复制 .env.example 为 .env 并填入密钥，重启终端后重试。")
        sys.exit(1)

    q = " ".join(args.question) or "把字句的教学难点有哪些"
    n = max(args.repeat, 1)

    total = {"prompt": 0, "hit": 0, "miss": 0, "out": 0}
    total_cost = 0.0
    total_sec = 0.0

    for i in range(n):
        if n > 1:
            print("—— 第 %d/%d 次 ——" % (i + 1, n))
        try:
            ans, tok, sec = ask(q, args.temperature, args.max_tokens, args.model)
        except openai.OpenAIError as e:              # 只捕 SDK 自己的异常，别的照样崩给我看
            print("错误：" + friendly_error(e))
            sys.exit(1)
        except RuntimeError as e:
            print("错误：" + str(e))
            sys.exit(1)

        cost = cost_of(tok)
        total["prompt"] += tok["prompt"]
        total["hit"] += tok["hit"]
        total["miss"] += tok["miss"]
        total["out"] += tok["out"]
        total_cost += cost
        total_sec += sec

        print(ans)                                   # 终端打印
        print("\n[用量] 输入 %d（命中 %d / 未命中 %d）+ 输出 %d = %d tokens"
              " | 用时 %.1fs | 本次费用 ￥%.6f"
              % (tok["prompt"], tok["hit"], tok["miss"], tok["out"],
                 tok["prompt"] + tok["out"], sec, cost))
        if n > 1:
            print()

        if not args.no_log:
            log_line(q, ans, tok, cost, sec, args, args.model)

    if n > 1:
        print("=" * 56)
        print("共 %d 次：输入 %d（命中 %d / 未命中 %d）+ 输出 %d = %d tokens"
              % (n, total["prompt"], total["hit"], total["miss"], total["out"],
                 total["prompt"] + total["out"]))
        print("总用时 %.1fs，平均每次 %.1fs" % (total_sec, total_sec / n))
        print("总费用 ￥%.6f（约 ￥%.4f），平均每次 ￥%.6f"
              % (total_cost, total_cost, total_cost / n))
        print("计价时段：%s（单价表基于 DeepSeek 官方价格页 2026-10-12）"
              % ("高峰" if is_peak() else "空闲"))
