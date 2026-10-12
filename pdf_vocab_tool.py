# W3 扩展功能 1：读《国际中文教育中文水平等级标准（第二分册：词汇）》PDF 的文字
#                -> 按词性分类输出词组
#
# 运行：
#   python pdf_vocab_tool.py                                  默认 PDF + 四级词汇页
#   python pdf_vocab_tool.py <PDF路径>                         指定 PDF
#   python pdf_vocab_tool.py <PDF路径> 45 57                   指定页范围（PDF 页码）
#   python pdf_vocab_tool.py <PDF路径> 全部                     全书词汇表（约 20 分钟，只跑一次）
#
# 为什么需要 OCR：这份官方 PDF 是**扫描件**（302 页整页图片，没有文字层），
# 任何"直接读文字"的库都取不到内容，所以先把页面渲染成图、再用 OCR 认字。
# 依赖（W1–W3 的主线任务不需要，只有这个扩展要）：
#   pip install pymupdf rapidocr-onnxruntime
#
# 只用到四个语法点：变量 / if / def / for。
import os
import re
import csv
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402

PDF = weekpath.data_path("词汇表.pdf")                  # 把官方 PDF 放到 data/ 下
CACHE = weekpath.root_path("词汇表_OCR缓存.csv")         # OCR 结果缓存：存"原始行"，改规则不用重跑 OCR
OUT = weekpath.root_path("词组_按词性.txt")              # 主产物

SCALE = 3            # 渲染倍数：太小认不出字，太大又慢（3 倍 ≈ 5 秒/页）
TEXT_SCORE = 0.3     # 识别置信度门槛。默认 0.5 会把"词性"列的单字全丢掉，必须调低
ROW_TOL = 7 * SCALE  # 同一行的高度容差（像素）：小于它就算同一行

POS_TAIL = re.compile(r"([\u4e00-\u9fff、]{1,12})$")       # 行尾的中文（含顿号）= 词性
RE_NO = re.compile(r"^(\d{1,6})\s+(.*)$")                  # 行首序号
RE_WORD = re.compile(r"^([\u4e00-\u9fff·]{1,8})\s+(.*)$")   # 序号后面的词语
RE_SPLIT = re.compile(r"(?=(?<!\d)\d{1,6}\s+[\u4e00-\u9fff·])")   # 「数字 + 空格 + 汉字」的起点

# 官方印刷页码与 PDF 页码相差 12 页（印刷第 33 页 = PDF 第 45 页）。
# 四级词汇：印刷 33–45 -> PDF 45–57；全书词汇表：印刷 3–147 -> PDF 15–159。
OFFSET = 12
START, END = 33 + OFFSET, 45 + OFFSET


def missing_deps():
    """检查本扩展要用的第三方库，返回缺失的包名（供 pip install）。"""
    import importlib.util
    pairs = [("pymupdf", "fitz"), ("rapidocr-onnxruntime", "rapidocr_onnxruntime"),
             ("numpy", "numpy")]
    lack = []
    for pip_name, mod_name in pairs:
        if importlib.util.find_spec(mod_name) is None:
            lack.append(pip_name)
    return lack


def render_page(doc, pno, scale=SCALE):
    """把某页渲染成图片数组，交给 OCR。"""
    import numpy as np
    pix = doc[pno - 1].get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    return img


def ocr_page(engine, img):
    """OCR 一页，返回 [(y中心, x左边, 文本), ...]。"""
    result, _ = engine(img, text_score=TEXT_SCORE)
    items = []
    if result is None:
        return items
    for box, text, score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((sum(ys) / 4.0, min(xs), text))
    return items


def merge_rows(items):
    """同一条水平线上的文本框合并成一行文本：按 y 聚类，行内按 x 排序拼接。"""
    items = sorted(items)
    rows = []
    for y, x, text in items:
        if len(rows) == 0:
            rows.append([y, [(x, text)]])
        elif abs(y - rows[-1][0]) <= ROW_TOL:
            rows[-1][1].append((x, text))
        else:
            rows.append([y, [(x, text)]])
    lines = []
    for y, cells in rows:
        cells.sort()
        lines.append(" ".join(c[1] for c in cells))
    return lines


def split_row(row_text):
    """一页有两栏（四级页是四栏），同一条水平线上的词条会被拼进一行；
    按「数字 + 空格 + 汉字」的起点切开，就能还原成一条条独立词条。"""
    parts = []
    for seg in RE_SPLIT.split(row_text):
        if seg.strip() != "":
            parts.append(seg)
    return parts


def parse_entry(line):
    """把 '614 闪 shǎn 动' 这种行拆成 (序号, 词语, 拼音, 词性)；拆不出来返回 None。"""
    m = RE_NO.match(line.strip())
    if m is None:
        return None                          # 表头、页码等非词条行，跳过
    no = m.group(1)
    m2 = RE_WORD.match(m.group(2))
    if m2 is None:
        return None                          # 这一行没认出词语（OCR 漏字），跳过
    word = m2.group(1).rstrip("·")           # 词语不会以 · 结尾，去掉 OCR 带出来的尾巴
    tail = m2.group(2).strip().rstrip("·.．,，、")   # 去掉尾标点，免得"名·"这种认不出
    m3 = POS_TAIL.search(tail)
    if m3 is None:
        pos = ""                             # 有些词条本身不标词性（如"上个月""失业"）
        pinyin = tail
    else:
        pos = m3.group(1)
        pinyin = tail[:m3.start()].strip()
    return (no, word, pinyin, pos)


def parse_page(pno, lines):
    """把一页的 OCR 行解析成词条：[(页码, 序号, 词语, 拼音, 词性), ...]。"""
    rows = []
    for line in lines:
        for seg in split_row(line):
            entry = parse_entry(seg)
            if entry is None:
                continue
            no, word, pinyin, pos = entry
            rows.append((pno, int(no), word, pinyin, pos))
    return rows


def read_cache():
    """读缓存：{页码(字符串): [该页的 OCR 行, ...]}。"""
    cache = {}
    if not os.path.exists(CACHE):
        return cache
    with open(CACHE, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            page = r["页码"]
            if page not in cache:
                cache[page] = []
            cache[page].append(r["行"])
    return cache


def write_cache(cache):
    """写回缓存 CSV（页码, 行），按页码排好，便于人工翻看。"""
    pages = []
    for page in cache:
        pages.append(int(page))
    pages.sort()
    with open(CACHE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["页码", "行"])
        for pno in pages:
            for line in cache[str(pno)]:
                w.writerow([pno, line])


def group_by_pos(rows):
    """按词性分组：{词性: [词语, ...]}；没标词性的归入"未标注"。"""
    groups = {}
    for row in rows:
        pos = row[4]
        if pos == "":
            pos = "未标注"
        if pos not in groups:
            groups[pos] = []
        groups[pos].append(row[2])
    return groups


def write_report(rows, start, end, src_name, path=OUT):
    """主产物：按词性分类的词组。"""
    lines = []
    lines.append("《国际中文教育中文水平等级标准（第二分册：词汇）》 词组 · 按词性分类")
    if start > OFFSET:
        lines.append("来源：%s　PDF 第 %d–%d 页（印刷第 %d–%d 页）　词条数：%d"
                     % (src_name, start, end, start - OFFSET, end - OFFSET, len(rows)))
    else:
        lines.append("来源：%s　PDF 第 %d–%d 页　词条数：%d" % (src_name, start, end, len(rows)))
    lines.append("说明：词语由 OCR 提取；拼音声调可能有误，完整拼音只存在缓存 CSV 里")
    lines.append("=" * 46)
    groups = group_by_pos(rows)
    for pos in groups:
        words = groups[pos]
        lines.append("")
        lines.append("【%s】共 %d 个" % (pos, len(words)))
        line = "  "
        for i in range(len(words)):
            line = line + words[i] + "、"
            if (i + 1) % 10 == 0:            # 每 10 个词换一行，方便打印
                lines.append(line)
                line = "  "
        if line.strip() != "":
            lines.append(line)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return path, groups


if __name__ == "__main__":
    pdf_path = PDF
    start, end = START, END
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    if len(sys.argv) > 2:
        if sys.argv[2] in ("全部", "all", "ALL", "-"):
            start, end = 1, 100000            # 会被真实页数截断
        else:
            start = int(sys.argv[2])
            end = int(sys.argv[3])

    lack = missing_deps()
    if len(lack) > 0:
        print("缺依赖：%s" % "、".join(lack))
        print("先运行：pip install %s" % " ".join(lack))
    elif not os.path.exists(pdf_path):
        print("找不到 PDF：%s" % pdf_path)
        print("用法：python pdf_vocab_tool.py <PDF路径> [起始页 结束页 | 全部]")
        print("提示：把官方《等级标准（第二分册：词汇）》PDF 放到 data/词汇表.pdf 最省事。")
    else:
        import fitz                        # PyMuPDF
        from rapidocr_onnxruntime import RapidOCR

        doc = fitz.open(pdf_path)
        if end > doc.page_count:
            end = doc.page_count
        print("PDF：%s（共 %d 页）→ 处理 PDF 第 %d–%d 页"
              % (os.path.basename(pdf_path), doc.page_count, start, end))

        cache = read_cache()
        todo = []
        for pno in range(start, end + 1):
            if str(pno) not in cache:          # 这一页还没 OCR 过
                todo.append(pno)

        if len(todo) == 0:
            print("命中缓存，跳过 OCR（缓存 %d 页）" % len(cache))
        else:
            print("本次需要 OCR %d 页（已缓存 %d 页会跳过）"
                  % (len(todo), (end - start + 1) - len(todo)))
            engine = RapidOCR()
            for pno in todo:
                lines = merge_rows(ocr_page(engine, render_page(doc, pno)))
                cache[str(pno)] = lines
                print("  第 %d 页：OCR 得到 %d 行" % (pno, len(lines)))
            write_cache(cache)
            print("缓存已更新（%d 页）-> %s" % (len(cache), CACHE))

        rows = []
        for pno in range(start, end + 1):
            if str(pno) in cache:
                rows.extend(parse_page(pno, cache[str(pno)]))
        rows.sort()

        out, groups = write_report(rows, start, end, os.path.basename(pdf_path))
        print("已生成：%s" % out)
        summary = ""
        for pos in groups:
            summary = summary + "%s %d 个　" % (pos, len(groups[pos]))
        print("词性分布：%s" % summary)
        doc.close()
