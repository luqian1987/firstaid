"""命令行：跑一次分析并把每层的产出打出来，用于开发期核对。"""
from __future__ import annotations

import argparse
from pathlib import Path

from .model import DISPOSITION_LABELS, TAG_LABELS, Disposition, TriState
from .pipeline import analyze_fixture, chapters

CHAPTER_TITLES = {
    "act_now": "01 值得重视，也能主动改善",
    "watch": "02 值得重视，以观察验证为主",
    "correct": "03 需纠正：原报告建议按组合判读不成立",
    "easy_win": "04 危害不高，但值得顺手改善",
    "downgrade": "05 可降级 / 可放心",
    "baseline": "06 建基线",
    "archive": "07 完整留档",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="firstaid")
    ap.add_argument("fixture", type=Path, help="夹具 YAML 路径")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    a = analyze_fixture(args.fixture)
    w = print

    w("=" * 74)
    w(f"体检二次判读 · {a.timeline.subject.id} · {a.encounter.label()}")
    w("=" * 74)

    w(f"\n【观察】共 {len(a.encounter.observations)} 条"
      f"（异常 {len(a.encounter.observations.abnormal())}，"
      f"无参考区间 {len(a.encounter.observations.unranged())}）")

    derived = [o for o in a.encounter.observations if o.kind.value == "derived"]
    w(f"\n【L2 派生指标】{len(derived)} 项（原报告未计算）")
    for o in derived:
        if o.code == "AGE":
            continue
        w(f"  {o.raw_name:24s} {o.display_value():>10s} {o.unit or '':8s}"
          f" ← {o.formula}")
    if a.consistency:
        w("\n  一致性校验：")
        for i in a.consistency:
            w(f"    ! {i.code} 原报告 {i.reported} vs 重算 {i.recomputed}"
              f"（相差 {i.rel_diff:.1%}，{i.severity}）")

    hits = a.engine.hits if a.engine else []
    fired = [h for h in hits if h.state is TriState.TRIGGERED]
    indet = [h for h in hits if h.state is TriState.INDETERMINATE]
    w(f"\n【L3 模式】评估 {len(hits)} 条规则 → 命中 {len(fired)}，"
      f"不可评估 {len(indet)}，未命中 {len(hits)-len(fired)-len(indet)}")

    w(f"\n【L4 判读链条】{len(a.chains)} 条 + 需纠正 {len(a.corrections)} 条")
    for ch, group in chapters(a).items():
        w(f"\n  ── {CHAPTER_TITLES.get(ch.value, ch.value)} ──")
        for c in group:
            w(f"  [{TAG_LABELS[c.tag]}] {c.title}   (优先级 {c.priority:g})")
            w(f"      进入判断的数值 {len(c.inputs)} 项 | 模式 {c.hits[0].archetype.value}")
            if args.verbose and c.verdict:
                w(f"      只看单项 → {c.single_read.strip()[:70]}…")
                w(f"      放在一起 → {c.joint_read.strip()[:70]}…")
                w(f"      可以确定 → {c.verdict.certain.strip()[:70]}…")
                w(f"      下次比什么 → {len(c.verdict.compare_next)} 项")

    if a.corrections:
        w(f"\n  ── {CHAPTER_TITLES['correct']} ──")
        for c in a.corrections:
            w(f"  · {c.claim}")
            w(f"      原报告：{c.original_advice[:56]}")
            w(f"      反证 {len(c.contradicting)} 项，均引自同一份报告")

    if a.plan:
        w(f"\n【纵向】下次比什么：{len(a.plan.items)} 项可比口径")
        for i in a.plan.items:
            dev = "（设备敏感）" if i.key.device_sensitive else ""
            w(f"  · {i.key.code:16s} {i.baseline_display:>14s}{dev}  {i.what[:44]}")

    if a.missing_context:
        w("\n【背景空白】本判读没有替你假设：")
        for m in a.missing_context:
            w(f"  · {m.label}  → 影响 {len(m.affects)} 条判读")

    if a.boundaries:
        w(f"\n【边界】{len(a.boundaries)} 项")
        for b in a.boundaries:
            mark = " ★最关键" if b.critical else ""
            w(f"  · {b.what}{mark}")
            if b.impact:
                w(f"      {b.impact}")

    cov = a.coverage
    if cov:
        w("\n【L5 覆盖率审计】")
        for k, v in sorted(cov.histogram().items(), key=lambda x: -x[1]):
            label = DISPOSITION_LABELS.get(Disposition(k), k)
            w(f"  {label:16s} {v:3d}")
        if cov.unreadable_pages:
            w(f"  纯图像页（不解读）: {len(cov.unreadable_pages)} 页")
        if cov.unjudged_codes:
            w(f"  暂未判定高低: {', '.join(cov.unjudged_codes)}")

    w("\n" + "=" * 74)
    if a.ok():
        w("构建通过：每一条观察都有归宿，分章不变式成立。")
        return 0
    w("构建失败：")
    for e in a.blocking():
        w(f"  ✗ {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
