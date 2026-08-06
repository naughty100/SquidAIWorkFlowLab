"""写盘前的敏感信息过滤。"""

from collections.abc import Iterable, Mapping
from enum import Enum
from pathlib import Path
from typing import cast

from pydantic import BaseModel, SecretStr

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]

REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
)


def is_sensitive_key(key: str) -> bool:
    """以大小写无关方式识别常见敏感字段。"""
    normalized = key.casefold().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact_text(value: str, secrets: Iterable[str]) -> str:
    """替换文本中出现的实际秘密值。"""
    redacted = value
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, REDACTED)
    return redacted


def sanitize(value: object, *, secrets: Iterable[str] = ()) -> JSONValue:
    """递归转换为 JSON 值，并按字段名及实际值脱敏。"""
    secret_tuple = tuple(secret for secret in secrets if secret)

    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, SecretStr):
        return REDACTED
    if isinstance(value, str):
        return redact_text(value, secret_tuple)
    if isinstance(value, Path):
        return redact_text(value.as_posix(), secret_tuple)
    if isinstance(value, Enum):
        return sanitize(value.value, secrets=secret_tuple)
    if isinstance(value, BaseException):
        return {
            "type": type(value).__name__,
            "message": redact_text(str(value), secret_tuple),
        }
    if isinstance(value, BaseModel):
        return sanitize(value.model_dump(mode="json"), secrets=secret_tuple)
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        result: dict[str, JSONValue] = {}
        for raw_key, item in mapping.items():
            key = str(raw_key)
            result[key] = REDACTED if is_sensitive_key(key) else sanitize(
                item, secrets=secret_tuple
            )
        return result
    if isinstance(value, Iterable) and not isinstance(value, bytes | bytearray):
        iterable = cast(Iterable[object], value)
        return [sanitize(item, secrets=secret_tuple) for item in iterable]
    return redact_text(str(value), secret_tuple)
