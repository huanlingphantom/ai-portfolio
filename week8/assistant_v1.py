# W8 阶段项目一：学科智能问答助手 v1.0
# 组装 = W2 提示词库 + W6 双引擎 + W7 知识库问答
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  让跨周 import 生效（llm 在 week06、rag_qa 在 week07）

weekpath.load_env()

from llm import LLM  # noqa: E402
from rag_qa import retrieve, build_prompt  # noqa: E402

llm = LLM()

SYSTEM_HINT = "你是国际中文教学助手，面向 HSK3–4 学习者，回答需给出依据。"


def answer(question, use_rag=True, prefer="local"):
    if use_rag:
        ctx = retrieve(question)
        prompt = SYSTEM_HINT + "\n" + build_prompt(question, ctx)
    else:
        prompt = SYSTEM_HINT + "\n" + question
    return llm.ask(prompt, prefer=prefer)


if __name__ == "__main__":
    for q in ["把字句的教学难点有哪些", "HSK4 词汇量要求是多少", "《愚公移山》可以设计什么课堂活动"]:
        print("Q:", q)
        try:
            print("A:", answer(q))
        except Exception as e:
            # 常见：Ollama 没启动 / 没 pull nomic-embed-text / 没配云端密钥
            print("A: [运行失败] %s" % e)
        print("-" * 40)

# 发布：
# git add . && git commit -m "W8: 助手 v1.0"
# git tag -a v1.0 -m "学科智能问答助手 v1.0" && git push origin main --tags
