"""深读层求值：把知识（通路定义、机制、修饰、干预）与本人数据合成。

通路的每一关跨没跨，由 crossed_when 表达式对本人数据求值决定，不手写。
求不出来就是 UNKNOWN —— 与整个系统的三态语义一致。
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..model import (
    Depth, Encounter, Intervention, InterventionKind, Mechanism, Modifier, Modifiers,
    Observation, Ontology, PathwayStage, PathwayTrack, StageState, Topology, Upstream,
)
from ..patterns.context import RuleContext
from ..patterns.expr import evaluate

# 通路文本里不允许出现时间预测。"多久到下一关"需要队列数据校准，我们没有。
_TIME = re.compile(r"约?\s*\d+\s*[~～\-—]\s*\d+\s*(年|个月)|"
                   r"\d+\s*年(内|后|以上)|数年内")

_TOKEN = re.compile(r"\{(\$?[A-Za-z0-9_]+)\}")


def _fill(text: str, obs: dict[str, Observation]) -> str:
    def sub(m):
        o = obs.get(m.group(1))
        return o.display_value() if o else m.group(0)
    return _TOKEN.sub(sub, text or "")


def _pick(ctx: RuleContext, codes) -> tuple[Observation, ...]:
    return tuple(o for c in codes if (o := ctx.obs(c)) is not None)


class DepthEngine:
    def __init__(self, spec: dict, ontology: Ontology, derived=None):
        self.spec = spec
        self.ontology = ontology
        # 派生指标定义在派生表里，不在本体里。两处都算"系统真有的指标"。
        self.known = set(ontology.indicators) | {
            d.code for d in (derived.defs if derived else ())}

    # ---------------- 构建期自检 ----------------
    def validate(self) -> list[str]:
        errs: list[str] = []
        known = self.known
        for p in self.spec.get("pathways", []):
            for st in p.get("stages", []):
                if not st.get("judged_by"):
                    errs.append(
                        f"{p['id']} / {st['name']}：没有 judged_by。"
                        "说不出哪个指标判定它，就不许画进拓扑图——"
                        "这条约束顺带挡掉了所有我们其实没有数据的远端病名。")
                for c in st.get("judged_by", []):
                    if c not in known:
                        errs.append(f"{p['id']} / {st['name']}：本体里没有指标 {c}")
            blob = " ".join(str(v) for v in
                            [p.get("tail", ""), p.get("next_gate", "")]
                            + [s.get("detail", "") for s in p.get("stages", [])])
            if _TIME.search(blob):
                errs.append(f"{p['id']}：通路文本含时间预测，本系统不做这种推断")
        for cid, block in (self.spec.get("depth") or {}).items():
            for m in block.get("mechanisms", []):
                for c in m.get("cites", []):
                    if c not in known:
                        errs.append(f"{cid}：机制引用了本体没有的指标 {c}")
        return errs

    # ---------------- 通路 ----------------
    def topology(self, enc: Encounter, chain_ids: set[str]) -> Topology:
        ctx = RuleContext(enc)
        obs = {o.code: o for o in enc.observations}
        names = {o.code: ctx.proxy(o.code) for o in enc.observations}

        ups: list[Upstream] = []
        for u in self.spec.get("upstreams", []):
            present = evaluate(u["present_when"], names) if u.get("present_when") else None
            ups.append(Upstream(
                id=u["id"], label=u["label"], sub=_fill(u.get("sub", ""), obs),
                modifiable=bool(u.get("modifiable", True)), note=u.get("note", ""),
                present=bool(present), evidence=_pick(ctx, u.get("codes", []))))

        tracks: list[PathwayTrack] = []
        for p in self.spec.get("pathways", []):
            # 只画那些对应链条本次真的命中的通路
            if p.get("chain") and p["chain"] not in chain_ids:
                continue
            stages = []
            for i, st in enumerate(p["stages"]):
                if any(ctx.obs(c) is None for c in st["judged_by"]):
                    state = StageState.UNKNOWN
                elif st.get("crossed_when"):
                    v = evaluate(st["crossed_when"], names)
                    state = (StageState.UNKNOWN if v is None
                             else StageState.CROSSED if v else StageState.CLEAR)
                else:
                    state = StageState.UNKNOWN
                stages.append(PathwayStage(
                    name=st["name"], judged_by=tuple(st["judged_by"]), state=state,
                    detail=_fill(st.get("detail", ""), obs), edge=st.get("edge", ""),
                    col=st.get("col"), emphasis=bool(st.get("emphasis")),
                    evidence=_pick(ctx, st["judged_by"])))
            tracks.append(PathwayTrack(
                id=p["id"], label=p["label"], upstream_id=p["upstream"],
                chain_id=p.get("chain"), stages=tuple(stages),
                tail=_fill(p.get("tail", ""), obs),
                next_gate=_fill(p.get("next_gate", ""), obs),
                gate_kind=p.get("gate_kind", "recheck")))

        live = {t.upstream_id for t in tracks}
        return Topology(upstreams=tuple(u for u in ups if u.id in live),
                        tracks=tuple(tracks))

    # ---------------- 机制 / 修饰 / 干预 ----------------
    def depth_for(self, enc: Encounter, chain, compare_codes: set[str]) -> Depth | None:
        block = (self.spec.get("depth") or {}).get(chain.id)
        if not block:
            return None
        ctx = RuleContext(enc)
        obs = {o.code: o for o in enc.observations}
        detail = chain.hits[0].detail if chain.hits else {}

        def fill(t: str) -> str:
            t = _TOKEN.sub(lambda m: (f"{detail.get(m.group(1)[1:]):g}"
                                      if m.group(1).startswith("$")
                                      and isinstance(detail.get(m.group(1)[1:]), float)
                                      else m.group(0)), t or "")
            return _fill(t, obs)

        mechs = tuple(Mechanism(
            pivot=fill(m["pivot"]), level=m.get("level", "机制"),
            cites=tuple(m.get("cites", [])), rules_out=m.get("rules_out", ""),
            evidence=_pick(ctx, m.get("cites", []))) for m in block.get("mechanisms", []))

        mod = block.get("modifiers") or {}

        def grp(key):
            return tuple(Modifier(
                name=m["name"], note=fill(m.get("note", "")), why=m.get("why", ""),
                codes=tuple(m.get("codes", [])), evidence=_pick(ctx, m.get("codes", [])))
                for m in (mod.get(key) or []))

        ivs = []
        for iv in block.get("interventions", []):
            v = iv.get("verify_by", "")
            ivs.append(Intervention(
                kind=InterventionKind(iv["kind"]), action=iv["action"],
                rationale=fill(iv.get("rationale", "")),
                target_codes=tuple(iv.get("target", [])), verify_by=v,
                verify_label=(obs[v].raw_name if v in obs else v),
                horizon=iv.get("horizon", ""), caveat=fill(iv.get("caveat", "")),
                conditional=iv.get("conditional", ""),
                paths=tuple(iv.get("paths", [])),
                ask_doctor=tuple(iv.get("ask_doctor", [])), note=iv.get("note", "")))
        return Depth(chain_id=chain.id, mechanisms=mechs,
                     modifiers=Modifiers(present=grp("present"), absent=grp("absent"),
                                         unknown=grp("unknown")),
                     interventions=tuple(ivs))


def load_depth_spec(path: str | Path) -> dict:
    p = Path(path)
    merged: dict = {"upstreams": [], "pathways": [], "depth": {}}
    for f in sorted(p.glob("**/*.yaml")) if p.is_dir() else [p]:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        merged["upstreams"] += doc.get("upstreams", [])
        merged["pathways"] += doc.get("pathways", [])
        merged["depth"].update(doc.get("depth") or {})
    return merged
