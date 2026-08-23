from __future__ import annotations

import pytest

from firstaid.model import Chapter, Disposition, Modifiability, RangeStatus
from firstaid.pipeline import analyze


def test_pipeline_builds(zhang, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    assert a.blocking() == [], a.blocking()
    assert a.ok()


def test_coverage_every_observation_has_a_disposition(zhang, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    cov = a.coverage
    assert cov is not None
    assert cov.unresolved_abnormal() == [], \
        [r.code for r in cov.unresolved_abnormal()]
    assert cov.duplicated() == []


def test_lpa_never_lands_in_actionable_chapter(zhang, knowledge):
    """参考实现把 Lp(a) 归进"也能主动改善"章并配了饮食运动方案。

    这条测试锁死那个分类错误：不可由本人改变的主线，绝不进可行动章。
    """
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    lpa = next(c for c in a.chains if c.id == "lipid.lpa_intracranial_lead")
    assert lpa.modifiability is Modifiability.NOT_MODIFIABLE
    assert lpa.chapter is not Chapter.ACT_NOW
    assert ont.modifiability("LPA") is Modifiability.NOT_MODIFIABLE


def test_chapter_invariant_is_enforced(zhang, knowledge):
    """把 Lp(a) 那条链强行改到可行动章，构建必须失败。"""
    from firstaid.assemble.rank import check_chapters
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    lpa = next(c for c in a.chains if c.id == "lipid.lpa_intracranial_lead")
    tampered = lpa.model_copy(update={"chapter": Chapter.ACT_NOW})
    errs = check_chapters([tampered])
    assert errs and "不可由本人改变" in errs[0]


def test_corrections_must_cite_same_report_evidence(zhang, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    assert len(a.corrections) == 4
    for c in a.corrections:
        assert c.contradicting, f"{c.id} 没有引用反证"
        for e in c.contradicting:
            assert e.observation.provenance.source_id, "反证必须有出处"


def test_correction_cannot_be_built_without_contradicting_evidence():
    from pydantic import ValidationError
    from firstaid.model import Correction, EvidenceRef, Observation, Provenance
    o = Observation(code="X", raw_name="x",
                    provenance=Provenance(source_id="s"))
    with pytest.raises(ValidationError):
        Correction(id="bad", claim="c", original_advice="a", original_source="s",
                   flagged=EvidenceRef(observation=o, role="abnormal"),
                   contradicting=(), why_not="w", what_to_do="d")


def test_advisory_range_never_masquerades_as_report_range(zhang):
    """原报告没给区间的项目，status 必须是 NO_RANGE，
    常用切点只出现在 advisory_* 字段里。"""
    enc = zhang.latest()
    lsm = enc.observations.get("LSM")
    assert lsm.status is RangeStatus.NO_RANGE
    assert lsm.has_advisory and lsm.advisory_in_range
    assert lsm.advisory_source and "知识库补充" in lsm.advisory_source


def test_missing_context_is_registered_not_assumed(zhang, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    keys = {m.key.value for m in a.missing_context}
    assert {"alcohol_intake", "medications", "smoking",
            "family_early_cvd"} <= keys


def test_single_point_is_declared_a_boundary(zhang, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    assert any("没有既往体检数据" in b.what for b in a.boundaries)


def test_comparison_plan_carries_device_sensitivity(zhang, knowledge):
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    cap = next(i for i in a.plan.items if i.key.code == "CAP")
    assert cap.key.device_sensitive
    assert cap.key.device == "FibroScan-A"


def test_narration_citations_are_verified(zhang, knowledge):
    from firstaid.render.narrate import verify_chain
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    errs = [e for c in a.chains for e in verify_chain(c)]
    assert errs == [], errs


def test_fabricated_number_is_rejected(zhang, knowledge):
    """叙述器凭空写出一个 evidence 里没有的数值，必须被拒。"""
    from firstaid.render.narrate import verify_citations
    ont, units, rules, derived = knowledge
    a = analyze(zhang, ont, units, rules, derived)
    chain = a.chains[0]
    bad = verify_citations("他的某项指标是 987.65，需要处理。", chain.brief)
    assert 987.65 in bad
