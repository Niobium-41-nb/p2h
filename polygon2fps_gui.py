#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon Codeforces → FPS 格式转换工具 - 图形界面版

用法:
    python polygon2fps_gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 导入核心转换模块
from polygon2fps_core import convert


class Polygon2FPSApp:
    """Polygon → FPS 转换 GUI 应用程序"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Polygon → FPS 格式转换工具")
        self.root.geometry("720x540")
        self.root.minsize(600, 450)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('vista' if 'vista' in self.style.theme_names() else 'clam')

        # 变量
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.auto_output = tk.BooleanVar(value=True)
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
            text="Polygon Codeforces → FPS 格式转换",
            font=('微软雅黑', 14, 'bold'),
        )
        title_label.pack(pady=(0, 16))

        # ===== 输入文件选择 =====
        input_frame = ttk.LabelFrame(main_frame, text="输入文件", padding=8)
        input_frame.pack(fill=tk.X, pady=(0, 8))

        input_row = ttk.Frame(input_frame)
        input_row.pack(fill=tk.X)

        self.input_entry = ttk.Entry(input_row, textvariable=self.input_path, state='readonly')
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        ttk.Button(input_row, text="浏览...", command=self._browse_input).pack(side=tk.RIGHT)

        ttk.Label(input_frame, text="选择 polygon.codeforces 格式的 .zip 文件",
                  foreground='gray').pack(anchor=tk.W, pady=(4, 0))

        # ===== 输出文件选择 =====
        output_frame = ttk.LabelFrame(main_frame, text="输出文件", padding=8)
        output_frame.pack(fill=tk.X, pady=(0, 8))

        # 自动输出
        auto_frame = ttk.Frame(output_frame)
        auto_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Checkbutton(
            auto_frame,
            text="自动生成输出文件名（与输入文件同名，后缀 .fps.xml）",
            variable=self.auto_output,
            command=self._toggle_output_entry,
        ).pack(anchor=tk.W)

        # 手动输出
        output_row = ttk.Frame(output_frame)
        output_row.pack(fill=tk.X)

        self.output_entry = ttk.Entry(output_row, textvariable=self.output_path, state='disabled')
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.output_browse_btn = ttk.Button(
            output_row, text="浏览...", command=self._browse_output, state='disabled'
        )
        self.output_browse_btn.pack(side=tk.RIGHT)

        # ===== 转换按钮 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(8, 8))

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
        progress_frame.pack(fill=tk.X, pady=(0, 8))

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
            height=12,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_config('info', foreground='#d4d4d4')
        self.log_text.tag_config('success', foreground='#4ec9b0')
        self.log_text.tag_config('error', foreground='#f44747')
        self.log_text.tag_config('warn', foreground='#dcdcaa')

        # ===== 底部信息 =====
        footer = ttk.Label(
            main_frame,
            text="支持 polygon.codeforces.com 导出的题目压缩包 → HUSTOJ/FPS 兼容格式",
            foreground='gray',
            font=('微软雅黑', 8),
        )
        footer.pack(pady=(4, 0))

    def _log(self, message: str, tag: str = 'info'):
        """向日志区域添加消息"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n', tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.root.update_idletasks()

    def _browse_input(self):
        """浏览输入文件"""
        path = filedialog.askopenfilename(
            title="选择 Polygon 格式的 ZIP 文件",
            filetypes=[("ZIP 文件", "*.zip"), ("所有文件", "*.*")],
        )
        if path:
            self.input_path.set(path)
            # 自动生成输出路径
            if self.auto_output.get():
                base = os.path.splitext(os.path.basename(path))[0]
                out_dir = os.path.dirname(path)
                self.output_path.set(os.path.join(out_dir, f'{base}.fps.xml'))

    def _browse_output(self):
        """浏览输出文件"""
        path = filedialog.asksaveasfilename(
            title="保存 FPS XML 文件",
            defaultextension=".xml",
            filetypes=[("XML 文件", "*.xml"), ("所有文件", "*.*")],
        )
        if path:
            self.output_path.set(path)

    def _toggle_output_entry(self):
        """切换输出文件输入框状态"""
        if self.auto_output.get():
            self.output_entry.configure(state='disabled')
            self.output_browse_btn.configure(state='disabled')
            # 自动生成
            inp = self.input_path.get()
            if inp:
                base = os.path.splitext(os.path.basename(inp))[0]
                out_dir = os.path.dirname(inp)
                self.output_path.set(os.path.join(out_dir, f'{base}.fps.xml'))
        else:
            self.output_entry.configure(state='normal')
            self.output_browse_btn.configure(state='normal')

    def _progress_callback(self, progress: int, message: str):
        """进度回调函数"""
        self.root.after(0, self._update_progress, progress, message)

    def _update_progress(self, progress: int, message: str):
        """更新进度显示（在主线程中执行）"""
        if progress < 0:
            # 错误
            self.progress_bar['value'] = 0
            self.status_label.configure(text=message, foreground='#f44747')
            self._log(f'❌ {message}', 'error')
            self.convert_btn.configure(state='normal')
            self.is_converting = False
        elif progress >= 100:
            # 完成
            self.progress_bar['value'] = 100
            self.status_label.configure(text=message, foreground='#4ec9b0')
            self._log(f'✅ {message}', 'success')
            self.convert_btn.configure(state='normal')
            self.is_converting = False
        else:
            self.progress_bar['value'] = progress
            self.status_label.configure(text=message, foreground='#d4d4d4')
            self._log(f'▶ {message}', 'info')

    def _start_convert(self):
        """开始转换"""
        # 验证输入
        inp = self.input_path.get()
        if not inp:
            messagebox.showwarning("提示", "请先选择输入的 ZIP 文件")
            return

        if not os.path.isfile(inp):
            messagebox.showerror("错误", f"输入文件不存在:\n{inp}")
            return

        if not inp.lower().endswith('.zip'):
            if not messagebox.askyesno("确认", "选择的文件不是 .zip 格式，确定继续吗？"):
                return

        # 确定输出路径
        if self.auto_output.get():
            base = os.path.splitext(os.path.basename(inp))[0]
            out_dir = os.path.dirname(inp)
            out_path = os.path.join(out_dir, f'{base}.fps.xml')
            self.output_path.set(out_path)
        else:
            out_path = self.output_path.get()
            if not out_path:
                messagebox.showwarning("提示", "请指定输出文件路径")
                return

        # 禁用按钮
        self.convert_btn.configure(state='disabled')
        self.is_converting = True

        # 清空日志
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')

        # 记录开始信息
        self._log('=' * 50, 'info')
        self._log('Polygon → FPS 格式转换', 'info')
        self._log('=' * 50, 'info')
        self._log(f'输入文件: {inp}', 'info')
        self._log(f'输出文件: {out_path}', 'info')
        self._log('-' * 50, 'info')

        # 在后台线程中执行转换
        thread = threading.Thread(
            target=self._do_convert,
            args=(inp, out_path),
            daemon=True,
        )
        thread.start()

    def _do_convert(self, inp: str, out_path: str):
        """执行转换（后台线程）"""
        try:
            convert(inp, out_path, progress_callback=self._progress_callback)
        except Exception as e:
            self._progress_callback(-1, f'{e}')

    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    root = tk.Tk()
    app = Polygon2FPSApp(root)
    app.run()


if __name__ == '__main__':
    main()
