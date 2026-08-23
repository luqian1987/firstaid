"""DeepSeek 提取适配器（骨架）。

这里只固定契约与约束，不在本阶段接真实网络调用：
  - 输出必须是 schema 受限的 JSON，字段与 ExtractedRow 一一对应；
  - 提取器只允许"抄"，不允许"判断"：不得改写数值、不得补参考区间、
    不得把没写的结论写出来。判断全部由规则层做。
  - 认不出的指标名原样返回，由本体层决定收不收，而不是让提取器猜。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .base import ExtractedDocument, ExtractedRow

EXTRACTION_CONTRACT = """你是体检报告的转录器，不是解读器。

规则：
1. 只转录报告上写着的内容。数值、单位、参考区间一律原样照抄，包括 "<0.20" 这类
   带检测限符号的写法——符号本身是信息，不许去掉。
2. 报告没给参考区间的项目，ref 留空。不要用你知道的常用区间去填。
3. 不要判断高低，不要写结论，不要合并同类项。原报告打的箭头放进 flag 字段。
4. 影像描述放 text 字段，并尽量抄下设备型号(device)与测量轴(axis)。
5. 认不出的指标名原样放进 raw_name，不要改写成你认识的名字。
6. 纯图像页（无文字结论）记入 unreadable_pages，不要描述图像内容。

按给定 JSON schema 输出。"""


class DeepSeekExtractor:
    name = "deepseek"

    def __init__(self, model: str = "deepseek-chat", api_key: str | None = None,
                 base_url: str = "https://api.deepseek.com"):
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = base_url

    def extract(self, path: Path) -> ExtractedDocument:
        raise NotImplementedError(
            "DeepSeek 提取尚未接线。当前阶段用 JsonExtractor 从已转录的 JSON 读入。")


class JsonExtractor:
    """从已转录好的 JSON 读入。用于测试、回归、以及人工校对后的复跑。"""
    name = "json"

    def extract(self, path: Path) -> ExtractedDocument:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = [ExtractedRow.model_validate(r) for r in doc.pop("rows", [])]
        return ExtractedDocument(rows=rows, extractor=self.name, **doc)
