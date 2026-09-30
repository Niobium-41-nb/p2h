#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → HOJ 格式核心转换模块

参考 HOJ 官方文档《题目管理 / 导入题目》：
    https://docs.hdoi.cn/use/import-problem

HOJ 导入包结构（zip 根目录下，**不能**再多套一层文件夹）：

    problem_1000.json        # 题目数据（json 文件名去掉后缀 = 测试数据文件夹名）
    problem_1000/            # 测试数据文件夹，名字必须与 json 文件名一一对应
        1.in
        1.out
        2.in
        2.out
        ...

题目 json 中 samples（评测点）的 input/output 指的是**测试数据文件夹内的文件名**，
其余信息（标题、题面、时间/空间限制等）都在 problem 对象里。
"""

import os
import re
import json
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Callable, Dict

from polygon_tests import load_test_data, failure_message


# ========== HOJ 相关常量 ==========

# HOJ 支持的判题语言（需与 HOJ language 表的 name 字段一致）
HOJ_LANGUAGES = ["C", "C++", "Java", "Python3", "Python2", "Golang", "C#"]

# 题目权限
AUTH_PUBLIC = 1      # 公开
AUTH_PRIVATE = 2     # 隐藏（私有）
AUTH_CONTEST = 3     # 比赛中

# 题目类型
TYPE_ACM = 0
TYPE_OI = 1

# 题目难度（二次开发后的 HOJ 共 9 个等级：0~8）
# 与 HOJ 前端下拉框保持一致；如需再次调整，只需修改这个列表
HOJ_DIFFICULTIES = [
    '0 - 暂无评定',
    '1 - 入门',
    '2 - 普及-',
    '3 - 普及',
    '4 - 普及+/提高-',
    '5 - 提高',
    '6 - 提高+/省选-',
    '7 - 省选/NOI-',
    '8 - NOI/NOI+/CTS',
]
HOJ_DIFFICULTY_MIN = 0
HOJ_DIFFICULTY_MAX = len(HOJ_DIFFICULTIES) - 1

# 用例模式
JUDGE_CASE_MODES = ["default", "ergodic_without_error", "subtask_lowest", "subtask_average"]


def normalize_difficulty(value) -> int:
    """把难度值收敛到合法范围（0~8），非法值回退为 0（暂无评定）"""
    try:
        level = int(value)
    except (TypeError, ValueError):
        return HOJ_DIFFICULTY_MIN
    if level < HOJ_DIFFICULTY_MIN or level > HOJ_DIFFICULTY_MAX:
        return HOJ_DIFFICULTY_MIN
    return level


# ========== 转换选项 ==========

@dataclass
class HojOptions:
    """HOJ 转换选项"""

    author: str = ''                      # 题目作者（留空则由导入者用户名作为作者）
    auth: int = AUTH_PUBLIC               # 1 公开 / 2 隐藏 / 3 比赛中
    problem_type: int = TYPE_ACM          # 0 ACM / 1 OI
    difficulty: int = HOJ_DIFFICULTY_MIN   # 难度 0~8（0 暂无评定、1 入门 … 8 NOI/NOI+/CTS）
    judge_case_mode: str = 'default'      # 用例模式
    tags: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=lambda: list(HOJ_LANGUAGES))
    problem_id: str = ''                  # 题目展示 ID（留空则使用 Polygon short-name）
    max_test_data_mb: float = 0           # 测试数据大小上限（MB），0 = 不限制
    generate_tests: bool = True           # 包内缺失的测试点是否现场动态生成（跑生成器 + 主标程）

    def normalized(self) -> 'HojOptions':
        """返回一个字段取值合法的副本"""
        opts = HojOptions(
            author=(self.author or '').strip(),
            auth=self.auth if self.auth in (AUTH_PUBLIC, AUTH_PRIVATE, AUTH_CONTEST) else AUTH_PUBLIC,
            problem_type=self.problem_type if self.problem_type in (TYPE_ACM, TYPE_OI) else TYPE_ACM,
            difficulty=normalize_difficulty(self.difficulty),
            judge_case_mode=self.judge_case_mode if self.judge_case_mode in JUDGE_CASE_MODES else 'default',
            tags=[t.strip() for t in (self.tags or []) if t and t.strip()],
            languages=[l.strip() for l in (self.languages or []) if l and l.strip()] or list(HOJ_LANGUAGES),
            problem_id=(self.problem_id or '').strip(),
            max_test_data_mb=self.max_test_data_mb if self.max_test_data_mb and self.max_test_data_mb > 0 else 0,
            generate_tests=bool(self.generate_tests),
        )
        return opts


# ========== 通用工具函数 ==========

def extract_zip(zip_path: str, extract_dir: str) -> str:
    """解压 zip 文件到指定目录"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    return extract_dir


def parse_problem_xml(extract_dir: str) -> ET.Element:
    """解析 problem.xml"""
    xml_path = os.path.join(extract_dir, 'problem.xml')
    tree = ET.parse(xml_path)
    return tree.getroot()


def get_text_content(file_path: str) -> str:
    """读取文本文件内容"""
    if not os.path.isfile(file_path):
        return ''
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def html_to_plain_text(html_content: str) -> str:
    """将 HTML 内容转换为纯文本（退化方案）"""
    text = html_content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = (text.replace('&lt;', '<').replace('&gt;', '>')
                .replace('&amp;', '&').replace('&nbsp;', ' ')
                .replace('&quot;', '"').replace('&#39;', "'"))
    text = re.sub(r'\$\$\$', '$', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# LaTeX 命令 → Unicode（题面中常见的符号）
_TEX_SYMBOLS = [
    ('\\Longleftrightarrow', '↔'), ('\\Longrightarrow', '⇒'), ('\\Longleftarrow', '⇐'),
    ('\\longrightarrow', '→'), ('\\longleftarrow', '←'), ('\\leftrightarrow', '↔'),
    ('\\rightarrow', '→'), ('\\leftarrow', '←'), ('\\Rightarrow', '⇒'), ('\\Leftarrow', '⇐'),
    ('\\uparrow', '↑'), ('\\downarrow', '↓'), ('\\Uparrow', '⇑'), ('\\Downarrow', '⇓'),
    ('\\mapsto', '↦'), ('\\to', '→'), ('\\gets', '←'),
    ('\\leqslant', '≤'), ('\\geqslant', '≥'), ('\\le', '≤'), ('\\ge', '≥'),
    ('\\ll', '≪'), ('\\gg', '≫'), ('\\neq', '≠'), ('\\ne', '≠'), ('\\equiv', '≡'),
    ('\\approx', '≈'), ('\\cong', '≅'), ('\\sim', '∼'), ('\\propto', '∝'), ('\\mid', '|'),
    ('\\parallel', '∥'), ('\\perp', '⊥'), ('\\lt', '<'), ('\\gt', '>'),
    ('\\notin', '∉'), ('\\subseteq', '⊆'), ('\\supseteq', '⊇'), ('\\subset', '⊂'),
    ('\\supset', '⊃'), ('\\cup', '∪'), ('\\cap', '∩'), ('\\setminus', '∖'),
    ('\\varnothing', '∅'), ('\\emptyset', '∅'), ('\\in', '∈'), ('\\ni', '∋'),
    ('\\times', '×'), ('\\div', '÷'), ('\\pm', '±'), ('\\mp', '∓'), ('\\cdot', '·'),
    ('\\ast', '*'), ('\\star', '★'), ('\\circ', '°'), ('\\bullet', '•'),
    ('\\oplus', '⊕'), ('\\otimes', '⊗'), ('\\odot', '⊙'),
    ('\\forall', '∀'), ('\\exists', '∃'), ('\\lnot', '¬'), ('\\land', '∧'), ('\\lor', '∨'),
    ('\\ldots', '...'), ('\\dots', '...'), ('\\cdots', '...'), ('\\vdots', '⋮'), ('\\ddots', '⋱'),
    ('\\infty', '∞'), ('\\partial', '∂'), ('\\nabla', '∇'), ('\\prime', '′'), ('\\degree', '°'),
    ('\\angle', '∠'), ('\\triangle', '△'), ('\\surd', '√'), ('\\ell', 'ℓ'), ('\\hbar', 'ħ'),
    ('\\lfloor', '⌊'), ('\\rfloor', '⌋'), ('\\lceil', '⌈'), ('\\rceil', '⌉'),
    ('\\P', '¶'), ('\\S', '§'),
]


# 数学模式片段：$$...$$ / \[...\] / \(...\) / $...$
_MATH_RE = re.compile(r'(\$\$.*?\$\$|\\\[.*?\\\]|\\\(.*?\\\)|\$[^$\n]*?\$)', re.DOTALL)


def _tex_to_markdown_text(text: str) -> str:
    """处理**非数学模式**的 LaTeX 片段（数学公式由 KaTeX 渲染，不做任何改动）"""
    # 1. 转义字符（必须放在通用命令清除之前）
    text = (text.replace('\\&', '&').replace('\\%', '%').replace('\\$', '$')
                .replace('\\#', '#').replace('\\_', '_')
                .replace('\\{', '{').replace('\\}', '}'))

    # 2. 章节命令 → Markdown 标题
    text = re.sub(r'\\section\*?\{([^}]*)\}', r'\n## \1\n', text)
    text = re.sub(r'\\subsection\*?\{([^}]*)\}', r'\n### \1\n', text)
    text = re.sub(r'\\subsubsection\*?\{([^}]*)\}', r'\n#### \1\n', text)

    # 3. 列表环境 → Markdown 列表
    text = re.sub(r'\\begin\{(?:itemize|enumerate|description)\}', '\n', text)
    text = re.sub(r'\\end\{(?:itemize|enumerate|description)\}', '\n', text)
    text = re.sub(r'\\item(?:\[[^\]]*\])?[ \t]*', '\n- ', text)

    # 4. 其余环境标记（表格、居中、图片等）直接丢弃环境名
    text = re.sub(r'\\begin\{[^}]*\}', '\n', text)
    text = re.sub(r'\\end\{[^}]*\}', '\n', text)

    # 5. 强调 / 等宽 / 文本命令 → Markdown
    text = re.sub(r'\\texttt\{([^}]*)\}', r'`\1`', text)
    text = re.sub(r'\\textbf\{([^}]*)\}', r'**\1**', text)
    text = re.sub(r'\\emph\{([^}]*)\}', r'*\1*', text)
    text = re.sub(r'\\textit\{([^}]*)\}', r'*\1*', text)
    text = re.sub(r'\\textsc\{([^}]*)\}', r'\1', text)
    for cmd in ('text', 'textrm', 'textnormal', 'mbox', 'hbox', 'mathrm', 'operatorname'):
        text = re.sub(r'\\' + cmd + r'\{([^}]*)\}', r'\1', text)

    # 6. 常见数学符号 → Unicode
    for cmd, repl in _TEX_SYMBOLS:
        text = text.replace(cmd, repl)

    # 7. 换行
    text = re.sub(r'\\\\[ \t]*(?:\n|$)', '\n', text)
    text = re.sub(r'\\\\', '\n', text)
    text = text.replace('\\newline', '\n').replace('\\par', '\n\n')

    # 8. 清除剩余的未知命令（保留花括号）
    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)

    # 9. 杂项清理
    text = text.replace('~', ' ')
    return text


def tex_to_markdown(tex_content: str) -> str:
    """将 LaTeX 题面转换为 Markdown（数学公式原样保留，供 KaTeX 渲染）"""
    text = tex_content

    # 去掉 LaTeX 注释
    text = re.sub(r'(?<!\\)%.*', '', text)

    # 按数学模式切分，公式内部不做任何转换（\frac、\sum、\begin{cases} 等必须原样保留）
    parts = _MATH_RE.split(text)
    converted = []
    for i, part in enumerate(parts):
        if i % 2 == 1:                      # 奇数下标 = 数学公式
            converted.append(part.replace('$$$', '$'))
        else:
            converted.append(_tex_to_markdown_text(part))
    text = ''.join(converted)

    text = re.sub(r'\$\$\$', '$', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ========== Polygon 数据提取 ==========

def pick_statement_language(extract_dir: str) -> str:
    """选择题面语言目录（优先中文）"""
    base = os.path.join(extract_dir, 'statement-sections')
    candidates = []
    if os.path.isdir(base):
        candidates = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    for prefer in ('chinese', 'english'):
        if prefer in candidates:
            return prefer
    if candidates:
        return sorted(candidates)[0]
    return 'chinese'


def get_problem_info(root: ET.Element) -> dict:
    """从 problem.xml 提取题目基本信息"""
    info = {}

    # 标题（优先中文）
    names_elem = root.find('names')
    title = ''
    if names_elem is not None:
        for name in names_elem.findall('name'):
            if name.get('language') == 'chinese':
                title = name.get('value', '')
                break
        if not title:
            first = names_elem.find('name')
            if first is not None:
                title = first.get('value', '')
    info['title'] = title
    info['short_name'] = root.get('short-name', '') or title

    # 时间 / 空间限制
    time_limit_ms = 1000
    memory_limit_bytes = 256 * 1024 * 1024
    testset = root.find('.//testset')
    if testset is not None:
        tl = testset.find('time-limit')
        if tl is not None and tl.text and tl.text.strip().isdigit():
            time_limit_ms = int(tl.text.strip())
        ml = testset.find('memory-limit')
        if ml is not None and ml.text and ml.text.strip().isdigit():
            memory_limit_bytes = int(ml.text.strip())

    info['time_limit_ms'] = max(1, min(time_limit_ms, 30000))
    info['memory_limit_mb'] = max(1, min(memory_limit_bytes // (1024 * 1024), 1024))
    return info


def build_hoj_sections(extract_dir: str, root: ET.Element, lang: str) -> Dict[str, str]:
    """构建 HOJ 题目各段内容（description / input / output / hint）"""
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)

    description = tex_to_markdown(get_text_content(os.path.join(sections_dir, 'legend.tex')))
    input_desc = tex_to_markdown(get_text_content(os.path.join(sections_dir, 'input.tex')))
    output_desc = tex_to_markdown(get_text_content(os.path.join(sections_dir, 'output.tex')))

    hint = tex_to_markdown(get_text_content(os.path.join(sections_dir, 'notes.tex')))
    if not hint:
        # 部分 Polygon 题目把提示放在 tutorial 之外的文件里，这里兼容 notes 的其它命名
        for alt in ('note.tex', 'hint.tex'):
            hint = tex_to_markdown(get_text_content(os.path.join(sections_dir, alt)))
            if hint:
                break

    # 都没有内容时退回到 HTML 题面
    if not description and not input_desc and not output_desc:
        html_path = os.path.join(extract_dir, 'statements', '.html', lang, 'problem.html')
        html_content = get_text_content(html_path)
        if html_content:
            description = html_to_plain_text(html_content)

    return {
        'description': description,
        'input': input_desc,
        'output': output_desc,
        'hint': hint,
    }


def get_examples(extract_dir: str, lang: str) -> List[Tuple[str, str]]:
    """获取题面样例（statement-sections/<lang>/example.N 与 example.N.a）"""
    samples = []
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)
    if not os.path.isdir(sections_dir):
        return samples

    inputs, outputs = {}, {}
    for f in os.listdir(sections_dir):
        m = re.match(r'^example\.(\d+)$', f)
        if m:
            inputs[int(m.group(1))] = os.path.join(sections_dir, f)
            continue
        m = re.match(r'^example\.(\d+)\.a$', f)
        if m:
            outputs[int(m.group(1))] = os.path.join(sections_dir, f)

    for idx in sorted(inputs):
        inp = get_text_content(inputs[idx]).strip()
        out = get_text_content(outputs.get(idx, '')).strip()
        if inp:
            samples.append((inp, out))
    return samples


def build_examples_html(examples: List[Tuple[str, str]]) -> str:
    """构建 HOJ problem.examples 字段（<input>..</input><output>..</output>）"""
    parts = []
    for inp, out in examples:
        parts.append(f'<input>{inp}</input><output>{out}</output>')
    return ''.join(parts)


def get_all_tests(extract_dir: str, root: ET.Element, max_test_data_mb: float = 0,
                  warn: Optional[Callable[[str], None]] = None,
                  generate_tests: bool = True,
                  log: Optional[Callable[[str], None]] = None) -> List[Tuple[bytes, bytes]]:
    """读取全部测试数据（返回原始字节，保证与评测文件完全一致）

    Polygon 包里的测试数据是「用生成器（gen）动态生成 + 用主标程算答案」得到的，
    压缩包中不一定静态存放；缺失部分由 polygon_tests 现场生成。
    """
    limit = int(max_test_data_mb * 1024 * 1024) if max_test_data_mb and max_test_data_mb > 0 else 0
    result = load_test_data(extract_dir, root, generate=generate_tests, log=log,
                            max_total_bytes=limit)
    if warn:
        for message in result.warnings:
            warn(message)
    if result.test_count and not result.tests:
        raise ValueError(failure_message(result))
    return [(t.input, t.answer) for t in result.tests]


# ========== HOJ 题目构建 ==========

def _sanitize_key(name: str) -> str:
    """生成合法的 json / 文件夹名（两者必须一致）"""
    key = re.sub(r'[\\/:*?"<>|\s]+', '_', (name or '').strip())
    key = key.strip('._')
    return key[:80] or 'problem'


def build_problem_id(info: dict, options: HojOptions) -> str:
    """题目展示 ID（HOJ 要求唯一、非空、长度 ≤ 50）"""
    pid = options.problem_id or info.get('short_name') or info.get('title') or 'problem'
    return pid.strip()[:50] or 'problem'


def build_samples(tests: List[Tuple[bytes, bytes]], options: HojOptions) -> List[dict]:
    """构建 samples（评测点）列表，input/output 为测试数据文件夹内的文件名"""
    samples = []
    total = len(tests)
    for i in range(total):
        item = {'input': f'{i + 1}.in', 'output': f'{i + 1}.out'}
        if options.problem_type == TYPE_OI:
            # OI 题目需要给每个测试点分配分数（总分 100）
            base, rem = divmod(100, total)
            item['score'] = base + (1 if i < rem else 0)
            if options.judge_case_mode in ('subtask_lowest', 'subtask_average'):
                item['groupNum'] = 1
        samples.append(item)
    return samples


def build_problem_json(info: dict, sections: Dict[str, str], examples_html: str,
                       tests: List[Tuple[bytes, bytes]], options: HojOptions) -> dict:
    """构建 HOJ 题目 json 对象"""
    problem = {
        'auth': options.auth,
        'isRemote': False,
        'problemId': build_problem_id(info, options),
        'description': sections['description'],
        'source': info.get('short_name') or '',
        'title': (info.get('title') or build_problem_id(info, options))[:255],
        'type': options.problem_type,
        'timeLimit': info['time_limit_ms'],
        'memoryLimit': info['memory_limit_mb'],
        'stackLimit': 128,
        'input': sections['input'],
        'output': sections['output'],
        'difficulty': options.difficulty,
        'examples': examples_html,
        'ioScore': 100,
        'codeShare': True,
        'hint': sections['hint'],
        'isRemoveEndBlank': True,
        'openCaseResult': True,
        'judgeCaseMode': options.judge_case_mode,
        'isFileIO': False,
        'isGroup': False,
        'isUploadCase': True,
        'ioReadFileName': None,
        'ioWriteFileName': None,
    }
    if options.author:
        problem['author'] = options.author

    return {
        # judgeMode: default 普通判题 / spj 特殊判题 / interactive 交互判题
        'judgeMode': 'default',
        # 题目的可选语言
        'languages': list(options.languages),
        # 评测点（input/output 为测试数据文件夹内的文件名）
        'samples': build_samples(tests, options),
        # 标签
        'tags': list(options.tags),
        # 题目本体
        'problem': problem,
        # 代码模板（HOJ 导入时必须存在该字段，否则会解析失败）
        'codeTemplates': [],
    }


def _build_problem_data(polygon_zip: str, options: HojOptions,
                        progress_callback: Optional[Callable] = None,
                        progress_range: Tuple[int, int] = (0, 100)) -> Tuple[dict, List[Tuple[str, bytes]], dict]:
    """
    解析单个 Polygon 压缩包，返回 (题目 json 对象, [(相对路径, 内容字节)], 统计信息)

    相对路径形如 '1.in' / '1.out'（相对于题目数据文件夹）
    """
    if not os.path.isfile(polygon_zip):
        raise FileNotFoundError(f'文件不存在: {polygon_zip}')

    start, end = progress_range
    span = end - start
    warnings: List[str] = []

    def report(ratio: float, msg: str):
        if progress_callback:
            progress_callback(int(start + span * ratio), msg)

    tmp_dir = tempfile.mkdtemp(prefix='polygon2hoj_')
    try:
        report(0.05, '正在解压...')
        extract_zip(polygon_zip, tmp_dir)

        report(0.25, '正在解析 problem.xml...')
        try:
            root = parse_problem_xml(tmp_dir)
        except Exception as e:
            raise ValueError(f'无法解析 problem.xml（{e}），请确认这是 Polygon 导出的题目压缩包') from e
        info = get_problem_info(root)

        report(0.45, '正在构建题面...')
        lang = pick_statement_language(tmp_dir)
        sections = build_hoj_sections(tmp_dir, root, lang)
        examples = get_examples(tmp_dir, lang)

        report(0.65, '正在准备测试数据...')

        # 生成过程的日志（含警告）由 log 回调输出，warn 只负责把警告收集进 stat
        tests = get_all_tests(tmp_dir, root, options.max_test_data_mb,
                              warn=warnings.append,
                              generate_tests=options.generate_tests,
                              log=lambda m: report(0.65, m))
        if not tests:
            raise ValueError('未在压缩包中找到任何测试数据')

        report(0.8, '正在生成题目数据...')
        data = build_problem_json(info, sections, build_examples_html(examples), tests, options)

        files: List[Tuple[str, bytes]] = []
        for i, (in_data, out_data) in enumerate(tests, start=1):
            files.append((f'{i}.in', in_data))
            files.append((f'{i}.out', out_data))

        stat = {
            'title': info.get('title', ''),
            'problem_id': data['problem']['problemId'],
            'tests': len(tests),
            'samples': len(examples),
            'warnings': warnings,
        }
        report(1.0, f'解析完成（{len(tests)} 组测试数据）')
        return data, files, stat
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


# ========== 对外接口 ==========

def convert_to_hoj(polygon_zip: str, output_dir: str,
                   options: Optional[HojOptions] = None,
                   progress_callback: Optional[Callable] = None) -> str:
    """
    将单个 Polygon 题目转换为 HOJ 导入用的 zip（内不含多余文件夹）。

    Args:
        polygon_zip: polygon.codeforces 格式的 zip 文件路径
        output_dir: 输出目录
        options: HojOptions 转换选项
        progress_callback: 进度回调 (stage:int, message:str)

    Returns:
        生成的 zip 文件路径
    """
    options = (options or HojOptions()).normalized()

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        data, files, stat = _build_problem_data(polygon_zip, options, progress_callback, (0, 80))
        key = _sanitize_key(options.problem_id or stat['problem_id'] or
                           os.path.splitext(os.path.basename(polygon_zip))[0])

        if progress_callback:
            progress_callback(85, '正在打包为 ZIP...')

        zip_path = os.path.join(output_dir, f'{key}.hoj.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f'{key}.json', _dump_json(data))
            for rel, content in files:
                zf.writestr(f'{key}/{rel}', content)

        if progress_callback:
            progress_callback(100, f'转换完成! 输出: {zip_path}')
        return zip_path

    except Exception as e:
        if progress_callback:
            progress_callback(-1, f'转换失败: {e}')
        raise


def convert_batch_to_hoj(polygon_zips: List[str], output_zip: str,
                         options: Optional[HojOptions] = None,
                         progress_callback: Optional[Callable] = None) -> Tuple[str, List[str]]:
    """
    将多个 Polygon 题目合并为一个 HOJ 导入 zip（一次导入多题）。

    Returns:
        (zip 文件路径, 失败题目的错误信息列表)
    """
    options = (options or HojOptions()).normalized()
    total = len(polygon_zips)
    if total == 0:
        raise ValueError('待转换的文件列表为空')

    out_dir = os.path.dirname(os.path.abspath(output_zip))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    errors: List[str] = []
    used_keys = set()
    entries: List[Tuple[str, dict, List[Tuple[str, bytes]], dict]] = []

    for i, zip_path in enumerate(polygon_zips):
        name = os.path.basename(zip_path)
        file_start = int(i / total * 85)
        file_end = int((i + 1) / total * 85)

        def report(stage, msg, _name=name, _i=i):
            if progress_callback:
                progress_callback(min(stage, 85), f'[{_i + 1}/{total}] {_name}: {msg}')

        try:
            data, files, stat = _build_problem_data(zip_path, options, report, (file_start, file_end))
        except Exception as e:
            errors.append(f'{name}: {e}')
            if progress_callback:
                progress_callback(min(file_end, 85), f'❌ {name} 转换失败: {e}')
            continue

        base_key = _sanitize_key(options.problem_id or stat['problem_id'] or
                                 os.path.splitext(name)[0])
        key = base_key
        seq = 2
        while key in used_keys:
            key = f'{base_key}_{seq}'
            seq += 1
        used_keys.add(key)
        entries.append((key, data, files, stat))

    if not entries:
        raise ValueError('所有题目均转换失败：' + '；'.join(errors))

    if progress_callback:
        progress_callback(90, '正在打包为 ZIP...')

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for key, data, files, _stat in entries:
            zf.writestr(f'{key}.json', _dump_json(data))
            for rel, content in files:
                zf.writestr(f'{key}/{rel}', content)

    if progress_callback:
        progress_callback(100, f'转换完成! 共 {len(entries)} 题 → {output_zip}')
    return output_zip, errors
