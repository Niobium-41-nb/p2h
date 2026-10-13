#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互题 / 通信题（run-twice）转换的回归测试

直接运行：python polygon_interactive_tests.py

覆盖：
* ``polygon_tests.detect_interactor``：从 ``<assets><interactor>`` /
  ``<judging run-count>`` / ``<interactor><runs>`` 判断交互题与通信题；
* 交互题不再跑主标程算答案（答案留空、不跑 checker）；
* ``polygon2hoj_core``：判题模式映射 + 交互器源码 / judgeExtraFile 导出；
* ``polygon2hydro_core``：Hydro 的 testdata/config.yaml + 交互器打包，通信题给出警告。

测试用包是现场拼出来的最小 Polygon 包（正例走 import 中的样例包会被 .gitignore 忽略）。
"""

import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import polygon_tests
import polygon2hoj_core as hoj
import polygon2hydro_core as hydro

INTERACTOR_CPP = '''#include "testlib.h"
int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    int a = inf.readInt();
    tout << a << "\\n";
    std::cout << a << std::endl;
    int ans = 0;
    ouf.readInt(ans);
    quitf(ans == a ? _ok : _wa, "done");
}
'''

TESTLIB_H = '// minimal testlib stand-in for tests\n'

PROBLEM_XML = '''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<problem revision="1" short-name="comm-demo">
    <names>
        <name language="chinese" value="通信题示例"/>
    </names>
    <judging run-count="{run_count}">
        <testset name="tests">
            <time-limit>1000</time-limit>
            <memory-limit>268435456</memory-limit>
            <test-count>2</test-count>
            <input-path-pattern>tests/%02d</input-path-pattern>
            <answer-path-pattern>tests/%02d.a</answer-path-pattern>
            <tests>
                <test method="manual" sample="true"/>
                <test method="manual"/>
            </tests>
        </testset>
    </judging>
    <files>
        <resources>
            <file path="files/testlib.h" type="h.g++"/>
        </resources>
        <executables>
            <executable>
                <source path="files/interactor.cpp" type="cpp.g++"/>
                <binary path="files/interactor.exe" type="exe.win32"/>
            </executable>
        </executables>
    </files>
    <assets>
        <interactor>
            <source path="files/interactor.cpp" type="cpp.g++"/>
            <binary path="files/interactor.exe" type="exe.win32"/>
            {runs}
        </interactor>
        <solutions>
            <solution tag="main">
                <source path="solutions/solution.cpp" type="cpp.g++"/>
                <binary path="solutions/solution.exe" type="exe.win32"/>
            </solution>
        </solutions>
    </assets>
</problem>
'''

RUNS_BOTH = '<runs><run>1</run><run>2</run></runs>'


def _write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(path, mode, **({} if isinstance(data, bytes) else {'encoding': 'utf-8'})) as f:
        f.write(data)


def make_polygon_zip(directory: str, run_count: int = 2, runs: str = RUNS_BOTH,
                     with_interactor: bool = True) -> str:
    """拼一个最小的 Polygon 导出包（两道手工测试、无 .a 答案）"""
    root = os.path.join(directory, f'pkg{run_count}{len(runs)}')
    xml = PROBLEM_XML.format(run_count=run_count, runs=runs)
    if not with_interactor:
        # 去掉交互器节点（保留 assets/solutions）
        start = xml.index('<interactor>')
        end = xml.index('</interactor>') + len('</interactor>')
        xml = xml[:start] + xml[end:]
    _write(os.path.join(root, 'problem.xml'), xml)
    _write(os.path.join(root, 'files', 'interactor.cpp'), INTERACTOR_CPP)
    _write(os.path.join(root, 'files', 'testlib.h'), TESTLIB_H)
    _write(os.path.join(root, 'solutions', 'solution.cpp'), 'int main() { return 0; }\n')
    # 用二进制写入，避免 Windows 下文本模式把 \n 翻成 \r\n（测试要校验原始字节）
    _write(os.path.join(root, 'tests', '01'), b'5\n')
    _write(os.path.join(root, 'tests', '02'), b'7\n')
    _write(os.path.join(root, 'statement-sections', 'chinese', 'legend.tex'), '题目描述')
    _write(os.path.join(root, 'statement-sections', 'chinese', 'input.tex'), '输入一行')
    _write(os.path.join(root, 'statement-sections', 'chinese', 'output.tex'), '输出一行')

    zip_path = root + '.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                zf.write(full, os.path.relpath(full, root).replace(os.sep, '/'))
    return zip_path


def read_root(zip_path: str) -> ET.Element:
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract('problem.xml', tmp)
    return ET.parse(os.path.join(tmp, 'problem.xml')).getroot()


# ========== 识别 ==========

def test_detect_communication():
    """run-count=2 + 交互器 runs 1,2 → Polygon 的通信题（run-twice）"""
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work, run_count=2, runs=RUNS_BOTH)
        info = polygon_tests.detect_interactor(read_root(zip_path))
        assert info is not None
        assert info.is_communication and info.second_run_interactive
        assert info.language == 'C++', info
        assert info.run_count == 2 and info.runs == (1, 2), info
        print('  ok  通信题：run_count=2 + <runs>1,2 → communication')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_detect_second_invocation_off():
    """run-count=2 但交互器只在第一轮调用（Polygon 关掉了 Interactive second invocation）"""
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work, run_count=2, runs='')
        info = polygon_tests.detect_interactor(read_root(zip_path))
        assert info.is_communication and not info.second_run_interactive, info
        mode, warns = hoj.resolve_judge_mode(hoj.HojOptions(), info)
        assert mode == hoj.JUDGE_MODE_COMMUNICATION, mode
        assert warns and 'second invocation' in warns[0], warns
        print('  ok  run-count=2 但第二轮不跑交互器 → communication + 警告')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_detect_plain_interactive():
    """run-count=1 → 普通交互题，用 HOJ 的 interactive 判题"""
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work, run_count=1, runs='')
        info = polygon_tests.detect_interactor(read_root(zip_path))
        assert info is not None and not info.is_communication, info
        mode, warns = hoj.resolve_judge_mode(hoj.HojOptions(), info)
        assert (mode, warns) == (hoj.JUDGE_MODE_INTERACTIVE, []), (mode, warns)
        print('  ok  交互题：run_count=1 → interactive')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_no_interactor_is_default():
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work, with_interactor=False)
        info = polygon_tests.detect_interactor(read_root(zip_path))
        assert info is None, info
        assert hoj.resolve_judge_mode(hoj.HojOptions(), info) == (hoj.JUDGE_MODE_DEFAULT, [])
        print('  ok  没有交互器 → default')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_forced_mode_without_interactor_falls_back():
    mode, warns = hoj.resolve_judge_mode(hoj.HojOptions(judge_mode='communication'), None)
    assert mode == hoj.JUDGE_MODE_DEFAULT, mode
    assert warns and '没有交互器' in warns[0], warns
    print('  ok  强制 communication 但包内无交互器 → 退回 default 并警告')


def test_forced_default_wins_over_interactor():
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work)
        info = polygon_tests.detect_interactor(read_root(zip_path))
        mode, warns = hoj.resolve_judge_mode(hoj.HojOptions(judge_mode='default'), info)
        assert mode == hoj.JUDGE_MODE_DEFAULT, mode
        assert warns and '交互题' in warns[0], warns
        print('  ok  显式指定 default：忽略交互器并提示')
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ========== 测试数据 ==========

def test_load_test_data_keeps_answers_empty():
    """交互题不跑主标程：答案留空、不跑 checker，也不因缺 .a 而跳过测试点"""
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work)
        extract = os.path.join(work, 'extract')
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract)
        result = polygon_tests.load_test_data(extract, ET.parse(
            os.path.join(extract, 'problem.xml')).getroot())
        assert result.interactive and len(result.tests) == 2, result
        assert all(t.answer == b'' for t in result.tests), result.tests
        assert result.generated_answers == 0 and not result.skipped
        assert result.tests[0].input == b'5\n'
        print('  ok  交互题答案留空，不跑主标程 / checker')
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ========== HOJ 导出 ==========

def test_hoj_communication_export():
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work)
        out_dir = os.path.join(work, 'out')
        os.makedirs(out_dir)
        hoj_zip = hoj.convert_to_hoj(zip_path, out_dir, hoj.HojOptions())

        with zipfile.ZipFile(hoj_zip) as zf:
            names = zf.namelist()
            assert 'comm-demo.json' in names, names
            assert 'comm-demo/1.in' in names and 'comm-demo/1.out' in names, names
            assert zf.read('comm-demo/1.out') == b'', '交互题的 .out 应为空文件'
            data = json.loads(zf.read('comm-demo.json').decode('utf-8'))

        assert data['judgeMode'] == 'communication', data['judgeMode']
        problem = data['problem']
        assert problem['judgeMode'] == 'communication'
        assert problem['spjLanguage'] == 'C++', problem['spjLanguage']
        assert problem['spjCode'] == INTERACTOR_CPP
        assert data['judgeExtraFile'] == {'testlib.h': TESTLIB_H}, data['judgeExtraFile']
        assert len(data['samples']) == 2
        print('  ok  HOJ 通信题包：judgeMode/spjLanguage/spjCode/judgeExtraFile 齐全')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_hoj_default_export_has_no_interactive_fields():
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work, with_interactor=False)
        out_dir = os.path.join(work, 'out')
        os.makedirs(out_dir)
        hoj_zip = hoj.convert_to_hoj(zip_path, out_dir,
                                     hoj.HojOptions(judge_mode='default'))
        with zipfile.ZipFile(hoj_zip) as zf:
            data = json.loads(zf.read('comm-demo.json').decode('utf-8'))
        assert data['judgeMode'] == 'default'
        assert 'judgeExtraFile' not in data
        assert 'spjCode' not in data['problem'] and 'spjLanguage' not in data['problem']
        print('  ok  普通题不写交互/通信字段')
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ========== Hydro ==========

def test_hydro_interactive_config():
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work, run_count=1, runs='')
        with zipfile.ZipFile(zip_path) as zf:
            extract = os.path.join(work, 'extract')
            zf.extractall(extract)
        info = polygon_tests.detect_interactor(ET.parse(
            os.path.join(extract, 'problem.xml')).getroot())
        config, files, warns = hydro.build_hydro_interactive_config(
            extract, info, 1000, 256)
        assert not warns, warns
        assert 'type: interactive' in config and 'interactor: interactor.cc' in config, config
        assert 'judge_extra_files' in config and '- testlib.h' in config, config
        assert 'time: 1000ms' in config and 'memory: 256m' in config, config
        assert files['interactor.cc'].decode('utf-8') == INTERACTOR_CPP
        assert files['testlib.h'].decode('utf-8') == TESTLIB_H
        print('  ok  Hydro 交互题：config.yaml + interactor.cc + testlib.h')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_hydro_communication_is_rejected():
    work = tempfile.mkdtemp()
    try:
        zip_path = make_polygon_zip(work)
        with zipfile.ZipFile(zip_path) as zf:
            extract = os.path.join(work, 'extract')
            zf.extractall(extract)
        info = polygon_tests.detect_interactor(ET.parse(
            os.path.join(extract, 'problem.xml')).getroot())
        config, files, warns = hydro.build_hydro_interactive_config(extract, info)
        assert config == '' and files == {}, (config, files)
        assert warns and 'communication' in warns[0] or 'run-twice' in warns[0], warns
        print('  ok  Hydro 不表达通信题（run-twice），给出警告')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'\n全部 {len(tests)} 组测试通过')


if __name__ == '__main__':
    main()
