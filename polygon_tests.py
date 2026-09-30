#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polygon 测试数据加载 / 动态生成（FPS / Hydro / HOJ 三个 core 共用）

Polygon（Codeforces）导出的压缩包里，测试数据 **不是** 全部静态存放的：

* ``<test method="manual">``    手工测试：输入放在 ``tests/%02d``，但答案 ``tests/%02d.a`` 也可能没有；
* ``<test method="generated">`` 生成型测试：包里 **完全没有** 输入文件，只有
  ``cmd="gen -T 10000 ..."`` 这样的命令行，必须运行 ``files/`` 下的生成器才能得到；
* 答案：一律需要运行主标程（``solutions/std.*``，``tag="main"``）算出来。

也就是说 Polygon 生成测试数据是「用 gen 动态生成 + 用标程算答案」，而不是静态上传。
本模块复刻包内 ``scripts/*.bat`` / ``doall.bat`` 的流程：

1. 按 ``problem.xml`` 的 ``input-path-pattern`` / ``answer-path-pattern`` 读取静态数据；
2. 缺失的输入 → 运行生成器（优先用包内预编译二进制，否则用本机 g++ 现场编译源码）；
3. 缺失的答案 → 运行主标程，stdin 喂输入、stdout 收答案；
4. 现场生成的测试点再跑一遍包内 validator / checker（与 Polygon 的 doall 一致）；
   压缩包自带的静态数据（如 Linux 包里的完整测试数据）视为 Polygon 已校验过，直接采用。

生成的临时文件都放在临时目录中，转换结束后自动清理。
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# ========== 默认值 / 常量 ==========

DEFAULT_INPUT_PATTERN = 'tests/%02d'
DEFAULT_ANSWER_PATTERN = 'tests/%02d.a'

# 生成器 / 标程 / 编译 的超时（秒）
GENERATOR_TIMEOUT = 180
SOLUTION_TIMEOUT_MIN = 30
SOLUTION_TIMEOUT_MAX = 300
COMPILE_TIMEOUT = 300

# 可用环境变量指定 C++ 编译器（默认依次尝试 g++ / c++ / clang++）
COMPILER_ENV_VAR = 'POLYGON2FPS_CXX'
COMPILER_CANDIDATES = ('g++', 'c++', 'clang++')

# 编译器参数组合（依次尝试，命中即止；静态链接可避免 Windows 下 DLL 混装问题）
def _compile_attempts() -> List[List[str]]:
    static = ['-static'] if sys.platform == 'win32' else []
    return [
        ['-std=gnu++17'] + static,
        ['-std=gnu++20'] + static,
        ['-std=gnu++17'],
        [],
    ]


# ========== 数据结构 ==========

@dataclass
class Tool:
    """problem.xml 里的一个可执行体（生成器 / 标程 / validator / checker）"""
    name: str
    source: Optional[str] = None   # 相对包根目录的源码路径，如 files/gen.cpp
    binary: Optional[str] = None   # 相对包根目录的二进制路径，如 files/gen.exe


@dataclass
class TestSpec:
    """``<testset><tests><test>`` 中的一个测试点声明"""
    index: int
    method: str = 'manual'   # manual / generated
    cmd: str = ''            # generated 时的生成命令（如 "gen 1 2 3"）
    sample: bool = False
    description: str = ''


@dataclass
class TestsetInfo:
    """``<testset>`` 的解析结果"""
    name: str = 'tests'
    test_count: int = 0
    input_pattern: str = DEFAULT_INPUT_PATTERN
    answer_pattern: str = DEFAULT_ANSWER_PATTERN
    time_limit_ms: int = 0
    specs: Dict[int, TestSpec] = field(default_factory=dict)

    def spec(self, index: int) -> TestSpec:
        """取某个测试点的声明（缺失时按手工测试处理）"""
        return self.specs.get(index) or TestSpec(index=index)


@dataclass
class TestData:
    """一组测试数据（原始字节，保证与评测文件完全一致）"""
    index: int
    input: bytes
    answer: bytes
    sample: bool = False
    generated_input: bool = False
    generated_answer: bool = False


@dataclass
class LoadResult:
    """测试数据加载结果"""
    tests: List[TestData] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped: List[int] = field(default_factory=list)
    test_count: int = 0
    generated_inputs: int = 0
    generated_answers: int = 0
    validated: int = 0
    checked: int = 0

    def size_bytes(self) -> int:
        return sum(len(t.input) + len(t.answer) for t in self.tests)

    def summary(self) -> str:
        """生成一句人话摘要，用于日志/进度显示"""
        parts = [f'{len(self.tests)} 组测试数据']
        if self.generated_inputs:
            parts.append(f'动态生成输入 {self.generated_inputs} 组')
        if self.generated_answers:
            parts.append(f'动态生成答案 {self.generated_answers} 组')
        if self.skipped:
            parts.append(f'跳过 {len(self.skipped)} 组（第 {_join_ints(self.skipped)} 个）')
        return '，'.join(parts)


def _join_ints(values: List[int], limit: int = 8) -> str:
    text = ', '.join(str(v) for v in values[:limit])
    if len(values) > limit:
        text += ' ...'
    return text


# ========== problem.xml 解析 ==========

def format_test_path(pattern: str, index: int) -> str:
    """把 Polygon 的 printf 风格路径模板（``tests/%02d``）格式化成实际文件名"""
    if not pattern:
        return ''
    try:
        return pattern % index
    except (TypeError, ValueError):
        return pattern.replace('%d', str(index))


def parse_testset(root: ET.Element) -> TestsetInfo:
    """解析 ``<testset>``（测试点数量、路径模板、每个测试点的生成命令）"""
    info = TestsetInfo()
    testset = root.find('.//testset')
    if testset is None:
        return info

    info.name = testset.get('name') or 'tests'

    def _text(tag: str, default: str) -> str:
        elem = testset.find(tag)
        if elem is not None and elem.text and elem.text.strip():
            return elem.text.strip()
        return default

    info.input_pattern = _text('input-path-pattern', DEFAULT_INPUT_PATTERN)
    info.answer_pattern = _text('answer-path-pattern', DEFAULT_ANSWER_PATTERN)

    count_text = _text('test-count', '0')
    try:
        info.test_count = int(count_text)
    except ValueError:
        info.test_count = 0

    tl_text = _text('time-limit', '0')
    try:
        info.time_limit_ms = int(tl_text)
    except ValueError:
        info.time_limit_ms = 0

    tests_elem = testset.find('tests')
    if tests_elem is not None:
        for index, test_elem in enumerate(tests_elem.findall('test'), start=1):
            info.specs[index] = TestSpec(
                index=index,
                method=(test_elem.get('method') or 'manual').strip(),
                cmd=(test_elem.get('cmd') or '').strip(),
                sample=(test_elem.get('sample') == 'true'),
                description=(test_elem.get('description') or '').strip(),
            )
        if not info.test_count:
            info.test_count = len(info.specs)

    return info


def _tool_key(path: str) -> str:
    """由源码/二进制路径得到程序名（``files/gen.cpp`` → ``gen``）"""
    base = os.path.basename((path or '').replace('\\', '/'))
    return os.path.splitext(base)[0]


def collect_tools(root: ET.Element) -> Dict[str, Tool]:
    """
    收集包内所有可执行体：
      ``generators`` 生成器（按程序名索引）、``solutions`` 标程（按 tag 索引），
      以及 ``validator`` / ``checker``（键名固定为 ``validator`` / ``checker``）。
    """
    tools: Dict[str, Tool] = {}

    def _add(tool: Tool, prefix: str = '') -> None:
        if tool.name:
            tools[prefix + tool.name] = tool

    for exec_elem in root.findall('.//files/executables/executable'):
        source = _elem_path(exec_elem.find('source'))
        binary = _elem_path(exec_elem.find('binary'))
        name = _tool_key(source) or _tool_key(binary)
        if name:
            _add(Tool(name=name, source=source, binary=binary), 'gen:')

    for solution in root.findall('.//assets/solutions/solution'):
        source = _elem_path(solution.find('source'))
        binary = _elem_path(solution.find('binary'))
        tag = (solution.get('tag') or '').strip()
        name = tag or _tool_key(source) or _tool_key(binary)
        if name:
            _add(Tool(name=name, source=source, binary=binary), 'solution:')

    validator = root.find('.//assets/validators/validator')
    if validator is not None:
        _add(Tool(name='validator',
                  source=_elem_path(validator.find('source')),
                  binary=_elem_path(validator.find('binary'))), 'tool:')

    checker = root.find('.//assets/checker')
    if checker is not None:
        source = _elem_path(checker.find('source'))
        binary = _elem_path(checker.find('binary'))
        if not source and not binary:
            # 形如 <checker name="std::ncmp.cpp" type="testlib"/>：用的是 Polygon 内建判题器
            copy = _elem_path(checker.find('copy'))
            source = copy
        _add(Tool(name='checker', source=source, binary=binary), 'tool:')

    return tools


def _elem_path(elem: Optional[ET.Element]) -> Optional[str]:
    if elem is None:
        return None
    path = elem.get('path')
    return path.strip() if path and path.strip() else None


# ========== 可执行体解析 / 运行 ==========

def is_runnable_binary(path: str) -> bool:
    """判断包内的预编译二进制能否在当前平台直接运行（看文件头魔数）"""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, 'rb') as f:
            head = f.read(4)
    except OSError:
        return False
    if sys.platform == 'win32':
        return head[:2] == b'MZ'
    return head == b'\x7fELF'


def find_compiler() -> Optional[str]:
    """查找可用的 C++ 编译器（可用环境变量 ``POLYGON2FPS_CXX`` 指定）"""
    explicit = os.environ.get(COMPILER_ENV_VAR, '').strip()
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        found = shutil.which(explicit)
        if found:
            return found
    for name in COMPILER_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _creation_flags() -> int:
    """Windows 下隐藏子进程控制台窗口（GUI 调用时不会闪黑框）"""
    if sys.platform == 'win32':
        return getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    return 0


def _split_cmd(cmd: str) -> List[str]:
    """切分 Polygon 的生成命令（尽量保留 Windows 反斜杠路径）"""
    text = (cmd or '').strip()
    if not text:
        return []
    try:
        parts = shlex.split(text, posix=False)
    except ValueError:
        parts = text.split()
    cleaned = []
    for part in parts:
        # shlex(posix=False) 会保留成对引号，这里手工去掉
        if len(part) >= 2 and part[0] == part[-1] and part[0] in '"\'':
            part = part[1:-1]
        cleaned.append(part)
    return cleaned


class TestDataRunner:
    """负责运行生成器 / 标程 / validator / checker，并按需现场编译源码"""

    def __init__(self, extract_dir: str, testset: TestsetInfo, tools: Dict[str, Tool],
                 log: Optional[Callable[[str], None]] = None):
        self.extract_dir = extract_dir
        self.testset = testset
        self.tools = tools
        self.log = log or (lambda _msg: None)
        self._exe_cache: Dict[Tuple[Optional[str], Optional[str]], Optional[str]] = {}
        self._compile_errors: Dict[str, str] = {}
        self._work_root: Optional[str] = None
        self._answer_tool_warned = False

    # ---- 目录 ----

    def _work_dir(self) -> str:
        if self._work_root is None:
            self._work_root = tempfile.mkdtemp(prefix='polygon2tests_')
        return self._work_root

    def close(self) -> None:
        if self._work_root:
            shutil.rmtree(self._work_root, ignore_errors=True)
            self._work_root = None

    # ---- 可执行体解析 ----

    def _resolve_tool(self, tool: Optional[Tool]) -> Optional[str]:
        if tool is None:
            return None
        key = (tool.source, tool.binary)
        if key in self._exe_cache:
            return self._exe_cache[key]

        exe = None
        if tool.binary:
            candidate = os.path.join(self.extract_dir, tool.binary.replace('/', os.sep))
            if is_runnable_binary(candidate):
                exe = candidate
        if exe is None and tool.source:
            source = os.path.join(self.extract_dir, tool.source.replace('/', os.sep))
            if os.path.isfile(source):
                exe = self._compile(source)
            else:
                self.log(f'[警告] 包内缺少源码 {tool.source}，无法编译 {tool.name}')
        self._exe_cache[key] = exe
        return exe
    def _compile(self, source: str) -> Optional[str]:
        """用本机 g++ 编译包内源码（生成器/标程通常依赖 files/testlib.h）"""
        compiler = find_compiler()
        if not compiler:
            self._compile_errors[source] = (
                '未找到 C++ 编译器（g++ / c++ / clang++），'
                f'可用环境变量 {COMPILER_ENV_VAR} 指定')
            return None

        name = os.path.splitext(os.path.basename(source))[0]
        out = os.path.join(self._work_dir(), name + ('.exe' if sys.platform == 'win32' else ''))
        include_dir = os.path.dirname(source)
        last_error = ''
        for extra in _compile_attempts():
            args = [compiler, '-O2', '-pipe']
            if include_dir:
                args.append(f'-I{include_dir}')
            args.extend(extra)
            args.extend([source, '-o', out])
            try:
                proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      timeout=COMPILE_TIMEOUT, creationflags=_creation_flags())
            except (OSError, subprocess.TimeoutExpired) as exc:
                last_error = f'{type(exc).__name__}: {exc}'
                continue
            if proc.returncode == 0 and os.path.isfile(out):
                return out
            last_error = _first_lines(proc.stdout)
        self._compile_errors[source] = last_error or '编译失败'
        self.log(f'[警告] 编译 {os.path.basename(source)} 失败：{last_error or "未知错误"}')
        return None

    # ---- 运行 ----

    def _run(self, args: List[str], stdin=None, stdout=None, cwd: Optional[str] = None,
             timeout: int = GENERATOR_TIMEOUT) -> Tuple[Optional[int], str]:
        try:
            proc = subprocess.run(args, cwd=cwd or self.extract_dir, stdin=stdin, stdout=stdout,
                                  stderr=subprocess.PIPE, timeout=timeout,
                                  creationflags=_creation_flags())
        except FileNotFoundError as exc:
            return None, f'无法执行 {args[0]}：{exc}'
        except subprocess.TimeoutExpired:
            return None, f'执行超时（>{timeout}s）'
        except OSError as exc:
            return None, f'执行失败：{exc}'
        return proc.returncode, proc.stderr.decode('utf-8', 'replace').strip()

    def _cmd_program(self, cmd: str) -> Tuple[Optional[str], List[str], str]:
        """把生成命令的第一个词解析为可执行文件路径"""
        parts = _split_cmd(cmd)
        if not parts:
            return None, [], '生成命令为空'
        program = parts[0]
        name = _tool_key(program)
        tool = self.tools.get('gen:' + name)
        exe = self._resolve_tool(tool) if tool else None
        if exe is None:
            # 命令里直接写了相对包根目录的路径（如 files/gen.exe）
            direct = os.path.join(self.extract_dir, program.replace('/', os.sep))
            if is_runnable_binary(direct):
                exe = direct
        if exe is None:
            why = ''
            if tool is not None and tool.source:
                error = self._compile_errors.get(os.path.join(
                    self.extract_dir, tool.source.replace('/', os.sep)), '')
                why = f'（{error}）' if error else '（包内没有可运行的程序）'
            else:
                why = '（包内没有该程序的可执行文件或源码）'
            return None, parts[1:], f'包内没有可用于生成测试点的程序 “{name}”{why}'
        return exe, parts[1:], ''

    def generate_input(self, spec: TestSpec) -> Optional[bytes]:
        """运行生成器得到某个测试点的输入（优先 stdout，其次文件模式）"""
        exe, args, error = self._cmd_program(spec.cmd)
        if exe is None:
            self.log(f'[警告] 测试点 {spec.index}：{error}')
            return None

        # 方式一：生成器把数据写到 stdout（Polygon 的 gen-input-via-stdout）
        with tempfile.TemporaryFile() as out, open(os.devnull, 'rb') as devnull:
            code, err = self._run([exe] + args, stdin=devnull, stdout=out)
            out.seek(0)
            data = out.read()
        if code == 0 and data:
            return data
        if code != 0:
            reason = err or f'退出码 {code}'

        # 方式二：生成器自己写出名为 <index> 的文件（Polygon 的 gen-input-via-file）
        file_data = self._generate_input_via_file(exe, args, spec.index)
        if file_data is not None:
            return file_data

        self.log(f'[警告] 测试点 {spec.index} 生成失败（cmd: {spec.cmd}）：{reason or "生成器没有输出数据"}')
        return None

    def _generate_input_via_file(self, exe: str, args: List[str], index: int) -> Optional[bytes]:
        work = tempfile.mkdtemp(prefix=f'gen{index}_', dir=self._work_dir())
        try:
            with open(os.devnull, 'rb') as devnull:
                code, err = self._run([exe] + args, stdin=devnull, cwd=work)
            candidate = os.path.join(work, str(index))
            if os.path.isfile(candidate):
                with open(candidate, 'rb') as f:
                    return f.read()
            if code not in (0, None):
                self.log(f'[警告] 测试点 {index} 文件模式生成失败：{err or f"退出码 {code}"}')
            return None
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def generate_answer(self, input_bytes: bytes) -> Optional[bytes]:
        """运行主标程，用 stdin 喂输入、stdout 收答案"""
        tool = self.tools.get('solution:main') or self.tools.get('solution:accepted')
        if tool is None:
            if not self._answer_tool_warned:
                self._answer_tool_warned = True
                self.log('[警告] 包内没有 tag="main" 的主标程，无法动态生成答案')
            return None
        exe = self._resolve_tool(tool)
        if exe is None:
            if not self._answer_tool_warned:
                self._answer_tool_warned = True
                self.log(f'[警告] 主标程 {tool.source or tool.binary} 不可用，无法动态生成答案')
            return None

        timeout = SOLUTION_TIMEOUT_MIN
        if self.testset.time_limit_ms > 0:
            timeout = min(SOLUTION_TIMEOUT_MAX,
                          max(SOLUTION_TIMEOUT_MIN, self.testset.time_limit_ms // 1000 * 10))
        with tempfile.TemporaryFile() as stdin_file, tempfile.TemporaryFile() as out:
            stdin_file.write(input_bytes)
            stdin_file.seek(0)
            code, err = self._run([exe], stdin=stdin_file, stdout=out, timeout=timeout)
            out.seek(0)
            data = out.read()
        if code is None:
            self.log(f'[警告] 主标程执行异常：{err}')
            return None
        if code != 0:
            self.log(f'[警告] 主标程返回值 {code}：{_first_lines(err.encode("utf-8", "replace"))}')
            return None
        return data

    # ---- 校验 ----

    def validate(self, input_bytes: bytes) -> Tuple[bool, str]:
        """运行 validator 校验输入（对应 Polygon 的 vali.exe --testset ... --group ...）"""
        tool = self.tools.get('tool:validator')
        if tool is None:
            return True, ''
        exe = self._resolve_tool(tool)
        if exe is None:
            return True, ''

        args = [exe, '--testset', self.testset.name or 'tests', '--group', '']
        with tempfile.TemporaryFile() as stdin_file:
            stdin_file.write(_local_tool_bytes(input_bytes))
            stdin_file.seek(0)
            code, err = self._run(args, stdin=stdin_file)
        if code == 0:
            return True, ''
        return False, err or f'退出码 {code}'

    def check(self, input_bytes: bytes, answer_bytes: bytes) -> Tuple[bool, str]:
        """运行 checker 校验答案（Polygon 用 “check 输入 答案 答案” 自检）"""
        tool = self.tools.get('tool:checker')
        if tool is None:
            return True, ''
        exe = self._resolve_tool(tool)
        if exe is None:
            return True, ''

        work = tempfile.mkdtemp(prefix='check_', dir=self._work_dir())
        try:
            in_path = os.path.join(work, 'input.txt')
            ans_path = os.path.join(work, 'answer.txt')
            with open(in_path, 'wb') as f:
                f.write(_local_tool_bytes(input_bytes))
            with open(ans_path, 'wb') as f:
                f.write(_local_tool_bytes(answer_bytes))
            code, err = self._run([exe, in_path, ans_path, ans_path], timeout=GENERATOR_TIMEOUT)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if code in (0, 7):   # testlib：0 = OK，7 = PE（Polygon 视为通过）
            return True, ''
        return False, _first_lines(err.encode('utf-8', 'replace')) if err else f'退出码 {code}'


def _first_lines(text, limit: int = 3, max_len: int = 300) -> str:
    """把外部程序的输出/报错压缩成一行（便于写进日志）"""
    if not text:
        return ''
    if isinstance(text, bytes):
        text = text.decode('utf-8', 'replace')
    lines = [line.strip() for line in text.splitlines() if line.strip()][:limit]
    joined = ' | '.join(lines)
    return joined[:max_len]


_EOL_RE = re.compile(rb'\r?\n')


def _local_tool_bytes(data: bytes) -> bytes:
    """把行尾补齐成当前平台上 testlib 期望的格式（**仅用于校验用的临时副本**）

    Windows 版 testlib 的 ``eoln()`` 在严格模式下必须看到 ``CR + LF``
    （testlib.h 中 ``#if (defined(ON_WINDOWS) && !defined(FOR_LINUX))`` 分支），
    直接拿 LF 数据去校验会一律得 ``FAIL Expected EOLN``。这里补齐行尾，
    使 Windows 上的校验行为与 Polygon 后端（Linux，两种行尾都接受）一致；
    导出的测试数据本身不做任何改动。
    """
    if sys.platform != 'win32':
        return data
    return _EOL_RE.sub(b'\r\n', data)


# ========== 主入口 ==========

def test_indices(extract_dir: str, testset: TestsetInfo) -> List[int]:
    """待处理的测试点编号：优先用 test-count，缺失时回退为扫描 tests 目录"""
    if testset.test_count > 0:
        return list(range(1, testset.test_count + 1))

    pattern_dir = os.path.dirname((testset.input_pattern or DEFAULT_INPUT_PATTERN).replace('/', os.sep))
    tests_dir = os.path.join(extract_dir, pattern_dir or 'tests')
    if not os.path.isdir(tests_dir):
        return []
    indices = []
    for name in os.listdir(tests_dir):
        if re.match(r'^\d+$', name):
            indices.append(int(name))
    return sorted(indices)


def load_test_data(extract_dir: str, root: ET.Element, generate: bool = True,
                   log: Optional[Callable[[str], None]] = None,
                   max_total_bytes: int = 0) -> LoadResult:
    """
    读取压缩包中的全部测试数据，缺失部分按 Polygon 的方式动态生成。

    Args:
        extract_dir: 解压后的包根目录
        root: problem.xml 的根元素
        generate: 是否允许运行动态生成（生成器 + 标程）
        log: 日志回调，接收一行字符串
        max_total_bytes: 测试数据总大小上限（字节），0 = 不限制；超限即停止

    Returns:
        LoadResult
    """
    log = log or (lambda _msg: None)
    testset = parse_testset(root)
    tools = collect_tools(root) if generate else {}
    runner = TestDataRunner(extract_dir, testset, tools, log) if generate else None

    result = LoadResult(test_count=testset.test_count)
    indices = test_indices(extract_dir, testset)

    def _read_static(path: str) -> Optional[bytes]:
        if not path:
            return None
        full = os.path.join(extract_dir, path.replace('/', os.sep))
        if not os.path.isfile(full):
            return None
        with open(full, 'rb') as f:
            return f.read()

    def _warn(message: str) -> None:
        result.warnings.append(message)
        log('[警告] ' + message)

    used = 0
    try:
        for index in indices:
            spec = testset.spec(index)
            in_rel = format_test_path(testset.input_pattern, index)
            ans_rel = format_test_path(testset.answer_pattern, index)

            input_data = _read_static(in_rel)
            generated_input = False
            if input_data is None:
                if runner is not None and spec.cmd:
                    log(f'正在运行生成器生成第 {index} 个测试点：{spec.cmd}')
                    input_data = runner.generate_input(spec)
                    generated_input = input_data is not None
                elif runner is not None and spec.method == 'generated':
                    _warn(f'第 {index} 个测试点由生成器动态生成，但包内没有对应的生成命令（cmd）')
                else:
                    _warn(f'压缩包内缺少第 {index} 个测试点的输入文件 {in_rel}'
                          + ('，且未启用动态生成' if runner is None else ''))
            if input_data is None:
                result.skipped.append(index)
                continue

            answer_data = _read_static(ans_rel)
            generated_answer = False
            if answer_data is None and runner is not None:
                log(f'正在运行主标程计算第 {index} 个测试点的答案')
                answer_data = runner.generate_answer(input_data)
                generated_answer = answer_data is not None
            if answer_data is None:
                _warn(f'第 {index} 个测试点缺少答案 {ans_rel}'
                      + ('，且无法通过主标程生成' if runner is not None else '，且未启用动态生成'))
                result.skipped.append(index)
                continue

            # 大小上限判断放在校验之前，避免为最终会被截断的测试点做无用功
            size = len(input_data) + len(answer_data)
            if max_total_bytes and result.tests and used + size > max_total_bytes:
                _warn(f'测试数据超过 {_format_mb(max_total_bytes)} MB 上限，'
                      f'已截断为 {len(result.tests)} 组')
                break

            # 只有现场生成的数据才额外校验：包内静态数据是 Polygon 生成时已校验过的，
            # 不必（也不该）在本地重跑 validator / checker
            if runner is not None and (generated_input or generated_answer):
                ok, message = runner.validate(input_data)
                if ok:
                    result.validated += 1
                else:
                    _warn(f'第 {index} 个测试点未通过 validator 校验：{message}')
                ok, message = runner.check(input_data, answer_data)
                if ok:
                    result.checked += 1
                else:
                    _warn(f'第 {index} 个测试点未通过 checker 校验：{message}')

            used += size
            result.tests.append(TestData(
                index=index,
                input=input_data,
                answer=answer_data,
                sample=spec.sample,
                generated_input=generated_input,
                generated_answer=generated_answer,
            ))
            if generated_input:
                result.generated_inputs += 1
            if generated_answer:
                result.generated_answers += 1
    finally:
        if runner is not None:
            runner.close()

    if runner is not None and result.tests and not result.validated and not result.checked:
        log('测试数据全部取自压缩包（Polygon 生成时已校验过），未额外运行 validator/checker')

    return result


def _format_mb(value: float) -> str:
    text = f'{value / 1048576:.6f}'.rstrip('0').rstrip('.')
    return text or '0'


def failure_message(result: LoadResult) -> str:
    """一组测试数据都拿不到时，拼一句能直接展示给用户的错误说明"""
    message = '未能获得任何测试数据'
    if result.warnings:
        message += '：' + '；'.join(result.warnings[:3])
    if result.skipped:
        message += f'（共 {len(result.skipped)} 个测试点被跳过）'
    return message
