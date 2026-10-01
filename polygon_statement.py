#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Polygon 题面 LaTeX 转换（FPS / Hydro / HOJ 三个 core 共用）

这里集中处理题面从 LaTeX 到 Markdown / 纯文本的转换，避免三份实现各修各的。
两个最容易踩的坑：

1. **软换行**。LaTeX 里段落内的单个换行只是空格，只有空行才是分段，``\\\\`` 才是
   硬换行。而 HOJ / Hydro 前端的 markdown-it 开着 ``breaks: true``（mavonEditor
   的默认配置），会把源文本里的每个 ``\\n`` 渲染成 ``<br>``。如果原样保留源文件中的
   换行，题面里每个 ``$公式$`` 前后都会断行，公式被顶到单独一行，排版完全错乱。
   因此转换前先把「软换行」折叠成空格，只保留空行与显式换行。

2. **数学模式**。``$...$`` / ``$$...$$`` / ``\\(...\\)`` / ``\\[...\\]`` 里的内容要原样
   交给 KaTeX，绝不能在数学模式内做 ``\\le → ≤`` 这类替换：``\\leq`` 会被 ``\\le``
   部分匹配成 ``≤q``。本模块先按数学模式切分，只转换数学模式之外的部分；
   纯文本（FPS）模式才把公式内容降级为 Unicode 文本。

另外，符号替换用「最长匹配优先」的一次性正则，避免 ``\\in`` 吃掉 ``\\infty``、
``\\subset`` 吃掉 ``\\subseteq`` 之类的部分匹配。
"""

import re

# ---------------------------------------------------------------------------
# LaTeX 命令 → Unicode 符号
# ---------------------------------------------------------------------------
SYMBOLS = {
    # 箭头
    '\\Longleftrightarrow': '↔',
    '\\Longleftarrow': '⇐',
    '\\Longrightarrow': '⇒',
    '\\longleftrightarrow': '↔',
    '\\longleftarrow': '←',
    '\\longrightarrow': '→',
    '\\leftrightarrow': '↔',
    '\\leftarrow': '←',
    '\\rightarrow': '→',
    '\\Leftarrow': '⇐',
    '\\Rightarrow': '⇒',
    '\\updownarrow': '↕',
    '\\Updownarrow': '⇕',
    '\\uparrow': '↑',
    '\\downarrow': '↓',
    '\\Uparrow': '⇑',
    '\\Downarrow': '⇓',
    '\\hookrightarrow': '↪',
    '\\hookleftarrow': '↩',
    '\\rightharpoonup': '⇀',
    '\\rightharpoondown': '⇁',
    '\\leftharpoonup': '↼',
    '\\leftharpoondown': '↽',
    '\\longmapsto': '⟼',
    '\\mapsto': '↦',
    '\\nearrow': '↗',
    '\\searrow': '↘',
    '\\swarrow': '↙',
    '\\nwarrow': '↖',
    '\\to': '→',
    '\\gets': '←',
    # 关系
    '\\leqslant': '≤',
    '\\geqslant': '≥',
    '\\leq': '≤',
    '\\geq': '≥',
    '\\le': '≤',
    '\\ge': '≥',
    '\\ll': '≪',
    '\\gg': '≫',
    '\\neq': '≠',
    '\\ne': '≠',
    '\\equiv': '≡',
    '\\approxeq': '≊',
    '\\approx': '≈',
    '\\cong': '≅',
    '\\simeq': '≃',
    '\\sim': '∼',
    '\\doteq': '≐',
    '\\propto': '∝',
    '\\models': '⊨',
    '\\vDash': '⊨',
    '\\mid': '|',
    '\\parallel': '∥',
    '\\perp': '⊥',
    '\\lt': '<',
    '\\gt': '>',
    '\\preceq': '⪯',
    '\\prec': '≺',
    '\\succeq': '⪰',
    '\\succ': '≻',
    # 集合
    '\\notin': '∉',
    '\\subseteq': '⊆',
    '\\subsetneq': '⊊',
    '\\subset': '⊂',
    '\\supseteq': '⊇',
    '\\supsetneq': '⊋',
    '\\supset': '⊃',
    '\\in': '∈',
    '\\ni': '∋',
    '\\cup': '∪',
    '\\cap': '∩',
    '\\setminus': '∖',
    '\\emptyset': '∅',
    '\\varnothing': '∅',
    # 运算符
    '\\times': '×',
    '\\div': '÷',
    '\\pm': '±',
    '\\mp': '∓',
    '\\cdot': '·',
    '\\ast': '*',
    '\\star': '★',
    '\\circ': '°',
    '\\bullet': '•',
    '\\oplus': '⊕',
    '\\ominus': '⊖',
    '\\otimes': '⊗',
    '\\oslash': '⊘',
    '\\odot': '⊙',
    '\\dagger': '†',
    '\\ddagger': '‡',
    '\\iiint': '∭',
    '\\iint': '∬',
    '\\oint': '∮',
    '\\int': '∫',
    '\\sum': '∑',
    '\\prod': '∏',
    '\\coprod': '∐',
    # 逻辑
    '\\nexists': '∄',
    '\\forall': '∀',
    '\\exists': '∃',
    '\\lnot': '¬',
    '\\land': '∧',
    '\\lor': '∨',
    '\\top': '⊤',
    '\\bot': '⊥',
    '\\vdash': '⊢',
    # 其他
    '\\ldots': '...',
    '\\dots': '...',
    '\\cdots': '...',
    '\\vdots': '⋮',
    '\\ddots': '⋱',
    '\\infty': '∞',
    '\\partial': '∂',
    '\\nabla': '∇',
    '\\prime': '′',
    '\\degree': '°',
    '\\angle': '∠',
    '\\triangle': '△',
    '\\surd': '√',
    '\\imath': 'i',
    '\\jmath': 'j',
    '\\ell': 'ℓ',
    '\\hbar': 'ħ',
    '\\lfloor': '⌊',
    '\\rfloor': '⌋',
    '\\lceil': '⌈',
    '\\rceil': '⌉',
    '\\P': '¶',
    '\\S': '§',
}

# 必须「最长优先」，否则 \in 会先匹配掉 \infty / \int，\subset 会吃掉 \subseteq。
# 再加 (?![a-zA-Z])，保证不会把命令名从中间截断（例如 \inf 不会被当成 \in）。
_SYMBOL_RE = re.compile(
    '|'.join(re.escape(cmd) + r'(?![a-zA-Z])'
             for cmd in sorted(SYMBOLS, key=len, reverse=True))
)

# 函数名（保留为普通文本）
_FUNCS = [
    'limsup', 'liminf', 'arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh',
    'max', 'min', 'sup', 'inf', 'lim', 'sum', 'prod', 'log', 'ln', 'lg',
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'det', 'dim', 'hom', 'ker',
    'exp', 'gcd', 'lcm', 'mod', 'bmod', 'pmod', 'arg', 'deg',
]
_FUNC_RE = re.compile(
    r'\\(?:' + '|'.join(sorted(_FUNCS, key=len, reverse=True)) + r')(?![a-zA-Z])'
)

# 数学模式：$$...$$ / \[...\] / \(...\) / $...$
_MATH_RE = re.compile(
    r'(\$\$.*?\$\$|\\\[.*?\\\]|\\\(.*?\\\)|\$[^$\n]*?\$)', re.DOTALL
)

# 代码/逐字环境（内部换行与命令都要原样保留）
_VERBATIM_RE = re.compile(
    r'\\begin\{(verbatim\*?|lstlisting\*?|Verbatim|code)\}(.*?)\\end\{\1\}',
    re.DOTALL,
)

_PLACEHOLDER = '\x00VB{}\x00'


# ---------------------------------------------------------------------------
# 预处理
# ---------------------------------------------------------------------------

def _brace_arg(text, start):
    """从 ``start``（必须指向 ``{``）开始取出配对的 {...} 内容，返回 (内容, 结束位置)。"""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if c == '\\':            # \{ \} 不参与配对
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    return None, start


def _replace_footnotes(text):
    """``\\footnote{...}`` → ``（...）``（Markdown 没有稳定的脚注语法，
    直接内联既不会丢内容，也不会在题面里留下裸命令）。"""
    needle = '\\footnote'
    out = []
    i = 0
    n = len(text)
    while True:
        j = text.find(needle, i)
        if j < 0:
            out.append(text[i:])
            break
        k = j + len(needle)
        if k < n and text[k].isalpha():     # \footnotesize 之类，不是脚注
            out.append(text[i:k])
            i = k
            continue
        while k < n and text[k] in ' \t\n':
            k += 1
        if k < n and text[k] == '[':        # 可选的编号参数
            end = text.find(']', k)
            if end >= 0:
                k = end + 1
        while k < n and text[k] in ' \t\n':
            k += 1
        if k < n and text[k] == '{':
            body, end = _brace_arg(text, k)
            if body is not None:
                out.append(text[i:j])
                body = body.strip()
                out.append(f'（{body}）' if body else '')
                i = end
                continue
        out.append(text[i:k])
        i = k
    return ''.join(out)


def _collapse_soft_newlines(text):
    """按 LaTeX 语义把段落内的单个换行折叠成空格，空行（分段）保留。"""
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return text


def _preprocess(tex):
    """去注释、暂存代码环境、处理脚注、折叠软换行。返回 (文本, 代码块列表)。"""
    text = tex.replace('\r\n', '\n').replace('\r', '\n')
    # LaTeX 注释；\% 不是注释
    text = re.sub(r'(?<!\\)%[^\n]*', '', text)

    blocks = []

    def _stash(m):
        blocks.append(m.group(2))
        return _PLACEHOLDER.format(len(blocks) - 1)

    text = _VERBATIM_RE.sub(_stash, text)
    # 脚注要在折叠换行前处理，这样跨行的脚注也能配对
    text = _replace_footnotes(text)
    text = _collapse_soft_newlines(text)
    return text, blocks


def _restore_verbatim(text, blocks, fenced=True):
    for i, body in enumerate(blocks):
        body = body.strip('\n')
        if fenced:
            replacement = '```\n' + body + '\n```'
        else:
            replacement = body
        text = text.replace(_PLACEHOLDER.format(i), replacement)
    return text


# ---------------------------------------------------------------------------
# 数学模式
# ---------------------------------------------------------------------------

def _strip_math_delimiters(part):
    if part.startswith('$$') and part.endswith('$$') and len(part) > 4:
        return part[2:-2]
    if part.startswith('\\[') and part.endswith('\\]'):
        return part[2:-2]
    if part.startswith('\\(') and part.endswith('\\)'):
        return part[2:-2]
    if part.startswith('$') and part.endswith('$') and len(part) > 2:
        return part[1:-1]
    return part


def _normalize_math_delimiters(part):
    """统一成 markdown-it-katex / KaTeX 都认的 $...$ 与 $$...$$。"""
    if part.startswith('$$') and part.endswith('$$'):
        return part
    if part.startswith('\\[') and part.endswith('\\]'):
        return '$$' + part[2:-2] + '$$'
    if part.startswith('\\(') and part.endswith('\\)'):
        return '$' + part[2:-2] + '$'
    return part


# ---------------------------------------------------------------------------
# 非数学片段：LaTeX → Markdown / 纯文本
# ---------------------------------------------------------------------------

_TEXT_COMMANDS = (
    'text', 'textrm', 'textnormal', 'textup', 'mbox', 'hbox',
    'mathrm', 'mathit', 'mathbf', 'mathsf', 'mathtt',
    'mathcal', 'mathbb', 'mathfrak', 'operatorname',
    'underline', 'overline', 'overbrace', 'underbrace',
)


def _convert_text(text):
    # 1. 转义字符（必须放在通用命令清除之前）
    for src, dst in (('\\&', '&'), ('\\%', '%'), ('\\$', '$'), ('\\#', '#'),
                     ('\\_', '_'), ('\\{', '{'), ('\\}', '}')):
        text = text.replace(src, dst)

    # 2. 章节 → 标题
    text = re.sub(r'\\section\*?\{([^{}]*)\}', r'\n## \1\n', text)
    text = re.sub(r'\\subsection\*?\{([^{}]*)\}', r'\n### \1\n', text)
    text = re.sub(r'\\subsubsection\*?\{([^{}]*)\}', r'\n#### \1\n', text)

    # 3. 列表环境 → Markdown 列表
    text = re.sub(r'\\begin\{(?:itemize|enumerate|description)\}', '\n', text)
    text = re.sub(r'\\end\{(?:itemize|enumerate|description)\}', '\n', text)
    text = re.sub(r'\\item(?:\[[^\]]*\])?[ \t]*', '\n- ', text)

    # 4. 其余环境标记（表格列格式等）丢弃
    text = re.sub(r'\\begin\{(?:tabular|tabularx|array)\}\{[^}]*\}', '\n', text)
    text = re.sub(r'\\begin\{[^}]*\}', '\n', text)
    text = re.sub(r'\\end\{[^}]*\}', '\n', text)

    # 5. 链接
    text = re.sub(r'\\href\{([^{}]*)\}\{([^{}]*)\}', r'[\2](\1)', text)
    text = re.sub(r'\\url\{([^{}]*)\}', r'\1', text)

    # 6. 强调 / 等宽 / 文本命令 → Markdown
    text = re.sub(r'\\texttt\{([^{}]*)\}', r'`\1`', text)
    text = re.sub(r'\\textbf\{([^{}]*)\}', r'**\1**', text)
    text = re.sub(r'\\emph\{([^{}]*)\}', r'*\1*', text)
    text = re.sub(r'\\textit\{([^{}]*)\}', r'*\1*', text)
    text = re.sub(r'\\textsc\{([^{}]*)\}', r'\1', text)
    for cmd in _TEXT_COMMANDS:
        text = re.sub(r'\\' + cmd + r'\{([^{}]*)\}', r'\1', text)

    # 7. 常用结构
    text = re.sub(r'\\[dt]frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt(?:\[([^\]]*)\])?\{([^{}]*)\}', r'sqrt(\2)', text)
    text = re.sub(r'\\binom\{([^{}]*)\}\{([^{}]*)\}', r'C(\1,\2)', text)

    # 8. 上下标
    text = re.sub(r'\^\{(.+?)\}', r'^\1', text)
    text = re.sub(r'_\{([^{}]*)\}', r'_\1', text)

    # 9. 符号 / 函数名
    text = _SYMBOL_RE.sub(lambda m: SYMBOLS[m.group(0)], text)
    text = _FUNC_RE.sub(lambda m: m.group(0)[1:], text)

    # 10. 换行
    text = re.sub(r'\\\\[ \t]*(?:\n|$)', '\n', text)
    text = text.replace('\\newline', '\n').replace('\\par', '\n\n')
    text = re.sub(r'\\\\', '\n', text)

    # 11. 清除剩余未知命令
    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)

    # 12. 杂项
    text = text.replace('~', ' ')
    text = text.replace('``', '“').replace("''", '”')
    return text


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def tex_to_markdown(tex_content):
    """LaTeX 题面 → Markdown（数学公式原样保留，供 KaTeX 渲染）。"""
    if not tex_content:
        return ''
    text, blocks = _preprocess(tex_content)

    parts = _MATH_RE.split(text)
    converted = []
    for i, part in enumerate(parts):
        if i % 2 == 1:                       # 奇数下标 = 数学公式
            converted.append(_normalize_math_delimiters(part))
        else:
            converted.append(_convert_text(part))
    text = ''.join(converted)

    text = _restore_verbatim(text, blocks, fenced=True)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def tex_to_plain_text(tex_content):
    """LaTeX 题面 → 纯文本（数学公式降级为 Unicode，FPS 等不支持 KaTeX 的场景用）。"""
    if not tex_content:
        return ''
    text, blocks = _preprocess(tex_content)

    # 数学模式只保留内部内容，再交给普通文本转换
    text = _MATH_RE.sub(lambda m: _strip_math_delimiters(m.group(0)), text)
    text = _convert_text(text)

    text = _restore_verbatim(text, blocks, fenced=False)
    text = text.replace('$', '')
    text = text.replace('{', '').replace('}', '')
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
