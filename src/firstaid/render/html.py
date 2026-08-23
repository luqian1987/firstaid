"""L6 渲染：结构化判读 → HTML 报告。

渲染层不做任何判断。它拿到的每一句话、每一个数字都已经由规则层认定并通过引用校验，
这里只负责排版。所以模板里不允许出现任何条件性的医学措辞。

信息架构：
    对账表（原报告每条 → 我们的回答）既是首屏也是目录，
    三条色带取代七个章节，「可以放下」整段折叠，「与医生确认」是叠加标记而非独立分类。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..model import (
    BAND_COLOR, BAND_META, Band, Disposition, Observation, ObservationKind,
    RangeStatus,
)
from ..pipeline import Analysis

TEMPLATES = Path(__file__).parent / "templates"


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

    return {"lo": pct(lo), "hi": pct(hi), "val": pct(val)}


def _state(o: Observation) -> str:
    return {RangeStatus.HIGH: "hi", RangeStatus.LOW: "lo",
            RangeStatus.IN_RANGE: "ok"}.get(o.status, "none")


def _ref_label(o: Observation) -> str:
    if o.ref and (o.ref.low is not None or o.ref.high is not None):
        return o.ref.display()
    if o.advisory_ref:
        return f"参考切点 {o.advisory_ref.display()}"
    if o.kind is ObservationKind.DERIVED:
        return "派生值"
    return "无区间"


def _rows(refs) -> list[dict]:
    return [{"o": e.observation, "note": e.note, "bar": _bar(e.observation),
             "state": _state(e.observation), "ref": _ref_label(e.observation)}
            for e in refs]


def build_context(a: Analysis) -> dict:
    enc, cov, recon = a.encounter, a.coverage, a.recon
    obs = list(enc.observations)
    chains = {c.id: c for c in a.chains}
    corrs = {c.id: c for c in a.corrections}

    bands = []
    for b in Band:
        rows = recon.by_band()[b] if recon else []
        detail = []
        for r in rows:
            if r.correction_id:
                continue          # 纠正统一收进「与医生确认」区，不在色带里重复
            c = chains.get(r.chain_id)
            if c:
                detail.append({"c": c, "rows": _rows(c.inputs), "recon": r})
        label, desc = BAND_META[b]
        color, bg = BAND_COLOR[b]
        bands.append({"key": b.value, "label": label, "desc": desc,
                      "color": color, "bg": bg, "rows": rows, "chains": detail,
                      "n": len(rows)})

    confirms = []
    for r in (recon.rows if recon else []):
        if not r.correction_id:
            continue
        c = corrs[r.correction_id]
        confirms.append({"c": c, "recon": r, "flag": _rows([c.flagged])[0],
                         "rows": _rows(c.contradicting)})

    confirmed_ok = [o for o in obs
                    if any(rec.code == o.code
                           and rec.disposition is Disposition.CONFIRMED_OK
                           for rec in (cov.records if cov else []))]
    by_src: dict[str, list[Observation]] = {}
    for o in confirmed_ok:
        by_src.setdefault(o.provenance.source_label or "其他", []).append(o)

    n_orig = len([f for f in enc.original_findings if not f.pending])
    return {
        "subject_id": enc.subject_id.upper(),
        "age": a.timeline.subject.age_on(enc.anchor_date),
        "sex": {"male": "男", "female": "女"}.get(a.timeline.subject.sex.value, ""),
        "period": enc.label(),
        "generated": date.today().isoformat(),
        "sources": enc.sources,
        "n_obs": len(obs),
        "n_abnormal": len(enc.observations.abnormal()),
        "n_orig": n_orig,
        "bands": bands,
        "recon": recon,
        "confirms": confirms,
        "derived": [{"o": o, "note": a.derived_notes.get(o.code)} for o in obs
                    if o.kind is ObservationKind.DERIVED and o.code != "AGE"],
        "consistency": a.consistency,
        "plan": a.plan,
        "by_src": by_src,
        "n_ok": len(confirmed_ok),
        "boundaries": [{"what": b.what, "impact": b.impact, "critical": b.critical}
                       for b in a.boundaries],
        "missing_context": [{"label": m.label, "why": m.why,
                             "titles": list(m.affect_titles)}
                            for m in a.missing_context],
        "coverage": cov,
        "unjudged": [next((o.raw_name for o in obs if o.code == c), c)
                     for c in (cov.unjudged_codes if cov else [])],
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
