"""Protocol identity and compatibility helpers."""

from __future__ import annotations


PROTOCOL_NAME = "rpi-robot-control"
PROTOCOL_VERSION = 1
SUPPORTED_PROTOCOL_VERSIONS = frozenset({PROTOCOL_VERSION})


def is_supported_protocol_version(value: object) -> bool:
    """Return whether *value* is a protocol version this package understands."""

    if isinstance(value, bool):
        return False
    try:
        version = int(value)
    except (TypeError, ValueError):
        return False
    return version in SUPPORTED_PROTOCOL_VERSIONS
