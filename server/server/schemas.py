from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field
from robot_protocol.actions import ALLOWED_ACTIONS, DIRECTIONS, Action, parse_action
from robot_protocol.messages import CommandMessage


MOTION_ACTIONS = DIRECTIONS | {Action.STOP.value}


class LoginRequest(BaseModel):
    key: str = Field(min_length=8, max_length=256)


class CommandRequest(BaseModel):
    action: str
    text: str = Field(default="", max_length=500)
    duration_ms: int = Field(default=650, ge=100, le=10_000)


def normalize_action(action: str) -> str:
    return action.strip().upper()


def build_command(body: CommandRequest, *, now: datetime | None = None) -> dict[str, Any]:
    action = normalize_action(body.action)
    created_at = now or datetime.now(timezone.utc)
    ttl = 2.0 if action in MOTION_ACTIONS else 15.0
    return CommandMessage(
        command_id=str(uuid.uuid4()),
        action=parse_action(action),
        text=body.text.strip(),
        duration_ms=body.duration_ms,
        created_at=created_at.isoformat(),
        expires_at=(created_at + timedelta(seconds=ttl)).isoformat(),
    ).to_dict()
