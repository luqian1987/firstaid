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
项目清单.md     协议附件 1 的 45 项名称与价格，已完成的打了勾
build.py       构建 + 逐份分页校验
assets/        base.css（19 份共用）+ overrides.css
sheets/        每个项目一个 HTML 片段 + manifest.txt 决定顺序
input/         检验报告原件（含个人健康数据，不进版本库）
out/           构建产物（不进版本库）
成稿/          已交付批次的成稿
```

已验证：装齐 playwright / poppler-utils / Noto Sans CJK SC 之后 `python build.py`
可跑通——4 份各 2 页，合并 8 页 A4，产物与 `成稿/` 里那份一致。
