"""L5 覆盖率审计。

不变式：每一条观察恰好一个归宿。异常项没有归宿 → 构建失败，不出报告。

这一层的作用不是好看，是让"我们看过了"这句话变成可验证的断言。
它同时会主动暴露规则库的缺口：某个异常项反复落进 UNRESOLVED，
说明知识库缺一条规则，而不是说明这次数据特殊。
"""
from __future__ import annotations

from ..model import (
    Chapter, CoverageReport, Disposition, Encounter, Ontology, RangeStatus, TriState,
)
from ..patterns.engine import EngineResult

_CHAPTER_DISPOSITION = {
    Chapter.CORRECT: Disposition.CORRECTED,
    Chapter.DOWNGRADE: Disposition.DOWNGRADED,
    Chapter.BASELINE: Disposition.BASELINE,
}


def build_coverage(enc: Encounter, result: EngineResult,
                   ontology: Ontology) -> CoverageReport:
    # 年龄这类人口学字段是计算输入，不是体检观察，不进覆盖率账
    clinical = [o for o in enc.observations
                if (d := ontology.get(o.code)) is None or d.system != "demographics"]
    rep = CoverageReport.start(clinical)

    # 1) 命中的规则按章节认领
    for chain in result.chains:
        d = _CHAPTER_DISPOSITION.get(chain.chapter, Disposition.CHAINED)
        for e in chain.inputs:
            rep.claim(e.observation.code, d, by=chain.id)
    for corr in result.corrections:
        rep.claim(corr.flagged.observation.code, Disposition.CORRECTED, by=corr.id)
        for e in corr.contradicting:
            rep.claim(e.observation.code, Disposition.CORRECTED, by=corr.id)

    # 2) 输入不全的规则，把它缺的那些登记为边界（而不是当作正常）
    #    但要分清两种"判定不了"：
    #      · 本次没做这项检查 —— 数据缺口，合法，登记为边界；
    #      · 做了、有值，而本系统对它没有任何判据 —— 知识库缺口，构建失败。
    #    不分开的话，缺一个切点就让整条规则静默失效，构建还是绿的。
    for hit in result.indeterminate:
        for code in hit.missing_codes:
            o = enc.observations.get(code)
            if (o is not None and o.value is not None
                    and not o.judged and not o.has_advisory):
                rep.no_criterion.append((code, o.raw_name, hit.rule_id))
                rep.claim(code, Disposition.INDETERMINATE, by=hit.rule_id,
                          note="本系统对它没有任何判据")
                continue
            rep.claim(code, Disposition.INDETERMINATE, by=hit.rule_id,
                      note="规则想用它但判定不了")

    # 3) 剩下的按状态兜底
    for o in clinical:
        rec = next((r for r in rep.records if r.code == o.code), None)
        if rec is None or rec.disposition is not Disposition.UNRESOLVED:
            continue
        if o.status is RangeStatus.IN_RANGE:
            rep.claim(o.code, Disposition.CONFIRMED_OK, by="coverage:in_range")
        elif o.status is RangeStatus.NO_RANGE:
            rep.claim(o.code, Disposition.BASELINE if o.kind.value == "imaging"
                      else Disposition.ARCHIVED, by="coverage:no_range")
        elif o.status is RangeStatus.UNKNOWN:
            rep.unjudged_codes.append(o.code)
            rep.claim(o.code, Disposition.ARCHIVED, by="coverage:unknown",
                      note="有值但无法判定高低，保留原值，不据此安排干预")
        # abnormal 的留在 UNRESOLVED —— 这就是构建失败信号

    for src in enc.sources:
        for page in src.unreadable_pages:
            rep.unreadable_pages.append(f"{src.label}第{page}页")
    return rep
