"""Binary WebSocket framing shared by the robot and relay server."""

from __future__ import annotations

import json
import struct
from typing import Any


MAGIC = b"RBT1"
HEADER = struct.Struct("!4sI")
MAX_METADATA_BYTES = 16_384
MAX_PAYLOAD_BYTES = 2_500_000


def pack_binary_event(event: dict[str, Any], payload: bytes) -> bytes:
    payload = bytes(payload)
    if not payload or len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("바이너리 페이로드 크기가 올바르지 않습니다.")
    metadata = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if not metadata or len(metadata) > MAX_METADATA_BYTES:
        raise ValueError("바이너리 메타데이터 크기가 올바르지 않습니다.")
    return HEADER.pack(MAGIC, len(metadata)) + metadata + payload


def unpack_binary_event(packet: bytes) -> tuple[dict[str, Any], bytes]:
    packet = bytes(packet)
    if len(packet) < HEADER.size:
        raise ValueError("바이너리 패킷이 너무 짧습니다.")
    magic, metadata_size = HEADER.unpack_from(packet)
    if magic != MAGIC or not 0 < metadata_size <= MAX_METADATA_BYTES:
        raise ValueError("바이너리 패킷 헤더가 올바르지 않습니다.")
    payload_offset = HEADER.size + metadata_size
    if payload_offset >= len(packet):
        raise ValueError("바이너리 페이로드가 없습니다.")
    payload = packet[payload_offset:]
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("바이너리 페이로드가 너무 큽니다.")
    metadata = json.loads(packet[HEADER.size:payload_offset].decode("utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("바이너리 메타데이터가 객체가 아닙니다.")
    return metadata, payload
