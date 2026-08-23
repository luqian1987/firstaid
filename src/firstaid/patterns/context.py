"""规则求值上下文。

把一次体检的观察包装成表达式里能直接写 GGT.is_high、ALT.in_range 的样子。
缺失的指标返回 MissingProxy —— 它的任何属性都是 None，从而让表达式求值出 None，
上层据此判 INDETERMINATE，而不是判"未命中"。这个区分是整套设计的关键之一。
"""
from __future__ import annotations

from typing import Any

from ..model import ContextKey, Encounter, Observation, ObservationSet


class MissingProxy:
    """缺失指标的占位。任何属性都是 None，且布尔上下文里不是 False 而是抛出。"""

    __slots__ = ("code",)

    def __init__(self, code: str):
        self.code = code

    def __getattr__(self, item: str) -> None:
        return None

    @property
    def present(self) -> bool:
        return False

    def __bool__(self) -> bool:
        # 直接 if GGT: 这种写法会被求值层捕获成 None → INDETERMINATE
        raise TypeError(f"指标 {self.code} 缺失")

    def __repr__(self) -> str:
        return f"<missing {self.code}>"


class ObsProxy:
    __slots__ = ("_o",)

    def __init__(self, o: Observation):
        self._o = o

    @property
    def present(self) -> bool:
        return True

    def __getattr__(self, item: str) -> Any:
        return getattr(self._o, item)

    def __bool__(self) -> bool:
        return True

    @property
    def obs(self) -> Observation:
        return self._o

    def __repr__(self) -> str:
        return f"<{self._o.code}={self._o.display_value()}>"


class RuleContext:
    def __init__(self, encounter: Encounter, observations: ObservationSet | None = None):
        self.encounter = encounter
        self.observations = observations or encounter.observations
        self._cache: dict[str, Any] = {}

    def proxy(self, code: str) -> ObsProxy | MissingProxy:
        if code not in self._cache:
            o = self.observations.get(code)
            self._cache[code] = ObsProxy(o) if o else MissingProxy(code)
        return self._cache[code]

    def obs(self, code: str) -> Observation | None:
        return self.observations.get(code)

    def has(self, code: str) -> bool:
        return self.observations.get(code) is not None

    def missing(self, codes) -> list[str]:
        return [c for c in codes if not self.has(c)]

    def has_context(self, key: ContextKey) -> bool:
        return key.value in self.encounter.context

    def names(self) -> dict[str, Any]:
        return {o.code: self.proxy(o.code) for o in self.observations}
