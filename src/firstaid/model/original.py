"""原报告的结论与建议，以及与本次判读的对账。

此前系统只读检验值，不读报告怎么说。结果是它只能自说自话：
客户手里那份"医院说我有 19 条问题"的清单，一条也没被正面回答。

有了这一层，覆盖率断言就从"每条观察都有归宿"扩展到
"原报告每条结论都有回答"——这才是客户真正关心的那个保证。
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from .common import Frozen, Provenance
from .finding import Tag


class Band(str, Enum):
    """对外只暴露三档。内部的 Chapter × Tag 分级不变，只是不再往外抛。

    七个章节乘七个标签摆在客户面前，读者要先学一套分类法才能读报告。
    三档的判据是"接下来做什么"，而不是"这属于哪一类"。
    """
    ACT = "act"          # 现在要做
    CLARIFY = "clarify"  # 先弄清楚
    SETTLE = "settle"    # 可以放下


BAND_META: dict[Band, tuple[str, str]] = {
    Band.ACT:     ("现在要做", "已经确定，而且有明确的入口"),
    Band.CLARIFY: ("先弄清楚", "事实还不牢，先复测或先补一项背景"),
    Band.SETTLE:  ("可以放下", "查过了，本次不需要占用精力"),
}

BAND_COLOR: dict[Band, tuple[str, str]] = {
    Band.ACT:     ("#A8452A", "#F7EDE9"),
    Band.CLARIFY: ("#3A5F8A", "#EAF0F7"),
    Band.SETTLE:  ("#1F5E56", "#E7F0EE"),
}

# 标签 → 色带。确定性映射，有测试锁死。
TAG_BAND: dict[Tag, Band] = {
    Tag.NEEDS_SPECIALIST: Band.ACT,
    Tag.SELF_ACTION:      Band.ACT,
    Tag.RETEST_FIRST:     Band.CLARIFY,
    Tag.DOWNGRADE:        Band.SETTLE,
    Tag.REASSURE:         Band.SETTLE,
    Tag.BASELINE:         Band.SETTLE,
    Tag.CORRECTION:       Band.SETTLE,
}

BAND_ORDER = {Band.ACT: 0, Band.CLARIFY: 1, Band.SETTLE: 2}


def band_of(tag: Tag, override: Band | None = None) -> Band:
    return override or TAG_BAND[tag]


class OriginalFinding(Frozen):
    """原报告的一条结论 + 它给的建议。

    这是提取层要抽的第二类东西（第一类是检验值）。它是半结构化文本：
        【检查项目】结论 → (1) 建议……
    """
    seq: int
    group: str                      # 就医 / 进一步检查 / 定期复检 / 其他
    source: str                     # 【】里的检查项目
    said: str                       # 结论原话
    advised: str = ""               # 建议原话
    codes: tuple[str, ...] = ()     # 这条结论涉及哪些指标（用于对账匹配）
    pending: bool = False           # 原报告标注"详见附件/报告自取"，本次未拿到
    provenance: Provenance | None = None

    def label(self) -> str:
        return f"{self.seq} · {self.source}"


class ReconciliationRow(Frozen):
    """一条对账记录：本次判读的某个结论，回答了原报告的哪几条。

    多条原报告条目映射到同一个结论时合并成一行——它们本来就是同一件事。
    原报告把"体重指数高"和"脂肪肝+GGT高"分成两条给建议，
    但在判读里它们是一件事，分开讲只会让人多读一遍。
    """
    band: Band
    headline: str                              # 一句话结论
    findings: tuple[OriginalFinding, ...] = () # 回答了原报告的哪几条
    chain_id: str | None = None
    correction_id: str | None = None
    needs_confirm: bool = False                # ◇ 与医生确认
    is_new: bool = False                       # 原报告没提，本次新增

    @property
    def anchor(self) -> str:
        return self.chain_id or self.correction_id or ""


class Reconciliation(Frozen):
    rows: tuple[ReconciliationRow, ...] = ()
    unaddressed: tuple[OriginalFinding, ...] = ()   # 无人回答 → 构建失败
    pending: tuple[OriginalFinding, ...] = ()       # 报告未拿到 → 进边界

    def by_band(self) -> dict[Band, list[ReconciliationRow]]:
        out: dict[Band, list[ReconciliationRow]] = {b: [] for b in Band}
        for r in sorted(self.rows, key=lambda r: BAND_ORDER[r.band]):
            out[r.band].append(r)
        return out

    def counts(self) -> dict[Band, int]:
        return {b: len(v) for b, v in self.by_band().items()}

    def ok(self) -> bool:
        return not self.unaddressed
