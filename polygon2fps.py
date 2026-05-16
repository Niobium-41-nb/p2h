#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS (Fresh Problem Set) 格式转换工具

将 polygon.codeforces.com 导出的题目压缩包转换为 HUSTOJ / FPS 兼容的 XML 格式。

用法:
    # 图形界面模式
    python polygon2fps.py

    # 命令行模式
    python polygon2fps.py <polygon_zip_file> [output_fps_file]

示例:
    python polygon2fps.py
    python polygon2fps.py hzau-2026-problem1-20linux.zip
    python polygon2fps.py hzau-2026-problem1-20linux.zip output.xml
"""

import sys
import os

# 确保可以导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) == 1:
        # 无参数 → 启动 GUI
        try:
            from polygon2fps_gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f'错误: 无法启动图形界面 - {e}')
            print('请确保 tkinter 已安装，或使用命令行模式:')
            print(f'  python {sys.argv[0]} <polygon_zip_file>')
            sys.exit(1)
    else:
        # 有参数 → 命令行模式
        from polygon2fps_core import convert

        polygon_zip = sys.argv[1]
        output_fps = sys.argv[2] if len(sys.argv) > 2 else None

        try:
            result = convert(polygon_zip, output_fps)
            size = os.path.getsize(result)
            print(f'转换完成!')
            print(f'  输出文件: {result}')
            print(f'  文件大小: {size:,} 字节')
        except Exception as e:
            print(f'转换失败: {e}')
            sys.exit(1)


if __name__ == '__main__':
    main()
