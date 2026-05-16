#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS (Fresh Problem Set) / Hydro 格式转换工具

将 polygon.codeforces.com 导出的题目压缩包转换为：
  - FPS 格式（.fps.xml）：兼容 HUSTOJ、HydroOJ 等
  - Hydro 格式（.zip）：兼容 HydroOJ 导入规范

用法:
    # 图形界面模式
    python polygon2fps.py

    # 命令行模式（FPS 格式）
    python polygon2fps.py fps <polygon_zip_file> [output_fps_file]

    # 命令行模式（Hydro 格式）
    python polygon2fps.py hydro <polygon_zip_file> <output_dir>

示例:
    python polygon2fps.py
    python polygon2fps.py fps hzau-2026-problem1-20linux.zip
    python polygon2fps.py fps hzau-2026-problem1-20linux.zip output.xml
    python polygon2fps.py hydro hzau-2026-problem1-20linux.zip ./hydro_problems
"""

import sys
import os

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

        else:
            print(f'错误: 未知命令 "{cmd}"')
            print_usage()
            sys.exit(1)


if __name__ == '__main__':
    main()
