#!/usr/bin/env python3
"""
总包构建 —— 把 sheets/ 里的原生 HTML 与外部 PDF 单页合成一册，前面加目录。

为什么需要它：15 份更早做的稿子只有 PDF、没有 HTML 源码。build.py 只认 HTML，
出不了这 15 份。本脚本按 pack.toml 描述的成册顺序，把两种来源拼在一起。

用法:
    python pack.py              # 出总册：out/总包_全册.pdf + out/总包_全册.html
    python pack.py --split      # 另按板块出 11 本分册到 out/分册/

来源在 pack.toml 里声明，两种：
    kind = "sheet"  → sheets/ 下的 HTML 片段，本脚本渲染
    kind = "pdf"    → 外部 PDF 的第 n、n+1 页，直接取用

HTML 版只含 kind="sheet" 的部分——PDF 页无法还原成 HTML。
拿到那 12 份的 HTML 源码后放进 sheets/、把条目改成 kind="sheet"，HTML 版即完整。
"""
import re
import sys
import asyncio
import tomllib
import subprocess
from pathlib import Path

import build                      # 复用 wrap() / render() / page_count()

ROOT = Path(__file__).parent
OUT = ROOT / "out"
CFG = ROOT / "pack.toml"


def load():
    with CFG.open("rb") as f:
        items = tomllib.load(f)["item"]
    # 页数不写在 pack.toml 里，读稿子 .mast 上印的「共 N 页」——
    # 那个数本来就要印对，让它当唯一事实来源，表和稿就不会打架。
    for it in items:
        it["n"] = build.declared_pages((ROOT / "sheets" / it["file"]).read_text(encoding="utf-8"))
    return items


# ── 目录页 ───────────────────────────────────────────────────────────────
TOC_CSS = """
.toc{ width:210mm; margin:10mm auto; background:#fff; padding:14mm 13mm 12mm;
      box-shadow:0 2px 16px rgba(20,40,70,.14); }
@media print{ .toc{ width:auto; margin:0; padding:0; box-shadow:none; } }
.toc h1{ margin:0; font-size:26pt; color:var(--deep); font-weight:700; letter-spacing:.02em; }
.toc .sub{ margin-top:2mm; font-size:10.5pt; color:#5B6B78; }
.toc .rule{ border-bottom:2px solid var(--deep); margin:2.6mm 0 3.4mm; }
.toc table{ width:100%; border-collapse:collapse; table-layout:fixed; }
.toc td{ padding:1mm 0; font-size:10.2pt; border-bottom:1px solid #EDF1F4; vertical-align:baseline; }
.toc tr.grp td{ padding:2.4mm 0 .9mm; border-bottom:1px solid #DDE3E9; }
.toc tr.grp b{ font-size:10.4pt; color:var(--teal); letter-spacing:.1em; font-weight:700; }
.toc tr.grp span{ color:#9AA6B0; font-size:8.8pt; margin-left:2.5mm; font-weight:400; }
.toc td.nn{ color:#A9BAC8; font-family:"Times New Roman",serif; font-size:9.6pt; }
.toc td.nm{ color:#262626; }
.toc td.nm b{ color:var(--deep); }
.toc td.pr{ text-align:right; color:#5B6B78;
            font-family:"Times New Roman",Georgia,serif; font-size:10pt; }
.toc td.pg{ text-align:right; color:#8A98A3;
            font-family:"Times New Roman",Georgia,serif; font-size:9.6pt; }
.toc .foot{ margin-top:3.6mm; padding-top:2.6mm; border-top:1px solid #DDE3E9;
            font-size:9.2pt; color:#8A98A3; line-height:1.75; }
.toc .foot b{ color:#3C4A57; }
"""


# 列宽写在 colgroup 里，不写在 td 上：table-layout:fixed 只看第一行，
# 而第一行是 colspan=4 的板块头，td 上的 width 会被整个忽略掉。
# 10+128+26+20 = 184mm，正好是 A4 减掉左右 13mm 页边距。
COLS = ('<colgroup><col style="width:10mm"><col style="width:128mm">'
        '<col style="width:26mm"><col style="width:20mm"></colgroup>')


def toc_html(items, start_page):
    """目录页。start_page 是第一份稿子在总册里的页码。"""
    rows, cur, pg = [], None, start_page
    for it in items:
        if it["sec"] != cur:
            cur = it["sec"]
            n = sum(1 for x in items if x["sec"] == cur)
            lab = "" if cur == "附录" else f"<span>{n} 份</span>"   # 附录不计份数
            rows.append(f'<tr class="grp"><td colspan="4"><b>{cur}</b>{lab}</td></tr>')
        extra = f'<span style="color:#9AA6B0"> · {it["n"]} 页</span>' if it["n"] != 2 else ""
        nm = f'<b>{it["code"]}</b>　{it["name"]}' if it["code"] else it["name"]
        pr = f'¥{it["price"]}' if it["price"] else ""
        rows.append(
            f'<tr><td class="nn">{it["nn"]}</td>'
            f'<td class="nm">{nm}{extra}</td>'
            f'<td class="pr">{pr}</td>'
            f'<td class="pg">{pg}</td></tr>')
        pg += it["n"]
    n_item = sum(1 for i in items if i["kind"] != "appendix")
    return (
        f'<style>{TOC_CSS}</style>\n<div class="toc">'
        f'<h1>功能医学检测项目速览</h1>'
        f'<div class="sub">共 {n_item} 份 · {sum(i["n"] for i in items)} 页 A4 · 版本 2026-08</div>'
        f'<div class="rule"></div>'
        f'<table>{COLS}{"".join(rows)}</table>'
        f'<div class="foot">'
        f'名称与收费以《心理睡眠体检检测项目协议》附件 1 为准。'
        f'本册为检测项目说明，不构成医疗建议；检测结果需由医师结合临床综合判断。<br>'
        f'除分子筛查 02 权益卡为 <b>4 页</b>外，其余各份均为 2 页；'
        f'末页<b>附录</b>为全册统一的版本与免责说明。'
        f'</div></div>')


# ── 组装 ────────────────────────────────────────────────────────────────
def render_sheets(sheets, tmp) -> Path:
    """原生稿**一次**渲成一个 PDF。

    逐份渲的话，Chromium 会把中文字体子集完整嵌进每一个 PDF，一份约 600KB，
    32 份就是 20MB 白搭进去，而且去不掉——每份的子集内容不同，不是重复对象。
    一次渲完只嵌一份：64 页才 7.3MB。
    """
    body = [(ROOT / "sheets" / i["file"]).read_text(encoding="utf-8") for i in sheets]
    h = tmp / "_原生稿全部.html"
    h.write_text(build.wrap("\n".join(body)), encoding="utf-8")
    dst = tmp / "_原生稿全部.pdf"
    asyncio.run(build.render(h, dst))
    n = build.page_count(dst)
    want = sum(i["n"] for i in sheets)
    assert n == want, f"原生稿合渲得 {n} 页，应为 {want} 页"
    return dst


def assemble(items, toc_pdf: Path, sheets_pdf: Path, dst: Path) -> int:
    """先整文件拼一次，再在同一个文件里重排页序。

    **不要按页拆了再拼。** pdfseparate 会把整套中文字体拷进每一个单页，
    64 页拆完再合是 44MB，事后 mutool clean -ggggz 也只压到 37MB，还要跑 4 分钟。
    整文件 pdfunite 只有 15.7MB（字体各源各一份），再用 mutool merge 在这一个
    文件内部重排页序，结果 14.6MB、耗时不到 1 秒——页序对了，体积也对了。
    30MB 是发送上限，这不是可选优化。
    """
    srcs = []          # 早先有过 kind="pdf" 的外部成稿，现已全部还原成 HTML；保留这条路
    for it in items:
        if it.get("kind") == "pdf" and it["file"] not in srcs:
            srcs.append(it["file"])
    whole = [toc_pdf, sheets_pdf] + [ROOT / f for f in srcs]
    tmp_all = dst.parent / "_全部未排序.pdf"
    subprocess.run(["pdfunite", *map(str, whole), str(tmp_all)],
                   check=True, capture_output=True)

    base, off = {}, 1
    for key, f in zip(["__toc__", "__sheets__"] + srcs, whole):
        base[key] = off
        off += build.page_count(f)

    order = list(range(1, build.page_count(toc_pdf) + 1))
    cur = base["__sheets__"]
    for it in items:
        order += list(range(cur, cur + it["n"]))
        cur += it["n"]
    assert cur == base["__sheets__"] + build.page_count(sheets_pdf), "原生稿有页没用掉"

    subprocess.run(["mutool", "merge", "-o", str(dst), str(tmp_all),
                    ",".join(map(str, order))], check=True, capture_output=True)
    tmp_all.unlink(missing_ok=True)
    return len(order)


def verify(pdf: Path, items, n_toc: int):
    """逐份核对页眉上印的板块编号，确认重排没错位。
    合渲之后单份页数不再单独可见，这是替代的分页校验。"""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         check=True, capture_output=True, text=True).stdout.split("\f")
    bad, k = [], n_toc
    for it in items:
        page = re.sub(r"\s", "", txt[k])
        if re.sub(r"\s", "", it["code"] or it["name"]) not in page:
            bad.append((it["nn"], it["code"], it["name"]))
        k += it["n"]
    if bad:
        sys.exit(f"页序错位，这些份的第 1 页找不到自己的编号：{bad}")
    print(f"  页序核对  {len(items)} 份全部对上")


def main():
    items = load()
    OUT.mkdir(exist_ok=True)
    tmp = OUT / "_parts"
    tmp.mkdir(exist_ok=True)

    # 目录先按 1 页估算；渲染后若真是 2 页，用真实页数重排一次
    for guess in (1, 2):
        toc = tmp / "00_目录.html"
        toc.write_text(build.wrap(toc_html(items, guess + 1)), encoding="utf-8")
        toc_pdf = tmp / "00_目录.pdf"
        asyncio.run(build.render(toc, toc_pdf))
        if build.page_count(toc_pdf) == guess:
            break
    print(f"目录 {build.page_count(toc_pdf)} 页")

    sheets_pdf = render_sheets(items, tmp)   # 项目与附录都是原生 HTML，一起渲
    print(f"  原生稿 {len(items)} 份合渲 {build.page_count(sheets_pdf)} 页"
          f"　{sheets_pdf.stat().st_size / 1024 / 1024:.1f} MB")

    pdf = OUT / "总包_全册.pdf"
    n_toc = build.page_count(toc_pdf)
    total = assemble(items, toc_pdf, sheets_pdf, pdf)
    expect = n_toc + sum(i["n"] for i in items)
    assert total == build.page_count(pdf) == expect, f"合并后 {total} 页，应为 {expect} 页"
    verify(pdf, items, n_toc)

    # HTML 版：目录 + 有源码的那些
    body = [toc_html([i for i in items], build.page_count(toc_pdf) + 1)]
    body += [(ROOT / "sheets" / i["file"]).read_text(encoding="utf-8")
             for i in items]          # 含附录
    html = OUT / "总包_全册.html"
    html.write_text(build.wrap("\n".join(body)), encoding="utf-8")

    # build.py 出的单份 PDF 不会被 pack.py 覆盖，改完稿子只跑 pack.py 的话
    # 它们就成了过期文件，容易被当成新的发出去——这里直接清掉。
    for f in list(OUT.glob("送印_*.pdf")) + list(OUT.glob("项目速览_*.html")):
        f.unlink()

    ns = sum(1 for i in items if i["kind"] != "appendix")
    print(f"\n完成")
    mb = pdf.stat().st_size / 1024 / 1024
    print(f"  {pdf.name}   {total} 页（目录 {n_toc} + {len(items)} 份共 {total - n_toc} 页）"
          f"　{mb:.1f} MB{'' if mb < 30 else '　!! 超 30MB，发不出去'}")
    print(f"  {html.name}  目录 + {ns} 份项目说明 + 附录")

    if "--split" in sys.argv:
        split_by_section(items, pdf, n_toc)


def split_by_section(items, pdf: Path, n_toc: int):
    """按板块切出分册。总册 7.9MB 本来就发得出去，分册是给交付用的——
    销售只带一个板块时不必抱着 90 页跑，客户也不用在 44 份里翻。
    直接从已排好序的总册里切页，不重渲。"""
    out = OUT / "分册"
    out.mkdir(exist_ok=True)
    for f in out.glob("*.pdf"):
        f.unlink()
    secs, pg = {}, n_toc + 1
    for it in items:
        secs.setdefault(it["sec"], []).extend(range(pg, pg + it["n"]))
        pg += it["n"]
    print("\n分册")
    for i, (sec, pages) in enumerate(secs.items(), 1):
        rng = ",".join(map(str, pages))
        dst = out / f"{i:02d}_{sec}.pdf"
        subprocess.run(["mutool", "merge", "-o", str(dst), str(pdf), rng],
                       check=True, capture_output=True)
        # 切页后每本都拖着整册的对象表，去重能省三成多，小文件上不到 1 秒
        tmp = dst.with_suffix(".tmp.pdf")
        subprocess.run(["mutool", "clean", "-ggggz", str(dst), str(tmp)],
                       check=True, capture_output=True)
        tmp.replace(dst)
        print(f"  {dst.name}　{build.page_count(dst)} 页"
              f"　{dst.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
