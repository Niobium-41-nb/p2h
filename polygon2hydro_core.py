#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → Hydro 格式核心转换模块

Hydro 题目格式（目录结构）:
    problem-id/
    ├── problem.md          # 题目描述（Markdown + YAML Front Matter）
    ├── testdata/           # 测试数据
    │   ├── 1.in
    │   ├── 1.out
    │   ├── 2.in
    │   └── 2.out
    └── (可选) extra_files/
"""

import os
import re
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple, Callable

from polygon_tests import load_test_data, failure_message
import polygon_statement


# ========== 复用 polygon2fps_core 的通用函数 ==========

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
    """将 LaTeX 内容转换为纯文本（数学公式降级为 Unicode）"""
    return polygon_statement.tex_to_plain_text(tex_content)


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


def tex_to_markdown(tex_content: str) -> str:
    """将 LaTeX 内容转换为 Markdown（数学公式原样保留，供 KaTeX 渲染）"""
    return polygon_statement.tex_to_markdown(tex_content)


# ========== Hydro 特定函数 ==========

def get_problem_info(root: ET.Element) -> dict:
    """从 problem.xml 提取题目基本信息"""
    info = {}

    # 标题
    names_elem = root.find('names')
    title = ''
    if names_elem is not None:
        for name in names_elem.findall('name'):
            if name.get('language') == 'chinese':
                title = name.get('value', '')
                break
        if not title:
            title = names_elem.find('name').get('value', '')
    info['title'] = title

    # 短名称（用作目录名）
    info['short_name'] = root.get('short-name', title)

    # 时间限制（毫秒）
    time_limit_ms = 1000
    memory_limit_bytes = 256 * 1024 * 1024
    testset = root.find('.//testset')
    if testset is not None:
        tl = testset.find('time-limit')
        if tl is not None and tl.text:
            time_limit_ms = int(tl.text)
        ml = testset.find('memory-limit')
        if ml is not None and ml.text:
            memory_limit_bytes = int(ml.text)
    info['time_limit_ms'] = time_limit_ms
    info['memory_limit_bytes'] = memory_limit_bytes

    return info


def build_hydro_description(extract_dir: str, root: ET.Element, lang: str = 'chinese') -> str:
    """构建 Hydro 格式的题目描述（Markdown）"""
    sections_dir = os.path.join(extract_dir, 'statement-sections', lang)
    parts = []

    # 题目背景/描述
    legend_file = os.path.join(sections_dir, 'legend.tex')
    legend_content = get_text_content(legend_file)
    if legend_content:
        parts.append(tex_to_markdown(legend_content))

    # 输入格式
    input_file = os.path.join(sections_dir, 'input.tex')
    input_content = get_text_content(input_file)
    if input_content:
        parts.append('## 输入格式\n\n' + tex_to_markdown(input_content))

    # 输出格式
    output_file = os.path.join(sections_dir, 'output.tex')
    output_content = get_text_content(output_file)
    if output_content:
        parts.append('## 输出格式\n\n' + tex_to_markdown(output_content))

    # 样例（在描述中引用）
    samples = get_hydro_samples(extract_dir, lang)
    if samples:
        sample_section = '## 样例\n'
        for i, (inp, out) in enumerate(samples, start=1):
            sample_section += f'\n### 样例 #{i}\n\n'
            sample_section += '**输入：**\n\n```\n' + inp + '\n```\n\n'
            sample_section += '**输出：**\n\n```\n' + out + '\n```\n'
        parts.append(sample_section)

    # 提示/注释
    notes_file = os.path.join(sections_dir, 'notes.tex')
    notes_content = get_text_content(notes_file)
    if notes_content:
        parts.append('## 提示\n\n' + tex_to_markdown(notes_content))

    if parts:
        return '\n\n'.join(parts)

    # 回退到 HTML
    html_path = os.path.join(extract_dir, 'statements', '.html', lang, 'problem.html')
    html_content = get_text_content(html_path)
    if html_content:
        return html_to_plain_text(html_content)

    return ''


def get_hydro_samples(extract_dir: str, lang: str = 'chinese') -> List[Tuple[str, str]]:
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


def get_hydro_all_tests(extract_dir: str, root: ET.Element, log=None,
                        generate_tests: bool = True) -> List[Tuple[bytes, bytes]]:
    """获取所有测试数据（返回原始字节，保证与 Polygon 判题结果一致）

    Polygon 的生成型测试点（method="generated"）需要运行生成器才能得到输入、
    运行主标程才能得到答案，这部分由 polygon_tests 自动完成。
    """
    result = load_test_data(extract_dir, root, generate=generate_tests, log=log)
    if result.test_count and not result.tests:
        raise ValueError(failure_message(result))
    if log:
        log(result.summary())
    return [(t.input, t.answer) for t in result.tests]


def build_problem_md(info: dict, description: str) -> str:
    """构建 problem.md 文件内容"""
    time_ms = info['time_limit_ms']
    memory_bytes = info['memory_limit_bytes']

    # 时间格式：1s 或 1000ms
    if time_ms >= 1000 and time_ms % 1000 == 0:
        time_str = f'{time_ms // 1000}s'
    else:
        time_str = f'{time_ms}ms'

    # 内存格式：256MB
    memory_mb = memory_bytes // (1024 * 1024)
    memory_str = f'{memory_mb}MB'

    lines = []
    lines.append('---')
    lines.append(f'title: "{info["title"]}"')
    lines.append(f'time: "{time_str}"')
    lines.append(f'memory: "{memory_str}"')
    lines.append('---')
    lines.append('')
    lines.append(description)
    lines.append('')

    return '\n'.join(lines)


def convert_to_hydro(polygon_zip: str, output_dir: str,
                     progress_callback: Optional[Callable] = None,
                     generate_tests: bool = True) -> str:
    """
    将 Polygon 格式题目转换为 Hydro 格式。

    Args:
        polygon_zip: polygon.codeforces 格式的 zip 文件路径
        output_dir: 输出目录（每个题目会创建子目录）
        progress_callback: 进度回调函数
        generate_tests: 包内缺失的测试点（生成器生成的输入、主标程算出的答案）
            是否现场动态生成，默认开启

    Returns:
        输出目录路径
    """
    if not os.path.isfile(polygon_zip):
        raise FileNotFoundError(f'文件不存在: {polygon_zip}')

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    if progress_callback:
        progress_callback(0, '正在解压...')

    tmp_dir = tempfile.mkdtemp(prefix='polygon2hydro_')
    try:
        extract_zip(polygon_zip, tmp_dir)

        if progress_callback:
            progress_callback(20, '正在解析 problem.xml...')

        root = parse_problem_xml(tmp_dir)
        info = get_problem_info(root)

        if progress_callback:
            progress_callback(40, '正在构建题目描述...')

        # 构建 problem.md
        description = build_hydro_description(tmp_dir, root, 'chinese')
        problem_md = build_problem_md(info, description)

        # 创建题目目录
        problem_dir_name = info['short_name']
        problem_dir = os.path.join(output_dir, problem_dir_name)
        os.makedirs(problem_dir, exist_ok=True)

        # 写入 problem.md
        md_path = os.path.join(problem_dir, 'problem.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(problem_md)

        if progress_callback:
            progress_callback(60, '正在准备测试数据...')

        def log(message: str) -> None:
            if progress_callback:
                progress_callback(60, message)

        # 读取测试数据（包内缺失的生成型测试点会现场运行生成器与主标程）
        all_tests = get_hydro_all_tests(tmp_dir, root, log=log,
                                        generate_tests=generate_tests)

        testdata_dir = os.path.join(problem_dir, 'testdata')
        os.makedirs(testdata_dir, exist_ok=True)

        for i, (inp, out) in enumerate(all_tests, start=1):
            # 按原始字节写入，保留结尾空格与换行
            with open(os.path.join(testdata_dir, f'{i}.in'), 'wb') as f:
                f.write(inp)
            with open(os.path.join(testdata_dir, f'{i}.out'), 'wb') as f:
                f.write(out)

        if progress_callback:
            progress_callback(80, '正在打包为 ZIP...')

        # 打包为 ZIP（Hydro 导入需要 ZIP 格式）
        zip_path = os.path.join(output_dir, f'{problem_dir_name}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加 problem.md
            zf.write(md_path, os.path.join(problem_dir_name, 'problem.md'))
            # 添加测试数据
            for i in range(1, len(all_tests) + 1):
                in_name = f'{i}.in'
                out_name = f'{i}.out'
                in_full = os.path.join(testdata_dir, in_name)
                out_full = os.path.join(testdata_dir, out_name)
                if os.path.isfile(in_full):
                    zf.write(in_full, os.path.join(problem_dir_name, 'testdata', in_name))
                if os.path.isfile(out_full):
                    zf.write(out_full, os.path.join(problem_dir_name, 'testdata', out_name))

        if progress_callback:
            progress_callback(100, f'转换完成! 输出: {zip_path}')

        return zip_path

    except Exception as e:
        if progress_callback:
            progress_callback(-1, f'转换失败: {e}')
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
