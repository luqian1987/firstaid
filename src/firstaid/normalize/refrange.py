"""参考区间解析与状态判定。

数据源泛化，各家医院区间写法不一。解析不出来就返回 None，
让这条观察落到 UNKNOWN —— 绝不猜成"正常"。
"""
from __future__ import annotations

import re

from ..model import Observation, RangeKind, RangeStatus, RefRange

_NUM = r"[-+]?\d+(?:\.\d+)?"
# 顺序有意义："10--60" 必须先按双连字符匹配，否则 -60 会被吃成负数
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"^\[?({_NUM})\s*--\s*(\d+(?:\.\d+)?)\]?$"), "both"),
    (re.compile(rf"^\[?({_NUM})\s*[-–—~至]\s*({_NUM})\]?$"), "both"),
    (re.compile(rf"^[<＜]\s*=?\s*({_NUM})$"), "upper"),
    (re.compile(rf"^≤\s*({_NUM})$"), "upper"),
    (re.compile(rf"^[>＞]\s*=?\s*({_NUM})$"), "lower"),
    (re.compile(rf"^≥\s*({_NUM})$"), "lower"),
    (re.compile(rf"^({_NUM})\s*以下$"), "upper"),
    (re.compile(rf"^({_NUM})\s*以上$"), "lower"),
]


def parse_range(raw: str | None, kind: RangeKind = RangeKind.UNSPECIFIED,
                source_note: str | None = None) -> RefRange | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(" ", "")
    if not s or s in {"-", "—", "/", "无", "未提供"}:
        return None
    for pat, mode in _PATTERNS:
        m = pat.match(s)
        if not m:
            continue
        if mode == "both":
            lo, hi = float(m.group(1)), float(m.group(2))
            return RefRange(low=lo, high=hi, kind=kind, raw=raw, source_note=source_note)
        if mode == "upper":
            return RefRange(high=float(m.group(1)), kind=kind, raw=raw,
                            source_note=source_note)
        return RefRange(low=float(m.group(1)), kind=kind, raw=raw,
                        source_note=source_note)
    return None


def parse_value(raw) -> tuple[float | None, str | None]:
    """返回 (数值, 删失符号)。"<0.20" → (0.20, "<")。

    删失本身是信息："血清叶酸低到测不出，属于重度缺乏的量级" 这句话
    正是建立在删失符号上的，所以不能在归一时丢掉。
    """
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    s = str(raw).strip()
    m = re.match(rf"^([<>＜＞≤≥]?)\s*({_NUM})$", s)
    if not m:
        return None, None
    sym = m.group(1)
    censor = {"<": "<", "＜": "<", "≤": "<", ">": ">", "＞": ">", "≥": ">"}.get(sym)
    return float(m.group(2)), censor


def judge(value: float | None, censor: str | None, ref: RefRange | None) -> RangeStatus:
    if ref is None or (ref.low is None and ref.high is None):
        return RangeStatus.NO_RANGE
    if value is None:
        return RangeStatus.UNKNOWN
    # 删失值：<0.20 在下限 0.40 之下，判 LOW；>x 同理
    if censor == "<":
        if ref.low is not None and value <= ref.low:
            return RangeStatus.LOW
        if ref.high is not None and value <= ref.high and ref.low is None:
            return RangeStatus.IN_RANGE
    if censor == ">":
        if ref.high is not None and value >= ref.high:
            return RangeStatus.HIGH
    if ref.low is not None and value < ref.low:
        return RangeStatus.LOW
    if ref.high is not None and value > ref.high:
        return RangeStatus.HIGH
    return RangeStatus.IN_RANGE


def restate(obs: Observation) -> Observation:
    """重算状态。归一或单位换算之后必须调用。"""
    return obs.model_copy(update={"status": judge(obs.value, obs.censor, obs.ref)})
