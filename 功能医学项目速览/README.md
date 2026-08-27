# 快速开始

```bash
pip install playwright && playwright install chromium
sudo apt-get install -y poppler-utils fonts-noto-cjk

claude          # 在本目录启动，Claude 会自动读 CLAUDE.md
```

把检验报告放进 `input/`，然后说：

> 把 input 里的肠道微生态报告做成项目速览

出稿在 `out/`。手动构建：`python build.py` 或 `python build.py 神经01`。

## 目录

```
CLAUDE.md      工作说明，Claude Code 进目录自动读
项目清单.md     协议附件 1 原文：45 项的名称与价格，不得改写
板块划分.md     出稿口径：11 个板块、33 份的编号与成册顺序、缺料状态
build.py       构建 + 逐份分页校验
prep.py        报告传不上去时先跑这个：抽文字层 / 压缩扫描件 / 自动分卷
assets/        base.css（19 份共用）+ overrides.css
sheets/        每个项目一个 HTML 片段 + manifest.txt 决定顺序
input/         检验报告原件（含个人健康数据，不进版本库）
out/           构建产物（不进版本库）
成稿/          已交付批次的成稿
```

## 报告太大传不上去

上传有 30MB 上限，**这是平台侧的，改不了**。但做速览要的是报告里的文字，不是像素：

```bash
python prep.py input/肠道微生态.pdf     # 处理一份
python prep.py input/                   # 处理目录里全部 PDF
python prep.py input/x.pdf --px 2200    # 字太小看不清就调高
```

有文字层的，抽出 `.txt` 直接传，几十 KB 顶几十 MB；扫描件按长边 1700px 重渲重打包，
实测 44MB → 5.3MB（12%），每一个数值和参考区间仍然清清楚楚；还超上限就自动分卷。
产物在 `input/_prep/` 下，不进版本库。

## 按板块出预览

```bash
python build.py 神经          # 只出神经板块
python build.py 神经 血栓      # 出两个板块
python build.py 代谢02        # 出单份
python build.py --check       # 全部只验分页，不出 PDF
```

板块名精确匹配，`代谢` 只命中代谢板块，不会误伤 `营养05_营养元素代谢…`；
板块匹配不上才退回文件名子串（`VAP` 这种）。

已验证：装齐 playwright / poppler-utils / Noto Sans CJK SC 之后 `python build.py`
可跑通——4 份各 2 页，合并 8 页 A4，中文无方块，逐页看图无溢出错位。
`成稿/` 是已交付批次的原件，内容与重建产物一致；顺序不同，那批按交付顺序排，
manifest 现在按成册顺序排。
