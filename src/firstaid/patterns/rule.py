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


# 时限。刻意不叫"严重程度"——那是我编的，不可核对。
# 判据只有一条，而且可以逐条核对：**等它，会不会变？变了能不能回来？**
#
#   now          会变，而且不可逆（龋损只往深走）
#   weeks        判读现在悬着，而一个问题或一项便宜检查就能定性
#   next_checkup 会变，但慢且可逆
#   know_it      不会变（遗传、解剖变异、既往改变）——知道就行
#   none         已经明确不需要处理
HORIZONS = ("now", "weeks", "next_checkup", "know_it", "none")
HORIZON_LABELS = {
    "now": "现在",
    "weeks": "几周内",
    "next_checkup": "明年体检",
    "know_it": "知道就行",
    "none": "不用管",
}
HORIZON_WHY = {
    "now": "会变，而且不可逆",
    "weeks": "判读现在悬着，一个问题或一项便宜检查就能定性",
    "next_checkup": "会变，但慢且可逆",
    "know_it": "不会变",
    "none": "已经明确不需要处理",
}


class HorizonSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when: str
    why: str                       # 为什么落这一档，按可逆性判据写


class GapSpec(BaseModel):
    """由本次结果延伸出来、而本次没有覆盖的一项。

    triggered_by 是它和"套餐里没买这一项"的分界：本次必须真的有一个发现在指向它，
    这条缺失才成立。否则就是拿规则库比病人的套餐大来制造焦虑。
    """
    model_config = ConfigDict(extra="forbid")
    what: str                      # 缺的是什么
    because: str                   # 本次哪个结果指向了它
    triggered_by: list[str]        # 这些指标本次必须在场，否则这条缺失不成立
    horizon: str = "weeks"
    effort: str = "test"           # recall 回想 / fetch 取回 / home 在家做 / test 加一项检查


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
    # 客户版按它分组。band 回答"要不要做"，horizon 回答"多急"，两件事。
    horizon: HorizonSpec | None = None
    # 这条判读打开了哪些"本次没覆盖"的口子
    gaps: list[GapSpec] = Field(default_factory=list)

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
        if self.correction is None:
            if self.horizon is None:
                errs.append(f"{self.id}: 缺 horizon —— 客户版要回答的第一件事是「多急」，"
                            "而它不能由 band 推出来：band 说要不要做，horizon 说等不等得")
            elif self.horizon.when not in HORIZONS:
                errs.append(f"{self.id}: horizon.when={self.horizon.when!r} 不在 "
                            f"{'/'.join(HORIZONS)} 之内")
            elif not self.horizon.why.strip():
                errs.append(f"{self.id}: horizon 没写理由。判据是「等它会不会变、"
                            "变了能不能回来」，写不出这句话就是还没想清楚")
        for g in self.gaps:
            if g.horizon not in HORIZONS:
                errs.append(f"{self.id}: 缺失项「{g.what}」的 horizon 不合法")
            if not g.triggered_by:
                errs.append(f"{self.id}: 缺失项「{g.what}」没有 triggered_by。"
                            "说不出本次哪个结果指向它，那就不是「由结果延伸」，"
                            "只是套餐里没买这一项")
        return errs


class RuleSet(BaseModel):
    rules: list[RuleSpec] = Field(default_factory=list)

    def enabled(self) -> list[RuleSpec]:
        return [r for r in self.rules if r.enabled]

    def by_id(self, rid: str) -> RuleSpec | None:
        return next((r for r in self.rules if r.id == rid), None)

    def validate_horizons(self) -> list[str]:
        """band 与 horizon 必须自洽。

        两者是独立声明的两件事——band 说"要不要做"，horizon 说"等不等得"。
        正因为独立，它们互相是对方的校验：说"现在要做"却又说"不用管"，
        一定有一个写错了。
        """
        from ..model import band_of, Band
        errs: list[str] = []
        for r in self.rules:
            if r.correction is not None or r.horizon is None:
                continue
            b, w = band_of(r.tag, r.band), r.horizon.when
            if b is Band.ACT and w in ("know_it", "none"):
                errs.append(f"{r.id}: 归在「现在要做」档，horizon 却是 {w}（不用做）")
            if b is Band.SETTLE and w in ("now", "weeks"):
                errs.append(f"{r.id}: 归在「可以放下」档，horizon 却是 {w}（要尽快）")
            if b is Band.CLARIFY and w != "weeks":
                errs.append(f"{r.id}: 归在「先弄清楚」档，horizon 却是 {w}；"
                            "先弄清楚的意思就是短期内能定性，两者对不上")
        return errs

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
        errs += self.validate_horizons()
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
