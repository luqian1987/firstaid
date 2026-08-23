"""对账层的不变式。

新增的核心保证：原报告说的每一条，都必须有一个回答。
这一层不是排版，是断言——找不到回答就是规则库漏了它，构建失败。
"""
from __future__ import annotations

import pytest

from firstaid.model import Band, Tag, band_of
from firstaid.pipeline import analyze


@pytest.fixture
def real(zhang_real, knowledge):
    ont, units, rules, derived = knowledge
    return analyze(zhang_real, ont, units, rules, derived)


def test_every_original_finding_is_answered(real):
    """原报告的每一条结论都必须有回答，标注"报告自取"的除外。"""
    assert real.recon.unaddressed == (), \
        [f"第{f.seq}条「{f.said}」" for f in real.recon.unaddressed]
    answered = sum(len(r.findings) for r in real.recon.rows)
    pending = len(real.recon.pending)
    total = len(real.encounter.original_findings)
    assert answered + pending == total, f"{answered}+{pending} != {total}"


def test_unanswered_original_finding_fails_the_build(real, zhang_real, knowledge):
    """人为塞一条谁也不认领的原报告结论，构建必须失败。"""
    from firstaid.model import OriginalFinding
    ont, units, rules, derived = knowledge
    enc = zhang_real.latest()
    enc.original_findings.append(OriginalFinding(
        seq=99, group="定期复检", source="某项本系统尚无规则的检查",
        said="某指标偏高", advised="建议随诊", codes=("NO_SUCH_CODE",)))
    a = analyze(zhang_real, ont, units, rules, derived)
    assert not a.ok()
    assert any("第 99 条" in m for m in a.blocking()), a.blocking()


def test_findings_about_the_same_thing_merge_into_one_row(real):
    """原报告把体重指数与脂肪肝分成两条给建议，但那本来就是一件事。"""
    merged = [r for r in real.recon.rows if len(r.findings) > 1]
    assert merged, "预期至少有一行合并了多条原报告条目"
    seqs = {tuple(sorted(f.seq for f in r.findings)) for r in merged}
    assert (8, 11) in seqs, seqs      # 体重指数高 + 脂肪肝/GGT高
    assert (12, 15) in seqs, seqs     # MCA M1 狭窄 + 脂蛋白(a)高


def test_only_three_bands_are_exposed(real):
    assert set(real.recon.by_band()) == set(Band)
    assert len(Band) == 3


@pytest.mark.parametrize("tag,band", [
    (Tag.NEEDS_SPECIALIST, Band.ACT), (Tag.SELF_ACTION, Band.ACT),
    (Tag.RETEST_FIRST, Band.CLARIFY),
    (Tag.DOWNGRADE, Band.SETTLE), (Tag.REASSURE, Band.SETTLE),
    (Tag.BASELINE, Band.SETTLE), (Tag.CORRECTION, Band.SETTLE),
])
def test_tag_to_band_is_deterministic(tag, band):
    assert band_of(tag) is band


def test_every_tag_has_a_band():
    for t in Tag:
        assert band_of(t) in Band


def test_corrections_carry_customer_facing_wording(real):
    """对外措辞不许判原报告的对错。"""
    banned = ("不成立", "错了", "有误", "报告错")
    for c in real.corrections:
        assert c.claim_soft.strip()
        assert not any(b in c.claim_soft for b in banned), \
            f"{c.id} 的对外措辞含判定性表述：{c.claim_soft}"


def test_every_chain_has_a_one_line_headline(real):
    for c in real.chains:
        assert c.headline.strip(), c.id
        assert len(c.headline) <= 60, (c.id, len(c.headline))


def test_pending_findings_become_boundaries_not_failures(real):
    """标注"报告自取"的条目进边界，不算构建失败。"""
    assert len(real.recon.pending) == 4
    for f in real.recon.pending:
        assert any(f.source in b.what for b in real.boundaries), f.source
    assert real.ok()
