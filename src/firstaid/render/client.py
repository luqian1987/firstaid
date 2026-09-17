"""客户版渲染。

组织轴和完整版不同。完整版按判读组织（一条多联一段）；
客户版按**体检者的三个问题**组织，顺序不能颠倒：

    1. 我有事吗
    2. 这次有什么没回答（而且是本次结果指向、却没覆盖的）
    3. 这些各自什么时候再看
    （4. 最后才是具体怎么做）

上一版把第 4 问当成了第 1 问，于是整份文件从第一屏开始派活。

硬约束：**客户版是完整版的投影，不允许出现完整版里没有的句子。**
这里所有文本都取自 chain.headline / verdict / Gap，没有一句是本层新写的。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from markupsafe import Markup

from ..assemble.gaps import group_gaps
from ..assemble.overview import LEAD_ROLES, build_overview, counted, load_systems
from ..model import Band, EFFORT_LABELS, ObservationKind, Tag, band_of
from .anatomy import render_anatomy
from ..patterns.rule import HORIZON_LABELS, HORIZON_WHY, HORIZONS
from ..pipeline import Analysis

TEMPLATES = Path(__file__).parent / "templates"


KNOWLEDGE_SYSTEMS = Path(__file__).resolve().parents[3] / "knowledge" / "ontology" / "_systems.yaml"


def _key_numbers(chain, limit: int = 3) -> list[dict]:
    """决定性的那一两个数。

    不是"进入判断的全部数值"——那是完整版的事。客户版给的是
    支撑这条结论的主角：担任 lead 角色的那几项。
    不给数字是客户版上一版最大的问题：只有结论没有凭据，读起来像断言。
    """
    out = []
    for e in chain.inputs:
        if e.role not in LEAD_ROLES:
            continue
        o = e.observation
        # 影像与定性项没有数字，硬塞进三栏网格会把指标名挤成竖排。
        # 它们本来就是一句话，就按一句话排。
        numeric = o.value is not None
        out.append({
            "kind": "num" if numeric else "text",
            "name": o.raw_name,
            "value": o.display_value() if numeric else "",
            "unit": o.unit or "" if numeric else "",
            "ref": o.ref.display() if (o.ref and (o.ref.low is not None
                                                  or o.ref.high is not None)) else "",
            "state": ("hi" if o.is_high else "lo" if o.is_low
                      else "ab" if o.abnormal else "ok"),
            "text": (o.text or o.display_value() or "") if not numeric else "",
        })
        if len(out) >= limit:
            break
    return out


def _horizon_of(a: Analysis, chain_id: str) -> str:
    r = a.rules.by_id(chain_id) if a.rules else None
    return r.horizon.when if (r and r.horizon) else "next_checkup"


def build_client_context(a: Analysis) -> dict:
    enc = a.encounter
    n_orig = len([f for f in enc.original_findings if not f.pending])

    by_h: dict[str, list] = {h: [] for h in HORIZONS}
    for c in sorted(a.chains, key=lambda c: -c.priority):
        w = _horizon_of(a, c.id)
        r = a.rules.by_id(c.id) if a.rules else None
        an = r.anatomy if r else None
        by_h[w].append({
            "id": c.id, "headline": c.headline, "title": c.title,
            "band": band_of(c.tag).value,
            "why": r.horizon.why if (r and r.horizon) else "",
            "steps": list(c.verdict.next_steps) if c.verdict else [],
            "certain": c.verdict.certain if c.verdict else "",
            "numbers": _key_numbers(c),
            "site": an.site if an else None,
            "svg": (Markup(render_anatomy(an.diagram, an.mark))
                    if (an and an.diagram) else None),
        })

    free = group_gaps([g for g in a.gaps if g.free])
    tests = group_gaps([g for g in a.gaps if not g.free])

    # 本次确立了什么。不新增字段：需要专科长期管理、而又不属于"现在/几周内"的，
    # 就是一件已经定下来、接下来靠节奏管理的事。三例真实报告上这个推导都成立，
    # 但它是推导不是声明——将来真有反例，就该升级成显式字段。
    established = [c for c in a.chains
                   if c.tag is Tag.NEEDS_SPECIALIST
                   and _horizon_of(a, c.id) in ("next_checkup", "know_it")]

    # 第一屏那句话。它只能说"查过的范围内"，而且必须和缺失数贴在一起。
    now_items = by_h["now"]
    verdict_line = ("本次查过的项目里，没有发现需要马上处理的问题。"
                    if not now_items else
                    f"本次查过的项目里，有 {len(now_items)} 件需要现在处理。")

    spec = load_systems(KNOWLEDGE_SYSTEMS)
    overview = build_overview(enc, a.chains, a.ontology, spec) if a.ontology else []
    checked = counted(enc, a.ontology, set(spec.get("excluded", []))) if a.ontology else []

    return {
        "overview": overview,
        "n_obs": len(checked),
        "n_derived": len([o for o in enc.observations
                          if o.kind is ObservationKind.DERIVED and o.code != "AGE"]),
        "n_abnormal": len([o for o in checked if o.abnormal]),
        "n_sources": len(enc.sources),
        "n_chains": len(a.chains),
        "subject_id": enc.subject_id.upper(),
        "age": a.timeline.subject.age_on(enc.anchor_date),
        "sex": {"male": "男", "female": "女"}.get(a.timeline.subject.sex.value, ""),
        "period": enc.label(),
        "generated": date.today().isoformat(),
        "n_orig": n_orig,
        "verdict_line": verdict_line,
        "now_items": now_items,
        "established": [{"headline": c.headline, "title": c.title} for c in established],
        "by_h": by_h,
        "horizon_labels": HORIZON_LABELS,
        "horizon_why": HORIZON_WHY,
        "horizons": [h for h in HORIZONS if by_h[h]],
        "gaps": a.gaps,
        "free_gaps": free,
        "test_gaps": tests,
        # 数量一律按"件"数，不按分组数——分组只是为了理由不重复说
        "n_free": sum(len(g["gaps"]) for g in free),
        "n_test": sum(len(g["gaps"]) for g in tests),
        "effort_labels": EFFORT_LABELS,
        "n_settled": len(by_h["none"]) + len(by_h["know_it"]),
        "band_color": {"act": "#B04226", "clarify": "#2F5D8C", "settle": "#1D6155"},
    }


def render_client(a: Analysis, out: Path) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATES),
                      autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    html = env.get_template("client.html.j2").render(**build_client_context(a))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
