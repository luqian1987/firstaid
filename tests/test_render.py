"""渲染层不做判断，只排版。这里锁死的是"不许泄漏内部标识、不许出现未渲染残留"。"""
from __future__ import annotations

import re

from firstaid.pipeline import analyze
from firstaid.render.html import render


def _html(tmp_path, tl, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(tl, ont, units, rules, derived)
    p = render(a, tmp_path / "r.html")
    return a, p.read_text(encoding="utf-8")


def test_renders_every_chain_and_correction(tmp_path, zhang, knowledge):
    """每条链条与每条纠正都必须出现在页面上——「可以放下」那档是折叠的 details，
    其余是展开的 section，两者相加应等于链条总数。"""
    a, h = _html(tmp_path, zhang, knowledge)
    for c in a.chains:
        assert f'id="{c.id}"' in h, c.id
    for c in a.corrections:
        assert f'id="{c.id}"' in h, c.id
        assert c.claim_soft in h


def test_no_unrendered_template_markers(tmp_path, zhang, knowledge):
    _, h = _html(tmp_path, zhang, knowledge)
    assert not re.search(r"\{\{|\{%", h)
    assert ">None<" not in h and "undefined" not in h


def test_no_internal_identifiers_leak(tmp_path, zhang, knowledge):
    """规则 id 和指标 code 是内部标识，不该出现在给人看的报告里。"""
    _, h = _html(tmp_path, zhang, knowledge)
    body = h.split("<body>")[1]
    text = re.sub(r"<[^>]+>", " ", body)
    leaked = re.findall(r"\b[a-z]+\.[a-z_]{4,}\b", text)
    assert leaked == [], leaked


def test_hero_counts_come_from_the_data(tmp_path, zhang, knowledge):
    """首屏数字不许写死在模板里——它们是对账层的结论。"""
    from firstaid.model import Band
    a, h = _html(tmp_path, zhang, knowledge)
    thesis = re.search(r'<h1 class="thesis">(.*?)</h1>', h, re.S).group(1)
    n_act = len(a.recon.by_band()[Band.ACT])
    assert f"<em>{n_act} 件</em>" in thesis


def test_correction_shows_soft_wording_not_internal_claim(tmp_path, zhang, knowledge):
    """对外只出现 claim_soft。内部精确说法（"不成立"这类）不许露给客户。"""
    a, h = _html(tmp_path, zhang, knowledge)
    body = h.split("<body>")[1]
    for c in a.corrections:
        assert c.claim_soft in body
        if c.claim != c.claim_soft:
            assert c.claim not in body, c.id


def test_report_does_not_print_personal_name(tmp_path, zhang, knowledge):
    _, h = _html(tmp_path, zhang, knowledge)
    assert "张韦韦" not in h


def test_advisory_cutoff_is_labelled_as_such(tmp_path, zhang, knowledge):
    """本系统补的常用切点必须标明，不许看起来像原报告给的区间。"""
    _, h = _html(tmp_path, zhang, knowledge)
    assert "参考切点" in h


def test_every_css_variable_is_defined():
    """用到的 CSS 变量必须在 :root 里定义过。

    --calm / --calm-bg 从来没有定义过，于是"可以放下"那一档的几处绿色
    一直在静默回退到继承值——渲染不报错，颜色只是"看起来有点怪"。
    与规则层的静默失效同一族：能变成断言的就变成断言。
    """
    import re
    from pathlib import Path
    tpl = (Path(__file__).resolve().parents[1] / "src" / "firstaid" / "render"
           / "templates" / "report.html.j2").read_text(encoding="utf-8")
    root = tpl[tpl.index(":root{"):tpl.index("}", tpl.index(":root{"))]
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", root))
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", tpl))
    assert used <= defined, f"这些变量没有定义: {sorted(used - defined)}"
