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
| `--difficulty` | 难度：`0`~`8`（默认 `0`），见下方难度对照表 |
| `--judge-case-mode` | 用例模式：`default`（默认）/ `ergodic_without_error` / `subtask_lowest` / `subtask_average` |
| `--tags` | 标签，逗号分隔 |
| `--problem-id` | 题目展示 ID（默认使用 Polygon `short-name`） |
| `--max-mb` | 测试数据大小上限（MB），`0` = 不限制 |
| `--no-generate-tests` | 不动态生成缺失的测试点（默认会自动生成，见下文） |

### HOJ 难度对照表（二次开发版）

本工具的难度选项与二次开发后的 HOJ 前端保持一致（共 9 级，取值 `0`~`8`）：

| 难度值 | 名称 | 颜色 | 国际站颜色名 | OI 排行榜权重 |
|:------:|------|------|--------------|:-------------:|
| 0 | 暂无评定 | 灰色 `#BFBFBF` | Gray | 0 |
| 1 | 入门 | 红色 `#FE4C61` | Red | 1 |
| 2 | 普及- | 橙色 `#F39C11` | Orange | 2 |
| 3 | 普及 | 黄色 `#FFC116` | Yellow | 3 |
| 4 | 普及+/提高- | 绿色 `#52C41A` | Green | 4 |
| 5 | 提高 | 青色 `#13C2C2` | Cyan | 5 |
| 6 | 提高+/省选- | 蓝色 `#3498DB` | Blue | 6 |
| 7 | 省选/NOI- | 紫色 `#9D3DCF` | Purple | 8 |
| 8 | NOI/NOI+/CTS | 黑色 `#0E1D69` | Black | 10 |

> 若后续再次调整等级，只需修改 `polygon2hoj_core.py` 中的 `HOJ_DIFFICULTIES` 列表 ——
> GUI 下拉框、CLI 参数校验与说明都会自动跟随；超出范围的值会被收敛为 `0`（暂无评定）。

## Polygon 的三种导出包（都已兼容）

Polygon 同一个题目可导出三种包，内部结构差别很大：

| 包 | 文件名 | `tests/` 内容 | 二进制 | `scripts/` |
|----|--------|---------------|--------|-----------|
| Standard（默认） | `xxx.zip` | **只有手工测试的输入**（如 `tests/01`），答案缺失 | PE（`files/gen.exe`、`solutions/std.exe`…） | 12 个（sh + bat） |
| Linux | `xxx$linux.zip` | **全部输入 + 答案**（`tests/%02d` 与 `tests/%02d.a`，LF 行尾） | 无（只有 `.cpp`） | 0 个 |
| Windows | `xxx$windows.zip` | 全部输入 + 答案（CRLF 行尾） | PE | 6 个（bat） |

本工具对三者的处理：

* 有静态数据就用静态数据（Linux / Windows 包通常一步到位，**按原始字节**导出，不动行尾）；
* Standard 包缺的输入 → 跑 `cmd` 里的生成器，缺的答案 → 跑 `tag="main"` 主标程；
* 没有预编译二进制（Linux 包）或二进制与当前平台不匹配时，用本机 `g++` 现场编译源码；
* 只有**现场生成**的测试点会额外跑 validator / checker；包内静态数据视为 Polygon 已校验过。
* 标注为样例（`sample="true"`）的那组测试点**仍会**作为普通测试点导出 —— 它在 Polygon 里
  就是测试点 1，丢掉会让判题点变少（也导致同一题目不同包导出结果不一致）。
* 包内静态测试数据按**原始字节**导出，不改行尾；现场生成的数据由包内二进制产出
  （Windows 包为 CRLF、Linux 包为 LF），与 Polygon 对应包保持一致。

> **Windows 上校验行尾的坑**：Windows 版 `testlib.h` 的 `eoln()` 在严格模式下必须看到
> `CR+LF`，拿 LF 数据去跑会一律报 `FAIL Expected EOLN`（Linux 包的数据就是 LF）。
> 工具在给校验用的临时副本里自动补齐行尾，**不会**改动导出的测试数据。

## 测试数据：动态生成（重要）

Polygon 里的测试数据**不是静态上传的**，导出包中往往没有完整数据：

| 测试点类型 | 包内内容 | 缺什么 |
|------------|----------|--------|
| `method="manual"`（手工测试） | `tests/01`、`tests/20` 等输入文件 | 答案 `tests/01.a` 也可能没有 |
| `method="generated"`（生成器生成） | **只有**生成命令，如 `cmd="gen -T 10000 -minn 50000 ..."` | 输入、答案都缺 |

所以转换时会**复刻 Polygon 自己的 `doall` 流程**动态生成这些数据：

1. 按 `problem.xml` 的 `input-path-pattern` / `answer-path-pattern` 读取包内已有的静态数据；
2. 缺失的输入 → 运行对应的生成器（`cmd` 里的 `gen` / `zhao` / `hack` …）；
3. 缺失的答案 → 运行主标程（`solution tag="main"`，如 `solutions/std.cpp`），stdin 喂输入、stdout 收答案；
4. 现场生成的测试点再跑一遍包内的 `validator` / `checker`（与 Polygon 一致；静态数据不重复校验）。

运行程序时的取用顺序：

* **优先用包内预编译二进制**（如 `files/gen.exe`、`solutions/std.exe`，Windows 包自带）；
* 二进制缺失或与当前平台不匹配（如 Linux 包在 Windows 上打开）时，用本机 `g++` 现场编译
  `files/gen.cpp` / `solutions/std.cpp`（自动带上 `files/testlib.h` 所在目录）；
  可用环境变量 `POLYGON2FPS_CXX` 指定编译器；
* 两者都不可用时，该测试点会被跳过并在日志中给出原因；若一个都没能拿到，直接报错。

生成过程中的日志（生成第 N 个测试点、跳过、校验失败等）会输出到 GUI 日志区或命令行。
如需关闭动态生成，可传 `--no-generate-tests`（HOJ 子命令），或在代码里给 `convert()` / `convert_to_hydro()`
传 `generate_tests=False`。

> 提示：生成型测试点可能很大（例如 `n=200000` 的测试点单组数据可达数 MB），
> 转换时间与输出体积都会明显上升，必要时用 `--max-mb` 限制。

## 项目结构

```
├── polygon2fps.py              # 统一入口（无参数→GUI，有参数→CLI）
├── polygon2fps_core.py         # FPS 核心转换逻辑
├── polygon2fps_gui.py          # 图形用户界面（基于 tkinter）
├── polygon2hydro_core.py       # Hydro 核心转换逻辑
├── polygon2hoj_core.py         # HOJ 核心转换逻辑
├── polygon_tests.py            # 测试数据加载 / 动态生成（三个 core 共用）
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
- ✅ **测试数据动态生成** — 包内缺失的生成型测试点会用生成器 + 主标程现场生成（同 Polygon 的 doall）
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
| `<test_input/output>` | 测试数据 | `tests/` 目录（缺失时由生成器/主标程现场生成） |
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
| `samples` | 评测点（含 OI 分数） | `tests/` 目录（缺失时现场生成） |
| `samples[].input/output` | 测试数据文件夹内的文件名 | 自动生成 `1.in` / `1.out` |
| `languages` / `tags` / `judgeMode` 等 | 判题配置 | 界面选项或默认值 |

> **注意**：
> - 测试数据按原始字节写入（保留结尾空格与换行），保证判题结果与 Polygon 一致。
> - 包内缺失的测试数据（生成型测试点的输入、所有测试点的答案）会自动动态生成，详见上文“测试数据：动态生成”。
> - HOJ 的 `codeTemplates` 字段虽然可为空，但必须存在，否则 HOJ 解析 json 会报错；本工具已固定输出该字段。
> - Polygon 的判题器（checker）不会被转换为 HOJ 的 SPJ 代码，导出的题目判题模式固定为 `default`（普通判题）。
> - 题解代码（solution）和教程（tutorial）**不会**被转换到输出中（三种格式均如此）。

## 依赖

- Python 3.6+
- tkinter（Python 标准库，通常已预装）
- 无需第三方库

## 许可证

MIT
