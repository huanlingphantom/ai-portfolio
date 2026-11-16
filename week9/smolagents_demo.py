# W9 加分选做 · smolagents 最小示例（A 路径：跑通 + 换成本地 HSK 工具）
# 依赖：pip install smolagents openai python-dotenv
# 说明：API 说明见 https://huggingface.co/docs/smolagents ；包内 LICENSE 为 Apache-2.0
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402

weekpath.load_env()

from smolagents import OpenAIModel, ToolCallingAgent, tool  # noqa: E402

VOCAB = weekpath.data_path("生词表.csv")


@tool
def hsk_level(word: str) -> str:
    """查课程生词表里词语的 HSK 等级。

    Args:
        word: 要查询的汉字或词语
    """
    with open(VOCAB, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["词汇"].strip() == word.strip():
                return "%s 是 %s 级" % (word, row["HSK等级"])
    return "未找到 %s" % word


@tool
def word_count(text: str) -> str:
    """统计一段中文文本的去重词数（按生词表匹配），用于估课文难度。

    Args:
        text: 要统计的中文文本
    """
    known = set()
    with open(VOCAB, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            known.add(row["词汇"].strip())
    hits = [w for w in known if w and w in text]
    return "命中生词表 %d 个：%s" % (len(hits), "、".join(sorted(hits)))


def main():
    model = OpenAIModel(
        model_id=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_base="https://api.deepseek.com/v1",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    )
    agent = ToolCallingAgent(tools=[hsk_level, word_count], model=model, max_steps=3)
    q = sys.argv[1] if len(sys.argv) > 1 else "'把'字是 HSK 几级词汇？顺便看看「愚公移山」里能命中几个生词。"
    print("问：", q)
    print("答：", agent.run(q))


if __name__ == "__main__":
    main()
