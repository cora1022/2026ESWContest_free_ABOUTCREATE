import asyncio
import json

import pytest
from fastapi import HTTPException

from server.config import Settings
from server.services.event_log import EventLog
from server.services.robot_hub import RobotHub
from server.services.sessions import SessionStore


class RecordingDashboard:
    def __init__(self):
        self.messages = []
        self.frames = []
        self.closed = asyncio.Event()
        self.close_code = None

    async def send_json(self, payload):
        self.messages.append(payload)

    async def send_bytes(self, payload):
        self.frames.append(payload)

    async def close(self, code=1000, reason=""):
        self.close_code = code
        self.closed.set()


class BlockingRobot:
    def __init__(self):
        self.closed = False
        self.close_code = None

    async def send_json(self, payload):
        await asyncio.Future()

    async def close(self, code=1000, reason=""):
        self.closed = True
        self.close_code = code


class StalledDashboard(RecordingDashboard):
    def __init__(self):
        super().__init__()
        self.send_started = asyncio.Event()

    async def send_bytes(self, payload):
        self.send_started.set()
        await asyncio.Future()


class CoalescingDashboard(RecordingDashboard):
    def __init__(self):
        super().__init__()
        self.send_started = asyncio.Event()
        self.release_first_frame = asyncio.Event()

    async def send_bytes(self, payload):
        if not self.frames:
            self.send_started.set()
            await self.release_first_frame.wait()
        self.frames.append(payload)


def test_event_log_removes_binary_and_secret_media_fields(tmp_path):
    path = tmp_path / "events.jsonl"
    log = EventLog(path)

    event = asyncio.run(
        log.append(
            {
                "type": "speech",
                "text": "안전한 기록",
                "audio_b64": "secret-audio",
                "image_b64": "secret-image",
                "binary_payload": b"secret-bytes",
            }
        )
    )

    assert "audio_b64" not in event
    assert "image_b64" not in event
    assert "binary_payload" not in event
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["text"] == "안전한 기록"


def test_session_store_revokes_session():
    sessions = SessionStore(session_hours=1)
    token, expires_at = sessions.create()

    assert sessions.valid(token)
    assert sessions.expires_at(token) == expires_at

    sessions.revoke(token)
    assert not sessions.valid(token)


def test_robot_send_timeout_closes_and_broadcasts_offline(tmp_path):
    async def scenario():
        settings = Settings(
            robot_token="r" * 24,
            dashboard_key="d" * 12,
            event_log_path=tmp_path / "events.jsonl",
            websocket_send_timeout=0.02,
        )
        hub = RobotHub(settings, EventLog(settings.event_log_path))
        robot = BlockingRobot()
        dashboard = RecordingDashboard()
        hub.add_dashboard(dashboard, "session")
        await hub.replace_robot(robot)
        hub.state.update({"distance_cm": 42, "obstacle": False})
        hub.camera_image = b"stale-frame"

        with pytest.raises(HTTPException) as error:
            await hub.send_command({"type": "command", "action": "STOP"})

        for _ in range(100):
            if any(message.get("type") == "state" for message in dashboard.messages):
                break
            await asyncio.sleep(0.002)

        assert error.value.status_code == 503
        assert robot.closed is True
        assert robot.close_code == 1011
        assert hub.robot is None
        assert hub.state["online"] is False
        assert "distance_cm" not in hub.state
        assert hub.camera_image is None
        assert any(event.get("type") == "robot_disconnected" for event in hub.events)
        assert any(
            message.get("type") == "state" and message["state"]["online"] is False
            for message in dashboard.messages
        )
        await hub.shutdown()

    asyncio.run(scenario())


def test_stalled_dashboard_never_blocks_broadcast_and_is_closed(tmp_path):
    async def scenario():
        settings = Settings(
            robot_token="r" * 24,
            dashboard_key="d" * 12,
            event_log_path=tmp_path / "events.jsonl",
            websocket_send_timeout=0.02,
        )
        hub = RobotHub(settings, EventLog(settings.event_log_path))
        dashboard = StalledDashboard()
        peer = hub.add_dashboard(dashboard, "session")

        await asyncio.wait_for(hub.broadcast_bytes(b"frame"), timeout=0.01)
        await asyncio.wait_for(dashboard.send_started.wait(), timeout=0.1)
        await asyncio.wait_for(dashboard.closed.wait(), timeout=0.2)

        assert peer.closed.is_set()
        assert dashboard.close_code == 1011
        assert dashboard not in hub.dashboards

    asyncio.run(scenario())


def test_dashboard_camera_queue_keeps_only_latest_waiting_frame(tmp_path):
    async def scenario():
        settings = Settings(
            robot_token="r" * 24,
            dashboard_key="d" * 12,
            event_log_path=tmp_path / "events.jsonl",
            websocket_send_timeout=0.5,
        )
        hub = RobotHub(settings, EventLog(settings.event_log_path))
        dashboard = CoalescingDashboard()
        hub.add_dashboard(dashboard, "session")

        await hub.broadcast_bytes(b"frame-1")
        await asyncio.wait_for(dashboard.send_started.wait(), timeout=0.1)
        await hub.broadcast_bytes(b"frame-2")
        await hub.broadcast_bytes(b"frame-3")
        dashboard.release_first_frame.set()

        for _ in range(100):
            if len(dashboard.frames) == 2:
                break
            await asyncio.sleep(0.002)

        assert dashboard.frames == [b"frame-1", b"frame-3"]
        await hub.shutdown()

    asyncio.run(scenario())
