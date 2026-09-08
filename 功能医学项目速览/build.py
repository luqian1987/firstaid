#!/usr/bin/env python3
"""
功能医学项目速览 —— 构建脚本

用法:
    python build.py                     # 构建 manifest 里的全部项目
    python build.py 神经01 代谢02        # 只构建指定项目（按文件名模糊匹配）
    python build.py --check             # 只做分页校验，不出 PDF

产物:
    out/项目速览_XXX.html   屏幕版（浏览器打开，有裁切线）
    out/送印_XXX.pdf        送印版 A4

关键校验: 每份项目说明的实际页数必须与它自己 .mast 上印的「共 N 页」一致。
默认 2 页；细则太长装不下的（如分子筛查 02 权益卡）可以写成 4 页，
改 .mast 与各个 .pbreak 上的「共 N 页」即可，脚本按稿子自己的声明校验。
脚本会逐份单独渲染计算页数，
超出的会明确报出来——不要靠肉眼看，直接看脚本报错。
"""
import re, sys, asyncio, subprocess, tempfile, shutil
from pathlib import Path

ROOT = Path(__file__).parent
SHEETS = ROOT / "sheets"
ASSETS = ROOT / "assets"
OUT = ROOT / "out"

PDF_MARGIN = {"top": "14mm", "right": "13mm", "bottom": "12mm", "left": "13mm"}


def load_css() -> str:
    css = (ASSETS / "base.css").read_text(encoding="utf-8")
    ov = ASSETS / "overrides.css"
    if ov.exists():
        css += "\n" + ov.read_text(encoding="utf-8")
    return css


def wrap(body: str) -> str:
    return (
        '<meta charset="utf-8">\n'
        "<title>功能医学检测项目 · 精简说明</title>\n"
        f"<style>{load_css()}</style>\n{body}"
    )


def section(name: str) -> str:
    """文件名 NN_板块编号_项目名.html 里的板块编号，如 代谢02。"""
    parts = name.split("_")
    return parts[1] if len(parts) > 2 else ""


def pick(filters):
    names = [l.strip() for l in (SHEETS / "manifest.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    missing = [n for n in names if not (SHEETS / n).exists()]
    if missing:
        sys.exit(f"manifest 里这些文件不存在: {missing}")
    if not filters:
        return names

    # 先按板块匹配（"代谢" 命中 代谢01–04，不会误伤 营养05_营养元素代谢…），
    # 板块匹配不上再退回文件名子串匹配（"VAP" 这种）。
    hit = []
    for f in filters:
        m = [n for n in names if section(n).startswith(f)] or [n for n in names if f in n]
        if not m:
            secs = sorted({section(n) for n in names if section(n)})
            sys.exit(f"没有匹配「{f}」的项目。现有板块: {secs}")
        hit += [n for n in m if n not in hit]
    return [n for n in names if n in hit]          # 按 manifest 顺序出稿


async def render(html_path: Path, pdf_path: Path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        await pg.goto("file://" + str(html_path.resolve()), wait_until="networkidle")
        await pg.pdf(path=str(pdf_path), format="A4", print_background=True, margin=PDF_MARGIN)
        await b.close()


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return -1


def declared_pages(text: str) -> int:
    """稿子自己声明的页数——.mast 上印的「共 N 页」。

    页数写在稿子里而不是另设一张登记表：这个数本来就要印在页眉上、
    而且必须是对的，让它同时当校验基准，就不会出现表和稿对不上的情况。
    """
    m = re.search(r"共\s*(\d+)\s*页", text)
    return int(m.group(1)) if m else 2


def check_each(names) -> bool:
    """逐份渲染，确认实际页数与稿子自己声明的一致。"""
    ok = True
    tmp = Path(tempfile.mkdtemp())
    for n in names:
        src = (SHEETS / n).read_text(encoding="utf-8")
        want = declared_pages(src)
        h = tmp / (n + ".html")
        h.write_text(wrap(src), encoding="utf-8")
        pdf = tmp / (n + ".pdf")
        asyncio.run(render(h, pdf))
        c = page_count(pdf)
        flag = "OK " if c == want else "!! "
        note = "" if c == want else f"（声明 {want} 页）"
        print(f"  {flag}{c} 页  {n}{note}")
        if c != want:
            ok = False
    shutil.rmtree(tmp, ignore_errors=True)
    if not ok:
        print("\n  超页的处理顺序（从影响最小的开始）:")
        print("   1. 适合人群 12 项 → 9 项")
        print("   2. 科学依据里最长那条删掉一个从句")
        print("   3. 可以做什么 的 <i> 段删掉一个短句")
        print("   注意: 不要改字号或行距，全套必须保持一致。")
        print("   细则确实装不下的，可以把稿子写成 4 页——改 .mast 与各 .pbreak 上的")
        print("   「共 N 页」，脚本按稿子自己的声明校验。")
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    names = pick(args)

    print(f"共 {len(names)} 份，逐份校验分页:")
    ok = check_each(names)
    if check_only:
        sys.exit(0 if ok else 1)
    if not ok:
        sys.exit("\n有项目的实际页数与声明不符，先修好再出稿。")

    OUT.mkdir(exist_ok=True)
    tag = "全部" if not args else "_".join(args)
    body = "\n".join((SHEETS / n).read_text(encoding="utf-8") for n in names)
    html = OUT / f"项目速览_{tag}.html"
    pdf = OUT / f"送印_{tag}.pdf"
    html.write_text(wrap(body), encoding="utf-8")
    asyncio.run(render(html, pdf))

    total = page_count(pdf)
    want = sum(declared_pages((SHEETS / n).read_text(encoding="utf-8")) for n in names)
    assert total == want, f"合并后 {total} 页，应为 {want} 页"
    print(f"\n完成: {html.name} / {pdf.name}  共 {total} 页")


if __name__ == "__main__":
    main()
