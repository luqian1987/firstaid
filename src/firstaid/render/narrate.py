"""L6 叙述层。

分工原则的执行点：
  规则决定"有没有这个发现"和"能引用哪些数"；叙述器只决定"怎么说"。

所以叙述器的输出要过一道机械校验：文本里出现的每一个数字，
必须能在 NarrationBrief.allowed_values 里找到对应。凭空出现的数字一律拒收。
这条校验对模板叙述器和 LLM 叙述器同等生效——没有例外通道。
"""
from __future__ import annotations

import re
from typing import Protocol

from ..model import Chain, NarrationBrief

_NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w])")

# 这些数字在中文里作序数/量词用，不算引用检验值
_BENIGN = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100}


class CitationError(ValueError):
    pass


def cited_numbers(text: str) -> list[float]:
    return [float(m.group(1)) for m in _NUMBER.finditer(text)]


def verify_citations(text: str, brief: NarrationBrief, tol: float = 0.02) -> list[float]:
    """返回文本里出现、但既不在允许值里、也不在原报告引文里的数字。空列表 = 通过。

    引文（参考区间写法、实验室区间口径说明、影像描述原文）里的数字算引用，
    不算断言 —— 否则"该实验室按 340 例健康人 5%-95% 分位定区间"这种
    对原报告的如实转述会被误判为编造。
    """
    allowed = list(brief.allowed_values)
    for q in brief.quoted_text:
        allowed += cited_numbers(q)
    bad: list[float] = []
    for n in cited_numbers(text):
        if n in _BENIGN:
            continue
        if any(abs(n - a) <= max(tol, abs(a) * tol) for a in allowed):
            continue
        bad.append(n)
    return bad


def verify_chain(chain: Chain) -> list[str]:
    if chain.brief is None:
        return [f"{chain.id}: 缺 NarrationBrief，无法校验引用"]
    errs = []
    for field, text in (("single_read", chain.single_read),
                        ("joint_read", chain.joint_read),
                        ("certain", chain.verdict.certain if chain.verdict else ""),
                        ("not_certain", chain.verdict.not_certain if chain.verdict else "")):
        bad = verify_citations(text, chain.brief)
        if bad:
            errs.append(f"{chain.id}.{field}: 引用了 evidence 里没有的数值 {bad}")
    return errs


class Narrator(Protocol):
    name: str

    def narrate(self, chain: Chain) -> Chain: ...


class TemplateNarrator:
    """确定性叙述器：直接用规则里写好的骨架，不调用任何模型。

    它存在的意义不是省钱，是让整条流水线在没有 API key 时也能跑通、能测试。
    LLM 叙述器只是把它的输出改写得更顺，受同一套校验约束。
    """
    name = "template"

    def narrate(self, chain: Chain) -> Chain:
        return chain


class LLMNarrator:
    """LLM 叙述器（骨架）。

    约束：
      - 输入只有 NarrationBrief + evidence 的显示值，看不到原始报告全文；
      - 不允许引入 must_convey 之外的新结论；
      - must_not_claim 逐条作为负面约束；
      - 输出过 verify_chain，任一条不通过就退回 TemplateNarrator 的文本。
    绝不让模型决定一个发现是否存在——它只重写已被规则认定的内容。
    """
    name = "llm"

    def __init__(self, client=None, fallback: Narrator | None = None):
        self.client = client
        self.fallback = fallback or TemplateNarrator()

    def narrate(self, chain: Chain) -> Chain:
        if self.client is None:
            return self.fallback.narrate(chain)
        raise NotImplementedError("LLM 叙述尚未接线；当前用 TemplateNarrator")
