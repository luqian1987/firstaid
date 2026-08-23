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
    a, h = _html(tmp_path, zhang, knowledge)
    assert h.count('<section class="chain"') == len(a.chains)
    assert h.count('<section class="fix"') == len(a.corrections)


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


def test_hero_headline_comes_from_top_ranked_chain(tmp_path, zhang, knowledge):
    """首屏论点不许写死在模板里——它是 L4 排序的结论。"""
    a, h = _html(tmp_path, zhang, knowledge)
    lead = max(a.chains, key=lambda c: c.priority)
    assert lead.title in h
    thesis = re.search(r'<h1 class="thesis">(.*?)</h1>', h, re.S).group(1)
    assert lead.title in thesis


def test_report_does_not_print_personal_name(tmp_path, zhang, knowledge):
    _, h = _html(tmp_path, zhang, knowledge)
    assert "张韦韦" not in h


def test_advisory_cutoff_is_labelled_as_such(tmp_path, zhang, knowledge):
    """本系统补的常用切点必须标明，不许看起来像原报告给的区间。"""
    _, h = _html(tmp_path, zhang, knowledge)
    assert "参考切点" in h
