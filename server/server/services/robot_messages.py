from __future__ import annotations

import base64
import time
from typing import Any

from server.services.robot_hub import RobotHub


async def consume_robot_message(hub: RobotHub, message: dict[str, Any]) -> None:
    message_type = message.get("type")
    if message_type == "telemetry":
        hub.state.update(message)
        hub.state.update({"online": True, "last_seen": time.time()})
        location = message.get("location")
        if location and location.get("latitude") is not None and location.get("longitude") is not None:
            point = dict(location)
            point["server_time"] = time.time()
            hub.locations.append(point)
        await hub.broadcast({"type": "state", "state": hub.state})
        return

    if message_type == "camera":
        image = message.get("binary_payload")
        if image is None:
            try:
                image = base64.b64decode(message.get("image_b64") or "", validate=True)
            except Exception:
                await hub.record({"type": "camera_rejected", "reason": "invalid_base64"})
                return
        if not image or len(image) > 2_000_000:
            await hub.record({"type": "camera_rejected", "reason": "invalid_size"})
            return
        hub.camera_image = image
        hub.camera_time = time.time()
        if not bool(message.get("stream")):
            await hub.record({"type": "camera_updated", "bytes": len(image)})
        await hub.broadcast_bytes(image)
        return

    if message_type == "speech":
        text = str(message.get("text") or "").strip()
        if not text:
            return
        audio_b64 = str(message.get("audio_b64") or "")
        audio_content_type = str(message.get("audio_content_type") or "audio/mpeg")
        if audio_content_type not in {"audio/mpeg", "audio/wav", "audio/ogg"}:
            audio_b64 = ""
            audio_content_type = "audio/mpeg"
        if audio_b64:
            try:
                audio = base64.b64decode(audio_b64, validate=True)
                if not audio or len(audio) > 2_000_000:
                    audio_b64 = ""
            except Exception:
                audio_b64 = ""

        speech_event = {
            "type": "speech",
            "robot_id": str(message.get("robot_id") or hub.settings.robot_id),
            "text": text[:500],
            "timestamp": message.get("timestamp") or time.time(),
        }
        await hub.record(speech_event, broadcast_event=False)
        await hub.broadcast(
            {
                **speech_event,
                "audio_b64": audio_b64,
                "audio_content_type": audio_content_type,
            }
        )
        return

    if message_type in {"command_result", "status"}:
        await hub.record(message)
