"""L2 派生层。

产出的 DerivedValue 就是一条 Observation（kind=DERIVED），
这样模式层不必区分"量出来的"和"算出来的"。
每个派生值带公式、带输入、带算式展示，可回溯复核。

同时做一致性校验：原报告若也给了同名派生值，重算对不上就登记 issue。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..model import (
    ConsistencyIssue, DerivedDef, DerivedRegistry, Encounter, Observation,
    ObservationKind, Provenance, RangeKind, RangeStatus, RefRange, Sex,
)
from ..normalize.refrange import judge
from ..patterns.context import RuleContext
from ..patterns.expr import evaluate


def load_derived(path: str | Path) -> DerivedRegistry:
    p = Path(path)
    files = sorted(p.glob("**/*.yaml")) if p.is_dir() else [p]
    defs: list[DerivedDef] = []
    for f in files:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for raw in doc.get("derived", []):
            defs.append(DerivedDef.model_validate(raw))
    return DerivedRegistry(defs=tuple(defs))


class DeriveEngine:
    def __init__(self, registry: DerivedRegistry, sex: Sex | None = None):
        self.registry = registry
        self.sex = sex

    def run(self, enc: Encounter) -> tuple[list[Observation], list[ConsistencyIssue]]:
        produced: list[Observation] = []
        issues: list[ConsistencyIssue] = []

        # 迭代若干轮，让派生值可以依赖别的派生值（如 非HDL-C(mg/dL) 依赖 非HDL-C）
        for _ in range(3):
            ctx = RuleContext(enc)
            added = False
            for d in self.registry.defs:
                if enc.observations.get(d.code) is not None:
                    continue
                if any(not ctx.has(c) for c in d.inputs):
                    continue
                names = {c: ctx.proxy(c) for c in list(d.inputs) + list(d.optional_inputs)
                         if ctx.has(c)}
                val = evaluate(d.expr, names)
                if val is None or isinstance(val, bool):
                    continue
                obs = self._make(d, float(val), enc, ctx)
                enc.observations.add(obs)
                produced.append(obs)
                added = True
            if not added:
                break

        # 一致性校验
        for d in self.registry.defs:
            if not d.cross_check_code:
                continue
            mine = enc.observations.get(d.code)
            theirs = enc.observations.get(d.cross_check_code)
            if mine is None or theirs is None:
                continue
            if mine.value is None or not theirs.value:
                continue
            rel = abs(mine.value - theirs.value) / abs(theirs.value)
            if rel > d.cross_check_tolerance:
                issues.append(ConsistencyIssue(
                    code=d.cross_check_code, reported=theirs.value,
                    recomputed=round(mine.value, 4), formula=d.expr,
                    rel_diff=round(rel, 4),
                    severity="warn" if rel < 0.1 else "error",
                ))
        return produced, issues

    def _make(self, d: DerivedDef, val: float, enc: Encounter,
              ctx: RuleContext) -> Observation:
        ref = None
        if d.ref_low is not None or d.ref_high is not None:
            ref = RefRange(low=d.ref_low, high=d.ref_high, kind=d.ref_kind, raw=d.ref_raw)
        advisory = adv_status = adv_source = None
        if ref is None and d.advisory is not None:
            cut = d.advisory.resolve(self.sex)
            if cut is not None:
                advisory = RefRange(low=cut.low, high=cut.high,
                                    kind=RangeKind.DISEASE_CUTOFF,
                                    source_note=cut.note)
                adv_status = judge(val, None, advisory)
                adv_source = cut.source
        display = None
        if d.formula_display:
            try:
                display = d.formula_display.format(
                    **{c: _fmt(ctx.obs(c).value) for c in d.inputs if ctx.obs(c)})
            except (KeyError, IndexError, AttributeError):
                display = d.formula_display
        return Observation(
            code=d.code, raw_name=d.name, kind=ObservationKind.DERIVED,
            value=round(val, 6), unit=d.unit, ref=ref,
            status=judge(val, None, ref),
            advisory_ref=advisory,
            advisory_status=adv_status or RangeStatus.UNKNOWN,
            advisory_source=adv_source,
            observed_at=enc.anchor_date,
            formula=display or d.expr, inputs=tuple(d.inputs),
            provenance=Provenance(
                source_id="derived", source_label="本系统派生",
                raw_text=display or d.expr, extractor="derive-engine",
            ),
        )


def _fmt(x) -> str:
    if x is None:
        return "—"
    return str(int(x)) if float(x).is_integer() else f"{x:g}"
