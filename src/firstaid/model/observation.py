"""L0 观察层 + L1 归一后的观察表示。

一条 Observation 就是"一个可以进入判读的事实"。它可能来自化验单的一行、
超声报告里的一个尺寸，也可能是本系统算出来的派生值——三者在模式层被同等对待，
这样规则不必关心某个数是量出来的还是算出来的。
"""
from __future__ import annotations

import math
from datetime import date
from typing import Iterable, Iterator

from pydantic import Field, model_validator

from .common import (
    Frozen,
    Mutable,
    ObservationKind,
    Provenance,
    Qualitative,
    RangeKind,
    RangeStatus,
)


class RefRange(Frozen):
    """参考区间。

    low/high 任一为 None 表示单边区间（如 HDL-C ">1.04"、MMA "≤47.2"）。
    两者都为 None 表示原报告没给区间——这时 Observation.status 是 NO_RANGE，
    而不是"正常"。
    """
    low: float | None = None
    high: float | None = None
    kind: RangeKind = RangeKind.UNSPECIFIED
    raw: str | None = None          # 原报告里的写法，原样留存
    source_note: str | None = None  # "该实验室按340例健康人5%-95%分位"

    @property
    def bounded(self) -> bool:
        return self.low is not None and self.high is not None

    @property
    def span(self) -> float | None:
        if not self.bounded:
            return None
        s = self.high - self.low
        return s if s > 0 else None

    def display(self) -> str:
        if self.raw:
            return self.raw
        if self.low is not None and self.high is not None:
            return f"{_num(self.low)}–{_num(self.high)}"
        if self.high is not None:
            return f"≤{_num(self.high)}"
        if self.low is not None:
            return f"≥{_num(self.low)}"
        return "无区间"


class Observation(Frozen):
    # --- 身份 ---
    code: str                                   # 归一后的规范代码，如 "GGT"
    raw_name: str                               # 原报告写法，如 "γ-谷氨酰转移酶"
    kind: ObservationKind = ObservationKind.QUANTITATIVE

    # --- 值 ---
    value: float | None = None
    censor: str | None = None                   # "<" 或 ">"：低于/高于检测限
    qualitative: Qualitative | None = None
    text: str | None = None                     # 影像描述、文字结论原文
    unit: str | None = None

    # --- 区间与判定 ---
    # ref/status 永远只反映"原报告给了什么"。原报告没给区间就是 NO_RANGE，
    # 系统不拿自己的知识去冒充报告的区间。
    ref: RefRange | None = None
    status: RangeStatus = RangeStatus.UNKNOWN
    reported_flag: str | None = None            # 原报告自己打的箭头 "↑"/"↓"

    # 本系统按知识库补充的常用切点。与上面严格分开：
    # "原报告未给参考区间；常用切点 7.0 kPa 以下无明显纤维化" —— 两句话，两个字段。
    advisory_ref: RefRange | None = None
    advisory_status: RangeStatus = RangeStatus.UNKNOWN
    advisory_source: str | None = None

    # --- 可比性口径（纵向的地基）---
    method: str | None = None                   # 方法学
    device: str | None = None                   # 设备/机型，影像必填
    specimen: str | None = None
    axis: str | None = None                     # 影像测量轴，如 "长径"

    # --- 时间与出处 ---
    observed_at: date | None = None
    provenance: Provenance

    # --- 派生值专用 ---
    formula: str | None = None
    inputs: tuple[str, ...] = ()

    # ---------------- 判定辅助 ----------------
    @property
    def is_high(self) -> bool:
        return self.status is RangeStatus.HIGH

    @property
    def is_low(self) -> bool:
        return self.status is RangeStatus.LOW

    @property
    def in_range(self) -> bool:
        return self.status is RangeStatus.IN_RANGE

    @property
    def abnormal(self) -> bool:
        return self.status in (RangeStatus.HIGH, RangeStatus.LOW)

    @property
    def has_range(self) -> bool:
        return self.ref is not None and (
            self.ref.low is not None or self.ref.high is not None
        )

    @property
    def negative(self) -> bool:
        """定性阴性/正常，或定量值在区间内。用于"佐证全阴"类规则。"""
        if self.qualitative is not None:
            return self.qualitative in (
                Qualitative.NEGATIVE, Qualitative.NOT_DETECTED, Qualitative.NORMAL)
        return self.in_range

    @property
    def advisory_in_range(self) -> bool:
        return self.advisory_status is RangeStatus.IN_RANGE

    @property
    def advisory_high(self) -> bool:
        return self.advisory_status is RangeStatus.HIGH

    @property
    def advisory_low(self) -> bool:
        return self.advisory_status is RangeStatus.LOW

    @property
    def has_advisory(self) -> bool:
        return self.advisory_ref is not None

    @property
    def ratio_to_upper(self) -> float | None:
        """达上限的几倍。GGT 92 / 60 = 1.53——原文正是这么描述形态的。"""
        if self.value is None or self.ref is None or not self.ref.high:
            return None
        return self.value / self.ref.high

    @property
    def ratio_to_lower(self) -> float | None:
        if self.value is None or self.ref is None or not self.ref.low:
            return None
        return self.value / self.ref.low

    @property
    def position_in_range(self) -> float | None:
        """在区间内的相对位置：0=下限, 1=上限, >1 超上限, <0 低于下限。

        配对背离类规则靠这个把不同单位的指标放到同一把尺子上。
        """
        if self.value is None or self.ref is None or not self.ref.bounded:
            return None
        span = self.ref.span
        if span is None:
            return None
        return (self.value - self.ref.low) / span

    def comparability_key(self) -> tuple:
        """两次体检之间，什么条件下这两条观察才允许直接比较。"""
        return (self.code, self.unit, self.method, self.device, self.axis)

    def display_value(self) -> str:
        if self.text:
            return self.text
        if self.qualitative is not None:
            return {"negative": "阴性", "positive": "阳性", "trace": "±",
                    "not_detected": "未检出", "normal": "正常"}[self.qualitative.value]
        if self.value is None:
            return "—"
        return f"{self.censor or ''}{_num(self.value)}"

    @model_validator(mode="after")
    def _check(self):
        if self.kind is ObservationKind.IMAGING and self.value is not None:
            if not self.device and not self.method:
                # 影像测量值没有设备口径，纵向就没法比。允许存在，但标记出来。
                object.__setattr__(self, "axis", self.axis or "未标注口径")
        return self


class ObservationSet(Mutable):
    """一次体检里的全部观察。按 code 索引，同 code 多条时保留全部。"""
    items: list[Observation] = Field(default_factory=list)

    def __iter__(self) -> Iterator[Observation]:      # type: ignore[override]
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def add(self, obs: Observation) -> None:
        self.items.append(obs)

    def extend(self, obs: Iterable[Observation]) -> None:
        self.items.extend(obs)

    def get(self, code: str) -> Observation | None:
        for o in self.items:
            if o.code == code:
                return o
        return None

    def all_of(self, code: str) -> list[Observation]:
        return [o for o in self.items if o.code == code]

    def codes(self) -> set[str]:
        return {o.code for o in self.items}

    def abnormal(self) -> list[Observation]:
        return [o for o in self.items if o.abnormal]

    def unranged(self) -> list[Observation]:
        return [o for o in self.items if o.status is RangeStatus.NO_RANGE]


def _num(x: float) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    if float(x).is_integer():
        return str(int(x))
    return f"{x:g}"
