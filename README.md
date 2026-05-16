# Polygon Codeforces → FPS / Hydro 格式转换工具

将 [Polygon Codeforces](https://polygon.codeforces.com) 格式的题目转换为 **FPS (Fresh Problem Set)** 或 **Hydro** 格式，兼容 HUSTOJ、HydroOJ 等在线评测系统。

## 快速开始

### 图形界面（推荐）

```bash
python polygon2fps.py
```

1. 选择输出格式（FPS / Hydro）
2. 点击 **"添加文件..."** 或 **"添加文件夹..."** 导入 Polygon 格式的 `.zip` 文件
3. 选择输出目录
4. 点击 **"开始转换"**，等待批量完成

### 命令行

```bash
# 启动图形界面
python polygon2fps.py

# FPS 格式转换
python polygon2fps.py fps problem.zip
python polygon2fps.py fps problem.zip output.xml

# Hydro 格式转换
python polygon2fps.py hydro problem.zip ./hydro_problems
```

## 项目结构

```
├── polygon2fps.py              # 统一入口（无参数→GUI，有参数→CLI）
├── polygon2fps_core.py          # FPS 核心转换逻辑
├── polygon2fps_gui.py           # 图形用户界面（基于 tkinter）
├── polygon2hydro_core.py        # Hydro 核心转换逻辑
├── README.md                    # 本文件
└── .gitignore
```

## 功能特性

- ✅ **双格式支持** — 同时支持 FPS 和 Hydro 两种输出格式
- ✅ **批量转换** — 支持多文件选择、文件夹导入，一键批量转换
- ✅ **图形界面** — 文件列表管理、进度条、日志输出，操作直观
- ✅ **命令行支持** — 适合批量处理或集成到脚本
- ✅ **完整转换** — 题目名称、描述、输入/输出格式、样例、测试数据
- ✅ **LaTeX 处理** — 自动将 LaTeX 数学公式转换为纯文本 / Markdown
- ✅ **CDATA 安全** — FPS 格式使用 `<![CDATA[...]]>` 包裹，避免 XML 转义问题
- ✅ **标准兼容** — 输出符合 FPS 1.2 标准和 Hydro 导入规范

## 输出格式说明

### FPS 格式

输出为 `.fps.xml` 文件，兼容 HUSTOJ、HydroOJ 等支持 FPS 标准的 OJ 系统。

| FPS 标签 | 说明 | 来源 |
|----------|------|------|
| `<title>` | 题目名称 | `problem.xml` → `<name>` |
| `<time_limit>` | 时间限制 (秒) | `problem.xml` → `<time-limit>` |
| `<memory_limit>` | 内存限制 (MB) | `problem.xml` → `<memory-limit>` |
| `<description>` | 题目描述 | `statement-sections/*/legend.tex` |
| `<input>` | 输入格式 | `statement-sections/*/input.tex` |
| `<output>` | 输出格式 | `statement-sections/*/output.tex` |
| `<sample_input/output>` | 样例数据 | `statement-sections/*/example.*` |
| `<test_input/output>` | 测试数据 | `tests/` 目录 |
| `<source>` | 题目来源 | `problem.xml` → `short-name` |

### Hydro 格式

输出为 HydroOJ 兼容的 ZIP 包，内部结构：

```
problem-id/
├── problem.md          # Markdown 描述（含 YAML Front Matter）
└── testdata/           # 测试数据
    ├── 1.in
    ├── 1.out
    ├── 2.in
    └── 2.out
```

`problem.md` 包含 YAML 元信息（标题、时间限制、内存限制）和 Markdown 格式的题目描述，可直接导入 HydroOJ。

> **注意**：题解代码（solution）和教程（tutorial）**不会**被转换到输出中。

## 依赖

- Python 3.6+
- tkinter（Python 标准库，通常已预装）
- 无需第三方库

## 许可证

MIT
