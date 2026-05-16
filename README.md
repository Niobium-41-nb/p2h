# Polygon Codeforces → FPS 格式转换工具

将 [Polygon Codeforces](https://polygon.codeforces.com) 格式的题目转换为 **FPS (Fresh Problem Set)** 格式，兼容 HUSTOJ、HydroOJ 等在线评测系统。

## 快速开始

### 图形界面（推荐）

```bash
python polygon2fps.py
```

**单文件转换：**
1. 点击 **"添加文件..."** 选择 Polygon 格式的 `.zip` 文件
2. 选择输出目录
3. 点击 **"开始转换"**

**批量转换：**
1. 点击 **"添加文件..."** 多选多个 `.zip` 文件，或点击 **"添加文件夹..."** 导入整个目录
2. 选择输出目录
3. 点击 **"开始转换"**，程序将依次转换所有题目

### 命令行

```bash
# 基本用法（自动生成输出文件名）
python polygon2fps.py problem.zip

# 指定输出文件名
python polygon2fps.py problem.zip output.xml
```

## 项目结构

```
├── polygon2fps.py          # 统一入口（无参数→GUI，有参数→CLI）
├── polygon2fps_core.py      # 核心转换逻辑
├── polygon2fps_gui.py       # 图形用户界面（基于 tkinter）
├── README.md                # 本文件
└── .gitignore
```

## 功能特性

- ✅ **批量转换** — 支持多文件选择、文件夹导入，一键批量转换
- ✅ **图形界面** — 文件列表管理、进度条、日志输出，操作直观
- ✅ **命令行支持** — 适合批量处理或集成到脚本
- ✅ **完整转换** — 题目名称、描述、输入/输出格式、样例、测试数据
- ✅ **LaTeX 处理** — 自动将 LaTeX 数学公式转换为纯文本
- ✅ **CDATA 安全** — 所有文本内容使用 `<![CDATA[...]]>` 包裹，避免 XML 转义问题
- ✅ **标准兼容** — 输出符合 FPS 1.2 标准，兼容主流 OJ 系统

## 转换内容

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

> **注意**：题解代码（solution）和教程（tutorial）**不会**被转换到 FPS 输出中。

## 依赖

- Python 3.6+
- tkinter（Python 标准库，通常已预装）
- 无需第三方库

## 许可证

MIT
