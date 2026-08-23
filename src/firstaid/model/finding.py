"""L3/L4：模式命中 → 判读链条。

判读链条的四段骨架是产品本体，不是排版：
    进入判断的数值 → 只看单项 ⟷ 放在一起看 → 可以确定/不能由此认定/下一步/下次比什么
四段缺一不可，缺哪段就是规则没写完，构建时报错。
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from .common import ContextKey, Frozen, TriState
from .comparison import ComparisonItem
from .observation import Observation


class Archetype(str, Enum):
    """九类可复用的推理模式。与具体指标解耦——换一组指标，逻辑不变。"""
    UPSTREAM_CONTRADICTED = "upstream_contradicted"      # 上游异常 / 下游全阴
    CORRECTED_VS_RAW = "corrected_vs_raw"                # 校正值正常解释未校正值异常
    PAIRED_DIVERGENCE = "paired_divergence"              # 配对同向背离 → 系统性偏差
    PATTERN_DISSOCIATION = "pattern_dissociation"        # 形态脱节
    LAYERED_EXCLUSION = "layered_exclusion"              # 多层排除
    ISOLATED_ABNORMAL = "isolated_abnormal"              # 孤立异常缺乏佐证
    ACUTE_PHASE_COHERENCE = "acute_phase_coherence"      # 急性期蛋白一致性
    NORMAL_PANEL_HIDDEN_RISK = "normal_panel_hidden_risk"  # 常规全正常但组合提示风险
    UNRANGED_STRUCTURAL = "unranged_structural"          # 无区间结构性发现 → 转比较口径
    RANGE_KIND_CAVEAT = "range_kind_caveat"              # 区间口径不当：拿实验室自有百分位当疾病界值
    BORDERLINE_CONCORDANT = "borderline_concordant"      # 多个相关指标同处区间同一端 → 建趋势基线


class Modifiability(str, Enum):
    """这一条能不能靠本人行为改变。

    Lp(a) 由基因决定、终生基本不变 —— 把它归进"可主动改善"章并配一套饮食方案，
    是分类错误而不是文案问题。所以这个字段是本体层的强制属性，
    组装层据此拒绝把 NOT_MODIFIABLE 的主线放进可行动章节。
    """
    SELF_MODIFIABLE = "self_modifiable"     # 饮食/运动/体重/戒断可改变
    CLINICAL = "clinical"                   # 需临床处置才可能改变
    NOT_MODIFIABLE = "not_modifiable"       # 遗传决定或结构既成
    UNKNOWN = "unknown"


class Chapter(str, Enum):
    """管理逻辑分章。分类法沿用参考实现，但分类依据换成模式层的输出。

    DOWNGRADE 与 BASELINE 单列，不并进 ARCHIVE：
    "原报告让你随诊、按组合判读可以降级" 和 "这条不重要" 是两件事，
    前者必须把降级的理由完整写出来，后者才是留档。
    """
    ACT_NOW = "act_now"                 # 值得重视，也能主动改善
    WATCH = "watch"                     # 值得重视，以观察验证为主
    EASY_WIN = "easy_win"               # 危害不高，但值得顺手改善
    CORRECT = "correct"                 # 需纠正：原报告建议按组合判读不成立
    DOWNGRADE = "downgrade"             # 可降级 / 可放心：原报告高估了
    BASELINE = "baseline"               # 建基线：无区间的结构性发现转比较口径
    ARCHIVE = "archive"                 # 暂不占主要精力，完整留档


class Tag(str, Enum):
    NEEDS_SPECIALIST = "needs_specialist"   # 需专科确认
    RETEST_FIRST = "retest_first"           # 先复测再解读
    SELF_ACTION = "self_action"             # 本人可改变
    CORRECTION = "correction"               # 需纠正
    DOWNGRADE = "downgrade"                 # 可降级
    REASSURE = "reassure"                   # 可放心
    BASELINE = "baseline"                   # 建基线


TAG_LABELS: dict[Tag, str] = {
    Tag.NEEDS_SPECIALIST: "需专科确认",
    Tag.RETEST_FIRST: "先复测再解读",
    Tag.SELF_ACTION: "本人可改变",
    Tag.CORRECTION: "需纠正",
    Tag.DOWNGRADE: "可降级",
    Tag.REASSURE: "可放心",
    Tag.BASELINE: "建基线",
}


class EvidenceRef(Frozen):
    """进入判断的一个数值。role 说明它在这条推理里担任什么角色。"""
    observation: Observation
    role: str                      # "upstream" / "downstream" / "confounder" / "anchor"
    note: str | None = None        # "达上限1.53倍" / "每个颗粒携带一个ApoB"


class NarrationBrief(Frozen):
    """交给叙述器的约束包。

    分工原则的落点：规则决定"有没有这个发现"和"能引用哪些数"，
    叙述器只决定"怎么说"。must_convey 是必须说到的事实，
    must_not_claim 是禁止越界的断言，allowed_values 是唯一允许出现的数字。
    """
    must_convey: tuple[str, ...] = ()
    must_not_claim: tuple[str, ...] = ()
    allowed_values: tuple[float, ...] = ()
    # 来自原报告的引文（参考区间写法、区间口径说明、影像描述原文）。
    # 其中的数字是"引用"不是"断言"，允许出现在叙述里。
    quoted_text: tuple[str, ...] = ()
    tone: str = "neutral"


class Verdict(Frozen):
    certain: str                                    # 可以确定
    not_certain: str                                # 不能由此认定
    next_steps: tuple[str, ...] = ()                # 下一步
    compare_next: tuple[ComparisonItem, ...] = ()   # 下次比什么

    @model_validator(mode="after")
    def _complete(self):
        if not self.certain.strip():
            raise ValueError("verdict.certain 不能为空")
        if not self.not_certain.strip():
            raise ValueError("verdict.not_certain 不能为空：不写边界的判读不许发布")
        return self


class PatternHit(Frozen):
    rule_id: str
    archetype: Archetype
    state: TriState
    evidence: tuple[EvidenceRef, ...] = ()
    consumed_codes: tuple[str, ...] = ()      # 本规则负责给出归宿的观察
    missing_codes: tuple[str, ...] = ()       # 因缺这些而 INDETERMINATE
    needs_context: tuple[ContextKey, ...] = ()
    detail: dict[str, float | str | None] = Field(default_factory=dict)

    @property
    def fired(self) -> bool:
        return self.state is TriState.TRIGGERED


class Chain(Frozen):
    """一条判读链条。"""
    id: str
    title: str
    lede: str
    tag: Tag
    chapter: Chapter
    modifiability: Modifiability
    priority: float = 0.0

    inputs: tuple[EvidenceRef, ...] = ()
    single_read: str = ""       # 只看单项会得到
    joint_read: str = ""        # 放在一起看得到
    verdict: Verdict | None = None
    hits: tuple[PatternHit, ...] = ()
    brief: NarrationBrief | None = None

    @model_validator(mode="after")
    def _skeleton(self):
        if not self.inputs:
            raise ValueError(f"{self.id}: 判读链条必须列出进入判断的数值")
        return self

    def is_complete(self) -> bool:
        return bool(self.single_read and self.joint_read and self.verdict)


class Correction(Frozen):
    """需纠正：原报告的一条建议，按组合判读不成立。

    责任约束写进类型里：contradicting 不能为空——每条纠正必须能引用到
    同一份报告内的反证；action 不允许是"不用管"，必须落到复测或面诊。
    """
    id: str
    claim: str                      # 本系统的说法："不建议按此补充维生素B6"
    original_advice: str            # 原报告原话
    original_source: str            # 原报告出处
    flagged: EvidenceRef            # 被原报告打箭头的那一项
    contradicting: tuple[EvidenceRef, ...]   # 同一份报告里的反证
    why_not: str                    # 为什么不成立
    what_to_do: str                 # 怎么做
    hits: tuple[PatternHit, ...] = ()

    @model_validator(mode="after")
    def _must_cite(self):
        if not self.contradicting:
            raise ValueError(
                f"{self.id}: 纠正原报告必须引用同一份报告内的反证，否则不允许生成"
            )
        return self


class MissingContextItem(Frozen):
    key: ContextKey
    label: str
    affects: tuple[str, ...] = ()          # 受影响的 chain id
    affect_titles: tuple[str, ...] = ()    # 对应的判读标题，给人看的
    why: str = ""


class BoundaryItem(Frozen):
    """边界：这份判读会在哪里失效。"""
    what: str                        # 尚未纳入的东西
    affects: tuple[str, ...] = ()
    impact: str = ""
    critical: bool = False
