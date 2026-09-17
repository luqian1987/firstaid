"""渲染层不做判断，只排版。这里锁死的是"不许泄漏内部标识、不许出现未渲染残留"。"""
from __future__ import annotations

import pytest

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


@pytest.fixture
def real(zhang_real, knowledge):
    from firstaid.pipeline import analyze
    ont, units, rules, derived = knowledge
    return analyze(zhang_real, ont, units, rules, derived)


def _client(a, tmp_path):
    from firstaid.render.client import render_client
    return render_client(a, tmp_path / "c.html").read_text(encoding="utf-8")


def test_client_is_a_projection_of_the_full_report(real, tmp_path):
    """客户版是完整版的投影：它显示的每一条结论，完整版里都必须有。

    两版一旦可以各写各的，就会漂移成两套不一样的医学主张。
    这是这个产品最危险的失败模式，所以它必须是一条断言而不是一条纪律。
    """
    from firstaid.render.html import render
    full = render(a := real, tmp_path / "f.html").read_text(encoding="utf-8")
    cli = _client(a, tmp_path)
    for c in a.chains:
        if c.headline and c.headline in cli:
            assert c.headline in full, c.id


def test_client_gaps_are_all_pointed_at_by_this_report(real):
    """缺失必须是"本次某个结果指向了它"，不能是"套餐里没买这一项"。

    不加这条判据，缺失清单会变成"你没查维生素B6、你没查脾脏厚径"，
    那是凭空制造焦虑。
    """
    for g in real.gaps:
        if g.origin == "rule":
            assert g.evidence, g.what          # 触发它的指标必须真的在场
        assert g.what and g.because, g.what


def test_client_never_promises_a_severity_score(real, tmp_path):
    """客户版不给严重程度评分。分组判据是可逆性，不是我编的风险分级。"""
    cli = _client(real, tmp_path)
    for banned in ("轻度风险", "中度风险", "高危", "健康评分", "风险等级"):
        assert banned not in cli, banned
    assert "等它，会不会变" in cli


def test_client_shows_the_decisive_numbers(real, tmp_path):
    """每条结论要带支撑它的那一两个数。

    上一版只有结论没有凭据，读起来像断言——"从结论的角度说得少"
    的感觉就是从这来的。数字不是全部数值（那是完整版的事），
    是担任主角的那几项。
    """
    cli = _client(real, tmp_path)
    lpa = real.encounter.observations.get("LPA")
    assert lpa.display_value() in cli, "主角指标的数值必须出现在客户版里"


def test_client_overview_covers_every_observation(real):
    """总览不能让任何一项凭空消失。

    "这一次一共查了 196 项"是客户版的第一个事实，
    而它必须等于按身体分区分出去的项数之和。
    """
    from firstaid.assemble.overview import build_overview, load_systems
    from firstaid.render.client import KNOWLEDGE_SYSTEMS
    spec = load_systems(KNOWLEDGE_SYSTEMS)
    rows = build_overview(real.encounter, real.chains, real.ontology, spec)
    from firstaid.assemble.overview import counted
    total = len(counted(real.encounter, real.ontology,
                        set(spec.get("excluded", []))))
    assert sum(r["n"] for r in rows) == total


def test_anatomy_diagram_never_claims_to_be_the_patient_image(real, tmp_path):
    """位置示意图必须每次都写明它不是本人的影像。

    我们手里没有他的原始影像。一张看起来像影像的图，
    读者默认会当成自己的——这是最容易造成误解的一处。
    """
    cli = _client(real, tmp_path)
    if "<svg" in cli and "位置示意图" in cli:
        assert "不是你的影像" in cli
        assert "非本人影像" in cli


def test_anatomy_diagrams_are_registered():
    """规则引用的示意图必须真的存在——写错图名会让位置图静默消失。"""
    from firstaid.loader import load_knowledge
    from firstaid.render.anatomy import DIAGRAMS
    _, _, rules, _ = load_knowledge()
    for r in rules.rules:
        if r.anatomy and r.anatomy.diagram:
            assert r.anatomy.diagram in DIAGRAMS, r.id
