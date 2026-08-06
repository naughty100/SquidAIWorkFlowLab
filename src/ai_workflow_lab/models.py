"""可注入的最小模型接口与固定响应实现。"""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol


class TextModel(Protocol):
    """后续实验可依赖的最小文本模型协议。"""

    def invoke(self, messages: Sequence[object]) -> str: ...

    def stream(self, messages: Sequence[object]) -> Iterator[str]: ...


@dataclass(frozen=True, slots=True)
class FixedResponseModel:
    """不访问网络、始终返回固定文本的模型。"""

    response: str
    stream_chunks: tuple[str, ...] = ()

    def invoke(self, messages: Sequence[object]) -> str:
        del messages
        return self.response

    def stream(self, messages: Sequence[object]) -> Iterator[str]:
        del messages
        chunks: Iterable[str] = self.stream_chunks or (self.response,)
        yield from chunks
