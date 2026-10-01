#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键打包为 Windows 可执行文件（PyInstaller）

用法:
    python build_exe.py                       # 打包 GUI 版 + CLI 版（默认版本号取自 VERSION）
    python build_exe.py --version 1.2.3       # 指定版本号（写进文件名）
    python build_exe.py --gui-only            # 只打包 GUI 版

产物（dist/ 目录）:
    Polygon2FPS-v<版本>.exe        # 双击即用（GUI，无控制台窗口）
    Polygon2FPS-CLI-v<版本>.exe    # 命令行版（带控制台输出）

说明:
    * 两个 exe 用的是同一个入口 `polygon2fps.py`：无参数启动 GUI，带参数按 CLI 运行；
      GUI 版打包成 --windowed（不弹黑框），CLI 版打包成 --console（能打印进度与错误）。
    * 打包只依赖标准库（tkinter），不需要额外 hidden-import。
"""

import argparse
import os
import shutil
import subprocess
import sys

VERSION = '1.1.0'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRY = 'polygon2fps.py'


def _prepare_console() -> None:
    """Windows 控制台默认 GBK，打印 ✓ 这类字符会抛 UnicodeEncodeError"""
    for name in ('stdout', 'stderr'):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass


def ensure_pyinstaller() -> str:
    """确认 PyInstaller 可用，返回调用方式（模块名）"""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print('错误: 未安装 PyInstaller，请先执行:')
        print(f'  {os.path.basename(sys.executable)} -m pip install pyinstaller')
        sys.exit(1)
    return 'PyInstaller'


def build(module: str, name: str, windowed: bool, onefile: bool = True) -> str:
    """调用 PyInstaller 打包，返回生成的 exe 路径"""
    args = [sys.executable, '-m', module, '--noconfirm', '--clean']
    args.append('--onefile' if onefile else '--onedir')
    args.append('--windowed' if windowed else '--console')
    args += [
        '--name', name,
        '--distpath', os.path.join(BASE_DIR, 'dist'),
        '--workpath', os.path.join(BASE_DIR, 'build'),
        '--specpath', os.path.join(BASE_DIR, 'build'),
        ENTRY,
    ]
    print('\n>>> ' + ' '.join(args[1:]))
    result = subprocess.run(args, cwd=BASE_DIR)
    if result.returncode != 0:
        print(f'打包失败（退出码 {result.returncode}）')
        sys.exit(result.returncode)

    suffix = '.exe' if sys.platform == 'win32' else ''
    exe_path = os.path.join(BASE_DIR, 'dist', name + suffix)
    if not os.path.isfile(exe_path):
        print(f'打包似乎成功，但没找到产物: {exe_path}')
        sys.exit(1)
    size_mb = os.path.getsize(exe_path) / 1048576
    print(f'[OK] {os.path.relpath(exe_path, BASE_DIR)}  ({size_mb:.1f} MB)')
    return exe_path


def main():
    parser = argparse.ArgumentParser(description='把 p2h 打包为 exe')
    parser.add_argument('--version', default=VERSION, help=f'版本号（默认 {VERSION}）')
    parser.add_argument('--gui-only', action='store_true', help='只打包 GUI 版')
    parser.add_argument('--cli-only', action='store_true', help='只打包 CLI 版')
    parser.add_argument('--onedir', action='store_true',
                        help='生成目录版而非单文件版（启动更快，但要整个目录一起分发）')
    ns = parser.parse_args()

    _prepare_console()
    module = ensure_pyinstaller()
    version = ns.version.lstrip('v')
    onefile = not ns.onedir

    # 打包前清掉旧产物，避免把上一个版本混进发布资产
    for path in ('dist', 'build'):
        shutil.rmtree(os.path.join(BASE_DIR, path), ignore_errors=True)

    built = []
    if not ns.cli_only:
        built.append(build(module, f'Polygon2FPS-v{version}', windowed=True, onefile=onefile))
    if not ns.gui_only:
        built.append(build(module, f'Polygon2FPS-CLI-v{version}', windowed=False, onefile=onefile))

    print('\n完成，产物:')
    for path in built:
        print('  ' + os.path.relpath(path, BASE_DIR))


if __name__ == '__main__':
    main()
