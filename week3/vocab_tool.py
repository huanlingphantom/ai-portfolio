# W3 生词表 CSV -> 自动生成练习题（造句 + 挖空填空）
# 运行：python vocab_tool.py          默认取 HSK4
#       python vocab_tool.py 3        可选：指定 HSK 等级（3/4/5/6…）
#
# 约定（与 README 一致）：
#   1) 数据一律用 weekpath.data_path() 定位，所以"从任何目录运行"都找得到 data/；
#   2) 产物一律用 weekpath.root_path() 落回代码包根目录，不随当前目录乱跑。
# 只用四个语法点：变量 / if / def / for —— 不引入类、异常处理、推导式，方便逐行读懂。
#
# 填空题形式（挖空）：把例句里的目标词挖掉，答案放括号里
#   例：我今天请假了，在家＿＿。（休息）        ← 空格数 = 目标词字数
#   句源：data/例句库.csv（老师可自行加行扩充）
import os
import csv
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  统一解析 data/ 路径，换目录也不会找不到文件

DATA = weekpath.data_path("生词表.csv")
EXAMPLES = weekpath.data_path("例句库.csv")
LINE = "=" * 46
BLANK = "＿"          # 全角下划线：一格 = 一个字，学生一眼知道要填几个字


def load_words(path=DATA):
    """读生词表 CSV：每行一个字典，整表存成列表。

    用 utf-8-sig 读：Excel 另存为 CSV 时会加 BOM，普通 utf-8 会把首列名读成"\\ufeff词汇"。
    """
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_examples(path=EXAMPLES):
    """读例句库 CSV（句子 / 目标词 / 来源），作为挖空填空题的句源。"""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def filter_by_level(words, level="4"):
    """挑出指定 HSK 等级的词汇（for + if 逐个判断，不用推导式）。"""
    result = []
    for w in words:
        if str(w["HSK等级"]) == str(level):
            result.append(w)
    return result


def count_by_pos(words):
    """词性分布统计：{词性: 个数}。"""
    d = {}
    for w in words:
        d[w["词性"]] = d.get(w["词性"], 0) + 1
    return d


def group_by_pos(words):
    """扩展功能 1：按词性分组，{词性: [词条, ...]}。

    分组顺序 = 词条在表里第一次出现的顺序，不额外排序，结果稳定可复现。
    """
    groups = {}
    for w in words:
        pos = w["词性"]
        if pos not in groups:      # 第一次遇到这个词性就开一个新格子
            groups[pos] = []
        groups[pos].append(w)
    return groups


def find_example(word, examples):
    """在例句库里找第一条命中该词的例句，找不到返回 None。"""
    for e in examples:
        if e["目标词"] == word:
            return e
    return None


def make_cloze(sentence, word):
    """把句子里的目标词挖掉：换成 N 个空格，答案用括号跟在句子后面。"""
    blank = BLANK * len(word)
    return sentence.replace(word, blank) + "（" + word + "）"


def sentence_lines(words):
    """造句练习的正文行：外层按词性分组，内层逐个出题。"""
    lines = []
    lines.append("一、造句练习（按词性分组）")
    groups = group_by_pos(words)
    for pos in groups:
        lines.append("")
        lines.append("【%s】共 %d 个" % (pos, len(groups[pos])))
        n = 0
        for w in groups[pos]:
            n = n + 1
            lines.append("  %d. 用“%s”造一个句子。（%s · HSK%s）"
                         % (n, w["词汇"], w["词性"], w["HSK等级"]))
    return lines


def cloze_lines(words, examples):
    """扩展功能 2：挖空填空题。返回 (正文行, 没有例句的词)。"""
    lines = []
    missing = []
    lines.append("二、填空题（把括号里的词填进空格）")
    lines.append("")
    n = 0
    for w in words:
        e = find_example(w["词汇"], examples)
        if e is None:                       # 例句库里没有这个词，先记下来
            missing.append(w["词汇"])
        else:
            n = n + 1
            lines.append("  %d. %s" % (n, make_cloze(e["句子"], w["词汇"])))
    if n == 0:
        lines.append("  （例句库里暂无这些词的例句，请在 data/例句库.csv 里补行）")
    return lines, missing


def write_lines(lines, path):
    """把一组文本行写进文件，统一 utf-8。"""
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def gen_exercises(words, examples, level, out=None):
    """把造句 + 挖空填空拼成一份《练习.txt》，统一落到代码包根目录。

    产物落在根目录而不是当前目录：否则"从哪个目录运行"决定了文件落在哪，
    与 README 的"任意目录运行"承诺冲突，且散落的产物 .gitignore 拦不住。
    """
    out = out or weekpath.root_path("练习.txt")
    lines = []
    lines.append("华文小助手 · 生词练习（自动生成）")
    lines.append("筛选等级：HSK%s　　词条数：%d　　句源：data/例句库.csv" % (level, len(words)))
    lines.append(LINE)
    for line in sentence_lines(words):
        lines.append(line)
    lines.append("")
    lines.append(LINE)
    blank, missing = cloze_lines(words, examples)
    for line in blank:
        lines.append(line)
    if len(missing) > 0:
        lines.append("")
        lines.append("（例句库缺 %d 个词的例句，未出题：%s）" % (len(missing), "、".join(missing)))
    write_lines(lines, out)
    return out


if __name__ == "__main__":
    level = "4"
    if len(sys.argv) > 1:          # 命令行给了等级就用它，否则用默认值
        level = sys.argv[1]

    words = load_words()
    examples = load_examples()
    picked = filter_by_level(words, level)

    print("总词汇 %d 个，其中 HSK%s 词汇 %d 个，词性分布：%s"
          % (len(words), level, len(picked), count_by_pos(picked)))
    print("例句库共 %d 条" % len(examples))

    if len(picked) == 0:           # 该等级没有词时给出可操作提示，不生成空文件
        print("表里没有 HSK%s 的词汇，换个等级试试，例如：python vocab_tool.py 3" % level)
    else:
        out = gen_exercises(picked, examples, level)
        print("已生成：%s" % out)

        groups = group_by_pos(picked)
        for pos in groups:
            names = ""
            for w in groups[pos]:
                if names != "":                    # 第一个词前面不加顿号
                    names = names + "、"
                names = names + w["词汇"]
            print("  %s %d 个：%s" % (pos, len(groups[pos]), names))
