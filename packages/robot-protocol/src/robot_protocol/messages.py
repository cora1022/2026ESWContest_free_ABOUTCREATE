"""Dependency-free JSON message models shared by both applications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any

from .actions import (
    DEFAULT_COMMAND_DURATION_MS,
    MAX_COMMAND_DURATION_MS,
    MIN_COMMAND_DURATION_MS,
    Action,
    parse_action,
)
from .version import PROTOCOL_VERSION, is_supported_protocol_version


class MessageType(str, Enum):
    HELLO = "hello"
    HELLO_ACK = "hello_ack"
    COMMAND = "command"
    TELEMETRY = "telemetry"
    STATUS = "status"
    COMMAND_RESULT = "command_result"
    CAMERA = "camera"
    SPEECH = "speech"
    STATE = "state"
    EVENT = "event"


ROBOT_TO_SERVER_TYPES = frozenset(
    {
        MessageType.HELLO,
        MessageType.TELEMETRY,
        MessageType.STATUS,
        MessageType.COMMAND_RESULT,
        MessageType.CAMERA,
        MessageType.SPEECH,
    }
)
SERVER_TO_ROBOT_TYPES = frozenset({MessageType.HELLO_ACK, MessageType.COMMAND})
SERVER_TO_DASHBOARD_TYPES = frozenset(
    {
        MessageType.STATE,
        MessageType.EVENT,
        MessageType.SPEECH,
    }
)


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} 값이 없습니다.")
    return value


def _protocol_version(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError(f"지원하지 않는 프로토콜 버전입니다: {value!r}")
    try:
        version = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"지원하지 않는 프로토콜 버전입니다: {value!r}") from exc
    if not is_supported_protocol_version(version):
        raise ValueError(f"지원하지 않는 프로토콜 버전입니다: {value!r}")
    return version


def parse_message_type(payload: Mapping[str, Any]) -> MessageType:
    """Read and validate the ``type`` field of a JSON message."""

    raw_type = str(payload.get("type") or "").strip()
    try:
        return MessageType(raw_type)
    except ValueError as exc:
        raise ValueError(f"알 수 없는 메시지 형식입니다: {raw_type or None!r}") from exc


@dataclass(frozen=True, slots=True)
class HelloMessage:
    robot_id: str
    token: str = field(repr=False)
    protocol_version: int = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if not self.robot_id.strip():
            raise ValueError("robot_id 값이 없습니다.")
        if not self.token:
            raise ValueError("token 값이 없습니다.")
        object.__setattr__(self, "protocol_version", _protocol_version(self.protocol_version))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HelloMessage":
        if parse_message_type(payload) is not MessageType.HELLO:
            raise ValueError("hello 메시지가 아닙니다.")
        return cls(
            robot_id=_required_string(payload, "robot_id"),
            token=_required_string(payload, "token"),
            protocol_version=_protocol_version(payload.get("protocol_version", PROTOCOL_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": MessageType.HELLO.value,
            "robot_id": self.robot_id,
            "token": self.token,
            "protocol_version": self.protocol_version,
        }


@dataclass(frozen=True, slots=True)
class HelloAckMessage:
    server_time: float
    protocol_version: int = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.server_time, bool):
            raise ValueError("server_time이 유효한 숫자가 아닙니다.")
        try:
            server_time = float(self.server_time)
        except (TypeError, ValueError) as exc:
            raise ValueError("server_time이 유효한 숫자가 아닙니다.") from exc
        if not math.isfinite(server_time) or server_time < 0:
            raise ValueError("server_time이 유효한 숫자가 아닙니다.")
        object.__setattr__(self, "server_time", server_time)
        object.__setattr__(self, "protocol_version", _protocol_version(self.protocol_version))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HelloAckMessage":
        if parse_message_type(payload) is not MessageType.HELLO_ACK:
            raise ValueError("hello_ack 메시지가 아닙니다.")
        return cls(
            server_time=payload.get("server_time"),
            protocol_version=_protocol_version(payload.get("protocol_version", PROTOCOL_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": MessageType.HELLO_ACK.value,
            "server_time": self.server_time,
            "protocol_version": self.protocol_version,
        }


@dataclass(frozen=True, slots=True)
class CommandMessage:
    command_id: str
    action: Action
    text: str = ""
    duration_ms: int = DEFAULT_COMMAND_DURATION_MS
    created_at: str = ""
    expires_at: str = ""

    def __post_init__(self) -> None:
        if not self.command_id.strip():
            raise ValueError("명령 ID가 없습니다.")
        if not isinstance(self.action, Action):
            raise TypeError("action은 Action 값이어야 합니다.")
        if not MIN_COMMAND_DURATION_MS <= self.duration_ms <= MAX_COMMAND_DURATION_MS:
            raise ValueError(
                f"duration_ms는 {MIN_COMMAND_DURATION_MS} 이상 "
                f"{MAX_COMMAND_DURATION_MS} 이하여야 합니다."
            )
        if self.action is Action.TEXT_COMMAND and not self.text.strip():
            raise ValueError("자연어 명령이 비어 있습니다.")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CommandMessage":
        if parse_message_type(payload) is not MessageType.COMMAND:
            raise ValueError("command 메시지가 아닙니다.")
        raw_duration = payload.get("duration_ms", DEFAULT_COMMAND_DURATION_MS)
        if isinstance(raw_duration, bool):
            raise ValueError("duration_ms가 정수가 아닙니다.")
        try:
            duration_ms = int(raw_duration)
        except (TypeError, ValueError) as exc:
            raise ValueError("duration_ms가 정수가 아닙니다.") from exc
        return cls(
            command_id=_required_string(payload, "id"),
            action=parse_action(payload.get("action")),
            text=str(payload.get("text") or "").strip(),
            duration_ms=duration_ms,
            created_at=str(payload.get("created_at") or "").strip(),
            expires_at=str(payload.get("expires_at") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        message: dict[str, Any] = {
            "type": MessageType.COMMAND.value,
            "id": self.command_id,
            "action": self.action.value,
            "text": self.text,
            "duration_ms": self.duration_ms,
        }
        if self.created_at:
            message["created_at"] = self.created_at
        if self.expires_at:
            message["expires_at"] = self.expires_at
        return message
