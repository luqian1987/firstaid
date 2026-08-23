"""端到端流水线：L0 → L6。

每一层的产出都是可检查的对象，不是字符串。构建失败的条件写死在这里：
覆盖率不通过、分章不变式违反、规则组装报错——任何一条都不出报告。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .assemble.rank import check_chapters, group_by_chapter, rank
from .assemble.depth import DepthEngine, load_depth_spec
from .assemble.reconcile import reconcile
from .audit.coverage import build_coverage
from .derive.engine import DeriveEngine
from .loader import KNOWLEDGE, load_fixture, load_knowledge

KNOWLEDGE_DEPTH = KNOWLEDGE / "depth"
from .model import (
    BoundaryItem, Chain, ComparisonItem, ComparisonPlan, ConsistencyIssue, Correction,
    CoverageReport, Depth, Encounter, MissingContextItem, Ontology, Reconciliation,
    Timeline, Topology,
)
from .patterns.context import RuleContext
from .patterns.engine import EngineResult, PatternEngine


@dataclass
class Analysis:
    timeline: Timeline
    encounter: Encounter
    chains: list[Chain] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    boundaries: list[BoundaryItem] = field(default_factory=list)
    missing_context: list[MissingContextItem] = field(default_factory=list)
    consistency: list[ConsistencyIssue] = field(default_factory=list)
    coverage: CoverageReport | None = None
    recon: Reconciliation | None = None
    topology: Topology | None = None
    topo_excluded: list = field(default_factory=list)
    depth: dict[str, Depth] = field(default_factory=dict)
    derived_notes: dict[str, str] = field(default_factory=dict)
    plan: ComparisonPlan | None = None
    engine: EngineResult | None = None
    errors: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return (not self.errors
                and (self.coverage is None or self.coverage.ok())
                and (self.recon is None or self.recon.ok()))

    def blocking(self) -> list[str]:
        out = list(self.errors)
        if self.coverage:
            out += self.coverage.failures()
        if self.recon:
            out += [f"原报告第 {f.seq} 条「{f.said}」没有任何回答"
                    for f in self.recon.unaddressed]
        return out


def analyze(timeline: Timeline, ontology=None, units=None, rules=None,
            derived=None, depth_spec=None) -> Analysis:
    if ontology is None:
        ontology, units, rules, derived = load_knowledge()
    if depth_spec is None:
        depth_spec = load_depth_spec(KNOWLEDGE_DEPTH)
    enc = timeline.latest()
    assert enc is not None, "timeline 里没有体检记录"
    a = Analysis(timeline=timeline, encounter=enc)

    # 规则库自检先行：规则写不完整，不允许开始分析
    a.errors += rules.validate_all()

    # L2 派生
    _, issues = DeriveEngine(derived, timeline.subject.sex).run(enc)
    a.consistency = issues
    a.derived_notes = {d.code: d.changes_what for d in derived.defs if d.changes_what}

    # L3/L4 模式 → 链条
    engine = PatternEngine(rules, ontology)
    res = engine.run(RuleContext(enc))
    a.engine = res
    a.errors += res.errors
    a.chains = rank(res.chains)
    a.corrections = res.corrections
    a.boundaries = list(res.boundaries)
    a.missing_context = list(res.missing_context)

    # 纵向：单点时显式声明
    if timeline.is_single_point():
        a.boundaries.append(BoundaryItem(
            what="没有既往体检数据",
            impact="本次全部结论都只是单点，趋势要等下一次",
            critical=False,
        ))

    # 分章不变式
    a.errors += check_chapters(a.chains)

    # L4.5 对账：原报告说的每一条，本次判读怎么回答
    a.recon = reconcile(enc, a.chains, a.corrections)
    for f in a.recon.pending:
        a.boundaries.append(BoundaryItem(
            what=f"{f.source}（原报告标注「{f.said}」，本次未拿到）",
            impact="该项结论未纳入本判读",
        ))

    # L4.7 深读：通路 / 机制 / 修饰因素 / 干预
    de = DepthEngine(depth_spec, ontology, derived)
    a.errors += de.validate()
    chain_ids = {c.id for c in a.chains}
    order = [c.id for c in sorted(a.chains, key=lambda c: -c.priority)]
    a.topology = de.topology(enc, chain_ids, order)
    a.topo_excluded, scope_errs = de.scope(a.chains)
    a.errors += scope_errs
    a.errors += de.check_absent_modifiers(enc, a.chains)
    for c in a.chains:
        d = de.depth_for(enc, c, {i.key.code for i in c.verdict.compare_next}
                         if c.verdict else set())
        if d and d.any():
            a.depth[c.id] = d

    # L5 覆盖率
    a.coverage = build_coverage(enc, res, ontology)

    # 纵向计划。同一个指标被两条判读同时点名是常态（前列腺径线既进结构性存档、
    # 又进膀胱那条），合并成一行并把两种看法都保留 —— 丢掉任何一句都是丢信息，
    # 而列两遍会让人以为系统出错了。
    merged: dict[str, ComparisonItem] = {}
    for c in a.chains:
        for it in (c.verdict.compare_next if c.verdict else ()):
            prev = merged.get(it.key.code)
            if prev is None:
                merged[it.key.code] = it
                continue
            whats = [prev.what] + ([it.what] if it.what not in prev.what else [])
            caveats = [x for x in (prev.caveat, it.caveat) if x]
            merged[it.key.code] = prev.model_copy(update={
                "what": "；".join(whats),
                "caveat": "；".join(dict.fromkeys(caveats)) or None,
                "rationale": prev.rationale or it.rationale,
            })
    items = list(merged.values())
    a.plan = ComparisonPlan(
        subject_id=timeline.subject.id, encounter_id=enc.id,
        created_for=enc.anchor_date, items=tuple(items),
    )
    return a


def analyze_fixture(path: str | Path) -> Analysis:
    ontology, units, rules, derived = load_knowledge()
    timeline, _ = load_fixture(path, ontology, units)
    return analyze(timeline, ontology, units, rules, derived)


def chapters(a: Analysis):
    return group_by_chapter(a.chains)
