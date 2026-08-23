"""单位换算。换算表是数据（knowledge/ontology/units.yaml），不是代码。

配对背离那类规则要求把 ApoB(g/L) 和非HDL-C(mmol/L) 放到同一把尺子上比，
所以单位换算不是清洗步骤，而是判读的前提。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..model import Observation, RefRange


class UnitTable:
    def __init__(self, factors: dict[str, dict[str, float]] | None = None):
        # factors[code][from_unit] = 乘以它得到 canonical 单位的值
        self.factors = factors or {}
        self.generic: dict[tuple[str, str], float] = {}

    @classmethod
    def load(cls, path: str | Path) -> "UnitTable":
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        t = cls(doc.get("by_indicator", {}))
        for row in doc.get("generic", []):
            t.generic[(row["from"], row["to"])] = float(row["factor"])
            if row.get("reversible", True) and row["factor"]:
                t.generic[(row["to"], row["from"])] = 1.0 / float(row["factor"])
        return t

    def factor(self, code: str, from_unit: str | None, to_unit: str | None) -> float | None:
        if from_unit is None or to_unit is None or from_unit == to_unit:
            return 1.0
        per_code = self.factors.get(code, {})
        key = f"{from_unit}->{to_unit}"
        if key in per_code:
            return float(per_code[key])
        return self.generic.get((from_unit, to_unit))

    def convert(self, obs: Observation, to_unit: str) -> Observation | None:
        f = self.factor(obs.code, obs.unit, to_unit)
        if f is None or obs.value is None:
            return None
        ref = obs.ref
        if ref is not None:
            ref = RefRange(
                low=None if ref.low is None else ref.low * f,
                high=None if ref.high is None else ref.high * f,
                kind=ref.kind, raw=ref.raw, source_note=ref.source_note,
            )
        return obs.model_copy(update={"value": obs.value * f, "unit": to_unit, "ref": ref})
