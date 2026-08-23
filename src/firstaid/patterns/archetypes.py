"""九类推理模式的实现。

设计要点：模式是"代码 + 测试"，规则实例是"纯数据"。
换一组指标不用改代码——"上游异常/下游全阴"这条逻辑，
用在叶酸与 Hcy/MCV/Hb/MMA 上，和用在 TSH 与 FT3/FT4 上，完全一样。

每个模式必须返回三态之一。缺输入一律 INDETERMINATE，绝不当作未命中。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from pydantic import BaseModel, Field

from ..model import (
    Archetype, ContextKey, EvidenceRef, Observation, PatternHit, RangeStatus, TriState,
)
from .context import RuleContext

# --------------------------------------------------------------------------
# 期望状态检查
# --------------------------------------------------------------------------
LOW_END_DEFAULT = 0.25
HIGH_END_DEFAULT = 0.75


def check_state(o: Observation | None, expect: str, threshold: float | None = None) -> bool | None:
    """None 表示"判定不了"（缺指标 / 缺区间），交由调用方升级为 INDETERMINATE。"""
    if o is None:
        return None
    e = expect.lower()
    if e == "present":
        return True
    if e == "in_range":
        return o.in_range if o.has_range else None
    if e == "high":
        return o.is_high if o.has_range else None
    if e == "low":
        return o.is_low if o.has_range else None
    if e == "abnormal":
        return o.abnormal if o.has_range else None
    if e == "not_high":
        return (not o.is_high) if o.has_range else None
    if e == "negative":
        if o.qualitative is not None:
            return o.negative
        return o.in_range if o.has_range else None
    if e == "negative_or_in_range":
        return o.negative if (o.qualitative is not None or o.has_range) else None
    if e in ("low_end", "high_end"):
        pos = o.position_in_range
        if pos is None:
            # 单边区间时退化：低端看是否 low，高端看是否 high
            if not o.has_range:
                return None
            return o.is_low if e == "low_end" else o.is_high
        t = threshold if threshold is not None else (
            LOW_END_DEFAULT if e == "low_end" else HIGH_END_DEFAULT)
        return pos <= t if e == "low_end" else pos >= t
    if e == "no_range":
        return o.status is RangeStatus.NO_RANGE
    # advisory_* :用本系统补的常用切点判定。与报告自带区间严格分开，
    # 规则必须显式选用哪一套，不做静默回退。
    if e == "advisory_in_range":
        return o.advisory_in_range if o.has_advisory else None
    if e == "advisory_high":
        return o.advisory_high if o.has_advisory else None
    if e == "advisory_low":
        return o.advisory_low if o.has_advisory else None
    if e == "in_range_or_advisory_in_range":
        if o.has_range:
            return o.in_range
        return o.advisory_in_range if o.has_advisory else None
    if e == "normal_text":
        return o.negative if (o.qualitative is not None or o.text) else None
    raise ValueError(f"未知的期望状态: {expect}")


class ArchetypeImpl(ABC):
    archetype: Archetype
    params_model: type[BaseModel]

    def run(self, rule_id: str, ctx: RuleContext, raw_params: dict) -> PatternHit:
        params = self.params_model.model_validate(raw_params)
        return self.evaluate(rule_id, ctx, params)

    @abstractmethod
    def evaluate(self, rule_id: str, ctx: RuleContext, p: Any) -> PatternHit: ...

    # -- 构造辅助 --
    def _hit(self, rule_id: str, state: TriState, *,
             evidence: Sequence[EvidenceRef] = (), consumed: Sequence[str] = (),
             missing: Sequence[str] = (), detail: dict | None = None,
             needs_context: Sequence[ContextKey] = ()) -> PatternHit:
        return PatternHit(
            rule_id=rule_id, archetype=self.archetype, state=state,
            evidence=tuple(evidence), consumed_codes=tuple(consumed),
            missing_codes=tuple(missing), detail=detail or {},
            needs_context=tuple(needs_context),
        )

    def _gather(self, ctx: RuleContext, codes: Sequence[str], role: str
                ) -> tuple[list[EvidenceRef], list[str]]:
        refs, missing = [], []
        for c in codes:
            o = ctx.obs(c)
            if o is None:
                missing.append(c)
            else:
                refs.append(EvidenceRef(observation=o, role=role))
        return refs, missing


# --------------------------------------------------------------------------
# 1. 上游异常 / 下游全阴  → 检测可信度存疑
#    例：血清叶酸 <0.20 属重度缺乏量级，但 Hcy、MCV、Hb、MMA 四个下游全正常。
# --------------------------------------------------------------------------
class UpstreamContradictedParams(BaseModel):
    upstream: str
    direction: str = "low"                 # low / high
    downstream: list[str]
    downstream_expect: str = "in_range"
    min_normal: int | None = None          # 默认要求全部正常


class UpstreamContradicted(ArchetypeImpl):
    archetype = Archetype.UPSTREAM_CONTRADICTED
    params_model = UpstreamContradictedParams

    def evaluate(self, rule_id, ctx, p: UpstreamContradictedParams) -> PatternHit:
        up = ctx.obs(p.upstream)
        if up is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.upstream])
        down_refs, missing = self._gather(ctx, p.downstream, "downstream")
        need = p.min_normal if p.min_normal is not None else len(p.downstream)
        if len(down_refs) < need:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing,
                             evidence=[EvidenceRef(observation=up, role="upstream")])

        up_ok = check_state(up, p.direction)
        if up_ok is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.upstream])
        if not up_ok:
            return self._hit(rule_id, TriState.NOT_TRIGGERED)

        results = [check_state(r.observation, p.downstream_expect) for r in down_refs]
        if any(r is None for r in results):
            unk = [r.observation.code for r, s in zip(down_refs, results) if s is None]
            return self._hit(rule_id, TriState.INDETERMINATE, missing=unk)
        n_normal = sum(1 for r in results if r)
        state = TriState.TRIGGERED if n_normal >= need else TriState.NOT_TRIGGERED
        return self._hit(
            rule_id, state,
            evidence=[EvidenceRef(observation=up, role="upstream")] + down_refs,
            consumed=[p.upstream] + [r.observation.code for r in down_refs],
            detail={"n_downstream_normal": float(n_normal),
                    "n_downstream": float(len(down_refs))},
        )


# --------------------------------------------------------------------------
# 2. 校正值 vs 未校正值  → 未校正的异常由已知混杂解释
#    例：低切/中切粘度升高，但扣掉压积影响的全血还原粘度完全正常。
# --------------------------------------------------------------------------
class CorrectedVsRawParams(BaseModel):
    raw: list[str]
    corrected: list[str]
    confounders: list[str] = Field(default_factory=list)
    corrected_expect: str = "in_range"


class CorrectedVsRaw(ArchetypeImpl):
    archetype = Archetype.CORRECTED_VS_RAW
    params_model = CorrectedVsRawParams

    def evaluate(self, rule_id, ctx, p: CorrectedVsRawParams) -> PatternHit:
        raw_refs, raw_missing = self._gather(ctx, p.raw, "raw")
        cor_refs, cor_missing = self._gather(ctx, p.corrected, "corrected")
        if not raw_refs or cor_missing:
            return self._hit(rule_id, TriState.INDETERMINATE,
                             missing=raw_missing + cor_missing)
        if not any(r.observation.abnormal for r in raw_refs):
            return self._hit(rule_id, TriState.NOT_TRIGGERED)
        states = [check_state(r.observation, p.corrected_expect) for r in cor_refs]
        if any(s is None for s in states):
            return self._hit(rule_id, TriState.INDETERMINATE,
                             missing=[r.observation.code
                                      for r, s in zip(cor_refs, states) if s is None])
        conf_refs, _ = self._gather(ctx, p.confounders, "confounder")
        state = TriState.TRIGGERED if all(states) else TriState.NOT_TRIGGERED
        return self._hit(
            rule_id, state, evidence=raw_refs + cor_refs + conf_refs,
            consumed=[r.observation.code for r in raw_refs + cor_refs + conf_refs],
            detail={"n_raw_abnormal": float(
                sum(1 for r in raw_refs if r.observation.abnormal))},
        )


# --------------------------------------------------------------------------
# 3. 配对同向背离  → 系统性偏差（方法学/定标），而非两个独立异常
#    例：ApoB↔非HDL-C 与 ApoA1↔HDL-C 两组同时朝同一方向散开。
# --------------------------------------------------------------------------
class Pair(BaseModel):
    particle: str
    cargo: str
    ratio_min: float
    ratio_max: float
    label: str | None = None


class PairedDivergenceParams(BaseModel):
    pairs: list[Pair]
    min_violations: int = 2
    require_same_direction: bool = True


class PairedDivergence(ArchetypeImpl):
    archetype = Archetype.PAIRED_DIVERGENCE
    params_model = PairedDivergenceParams

    def evaluate(self, rule_id, ctx, p: PairedDivergenceParams) -> PatternHit:
        refs: list[EvidenceRef] = []
        missing: list[str] = []
        violations: list[str] = []
        detail: dict[str, Any] = {}
        for pair in p.pairs:
            a, b = ctx.obs(pair.particle), ctx.obs(pair.cargo)
            if a is None or a.value in (None, 0) or b is None or b.value is None:
                missing += [c for c, o in ((pair.particle, a), (pair.cargo, b))
                            if o is None or o.value is None]
                continue
            ratio = b.value / a.value
            key = pair.label or f"{pair.cargo}/{pair.particle}"
            detail[key] = round(ratio, 4)
            refs += [EvidenceRef(observation=a, role="particle"),
                     EvidenceRef(observation=b, role="cargo")]
            if ratio < pair.ratio_min:
                violations.append("low")
            elif ratio > pair.ratio_max:
                violations.append("high")
        if missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing,
                             evidence=refs, detail=detail)
        same_dir = len(set(violations)) <= 1
        ok = (len(violations) >= p.min_violations
              and (same_dir or not p.require_same_direction))
        detail["n_violations"] = float(len(violations))
        detail["direction"] = violations[0] if violations else "none"
        return self._hit(
            rule_id, TriState.TRIGGERED if ok else TriState.NOT_TRIGGERED,
            evidence=refs, consumed=[r.observation.code for r in refs], detail=detail,
        )


# --------------------------------------------------------------------------
# 4. 形态脱节  → 单项升高与它本该同行的指标不同步，指向不同病因
#    例：GGT 达上限 1.53 倍，而 ALT/AST 正常、AST/ALT 仅 0.77。
# --------------------------------------------------------------------------
class RatioCheck(BaseModel):
    numerator: str
    denominator: str
    below: float | None = None
    above: float | None = None
    label: str | None = None


class PatternDissociationParams(BaseModel):
    lead: str
    lead_min_ratio_to_upper: float = 1.2
    companions: list[str]
    companions_expect: str = "in_range"
    ratio_checks: list[RatioCheck] = Field(default_factory=list)


class PatternDissociation(ArchetypeImpl):
    archetype = Archetype.PATTERN_DISSOCIATION
    params_model = PatternDissociationParams

    def evaluate(self, rule_id, ctx, p: PatternDissociationParams) -> PatternHit:
        lead = ctx.obs(p.lead)
        if lead is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.lead])
        comp_refs, missing = self._gather(ctx, p.companions, "companion")
        if missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing)
        r = lead.ratio_to_upper
        if r is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.lead])
        detail: dict[str, Any] = {"lead_ratio_to_upper": round(r, 3)}
        states = [check_state(c.observation, p.companions_expect) for c in comp_refs]
        if any(s is None for s in states):
            return self._hit(rule_id, TriState.INDETERMINATE,
                             missing=[c.observation.code
                                      for c, s in zip(comp_refs, states) if s is None])
        ok = r >= p.lead_min_ratio_to_upper and all(states)
        extra: list[EvidenceRef] = []
        for rc in p.ratio_checks:
            n, d = ctx.obs(rc.numerator), ctx.obs(rc.denominator)
            if n is None or d is None or not d.value:
                return self._hit(rule_id, TriState.INDETERMINATE,
                                 missing=[rc.numerator, rc.denominator])
            val = n.value / d.value
            detail[rc.label or f"{rc.numerator}/{rc.denominator}"] = round(val, 3)
            if rc.below is not None and not val < rc.below:
                ok = False
            if rc.above is not None and not val > rc.above:
                ok = False
            extra += [EvidenceRef(observation=n, role="ratio"),
                      EvidenceRef(observation=d, role="ratio")]
        refs = [EvidenceRef(observation=lead, role="lead")] + comp_refs + extra
        return self._hit(
            rule_id, TriState.TRIGGERED if ok else TriState.NOT_TRIGGERED,
            evidence=refs, consumed=[x.observation.code for x in refs], detail=detail,
        )


# --------------------------------------------------------------------------
# 5. 多层排除  → 一个命名发现，按层逐一排除后可降级
#    例：脾大 = 尺寸层（长径仍在界值内）+ 功能层（三系正常）+ 上游层（无门脉高压）
# --------------------------------------------------------------------------
class Layer(BaseModel):
    name: str
    codes: list[str]
    expect: str = "in_range"
    threshold: float | None = None


class LayeredExclusionParams(BaseModel):
    finding: str
    layers: list[Layer]


class LayeredExclusion(ArchetypeImpl):
    archetype = Archetype.LAYERED_EXCLUSION
    params_model = LayeredExclusionParams

    def evaluate(self, rule_id, ctx, p: LayeredExclusionParams) -> PatternHit:
        fo = ctx.obs(p.finding)
        if fo is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.finding])
        refs = [EvidenceRef(observation=fo, role="finding")]
        cleared: dict[str, Any] = {}
        missing: list[str] = []
        all_clear = True
        for layer in p.layers:
            lrefs, lmiss = self._gather(ctx, layer.codes, f"layer:{layer.name}")
            missing += lmiss
            refs += lrefs
            states = [check_state(r.observation, layer.expect, layer.threshold)
                      for r in lrefs]
            if lmiss or any(s is None for s in states):
                missing += [r.observation.code
                            for r, s in zip(lrefs, states) if s is None]
                cleared[layer.name] = "indeterminate"
                continue
            cleared[layer.name] = "clear" if all(states) else "not_clear"
            if not all(states):
                all_clear = False
        if missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing,
                             evidence=refs, detail=cleared)
        return self._hit(
            rule_id, TriState.TRIGGERED if all_clear else TriState.NOT_TRIGGERED,
            evidence=refs, consumed=[r.observation.code for r in refs], detail=cleared,
        )


# --------------------------------------------------------------------------
# 6. 孤立异常缺乏佐证
#    例：尿细菌 15↑，而白细胞、酯酶、亚硝酸盐、白细胞团四项全阴 → 污染而非感染
# --------------------------------------------------------------------------
class IsolatedAbnormalParams(BaseModel):
    abnormal: str
    direction: str = "abnormal"
    corroborators: list[str]
    corroborator_expect: str = "negative_or_in_range"


class IsolatedAbnormal(ArchetypeImpl):
    archetype = Archetype.ISOLATED_ABNORMAL
    params_model = IsolatedAbnormalParams

    def evaluate(self, rule_id, ctx, p: IsolatedAbnormalParams) -> PatternHit:
        ab = ctx.obs(p.abnormal)
        if ab is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.abnormal])
        st = check_state(ab, p.direction)
        if st is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.abnormal])
        if not st:
            return self._hit(rule_id, TriState.NOT_TRIGGERED)
        refs, missing = self._gather(ctx, p.corroborators, "corroborator")
        if missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing)
        states = [check_state(r.observation, p.corroborator_expect) for r in refs]
        if any(s is None for s in states):
            return self._hit(rule_id, TriState.INDETERMINATE,
                             missing=[r.observation.code
                                      for r, s in zip(refs, states) if s is None])
        allrefs = [EvidenceRef(observation=ab, role="abnormal")] + refs
        return self._hit(
            rule_id, TriState.TRIGGERED if all(states) else TriState.NOT_TRIGGERED,
            evidence=allrefs, consumed=[r.observation.code for r in allrefs],
            detail={"n_corroborators_silent": float(sum(1 for s in states if s))},
        )


# --------------------------------------------------------------------------
# 7. 急性期蛋白一致性  → 多个指标共同描述同一个良性背景
#    例：FIB 1.72↓ + ESR 1 + CRP<0.5 三者互证 = 低炎症背景，不是出血倾向
# --------------------------------------------------------------------------
class Member(BaseModel):
    code: str
    expect: str
    threshold: float | None = None


class AcutePhaseCoherenceParams(BaseModel):
    members: list[Member]
    functional_normal: list[str] = Field(default_factory=list)


class AcutePhaseCoherence(ArchetypeImpl):
    archetype = Archetype.ACUTE_PHASE_COHERENCE
    params_model = AcutePhaseCoherenceParams

    def evaluate(self, rule_id, ctx, p: AcutePhaseCoherenceParams) -> PatternHit:
        refs: list[EvidenceRef] = []
        missing: list[str] = []
        states: list[bool] = []
        for m in p.members:
            o = ctx.obs(m.code)
            if o is None:
                missing.append(m.code)
                continue
            s = check_state(o, m.expect, m.threshold)
            if s is None:
                missing.append(m.code)
                continue
            refs.append(EvidenceRef(observation=o, role="acute_phase"))
            states.append(s)
        fr, fmiss = self._gather(ctx, p.functional_normal, "functional")
        missing += fmiss
        if missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing,
                             evidence=refs + fr)
        fstates = [check_state(r.observation, "in_range") for r in fr]
        if any(s is None for s in fstates):
            return self._hit(rule_id, TriState.INDETERMINATE,
                             missing=[r.observation.code
                                      for r, s in zip(fr, fstates) if s is None])
        ok = all(states) and all(fstates)
        allrefs = refs + fr
        return self._hit(
            rule_id, TriState.TRIGGERED if ok else TriState.NOT_TRIGGERED,
            evidence=allrefs, consumed=[r.observation.code for r in allrefs],
            detail={"n_coherent": float(sum(1 for s in states if s))},
        )


# --------------------------------------------------------------------------
# 8. 常规组套全正常，但组合提示风险
#    例：血脂四项全部在区间内，而 Lp(a) 456.7 + 颅内 M1 段狭窄 + 颈动脉干净
# --------------------------------------------------------------------------
class NormalPanelHiddenRiskParams(BaseModel):
    panel: list[str]
    hidden: str
    hidden_direction: str = "high"
    anchors: list[str] = Field(default_factory=list)
    anchor_mode: str = "any"               # any / all
    negative_anchors: list[str] = Field(default_factory=list)  # 应为阴性的对照部位


class NormalPanelHiddenRisk(ArchetypeImpl):
    archetype = Archetype.NORMAL_PANEL_HIDDEN_RISK
    params_model = NormalPanelHiddenRiskParams

    def evaluate(self, rule_id, ctx, p: NormalPanelHiddenRiskParams) -> PatternHit:
        hidden = ctx.obs(p.hidden)
        if hidden is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.hidden])
        hs = check_state(hidden, p.hidden_direction)
        if hs is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.hidden])
        panel_refs, missing = self._gather(ctx, p.panel, "panel")
        if missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing)
        pstates = [check_state(r.observation, "in_range") for r in panel_refs]
        if any(s is None for s in pstates):
            return self._hit(rule_id, TriState.INDETERMINATE,
                             missing=[r.observation.code
                                      for r, s in zip(panel_refs, pstates) if s is None])
        anchor_refs, anchor_missing = self._gather(ctx, p.anchors, "anchor")
        neg_refs, _ = self._gather(ctx, p.negative_anchors, "negative_anchor")
        if p.anchor_mode == "all" and anchor_missing:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=anchor_missing)
        anchor_ok = bool(anchor_refs) if p.anchor_mode == "any" else not anchor_missing
        ok = hs and all(pstates) and (anchor_ok or not p.anchors)
        refs = [EvidenceRef(observation=hidden, role="hidden")] + panel_refs \
            + anchor_refs + neg_refs
        return self._hit(
            rule_id, TriState.TRIGGERED if ok else TriState.NOT_TRIGGERED,
            evidence=refs, consumed=[r.observation.code for r in refs],
            detail={"panel_all_normal": float(all(pstates)),
                    "hidden_ratio_to_upper": (
                        round(hidden.ratio_to_upper, 3)
                        if hidden.ratio_to_upper else None)},
        )


# --------------------------------------------------------------------------
# 9. 无区间结构性发现  → 不判高低，转"比较口径"
#    例：CAP 272、LSM 6.1、脾 116×46、结节 4mm —— 原报告没给区间的数字
# --------------------------------------------------------------------------
class UnrangedStructuralParams(BaseModel):
    codes: list[str]
    require_no_range: bool = True


class UnrangedStructural(ArchetypeImpl):
    archetype = Archetype.UNRANGED_STRUCTURAL
    params_model = UnrangedStructuralParams

    def evaluate(self, rule_id, ctx, p: UnrangedStructuralParams) -> PatternHit:
        refs, missing = self._gather(ctx, p.codes, "structural")
        if not refs:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=missing)
        if p.require_no_range:
            refs = [r for r in refs if not r.observation.has_range]
        if not refs:
            return self._hit(rule_id, TriState.NOT_TRIGGERED)
        return self._hit(
            rule_id, TriState.TRIGGERED, evidence=refs,
            consumed=[r.observation.code for r in refs], missing=missing,
            detail={"n_structural": float(len(refs))},
        )


# --------------------------------------------------------------------------
# 10. 区间口径不当  → 被标"异常"用的不是疾病界值，而是实验室自有百分位区间
#     例：辅酶Q10 被标"不足"，用的是该实验室按 340 例健康人 5%-95% 分位定的自有区间。
#     这一类是覆盖率审计逼出来的：两项异常反复落进 UNRESOLVED，
#     说明知识库缺一条规则，而不是这次数据特殊。
# --------------------------------------------------------------------------
class RangeKindCaveatParams(BaseModel):
    code: str
    caveat_kinds: list[str] = Field(default_factory=lambda: ["lab_percentile"])
    # 只有这些前提都不成立时，这条"异常"才判定为无需处理
    absent_preconditions: list[Member] = Field(default_factory=list)


class RangeKindCaveat(ArchetypeImpl):
    archetype = Archetype.RANGE_KIND_CAVEAT
    params_model = RangeKindCaveatParams

    def evaluate(self, rule_id, ctx, p: RangeKindCaveatParams) -> PatternHit:
        o = ctx.obs(p.code)
        if o is None:
            return self._hit(rule_id, TriState.INDETERMINATE, missing=[p.code])
        if not o.abnormal or o.ref is None:
            return self._hit(rule_id, TriState.NOT_TRIGGERED)
        if o.ref.kind.value not in p.caveat_kinds:
            return self._hit(rule_id, TriState.NOT_TRIGGERED)
        refs = [EvidenceRef(observation=o, role="abnormal",
                            note=o.ref.source_note)]
        for m in p.absent_preconditions:
            po = ctx.obs(m.code)
            if po is None:
                return self._hit(rule_id, TriState.INDETERMINATE, missing=[m.code])
            st = check_state(po, m.expect, m.threshold)
            if st is None:
                return self._hit(rule_id, TriState.INDETERMINATE, missing=[m.code])
            refs.append(EvidenceRef(observation=po, role="precondition"))
            if not st:
                return self._hit(rule_id, TriState.NOT_TRIGGERED, evidence=refs)
        return self._hit(
            rule_id, TriState.TRIGGERED, evidence=refs,
            consumed=[r.observation.code for r in refs],
            detail={"range_kind": o.ref.kind.value,
                    "source_note": o.ref.source_note or ""},
        )


REGISTRY: dict[Archetype, ArchetypeImpl] = {
    impl.archetype: impl for impl in (
        UpstreamContradicted(), CorrectedVsRaw(), PairedDivergence(),
        PatternDissociation(), LayeredExclusion(), IsolatedAbnormal(),
        AcutePhaseCoherence(), NormalPanelHiddenRisk(), UnrangedStructural(),
        RangeKindCaveat(),
    )
}
