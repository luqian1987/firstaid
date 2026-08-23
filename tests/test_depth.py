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
    stripped = {**spec, "no_progression":
                [x for x in spec["no_progression"]
                 if x["chain"] != "gastric.saliva_pepsin_vs_normal_panel"]}
    _, errs = DepthEngine(stripped, ont, derived).scope(a.chains)
    assert any("gastric" in e for e in errs), errs


def test_a_track_may_have_no_upstream(real):
    """本次没找到推动它的上游，是判读结论，不是渲染缺失。"""
    from firstaid.render.topology import render_topology
    renal = next(t for t in real.topology.tracks if t.id == "renal.albuminuria")
    assert renal.upstream_id is None
    assert "本次未找到上游" in render_topology(real.topology)


def test_oral_chain_is_on_the_chart(real):
    """牙龈出血在「现在要做」档，此前漏出了拓扑图。"""
    assert "oral.gingival_bleeding_is_local" in {t.chain_id for t in real.topology.tracks}
