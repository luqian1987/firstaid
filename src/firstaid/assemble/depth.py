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


def _chains_of(p: dict) -> list[str]:
    """一条通路可以由不止一条判读带上图。

    同一个演变过程，不同的人可能是被不同的判读命中的
    （牙周这条：病例 1 是"牙龈出血在场"，病例 3 是"结石在场但炎症不活动"）。
    过程是同一个，没有理由抄两份通路定义。
    """
    c = p.get("chain")
    if c is None:
        return []
    return list(c) if isinstance(c, (list, tuple)) else [c]


def _one_of(spec, names, obs) -> str:
    """按条件挑一句话。

    "本次没有上游"后面那句解释，写死就等于把第一个病人的情况钉进知识库
    （"幽门螺杆菌本次未检测"——换个人是做了且阴性）。
    所以它可以写成一串 {when, text}，按顺序取第一个成立的。
    """
    if spec is None:
        return ""
    if isinstance(spec, str):
        return _fill(spec, obs)
    for item in spec:
        cond = item.get("when")
        if cond is None or evaluate(cond, names):
            return _fill(item.get("text", ""), obs)
    return ""


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
    def topology(self, enc: Encounter, chain_ids: set[str],
                 chain_order: list[str] | None = None) -> Topology:
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
            owners = _chains_of(p)
            if owners and not (set(owners) & chain_ids):
                continue
            owner = next((c for c in owners if c in chain_ids), None)
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
                chain_id=owner, stages=tuple(stages),
                tail=_fill(p.get("tail", ""), obs),
                next_gate=_fill(p.get("next_gate", ""), obs),
                gate_kind=p.get("gate_kind", "recheck"),
                no_upstream_note=_one_of(p.get("no_upstream_note"), names, obs)))

        order = {c: i for i, c in enumerate(chain_order)} if chain_order else {}
        tracks.sort(key=lambda t: order.get(t.chain_id, 999))
        live = {t.upstream_id for t in tracks}
        return Topology(upstreams=tuple(u for u in ups if u.id in live),
                        tracks=tuple(tracks))

    def scope(self, chains) -> tuple[list[dict], list[str]]:
        """拓扑覆盖了谁、没覆盖谁、为什么。

        行动档（现在要做 / 先弄清楚）的每条链条，要么有通路，要么在
        no_progression 里写明理由。缺一个就是构建失败——
        "忘了画"这种状态不允许存在。
        """
        from ..model import Band, band_of
        has = {c for p in self.spec.get("pathways", []) for c in _chains_of(p)}
        why = {x["chain"]: x["why"] for x in self.spec.get("no_progression", [])}
        excluded, errs = [], []
        for c in chains:
            if c.id in has:
                continue
            if c.id in why:
                excluded.append({"title": c.title, "why": why[c.id],
                                 "band": band_of(c.tag)})
            elif band_of(c.tag) in (Band.ACT, Band.CLARIFY):
                errs.append(
                    f"{c.id}（{band_of(c.tag).value} 档）既没有通路，"
                    "也没有在 no_progression 里说明为什么没有")
        return excluded, errs

    # ---------------- 机制 / 修饰 / 干预 ----------------
    def check_absent_modifiers(self, enc: Encounter, chains) -> list[str]:
        """说"这个因素不在场"，那它引用的指标就不能是异常的。

        深读文本是按第一个病人写的，换一个人可能整句话都不成立
        （胃那条把"胃窦萎缩：胃泌素17"列进"已排除"，而病例 3 的胃泌素17 是三倍上限）。
        这一条只覆盖 absent 这一栏，但它恰好是最危险的一栏——
        "已排除"比"在场"更容易被读者当成结论。
        """
        errs: list[str] = []
        ids = {c.id for c in chains}
        for cid, block in (self.spec.get("depth") or {}).items():
            if cid not in ids:
                continue
            for m in ((block.get("modifiers") or {}).get("absent") or []):
                for code in m.get("codes", []):
                    o = enc.observations.get(code)
                    if o is not None and o.abnormal:
                        errs.append(
                            f"{cid}: 修饰因素「{m['name']}」列在「已排除」，"
                            f"但它引用的 {code}（{o.raw_name}）本次是异常的。"
                            "这句话在这个人身上不成立——改判据，或把这一项挪出 absent")
        return errs

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
    merged: dict = {"upstreams": [], "pathways": [], "depth": {},
                    "no_progression": []}
    for f in sorted(p.glob("**/*.yaml")) if p.is_dir() else [p]:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        merged["upstreams"] += doc.get("upstreams", [])
        merged["pathways"] += doc.get("pathways", [])
        merged["depth"].update(doc.get("depth") or {})
        merged["no_progression"] += doc.get("no_progression", [])
    return merged
