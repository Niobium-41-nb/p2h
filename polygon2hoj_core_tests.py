#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""polygon2hoj_core 的回归测试（直接运行：python polygon2hoj_core_tests.py）

重点锁住「题目展示 ID 默认留空」这个约定：
* 不指定时输出的 json **不能**包含 problemId（HOJ 只在 problemId 为 null 时才
  用自增 id 自动分配 P<id>）；
* 也**不能**写成空字符串——HOJ 的 adminAddProblem 对空串会走唯一性校验，
  同一批导入的第二个题目直接报「problem_id [] already exists」；
* 显式指定（界面「展示 ID」/--problem-id）时才写入。
"""

import polygon2hoj_core as hoj

INFO = {
    'title': '钒钒的括号序列',
    'short_name': 'hzau-2026-problem4',
    'time_limit_ms': 1000,
    'memory_limit_mb': 256,
}
SECTIONS = {'description': 'd', 'input': 'i', 'output': 'o', 'hint': 'h'}
TESTS = [(b'1\n', b'1\n'), (b'2\n', b'2\n')]


def _problem(options=None):
    data = hoj.build_problem_json(INFO, SECTIONS, '', TESTS, options or hoj.HojOptions())
    return data['problem']


def test_blank_by_default():
    problem = _problem()
    assert 'problemId' not in problem, problem
    # 标题/来源仍然要有值
    assert problem['title'] == '钒钒的括号序列'
    assert problem['source'] == 'hzau-2026-problem4'
    print('  ok  默认不写 problemId（留空，交由 HOJ 自动分配）')


def test_blank_string_is_never_emitted():
    problem = _problem(hoj.HojOptions(problem_id='   '))
    assert 'problemId' not in problem, problem
    print('  ok  纯空白等同留空，不会写成 ""')


def test_explicit_id_is_written():
    problem = _problem(hoj.HojOptions(problem_id=' TESTID '))
    assert problem['problemId'] == 'TESTID'
    print('  ok  显式指定时写入 problemId')


def test_stat_key_falls_back_to_short_name():
    """展示 ID 留空时，打包用的文件名/文件夹名要退回 short-name，不能变成空。"""
    data = hoj.build_problem_json(INFO, SECTIONS, '', TESTS, hoj.HojOptions())
    stat_id = data['problem'].get('problemId') or INFO['short_name'] or 'problem'
    key = hoj._sanitize_key(stat_id)
    assert key == 'hzau-2026-problem4', key
    print('  ok  文件名/文件夹名退回 short-name')


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'\n全部 {len(tests)} 组测试通过')


if __name__ == '__main__':
    main()
