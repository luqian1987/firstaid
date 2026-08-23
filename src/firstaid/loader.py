"""知识库与夹具的加载。"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .model import (
    Encounter, IndicatorDef, Observation, ObservationKind, ObservationSet, Ontology,
    OriginalFinding, Provenance, Sex, SourceDocument, Subject, Timeline,
)
from .normalize.pipeline import Normalizer
from .normalize.units import UnitTable
from .patterns.rule import RuleSet, load_rules
from .derive.engine import load_derived

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "knowledge"


def load_ontology(path: Path | None = None) -> Ontology:
    base = path or (KNOWLEDGE / "ontology")
    files = sorted(base.glob("indicators*.yaml")) if base.is_dir() else [base]
    ont = Ontology()
    for f in files:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for raw in doc.get("indicators", []):
            raw = dict(raw)
            raw["aliases"] = tuple(raw.get("aliases", []))
            ont.add(IndicatorDef.model_validate(raw))
    return ont


def load_units(path: Path | None = None) -> UnitTable:
    return UnitTable.load(path or (KNOWLEDGE / "ontology" / "units.yaml"))


def load_knowledge():
    return (load_ontology(), load_units(),
            load_rules(KNOWLEDGE / "rules"),
            load_derived(KNOWLEDGE / "derived"))


def load_fixture(path: str | Path, ontology: Ontology,
                 units: UnitTable | None = None) -> tuple[Timeline, Normalizer]:
    """夹具 YAML → Timeline。夹具走的是和真实数据完全相同的归一路径。"""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    s = doc["subject"]
    subject = Subject(
        id=s["id"], sex=Sex(s.get("sex", "unknown")),
        birth_date=s.get("birth_date"), age_at_report=s.get("age_at_report"),
        display_name=s.get("display_name"),
    )
    e = doc["encounter"]
    sources = [SourceDocument.model_validate(x) for x in e.get("sources", [])]
    enc = Encounter(
        id=e["id"], subject_id=subject.id,
        date_from=e["date_from"], date_to=e.get("date_to"),
        sources=sources, context=e.get("context", {}) or {},
        observations=ObservationSet(),
    )
    for raw in doc.get("original_findings", []):
        raw = dict(raw)
        page = raw.pop("page", None)
        raw["codes"] = tuple(raw.get("codes", []))
        raw["provenance"] = Provenance(
            source_id="main", source_label=sources[0].label if sources else "主报告",
            page=page, extractor="fixture")
        enc.original_findings.append(OriginalFinding.model_validate(raw))

    labels = {s.id: s.label for s in sources}
    norm = Normalizer(ontology, units or UnitTable(), sex=subject.sex)
    for row in doc.get("observations", []):
        row = dict(row)
        sid = row.pop("source", "unknown")
        prov = Provenance(source_id=sid, source_label=labels.get(sid, sid),
                          page=row.pop("page", None), extractor="fixture")
        obs = norm.normalize(row, prov, default_date=enc.anchor_date)
        if obs is not None:
            enc.observations.add(obs)

    # 年龄注入为观察，供 FIB-4 等派生公式使用
    age = subject.age_on(enc.anchor_date)
    if age is not None and enc.observations.get("AGE") is None:
        enc.observations.add(Observation(
            code="AGE", raw_name="年龄", value=float(age), unit="岁",
            kind=ObservationKind.DERIVED, observed_at=enc.anchor_date,
            provenance=Provenance(source_id="subject", source_label="受检人信息",
                                  extractor="loader"),
        ))
    return Timeline(subject=subject, encounters=[enc]), norm
