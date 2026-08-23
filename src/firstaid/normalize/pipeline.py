"""L1 归一：提取器给的原始行 → 规范 Observation。

解析不了的不丢，落成 UNKNOWN 状态并进审计报告的「暂未判定高低」——
数据缺失只影响分析覆盖范围，不能被包装成健康风险，也不能被当成正常。
"""
from __future__ import annotations

from datetime import date

from ..model import (
    Observation, ObservationKind, Ontology, Provenance, Qualitative, RangeKind,
    RangeStatus, RefRange,
)
from .refrange import judge, parse_range, parse_value
from .units import UnitTable

_QUAL = {
    "阴性": Qualitative.NEGATIVE, "negative": Qualitative.NEGATIVE, "-": Qualitative.NEGATIVE,
    "阳性": Qualitative.POSITIVE, "positive": Qualitative.POSITIVE, "+": Qualitative.POSITIVE,
    "±": Qualitative.TRACE, "弱阳性": Qualitative.TRACE,
    "未检出": Qualitative.NOT_DETECTED, "未见": Qualitative.NOT_DETECTED,
    "正常": Qualitative.NORMAL, "未见异常": Qualitative.NORMAL,
    "未见明显异常": Qualitative.NORMAL, "normal": Qualitative.NORMAL,
}


class Normalizer:
    def __init__(self, ontology: Ontology, units: UnitTable | None = None):
        self.ontology = ontology
        self.units = units or UnitTable()
        self.unresolved: list[str] = []

    def normalize(self, row: dict, provenance: Provenance,
                  default_date: date | None = None) -> Observation | None:
        raw_name = row.get("raw_name") or row.get("name") or ""
        code = row.get("code") or self.ontology.resolve(raw_name)
        if not code:
            # 认不出来的指标不丢弃，记录下来供本体补充；但不进判读。
            self.unresolved.append(raw_name)
            return None
        d = self.ontology.get(code)

        value, censor = parse_value(row.get("value"))
        qual = _QUAL.get(str(row.get("value", "")).strip()) if value is None else None
        text = row.get("text")
        kind = ObservationKind(row["kind"]) if row.get("kind") else (
            d.kind if d else ObservationKind.QUANTITATIVE)

        ref = parse_range(
            row.get("ref"),
            kind=RangeKind(row["ref_kind"]) if row.get("ref_kind")
            else (d.default_range_kind if d else RangeKind.UNSPECIFIED),
            source_note=row.get("ref_note"),
        )

        obs = Observation(
            code=code, raw_name=raw_name or (d.name if d else code), kind=kind,
            value=value, censor=censor, qualitative=qual, text=text,
            unit=row.get("unit"), ref=ref,
            status=judge(value, censor, ref) if (value is not None or ref) else (
                RangeStatus.NO_RANGE if qual is None and text else RangeStatus.UNKNOWN),
            reported_flag=row.get("flag"),
            method=row.get("method"), device=row.get("device"),
            specimen=row.get("specimen"), axis=row.get("axis"),
            observed_at=row.get("observed_at") or default_date,
            provenance=provenance,
        )
        if qual is not None:
            obs = obs.model_copy(update={"status": RangeStatus.NO_RANGE})

        # 补常用切点（只在原报告没给区间时）
        if d and (d.advisory_low is not None or d.advisory_high is not None) \
                and not obs.has_range and obs.value is not None:
            adv = RefRange(low=d.advisory_low, high=d.advisory_high,
                           kind=RangeKind.DISEASE_CUTOFF,
                           raw=None, source_note=d.advisory_note)
            obs = obs.model_copy(update={
                "advisory_ref": adv,
                "advisory_status": judge(obs.value, obs.censor, adv),
                "advisory_source": d.advisory_source,
            })

        # 单位归一到本体的 canonical 单位
        if d and d.canonical_unit and obs.unit and obs.unit != d.canonical_unit:
            conv = self.units.convert(obs, d.canonical_unit)
            if conv is not None:
                obs = conv.model_copy(update={"status": judge(conv.value, conv.censor, conv.ref)})
        return obs
