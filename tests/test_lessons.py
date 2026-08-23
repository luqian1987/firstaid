"""错误台账本身要被守住。

这套系统的核心哲学是"每条观察必须有归宿"。同样的思路用在错误上：
每个记下来的错必须有归宿——落在哪一层、被哪条测试守着。
台账里指向的测试如果不存在，台账就退化成一份没人看的文档。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "knowledge" / "lessons" / "lessons.yaml"

# 越靠前越有价值：只有前两层能防止同类再犯
LAYERS = ["invariant", "criterion", "archetype", "knowledge", "hardcode"]


@pytest.fixture(scope="module")
def lessons():
    return yaml.safe_load(LEDGER.read_text(encoding="utf-8"))["lessons"]


@pytest.fixture(scope="module")
def known_tests() -> set[str]:
    """从测试文件里静态收集函数名，不跑子进程。"""
    out: set[str] = set()
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name.startswith("test_"):
                out.add(f"tests/{f.name}::{node.name}")
    return out


def test_ledger_shape(lessons):
    seen = set()
    for l in lessons:
        assert l["id"] not in seen, f"id 重复: {l['id']}"
        seen.add(l["id"])
        for field in ("symptom", "root_cause", "layer", "fix", "guarded_by"):
            assert l.get(field), f"{l['id']} 缺字段 {field}"
        assert l["layer"] in LAYERS, f"{l['id']} 的 layer 不在允许集合: {l['layer']}"


def test_every_lesson_points_to_a_real_test(lessons, known_tests):
    """台账里指向的测试必须真实存在。指不到的等于没修。"""
    missing = [(l["id"], t) for l in lessons for t in l["guarded_by"]
               if t not in known_tests]
    assert missing == [], missing


def test_hardcoded_fixes_must_justify_why_they_cannot_generalize(lessons):
    """降级到硬编码是允许的，但必须说明为什么上不去。

    没有这条，"硬编码"会变成偷懒的默认选项。
    """
    for l in lessons:
        if l["layer"] == "hardcode":
            assert l.get("why_not_general"), \
                f"{l['id']} 降级到硬编码却没说明为什么无法泛化"


def test_most_fixes_land_on_the_two_preventive_layers(lessons):
    """不变式与判据是仅有的两层能防止同类再犯的修复。

    这条不是硬性门槛，是一个会说话的信号：如果多数修复都落在
    knowledge/hardcode，说明在一个一个补窟窿，而不是在关掉整类窟窿。
    """
    preventive = sum(1 for l in lessons if l["layer"] in ("invariant", "criterion"))
    assert preventive / len(lessons) >= 0.5, (
        f"只有 {preventive}/{len(lessons)} 条修复落在预防层——"
        "在补窟窿，不是在关窟窿")


def test_docs_mention_the_ledger(lessons):
    """台账要被文档指到，否则新人不会知道它存在。"""
    txt = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "lessons" in txt
