"""规则实例：纯数据。

一条规则 = 触发参数（交给模式）+ 表达骨架（交给叙述器）+ 判读四格 + 自带测试夹具。
规则里不允许出现任何自由发挥的结论文本 —— must_convey / must_not_claim
是给叙述器的约束，不是最终文案；最终文案由叙述器生成并受 allowed_values 校验。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ..model import Archetype, Band, Chapter, ContextKey, Modifiability, Tag


class CompareNextSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    what: str
    caveat: str | None = None
    rationale: str | None = None


class VerdictSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    certain: str
    not_certain: str
    next_steps: list[str] = Field(default_factory=list)
    compare_next: list[CompareNextSpec] = Field(default_factory=list)


class NarrationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    single_read: str                       # 只看单项会得到
    joint_read: str                        # 放在一起看得到
    must_convey: list[str] = Field(default_factory=list)
    must_not_claim: list[str] = Field(default_factory=list)


class CorrectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str                 # 内部精确说法
    claim_soft: str            # 对外措辞：陈述发现 + 请求确认，不判原报告对错
    original_advice: str
    original_source: str
    flagged: str                           # 被原报告打箭头的 code
    why_not: str
    what_to_do: str


class RuleTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    expect: str                            # triggered / not_triggered / indeterminate
    fixture: str | None = None             # 引用 tests/fixtures 下的夹具
    overrides: dict[str, Any] = Field(default_factory=dict)


class RuleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    archetype: Archetype
    title: str
    # 一句话结论，对账表里显示的就是它。刻意限长——写不进一行的结论说明还没想清楚。
    headline: str = ""
    lede: str = ""
    tag: Tag
    chapter: Chapter
    band: Band | None = None       # 覆盖 tag→band 的默认映射，通常不用写
    modifiability: Modifiability = Modifiability.UNKNOWN
    priority: float = 0.0
    params: dict[str, Any] = Field(default_factory=dict)
    # 参与展示但不参与触发的数值。B 版判读把"进入判断的全部数值"都摆出来，
    # 包括那些只作背景的正常项——这是可核对性的一部分，不是排版偏好。
    extra_evidence: list[str] = Field(default_factory=list)
    needs_context: list[ContextKey] = Field(default_factory=list)
    narration: NarrationSpec | None = None
    verdict: VerdictSpec | None = None
    correction: CorrectionSpec | None = None
    tests: list[RuleTest] = Field(default_factory=list)
    enabled: bool = True
    source: str | None = None              # 规则出自哪份指南/文献

    def validate_shape(self) -> list[str]:
        """构建期自检。规则写不完整，构建就该失败，而不是产出半截判读。"""
        errs: list[str] = []
        if self.chapter is Chapter.CORRECT and self.correction is None:
            errs.append(f"{self.id}: 归入「需纠正」章必须提供 correction 块")
        if self.correction is None and not self.headline.strip():
            errs.append(f"{self.id}: 缺 headline —— 对账表需要一句话结论")
        if len(self.headline) > 60:
            errs.append(f"{self.id}: headline 超过 60 字（{len(self.headline)}），"
                        "写不进一行的结论说明还没想清楚")
        if self.correction is not None and self.chapter is not Chapter.CORRECT:
            errs.append(f"{self.id}: 提供了 correction 块但章节不是 CORRECT")
        # 「需纠正」用「为什么不成立 / 怎么做」两段，不套用四段骨架；
        # 其余章节必须写全，缺一段就是规则没写完。
        if self.chapter not in (Chapter.ARCHIVE, Chapter.CORRECT):
            if self.narration is None:
                errs.append(f"{self.id}: 缺 narration（只看单项/放在一起看）")
            if self.verdict is None:
                errs.append(f"{self.id}: 缺 verdict 四格")
        if self.chapter is Chapter.ACT_NOW and \
                self.modifiability is Modifiability.NOT_MODIFIABLE:
            errs.append(
                f"{self.id}: 主线不可由本人改变，不允许归入「值得重视，也能主动改善」章"
                "——这正是 Lp(a) 被配上一套饮食方案的那类分类错误")
        if not self.tests:
            errs.append(f"{self.id}: 规则必须自带至少一个测试夹具")
        return errs


class RuleSet(BaseModel):
    rules: list[RuleSpec] = Field(default_factory=list)

    def enabled(self) -> list[RuleSpec]:
        return [r for r in self.rules if r.enabled]

    def by_id(self, rid: str) -> RuleSpec | None:
        return next((r for r in self.rules if r.id == rid), None)

    def validate_params(self) -> list[str]:
        """参数必须能被对应模式的参数模型接住。

        参数模型都是 extra="forbid"，所以字段名写错在这里就会被抓到，
        而不是等到某个病人恰好跑到这条规则时才炸——或者更糟，静默用默认值。
        """
        from .archetypes import REGISTRY
        errs: list[str] = []
        for r in self.rules:
            impl = REGISTRY.get(r.archetype)
            if impl is None:
                errs.append(f"{r.id}: 未实现的模式 {r.archetype.value}")
                continue
            try:
                impl.params_model.model_validate(r.params)
            except Exception as e:
                first = str(e).splitlines()[1] if "\n" in str(e) else str(e)
                errs.append(f"{r.id}: params 不合模式 {r.archetype.value} 的定义 —— {first}")
        return errs

    def validate_all(self) -> list[str]:
        errs: list[str] = []
        seen: set[str] = set()
        for r in self.rules:
            if r.id in seen:
                errs.append(f"规则 id 重复: {r.id}")
            seen.add(r.id)
            errs += r.validate_shape()
        errs += self.validate_params()
        return errs


def load_rules(path: str | Path) -> RuleSet:
    """从目录或单文件加载规则。"""
    p = Path(path)
    files: Iterable[Path] = sorted(p.glob("**/*.yaml")) if p.is_dir() else [p]
    rules: list[RuleSpec] = []
    for f in files:
        if f.name.startswith("_"):
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for raw in doc.get("rules", []):
            raw.setdefault("source", str(f.relative_to(p) if p.is_dir() else f.name))
            rules.append(RuleSpec.model_validate(raw))
    return RuleSet(rules=rules)


# --------------------------------------------------------------------------
# 模板渲染：{CODE} → 该观察的显示值；{$key} → 模式算出的中间量
# 只允许引用本规则 evidence 里出现过的 code，越界即报错。
# --------------------------------------------------------------------------
_TOKEN = re.compile(r"\{(\$?[A-Za-z0-9_]+)(?::([a-z_]+))?\}")


def render_template(text: str, values: dict[str, str], detail: dict[str, Any]) -> str:
    def sub(m: re.Match) -> str:
        key, fmt = m.group(1), m.group(2)
        if key.startswith("$"):
            v = detail.get(key[1:])
            if v is None:
                raise KeyError(f"模板引用了不存在的中间量 {key}")
            return f"{v:g}" if isinstance(v, float) else str(v)
        if key not in values:
            raise KeyError(f"模板引用了不在 evidence 里的指标 {key}")
        return values[key]
    return _TOKEN.sub(sub, text)
