"""L2 派生指标定义。

派生值不是装饰：几条主要判读的依据正是原报告没算的这些数，
而不是任何单项的箭头。所以每个派生值必须带公式和输入，可回溯、可复核。
"""
from __future__ import annotations

from pydantic import Field

from .common import Frozen, RangeKind, Sex


class AdvisoryCutoff(Frozen):
    """本系统补的常用切点。永远进 advisory_* 字段，不冒充报告自带区间。

    分性别是常态而不是特例（腰臀比、血红蛋白、尿酸……），所以切点本身
    就按性别建模；性别未知时只用 low/high 这一套通用值，宁可判不了也不猜。
    """
    low: float | None = None
    high: float | None = None
    note: str | None = None
    source: str | None = None                   # 必写出处，否则自检不过
    by_sex: dict[str, "AdvisoryCutoff"] = {}

    def resolve(self, sex: Sex | str | None) -> "AdvisoryCutoff | None":
        key = sex.value if isinstance(sex, Sex) else (sex or "")
        sub = self.by_sex.get(key)
        if sub is not None:
            return sub.model_copy(update={
                "note": sub.note or self.note,
                "source": sub.source or self.source,
            })
        if self.by_sex and (self.low is None and self.high is None):
            # 只按性别定义切点，而本次性别未知 —— 判不了，不退回通用值
            return None
        if self.low is None and self.high is None:
            return None
        return self


class DerivedDef(Frozen):
    code: str
    name: str
    unit: str | None = None
    expr: str                                   # 受限表达式，见 patterns/expr.py
    inputs: tuple[str, ...] = ()                # 需要的观察 code
    optional_inputs: tuple[str, ...] = ()
    ref_low: float | None = None
    ref_high: float | None = None
    ref_kind: RangeKind = RangeKind.UNSPECIFIED
    ref_raw: str | None = None
    # 原报告没给区间时用它补判据。派生值不会自带区间，所以这里是唯一来源。
    advisory: AdvisoryCutoff | None = None
    formula_display: str | None = None          # "4.90 × 6.14 ÷ 22.5" 用的模板
    changes_what: str | None = None             # 它改变了什么判断
    system: str | None = None

    # 一致性校验：若原报告也报了同名指标，重算值与其相差超过阈值即登记 issue
    cross_check_code: str | None = None
    cross_check_tolerance: float = 0.02
    note: str | None = None


class DerivedRegistry(Frozen):
    defs: tuple[DerivedDef, ...] = ()

    def get(self, code: str) -> DerivedDef | None:
        for d in self.defs:
            if d.code == code:
                return d
        return None
