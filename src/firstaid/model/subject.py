"""受检人与体检次。纵向的容器。

v1 只分析单次，但数据模型现在就按多次设计——Encounter 是一等对象，
Timeline 保证按时间排序，判读永远针对 "timeline 中的某一次 + 它之前的全部"。
"""
from __future__ import annotations

from datetime import date

from pydantic import Field

from .common import Frozen, Mutable, Sex, SourceDocument
from .observation import Observation, ObservationSet
from .original import OriginalFinding


class Subject(Frozen):
    id: str
    sex: Sex = Sex.UNKNOWN
    birth_date: date | None = None
    age_at_report: int | None = None       # 原报告直接给的年龄，缺生日时用
    display_name: str | None = None        # 客户页默认不展示

    def age_on(self, when: date | None) -> int | None:
        if self.birth_date and when:
            return (when - self.birth_date).days // 365
        return self.age_at_report


class Encounter(Mutable):
    """一次体检周期。可能由多份报告合并而成。"""
    id: str
    subject_id: str
    date_from: date
    date_to: date | None = None
    sources: list[SourceDocument] = Field(default_factory=list)
    observations: ObservationSet = Field(default_factory=ObservationSet)
    # 原报告自己给出的结论与建议。没有它就无法对账，只能自说自话。
    original_findings: list[OriginalFinding] = Field(default_factory=list)
    # 本人背景事实：key 为 ContextKey 的值，缺失即不在字典里
    context: dict[str, str] = Field(default_factory=dict)

    @property
    def anchor_date(self) -> date:
        return self.date_from

    def label(self) -> str:
        if self.date_to and self.date_to != self.date_from:
            return f"{self.date_from} 至 {self.date_to}"
        return str(self.date_from)


class Timeline(Mutable):
    subject: Subject
    encounters: list[Encounter] = Field(default_factory=list)

    def sorted(self) -> list[Encounter]:
        return sorted(self.encounters, key=lambda e: e.anchor_date)

    def latest(self) -> Encounter | None:
        s = self.sorted()
        return s[-1] if s else None

    def before(self, enc: Encounter) -> list[Encounter]:
        return [e for e in self.sorted() if e.anchor_date < enc.anchor_date]

    def series(self, code: str) -> list[tuple[date, Observation]]:
        """某指标的历史序列，只返回可比的那些（口径一致性由调用方校验）。"""
        out: list[tuple[date, Observation]] = []
        for e in self.sorted():
            for o in e.observations.all_of(code):
                out.append((o.observed_at or e.anchor_date, o))
        return out

    def is_single_point(self) -> bool:
        return len(self.encounters) <= 1
