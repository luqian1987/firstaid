"""L2 派生指标定义。

派生值不是装饰：几条主要判读的依据正是原报告没算的这些数，
而不是任何单项的箭头。所以每个派生值必须带公式和输入，可回溯、可复核。
"""
from __future__ import annotations

from pydantic import Field

from .common import Frozen, RangeKind


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
