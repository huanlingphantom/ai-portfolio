# W6 双引擎封装 —— 此后所有周统一经此调用
# 依赖：pip install openai requests python-dotenv
#
# 本文件相对讲义骨架的三处增强（都写在注释里，方便对照）：
#   1. 本地请求 trust_env=False —— 本机有系统代理（HTTP_PROXY=127.0.0.1:xxxxx），
#      requests 默认会把 localhost 也送去代理，结果是"Ollama 明明在跑却连不上"。
#   2. 每次调用打印耗时与费用估算（课后作业 1 的第三项）。
#      选它的理由：W4 已经在按 token 算钱，W6 把两个引擎放进同一个入口后，
#      "同一句话到底花多少钱、等多久"才有可比性；选"多轮对话"会让 ask() 的签名变复杂，
#      选"失败重试"会和 LLM 已有的回退逻辑打架——回退本身就是一种更彻底的容错。
#   3. LLM 记录 last_engine / last_stats，供边界测试脚本判断"这次到底谁答的"。
#      不靠 print 猜，证据更硬。
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import weekpath  # noqa: E402  跨周导入 + 加载 .env

    weekpath.load_env()
except ImportError:
    # 作品集仓库里只放了 week6/ 一个目录，没有根目录的 weekpath.py。
    # 这时退化成"只加载本目录的 .env"，保证 llm.py 单独拷出去也能跑。
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    except ImportError:
        pass

import requests  # noqa: E402
import openai  # noqa: E402

# DeepSeek 价格（元 / 百万 tokens）。高峰 = 周一至周五 9:00–12:00、14:00–18:00（北京时间），
# 其余时段按半价。数字来源：DeepSeek 官方价格页，2026-10 抓取。
PRICE = {
    "peak": {"in": 2.0, "out": 8.0},
    "offpeak": {"in": 1.0, "out": 4.0},
}


def is_peak(now=None):
    """判断当前是否处于 DeepSeek 的高峰时段。"""
    t = now or time.localtime()
    if t.tm_wday >= 5:            # 周六、周日全天半价
        return False
    hm = t.tm_hour * 60 + t.tm_min
    return (9 * 60 <= hm < 12 * 60) or (14 * 60 <= hm < 18 * 60)


class LocalEngine:
    """本地引擎（Ollama）：隐私任务优先、断网可用。"""

    def __init__(self, model=None):
        self.model = model or os.getenv("LOCAL_MODEL", "qwen2.5:0.5b")

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        # trust_env=False：忽略系统代理，保证 localhost 不被送进代理隧道
        s = requests.Session()
        s.trust_env = False
        r = s.post(
            "http://localhost:11434/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            },
            timeout=60,          # 首次装载模型可能要 30 秒，必须留超时，否则永久卡住
        )
        r.raise_for_status()     # 模型名写错会返回 404，让错误当场暴露
        data = r.json()
        self.last_stats = {
            "engine": "local",
            "model": self.model,
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0),
            "cost": 0.0,         # 本地不计费
        }
        return data["message"]["content"]


class APIEngine:
    """云端引擎：复杂任务、本地失败兜底。

    注意：openai.OpenAI(...) 在 api_key 为 None 时会直接抛错。
    若在这里（构造 LLM 时）就建客户端，那么没配密钥的同学连"纯本地"模式都跑不起来。
    因此改为**按需创建**：第一次真正调用云端时才建客户端。
    """

    def __init__(self, base_url=None, model=None):
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = model or os.getenv("API_MODEL", "deepseek-chat")
        self._client = None

    def _get_client(self):
        if self._client is None:
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                raise RuntimeError(
                    "未配置 DEEPSEEK_API_KEY：请复制 .env.example 为 .env 并填入密钥，"
                    "或在系统环境变量中设置。纯本地模式请调用 ask(..., prefer='local')。"
                )
            self._client = openai.OpenAI(base_url=self.base_url, api_key=key)
        return self._client

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        r = self._get_client().chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = getattr(r, "usage", None)
        p_tok = getattr(usage, "prompt_tokens", 0) or 0
        c_tok = getattr(usage, "completion_tokens", 0) or 0
        price = PRICE["peak"] if is_peak() else PRICE["offpeak"]
        self.last_stats = {
            "engine": "api",
            "model": self.model,
            "prompt_tokens": p_tok,
            "output_tokens": c_tok,
            "cost": (p_tok * price["in"] + c_tok * price["out"]) / 1_000_000,
        }
        return r.choices[0].message.content


class LLM:
    """统一入口：ask(prompt)。本地优先、云端兜底、**双向**异常自动切换。

    prefer='local'：本地挂了自动切云端；
    prefer='api'  ：云端挂了（断网/超时/未配密钥）自动切本地。
    两侧对称，任何一边失败都不会让程序直接崩——这正是"双引擎"存在的意义。
    """

    def __init__(self, local_model=None, verbose=True):
        self.local = LocalEngine(local_model)
        self.api = APIEngine()
        self.verbose = verbose
        self.last_engine = None      # "local" / "api"：这次是谁答的
        self.last_stats = {}
        self.last_elapsed = 0.0
        self.last_fallback = None    # 回退原因（None 表示没回退）

    def ask(self, prompt, prefer="local", **kw):
        if prefer == "local":
            first, second, tag = self.local, self.api, "本地失败，自动切换云端"
        else:
            first, second, tag = self.api, self.local, "云端失败，自动切换本地"

        self.last_fallback = None
        t0 = time.time()
        try:
            text = first.ask(prompt, **kw)
        except Exception as e:
            # 三纪律之一：不吞异常、必须打印原因。这行日志就是边界测试的证据。
            print("[%s] %s" % (tag, e))
            self.last_fallback = "%s: %s" % (type(e).__name__, e)
            text = second.ask(prompt, **kw)     # 三纪律之二：返回真实结果，不返回空串

        self.last_elapsed = time.time() - t0
        self.last_stats = getattr(first if self.last_fallback is None else second, "last_stats", {})
        self.last_engine = self.last_stats.get("engine")
        if self.verbose:
            print(
                "[耗时/费用] 实际引擎=%(engine)s 模型=%(model)s "
                "用时 %(elapsed).2fs 输出 %(out)d tokens 费用 %(cost).6f 元"
                % {
                    "engine": self.last_stats.get("engine", "?"),
                    "model": self.last_stats.get("model", "?"),
                    "elapsed": self.last_elapsed,
                    "out": self.last_stats.get("output_tokens", 0),
                    "cost": self.last_stats.get("cost", 0.0),
                }
            )
        return text


if __name__ == "__main__":
    llm = LLM()
    print(llm.ask("给《愚公移山》出一道 HSK4 阅读理解题", prefer="local"))
