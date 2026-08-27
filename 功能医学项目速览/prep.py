#!/usr/bin/env python3
"""
检验报告上传预处理 —— 把过大的 PDF 变成能传上去的东西

上传有 30MB 上限，改不了。但做速览需要的是报告里的**文字**：项目名、样本类型、
方法学、参考区间、单位、示例值。扫描件那 30MB 全是像素，没有信息量。

用法:
    python prep.py input/肠道微生态.pdf         # 处理一份
    python prep.py input/                       # 处理目录里全部 PDF
    python prep.py input/x.pdf --px 2200        # 字太小看不清就调高
    python prep.py input/x.pdf --limit 20       # 分卷上限改成 20MB

产物在 input/_prep/<报告名>/ 下，脚本最后会直接告诉你该传哪个。

依赖: poppler-utils（pdftotext / pdftoppm / pdfinfo）。
      扫描件重打包成 PDF 还需要 pip install Pillow；没装就只出图片，一样能传。
"""
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

MB = 1024 * 1024
TEXT_PER_PAGE = 80          # 每页平均字符数低于此值，判为扫描件


def need(*tools):
    miss = [t for t in tools if not shutil.which(t)]
    if miss:
        sys.exit(f"缺少工具 {miss}，先装 poppler-utils:\n"
                 f"  sudo apt-get install -y poppler-utils   # macOS: brew install poppler")


def size_mb(p: Path) -> float:
    return p.stat().st_size / MB


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def extract_text(pdf: Path, dest: Path) -> tuple[Path | None, int]:
    """抽文字层。返回 (文件路径或 None, 字符数)。"""
    txt = dest / (pdf.stem + ".txt")
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)],
                   capture_output=True, text=True)
    if not txt.exists():
        return None, 0
    n = len(txt.read_text(encoding="utf-8", errors="replace").strip())
    if n == 0:
        txt.unlink()
        return None, 0
    return txt, n


def render(pdf: Path, dest: Path, px: int, quality: int) -> list[Path]:
    """按长边像素封顶渲染。

    不要用 -r dpi：页面 box 不正常的 PDF（比如别的工具用图片拼出来的）
    一页可能标着 46 英寸宽，150 dpi 渲出来是 7000 像素，越压越大。
    -scale-to 直接锁长边，跟页面尺寸无关。
    """
    subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", f"quality={quality}",
                    "-scale-to", str(px), str(pdf), str(dest / "p")],
                   capture_output=True, text=True)
    return sorted(dest.glob("p-*.jpg")) or sorted(dest.glob("p*.jpg"))


def repack(imgs: list[Path], dest: Path, stem: str, limit_mb: float) -> list[Path]:
    """把页图重新打包成 PDF；超过上限就分卷。Pillow 缺失时返回空列表。"""
    try:
        from PIL import Image
    except ImportError:
        return []

    # 按累计图片体积切卷，留 15% 余量给 PDF 结构开销
    budget = limit_mb * MB * 0.85
    vols, cur, acc = [], [], 0
    for im in imgs:
        s = im.stat().st_size
        if cur and acc + s > budget:
            vols.append(cur)
            cur, acc = [], 0
        cur.append(im)
        acc += s
    if cur:
        vols.append(cur)

    out = []
    for i, vol in enumerate(vols, 1):
        name = f"{stem}_压缩.pdf" if len(vols) == 1 else f"{stem}_压缩_第{i}卷共{len(vols)}卷.pdf"
        path = dest / name
        pages = [Image.open(p).convert("RGB") for p in vol]
        pages[0].save(path, save_all=True, append_images=pages[1:])
        for p in pages:
            p.close()
        out.append(path)
    return out


def handle(pdf: Path, px: int, quality: int, limit: float, keep_images: bool):
    dest = pdf.parent / "_prep" / pdf.stem
    dest.mkdir(parents=True, exist_ok=True)

    pages = page_count(pdf)
    print(f"\n── {pdf.name}　{size_mb(pdf):.1f} MB　{pages} 页 " + "─" * 20)

    txt, chars = extract_text(pdf, dest)
    per_page = chars / pages if pages else 0

    if txt and per_page >= TEXT_PER_PAGE:
        print(f"   文字层可用：{chars} 字，每页约 {per_page:.0f} 字")
        print(f"   → 传这个就够了，别传 PDF：{txt.relative_to(pdf.parent.parent)}"
              f"　{txt.stat().st_size/1024:.0f} KB")
        if not keep_images:
            return
        print("   （--keep-images 已开，仍然渲染页图备查）")
    elif txt:
        print(f"   文字层几乎是空的：{chars} 字，每页约 {per_page:.0f} 字 —— 按扫描件处理")
    else:
        print("   没有文字层 —— 扫描件")

    imgs = render(pdf, dest, px, quality)
    if not imgs:
        print("   !! 渲染失败，检查 pdftoppm 是否正常")
        return
    img_mb = sum(i.stat().st_size for i in imgs) / MB
    print(f"   页图：{len(imgs)} 张　长边 {px}px　合计 {img_mb:.1f} MB")

    vols = repack(imgs, dest, pdf.stem, limit)
    if not vols:
        print(f"   → Pillow 没装，直接传这批 JPG：{dest.relative_to(pdf.parent.parent)}/")
        print("      装上就能合成 PDF：pip install Pillow")
        return

    total = sum(size_mb(v) for v in vols)
    print(f"   压缩后：{total:.1f} MB（原 {size_mb(pdf):.1f} MB，"
          f"降到 {total/size_mb(pdf)*100:.0f}%）")
    for v in vols:
        flag = "  !! 仍超上限" if size_mb(v) > limit else ""
        print(f"   → 传：{v.relative_to(pdf.parent.parent)}　{size_mb(v):.1f} MB{flag}")

    if total >= size_mb(pdf):
        print(f"   !! 没压下去。原件本来就是低清扫描，或者 --px 给太大了"
              f"（现在 {px}）。原件 {size_mb(pdf):.1f} MB"
              + ("，本来就在上限内，直接传原件。" if size_mb(pdf) <= limit else "，把 --px 调到 1200 再试。"))
    elif any(size_mb(v) > limit for v in vols):
        print(f"   单页就超 {limit} MB，把 --px 调低（现在 {px}）再跑一次。")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("target", help="PDF 文件，或装着 PDF 的目录")
    ap.add_argument("--px", type=int, default=1700,
                    help="页面长边像素上限，默认 1700（≈A4 150dpi）；字小看不清调到 2200")
    ap.add_argument("--quality", type=int, default=75, help="JPEG 质量，默认 75")
    ap.add_argument("--limit", type=float, default=28, help="分卷上限 MB，默认 28（30 留点余量）")
    ap.add_argument("--keep-images", action="store_true", help="文字层可用时也渲染页图")
    a = ap.parse_args()

    need("pdftotext", "pdftoppm", "pdfinfo")

    t = Path(a.target)
    if t.is_dir():
        pdfs = sorted(p for p in t.glob("*.pdf") if "_prep" not in p.parts)
    elif t.is_file():
        pdfs = [t]
    else:
        sys.exit(f"找不到 {t}")
    if not pdfs:
        sys.exit(f"{t} 里没有 PDF")

    for pdf in pdfs:
        handle(pdf, a.px, a.quality, a.limit, a.keep_images)
    print(f"\n共处理 {len(pdfs)} 份。产物在 _prep/ 下，不进版本库。")


if __name__ == "__main__":
    main()
