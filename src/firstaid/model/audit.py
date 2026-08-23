"""L5 审计层：覆盖率保证。

两份参考实现都没做全的一层。
「已经确认没有问题的部分」那一节写着："这一段存在的意义只有一个：
确认它们被看过了，而不是被略过了。" —— 这句话说的就是覆盖率，
现在靠人保证，这里让它机械可证。

不变式：每一条观察必须恰好有一个归宿。任何 abnormal 观察落到 UNRESOLVED，
构建失败，不允许出报告。
"""
from __future__ import annotations

from collections import Counter
from enum import Enum

from pydantic import Field

from .common import Frozen, Mutable
from .observation import Observation


class Disposition(str, Enum):
    CHAINED = "chained"            # 进入了某条判读链条
    CORRECTED = "corrected"        # 进入了「需纠正」
    DOWNGRADED = "downgraded"      # 被显式降级（可降级/可放心）
    BASELINE = "baseline"          # 结构性发现，转为比较口径建基线
    CONFIRMED_OK = "confirmed_ok"  # 已确认良好，折叠展示
    ARCHIVED = "archived"          # 完整留档，不进正文
    INDETERMINATE = "indeterminate"  # 规则想用它但输入不全，已登记到边界
    UNRESOLVED = "unresolved"      # 没有任何规则认领 —— 异常项落这里即构建失败


DISPOSITION_LABELS: dict[Disposition, str] = {
    Disposition.CHAINED: "进入判读链条",
    Disposition.CORRECTED: "进入需纠正",
    Disposition.DOWNGRADED: "已降级",
    Disposition.BASELINE: "建立比较基线",
    Disposition.CONFIRMED_OK: "已确认良好",
    Disposition.ARCHIVED: "完整留档",
    Disposition.INDETERMINATE: "输入不全，登记为边界",
    Disposition.UNRESOLVED: "未认领",
}


class DispositionRecord(Frozen):
    code: str
    raw_name: str
    disposition: Disposition
    by: str | None = None            # 哪条规则/哪个章节认领的
    abnormal: bool = False
    note: str | None = None


class ConsistencyIssue(Frozen):
    """原报告给出的派生值 与 用原始值重算的结果 对不上。

    例：原报告 BMI 26.9，而身高 164 / 体重 71.2 反算是 26.5。
    不影响结论，但正是这一层该抓的东西。
    """
    code: str
    reported: float
    recomputed: float
    formula: str
    rel_diff: float
    severity: str = "info"           # info / warn / error


class CoverageReport(Mutable):
    records: list[DispositionRecord] = Field(default_factory=list)
    consistency: list[ConsistencyIssue] = Field(default_factory=list)
    unreadable_pages: list[str] = Field(default_factory=list)
    unjudged_codes: list[str] = Field(default_factory=list)   # 有值但无法判定高低

    def add(self, rec: DispositionRecord) -> None:
        self.records.append(rec)

    def histogram(self) -> dict[str, int]:
        return dict(Counter(r.disposition.value for r in self.records))

    def unresolved_abnormal(self) -> list[DispositionRecord]:
        return [r for r in self.records
                if r.abnormal and r.disposition is Disposition.UNRESOLVED]

    def duplicated(self) -> list[str]:
        c = Counter(r.code for r in self.records)
        return [k for k, v in c.items() if v > 1]

    def ok(self) -> bool:
        return not self.unresolved_abnormal() and not self.duplicated()

    def failures(self) -> list[str]:
        out: list[str] = []
        for r in self.unresolved_abnormal():
            out.append(f"异常项 {r.code}（{r.raw_name}）没有任何归宿")
        for code in self.duplicated():
            out.append(f"观察 {code} 被重复认领")
        return out

    @classmethod
    def start(cls, observations: list[Observation]) -> "CoverageReport":
        """先把所有观察登记为 UNRESOLVED，之后各层逐步认领。"""
        rep = cls()
        for o in observations:
            rep.add(DispositionRecord(
                code=o.code, raw_name=o.raw_name,
                disposition=Disposition.UNRESOLVED, abnormal=o.abnormal,
            ))
        return rep

    def claim(self, code: str, disposition: Disposition, by: str,
              note: str | None = None) -> bool:
        for i, r in enumerate(self.records):
            if r.code == code and r.disposition is Disposition.UNRESOLVED:
                self.records[i] = r.model_copy(
                    update={"disposition": disposition, "by": by, "note": note})
                return True
        return False
