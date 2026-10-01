#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS / Hydro / HOJ 格式转换工具 - 图形界面版（支持批量转换）

用法:
    python polygon2fps_gui.py
"""

import os
import re
import sys
import threading
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 导入核心转换模块
from polygon2fps_core import convert as convert_to_fps
from polygon2hydro_core import convert_to_hydro
from polygon2hoj_core import (convert_to_hoj, convert_batch_to_hoj,
                              HojOptions, HOJ_LANGUAGES, HOJ_DIFFICULTIES)


def _log_tag(stage, message: str) -> str:
    """根据进度回调内容选择日志颜色（错误 / 警告 / 普通）"""
    if stage is not None and stage < 0:
        return 'error'
    text = message or ''
    if text.startswith('⚠') or text.startswith('[警告]'):
        return 'warn'
    return 'info'


class Polygon2FPSApp:
    """Polygon → FPS / Hydro / HOJ 转换 GUI 应用程序（支持批量转换）"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Polygon → FPS / Hydro / HOJ 格式转换工具")
        # 窗口尺寸根据屏幕自适应（HOJ 选项面板较高）
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{min(920, sw - 60)}x{min(980, sh - 80)}')
        self.root.minsize(760, 560)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('vista' if 'vista' in self.style.theme_names() else 'clam')

        # 变量
        self.input_files = []           # 待转换文件列表
        self.output_dir = tk.StringVar()
        self.output_format = tk.StringVar(value='fps')  # 'fps' / 'hydro' / 'hoj'
        self.max_test_data_mb = tk.StringVar(value='0')  # FPS 测试数据大小上限（MB），0 = 不限制
        self.is_converting = False

        # HOJ 转换选项
        self.hoj_max_mb = tk.StringVar(value='0')
        self.hoj_author = tk.StringVar(value='')
        self.hoj_auth = tk.StringVar(value='1 - 公开')
        self.hoj_type = tk.StringVar(value='0 - ACM')
        self.hoj_difficulty = tk.StringVar(value=HOJ_DIFFICULTIES[0])
        self.hoj_case_mode = tk.StringVar(value='default')
        self.hoj_tags = tk.StringVar(value='')
        self.hoj_problem_id = tk.StringVar(value='')
        self.hoj_languages = tk.StringVar(value=', '.join(HOJ_LANGUAGES))
        self.hoj_merge = tk.BooleanVar(value=True)

        self._build_ui()
        self._center_window()

    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _build_ui(self):
        """构建界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 标题 =====
        title_label = ttk.Label(
            main_frame,
            text="Polygon Codeforces → FPS / Hydro / HOJ 格式转换",
            font=('微软雅黑', 13, 'bold'),
        )
        title_label.pack(pady=(0, 8))

        # 保存 limit_frame 引用供 _on_format_changed 使用
        self.limit_frame = None

        # ===== 输出格式选择 =====
        format_frame = ttk.LabelFrame(main_frame, text="输出格式", padding=8)
        format_frame.pack(fill=tk.X, pady=(0, 6))

        format_row = ttk.Frame(format_frame)
        format_row.pack(fill=tk.X)

        ttk.Radiobutton(
            format_row,
            text="FPS 格式（.fps.xml）— 兼容 HUSTOJ、HydroOJ 等",
            variable=self.output_format,
            value='fps',
            command=self._on_format_changed,
        ).pack(anchor=tk.W, pady=(0, 2))

        ttk.Radiobutton(
            format_row,
            text="Hydro 格式（.zip）— 兼容 HydroOJ 导入规范",
            variable=self.output_format,
            value='hydro',
            command=self._on_format_changed,
        ).pack(anchor=tk.W, pady=(0, 2))

        ttk.Radiobutton(
            format_row,
            text="HOJ 格式（.zip）— 兼容 HOJ 后台“导入题目”",
            variable=self.output_format,
            value='hoj',
            command=self._on_format_changed,
        ).pack(anchor=tk.W)

        # ===== 输入文件列表 =====
        input_frame = ttk.LabelFrame(main_frame, text="输入文件（支持多选）", padding=8)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # 按钮行
        btn_row = ttk.Frame(input_frame)
        btn_row.pack(fill=tk.X, pady=(0, 4))

        ttk.Button(btn_row, text="添加文件...", command=self._browse_input).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="添加文件夹...", command=self._browse_folder).pack(side=tk.LEFT, padx=(0, 4))
        self.remove_btn = ttk.Button(btn_row, text="移除选中", command=self._remove_selected, state='disabled')
        self.remove_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.clear_btn = ttk.Button(btn_row, text="清空列表", command=self._clear_list, state='disabled')
        self.clear_btn.pack(side=tk.LEFT)

        # 文件列表（带滚动条）
        list_frame = ttk.Frame(input_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            font=('Consolas', 10),
            height=4,
            bg='#1e1e1e',
            fg='#d4d4d4',
            selectbackground='#264f78',
            selectforeground='#ffffff',
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self._on_selection_changed)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        # 文件数量标签
        self.count_label = ttk.Label(input_frame, text="共 0 个文件", foreground='gray')
        self.count_label.pack(anchor=tk.W, pady=(2, 0))

        # ===== 与格式相关的选项区（FPS / HOJ 各一个面板） =====
        self.specific_frame = ttk.Frame(main_frame)
        self.specific_frame.pack(fill=tk.X)

        # ----- 测试数据大小限制（仅 FPS 格式） -----
        self.limit_frame = ttk.LabelFrame(self.specific_frame, text="测试数据大小限制", padding=8)
        self.limit_frame.pack(fill=tk.X, pady=(0, 6))

        limit_row = ttk.Frame(self.limit_frame)
        limit_row.pack(fill=tk.X)

        ttk.Label(limit_row, text="最多包含").pack(side=tk.LEFT)

        self.limit_spinbox = ttk.Spinbox(
            limit_row,
            from_=0, to=1000,
            textvariable=self.max_test_data_mb,
            width=6,
        )
        self.limit_spinbox.pack(side=tk.LEFT, padx=(4, 4))

        ttk.Label(limit_row, text="MB 的测试数据（超出部分将被截断，0=不限制）").pack(side=tk.LEFT)

        self.limit_hint_label = ttk.Label(
            self.limit_frame,
            text="提示：大多数 OJ 平台上传限制为 50MB~100MB，如遇上传失败可在此限制测试数据大小",
            foreground='gray',
            font=('微软雅黑', 8),
        )
        self.limit_hint_label.pack(anchor=tk.W, pady=(2, 0))

        # ----- HOJ 选项（仅 HOJ 格式） -----
        self.hoj_frame = ttk.LabelFrame(self.specific_frame, text="HOJ 导入选项", padding=8)
        self._build_hoj_options(self.hoj_frame)

        # ===== 输出目录选择 =====
        output_frame = ttk.LabelFrame(main_frame, text="输出目录", padding=8)
        output_frame.pack(fill=tk.X, pady=(0, 6))

        output_row = ttk.Frame(output_frame)
        output_row.pack(fill=tk.X)

        self.output_entry = ttk.Entry(output_row, textvariable=self.output_dir, state='readonly')
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        ttk.Button(output_row, text="浏览...", command=self._browse_output).pack(side=tk.RIGHT)

        self.output_hint_label = ttk.Label(
            output_frame,
            text="输出文件将保存在此目录，文件名自动生成为 {原文件名}.fps.xml",
            foreground='gray',
        )
        self.output_hint_label.pack(anchor=tk.W, pady=(4, 0))

        # ===== 转换按钮 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(2, 6))

        self.convert_btn = ttk.Button(
            btn_frame,
            text="开始转换",
            command=self._start_convert,
            style='Accent.TButton',
        )
        self.convert_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 尝试设置强调按钮样式
        try:
            self.style.configure('Accent.TButton', font=('微软雅黑', 10, 'bold'))
        except Exception:
            pass

        # ===== 进度条 =====
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        self.status_label = ttk.Label(progress_frame, text="就绪", foreground='gray')
        self.status_label.pack(anchor=tk.W, pady=(2, 0))

        # ===== 日志输出 =====
        log_frame = ttk.LabelFrame(main_frame, text="转换日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            state='disabled',
            height=6,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_config('info', foreground='#d4d4d4')
        self.log_text.tag_config('success', foreground='#4ec9b0')
        self.log_text.tag_config('error', foreground='#f44747')
        self.log_text.tag_config('warn', foreground='#dcdcaa')
        self.log_text.tag_config('header', foreground='#569cd6', font=('Consolas', 9, 'bold'))

    def _build_hoj_options(self, parent: ttk.LabelFrame):
        """构建 HOJ 选项面板（紧凑两列布局，控制在 5 行以内以保证小屏幕上不裁切日志区）"""
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(3, weight=1)

        def pair(r, label1, widget1, label2=None, widget2=None):
            ttk.Label(parent, text=label1).grid(row=r, column=0, sticky=tk.W, padx=(0, 4), pady=2)
            widget1.grid(row=r, column=1, sticky=tk.EW, pady=2)
            if label2 is not None:
                ttk.Label(parent, text=label2).grid(row=r, column=2, sticky=tk.W,
                                                    padx=(10, 4), pady=2)
                widget2.grid(row=r, column=3, sticky=tk.EW, pady=2)

        pair(0, '题目作者', ttk.Entry(parent, textvariable=self.hoj_author),
             '展示 ID', ttk.Entry(parent, textvariable=self.hoj_problem_id))
        pair(1, '题目权限',
             ttk.Combobox(parent, textvariable=self.hoj_auth, state='readonly',
                          values=['1 - 公开', '2 - 隐藏', '3 - 比赛中']),
             '题目类型',
             ttk.Combobox(parent, textvariable=self.hoj_type, state='readonly',
                          values=['0 - ACM', '1 - OI']))
        pair(2, '题目难度',
             ttk.Combobox(parent, textvariable=self.hoj_difficulty, state='readonly',
                          values=list(HOJ_DIFFICULTIES)),
             '用例模式',
             ttk.Combobox(parent, textvariable=self.hoj_case_mode, state='readonly',
                          values=['default', 'ergodic_without_error',
                                  'subtask_lowest', 'subtask_average']))

        # 第 4 行：标签 + 合并开关
        ttk.Label(parent, text='标签').grid(row=3, column=0, sticky=tk.W, padx=(0, 4), pady=2)
        ttk.Entry(parent, textvariable=self.hoj_tags).grid(
            row=3, column=1, sticky=tk.EW, pady=2)
        ttk.Checkbutton(parent, text='合并为单个 ZIP', variable=self.hoj_merge).grid(
            row=3, column=2, columnspan=2, sticky=tk.W, padx=(10, 0), pady=2)

        # 第 5 行：支持语言 + 测试数据上限
        ttk.Label(parent, text='支持语言').grid(row=4, column=0, sticky=tk.W, padx=(0, 4), pady=(2, 0))
        ttk.Entry(parent, textvariable=self.hoj_languages).grid(
            row=4, column=1, sticky=tk.EW, pady=(2, 0))
        tail = ttk.Frame(parent)
        tail.grid(row=4, column=2, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(2, 0))
        ttk.Label(tail, text='数据上限').pack(side=tk.LEFT)
        ttk.Spinbox(tail, from_=0, to=1000, textvariable=self.hoj_max_mb, width=5).pack(
            side=tk.LEFT, padx=(4, 4))
        ttk.Label(tail, text='MB（0 = 不限制）').pack(side=tk.LEFT)

    def _on_format_changed(self):
        """格式切换时的界面调整"""
        fmt = self.output_format.get()

        # 更新输出目录提示
        if fmt == 'fps':
            hint = "输出文件将保存在此目录，文件名自动生成为 {原文件名}.fps.xml"
        elif fmt == 'hydro':
            hint = "每个题目将创建独立目录并打包为 {题目名}.zip"
        else:
            hint = "每个题目生成 {题目短名}.hoj.zip（填了展示 ID 则用 ID）；勾选“合并为单个 ZIP”时输出 hoj_batch_时间戳.zip"
        self.output_hint_label.configure(text=hint)

        # 显示/隐藏与格式相关的选项面板
        self.limit_frame.pack_forget()
        self.hoj_frame.pack_forget()
        if fmt == 'fps':
            self.limit_frame.pack(fill=tk.X, pady=(0, 6))
        elif fmt == 'hoj':
            self.hoj_frame.pack(fill=tk.X, pady=(0, 6))

    def _log(self, message: str, tag: str = 'info'):
        """向日志区域添加消息"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n', tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.root.update_idletasks()

    def _update_file_count(self, missing: int = 0):
        """更新文件数量显示"""
        count = len(self.input_files)
        text = f"共 {count} 个文件"
        if missing:
            text += f"（其中 {missing} 个文件已不存在，请移除后重试）"
        self.count_label.configure(text=text, foreground='#f44747' if missing else 'gray')
        self.clear_btn.configure(state='normal' if count > 0 else 'disabled')
        self.remove_btn.configure(state='disabled')

    def _refresh_file_list(self):
        """刷新文件列表显示

        列表里的文件可能已被移动或删除（比如选完文件后又把它挪走），
        这里必须容错，否则 os.path.getsize 会直接抛 FileNotFoundError。
        """
        self.file_listbox.delete(0, tk.END)
        missing = 0
        for i, f in enumerate(self.input_files, start=1):
            name = os.path.basename(f)
            try:
                size_str = self._format_size(os.path.getsize(f))
                text = f"  {i:3d}. {name}  ({size_str})"
                is_missing = False
            except OSError:
                missing += 1
                text = f"  {i:3d}. {name}  (文件不存在)"
                is_missing = True
            self.file_listbox.insert(tk.END, text)
            if is_missing:
                self.file_listbox.itemconfig(tk.END, foreground='#f44747')
        self._update_file_count(missing)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f'{size_bytes} B'
        elif size_bytes < 1024 * 1024:
            return f'{size_bytes / 1024:.1f} KB'
        else:
            return f'{size_bytes / 1024 / 1024:.1f} MB'

    def _on_selection_changed(self, event):
        """列表选中状态变化"""
        selected = self.file_listbox.curselection()
        self.remove_btn.configure(state='normal' if selected else 'disabled')

    def _browse_input(self):
        """浏览添加多个输入文件"""
        paths = filedialog.askopenfilenames(
            title="选择 Polygon 格式的 ZIP 文件（可多选）",
            filetypes=[("ZIP 文件", "*.zip"), ("所有文件", "*.*")],
        )
        if not paths:
            return

        added = 0
        for path in paths:
            if path not in self.input_files:
                self.input_files.append(path)
                added += 1

        if added > 0:
            self._refresh_file_list()
            self._log(f'已添加 {added} 个文件', 'info')
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(paths[0]))

    def _browse_folder(self):
        """浏览文件夹，添加其中所有 zip 文件"""
        folder = filedialog.askdirectory(title="选择包含 Polygon ZIP 文件的文件夹")
        if not folder:
            return

        try:
            entries = sorted(os.listdir(folder))
        except OSError as exc:
            messagebox.showerror("错误", f"无法读取文件夹:\n{folder}\n\n{exc}")
            return

        added = 0
        for f in entries:
            if f.lower().endswith('.zip'):
                full_path = os.path.join(folder, f)
                if full_path not in self.input_files:
                    self.input_files.append(full_path)
                    added += 1

        if added > 0:
            self._refresh_file_list()
            self._log(f'从文件夹添加了 {added} 个 ZIP 文件', 'info')
            if not self.output_dir.get():
                self.output_dir.set(folder)

    def _remove_selected(self):
        """移除选中的文件"""
        selected = self.file_listbox.curselection()
        if not selected:
            return
        for idx in reversed(selected):
            self.input_files.pop(idx)
        self._refresh_file_list()
        self._log(f'已移除 {len(selected)} 个文件', 'info')

    def _clear_list(self):
        """清空文件列表"""
        if not self.input_files:
            return
        if messagebox.askyesno("确认", f"确定要清空文件列表（共 {len(self.input_files)} 个文件）吗？"):
            self.input_files.clear()
            self._refresh_file_list()
            self._log('已清空文件列表', 'info')

    def _browse_output(self):
        """浏览输出目录"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)

    def _start_convert(self):
        """开始批量转换"""
        if not self.input_files:
            messagebox.showwarning("提示", "请先添加要转换的 ZIP 文件")
            return

        # 文件可能在加入列表后被移动/删除，这里先备一次，避免转到一半才报错
        missing = [f for f in self.input_files if not os.path.isfile(f)]
        if missing:
            self._refresh_file_list()
            preview = '\n'.join(os.path.basename(f) for f in missing[:5])
            if len(missing) > 5:
                preview += f'\n...（共 {len(missing)} 个）'
            self._log(f'❌ 以下文件已不存在，请从列表移除后重试：\n{preview}', 'error')
            messagebox.showerror("错误", f"以下文件已不存在，请从列表移除后重试:\n\n{preview}")
            return

        out_dir = self.output_dir.get()
        if not out_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        if not os.path.isdir(out_dir):
            messagebox.showerror("错误", f"输出目录不存在:\n{out_dir}")
            return

        fmt = self.output_format.get()
        fmt_name = {'fps': 'FPS', 'hydro': 'Hydro', 'hoj': 'HOJ'}.get(fmt, fmt.upper())

        # 禁用按钮
        self.convert_btn.configure(state='disabled')
        self.is_converting = True

        # 清空日志
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')

        # 记录开始信息
        self._log('=' * 56, 'header')
        self._log(f'  Polygon → {fmt_name} 批量转换', 'header')
        self._log('=' * 56, 'header')
        self._log(f'输出格式: {fmt_name}', 'info')
        self._log(f'文件总数: {len(self.input_files)}', 'info')
        self._log(f'输出目录: {out_dir}', 'info')
        self._log('测试数据: Polygon 的生成型测试点会用包内生成器动态生成，'
                  '答案由 tag="main" 的主标程算出', 'info')
        self._log('-' * 56, 'info')

        # 解析测试数据大小限制
        try:
            max_mb = float(self.max_test_data_mb.get())
            if max_mb < 0:
                max_mb = 0
        except ValueError:
            max_mb = 0

        if fmt == 'hydro':
            max_mb = 0  # Hydro 格式不需要此限制

        # 组装 HOJ 选项
        hoj_options = None
        hoj_merge = False
        if fmt == 'hoj':
            hoj_options = self._collect_hoj_options()
            hoj_merge = self.hoj_merge.get()
            self._log(f'题目权限: {self.hoj_auth.get()} | 类型: {self.hoj_type.get()}'
                      f' | 难度: {self.hoj_difficulty.get()}', 'info')
            self._log(f'用例模式: {self.hoj_case_mode.get()}'
                      f' | 作者: {hoj_options.author or "（由导入者决定）"}', 'info')
            if hoj_options.tags:
                self._log(f'标签: {", ".join(hoj_options.tags)}', 'info')
            self._log('题面样例将写入 examples，全部测试点写入 samples（题解/教程不导出）', 'info')
            self._log(f'输出方式: {"合并为单个 ZIP" if hoj_merge else "每题一个 ZIP"}', 'info')

        # 在后台线程中执行批量转换
        thread = threading.Thread(
            target=self._do_batch_convert,
            args=(list(self.input_files), out_dir, fmt, max_mb, hoj_options, hoj_merge),
            daemon=True,
        )
        thread.start()

    def _collect_hoj_options(self) -> HojOptions:
        """从界面控件读取 HOJ 转换选项"""
        def to_int(value: str, default: int = 0) -> int:
            """从 '4 - 普及+/提高-' 这类下拉框中取出前面的数字"""
            match = re.match(r'\s*(-?\d+)', value or '')
            return int(match.group(1)) if match else default

        try:
            max_mb = float(self.hoj_max_mb.get())
            if max_mb < 0:
                max_mb = 0
        except ValueError:
            max_mb = 0

        return HojOptions(
            author=self.hoj_author.get().strip(),
            auth=to_int(self.hoj_auth.get(), 1),
            problem_type=to_int(self.hoj_type.get(), 0),
            difficulty=to_int(self.hoj_difficulty.get(), 0),
            judge_case_mode=self.hoj_case_mode.get().strip() or 'default',
            tags=[t.strip() for t in self.hoj_tags.get().replace('，', ',').split(',') if t.strip()],
            languages=[l.strip() for l in self.hoj_languages.get().replace('，', ',').split(',') if l.strip()],
            problem_id=self.hoj_problem_id.get().strip(),
            max_test_data_mb=max_mb,
        )

    def _do_batch_convert(self, files: list, out_dir: str, fmt: str,
                          max_mb: float = 0, hoj_options: HojOptions = None,
                          hoj_merge: bool = False):
        """执行批量转换（后台线程）"""
        total = len(files)
        success_count = 0
        fail_count = 0

        # ---- HOJ 合并模式：所有题目打包成一个 zip ----
        if fmt == 'hoj' and hoj_merge:
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            out_zip = os.path.join(out_dir, f'hoj_batch_{stamp}.zip')

            def cb(stage, message):
                if stage < 0:
                    self.root.after(0, self._log, f'  {message}', 'error')
                else:
                    self.root.after(0, self._update_progress, max(0, min(stage, 100)), message)

            try:
                result, errors = convert_batch_to_hoj(files, out_zip, hoj_options, cb)
                success_count = total - len(errors)
                fail_count = len(errors)
                for err in errors:
                    self.root.after(0, self._log, f'  ⚠ {err}', 'warn')
                if success_count > 0:
                    self.root.after(0, self._log,
                                    f'  ✅ 已生成 HOJ 导入包: {os.path.basename(result)}'
                                    f'（{success_count} 题）', 'success')
            except Exception as e:
                fail_count = total
                self.root.after(0, self._log, f'  ❌ 合并转换失败: {e}', 'error')

            self.root.after(0, self._on_batch_complete, total, success_count, fail_count)
            return

        # ---- 逐题转换 ----
        for idx, file_path in enumerate(files):
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]

            # 更新进度
            overall_progress = int((idx / total) * 100)
            self.root.after(0, self._update_progress, overall_progress,
                            f'[{idx + 1}/{total}] 正在转换: {file_name}')

            try:
                if fmt == 'fps':
                    out_path = os.path.join(out_dir, f'{base_name}.fps.xml')

                    def cb(stage, message):
                        self.root.after(0, self._log, f'  {message}',
                                        _log_tag(stage, message))

                    convert_to_fps(file_path, out_path, progress_callback=cb,
                                   max_test_data_mb=max_mb)
                    self.root.after(0, self._log,
                                    f'  ✅ [{idx + 1}/{total}] {file_name} → {base_name}.fps.xml', 'success')
                elif fmt == 'hoj':
                    def cb(stage, message):
                        self.root.after(0, self._log, f'  {message}',
                                        _log_tag(stage, message))

                    out_path = convert_to_hoj(file_path, out_dir, hoj_options, cb)
                    self.root.after(0, self._log,
                                    f'  ✅ [{idx + 1}/{total}] {file_name} → {os.path.basename(out_path)}', 'success')
                else:  # hydro
                    def cb(stage, message):
                        self.root.after(0, self._log, f'  {message}',
                                        _log_tag(stage, message))

                    convert_to_hydro(file_path, out_dir, cb)
                    self.root.after(0, self._log,
                                    f'  ✅ [{idx + 1}/{total}] {file_name} → Hydro 格式', 'success')

                success_count += 1
            except Exception as e:
                fail_count += 1
                self.root.after(0, self._log,
                                f'  ❌ [{idx + 1}/{total}] {file_name} - 失败: {e}', 'error')

        # 完成
        self.root.after(0, self._on_batch_complete, total, success_count, fail_count)

    def _on_batch_complete(self, total: int, success: int, fail: int):
        """批量转换完成"""
        self._log('-' * 56, 'info')
        if fail == 0:
            self._log(f'✅ 全部完成！共 {total} 个文件，全部转换成功', 'success')
            self.progress_bar['value'] = 100
            self.status_label.configure(
                text=f'转换完成！成功: {success}，失败: {fail}',
                foreground='#4ec9b0',
            )
        else:
            self._log(f'⚠️ 转换完成。成功: {success}，失败: {fail}', 'warn')
            self.progress_bar['value'] = 100
            self.status_label.configure(
                text=f'转换完成（部分失败）。成功: {success}，失败: {fail}',
                foreground='#dcdcaa',
            )

        self.convert_btn.configure(state='normal')
        self.is_converting = False

    def _update_progress(self, progress: int, message: str):
        """更新进度显示（在主线程中执行）"""
        self.progress_bar['value'] = progress
        self.status_label.configure(text=message, foreground='#d4d4d4')
        self._log(f'▶ {message}', 'info')

    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    root = tk.Tk()
    app = Polygon2FPSApp(root)
    app.run()


if __name__ == '__main__':
    main()
