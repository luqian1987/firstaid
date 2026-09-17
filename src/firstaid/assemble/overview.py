"""按身体分区的总览。

客户版的第一个问题是"我有事吗"，第二个紧挨着的是"那你都查了什么"。
后者现在没人回答：完整版把 196 条观察摊在各章，客户版一条都不给。
"你查了 196 项、其中 20 项有箭头、集中在这 4 个区"——这句话本身就是结论。

实验室分组（血流变、肿瘤标志物）是给判读用的，不是给人看的，
所以中间隔一层显式映射，见 knowledge/ontology/_systems.yaml。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..model import ObservationKind, Ontology

_CACHE: dict | None = None

# 判读里担任主角的角色。与对账层用的是同一套定义。
LEAD_ROLES = {
    "hidden", "lead", "upstream", "abnormal", "finding", "raw", "particle",
    "cargo", "borderline", "structural", "acute_phase", "anchor", "factor",
    "lesion", "duplicate", "flagged",
}


def load_systems(path: str | Path) -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return _CACHE


def check_systems(spec: dict, ontology: Ontology) -> list[str]:
    """本体里的每个 system 都要有归属。漏一个，总览里就会凭空少掉一批指标。"""
    mapped = {s for g in spec["groups"].values() for s in g["of"]}
    mapped |= set(spec.get("excluded", []))
    used = {d.system for d in ontology.indicators.values() if d.system}
    errs = [f"指标分组 {s!r} 没有归入任何身体分区（见 knowledge/ontology/_systems.yaml）"
            for s in sorted(used - mapped)]
    errs += [f"身体分区 {g!r} 不在 order 里，总览会漏掉它"
             for g in spec["groups"] if g not in spec["order"]]
    return errs


def counted(enc, ontology: Ontology, excluded) -> list:
    """进总览的观察。

    派生值不算"查过的项目"——它们是我们算出来的，不是医院测的。
    把它们算进"这一次查了多少项"会虚报体检的覆盖面。
    """
    out = []
    for o in enc.observations:
        if o.kind is ObservationKind.DERIVED:
            continue
        d = ontology.get(o.code)
        if (d.system if d else None) in excluded:
            continue
        out.append(o)
    return out


def build_overview(enc, chains, ontology: Ontology, spec: dict) -> list[dict]:
    where = {s: g for g, d in spec["groups"].items() for s in d["of"]}
    excluded = set(spec.get("excluded", []))

    rows = {g: {"key": g, "label": spec["groups"][g]["label"],
                "n": 0, "abnormal": 0, "chains": []} for g in spec["order"]}
    for o in counted(enc, ontology, excluded):
        d = ontology.get(o.code)
        sysname = d.system if d else None
        g = where.get(sysname)
        if g is None:
            continue
        rows[g]["n"] += 1
        if o.abnormal:
            rows[g]["abnormal"] += 1

    # 每条判读归到它主角所在的分区。
    # 判读条数才是"这个区有没有发现"的信号，异常项数不是：
    # 影像发现多半没有参考区间因此不算 abnormal，只看异常数会把颅内狭窄、
    # 脾大、肺结节这一整类算成"0 异常"。
    for c in chains:
        seen = set()
        for e in c.inputs:
            if e.role not in LEAD_ROLES:
                continue
            d = ontology.get(e.observation.code)
            g = where.get(d.system if d else None)
            if g:
                seen.add(g)
        for g in seen:
            rows[g]["chains"].append(c.id)

    return [r for r in (rows[g] for g in spec["order"]) if r["n"]]
