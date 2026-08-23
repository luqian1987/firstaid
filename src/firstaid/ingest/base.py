"""提取层的契约。

数据源泛化（PDF / 图片 / 不同医院），所以提取器是可替换适配器：
上层只认 ExtractedDocument，不关心它是 DeepSeek 抽的、别的模型抽的，还是人工录的。
将来并联多个提取器做交叉校验，也是在这一层做。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ExtractedRow(BaseModel):
    """提取器输出的一行。刻意保持"原样"——归一是下一层的事。"""
    raw_name: str
    value: Any = None
    unit: str | None = None
    ref: str | None = None
    flag: str | None = None
    text: str | None = None
    kind: str | None = None
    method: str | None = None
    device: str | None = None
    specimen: str | None = None
    axis: str | None = None
    observed_at: date | None = None
    page: int | None = None
    raw_line: str | None = None
    confidence: float | None = None
    # 提取器若做了初步归一，把它猜的 code 放这里；本体解析优先，猜测仅作兜底
    suggested_code: str | None = None


class ExtractedDocument(BaseModel):
    source_id: str
    source_label: str
    kind: str = "unknown"
    date_from: date | None = None
    date_to: date | None = None
    page_count: int | None = None
    unreadable_pages: list[int] = Field(default_factory=list)
    rows: list[ExtractedRow] = Field(default_factory=list)
    subject_hints: dict[str, Any] = Field(default_factory=dict)
    extractor: str = "unknown"


@runtime_checkable
class Extractor(Protocol):
    name: str

    def extract(self, path: Path) -> ExtractedDocument: ...
