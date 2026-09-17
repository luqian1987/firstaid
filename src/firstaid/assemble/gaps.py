"""收齐「这次体检没回答的」。

四个来源，合成一张表：
  rule      判读显式声明的缺口（triggered_by 全部在场才成立）
  unsettled 判据不全的发现，它的 settled_by 本身就是缺口声明
  pending   原报告做了、但本次没拿到结果的项目 —— 这是客户花过的钱
  context   背景空白：不需要任何检查，但会改变判断

不收的：规则库里有这条规则、而本人压根没有那个发现。
那不是"这次体检的缺失"，是规则库比他的套餐大。
"""
from __future__ import annotations

from ..model import Archetype, Encounter, Gap
from ..patterns.rule import RuleSet

_H_ORDER = {"now": 0, "weeks": 1, "next_checkup": 2, "know_it": 3, "none": 4}


def group_gaps(gaps):
    """同一条判读打开的多个口子合成一组，理由只说一遍。

    立卧位血压和一周血压序列是同一件事的两半，各写一遍"缺的是体位与症状记录"
    只是让人多读一遍同样的话。
    """
    out, index = [], {}
    for g in gaps:
        key = (g.from_chain or g.origin, g.because)
        if key in index:
            index[key]["gaps"].append(g)
            continue
        index[key] = {"because": g.because, "origin": g.origin,
                      "horizon": g.horizon, "free": g.free, "gaps": [g]}
        out.append(index[key])
    return out


def collect_gaps(enc: Encounter, chains, rules: RuleSet,
                 missing_context) -> list[Gap]:
    out: list[Gap] = []
    seen: set[str] = set()

    def add(g: Gap) -> None:
        key = g.what.strip()
        if key in seen:
            return
        seen.add(key)
        out.append(g)

    for c in chains:
        r = rules.by_id(c.id)
        if r is None:
            continue

        # 1) 显式声明的缺口。triggered_by 全在场才算"由结果延伸"
        for spec in r.gaps:
            obs = [o for code in spec.triggered_by
                   if (o := enc.observations.get(code)) is not None]
            if len(obs) != len(spec.triggered_by):
                continue
            add(Gap(what=spec.what, because=spec.because, horizon=spec.horizon,
                    effort=spec.effort, origin="rule", from_chain=c.id,
                    evidence=tuple(obs)))

        # 2) 判据不全的发现：settled_by 就是缺口，主角在场是它成立的前提
        if any(h.archetype is Archetype.UNSETTLED_FINDING for h in c.hits):
            finding = r.params.get("finding")
            fo = enc.observations.get(finding) if finding else None
            if fo is None:
                continue
            for t in r.params.get("settled_by", []):
                if enc.observations.get(t["code"]) is not None:
                    continue          # 做了就不是缺口
                add(Gap(what=t["what"], because=f"{fo.raw_name}：{c.headline}",
                        horizon=(r.horizon.when if r.horizon else "weeks"),
                        effort=t.get("effort", "test"),
                        origin="unsettled", from_chain=c.id, evidence=(fo,)))

    # 3) 花了钱做了、但结果没拿到
    for f in enc.original_findings:
        if not f.pending:
            continue
        add(Gap(what=f.source,
                because="原报告标注「" + (f.said or "详见附件") + "」，本次没有拿到结果",
                horizon="weeks", effort="fetch", origin="pending"))

    # 4) 背景空白：不需要任何检查，但会改变判断
    for m in missing_context:
        n = len(m.affect_titles)
        add(Gap(what=m.label,
                because=f"报告里是空白，而它会改变本次 {n} 条判读的结论",
                horizon="weeks", effort="recall", origin="context"))

    out.sort(key=lambda g: (_H_ORDER.get(g.horizon, 9), 0 if g.free else 1))
    return out
