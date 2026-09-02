"""Connect a laptop to the VPS as a harmless robot simulator."""

import asyncio
import base64
import io
import json
import math
import os
import struct
import time
import wave

from dotenv import load_dotenv
from PIL import Image, ImageDraw
from websockets.asyncio.client import connect

from robot_protocol.messages import HelloAckMessage, HelloMessage
from robot_protocol.transport import pack_binary_event


load_dotenv()


async def main():
    url = os.getenv("ROBOT_SERVER_URL", "wss://181.214.136.80/ws/robot")
    robot_id = os.getenv("ROBOT_ID", "robot-01")
    token = os.getenv("ROBOT_TOKEN", "")
    if not token:
        raise SystemExit("ROBOT_TOKEN을 .env에 설정하세요.")

    state = {"mode": "LOCAL", "motion": "STOPPED", "distance_cm": 120.0, "video_active": False}
    preview = Image.new("RGB", (848, 480), color=(18, 18, 18))
    canvas = ImageDraw.Draw(preview)
    canvas.rectangle((36, 36, 812, 444), outline=(255, 229, 0), width=5)
    canvas.text((64, 64), "SIMULATED ROBOT CAMERA", fill=(255, 229, 0))
    preview_buffer = io.BytesIO()
    preview.save(preview_buffer, format="JPEG", quality=70)
    preview_jpeg = preview_buffer.getvalue()
    tone_buffer = io.BytesIO()
    with wave.open(tone_buffer, "wb") as tone:
        tone.setnchannels(1)
        tone.setsampwidth(2)
        tone.setframerate(16_000)
        samples = [int(2600 * math.sin(2 * math.pi * 660 * index / 16_000)) for index in range(32_000)]
        tone.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    preview_audio_b64 = base64.b64encode(tone_buffer.getvalue()).decode("ascii")
    async with connect(url, max_size=3_000_000) as websocket:
        hello = HelloMessage(robot_id=robot_id, token=token)
        await websocket.send(json.dumps(hello.to_dict()))
        acknowledgement = HelloAckMessage.from_mapping(json.loads(await websocket.recv()))
        print(f"서버 연결 완료: protocol v{acknowledgement.protocol_version}")

        async def telemetry():
            while True:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "telemetry",
                            "robot_id": robot_id,
                            **state,
                            "obstacle": False,
                            "remote_connected": True,
                            "remote_control_active": state["mode"] == "REMOTE",
                            "location": {"latitude": 37.5665, "longitude": 126.9780, "speed_mps": 0.0},
                            "timestamp": time.time(),
                        }
                    )
                )
                await asyncio.sleep(1)

        task = asyncio.create_task(telemetry())
        try:
            async for raw in websocket:
                command = json.loads(raw)
                if command.get("type") != "command":
                    continue
                action = command.get("action")
                state["motion"] = action if action in {"FORWARD", "BACKWARD", "LEFT", "RIGHT"} else "STOPPED"
                state["mode"] = "REMOTE" if state["motion"] != "STOPPED" else "LOCAL"
                if action == "VIDEO_START":
                    state["video_active"] = True
                    await websocket.send(
                        pack_binary_event(
                            {
                                "type": "camera",
                                "content_type": "image/jpeg",
                                "stream": True,
                                "timestamp": time.time(),
                            },
                            preview_jpeg,
                        )
                    )
                elif action == "VIDEO_STOP":
                    state["video_active"] = False
                elif action == "TEXT_COMMAND":
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "speech",
                                "robot_id": robot_id,
                                "text": f"{command.get('text') or '테스트 명령'} 요청을 확인했습니다.",
                                "audio_b64": preview_audio_b64,
                                "audio_content_type": "audio/wav",
                                "timestamp": time.time(),
                            },
                            ensure_ascii=False,
                        )
                    )
                await websocket.send(
                    json.dumps(
                        {
                            "type": "command_result",
                            "robot_id": robot_id,
                            "command_id": command.get("id"),
                            "status": "completed",
                            "reason": f"simulated_{action.lower()}",
                            "timestamp": time.time(),
                        }
                    )
                )
        finally:
            task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
