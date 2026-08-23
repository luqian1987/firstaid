"""L1 本体：指标的规范定义。

数据来源泛化（不同医院、不同实验室），所以别名表和单位换算必须是数据而不是代码。
"""
from __future__ import annotations

from pydantic import Field

from .common import Frozen, Mutable, ObservationKind, RangeKind
from .finding import Modifiability


class IndicatorDef(Frozen):
    code: str
    name: str
    short: str | None = None
    kind: ObservationKind = ObservationKind.QUANTITATIVE
    canonical_unit: str | None = None
    aliases: tuple[str, ...] = ()          # 各医院写法
    unit_aliases: dict[str, str] = Field(default_factory=dict)
    system: str | None = None              # 归属系统：lipid / liver / renal ...
    default_range_kind: RangeKind = RangeKind.UNSPECIFIED

    # 强制属性：这一条能不能靠本人行为改变
    modifiability: Modifiability = Modifiability.UNKNOWN
    modifiability_note: str | None = None

    device_sensitive: bool = False         # 换设备即不可比（CAP / LSM / 影像径线）

    # 原报告没给区间时，本系统可补一个常用切点。它进 advisory_* 字段，
    # 永远不冒充报告自带区间。必须写明出处。
    advisory_low: float | None = None
    advisory_high: float | None = None
    advisory_note: str | None = None
    advisory_source: str | None = None

    note: str | None = None

    def matches(self, raw_name: str) -> bool:
        n = _norm(raw_name)
        if n == _norm(self.name):
            return True
        return any(n == _norm(a) for a in self.aliases)


class Ontology(Mutable):
    indicators: dict[str, IndicatorDef] = Field(default_factory=dict)
    _alias_index: dict[str, str] = {}

    def add(self, d: IndicatorDef) -> None:
        self.indicators[d.code] = d
        self._alias_index[_norm(d.name)] = d.code
        if d.short:
            self._alias_index[_norm(d.short)] = d.code
        for a in d.aliases:
            self._alias_index[_norm(a)] = d.code

    def get(self, code: str) -> IndicatorDef | None:
        return self.indicators.get(code)

    def resolve(self, raw_name: str) -> str | None:
        """原报告写法 → 规范 code。解析不了返回 None（不猜）。"""
        return self._alias_index.get(_norm(raw_name))

    def modifiability(self, code: str) -> Modifiability:
        d = self.get(code)
        return d.modifiability if d else Modifiability.UNKNOWN

    def device_sensitive(self, code: str) -> bool:
        d = self.get(code)
        return bool(d and d.device_sensitive)


def _norm(s: str) -> str:
    if s is None:
        return ""
    out = s.strip().lower()
    for ch in " \t　()（）[]【】·-—_/、,，.":
        out = out.replace(ch, "")
    return out
