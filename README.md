# Polygon Codeforces → FPS / Hydro / HOJ 格式转换工具

将 [Polygon Codeforces](https://polygon.codeforces.com) 格式的题目转换为 **FPS (Fresh Problem Set)**、**Hydro** 或 **HOJ** 格式，兼容 HUSTOJ、HydroOJ、HOJ 等在线评测系统。

## 快速开始

### 图形界面（推荐）

```bash
python polygon2fps.py
```

1. 选择输出格式（FPS / Hydro / HOJ）
2. 点击 **"添加文件..."** 或 **"添加文件夹..."** 导入 Polygon 格式的 `.zip` 文件
3. 选择输出目录（HOJ 格式还可设置作者 / 权限 / 类型 / 难度 / 标签等）
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

# HOJ 格式转换
python polygon2fps.py hoj problem.zip -o ./hoj_problems
python polygon2fps.py hoj a.zip b.zip -o batch.zip --merge --author admin --type oi --tags 测试,贪心
```

HOJ 子命令参数：

| 参数 | 说明 |
|------|------|
| `-o, --output` | 输出目录（默认与输入文件同目录）；`--merge` 时既可为目录也可为 `.zip` 路径 |
| `--merge` | 将多个题目合并为一个 zip，便于在 HOJ 后台一次性导入 |
| `--author` | 题目作者（留空则由导入者用户名作为作者） |
| `--auth` | 权限：`1` 公开（默认）/ `2` 隐藏 / `3` 比赛中 |
| `--type` | 题目类型：`acm`（默认）/ `oi`（自动为每个测试点分配 100 分总分） |
| `--difficulty` | 难度：`0` 未设置（默认）/ `1` 简单 / `2` 中等 / `3` 困难 |
| `--judge-case-mode` | 用例模式：`default`（默认）/ `ergodic_without_error` / `subtask_lowest` / `subtask_average` |
| `--tags` | 标签，逗号分隔 |
| `--problem-id` | 题目展示 ID（默认使用 Polygon `short-name`） |
| `--max-mb` | 测试数据大小上限（MB），`0` = 不限制 |

## 项目结构

```
├── polygon2fps.py              # 统一入口（无参数→GUI，有参数→CLI）
├── polygon2fps_core.py         # FPS 核心转换逻辑
├── polygon2fps_gui.py          # 图形用户界面（基于 tkinter）
├── polygon2hydro_core.py       # Hydro 核心转换逻辑
├── polygon2hoj_core.py         # HOJ 核心转换逻辑
├── README.md                   # 本文件
└── .gitignore
```

## 功能特性

- ✅ **三种格式支持** — 同时支持 FPS、Hydro、HOJ 输出格式
- ✅ **批量转换** — 支持多文件选择、文件夹导入，一键批量转换
- ✅ **合并导入包** — HOJ 格式可将多题合并为单个 zip 一次性导入
- ✅ **图形界面** — 文件列表管理、进度条、日志输出，操作直观
- ✅ **命令行支持** — 适合批量处理或集成到脚本
- ✅ **完整转换** — 题目名称、描述、输入/输出格式、样例、测试数据
- ✅ **LaTeX 处理** — 数学公式原样保留给 KaTeX 渲染，正文 LaTeX 命令转为 Markdown
- ✅ **CDATA 安全** — FPS 格式使用 `<![CDATA[...]]>` 包裹，避免 XML 转义问题
- ✅ **标准兼容** — 输出符合 FPS 1.2、Hydro 导入规范与 HOJ 导入规范

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

### HOJ 格式

输出符合 [HOJ 导入规范](https://docs.hdoi.cn/use/import-problem) 的 ZIP 包，**包内不再多套一层文件夹**：

```
aplusb.json           # 题目数据（文件名去掉后缀 = 测试数据文件夹名）
aplusb/
├── 1.in
├── 1.out
├── 2.in
└── 2.out
```

JSON 字段映射：

| JSON 字段 | 说明 | 来源 |
|-----------|------|------|
| `problem.title` | 题目标题 | `problem.xml` → `<name language="chinese">` |
| `problem.problemId` | 题目展示 ID | Polygon `short-name`（可在界面/`--problem-id` 中覆盖） |
| `problem.description` | 题目描述（Markdown） | `statement-sections/*/legend.tex` |
| `problem.input` / `problem.output` | 输入/输出格式 | `input.tex` / `output.tex` |
| `problem.hint` | 题目提示 | `notes.tex` |
| `problem.examples` | 题面样例 | `example.N` / `example.N.a` |
| `problem.timeLimit` | 时间限制 (ms) | `problem.xml` → `<time-limit>`（限 1~30000） |
| `problem.memoryLimit` | 空间限制 (MB) | `problem.xml` → `<memory-limit>`（限 1~1024） |
| `samples` | 评测点（含 OI 分数） | `tests/` 目录 |
| `samples[].input/output` | 测试数据文件夹内的文件名 | 自动生成 `1.in` / `1.out` |
| `languages` / `tags` / `judgeMode` 等 | 判题配置 | 界面选项或默认值 |

> **注意**：
> - 测试数据按原始字节写入（保留结尾空格与换行），保证判题结果与 Polygon 一致。
> - HOJ 的 `codeTemplates` 字段虽然可为空，但必须存在，否则 HOJ 解析 json 会报错；本工具已固定输出该字段。
> - Polygon 的判题器（checker）不会被转换为 HOJ 的 SPJ 代码，导出的题目判题模式固定为 `default`（普通判题）。
> - 题解代码（solution）和教程（tutorial）**不会**被转换到输出中（三种格式均如此）。

## 依赖

- Python 3.6+
- tkinter（Python 标准库，通常已预装）
- 无需第三方库

## 许可证

MIT
