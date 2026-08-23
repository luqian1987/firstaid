"""规则夹具运行器。

overrides 语法：
    {LPA: 120}                     改数值
    {APOA1: null}                  删掉这条观察（模拟指标缺失 → 应判 INDETERMINATE）
    {COQ10__ref_kind: disease_cutoff}  改参考区间口径
"""
from __future__ import annotations

from pathlib import Path

import yaml

from firstaid.derive.engine import DeriveEngine
from firstaid.loader import load_fixture
from firstaid.model import RangeKind
from firstaid.normalize.refrange import judge
from firstaid.patterns.archetypes import REGISTRY
from firstaid.patterns.context import RuleContext

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def build(fixture: str, overrides: dict, ont, units, derived):
    raw = yaml.safe_load((FIXTURES / f"{fixture}.yaml").read_text(encoding="utf-8"))
    drop, setval, setattrs = set(), {}, {}
    for k, v in (overrides or {}).items():
        if "__" in k:
            code, attr = k.split("__", 1)
            setattrs.setdefault(code, {})[attr] = v
            continue
        if v is None:
            drop.add(k)
        else:
            setval[k] = v

    rows = []
    for row in raw["observations"]:
        code = row["code"]
        if code in drop:
            continue
        row = dict(row)
        if code in setval:
            row["value"] = setval[code]
        for attr, val in setattrs.get(code, {}).items():
            row[attr] = val
        rows.append(row)
    raw["observations"] = rows

    tmp = FIXTURES / f".tmp_{fixture}.yaml"
    tmp.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    try:
        tl, _ = load_fixture(tmp, ont, units)
    finally:
        tmp.unlink(missing_ok=True)
    enc = tl.latest()
    DeriveEngine(derived).run(enc)
    return enc


def evaluate(rule, enc):
    impl = REGISTRY[rule.archetype]
    return impl.run(rule.id, RuleContext(enc), rule.params)
