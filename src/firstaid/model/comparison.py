"""纵向可比性。

「下次比什么」在这个系统里不是一段文案，是一个会被持久化的对象：
本次判读产出 ComparisonPlan，下次体检把新数据按同一把口径尺子对上去。
比不了要说清为什么比不了（换设备、换单位、换方法），而不是硬比。
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import Field

from .common import Frozen
from .observation import Observation


class Comparability(str, Enum):
    COMPARABLE = "comparable"
    UNIT_MISMATCH = "unit_mismatch"
    METHOD_MISMATCH = "method_mismatch"
    DEVICE_MISMATCH = "device_mismatch"     # 影像换设备即不可比
    AXIS_MISMATCH = "axis_mismatch"
    MISSING = "missing"


class ComparabilityKey(Frozen):
    code: str
    unit: str | None = None
    method: str | None = None
    device: str | None = None
    axis: str | None = None
    device_sensitive: bool = False   # True 时换设备直接判不可比（CAP/LSM）

    @classmethod
    def of(cls, obs: Observation, device_sensitive: bool = False) -> "ComparabilityKey":
        return cls(code=obs.code, unit=obs.unit, method=obs.method,
                   device=obs.device, axis=obs.axis,
                   device_sensitive=device_sensitive)

    def check(self, other: Observation) -> Comparability:
        if other.code != self.code:
            return Comparability.MISSING
        if self.unit and other.unit and other.unit != self.unit:
            return Comparability.UNIT_MISMATCH
        if self.method and other.method and other.method != self.method:
            return Comparability.METHOD_MISMATCH
        if self.device_sensitive and self.device and other.device \
                and other.device != self.device:
            return Comparability.DEVICE_MISMATCH
        if self.axis and other.axis and other.axis != self.axis:
            return Comparability.AXIS_MISMATCH
        return Comparability.COMPARABLE


class ComparisonItem(Frozen):
    """一条「下次比什么」。

    what 说的是比什么对象，caveat 说的是比的前提。
    刻意不允许写成"看有没有变化"这类无法验证的话——必须落到 key 上。
    """
    key: ComparabilityKey
    what: str                              # "只比 M1 段本身，不比报告结论"
    baseline_display: str                  # "116 × 46 mm"
    caveat: str | None = None              # "必须同一台设备"
    rationale: str | None = None           # 为什么盯这个而不是别的
    from_rule: str | None = None


class ComparisonPlan(Frozen):
    subject_id: str
    encounter_id: str
    created_for: date
    items: tuple[ComparisonItem, ...] = ()

    def codes(self) -> set[str]:
        return {i.key.code for i in self.items}


class ComparisonResult(Frozen):
    """把新一次体检的观察对到上一次的 plan 上之后的结果。"""
    item: ComparisonItem
    status: Comparability
    previous_display: str
    current_display: str | None = None
    delta: float | None = None
    note: str | None = None
