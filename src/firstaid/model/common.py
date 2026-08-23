"""基础枚举与共用值对象。

这一层刻意不含任何医学知识——医学知识全部下沉到 knowledge/ 下的 YAML。
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Mutable(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# 观察的性质
# --------------------------------------------------------------------------
class ObservationKind(str, Enum):
    QUANTITATIVE = "quantitative"   # 有数值，可与参考区间比较
    QUALITATIVE = "qualitative"     # 阴性/阳性/±
    IMAGING = "imaging"             # 影像测量或影像描述
    NARRATIVE = "narrative"         # 报告里的文字结论
    DERIVED = "derived"             # 本系统算出来的派生指标


class RangeStatus(str, Enum):
    IN_RANGE = "in_range"
    HIGH = "high"
    LOW = "low"
    NO_RANGE = "no_range"     # 原报告没给区间：一等状态，不是缺失
    UNKNOWN = "unknown"       # 有区间但无法判定（单位不明、值非数值等）


class RangeKind(str, Enum):
    """参考区间是"什么口径"的区间。

    这个区分是必需的：辅酶Q10 被标"不足"用的是实验室按 340 例健康人
    5%-95% 分位定的自有区间，不是疾病界值。两者不能同等对待。
    """
    DISEASE_CUTOFF = "disease_cutoff"      # 疾病界值（如 LDL-C 目标值）
    POPULATION = "population"              # 公认人群参考区间
    LAB_PERCENTILE = "lab_percentile"      # 实验室自有百分位区间
    UNSPECIFIED = "unspecified"            # 原报告给了区间但没说口径


class Qualitative(str, Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"
    TRACE = "trace"
    NOT_DETECTED = "not_detected"
    NORMAL = "normal"          # 影像文字结论"正常 / 未见异常"


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


# --------------------------------------------------------------------------
# 出处
# --------------------------------------------------------------------------
class Provenance(Frozen):
    """每一条观察必须能回到原始文件的具体位置。

    二次判读之所以敢反驳原报告的建议，前提是每个反证都能指回同一份报告。
    没有出处的观察不允许进入判读。
    """
    source_id: str                      # 来源文档 id
    source_label: str | None = None     # "综合体检主报告"
    page: int | None = None
    raw_text: str | None = None         # 提取到的原始文本片段
    extractor: str | None = None        # "deepseek-chat@2026-08" / "manual"
    extracted_at: datetime | None = None
    confidence: float | None = None     # 提取器自评置信度 0-1

    def cite(self) -> str:
        bits = [self.source_label or self.source_id]
        if self.page is not None:
            bits.append(f"第{self.page}页")
        return " · ".join(bits)


class SourceDocument(Frozen):
    """一份来源报告。多来源合并时，身份与周期核对的记录挂在这里。"""
    id: str
    label: str
    kind: str = "unknown"               # main_report / supplement / screening
    date_from: date | None = None
    date_to: date | None = None
    page_count: int | None = None
    merge_note: str | None = None       # "已核对为同一体检周期"
    unreadable_pages: list[int] = Field(default_factory=list)  # 纯图像页


# --------------------------------------------------------------------------
# 三态
# --------------------------------------------------------------------------
class TriState(str, Enum):
    """规则的评估结果。

    INDETERMINATE 是这个系统的关键设计：输入不全时规则既不算命中也不算未命中，
    它要浮到「边界」章节里去，回答"哪些结论会被尚未拿到的报告推翻"。
    """
    TRIGGERED = "triggered"
    NOT_TRIGGERED = "not_triggered"
    INDETERMINATE = "indeterminate"


class ContextKey(str, Enum):
    """本人背景事实。报告里没有，但规则可能依赖。

    缺失时规则不假设，只把动作降级为条件式，并登记到「边界」。
    """
    ALCOHOL_INTAKE = "alcohol_intake"           # 每周饮酒量
    MEDICATIONS = "medications"                 # 在服药物与保健品
    SMOKING = "smoking"                         # 吸烟史
    FAMILY_CVD = "family_early_cvd"             # 家族早发心脑血管病史
    PREGNANCY = "pregnancy"
    SYMPTOMS = "symptoms"                       # 相关症状时间线
    PRIOR_ENCOUNTERS = "prior_encounters"       # 既往体检数据
    TRAUMA_HISTORY = "trauma_history"           # 外伤/骨折史
    PRIOR_IMAGING = "prior_imaging"             # 既往影像原片（不是报告单）


CONTEXT_LABELS: dict[ContextKey, str] = {
    ContextKey.ALCOHOL_INTAKE: "每周饮酒量",
    ContextKey.MEDICATIONS: "在服药物与保健品清单",
    ContextKey.SMOKING: "吸烟史",
    ContextKey.FAMILY_CVD: "家族早发心脑血管病史（男<55/女<65）",
    ContextKey.PREGNANCY: "妊娠状态",
    ContextKey.SYMPTOMS: "相关症状时间线",
    ContextKey.TRAUMA_HISTORY: "外伤或骨折史",
    ContextKey.PRIOR_IMAGING: "既往影像原片（不是报告单）",
    ContextKey.PRIOR_ENCOUNTERS: "既往体检数据",
}


def as_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None
