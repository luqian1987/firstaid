from __future__ import annotations

import math

import pytest

from firstaid.derive.engine import DeriveEngine
from firstaid.model import RangeStatus


@pytest.fixture
def derived_enc(zhang, knowledge):
    _, _, _, derived = knowledge
    enc = zhang.latest()
    DeriveEngine(derived).run(enc)
    return enc


@pytest.mark.parametrize("code,expected", [
    ("HOMA_IR", 4.90 * 6.14 / 22.5),
    ("FIB4", 42 * 36 / (162 * math.sqrt(47))),
    ("NONHDL_C", 3.84 - 1.52),
    ("TG_HDL_RATIO", 1.56 / 1.52),
    ("AST_ALT_RATIO", 36 / 47),
    ("WHTR", 88 / 164),
    ("APOB_MGDL", 139.0),
])
def test_derived_arithmetic(derived_enc, code, expected):
    o = derived_enc.observations.get(code)
    assert o is not None, f"{code} 未生成"
    assert o.value == pytest.approx(expected, rel=1e-6)


def test_derived_values_carry_their_formula(derived_enc):
    o = derived_enc.observations.get("HOMA_IR")
    assert o.formula and "÷ 22.5" in o.formula
    assert o.inputs == ("GLU_FASTING", "INSULIN")
    assert o.provenance.source_label == "本系统派生"


def test_derived_can_depend_on_derived(derived_enc):
    """非HDL-C(mg/dL) 依赖非HDL-C，后者本身也是派生值。"""
    assert derived_enc.observations.get("NONHDL_C_MGDL").value == pytest.approx(
        (3.84 - 1.52) * 38.67, rel=1e-6)


def test_bmi_consistency_issue_is_surfaced(zhang, knowledge):
    """原报告 BMI 26.9，身高164/体重71.2 反算 26.47。
    不影响结论，但正是这一层该抓的东西。"""
    _, _, _, derived = knowledge
    _, issues = DeriveEngine(derived).run(zhang.latest())
    bmi = next(i for i in issues if i.code == "BMI")
    assert bmi.reported == 26.9
    assert bmi.recomputed == pytest.approx(26.472, abs=0.01)
    assert bmi.severity == "warn"


def test_whtr_crosses_its_cutoff(derived_enc):
    assert derived_enc.observations.get("WHTR").status is RangeStatus.HIGH


def test_expression_sandbox_rejects_escapes():
    from firstaid.patterns.expr import ExprError, validate
    for bad in ["__import__('os').system('x')", "x.__class__", "[].__len__()",
                "open('f')", "lambda: 1"]:
        with pytest.raises(ExprError):
            validate(bad)


def test_expression_missing_input_yields_none_not_false():
    """缺输入必须求值成 None → 上层判 INDETERMINATE，绝不当作未命中。"""
    from firstaid.patterns.expr import evaluate
    assert evaluate("A.value > 1", {}) is None
