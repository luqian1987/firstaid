"""L3 模式引擎 → L4 链条组装。

流程：规则 → 模式求值（三态）→ TRIGGERED 的组装成 Chain / Correction，
INDETERMINATE 的登记为边界，NOT_TRIGGERED 的丢弃但保留统计。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model import (
    Archetype, BoundaryItem, Chain, Chapter, ComparabilityKey, ComparisonItem,
    ContextKey, CONTEXT_LABELS, Correction, EvidenceRef, MissingContextItem,
    Modifiability, NarrationBrief, Ontology, PatternHit, TriState, Verdict,
)
from .archetypes import REGISTRY
from .context import RuleContext
from .rule import RuleSet, RuleSpec, render_template


@dataclass
class EngineResult:
    chains: list[Chain] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    hits: list[PatternHit] = field(default_factory=list)
    boundaries: list[BoundaryItem] = field(default_factory=list)
    missing_context: list[MissingContextItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def fired(self) -> list[PatternHit]:
        return [h for h in self.hits if h.state is TriState.TRIGGERED]

    @property
    def indeterminate(self) -> list[PatternHit]:
        return [h for h in self.hits if h.state is TriState.INDETERMINATE]

    def consumed_codes(self) -> set[str]:
        out: set[str] = set()
        for h in self.fired:
            out.update(h.consumed_codes)
        return out


class PatternEngine:
    def __init__(self, ruleset: RuleSet, ontology: Ontology):
        self.ruleset = ruleset
        self.ontology = ontology

    def run(self, ctx: RuleContext) -> EngineResult:
        res = EngineResult()
        ctx_missing: dict[ContextKey, list[tuple[str, str]]] = {}

        for rule in self.ruleset.enabled():
            impl = REGISTRY.get(rule.archetype)
            if impl is None:
                res.errors.append(f"{rule.id}: 未实现的模式 {rule.archetype}")
                continue
            try:
                hit = impl.run(rule.id, ctx, rule.params)
            except Exception as e:                      # 规则写错不静默
                res.errors.append(f"{rule.id}: 求值失败 {type(e).__name__}: {e}")
                continue
            res.hits.append(hit)

            if hit.state is TriState.TRIGGERED:
                # 只有真正成立的判读才谈得上"受某项背景影响"
                for key in rule.needs_context:
                    if not ctx.has_context(key):
                        ctx_missing.setdefault(key, []).append((rule.id, rule.title))

            if hit.state is TriState.INDETERMINATE:
                res.boundaries.append(BoundaryItem(
                    what=f"缺少 {'、'.join(hit.missing_codes)}",
                    affects=(rule.id,),
                    impact=f"「{rule.title}」无法评估，既不作阳性也不作阴性",
                    critical=rule.priority >= 80,
                ))
                continue
            if hit.state is not TriState.TRIGGERED:
                continue

            hit = self._attach_extra(rule, hit, ctx)
            try:
                if rule.correction is not None:
                    res.corrections.append(self._build_correction(rule, hit))
                else:
                    res.chains.append(self._build_chain(rule, hit))
            except Exception as e:
                res.errors.append(f"{rule.id}: 组装失败 {type(e).__name__}: {e}")

        for key, pairs in ctx_missing.items():
            res.missing_context.append(MissingContextItem(
                key=key, label=CONTEXT_LABELS[key],
                affects=tuple(p[0] for p in pairs),
                affect_titles=tuple(p[1] for p in pairs),
                why="报告里没有这项背景，本判读不替你假设",
            ))
        return res

    # ---------------- 组装 ----------------
    def _attach_extra(self, rule: RuleSpec, hit: PatternHit,
                      ctx: RuleContext) -> PatternHit:
        if not rule.extra_evidence:
            return hit
        have = {e.observation.code for e in hit.evidence}
        extra = [EvidenceRef(observation=o, role="context")
                 for c in rule.extra_evidence
                 if c not in have and (o := ctx.obs(c)) is not None]
        if not extra:
            return hit
        return hit.model_copy(update={
            "evidence": hit.evidence + tuple(extra),
            "consumed_codes": hit.consumed_codes + tuple(
                e.observation.code for e in extra),
        })

    def _values(self, hit: PatternHit) -> dict[str, str]:
        return {e.observation.code: e.observation.display_value() for e in hit.evidence}

    def _allowed_values(self, hit: PatternHit) -> tuple[float, ...]:
        vals = [e.observation.value for e in hit.evidence if e.observation.value is not None]
        vals += [v for v in hit.detail.values() if isinstance(v, (int, float))]
        return tuple(float(v) for v in vals)

    def _quoted_text(self, hit: PatternHit) -> tuple[str, ...]:
        out: list[str] = []
        for e in hit.evidence:
            o = e.observation
            if o.ref is not None:
                out += [t for t in (o.ref.raw, o.ref.source_note) if t]
            if o.text:
                out.append(o.text)
            if o.advisory_ref is not None and o.advisory_ref.source_note:
                out.append(o.advisory_ref.source_note)
            if e.note:
                out.append(e.note)
        out += [v for v in hit.detail.values() if isinstance(v, str)]
        return tuple(out)

    def _dedup_evidence(self, hit: PatternHit) -> tuple[EvidenceRef, ...]:
        seen: set[str] = set()
        out: list[EvidenceRef] = []
        for e in hit.evidence:
            if e.observation.code in seen:
                continue
            seen.add(e.observation.code)
            out.append(e)
        return tuple(out)

    def _build_chain(self, rule: RuleSpec, hit: PatternHit) -> Chain:
        vals, detail = self._values(hit), hit.detail
        nar, vs = rule.narration, rule.verdict
        if nar is None or vs is None:
            raise ValueError("缺 narration 或 verdict")

        compare = []
        for c in vs.compare_next:
            o = next((e.observation for e in hit.evidence if e.observation.code == c.code),
                     None)
            if o is None:
                raise ValueError(f"compare_next 引用了不在 evidence 里的 {c.code}")
            compare.append(ComparisonItem(
                key=ComparabilityKey.of(o, self.ontology.device_sensitive(o.code)),
                what=render_template(c.what, vals, detail),
                baseline_display=f"{o.display_value()}{o.unit or ''}",
                caveat=c.caveat, rationale=c.rationale, from_rule=rule.id,
            ))

        verdict = Verdict(
            certain=render_template(vs.certain, vals, detail),
            not_certain=render_template(vs.not_certain, vals, detail),
            next_steps=tuple(render_template(s, vals, detail) for s in vs.next_steps),
            compare_next=tuple(compare),
        )
        return Chain(
            id=rule.id, title=rule.title,
            lede=render_template(rule.lede, vals, detail),
            tag=rule.tag, chapter=rule.chapter,
            modifiability=self._resolve_modifiability(rule, hit),
            priority=rule.priority,
            inputs=self._dedup_evidence(hit),
            single_read=render_template(nar.single_read, vals, detail),
            joint_read=render_template(nar.joint_read, vals, detail),
            verdict=verdict, hits=(hit,),
            brief=NarrationBrief(
                must_convey=tuple(render_template(s, vals, detail)
                                  for s in nar.must_convey),
                must_not_claim=tuple(nar.must_not_claim),
                allowed_values=self._allowed_values(hit),
                quoted_text=self._quoted_text(hit),
            ),
        )

    def _resolve_modifiability(self, rule: RuleSpec, hit: PatternHit) -> Modifiability:
        """规则没写就从本体推：主线指标只要有一个不可改变，整条链就不算可主动改善。"""
        if rule.modifiability is not Modifiability.UNKNOWN:
            return rule.modifiability
        leads = [e.observation.code for e in hit.evidence
                 if e.role in ("hidden", "lead", "upstream", "abnormal", "finding")]
        mods = {self.ontology.modifiability(c) for c in leads}
        if Modifiability.NOT_MODIFIABLE in mods:
            return Modifiability.NOT_MODIFIABLE
        if Modifiability.CLINICAL in mods:
            return Modifiability.CLINICAL
        if mods == {Modifiability.SELF_MODIFIABLE}:
            return Modifiability.SELF_MODIFIABLE
        return Modifiability.UNKNOWN

    def _build_correction(self, rule: RuleSpec, hit: PatternHit) -> Correction:
        c = rule.correction
        assert c is not None
        vals, detail = self._values(hit), hit.detail
        flagged = next((e for e in hit.evidence if e.observation.code == c.flagged), None)
        if flagged is None:
            raise ValueError(f"correction.flagged={c.flagged} 不在 evidence 里")
        contradicting = tuple(e for e in self._dedup_evidence(hit)
                              if e.observation.code != c.flagged)
        return Correction(
            id=rule.id,
            claim=render_template(c.claim, vals, detail),
            original_advice=c.original_advice,
            original_source=c.original_source,
            flagged=flagged, contradicting=contradicting,
            why_not=render_template(c.why_not, vals, detail),
            what_to_do=render_template(c.what_to_do, vals, detail),
            hits=(hit,),
        )
