"""L6 渲染：结构化判读 → HTML 报告。

渲染层不做任何判断。它拿到的每一句话、每一个数字都已经由规则层认定并通过引用校验，
这里只负责排版。所以模板里不允许出现任何条件性的医学措辞。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..model import (
    Chapter, DISPOSITION_LABELS, Disposition, Observation, ObservationKind,
    RangeStatus, TAG_LABELS,
)
from ..pipeline import Analysis

TEMPLATES = Path(__file__).parent / "templates"

CHAPTER_NAV = {
    Chapter.ACT_NOW: "可行动", Chapter.WATCH: "需重视", Chapter.EASY_WIN: "顺手改善",
    Chapter.DOWNGRADE: "可降级", Chapter.BASELINE: "建基线", Chapter.ARCHIVE: "留档",
}

CHAPTER_META = {
    Chapter.ACT_NOW:   ("值得重视，也能主动改善", "既说明现实问题，也给出现在能做的行动"),
    Chapter.WATCH:     ("值得重视，以观察验证为主", "先看清事实和影响，再用可比资料判断变化"),
    Chapter.CORRECT:   ("需纠正", "原报告的建议，按组合判读不成立"),
    Chapter.EASY_WIN:  ("危害不高，但值得顺手改善", "不占用风险焦虑，却有明确、低负担的入口"),
    Chapter.DOWNGRADE: ("可降级 / 可放心", "原报告列为需随诊，按组合判读可以降级"),
    Chapter.BASELINE:  ("建基线", "本次不需要行动，价值全在下次能不能按同一口径比较"),
    Chapter.ARCHIVE:   ("完整留档", "不删除结果，也不让低价值信息挤占主要行动"),
}

TAG_CLASS = {
    "needs_specialist": "act", "correction": "act", "self_action": "act",
    "retest_first": "neutral", "baseline": "neutral",
    "downgrade": "calm", "reassure": "calm",
}


def _bar(o: Observation) -> dict | None:
    """参考区间位置条。区间不完整就不画——不猜一个位置出来。"""
    ref = o.ref if (o.ref and o.ref.bounded) else (
        o.advisory_ref if (o.advisory_ref and o.advisory_ref.bounded) else None)
    if ref is None or o.value is None:
        return None
    lo, hi, val = ref.low, ref.high, o.value
    span = hi - lo
    if span <= 0:
        return None
    d0, d1 = lo - span * 0.55, hi + span * 0.55
    if lo >= 0 and d0 < 0:
        d0 = 0.0
    d0 = min(d0, val - span * 0.15)
    d1 = max(d1, val + span * 0.15)

    def pct(x: float) -> float:
        return max(1.5, min(98.5, (x - d0) / (d1 - d0) * 100))

    return {"lo": pct(lo), "hi": pct(hi), "val": pct(val),
            "advisory": ref is o.advisory_ref}


def _state(o: Observation) -> str:
    if o.status is RangeStatus.HIGH:
        return "hi"
    if o.status is RangeStatus.LOW:
        return "lo"
    if o.status is RangeStatus.IN_RANGE:
        return "ok"
    return "none"


def _ref_label(o: Observation) -> str:
    if o.ref and (o.ref.low is not None or o.ref.high is not None):
        return o.ref.display()
    if o.advisory_ref:
        return f"参考切点 {o.advisory_ref.display()}"
    if o.kind is ObservationKind.DERIVED:
        return "派生值"
    return "无区间"


def tag_of(chain) -> str:
    return TAG_CLASS.get(chain.tag.value, "neutral") if chain else "neutral"


def build_context(a: Analysis) -> dict:
    enc, cov = a.encounter, a.coverage
    obs = list(enc.observations)
    derived = [{"o": o, "note": a.derived_notes.get(o.code)}
               for o in obs
               if o.kind is ObservationKind.DERIVED and o.code != "AGE"]

    chapters = []
    for ch in (Chapter.ACT_NOW, Chapter.WATCH, Chapter.EASY_WIN,
               Chapter.DOWNGRADE, Chapter.BASELINE):
        group = [c for c in a.chains if c.chapter is ch]
        if group:
            title, blurb = CHAPTER_META[ch]
            chapters.append({"key": ch.value, "title": title, "blurb": blurb,
                             "nav": CHAPTER_NAV[ch], "chains": group})

    def prep(refs):
        out = []
        for e in refs:
            o = e.observation
            out.append({"o": o, "role": e.role, "note": e.note,
                        "bar": _bar(o), "state": _state(o), "ref": _ref_label(o)})
        return out

    for chdata in chapters:
        for c in chdata["chains"]:
            c.__dict__["_rows"] = prep(c.inputs)

    corrections = []
    for c in a.corrections:
        corrections.append({
            "c": c, "flagged": prep([c.flagged])[0],
            "rows": prep(c.contradicting),
        })

    confirmed = [o for o in obs
                 if any(r.code == o.code and r.disposition is Disposition.CONFIRMED_OK
                        for r in (cov.records if cov else []))]
    by_system: dict[str, list[Observation]] = {}
    for o in confirmed:
        by_system.setdefault(o.provenance.source_label or "其他", []).append(o)

    # 边界表里不该露出规则 id 和指标 code —— 这些是内部标识，不是给读者看的
    titles = {c.id: c.title for c in a.chains}
    titles.update({c.id: c.claim for c in a.corrections})
    names = {o.code: o.raw_name for o in obs}
    boundaries = [{"what": b.what, "impact": b.impact, "critical": b.critical}
                  for b in a.boundaries]
    missing = [{"label": m.label, "why": m.why, "affects": list(m.affect_titles)}
               for m in a.missing_context]

    n_act = sum(1 for c in a.chains if c.chapter in (Chapter.ACT_NOW, Chapter.WATCH))

    # 首屏论点由最高优先级的那条链条给出，不在模板里写死——
    # 渲染层不做判断，"本次最要紧的是哪一条"是 L4 排序的结论。
    lead = max(a.chains, key=lambda c: c.priority, default=None)
    return {
        "lead": lead,
        "lead_tag": tag_of(lead),
        "subject_id": a.timeline.subject.id,
        "age": a.timeline.subject.age_on(enc.anchor_date),
        "sex": {"male": "男", "female": "女"}.get(a.timeline.subject.sex.value, ""),
        "period": enc.label(),
        "generated": date.today().isoformat(),
        "sources": enc.sources,
        "n_obs": len(obs),
        "n_abnormal": len(enc.observations.abnormal()),
        "n_act": n_act,
        "n_fix": len(a.corrections),
        "n_baseline": len(set(i.key.code for i in a.plan.items)) if a.plan else 0,
        "n_boundary": len(a.boundaries) + len(a.missing_context),
        "chapters": chapters,
        "corrections": corrections,
        "derived": derived,
        "consistency": a.consistency,
        "plan": a.plan,
        "confirmed_by_source": by_system,
        "boundaries": boundaries,
        "missing_context": missing,
        "coverage": cov,
        "cov_hist": [(DISPOSITION_LABELS[Disposition(k)], v)
                     for k, v in sorted((cov.histogram() if cov else {}).items(),
                                        key=lambda x: -x[1])],
        "tag_labels": {k.value: v for k, v in TAG_LABELS.items()},
        "tag_class": TAG_CLASS,
        "unjudged": [names.get(c, c) for c in (cov.unjudged_codes if cov else [])],
    }


def render(a: Analysis, out: str | Path) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATES),
                      autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["disp"] = lambda o: o.display_value()
    html = env.get_template("report.html.j2").render(**build_context(a))
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p
