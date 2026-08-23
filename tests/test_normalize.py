from __future__ import annotations

import pytest

from firstaid.model import RangeKind, RangeStatus
from firstaid.normalize.refrange import judge, parse_range, parse_value


@pytest.mark.parametrize("raw,lo,hi", [
    ("0-300", 0, 300), ("0.40-20.00", 0.4, 20.0), ("[18.5-23.9]", 18.5, 23.9),
    ("10--60", 10, 60), ("17.63~24.47", 17.63, 24.47),
])
def test_parse_bounded(raw, lo, hi):
    r = parse_range(raw)
    assert (r.low, r.high) == (lo, hi)


@pytest.mark.parametrize("raw,lo,hi", [
    (">1.04", 1.04, None), ("≤47.2", None, 47.2), ("<0.5", None, 0.5),
])
def test_parse_single_sided(raw, lo, hi):
    r = parse_range(raw)
    assert (r.low, r.high) == (lo, hi)


def test_unparseable_range_is_none_not_guessed():
    """认不出的区间返回 None → 观察落 NO_RANGE，绝不猜成正常。"""
    assert parse_range("参见说明") is None
    assert parse_range("") is None
    assert judge(5.0, None, None) is RangeStatus.NO_RANGE


def test_censored_value_keeps_its_symbol():
    """"<0.20" 的符号本身是信息：血清叶酸低到测不出，是判读的前提。"""
    v, c = parse_value("<0.20")
    assert (v, c) == (0.20, "<")
    r = parse_range("0.40-20.00")
    assert judge(v, c, r) is RangeStatus.LOW


def test_hscrp_below_detection_limit_is_in_range():
    v, c = parse_value("<0.5")
    assert judge(v, c, parse_range("0-10")) is RangeStatus.IN_RANGE


def test_unknown_indicator_is_recorded_not_dropped(knowledge):
    from firstaid.model import Provenance
    from firstaid.normalize.pipeline import Normalizer
    ont, units, _, _ = knowledge
    n = Normalizer(ont, units)
    out = n.normalize({"raw_name": "某院自定义指标X", "value": 1.0},
                      Provenance(source_id="s"))
    assert out is None
    assert "某院自定义指标X" in n.unresolved


def test_alias_resolution_across_hospitals(knowledge):
    ont, _, _, _ = knowledge
    for name in ["γ-谷氨酰转移酶", "谷氨酰转肽酶", "GGT", "γ-GT"]:
        assert ont.resolve(name) == "GGT", name


def test_lab_percentile_range_is_kept_distinct(zhang):
    coq = zhang.latest().observations.get("COQ10")
    assert coq.ref.kind is RangeKind.LAB_PERCENTILE
    assert coq.status is RangeStatus.LOW      # 确实低于该区间
    assert "不是疾病界值" in coq.ref.source_note
