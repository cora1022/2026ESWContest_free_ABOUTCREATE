"""Shared command names and duration limits."""

from __future__ import annotations

from enum import Enum


class Action(str, Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    STOP = "STOP"
    TEXT_COMMAND = "TEXT_COMMAND"
    GET_DISTANCE = "GET_DISTANCE"
    CAPTURE_IMAGE = "CAPTURE_IMAGE"
    VIDEO_START = "VIDEO_START"
    VIDEO_STOP = "VIDEO_STOP"


DRIVE_ACTIONS = frozenset(
    {
        Action.FORWARD,
        Action.BACKWARD,
        Action.LEFT,
        Action.RIGHT,
    }
)
QUEUED_ACTION_MEMBERS = frozenset(
    {
        Action.TEXT_COMMAND,
        Action.CAPTURE_IMAGE,
        Action.GET_DISTANCE,
    }
)
VIDEO_ACTION_MEMBERS = frozenset({Action.VIDEO_START, Action.VIDEO_STOP})
ACTION_MEMBERS = frozenset(Action)

# String sets keep migration from the existing applications straightforward.
DIRECTIONS = frozenset(action.value for action in DRIVE_ACTIONS)
QUEUED_ACTIONS = frozenset(action.value for action in QUEUED_ACTION_MEMBERS)
VIDEO_ACTIONS = frozenset(action.value for action in VIDEO_ACTION_MEMBERS)
ALLOWED_ACTIONS = frozenset(action.value for action in ACTION_MEMBERS)

DEFAULT_COMMAND_DURATION_MS = 500
MIN_COMMAND_DURATION_MS = 100
MAX_COMMAND_DURATION_MS = 10_000
MAX_DRIVE_DURATION_MS = 1_000


def parse_action(value: object) -> Action:
    """Normalize a value to an allowed action or raise ``ValueError``."""

    normalized = str(value or "").strip().upper()
    try:
        return Action(normalized)
    except ValueError as exc:
        raise ValueError(f"허용되지 않은 명령입니다: {normalized or value!r}") from exc


def max_duration_ms(action: Action | str) -> int:
    """Return the protocol-level duration ceiling for an action."""

    parsed = action if isinstance(action, Action) else parse_action(action)
    if parsed in DRIVE_ACTIONS or parsed is Action.STOP:
        return MAX_DRIVE_DURATION_MS
    return MAX_COMMAND_DURATION_MS
