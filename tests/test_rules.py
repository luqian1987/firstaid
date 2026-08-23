"""每条规则自带的夹具全部跑一遍。

这是知识库能长期扩充的前提：加一条规则必须同时加一个会命中的夹具
和一个不该命中的反例，否则规则库越长越不可信。
"""
from __future__ import annotations

import pytest

from harness import build, evaluate


def _cases(ruleset):
    for rule in ruleset.rules:
        for t in rule.tests:
            yield pytest.param(rule, t, id=f"{rule.id}::{t.name}")


def test_ruleset_shape(knowledge):
    _, _, rules, _ = knowledge
    assert rules.validate_all() == []


def test_every_rule_has_positive_and_negative_case(knowledge):
    """只有正例的规则不算写完——没有反例就无法证明它不会乱命中。"""
    _, _, rules, _ = knowledge
    weak = [r.id for r in rules.rules
            if not any(t.expect == "triggered" for t in r.tests)
            or not any(t.expect != "triggered" for t in r.tests)]
    assert weak == [], f"这些规则缺正例或反例: {weak}"


def test_rule_fixtures(knowledge, request):
    ont, units, rules, derived = knowledge
    failures = []
    for rule in rules.rules:
        for t in rule.tests:
            if not t.fixture:
                continue
            enc = build(t.fixture, t.overrides, ont, units, derived)
            hit = evaluate(rule, enc, ont)
            if hit.state.value != t.expect:
                failures.append(
                    f"{rule.id} / {t.name}: 期望 {t.expect}，实际 {hit.state.value}"
                    f"（缺 {list(hit.missing_codes)}）")
    assert failures == [], "\n".join(failures)
