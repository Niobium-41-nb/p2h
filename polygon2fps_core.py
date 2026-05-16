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
from xml.dom import minidom
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
    text = re.sub(r'(?<!\\)%.*', '', text)
    text = text.replace('\\ldots', '...')
    text = text.replace('\\mid', '|')
    text = text.replace('\\&', '&')
    text = text.replace('\\cdot', '·')
    text = text.replace('\\le', '≤')
    text = text.replace('\\ge', '≥')
    text = text.replace('\\lt', '<')
    text = text.replace('\\gt', '>')
    text = text.replace('\\times', '×')
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textbf\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\textit\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\texttt\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\$\$\$', '$', text)
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


def build_hint(extract_dir: str, lang: str = 'chinese') -> str:
    """构建提示/题解"""
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)
    tutorial_file = os.path.join(sections_dir, 'tutorial.tex')
    tutorial_content = get_text_content(tutorial_file)
    if tutorial_content:
        return tex_to_plain_text(tutorial_content)

    html_path = os.path.join(extract_dir, 'statements', '.html', lang, 'tutorial.html')
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


def get_solutions(extract_dir: str, root: ET.Element) -> List[Tuple[str, str, str]]:
    """获取题解代码"""
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
    """构建 FPS XML 字符串"""
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
    all_tests = get_all_tests(extract_dir, root)

    fps = ET.Element('fps', {
        'version': '1.2',
        'url': 'https://github.com/zhblue/freeproblemset',
    })

    generator = ET.SubElement(fps, 'generator')
    generator.set('name', 'polygon2fps')
    generator.set('url', 'https://github.com/your-username/polygon2fps')

    item = ET.SubElement(fps, 'item')

    title_elem = ET.SubElement(item, 'title')
    title_elem.text = escape_xml(title)

    tl_elem = ET.SubElement(item, 'time_limit')
    tl_elem.text = escape_xml(time_limit)
    tl_elem.set('unit', 's')

    ml_elem = ET.SubElement(item, 'memory_limit')
    ml_elem.text = escape_xml(memory_limit)
    ml_elem.set('unit', 'MB')

    desc_elem = ET.SubElement(item, 'description')
    desc_elem.text = escape_xml(description)

    input_elem = ET.SubElement(item, 'input')
    input_elem.text = escape_xml(input_desc)

    output_elem = ET.SubElement(item, 'output')
    output_elem.text = escape_xml(output_desc)

    for sample_in, sample_out in samples:
        si = ET.SubElement(item, 'sample_input')
        si.text = escape_xml(sample_in)
        so = ET.SubElement(item, 'sample_output')
        so.text = escape_xml(sample_out)

    sample_set = set(samples)
    for test_in, test_out in all_tests:
        if (test_in, test_out) in sample_set:
            continue
        ti = ET.SubElement(item, 'test_input')
        ti.text = escape_xml(test_in)
        to = ET.SubElement(item, 'test_output')
        to.text = escape_xml(test_out)

    source_elem = ET.SubElement(item, 'source')
    short_name = root.get('short-name', '')
    source_elem.text = escape_xml(f'Polygon: {short_name}')

    rough_string = ET.tostring(fps, encoding='utf-8', method='xml')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent='  ', encoding='utf-8')

    return pretty_xml.decode('utf-8')


def convert(polygon_zip: str, output_fps: Optional[str] = None,
            progress_callback=None) -> str:
    """
    主转换函数。

    Args:
        polygon_zip: polygon.codeforces 格式的 zip 文件路径
        output_fps: 输出的 FPS XML 文件路径
        progress_callback: 进度回调函数，接收 (stage, message) 参数

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

        fps_xml = build_fps_xml(root, tmp_dir)

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
