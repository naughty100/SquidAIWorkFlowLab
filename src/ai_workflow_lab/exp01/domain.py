"""实验一的公共输入、模型响应与最终领域对象。"""

import hashlib
import json
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class IdeaBrief(BaseModel):
    """内容选题输入。"""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=2, max_length=200)
    goal: str = Field(min_length=2, max_length=300)
    audience: str = Field(min_length=2, max_length=200)
    constraints: list[str] = Field(default_factory=list, max_length=10)


class TopicOptionDraft(BaseModel):
    """只包含允许模型生成的字段。

    稳定标识符由应用在校验完成后补齐，避免模型伪造确定性数据。
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=100)
    angle: str = Field(min_length=2, max_length=300)
    target_audience: str = Field(min_length=2, max_length=200)
    core_question: str = Field(min_length=2, max_length=300)
    reason: str = Field(min_length=2, max_length=300)


class TopicOptionsDraft(BaseModel):
    """三个 variant 共用的模型响应容器。"""

    model_config = ConfigDict(extra="forbid")

    options: Annotated[list[TopicOptionDraft], Field(min_length=3, max_length=3)]


class TopicOption(TopicOptionDraft):
    """校验通过后由代码补齐稳定 ID 的最终选题。"""

    topic_id: str = Field(pattern=r"^topic-[0-9a-f]{12}$")


class TopicOptions(BaseModel):
    """实验一最终输出。"""

    model_config = ConfigDict(extra="forbid")

    options: Annotated[list[TopicOption], Field(min_length=3, max_length=3)]


def _slug_source(value: str) -> str:
    """规范化参与 ID 派生的文本，消除大小写与连续空白差异。"""
    return re.sub(r"\s+", " ", value.strip().casefold())


def finalize_topic_options(draft: TopicOptionsDraft) -> TopicOptions:
    """以规范化内容和位置派生 ID；相同合法输出始终得到相同 ID。"""
    finalized: list[TopicOption] = []
    for index, option in enumerate(draft.options):
        # ID 只依赖稳定的业务内容与位置 同一合法结果在不同运行中可复现
        source = json.dumps(
            {
                "index": index,
                "title": _slug_source(option.title),
                "angle": _slug_source(option.angle),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
        finalized.append(TopicOption(topic_id=f"topic-{digest}", **option.model_dump()))
    return TopicOptions(options=finalized)
