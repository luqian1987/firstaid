"""本次体检没有回答的东西。

体检报告天生只回答"查过的东西正不正常"。它不会说：你以为查了其实没查、
这个结果引出了一个方向而那个方向没覆盖、你花钱做的项目结果没给你。
人做体检买的是安心，而那份安心的边界在哪，报告从不交代——这一层就是交代它。

与"套餐里没买这一项"的分界是硬的：**本次必须真有一个发现在指向它**。
拿规则库比病人的套餐大来列一串"你没查维生素B6"，那是制造焦虑，不是判读。
"""
from __future__ import annotations

from .common import Frozen
from .observation import Observation

EFFORTS = ("recall", "fetch", "home", "test")
EFFORT_LABELS = {
    "recall": "回想一下",
    "fetch": "找出来 / 取回来",
    "home": "在家能做",
    "test": "加一项检查",
}


class Gap(Frozen):
    what: str                        # 缺的是什么
    because: str                     # 本次哪个结果指向了它
    horizon: str = "weeks"
    effort: str = "test"
    origin: str = "rule"             # rule / unsettled / pending / context
    from_chain: str | None = None    # 哪条判读打开了这个口子
    evidence: tuple[Observation, ...] = ()

    @property
    def free(self) -> bool:
        """不用再做检查就能回答的。客户版把这些单独归一组——它们最该先做。"""
        return self.effort in ("recall", "fetch", "home")
