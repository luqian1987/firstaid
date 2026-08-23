"""深读层：通路 / 机制支点 / 修饰因素 / 干预。

四层共享一条约束：**写不出引用本人数据的内容，不许出现在报告里。**
它对机制成立（Mechanism.cites 非空），对通路同样成立
（PathwayStage.judged_by 非空）——后者顺带解决了"远端病名吓人"的问题：
我们对肝硬化、胃癌这些阶段一个指标都没有，所以它们自动画不出来。
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from .common import Frozen
from .observation import Observation


# --------------------------------------------------------------------------
# 通路
# --------------------------------------------------------------------------
class StageState(str, Enum):
    CROSSED = "crossed"    # 本次已见
    CLEAR = "clear"        # 本次未见（有指标判定）
    UNKNOWN = "unknown"    # 判不了（有指标但定不了，或缺指标）


STAGE_LABELS = {
    StageState.CROSSED: "本次已见",
    StageState.CLEAR: "本次未见",
    StageState.UNKNOWN: "判不了",
}


class PathwayStage(Frozen):
    name: str
    judged_by: tuple[str, ...]        # 判定它的指标。为空即不允许出现在图上
    state: StageState = StageState.UNKNOWN
    detail: str = ""
    edge: str = ""                    # 通向这一关的边标签：说明状态转移的依据
    col: int | None = None            # 落在哪一列（现在所在/下一关/再往后）
    emphasis: bool = False            # 已确认的器质性发现，用脉动边框
    evidence: tuple[Observation, ...] = ()


class Upstream(Frozen):
    id: str
    label: str
    sub: str = ""
    modifiable: bool = True
    note: str = ""
    present: bool = False
    evidence: tuple[Observation, ...] = ()


class PathwayTrack(Frozen):
    id: str
    label: str
    upstream_id: str | None = None
    chain_id: str | None = None
    stages: tuple[PathwayStage, ...] = ()
    tail: str = ""                    # 再往后为什么不展开
    next_gate: str = ""               # 下一关由什么决定
    gate_kind: str = "recheck"        # recheck / specialist

    @property
    def position(self) -> int:
        return sum(1 for s in self.stages if s.state is StageState.CROSSED)


class Topology(Frozen):
    upstreams: tuple[Upstream, ...] = ()
    tracks: tuple[PathwayTrack, ...] = ()

    def shared(self) -> list[Upstream]:
        return [u for u in self.upstreams
                if sum(1 for t in self.tracks if t.upstream_id == u.id) > 1]

    def ok(self) -> bool:
        return bool(self.tracks)


# --------------------------------------------------------------------------
# 机制支点
# --------------------------------------------------------------------------
class Mechanism(Frozen):
    """只写改变判读方向的那一句，不写教科书。

    cites 非空是硬约束：写不出引用的机制说明它没参与判断。
    """
    pivot: str
    level: str = "机制"
    cites: tuple[str, ...] = ()
    rules_out: str = ""
    evidence: tuple[Observation, ...] = ()

    @model_validator(mode="after")
    def _must_cite(self):
        if not self.cites:
            raise ValueError(f"机制缺引用：{self.pivot[:24]}…（无引用的机制是教科书内容）")
        return self


# --------------------------------------------------------------------------
# 修饰因素：权重的可核对表达，不是黑箱系数
# --------------------------------------------------------------------------
class Modifier(Frozen):
    name: str
    note: str = ""
    why: str = ""                     # 未知项专用：它为什么会改变判断
    codes: tuple[str, ...] = ()
    evidence: tuple[Observation, ...] = ()


class Modifiers(Frozen):
    present: tuple[Modifier, ...] = ()    # 加重因素在场
    absent: tuple[Modifier, ...] = ()     # 加重因素已排除
    unknown: tuple[Modifier, ...] = ()    # 未知，会改变判断

    def any(self) -> bool:
        return bool(self.present or self.absent or self.unknown)


# --------------------------------------------------------------------------
# 干预
# --------------------------------------------------------------------------
class InterventionKind(str, Enum):
    MEASUREMENT = "measurement"   # 先测量 / 先补一项信息
    LIFESTYLE = "lifestyle"       # 本人可做
    CLINICAL = "clinical"         # 门诊讨论：只说路径与该问什么，不写用什么药


KIND_LABELS = {
    InterventionKind.MEASUREMENT: "先测量",
    InterventionKind.LIFESTYLE: "本人可做",
    InterventionKind.CLINICAL: "门诊讨论",
}


class Intervention(Frozen):
    kind: InterventionKind
    action: str
    rationale: str = ""
    target_codes: tuple[str, ...] = ()
    verify_by: str = ""              # 用什么验证。必须已在该链条的"下次比什么"里
    verify_label: str = ""
    horizon: str = ""
    caveat: str = ""
    conditional: str = ""
    paths: tuple[str, ...] = ()      # 门诊可能面对的路径
    ask_doctor: tuple[str, ...] = ()  # 值得当面问的
    note: str = ""

    @model_validator(mode="after")
    def _shape(self):
        if self.kind is InterventionKind.CLINICAL:
            if not self.paths and not self.ask_doctor:
                raise ValueError("门诊类干预必须给出可能面对的路径或该问的问题")
        elif not self.verify_by:
            raise ValueError(f"干预「{self.action[:18]}…」没有说明用什么验证")
        return self


class Depth(Frozen):
    """一条链条的深读内容。"""
    chain_id: str
    mechanisms: tuple[Mechanism, ...] = ()
    modifiers: Modifiers | None = None
    interventions: tuple[Intervention, ...] = ()

    def any(self) -> bool:
        return bool(self.mechanisms or self.interventions
                    or (self.modifiers and self.modifiers.any()))
