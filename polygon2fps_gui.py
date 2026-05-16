#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS / Hydro 格式转换工具 - 图形界面版（支持批量转换）

用法:
    python polygon2fps_gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 导入核心转换模块
from polygon2fps_core import convert as convert_to_fps
from polygon2hydro_core import convert_to_hydro


class Polygon2FPSApp:
    """Polygon → FPS / Hydro 转换 GUI 应用程序（支持批量转换）"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Polygon → FPS / Hydro 格式转换工具")
        self.root.geometry("780x640")
        self.root.minsize(640, 480)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('vista' if 'vista' in self.style.theme_names() else 'clam')

        # 变量
        self.input_files = []           # 待转换文件列表
        self.output_dir = tk.StringVar()
        self.output_format = tk.StringVar(value='fps')  # 'fps' 或 'hydro'
        self.max_test_data_mb = tk.StringVar(value='50')  # 测试数据大小上限（MB）
        self.is_converting = False

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
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 标题 =====
        title_label = ttk.Label(
            main_frame,
            text="Polygon Codeforces → FPS / Hydro 格式转换",
            font=('微软雅黑', 14, 'bold'),
        )
        title_label.pack(pady=(0, 12))

        # 保存 limit_frame 引用供 _on_format_changed 使用
        self.limit_frame = None

        # ===== 输出格式选择 =====
        format_frame = ttk.LabelFrame(main_frame, text="输出格式", padding=8)
        format_frame.pack(fill=tk.X, pady=(0, 8))

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
        ).pack(anchor=tk.W)

        # ===== 输入文件列表 =====
        input_frame = ttk.LabelFrame(main_frame, text="输入文件（支持多选）", padding=8)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

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

        # ===== 测试数据大小限制（仅 FPS 格式） =====
        self.limit_frame = ttk.LabelFrame(main_frame, text="测试数据大小限制", padding=8)
        self.limit_frame.pack(fill=tk.X, pady=(0, 8))

        limit_row = ttk.Frame(self.limit_frame)
        limit_row.pack(fill=tk.X)

        ttk.Label(limit_row, text="最多包含").pack(side=tk.LEFT)

        self.limit_spinbox = ttk.Spinbox(
            limit_row,
            from_=1, to=1000,
            textvariable=self.max_test_data_mb,
            width=6,
        )
        self.limit_spinbox.pack(side=tk.LEFT, padx=(4, 4))

        ttk.Label(limit_row, text="MB 的测试数据（超出部分将被截断，0=不限制）").pack(side=tk.LEFT)

        self.limit_hint_label = ttk.Label(
            self.limit_frame,
            text="提示：大多数 OJ 平台上传限制为 50MB~100MB，建议将 FPS 文件控制在 50MB 以内",
            foreground='gray',
            font=('微软雅黑', 8),
        )
        self.limit_hint_label.pack(anchor=tk.W, pady=(2, 0))

        # ===== 输出目录选择 =====
        output_frame = ttk.LabelFrame(main_frame, text="输出目录", padding=8)
        output_frame.pack(fill=tk.X, pady=(0, 8))

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
        btn_frame.pack(fill=tk.X, pady=(4, 8))

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
            height=10,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_config('info', foreground='#d4d4d4')
        self.log_text.tag_config('success', foreground='#4ec9b0')
        self.log_text.tag_config('error', foreground='#f44747')
        self.log_text.tag_config('warn', foreground='#dcdcaa')
        self.log_text.tag_config('header', foreground='#569cd6', font=('Consolas', 9, 'bold'))

        # ===== 底部信息 =====
        footer = ttk.Label(
            main_frame,
            text="支持 polygon.codeforces.com 导出的题目压缩包 → FPS / Hydro 兼容格式",
            foreground='gray',
            font=('微软雅黑', 8),
        )
        footer.pack(pady=(2, 0))

    def _on_format_changed(self):
        """格式切换时的界面调整"""
        # 更新输出目录提示
        if self.output_format.get() == 'fps':
            hint = "输出文件将保存在此目录，文件名自动生成为 {原文件名}.fps.xml"
        else:
            hint = "每个题目将创建独立目录并打包为 {题目名}.zip"
        self.output_hint_label.configure(text=hint)

        # 显示/隐藏测试数据大小限制（仅 FPS 格式需要）
        if hasattr(self, 'limit_frame') and self.limit_frame is not None:
            if self.output_format.get() == 'fps':
                self.limit_frame.pack(fill=tk.X, pady=(0, 8), before=self.limit_frame.master.winfo_children()[-1])
            else:
                self.limit_frame.pack_forget()

    def _log(self, message: str, tag: str = 'info'):
        """向日志区域添加消息"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n', tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.root.update_idletasks()

    def _update_file_count(self):
        """更新文件数量显示"""
        count = len(self.input_files)
        self.count_label.configure(text=f"共 {count} 个文件")
        self.clear_btn.configure(state='normal' if count > 0 else 'disabled')
        self.remove_btn.configure(state='disabled')

    def _refresh_file_list(self):
        """刷新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for i, f in enumerate(self.input_files, start=1):
            name = os.path.basename(f)
            size = os.path.getsize(f)
            size_str = self._format_size(size)
            self.file_listbox.insert(tk.END, f"  {i:3d}. {name}  ({size_str})")
        self._update_file_count()

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

        added = 0
        for f in sorted(os.listdir(folder)):
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

        out_dir = self.output_dir.get()
        if not out_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        if not os.path.isdir(out_dir):
            messagebox.showerror("错误", f"输出目录不存在:\n{out_dir}")
            return

        fmt = self.output_format.get()
        fmt_name = 'FPS' if fmt == 'fps' else 'Hydro'

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

        # 在后台线程中执行批量转换
        thread = threading.Thread(
            target=self._do_batch_convert,
            args=(list(self.input_files), out_dir, fmt, max_mb),
            daemon=True,
        )
        thread.start()

    def _do_batch_convert(self, files: list, out_dir: str, fmt: str, max_mb: float = 0):
        """执行批量转换（后台线程）"""
        total = len(files)
        success_count = 0
        fail_count = 0

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
                    convert_to_fps(file_path, out_path, max_test_data_mb=max_mb)
                    self.root.after(0, self._log,
                                    f'  ✅ [{idx + 1}/{total}] {file_name} → {base_name}.fps.xml', 'success')
                else:  # hydro
                    convert_to_hydro(file_path, out_dir)
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
