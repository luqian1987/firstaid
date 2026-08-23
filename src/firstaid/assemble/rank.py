"""L4 排序与分章校验。

排序不是按"异常程度"，而是按 (确定性 × 严重度 × 可行动性)：
一个不可改变但指向明确的发现，优先级高于一堆可改变但方向模糊的生活方式条目。
"""
from __future__ import annotations

from ..model import Chain, Chapter, Modifiability

_CHAPTER_ORDER = {
    Chapter.ACT_NOW: 0, Chapter.WATCH: 1, Chapter.CORRECT: 2,
    Chapter.EASY_WIN: 3, Chapter.DOWNGRADE: 4, Chapter.BASELINE: 5,
    Chapter.ARCHIVE: 6,
}


class ChapterViolation(Exception):
    pass


def check_chapters(chains: list[Chain]) -> list[str]:
    """分章不变式。违反即构建失败。

    最重要的一条：主线不可由本人改变的链条，绝不能落在「也能主动改善」章。
    参考实现正是在这里把 Lp(a) 归进了可行动章，并给它配了一整套饮食运动方案。
    """
    errs: list[str] = []
    for c in chains:
        if c.chapter is Chapter.ACT_NOW and \
                c.modifiability is Modifiability.NOT_MODIFIABLE:
            errs.append(
                f"{c.id}: 主线不可由本人改变，却归入「值得重视，也能主动改善」章。"
                f"这类分类错误会导致给遗传性指标配饮食运动方案。")
        if c.chapter is Chapter.EASY_WIN and \
                c.modifiability is not Modifiability.SELF_MODIFIABLE:
            errs.append(f"{c.id}: 「顺手改善」章要求主线可由本人改变")
    return errs


def rank(chains: list[Chain]) -> list[Chain]:
    return sorted(chains, key=lambda c: (_CHAPTER_ORDER.get(c.chapter, 9), -c.priority))


def group_by_chapter(chains: list[Chain]) -> dict[Chapter, list[Chain]]:
    out: dict[Chapter, list[Chain]] = {}
    for c in rank(chains):
        out.setdefault(c.chapter, []).append(c)
    return out
