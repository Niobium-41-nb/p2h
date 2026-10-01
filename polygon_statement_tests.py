#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""polygon_statement.py 的回归测试（直接运行：python polygon_statement_tests.py）

覆盖两类曾经真实踩过的坑：

* **软换行**：HOJ / Hydro 前端 markdown-it 开着 breaks:true，源文件里段落内的单个
  换行会被渲染成 <br>，必须折叠成空格（LaTeX 语义），否则每个 $公式$ 都会被顶到
  单独一行。
* **数学模式**：数学公式必须原样保留给 KaTeX；符号替换必须最长匹配优先，
  不能把 \\leq 变成 ≤q、\\infty 变成 ∈fty、\\subseteq 变成 ⊂eq。
"""

import polygon_statement as ps


def test_soft_newlines_collapsed():
    """每个 $公式$ 独占一行时，转换结果必须回到行内。"""
    tex = '已知初始（第\n$0$\n天）有\n$n$\n个麦当劳。\n\n第二段\n$m$\n天。'
    md = ps.tex_to_markdown(tex)
    assert '\n$0$\n' not in md
    assert '已知初始（第 $0$ 天）有 $n$ 个麦当劳。' in md
    # 空行仍然分段
    assert '\n\n第二段 $m$ 天。' in md
    print('  ok  软换行折叠为空格、空行保留')


def test_math_protected_from_symbols():
    """数学模式内的命令不能被替换掉。"""
    md = ps.tex_to_markdown(r'$a \leq b$、$x \times y$、$u \gets v$、$k$ 与 $m$')
    assert md == r'$a \leq b$、$x \times y$、$u \gets v$、$k$ 与 $m$'
    assert '≤q' not in md and '×' not in md
    print('  ok  数学模式原样保留')


def test_longest_match_symbols():
    """非数学部分：最长匹配优先，不产生 ≤q / ∈fty / ⊂eq。"""
    md = ps.tex_to_markdown(r'若 $x \in \mathbb{R}$ 且 $S \subseteq T$，则 $x \to \infty$。')
    assert r'\in' in md and r'\subseteq' in md and r'\to' in md
    assert r'\infty' in md
    plain = ps.tex_to_plain_text(r'$x \in \mathbb{R}$，$S \subseteq T$，$\gets \infty \int \top$')
    for bad in ('≤q', '≥q', '∈fty', '⊂eq', '⊃eq', '→p', '∈t'):
        assert bad not in plain, bad
    assert '∞' in plain and '∫' in plain and '⊆' in plain
    print('  ok  符号最长匹配优先')


def test_lists_and_quotes():
    tex = ("当且仅当：\n\n\\begin{itemize}\n"
           "\\item $1 \\leq l \\leq r \\leq n$.\n"
           "\\item 区间 $[l, r]$ 内必须包含权值为 $k$ 的货物。\n"
           "\\end{itemize}\n\n进入``拿捏领域''状态。")
    md = ps.tex_to_markdown(tex)
    assert '- $1 \\leq l \\leq r \\leq n$.' in md
    assert '\n- 区间 $[l, r]$ 内必须包含权值为 $k$ 的货物。' in md
    assert '“拿捏领域”' in md
    print('  ok  列表与引号')


def test_math_delimiters_normalized():
    md = ps.tex_to_markdown(r'行内 \(a \le b\) 与块级 \[c \le d\]。')
    assert '$a \\le b$' in md
    assert '$$c \\le d$$' in md
    print('  ok  \\(...\\) / \\[...\\] 归一化为 $...$ / $$...$$')


def test_footnote_and_comment():
    tex = '整数 % 这是注释，整行其余部分应消失\n\\footnote{表示不超过 $x$ 的最大整数。} 的 $\\lfloor x\\rfloor$ 值，以及 $k\\%$。'
    md = ps.tex_to_markdown(tex)
    assert '这是注释' not in md
    assert '（表示不超过 $x$ 的最大整数。）' in md
    assert r'$k\%$' in md
    print('  ok  注释删除与脚注内联')


def test_paragraphs_preserved():
    tex = '第一段第一行\n第一段第二行\n\n第二段'
    md = ps.tex_to_markdown(tex)
    assert md == '第一段第一行 第一段第二行\n\n第二段'
    print('  ok  段落保留')


def test_plain_text_strips_math():
    plain = ps.tex_to_plain_text(r'答案是 $\lfloor t \times k\% \rfloor$，其中 $a \le b$。')
    assert '$' not in plain
    assert '⌊ t × k% ⌋' in plain
    assert 'a ≤ b' in plain
    print('  ok  纯文本降级（FPS）')


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'\n全部 {len(tests)} 组测试通过')


if __name__ == '__main__':
    main()
