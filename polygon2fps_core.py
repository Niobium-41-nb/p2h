#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS (Fresh Problem Set) 核心转换模块
"""

import os
import re
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape
from typing import Optional, List, Tuple


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
    """读取文件内容"""
    if not os.path.isfile(file_path):
        return ''
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def tex_to_plain_text(tex_content: str) -> str:
    """将 LaTeX 内容转换为纯文本"""
    text = tex_content

    # 1. 移除注释
    text = re.sub(r'(?<!\\)%.*', '', text)

    # 2. 处理 \begin{xxx} 和 \end{xxx} 环境标记
    text = re.sub(r'\\begin\{[^}]*\}', '', text)
    text = re.sub(r'\\end\{[^}]*\}', '', text)

    # 3. 处理 \item (列表项)
    text = re.sub(r'\\item\s*', '- ', text)

    # 4. 处理 \left, \right (通常可以移除，但要保留后面的内容)
    text = re.sub(r'\\left\b\s*', '', text)
    text = re.sub(r'\\right\b\s*', '', text)

    # 5. 移除 \displaystyle, \limits 等格式命令
    text = re.sub(r'\\displaystyle\s*', '', text)
    text = re.sub(r'\\limits\s*', '', text)

    # 6. 数学符号替换（完整命令优先，避免部分匹配）
    replacements = [
        # 箭头
        ('\\Longleftarrow', '⇐'),
        ('\\Longrightarrow', '⇒'),
        ('\\Longleftrightarrow', '↔'),
        ('\\longleftarrow', '←'),
        ('\\longrightarrow', '→'),
        ('\\leftarrow', '←'),
        ('\\rightarrow', '→'),
        ('\\Leftarrow', '⇐'),
        ('\\Rightarrow', '⇒'),
        ('\\leftrightarrow', '↔'),
        ('\\uparrow', '↑'),
        ('\\downarrow', '↓'),
        ('\\updownarrow', '↕'),
        ('\\Uparrow', '⇑'),
        ('\\Downarrow', '⇓'),
        ('\\Updownarrow', '⇕'),
        ('\\mapsto', '↦'),
        ('\\longmapsto', '⟼'),
        ('\\nearrow', '↗'),
        ('\\searrow', '↘'),
        ('\\swarrow', '↙'),
        ('\\nwarrow', '↖'),
        ('\\to', '→'),
        ('\\gets', '←'),
        # 关系符号
        ('\\le', '≤'),
        ('\\ge', '≥'),
        ('\\leqslant', '≤'),
        ('\\geqslant', '≥'),
        ('\\ll', '≪'),
        ('\\gg', '≫'),
        ('\\neq', '≠'),  # 必须放在 \ne 之前，避免 \neq 被 \ne 部分匹配
        ('\\ne', '≠'),
        ('\\equiv', '≡'),
        ('\\approx', '≈'),
        ('\\approxeq', '≊'),
        ('\\cong', '≅'),
        ('\\simeq', '≃'),
        ('\\sim', '∼'),
        ('\\doteq', '≐'),
        ('\\propto', '∝'),
        ('\\models', '⊨'),
        ('\\mid', '|'),
        ('\\parallel', '∥'),
        ('\\perp', '⊥'),
        ('\\lt', '<'),
        ('\\gt', '>'),
        # 集合符号
        ('\\in', '∈'),
        ('\\notin', '∉'),
        ('\\ni', '∋'),
        ('\\subset', '⊂'),
        ('\\supset', '⊃'),
        ('\\subseteq', '⊆'),
        ('\\supseteq', '⊇'),
        ('\\subsetneq', '⊊'),
        ('\\supsetneq', '⊋'),
        ('\\cup', '∪'),
        ('\\cap', '∩'),
        ('\\setminus', '∖'),
        ('\\emptyset', '∅'),
        ('\\varnothing', '∅'),
        # 运算符
        ('\\times', '×'),
        ('\\div', '÷'),
        ('\\pm', '±'),
        ('\\mp', '∓'),
        ('\\cdot', '·'),
        ('\\ast', '*'),
        ('\\star', '★'),
        ('\\circ', '°'),
        ('\\bullet', '•'),
        ('\\oplus', '⊕'),
        ('\\ominus', '⊖'),
        ('\\otimes', '⊗'),
        ('\\oslash', '⊘'),
        ('\\odot', '⊙'),
        ('\\dagger', '†'),
        ('\\ddagger', '‡'),
        # 逻辑符号
        ('\\forall', '∀'),
        ('\\exists', '∃'),
        ('\\nexists', '∄'),
        ('\\land', '∧'),
        ('\\lor', '∨'),
        ('\\lnot', '¬'),
        ('\\top', '⊤'),
        ('\\bot', '⊥'),
        ('\\vdash', '⊢'),
        ('\\vDash', '⊨'),
        # 其他符号
        ('\\ldots', '...'),
        ('\\dots', '...'),
        ('\\cdots', '...'),
        ('\\vdots', '⋮'),
        ('\\ddots', '⋱'),
        ('\\infty', '∞'),
        ('\\partial', '∂'),
        ('\\nabla', '∇'),
        ('\\prime', '′'),
        ('\\degree', '°'),
        ('\\angle', '∠'),
        ('\\triangle', '△'),
        ('\\surd', '√'),
        ('\\imath', 'i'),
        ('\\jmath', 'j'),
        ('\\ell', 'ℓ'),
        ('\\hbar', 'ħ'),
        ('\\lfloor', '⌊'),
        ('\\rfloor', '⌋'),
        ('\\lceil', '⌈'),
        ('\\rceil', '⌉'),
        ('\\&', '&'),
        ('\\_', '_'),
        ('\\%', '%'),
        ('\\$', '$'),
        ('\\#', '#'),
        ('\\P', '¶'),
        ('\\S', '§'),
    ]
    for cmd, repl in replacements:
        text = text.replace(cmd, repl)

    # 7. 函数名（需要保留为文本）
    # 注意: 使用 (?![a-zA-Z]) 替代 \b，因为 _ 是 \w 的一部分
    func_names = [
        'max', 'min', 'sum', 'prod', 'log', 'ln', 'lg', 'sin', 'cos',
        'tan', 'cot', 'sec', 'csc', 'arcsin', 'arccos', 'arctan',
        'sinh', 'cosh', 'tanh', 'det', 'dim', 'hom', 'ker', 'exp',
        'gcd', 'lcm', 'mod', 'bmod', 'pmod', 'arg', 'deg',
    ]
    for name in func_names:
        text = re.sub(rf'\\{name}(?![a-zA-Z])', name, text)

    # 8. 处理 \text{...}, \textbf{...}, \textit{...}, \texttt{...}
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\texttt\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathit\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathbf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathsf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathtt\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathcal\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathbb\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathfrak\{([^}]*)\}', r'\1', text)

    # 9. 处理上标和下标
    text = re.sub(r'\^\{(.+?)\}', r'^{\1}', text)
    text = re.sub(r'\_\{(.+?)\}', r'_{\1}', text)

    # 10. 处理 \frac{a}{b} → a/b
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'\1/\2', text)

    # 11. 处理 \sqrt, \sqrt[n]{...}
    text = re.sub(r'\\sqrt(?:\[([^\]]*)\])?\{([^}]*)\}', r'sqrt(\2)', text)

    # 12. 处理 \binom{n}{k}
    text = re.sub(r'\\binom\{([^}]*)\}\{([^}]*)\}', r'C(\1,\2)', text)

    # 13. 处理 \underline, \overline, \overbrace, \underbrace
    text = re.sub(r'\\underline\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\overline\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\overbrace\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\underbrace\{([^}]*)\}', r'\1', text)

    # 14. 处理 \operatorname{name}
    text = re.sub(r'\\operatorname\{([^}]*)\}', r'\1', text)

    # 15. 处理 \mbox{...}
    text = re.sub(r'\\mbox\{([^}]*)\}', r'\1', text)

    # 16. 移除剩余的 \xxx 命令（未知命令）
    text = re.sub(r'\\[a-zA-Z]+(?![a-zA-Z])', '', text)

    # 17. 处理 { 和 } 括号（数学模式中的分组括号）
    text = text.replace('{', '')
    text = text.replace('}', '')

    # 18. 处理 $$...$$ 和 $...$ 数学模式标记
    text = re.sub(r'\$\$\$(.+?)\$\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$\$(.+?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', r'\1', text, flags=re.DOTALL)

    # 19. 合并多余空行
    text = re.sub(r'\n\s*\n', '\n\n', text)

    text = text.strip()
    return text


def html_to_plain_text(html_content: str) -> str:
    """将 HTML 内容转换为纯文本"""
    text = html_content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&', '&')
    text = text.replace('<', '<')
    text = text.replace('>', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('"', '"')
    text = re.sub(r'\$\$\$', '$', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    return text


def build_description(extract_dir: str, root: ET.Element, lang: str = 'chinese') -> str:
    """构建题目描述"""
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)
    parts = []

    name_file = os.path.join(sections_dir, 'name.tex')
    name_content = get_text_content(name_file)
    if name_content:
        parts.append(tex_to_plain_text(name_content))

    legend_file = os.path.join(sections_dir, 'legend.tex')
    legend_content = get_text_content(legend_file)
    if legend_content:
        parts.append(tex_to_plain_text(legend_content))

    input_file = os.path.join(sections_dir, 'input.tex')
    input_content = get_text_content(input_file)
    if input_content:
        parts.append('【输入格式】\n' + tex_to_plain_text(input_content))

    output_file = os.path.join(sections_dir, 'output.tex')
    output_content = get_text_content(output_file)
    if output_content:
        parts.append('【输出格式】\n' + tex_to_plain_text(output_content))

    notes_file = os.path.join(sections_dir, 'notes.tex')
    notes_content = get_text_content(notes_file)
    if notes_content:
        parts.append('【提示】\n' + tex_to_plain_text(notes_content))

    if parts:
        return '\n\n'.join(parts)

    html_path = os.path.join(extract_dir, 'statements', '.html', lang, 'problem.html')
    html_content = get_text_content(html_path)
    if html_content:
        return html_to_plain_text(html_content)

    return ''


def get_samples(extract_dir: str, lang: str = 'chinese') -> List[Tuple[str, str]]:
    """获取样例数据"""
    samples = []
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)

    if os.path.isdir(sections_dir):
        files = os.listdir(sections_dir)
        example_inputs = {}
        example_outputs = {}

        for f in files:
            match = re.match(r'example\.(\d+)$', f)
            if match:
                idx = int(match.group(1))
                example_inputs[idx] = os.path.join(sections_dir, f)
            match_a = re.match(r'example\.(\d+)\.a$', f)
            if match_a:
                idx = int(match_a.group(1))
                example_outputs[idx] = os.path.join(sections_dir, f)

        for idx in sorted(example_inputs.keys()):
            inp = get_text_content(example_inputs[idx]).strip()
            out = get_text_content(example_outputs.get(idx, '')).strip()
            if inp and out:
                samples.append((inp, out))

    return samples


def get_all_tests(extract_dir: str, root: ET.Element) -> List[Tuple[str, str]]:
    """获取所有测试数据"""
    tests_dir = os.path.join(extract_dir, 'tests')
    tests = []

    if not os.path.isdir(tests_dir):
        return tests

    testset = root.find('.//testset')
    test_count = 0
    if testset is not None:
        tc = testset.find('test-count')
        if tc is not None and tc.text:
            test_count = int(tc.text)

    for i in range(1, test_count + 1):
        input_file = os.path.join(tests_dir, f'{i:02d}')
        output_file = os.path.join(tests_dir, f'{i:02d}.a')
        inp = get_text_content(input_file).strip()
        out = get_text_content(output_file).strip()
        if inp and out:
            tests.append((inp, out))

    return tests


def _xml_tag(name: str, content: str, indent: int = 1) -> str:
    """生成 XML 标签（使用 CDATA 包裹内容，避免转义问题）"""
    pad = '  ' * indent
    return f'{pad}<{name}><![CDATA[{content}]]></{name}>'


def _xml_tag_with_attr(name: str, content: str, attrs: dict, indent: int = 1) -> str:
    """生成带属性的 XML 标签"""
    pad = '  ' * indent
    attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
    return f'{pad}<{name} {attr_str}><![CDATA[{content}]]></{name}>'


def build_fps_xml(root: ET.Element, extract_dir: str,
                  max_test_data_mb: float = 0) -> str:
    """构建 FPS XML 字符串（手动构建，避免转义问题）

    Args:
        root: problem.xml 的根元素
        extract_dir: 解压目录
        max_test_data_mb: 测试数据大小上限（MB），0 表示不限制
    """
    # 基本信息
    names_elem = root.find('names')
    title = ''
    if names_elem is not None:
        for name in names_elem.findall('name'):
            if name.get('language') == 'chinese':
                title = name.get('value', '')
                break
        if not title:
            title = names_elem.find('name').get('value', '')

    time_limit = '1'
    memory_limit = '256'
    testset = root.find('.//testset')
    if testset is not None:
        tl = testset.find('time-limit')
        if tl is not None and tl.text:
            time_limit = str(int(tl.text) // 1000)
        ml = testset.find('memory-limit')
        if ml is not None and ml.text:
            memory_limit = str(int(ml.text) // 1048576)

    # 描述
    description = build_description(extract_dir, root, 'chinese')
    input_desc = ''
    output_desc = ''

    sections_dir = os.path.join(extract_dir, 'statement-sections', 'chinese')
    input_tex = get_text_content(os.path.join(sections_dir, 'input.tex'))
    output_tex = get_text_content(os.path.join(sections_dir, 'output.tex'))
    if input_tex:
        input_desc = tex_to_plain_text(input_tex)
    if output_tex:
        output_desc = tex_to_plain_text(output_tex)

    # 样例
    samples = get_samples(extract_dir, 'chinese')
    if not samples:
        tests_elem = testset.find('tests') if testset is not None else None
        if tests_elem is not None:
            tests_dir = os.path.join(extract_dir, 'tests')
            for i, test_elem in enumerate(tests_elem.findall('test'), start=1):
                if test_elem.get('sample') == 'true':
                    inp = get_text_content(os.path.join(tests_dir, f'{i:02d}')).strip()
                    out = get_text_content(os.path.join(tests_dir, f'{i:02d}.a')).strip()
                    if inp and out:
                        samples.append((inp, out))

    # 所有测试数据
    all_tests = get_all_tests(extract_dir, root)

    # 如果设置了大小限制，过滤测试数据
    test_data_size_limit = max_test_data_mb * 1024 * 1024 if max_test_data_mb > 0 else 0
    if test_data_size_limit > 0:
        filtered_tests = []
        current_size = 0
        for test_in, test_out in all_tests:
            # 估算大小（CDATA 开销约 12 字节 + XML 标签开销）
            est_size = len(test_in.encode('utf-8')) + len(test_out.encode('utf-8')) + 200
            if current_size + est_size > test_data_size_limit:
                break
            filtered_tests.append((test_in, test_out))
            current_size += est_size
        if len(filtered_tests) < len(all_tests):
            all_tests = filtered_tests

    # 来源
    short_name = root.get('short-name', '')

    # ===== 手动构建 XML =====
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<fps version="1.2" url="https://github.com/zhblue/freeproblemset">')
    lines.append('  <generator name="polygon2fps" url="https://github.com/your-username/polygon2fps"/>')
    lines.append('  <item>')

    # 标题
    lines.append(f'    <title><![CDATA[{title}]]></title>')

    # 时间限制
    lines.append(f'    <time_limit unit="s"><![CDATA[{time_limit}]]></time_limit>')

    # 内存限制
    lines.append(f'    <memory_limit unit="MB"><![CDATA[{memory_limit}]]></memory_limit>')

    # 描述
    lines.append(f'    <description><![CDATA[{description}]]></description>')

    # 输入格式
    lines.append(f'    <input><![CDATA[{input_desc}]]></input>')

    # 输出格式
    lines.append(f'    <output><![CDATA[{output_desc}]]></output>')

    # 样例
    for sample_in, sample_out in samples:
        lines.append(f'    <sample_input><![CDATA[{sample_in}]]></sample_input>')
        lines.append(f'    <sample_output><![CDATA[{sample_out}]]></sample_output>')

    # 测试数据（排除样例）
    sample_set = set(samples)
    for test_in, test_out in all_tests:
        if (test_in, test_out) in sample_set:
            continue
        lines.append(f'    <test_input><![CDATA[{test_in}]]></test_input>')
        lines.append(f'    <test_output><![CDATA[{test_out}]]></test_output>')

    # 提示（某些 OJ 要求此标签存在）
    lines.append('    <hint><![CDATA[]]></hint>')

    # 来源
    lines.append(f'    <source><![CDATA[Polygon: {short_name}]]></source>')

    lines.append('  </item>')
    lines.append('</fps>')

    return '\n'.join(lines)


def convert(polygon_zip: str, output_fps: Optional[str] = None,
            progress_callback=None,
            max_test_data_mb: float = 0) -> str:
    """
    主转换函数。

    Args:
        polygon_zip: polygon.codeforces 格式的 zip 文件路径
        output_fps: 输出的 FPS XML 文件路径
        progress_callback: 进度回调函数，接收 (stage, message) 参数
        max_test_data_mb: 测试数据大小上限（MB），0 表示不限制

    Returns:
        输出文件路径
    """
    if not os.path.isfile(polygon_zip):
        raise FileNotFoundError(f'文件不存在: {polygon_zip}')

    if progress_callback:
        progress_callback(0, '正在解压...')

    tmp_dir = tempfile.mkdtemp(prefix='polygon2fps_')
    try:
        extract_zip(polygon_zip, tmp_dir)

        if progress_callback:
            progress_callback(30, '正在解析 problem.xml...')

        root = parse_problem_xml(tmp_dir)

        if progress_callback:
            progress_callback(50, '正在构建 FPS XML...')

        fps_xml = build_fps_xml(root, tmp_dir, max_test_data_mb)

        if output_fps is None:
            base_name = os.path.splitext(os.path.basename(polygon_zip))[0]
            output_fps = os.path.join(os.path.dirname(polygon_zip), f'{base_name}.fps.xml')

        with open(output_fps, 'w', encoding='utf-8') as f:
            f.write(fps_xml)

        if progress_callback:
            progress_callback(100, f'转换完成! 输出: {output_fps}')

        return output_fps

    except Exception as e:
        if progress_callback:
            progress_callback(-1, f'转换失败: {e}')
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
