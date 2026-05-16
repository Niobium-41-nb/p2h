#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces 格式 → FPS (Fresh Problem Set) 格式转换工具

将 polygon.codeforces.com 导出的题目压缩包转换为 HUSTOJ / FPS 兼容的 XML 格式。

用法:
    python polygon2fps.py <polygon_zip_file> [output_fps_file]

示例:
    python polygon2fps.py hzau-2026-problem1-20linux.zip output.xml
    python polygon2fps.py hzau-2026-problem1-20linux.zip  # 自动生成 output.fps.xml
"""

import os
import sys
import re
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional


def extract_zip(zip_path: str, extract_dir: str) -> str:
    """解压 zip 文件到指定目录，返回解压后的目录路径"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    return extract_dir


def parse_problem_xml(extract_dir: str) -> ET.Element:
    """解析 problem.xml，返回根 Element"""
    xml_path = os.path.join(extract_dir, 'problem.xml')
    tree = ET.parse(xml_path)
    return tree.getroot()


def get_text_content(file_path: str) -> str:
    """读取文件内容，如果文件不存在返回空字符串"""
    if not os.path.isfile(file_path):
        return ''
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def tex_to_plain_text(tex_content: str) -> str:
    """
    将 LaTeX 内容转换为纯文本（去除 LaTeX 命令，保留基本文本）。
    注意：这里做简单转换，保留数学公式标记以便后续处理。
    """
    text = tex_content

    # 移除注释
    text = re.sub(r'(?<!\\)%.*', '', text)

    # 将 \ldots 等替换为文本
    text = text.replace('\\ldots', '...')
    text = text.replace('\\mid', '|')
    text = text.replace('\\&', '&')
    text = text.replace('\\cdot', '·')
    text = text.replace('\\le', '≤')
    text = text.replace('\\ge', '≥')
    text = text.replace('\\lt', '<')
    text = text.replace('\\gt', '>')
    text = text.replace('\\times', '×')

    # 移除 \text{...} 但保留内容
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)

    # 移除 \textbf{...} 等
    text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\texttt\{([^}]*)\}', r'\1', text)

    # 将 $$$...$$$ 或 $...$ 保留为 FPS 可识别的格式
    # 但需要将 $$$ 转换为 $ (FPS 通常使用单个 $)
    text = re.sub(r'\$\$\$', '$', text)

    # 移除多余的空白
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()

    return text


def html_to_plain_text(html_content: str) -> str:
    """
    将 HTML 内容转换为纯文本。
    提取 <div class="legend">, <div class="input-specification"> 等中的文本。
    """
    text = html_content

    # 移除 <script> 及其内容
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 移除所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)

    # 解码 HTML 实体
    text = text.replace('&', '&')
    text = text.replace('<', '<')
    text = text.replace('>', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('"', '"')

    # 将 $$$ 转换为 $
    text = re.sub(r'\$\$\$', '$', text)

    # 移除多余的空白行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()

    return text


def build_description(extract_dir: str, root: ET.Element, lang: str = 'chinese') -> str:
    """
    构建题目描述文本。
    优先从 statement-sections 读取 LaTeX 片段，否则从 HTML 提取。
    """
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)

    parts = []

    # 题目名称
    name_file = os.path.join(sections_dir, 'name.tex')
    name_content = get_text_content(name_file)
    if name_content:
        parts.append(tex_to_plain_text(name_content))

    # 背景/描述 (legend)
    legend_file = os.path.join(sections_dir, 'legend.tex')
    legend_content = get_text_content(legend_file)
    if legend_content:
        parts.append(tex_to_plain_text(legend_content))

    # 输入格式
    input_file = os.path.join(sections_dir, 'input.tex')
    input_content = get_text_content(input_file)
    if input_content:
        parts.append('【输入格式】\n' + tex_to_plain_text(input_content))

    # 输出格式
    output_file = os.path.join(sections_dir, 'output.tex')
    output_content = get_text_content(output_file)
    if output_content:
        parts.append('【输出格式】\n' + tex_to_plain_text(output_content))

    # 备注
    notes_file = os.path.join(sections_dir, 'notes.tex')
    notes_content = get_text_content(notes_file)
    if notes_content:
        parts.append('【提示】\n' + tex_to_plain_text(notes_content))

    if parts:
        return '\n\n'.join(parts)

    # 如果 LaTeX 片段不存在，尝试从 HTML 提取
    html_path = os.path.join(extract_dir, 'statements', '.html', lang, 'problem.html')
    html_content = get_text_content(html_path)
    if html_content:
        return html_to_plain_text(html_content)

    return ''


def build_hint(extract_dir: str, lang: str = 'chinese') -> str:
    """构建提示/题解内容"""
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)
    tutorial_file = os.path.join(sections_dir, 'tutorial.tex')
    tutorial_content = get_text_content(tutorial_file)
    if tutorial_content:
        return tex_to_plain_text(tutorial_content)

    # 尝试从 HTML 提取
    html_path = os.path.join(extract_dir, 'statements', '.html', lang, 'tutorial.html')
    html_content = get_text_content(html_path)
    if html_content:
        return html_to_plain_text(html_content)

    return ''


def get_samples(extract_dir: str, lang: str = 'chinese'):
    """
    从 statement-sections 中读取样例输入/输出。
    返回 [(input, output), ...] 列表。
    """
    samples = []
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)

    # 查找所有 example.XX 和 example.XX.a 文件
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


def get_all_tests(extract_dir: str, root: ET.Element):
    """
    从 tests/ 目录读取所有测试数据。
    返回 [(input, output), ...] 列表。
    """
    tests_dir = os.path.join(extract_dir, 'tests')
    tests = []

    if not os.path.isdir(tests_dir):
        return tests

    # 从 problem.xml 获取 test-count
    testset = root.find('.//testset')
    test_count = 0
    if testset is not None:
        tc = testset.find('test-count')
        if tc is not None and tc.text:
            test_count = int(tc.text)

    # 读取测试文件
    for i in range(1, test_count + 1):
        input_file = os.path.join(tests_dir, f'{i:02d}')
        output_file = os.path.join(tests_dir, f'{i:02d}.a')

        inp = get_text_content(input_file).strip()
        out = get_text_content(output_file).strip()

        if inp and out:
            tests.append((inp, out))

    return tests


def get_solutions(extract_dir: str, root: ET.Element):
    """
    获取所有题解代码。
    返回 [(tag, language, code), ...] 列表。
    """
    solutions = []
    solutions_elem = root.find('.//solutions')
    if solutions_elem is None:
        return solutions

    for sol in solutions_elem.findall('solution'):
        tag = sol.get('tag', '')
        source = sol.find('source')
        if source is not None:
            src_path = source.get('path', '')
            src_type = source.get('type', '')
            full_path = os.path.join(extract_dir, src_path)
            code = get_text_content(full_path)
            if code:
                solutions.append((tag, src_type, code))

    return solutions


def escape_xml(text: str) -> str:
    """转义 XML 特殊字符"""
    text = text.replace('&', '&')
    text = text.replace('<', '<')
    text = text.replace('>', '>')
    text = text.replace('"', '"')
    text = text.replace("'", "'")
    return text


def build_fps_xml(root: ET.Element, extract_dir: str) -> str:
    """
    构建 FPS 格式的 XML 字符串。
    """
    # 获取基本信息
    names_elem = root.find('names')
    title = ''
    if names_elem is not None:
        for name in names_elem.findall('name'):
            if name.get('language') == 'chinese':
                title = name.get('value', '')
                break
        if not title:
            title = names_elem.find('name').get('value', '')

    # 时间限制 (ms -> s)
    time_limit = '1'
    memory_limit = '256'
    testset = root.find('.//testset')
    if testset is not None:
        tl = testset.find('time-limit')
        if tl is not None and tl.text:
            # 转换为秒
            time_limit = str(int(tl.text) // 1000)
        ml = testset.find('memory-limit')
        if ml is not None and ml.text:
            # 转换为 MB
            memory_limit = str(int(ml.text) // 1048576)

    # 输入/输出文件 (空表示标准输入输出)
    judging = root.find('judging')
    input_file = ''
    output_file = ''
    if judging is not None:
        input_file = judging.get('input-file', '')
        output_file = judging.get('output-file', '')

    # 构建描述
    description = build_description(extract_dir, root, 'chinese')
    input_desc = ''
    output_desc = ''

    # 从描述中分离输入/输出格式
    sections_dir = os.path.join(extract_dir, 'statement-sections', 'chinese')
    input_tex = get_text_content(os.path.join(sections_dir, 'input.tex'))
    output_tex = get_text_content(os.path.join(sections_dir, 'output.tex'))
    if input_tex:
        input_desc = tex_to_plain_text(input_tex)
    if output_tex:
        output_desc = tex_to_plain_text(output_tex)

    # 提示
    hint = build_hint(extract_dir, 'chinese')

    # 样例
    samples = get_samples(extract_dir, 'chinese')
    if not samples:
        # 如果 statement-sections 中没有，从 tests 中找 sample 测试
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

    # 题解代码
    solutions = get_solutions(extract_dir, root)

    # 构建 FPS XML
    fps = ET.Element('fps', {
        'version': '1.2',
        'url': 'https://github.com/zhblue/freeproblemset',
    })

    # 生成器版本
    generator = ET.SubElement(fps, 'generator')
    generator.set('name', 'polygon2fps')
    generator.set('url', 'https://github.com/your-username/polygon2fps')

    item = ET.SubElement(fps, 'item')

    # 标题
    title_elem = ET.SubElement(item, 'title')
    title_elem.text = escape_xml(title)

    # 时间限制
    tl_elem = ET.SubElement(item, 'time_limit')
    tl_elem.text = escape_xml(time_limit)
    tl_elem.set('unit', 's')

    # 内存限制
    ml_elem = ET.SubElement(item, 'memory_limit')
    ml_elem.text = escape_xml(memory_limit)
    ml_elem.set('unit', 'MB')

    # 描述
    desc_elem = ET.SubElement(item, 'description')
    desc_elem.text = escape_xml(description)

    # 输入格式
    input_elem = ET.SubElement(item, 'input')
    input_elem.text = escape_xml(input_desc)

    # 输出格式
    output_elem = ET.SubElement(item, 'output')
    output_elem.text = escape_xml(output_desc)

    # 样例
    for sample_in, sample_out in samples:
        si = ET.SubElement(item, 'sample_input')
        si.text = escape_xml(sample_in)
        so = ET.SubElement(item, 'sample_output')
        so.text = escape_xml(sample_out)

    # 测试数据 (排除已经是样例的)
    sample_set = set(samples)
    for test_in, test_out in all_tests:
        if (test_in, test_out) in sample_set:
            continue
        ti = ET.SubElement(item, 'test_input')
        ti.text = escape_xml(test_in)
        to = ET.SubElement(item, 'test_output')
        to.text = escape_xml(test_out)

    # 提示
    if hint:
        hint_elem = ET.SubElement(item, 'hint')
        hint_elem.text = escape_xml(hint)

    # 来源
    source_elem = ET.SubElement(item, 'source')
    short_name = root.get('short-name', '')
    source_elem.text = escape_xml(f'Polygon: {short_name}')

    # 题解代码
    for tag, src_type, code in solutions:
        sol_elem = ET.SubElement(item, 'solution')
        sol_elem.set('tag', tag)
        sol_elem.set('type', src_type)
        sol_elem.text = escape_xml(code)

    # 转换为美化后的 XML 字符串
    rough_string = ET.tostring(fps, encoding='utf-8', method='xml')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent='  ', encoding='utf-8')

    return pretty_xml.decode('utf-8')


def convert(polygon_zip: str, output_fps: Optional[str] = None):
    """
    主转换函数。
    
    Args:
        polygon_zip: polygon.codeforces 格式的 zip 文件路径
        output_fps: 输出的 FPS XML 文件路径，如果为 None 则自动生成
    """
    if not os.path.isfile(polygon_zip):
        print(f'错误: 文件不存在 - {polygon_zip}')
        sys.exit(1)

    # 创建临时目录
    tmp_dir = tempfile.mkdtemp(prefix='polygon2fps_')
    try:
        print(f'正在解压: {polygon_zip}')
        extract_zip(polygon_zip, tmp_dir)

        print('正在解析 problem.xml...')
        root = parse_problem_xml(tmp_dir)

        print('正在构建 FPS XML...')
        fps_xml = build_fps_xml(root, tmp_dir)

        # 确定输出文件名
        if output_fps is None:
            base_name = os.path.splitext(os.path.basename(polygon_zip))[0]
            output_fps = os.path.join(os.path.dirname(polygon_zip), f'{base_name}.fps.xml')

        # 写入文件
        with open(output_fps, 'w', encoding='utf-8') as f:
            f.write(fps_xml)

        print(f'转换完成! 输出文件: {output_fps}')
        print(f'文件大小: {os.path.getsize(output_fps):,} 字节')

    except Exception as e:
        print(f'转换失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    polygon_zip = sys.argv[1]
    output_fps = sys.argv[2] if len(sys.argv) > 2 else None
    convert(polygon_zip, output_fps)


if __name__ == '__main__':
    main()
