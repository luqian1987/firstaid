"""回归集：每一份真实报告夹具都必须整条流水线跑绿。

规则库是一次改一条长起来的。判断某条改动有没有把别人弄坏，
唯一可靠的办法是让它同时对着所有攒下来的真实报告跑一遍。

这里同时锁死另一件事：夹具文件加了却没登记，测试就失败。
覆盖率断言在这一层的形式就是它。
"""
from __future__ import annotations

import yaml
import pytest

from conftest import FIXTURES
from firstaid.loader import load_fixture
from firstaid.pipeline import analyze

_CORPUS = yaml.safe_load((FIXTURES / "corpus.yaml").read_text(encoding="utf-8"))
_CASES = [c["file"] for c in _CORPUS["cases"]]
_EXCLUDED = {c["file"] for c in _CORPUS["excluded"]}


def test_every_fixture_file_is_registered():
    on_disk = {p.name for p in FIXTURES.glob("*.yaml")} - {"corpus.yaml"}
    unregistered = on_disk - set(_CASES) - _EXCLUDED
    assert unregistered == set(), (
        f"这些夹具没有登记进 corpus.yaml：{sorted(unregistered)}。"
        "要么把它加进 cases 让它每次都跑，要么在 excluded 里写明为什么不跑。")
    missing = (set(_CASES) | _EXCLUDED) - on_disk
    assert missing == set(), f"corpus.yaml 里登记了不存在的夹具：{sorted(missing)}"


def test_every_excluded_fixture_states_a_reason():
    for c in _CORPUS["excluded"]:
        assert c.get("why", "").strip(), f"{c['file']} 被排除但没写理由"


@pytest.mark.parametrize("name", _CASES)
def test_real_case_builds(name, knowledge):
    ont, units, rules, derived = knowledge
    tl, _ = load_fixture(FIXTURES / name, ont, units)
    a = analyze(tl, ont, units, rules, derived)
    assert a.blocking() == [], f"{name}:\n" + "\n".join(a.blocking())
    assert a.ok(), name


@pytest.mark.parametrize("name", _CASES)
def test_real_case_answers_every_original_finding(name, knowledge):
    """原报告说的每一条，本次判读都要有回答。漏一条就是规则库缺一条。"""
    ont, units, rules, derived = knowledge
    tl, _ = load_fixture(FIXTURES / name, ont, units)
    a = analyze(tl, ont, units, rules, derived)
    unaddressed = [(f.seq, f.said) for f in a.recon.unaddressed]
    assert unaddressed == [], f"{name} 有没被回答的原报告结论：{unaddressed}"


@pytest.mark.parametrize("name", _CASES)
def test_real_case_never_reveals_identity(name, knowledge):
    """夹具必须已去标识。报告里出现姓名/身份证/电话即失败。"""
    import re
    raw = (FIXTURES / name).read_text(encoding="utf-8")
    assert not re.search(r"\b\d{15}(\d{2}[\dXx])?\b", raw), f"{name} 疑似含身份证号"
    assert not re.search(r"\b1[3-9]\d{9}\b", raw), f"{name} 疑似含手机号"
    ont, units, _, _ = knowledge
    tl, _ = load_fixture(FIXTURES / name, ont, units)
    assert tl.subject.display_name is None, f"{name} 夹具带了姓名"
