"""审计层的两条不变式，都是被真实病例逼出来的。

一、"判不了"分两种。本次没做这项检查是数据缺口，合法；
    做了、有值，而本系统对它没有任何判据，是知识库缺口——
    不区分的话，缺一个切点就让整条规则静默失效，而构建还是绿的。

二、规则要能跨病人复用。规则引用的某项在下一个人身上不存在是常态，
    不能因此整条崩溃；但如果一条都不剩，那条判读就给不出可比基线，必须报错。
"""
from __future__ import annotations

import datetime as dt

import pytest

from firstaid.audit.coverage import build_coverage
from firstaid.model import (
    Archetype, Encounter, Observation, Ontology, PatternHit, Provenance,
    RangeStatus, RefRange, TriState,
)
from firstaid.patterns.engine import EngineResult


def _obs(code, **kw):
    return Observation(code=code, raw_name=code,
                       provenance=Provenance(source_id="s"), **kw)


def _enc(*obs):
    e = Encounter(id="e", subject_id="s", date_from=dt.date(2024, 1, 1))
    for o in obs:
        e.observations.add(o)
    return e


def _indeterminate(rule_id, *missing):
    return EngineResult(hits=[PatternHit(
        rule_id=rule_id, archetype=Archetype.RISK_CONVERGENCE,
        state=TriState.INDETERMINATE, missing_codes=tuple(missing))])


def test_measured_but_unjudgeable_input_fails_the_build():
    """指标测了、有值，而本系统给不出任何判据 —— 知识库缺口，构建必须失败。

    腰臀比 0.92 就是这样溜过去的：派生值不带区间，知识库也没给切点，
    于是 check_state 返回 None，整条动脉粥样硬化判读静默变成"判不了"，
    而构建报告一切正常。
    """
    enc = _enc(_obs("WHR", value=0.92, status=RangeStatus.NO_RANGE))
    rep = build_coverage(enc, _indeterminate("athero.demo", "WHR"), Ontology())
    assert rep.no_criterion == [("WHR", "WHR", "athero.demo")]
    assert not rep.ok()
    assert any("没有任何判据" in f for f in rep.failures())


def test_advisory_cutoff_counts_as_a_criterion():
    """补上带出处的常用切点之后，同一项就不再是知识库缺口。"""
    enc = _enc(_obs("WHR", value=0.92, status=RangeStatus.NO_RANGE,
                    advisory_ref=RefRange(high=0.90),
                    advisory_status=RangeStatus.HIGH,
                    advisory_source="WHO 2008"))
    rep = build_coverage(enc, _indeterminate("athero.demo", "WHR"), Ontology())
    assert rep.no_criterion == []


def test_test_not_done_is_a_data_gap_not_a_build_failure():
    """本次没做这项检查 —— 合法，登记为边界，不失败。"""
    enc = _enc(_obs("HDL_C", value=1.4, status=RangeStatus.IN_RANGE))
    rep = build_coverage(enc, _indeterminate("athero.demo", "HBA1C"), Ontology())
    assert rep.no_criterion == []
    assert rep.ok()


def test_compare_next_survives_a_missing_indicator(knowledge):
    """规则列在"下次比什么"里的某项，下一个人没做 —— 跳过，不是规则写错。"""
    from firstaid.loader import load_fixture
    from firstaid.patterns.engine import PatternEngine
    from firstaid.patterns.context import RuleContext
    from conftest import FIXTURES

    ont, units, rules, derived = knowledge
    tl, _ = load_fixture(FIXTURES / "case2_2024-08-03.yaml", ont, units)
    enc = tl.latest()
    from firstaid.derive.engine import DeriveEngine
    DeriveEngine(derived, tl.subject.sex).run(enc)
    res = PatternEngine(rules, ont).run(RuleContext(enc))
    ledger = next(c for c in res.chains if c.id == "structural.baseline_ledger")
    codes = {i.key.code for i in ledger.verdict.compare_next}
    # 病例 2 没做 FibroScan，所以 CAP / LSM 两项该被跳过而不是让规则崩溃
    assert "CAP" not in codes and "LSM" not in codes
    assert codes, "compare_next 全被跳过时应当报错，而不是给出空基线"
