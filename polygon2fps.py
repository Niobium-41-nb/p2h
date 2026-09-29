#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS (Fresh Problem Set) / Hydro / HOJ 格式转换工具

将 polygon.codeforces.com 导出的题目压缩包转换为：
  - FPS 格式（.fps.xml）：兼容 HUSTOJ、HydroOJ 等
  - Hydro 格式（.zip）：兼容 HydroOJ 导入规范
  - HOJ 格式（.zip）：兼容 HOJ 导入规范（https://docs.hdoi.cn/use/import-problem）

用法:
    # 图形界面模式
    python polygon2fps.py

    # 命令行模式（FPS 格式）
    python polygon2fps.py fps <polygon_zip_file> [output_fps_file]

    # 命令行模式（Hydro 格式）
    python polygon2fps.py hydro <polygon_zip_file> <output_dir>

    # 命令行模式（HOJ 格式）
    python polygon2fps.py hoj <polygon_zip_file> [更多.zip ...] [-o 输出目录|输出.zip] [选项]

示例:
    python polygon2fps.py
    python polygon2fps.py fps hzau-2026-problem1-20linux.zip
    python polygon2fps.py fps hzau-2026-problem1-20linux.zip output.xml
    python polygon2fps.py hydro hzau-2026-problem1-20linux.zip ./hydro_problems
    python polygon2fps.py hoj hzau-2026-problem1-20linux.zip -o ./hoj_problems
    python polygon2fps.py hoj a.zip b.zip -o out.zip --merge --author admin --type oi
"""

import sys
import os
import re

# 确保可以导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_usage():
    """打印用法信息"""
    print(__doc__)


def main():
    if len(sys.argv) == 1:
        # 无参数 → 启动 GUI
        try:
            from polygon2fps_gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f'错误: 无法启动图形界面 - {e}')
            print('请确保 tkinter 已安装，或使用命令行模式:')
            print(f'  python {sys.argv[0]} fps <polygon_zip_file>')
            sys.exit(1)
    else:
        cmd = sys.argv[1].lower()

        if cmd == 'fps':
            # FPS 格式转换
            from polygon2fps_core import convert

            if len(sys.argv) < 3:
                print('错误: 缺少参数')
                print_usage()
                sys.exit(1)

            polygon_zip = sys.argv[2]
            output_fps = sys.argv[3] if len(sys.argv) > 3 else None

            try:
                result = convert(polygon_zip, output_fps)
                size = os.path.getsize(result)
                print(f'转换完成!')
                print(f'  输出文件: {result}')
                print(f'  文件大小: {size:,} 字节')
            except Exception as e:
                print(f'转换失败: {e}')
                sys.exit(1)

        elif cmd == 'hydro':
            # Hydro 格式转换
            from polygon2hydro_core import convert_to_hydro

            if len(sys.argv) < 4:
                print('错误: 缺少参数')
                print_usage()
                sys.exit(1)

            polygon_zip = sys.argv[2]
            output_dir = sys.argv[3]

            try:
                result = convert_to_hydro(polygon_zip, output_dir)
                size = os.path.getsize(result)
                print(f'转换完成!')
                print(f'  输出文件: {result}')
                print(f'  文件大小: {size:,} 字节')
            except Exception as e:
                print(f'转换失败: {e}')
                sys.exit(1)

        elif cmd == 'hoj':
            # HOJ 格式转换
            run_hoj_cli(sys.argv[2:])

        else:
            print(f'错误: 未知命令 "{cmd}"')
            print_usage()
            sys.exit(1)


def run_hoj_cli(args):
    """HOJ 格式命令行转换"""
    import argparse
    import datetime
    from polygon2hoj_core import (convert_to_hoj, convert_batch_to_hoj, HojOptions,
                                  AUTH_PUBLIC)

    parser = argparse.ArgumentParser(
        prog='polygon2fps.py hoj',
        description='将 Polygon 题目转换为 HOJ 导入格式',
    )
    parser.add_argument('inputs', nargs='+', help='Polygon zip 文件（可传多个，配合 --merge 合并）')
    parser.add_argument('-o', '--output', default=None,
                        help='非合并模式：输出目录（默认与输入文件同目录）；合并模式：输出 zip 路径')
    parser.add_argument('--merge', action='store_true',
                        help='将所有题目合并为一个 zip，便于在 HOJ 后台一次性导入')
    parser.add_argument('--author', default='', help='题目作者（留空则由导入者用户名作为作者）')
    parser.add_argument('--auth', type=int, default=AUTH_PUBLIC,
                        help='权限：1 公开 / 2 隐藏 / 3 比赛中（默认 1）')
    parser.add_argument('--type', dest='problem_type', choices=['acm', 'oi'], default='acm',
                        help='题目类型：acm / oi（默认 acm）')
    parser.add_argument('--difficulty', type=int, default=0,
                        help='难度：0 未设置 / 1 简单 / 2 中等 / 3 困难（默认 0）')
    parser.add_argument('--judge-case-mode', default='default',
                        help='用例模式：default / ergodic_without_error / subtask_lowest / subtask_average')
    parser.add_argument('--tags', default='', help='标签，逗号分隔')
    parser.add_argument('--problem-id', default='', help='题目展示 ID（默认使用 Polygon short-name）')
    parser.add_argument('--max-mb', type=float, default=0, help='测试数据大小上限（MB），0 = 不限制')

    ns = parser.parse_args(args)

    missing = [p for p in ns.inputs if not os.path.isfile(p)]
    if missing:
        print(f'错误: 文件不存在 - {", ".join(missing)}')
        print('提示: 输出目录/输出 zip 请用 -o 指定，例如：'
              'python polygon2fps.py hoj problem.zip -o ./out')
        sys.exit(1)

    options = HojOptions(
        author=ns.author,
        auth=ns.auth,
        problem_type=1 if ns.problem_type == 'oi' else 0,
        difficulty=ns.difficulty,
        judge_case_mode=ns.judge_case_mode,
        tags=[t for t in re.split(r'[,，]', ns.tags) if t.strip()],
        problem_id=ns.problem_id,
        max_test_data_mb=ns.max_mb,
    )

    def log(stage, message):
        if stage < 0:
            print(f'  ❌ {message}')
        else:
            print(f'  {message}')

    try:
        if ns.merge:
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            out_zip = ns.output
            if out_zip and not out_zip.lower().endswith('.zip'):
                # 未以 .zip 结尾，视为输出目录
                out_zip = os.path.join(out_zip, f'hoj_batch_{stamp}.zip')
            elif not out_zip:
                out_zip = f'hoj_batch_{stamp}.zip'
            result, errors = convert_batch_to_hoj(ns.inputs, out_zip, options, log)
            for err in errors:
                print(f'  ⚠ {err}')
        else:
            result = None
            for path in ns.inputs:
                print(f'[{os.path.basename(path)}]')
                out_dir = ns.output or os.path.dirname(os.path.abspath(path))
                result = convert_to_hoj(path, out_dir, options, log)

        size = os.path.getsize(result)
        print('转换完成!')
        print(f'  输出文件: {result}')
        print(f'  文件大小: {size:,} 字节')
    except Exception as e:
        print(f'转换失败: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
