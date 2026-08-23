"""对账：原报告说的每一条，本次判读怎么回答。

匹配是机械的，不靠手工连线——原报告条目声明它涉及哪些指标，
判读链条声明它用了哪些指标，两者取交集。
一条原报告结论找不到任何回答，就是构建失败：说明规则库漏了它。

多条原报告条目落到同一个判读上时合并成一行。原报告把"体重指数高"
和"脂肪肝 + GGT 高"分成两条给建议，但那本来就是一件事。
"""
from __future__ import annotations

from ..model import (
    BAND_ORDER, Band, Chain, Correction, Encounter, OriginalFinding,
    Reconciliation, ReconciliationRow, Tag, band_of,
)

# 指标在链条里担任主角的角色。对账优先匹配主角，避免被"背景数值"误吸走。
LEAD_ROLES = {
    "hidden", "lead", "upstream", "abnormal", "finding", "raw",
    "particle", "cargo", "borderline", "structural",
    # 这两个也是主角：急性期蛋白那条链讲的就是这几个指标本身；
    # 影像落点是"常规全正常但组合提示风险"那条链的另一半，不是背景。
    "acute_phase", "anchor",
}


def _codes(chain_or_corr, lead_only: bool) -> set[str]:
    if isinstance(chain_or_corr, Correction):
        refs = (chain_or_corr.flagged,) + chain_or_corr.contradicting
    else:
        refs = chain_or_corr.inputs
    return {e.observation.code for e in refs
            if not lead_only or e.role in LEAD_ROLES}


def reconcile(enc: Encounter, chains: list[Chain],
              corrections: list[Correction]) -> Reconciliation:
    answers: list[tuple[str, object, Band, str, bool]] = []
    for c in corrections:
        answers.append((c.id, c, band_of(Tag.CORRECTION), c.claim_soft, True))
    for ch in chains:
        answers.append((ch.id, ch, band_of(ch.tag), ch.headline or ch.title, False))

    # 纠正优先：它专门针对原报告打箭头的那一项
    answers.sort(key=lambda a: (0 if a[4] else 1, -getattr(a[1], "priority", 0)))

    matched: dict[str, list[OriginalFinding]] = {}
    unaddressed: list[OriginalFinding] = []
    pending: list[OriginalFinding] = []

    for f in enc.original_findings:
        if f.pending:
            pending.append(f)
            continue
        hit = None
        for lead_only in (True, False):     # 先按主角匹配，再放宽到全部
            for aid, obj, _band, _head, _is_corr in answers:
                if f.codes and (set(f.codes) & _codes(obj, lead_only)):
                    hit = aid
                    break
            if hit:
                break
        if hit is None:
            unaddressed.append(f)
        else:
            matched.setdefault(hit, []).append(f)

    rows: list[ReconciliationRow] = []
    for aid, obj, band, headline, is_corr in answers:
        fs = matched.get(aid, [])
        # 没匹配上不等于原报告没提：一条原报告结论可能同时被两条判读回答，
        # 而它只会挂在其中一条上。另一条要说的是"原报告在第 N 条里提过"，
        # 不是"原报告未提及"。
        also = ()
        if not fs:
            mine = _codes(obj, False)
            also = tuple(f.seq for f in enc.original_findings
                         if not f.pending and (set(f.codes) & mine))
        rows.append(ReconciliationRow(
            band=band, headline=headline, findings=tuple(fs),
            chain_id=None if is_corr else aid,
            correction_id=aid if is_corr else None,
            needs_confirm=is_corr,
            is_new=not fs and not also,
            also_from=also,
        ))
    rows.sort(key=lambda r: (BAND_ORDER[r.band], 0 if r.findings else 1,
                             min((f.seq for f in r.findings), default=999)))
    return Reconciliation(rows=tuple(rows), unaddressed=tuple(unaddressed),
                          pending=tuple(pending))
