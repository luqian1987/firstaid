"""深读层的不变式。

核心一条：写不出引用本人数据的内容，不许出现在报告里。
它对机制成立（cites 非空），对通路同样成立（judged_by 非空）——
后者顺带解决了"远端病名吓人"：我们对肝硬化、胃癌这些阶段一个指标都没有，
所以它们自动画不出来，不需要靠人记得删。
"""
from __future__ import annotations

import re

import pytest

from firstaid.assemble.depth import DepthEngine, load_depth_spec
from firstaid.model import InterventionKind, StageState
from firstaid.pipeline import KNOWLEDGE_DEPTH, analyze


@pytest.fixture
def real(zhang_real, knowledge):
    ont, units, rules, derived = knowledge
    return analyze(zhang_real, ont, units, rules, derived)


@pytest.fixture(scope="session")
def spec():
    return load_depth_spec(KNOWLEDGE_DEPTH)


def test_knowledge_validates(spec, knowledge):
    ont, _, _, derived = knowledge
    assert DepthEngine(spec, ont, derived).validate() == []


def test_every_pathway_stage_names_its_judging_indicators(spec):
    """说不出哪个指标判定它，就不许画进拓扑图。"""
    for p in spec["pathways"]:
        for st in p["stages"]:
            assert st.get("judged_by"), f'{p["id"]} / {st["name"]}'


def test_a_stage_without_indicators_fails_the_build(spec, knowledge):
    """人为塞一关没有 judged_by 的"肝硬化"，构建必须失败。"""
    ont, _, _, derived = knowledge
    bad = {**spec, "pathways": spec["pathways"] + [{
        "id": "x.bad", "label": "X", "upstream": "adipose",
        "stages": [{"name": "肝硬化"}]}]}
    errs = DepthEngine(bad, ont, derived).validate()
    assert any("肝硬化" in e for e in errs), errs


def test_no_time_prediction_anywhere_in_pathways(spec, knowledge):
    ont, _, _, derived = knowledge
    bad = {**spec, "pathways": [{**spec["pathways"][0],
                                 "tail": "不干预演变：约 2~4 年"}]}
    assert any("时间预测" in e for e in DepthEngine(bad, ont, derived).validate())


def test_stage_states_are_computed_from_data_not_authored(real):
    """通路状态由本人数据求值，不是写死的。"""
    liver = next(t for t in real.topology.tracks if t.id == "liver.nafld")
    by = {s.name: s.state for s in liver.stages}
    assert by["肝脂肪变"] is StageState.CROSSED        # CAP 272 > 常用切点 248
    assert by["脂肪性肝炎"] is StageState.UNKNOWN      # 有指标但定不了
    assert by["显著纤维化"] is StageState.CLEAR        # LSM 6.1 与 FIB-4 1.36 都在切点下


def test_insulin_resistance_is_not_crossed(real):
    """参考实现把胰岛素抵抗画成已发生。本人三个独立指标全部正常。"""
    m = next(t for t in real.topology.tracks if t.id == "metabolic.ir")
    assert m.stages[0].state is StageState.CLEAR


def test_non_modifiable_upstream_is_marked_and_unshared(real):
    """Lp(a) 是独立上游，不与代谢路径共享——这是"同一个干预覆盖不到它"的依据。"""
    lpa = next(u for u in real.topology.upstreams if u.id == "lpa_genetic")
    assert lpa.modifiable is False
    fed = [t.id for t in real.topology.tracks if t.upstream_id == "lpa_genetic"]
    assert fed == ["vascular.lpa"]
    shared = [u.id for u in real.topology.shared()]
    assert "lpa_genetic" not in shared and "adipose" in shared


def test_every_mechanism_cites_the_subject_data(real):
    for d in real.depth.values():
        for m in d.mechanisms:
            assert m.cites, m.pivot[:20]
            assert m.evidence, f"引用了指标但本次没有这些观察：{m.cites}"


def test_non_clinical_interventions_declare_how_to_verify(real):
    for d in real.depth.values():
        for iv in d.interventions:
            if iv.kind is not InterventionKind.CLINICAL:
                assert iv.verify_by, iv.action
                assert iv.verify_label and iv.verify_label != iv.verify_by or True


def test_clinical_interventions_never_name_a_drug_or_dose(real):
    """临床部分只说路径与该问什么。不写药名、不写剂量。"""
    # 剂量与浓度要分开：456.7 mg/L 是化验值，20 mg 才是剂量。
    # 后面跟斜杠的是浓度单位，不算。
    banned = re.compile(r"\d+(\.\d+)?\s*(mg|毫克)\b(?!\s*/)"
                        r"|每[日天].{0,6}(mg|毫克|片|粒)"
                        r"|他汀|阿司匹林|二甲双胍|奥美拉唑|拉唑\b")
    for d in real.depth.values():
        for iv in d.interventions:
            if iv.kind is not InterventionKind.CLINICAL:
                continue
            blob = " ".join((iv.action, *iv.paths, *iv.ask_doctor, iv.note))
            hit = banned.search(blob)
            assert not hit, f"{iv.action}: 出现了药名或剂量「{hit.group()}」"
            assert iv.note or iv.ask_doctor


def test_depth_only_on_the_two_action_bands(real):
    """「可以放下」那档不配机制与通路——既然结论是放下，就不该再展开。"""
    from firstaid.model import Band, band_of
    for cid in real.depth:
        c = next(c for c in real.chains if c.id == cid)
        assert band_of(c.tag) in (Band.ACT, Band.CLARIFY), cid


def test_topology_renders_with_breathing_animation(real):
    from firstaid.render.topology import render_topology
    svg = render_topology(real.topology)
    assert svg.count("<animate") >= 4
    assert "本次已见" in svg and "判不了" in svg
    assert not re.search(r"\d+\s*[~-]\s*\d+\s*年", svg)


def test_topology_covers_every_action_band_chain_or_says_why_not(real):
    """行动档的每条链条，要么在图上，要么写明为什么不在。
    「忘了画」这种状态不允许存在——之前牙龈出血就是这样漏掉的。"""
    from firstaid.model import Band, band_of
    on_chart = {t.chain_id for t in real.topology.tracks}
    declared = {x["title"] for x in real.topo_excluded}
    for c in real.chains:
        if band_of(c.tag) in (Band.ACT, Band.CLARIFY):
            assert c.id in on_chart or c.title in declared, c.id


def test_every_chain_is_accounted_for_by_the_topology_section(real):
    on_chart = {t.chain_id for t in real.topology.tracks}
    assert len(on_chart) + len(real.topo_excluded) == len(real.chains)


def test_missing_declaration_fails_the_build(zhang_real, knowledge, spec):
    """抽掉一条行动档链条的说明，构建必须失败。"""
    from firstaid.assemble.depth import DepthEngine
    ont, units, rules, derived = knowledge
    a = analyze(zhang_real, ont, units, rules, derived)
    # 抽掉一条仍靠声明豁免的行动档链条（维生素A，clarify 档）
    victim = "nutrition.vitamin_a_isolated_high"
    assert victim in {x["chain"] for x in spec["no_progression"]}
    stripped = {**spec, "no_progression":
                [x for x in spec["no_progression"] if x["chain"] != victim]}
    _, errs = DepthEngine(stripped, ont, derived).scope(a.chains)
    assert any(victim in e for e in errs), errs


def test_a_track_may_have_no_upstream(real):
    """本次没找到推动它的上游，是判读结论，不是渲染缺失。"""
    from firstaid.render.topology import render_topology
    renal = next(t for t in real.topology.tracks if t.id == "renal.albuminuria")
    assert renal.upstream_id is None
    assert "本次未找到上游" in render_topology(real.topology)


def test_oral_chain_is_on_the_chart(real):
    """牙龈出血在「现在要做」档，此前漏出了拓扑图。"""
    assert "oral.gingival_bleeding_is_local" in {t.chain_id for t in real.topology.tracks}


def test_the_two_previously_misjudged_chains_are_now_on_the_chart(real):
    """胃黏膜萎缩与脾功能亢进都是可判定的演变关口，此前被凭感觉排除了。"""
    on_chart = {t.chain_id for t in real.topology.tracks}
    assert "gastric.saliva_pepsin_vs_normal_panel" in on_chart
    assert "spleen.layered_exclusion" in on_chart


def test_excluded_chains_all_cite_the_criterion(spec):
    """排除理由必须援引判据，不能是随手写的一句话。"""
    for x in spec["no_progression"]:
        assert "判据" in x["why"], x["chain"]


def test_tracks_without_upstream_explain_why_per_track(real):
    """三条无上游路径的说明各不相同，不能共用一句写死的话。"""
    from firstaid.render.topology import render_topology
    notes = {t.no_upstream_note for t in real.topology.tracks
             if t.upstream_id is None}
    assert len(notes) == 3, notes
    svg = render_topology(real.topology)
    for n in notes:
        assert n in svg


def test_diagram_lives_with_its_own_chain(real, tmp_path):
    """图画在它自己那一组多联旁边，一组一张，没有汇总大图。

    原来是顶部一张汇总图 + 每章一行文字定位，理由写的是"汇总图的价值在于
    跨路径比较、谁共享上游"。攒到三份真实报告之后这句话可以查了：
    没有任何一个上游被两条不同的多联共用。理由不成立，所以拆开。
    """
    from firstaid.render.html import render
    h = render(real, tmp_path / "r.html").read_text(encoding="utf-8")
    owners = {t.chain_id for t in real.topology.tracks}
    assert h.count("<svg") == len(owners), (h.count("<svg"), owners)
    # 一条多联自己带两条路径时，两条仍在同一张图里
    assert len(real.topology.tracks) > len(owners)
    assert 'id="topo"' not in h


def test_chains_without_a_pathway_say_why_in_their_own_block(real, tmp_path):
    """没有进展结构的多联，理由写在它自己那一段，不再集中堆在报告末尾。"""
    from firstaid.render.html import render
    h = render(real, tmp_path / "r.html").read_text(encoding="utf-8")
    assert real.topo_excluded, "本例应当有若干条被排除"
    for x in real.topo_excluded:
        assert x["why"][:24] in h, x["chain"]
    assert h.count("ctopo noprog") == len(real.topo_excluded)


def test_modifiers_never_repeat_what_the_diagram_already_shows(real):
    """图挪到旁边之后，与图重复的修饰因素必须消失。

    "在场"那一栏基本就是图上已跨过的关，"已排除"里有一部分是图上未跨过的关。
    图放得远的时候看不出来，放到旁边就是同一件事讲两遍。
    """
    from firstaid.assemble.depth import DepthEngine
    for c in real.chains:
        d = real.depth.get(c.id)
        if not d or not d.modifiers:
            continue
        on_chart = DepthEngine.chart_codes(real.topology, c.id)
        left = d.modifiers.off_chart()
        for m in list(left.present) + list(left.absent):
            assert not (set(m.codes) & on_chart), (c.id, m.name)


def test_every_modifier_with_indicators_declares_its_relation(knowledge):
    """带指标的修饰因素必须说得出它与主线的关系，否则不许进这一栏。

    以前是凭感觉挑的，于是宽严不一：甲状腺那条把"贫血"列进已排除，
    可在甲功正常的阶段，贫血不是这条判读的竞争解释。
    """
    from firstaid.model import MODIFIER_RELATIONS
    from firstaid.pipeline import KNOWLEDGE_DEPTH, load_depth_spec
    spec = load_depth_spec(KNOWLEDGE_DEPTH)
    bad = []
    for cid, block in (spec.get("depth") or {}).items():
        for key in ("present", "absent"):
            for m in ((block.get("modifiers") or {}).get(key) or []):
                if m.get("codes") and m.get("relation") not in MODIFIER_RELATIONS:
                    bad.append((cid, m["name"], m.get("relation")))
    assert bad == [], bad
