#!/usr/bin/env python3
"""
总包构建 —— 把 sheets/ 里的原生 HTML 与外部 PDF 单页合成一册，前面加目录。

为什么需要它：15 份更早做的稿子只有 PDF、没有 HTML 源码。build.py 只认 HTML，
出不了这 15 份。本脚本按 pack.toml 描述的成册顺序，把两种来源拼在一起。

用法:
    python pack.py              # 出 out/总包_目录.pdf + out/总包_全册.pdf + out/总包_全册.html

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
        return tomllib.load(f)["item"]


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
            rows.append(f'<tr class="grp"><td colspan="4"><b>{cur}</b>'
                        f'<span>{n} 份</span></td></tr>')
        rows.append(
            f'<tr><td class="nn">{it["nn"]}</td>'
            f'<td class="nm"><b>{it["code"]}</b>　{it["name"]}</td>'
            f'<td class="pr">¥{it["price"]}</td>'
            f'<td class="pg">{pg}</td></tr>')
        pg += 2
    n_pdf = sum(1 for i in items if i["kind"] == "pdf")
    return (
        f'<style>{TOC_CSS}</style>\n<div class="toc">'
        f'<h1>功能医学检测项目速览</h1>'
        f'<div class="sub">共 {len(items)} 份 · 每份 2 页 A4 · 版本 2026-08</div>'
        f'<div class="rule"></div>'
        f'<table>{COLS}{"".join(rows)}</table>'
        f'<div class="foot">'
        f'名称与收费以《心理睡眠体检检测项目协议》附件 1 为准。'
        f'本册为检测项目说明，不构成医疗建议；检测结果需由医师结合临床综合判断。<br>'
        f'其中 <b>{n_pdf} 份</b>由既有 PDF 成稿直接并入，'
        f'<b>{len(items)-n_pdf} 份</b>由本工程 HTML 源码渲染。'
        f'</div></div>')


# ── 取页 ────────────────────────────────────────────────────────────────
def slice_pdf(src: Path, first: int, dst: Path):
    """取 src 的 first、first+1 两页写到 dst。

    用 poppler 的 pdfseparate + pdfunite，不引 pypdf——本机的 cryptography
    装坏了（缺 _cffi_backend），pypdf 一 import 就炸。
    """
    tmp = dst.parent / f"_sep_{dst.stem}"
    tmp.mkdir(exist_ok=True)
    subprocess.run(["pdfseparate", "-f", str(first), "-l", str(first + 1),
                    str(src), str(tmp / "p-%d.pdf")], check=True, capture_output=True)
    pages = [tmp / f"p-{first}.pdf", tmp / f"p-{first + 1}.pdf"]
    subprocess.run(["pdfunite", *map(str, pages), str(dst)], check=True, capture_output=True)
    for f in pages:
        f.unlink(missing_ok=True)
    tmp.rmdir()


def merge(parts, dst: Path):
    subprocess.run(["pdfunite", *map(str, parts), str(dst)], check=True, capture_output=True)


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

    parts, bad = [toc_pdf], []
    for it in items:
        dst = tmp / f'{it["nn"]}.pdf'
        if it["kind"] == "sheet":
            src = ROOT / "sheets" / it["file"]
            h = tmp / f'{it["nn"]}.html'
            h.write_text(build.wrap(src.read_text(encoding="utf-8")), encoding="utf-8")
            asyncio.run(build.render(h, dst))
        else:
            slice_pdf(ROOT / it["file"], it["page"], dst)
        n = build.page_count(dst)
        if n != 2:
            bad.append((it["code"], n))
        print(f'  {"OK " if n == 2 else "!! "}{n} 页  {it["nn"]} {it["code"]} {it["name"]}')
        parts.append(dst)

    if bad:
        sys.exit(f"\n这些不是 2 页，先修：{bad}")

    pdf = OUT / "总包_全册.pdf"
    merge(parts, pdf)
    total = build.page_count(pdf)
    expect = build.page_count(toc_pdf) + 2 * len(items)
    assert total == expect, f"合并后 {total} 页，应为 {expect} 页"

    # HTML 版：目录 + 有源码的那些
    body = [toc_html([i for i in items], build.page_count(toc_pdf) + 1)]
    body += [(ROOT / "sheets" / i["file"]).read_text(encoding="utf-8")
             for i in items if i["kind"] == "sheet"]
    html = OUT / "总包_全册.html"
    html.write_text(build.wrap("\n".join(body)), encoding="utf-8")

    ns = sum(1 for i in items if i["kind"] == "sheet")
    print(f"\n完成")
    print(f"  {pdf.name}   {total} 页（目录 {build.page_count(toc_pdf)} + {len(items)} 份 × 2）")
    print(f"  {html.name}  目录 + {ns} 份原生 HTML（另 {len(items)-ns} 份仅 PDF，无源码）")


if __name__ == "__main__":
    main()
