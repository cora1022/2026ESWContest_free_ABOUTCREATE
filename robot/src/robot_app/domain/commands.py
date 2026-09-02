from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from robot_protocol.actions import ALLOWED_ACTIONS, DIRECTIONS, QUEUED_ACTIONS, VIDEO_ACTIONS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class RobotCommand:
    command_id: str
    action: str
    text: str = ""
    duration_ms: int = 500
    expires_at: datetime | None = None

    @classmethod
    def from_message(cls, payload: dict[str, Any]) -> "RobotCommand":
        command_id = str(payload.get("id") or "").strip()
        action = str(payload.get("action") or "").strip().upper()
        if not command_id:
            raise ValueError("명령 ID가 없습니다.")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"허용되지 않은 명령입니다: {action}")

        try:
            duration_ms = int(payload.get("duration_ms", 500))
        except (TypeError, ValueError):
            duration_ms = 500

        max_duration_ms = 10_000 if action == "VIDEO_START" else 1_000
        return cls(
            command_id=command_id,
            action=action,
            text=str(payload.get("text") or "").strip(),
            duration_ms=max(100, min(duration_ms, max_duration_ms)),
            expires_at=parse_utc(payload.get("expires_at")),
        )

    def is_expired(self) -> bool:
        return self.expires_at is not None and utc_now() >= self.expires_at


__all__ = [
    "ALLOWED_ACTIONS",
    "DIRECTIONS",
    "QUEUED_ACTIONS",
    "VIDEO_ACTIONS",
    "RobotCommand",
    "parse_utc",
    "utc_now",
]
