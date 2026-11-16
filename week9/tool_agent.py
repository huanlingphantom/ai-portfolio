# W9 手写最小工具调用循环（不用框架）
# 依赖：pip install openai python-dotenv
import os
import csv
import sys
import ast
import json
import re
import operator
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  数据路径 + 加载 .env

weekpath.load_env()

import openai  # noqa: E402

VOCAB = weekpath.data_path("生词表.csv")

# 默认走 DeepSeek 云端；教师机演示可通过环境变量切到本机 Ollama
# （OpenAI 兼容端点），例如 DEEPSEEK_BASE_URL=http://localhost:11434/v1
# DEEPSEEK_MODEL=llama3.1:8b-local。不设置时行为与云端口径完全一致。
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

_client = None


def get_client():
    global _client
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请先在 .env 中填写")
        base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        _client = openai.OpenAI(base_url=base, api_key=key)
    return _client


def get_time():
    return str(datetime.datetime.now())


# ---- 安全计算：白名单 AST，绝不使用裸 eval ----
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("只允许数字与 + - * / ** % 运算")


def calc(expr):
    """教学演示用：只做四则运算。为什么不用 eval？
    因为 eval 会执行任意 Python 代码，是典型的安全反模式（本课程伦理红线之一）。"""
    try:
        return str(_eval_node(ast.parse(str(expr), mode="eval")))
    except ZeroDivisionError:
        return "错误：除数为 0"
    except Exception as e:
        return "拒绝计算：%s" % e


def hsk_level(word):
    with open(VOCAB, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["词汇"].strip() == str(word).strip():
                return "%s 是 %s 级" % (word, row["HSK等级"])
    return "未找到 %s" % word


# ---- 第 4 个工具：课文难度评估（作业 2） ----
_CN_NUM = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7"}


def _norm_level(x):
    """'HSK4' / 'hsk 4' / '四级' / 4 → 4；认不出返回 None。"""
    s = str(x).strip().upper()
    for cn, num in _CN_NUM.items():
        s = s.replace(cn, num)
    s = s.replace("HSK", "").replace("级", "").strip()
    return int(s) if s.isdigit() and 1 <= int(s) <= 9 else None


def _load_vocab(path=None):
    """读词表 → {词: 等级}。换成完整 HSK 词表（同表头）即可评估全文难度。"""
    vocab = {}
    with open(path or VOCAB, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            w = (row.get("词汇") or "").strip()
            lv = (row.get("HSK等级") or "").strip()
            if w and lv.isdigit():
                vocab[w] = int(lv)
    return vocab


def _is_hanzi(ch):
    return "\u4e00" <= ch <= "\u9fff"


def _read_data_text(name):
    """按文件名读 data/ 下的课文；只取 basename，挡掉 ../ 路径穿越。"""
    path = weekpath.data_path(os.path.basename(str(name).strip()))
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def text_difficulty(text, target_level, file=""):
    """评估一段课文对某个目标等级是否合适：给出生词覆盖率与超纲词清单。

    text：课文正文；留空则读 data/ 下的 file（如 愚公移山.txt）
    target_level：目标等级，1-6 的整数或 'HSK4' / '四级'
    """
    level = _norm_level(target_level)
    if level is None:
        return "目标等级无法识别：%r（请给 1-6 或 HSK4 这样的写法）" % (target_level,)

    body = str(text or "").strip()
    # 模型常把文件名塞进第一个参数（实测给了 "data/愚公移山"）：短、无换行、能对上文件就当文件读
    if not file and 0 < len(body) <= 30 and "\n" not in body:
        guess = body.replace("\\", "/").split("/")[-1]
        if not guess.endswith(".txt"):
            guess += ".txt"
        loaded = _read_data_text(guess)
        if loaded is not None:
            body, file = loaded, guess
    if not body and file:
        loaded = _read_data_text(file)
        if loaded is None:
            return "data/ 下没有 %s" % os.path.basename(str(file))
        body = loaded

    total = sum(1 for c in body if _is_hanzi(c))
    if total == 0:
        return "没有可评估的汉字：请粘贴课文正文，或给 data/ 下的文件名"

    vocab = _load_vocab()
    maxlen = max(len(w) for w in vocab)
    hits = {}          # 词 → 出现次数
    covered = 0        # 被词表命中的汉字数
    i = 0
    while i < len(body):
        if not _is_hanzi(body[i]):
            i += 1
            continue
        # 最大正向匹配：只在连续汉字内部匹配，不跨标点拼词
        for L in range(min(maxlen, len(body) - i), 0, -1):
            frag = body[i:i + L]
            if frag in vocab and all(_is_hanzi(c) for c in frag):
                hits[frag] = hits.get(frag, 0) + 1
                covered += L
                i += L
                break
        else:
            i += 1

    over = sorted(((w, vocab[w], c) for w, c in hits.items() if vocab[w] > level),
                  key=lambda x: (-x[1], -x[2]))
    parts = ["%s(%d级)×%d" % (w, lv, c) for w, lv, c in over]
    all_hits = sorted(hits.items(), key=lambda x: (-x[1], x[0]))
    hit_txt = "、".join("%s(%d级)×%d" % (w, vocab[w], c) for w, c in all_hits)

    lines = [
        "目标 HSK%d｜汉字 %d 个｜词表 %d 条" % (level, total, len(vocab)),
        "生词复现：%d/%d 条（%.0f%%）—— %s" % (
            len(hits), len(vocab), 100.0 * len(hits) / len(vocab), hit_txt or "无"),
        "文本覆盖率：%.1f%%（%d/%d 字命中词表）" % (100.0 * covered / total, covered, total),
        "超纲词（>%d 级）：%s" % (level, "、".join(parts) if parts else "无"),
    ]
    if total > covered:
        lines.append("表外汉字 %d 个（%.1f%%，词表未收录，需人工判断）"
                     % (total - covered, 100.0 * (total - covered) / total))
    return "\n".join(lines)


TOOLS = {"get_time": get_time, "calc": calc, "hsk_level": hsk_level,
         "text_difficulty": text_difficulty}

SYS = ("你是国际中文助教。可用工具只有这 4 个：get_time（查当前时间，无参数）、"
       "calc（四则运算，如 calc('35*24')）、hsk_level（查生词 HSK 等级，如 hsk_level('把')）、"
       "text_difficulty（评估课文难度，参数为课文正文与目标等级，"
       "如 text_difficulty('北山有位叫愚公的老人……', 'HSK4')；正文太长时可只给 data/ 下的文件名）。"
       '如需调用，只输出一行 JSON，格式：{"tool": "工具名", "args": [参数…]}；'
       "键名只能是 tool 和 args，不要写成 name/arguments；args 必须是列表，多个参数按顺序放。"
       "一次只调用一个工具，绝不编造不存在的工具名；无需工具时直接回答。")


def _as_call(obj):
    """把模型给的对象统一成 {"tool": 名, "args": 列表}；认不出返回 None。

    作业 1 的补丁：探针实测模型会混用 OpenAI 的 {"name":..., "arguments":{...}}
    （原版只认 tool/args，于是这坨 JSON 被当成"最终回答"直接返回给用户）。"""
    if not isinstance(obj, dict):
        return None
    name = obj.get("tool", obj.get("name"))
    args = obj.get("args", obj.get("arguments", obj.get("parameters")))
    inner = obj.get("function")
    if inner is None and isinstance(name, dict):
        inner = name                             # {"name": {"name":..., "arguments":...}}
    if isinstance(inner, dict):                  # {"function": {"name":..., "arguments":...}}
        name = inner.get("name")
        args = inner.get("arguments", inner.get("args", args))
    if not isinstance(name, str) or not name.strip():
        return None
    if args is None:
        args = []
    if isinstance(args, dict) and len(args) == 1:     # {"expr": "35*24"} → ["35*24"]
        args = list(args.values())
    elif isinstance(args, (str, int, float)):          # "35*24" → ["35*24"]
        args = [args]
    return {"tool": name.strip(), "args": args}


def parse_calls(txt):
    """容错解析：剥掉 ```json 围栏与前后客套话，返回全部工具调用（0/1/多个）。

    模型不一定老实输出一个 JSON：可能带围栏、可能一段自然语言里夹着 JSON、
    也可能把多个工具调用并列输出成多行、还可能用 name/arguments 的键名——
    这里全部兜住，并统一成 {"tool":..., "args": [...]}。"""
    s = (txt or "").strip()
    s = s.replace("```json", "").replace("```", "").strip()
    try:
        call = _as_call(json.loads(s))
        return [call] if call else []
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)  # re.S：跨行也能匹配到 JSON 块
        if m:
            try:
                call = _as_call(json.loads(m.group()))
                if call:
                    return [call]
            except Exception:
                pass
        # 多个工具调用并列输出（小模型常态）：逐块全部解析，一轮依次执行
        calls = []
        for blk in re.findall(r"\{[^{}]*\}", s):
            try:
                call = _as_call(json.loads(blk))
            except Exception:
                continue
            if call:
                calls.append(call)
        return calls


def run(user_msg, max_calls=2):
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user_msg}]
    for _ in range(max_calls):
        txt = get_client().chat.completions.create(
            model=MODEL, messages=msgs).choices[0].message.content
        calls = [c for c in parse_calls(txt)
                 if isinstance(c.get("tool"), str) and c.get("tool") in TOOLS]
        if not calls:
            return txt                                   # 没调用工具 → 直接回答
        # 一轮内依次执行模型请求的全部工具，结果合并回喂
        results = []
        for call in calls:
            args = call.get("args") or []
            if not isinstance(args, list):
                results.append("工具参数格式错误：%r" % (args,))
                continue
            try:
                results.append("%s%r → %s" % (call["tool"], args, TOOLS[call["tool"]](*args)))
            except Exception as e:
                results.append("工具执行失败：%s" % e)
        msgs += [{"role": "assistant", "content": txt},
                 {"role": "user", "content": "工具返回：%s。请据此作答。" % "；".join(results)}]
    # 达到上限后强制收口，避免无限循环烧 token
    return get_client().chat.completions.create(
        model=MODEL, messages=msgs).choices[0].message.content


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "请依次查询两件事：1. '把'字的 HSK 等级是多少？2. 现在的时间是多少？"
    print("用户输入：", q)
    print("助手：", run(q))
