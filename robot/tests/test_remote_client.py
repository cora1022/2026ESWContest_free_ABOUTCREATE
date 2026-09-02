import asyncio
import json

import pytest

from robot_core.remote_client import RobotRemoteClient
from robot_app.infrastructure.outbound_buffer import OutboundBuffer
from robot_app.config import RemoteSettings
from robot_protocol.messages import HelloAckMessage
from robot_protocol.version import PROTOCOL_VERSION


class RecordingController:
    def __init__(self):
        self.events = []

    def set_remote_connected(self, connected):
        self.events.append(("connected", connected))


class HandshakeWebSocket:
    def __init__(self, response):
        self.response = response
        self.sent = []

    async def send(self, payload):
        self.sent.append(payload)

    async def recv(self):
        return json.dumps(self.response)


def drain(queue):
    items = []
    while not queue.empty():
        item = queue.get_nowait()
        queue.task_done()
        items.append(item)
    return items


def test_stream_queue_keeps_only_latest_camera_frame():
    queue = asyncio.Queue(maxsize=5)
    RobotRemoteClient._put_event(queue, {"type": "status", "event": "ready"})
    RobotRemoteClient._put_event(queue, {"type": "camera", "stream": True, "image_bytes": b"old"})
    RobotRemoteClient._put_event(queue, {"type": "camera", "stream": True, "image_bytes": b"latest"})

    items = drain(queue)

    assert [item["type"] for item in items] == ["status", "camera"]
    assert items[-1]["image_bytes"] == b"latest"


def test_telemetry_queue_keeps_only_latest_snapshot():
    queue = asyncio.Queue(maxsize=5)
    RobotRemoteClient._put_event(queue, {"type": "telemetry", "distance_cm": 100})
    RobotRemoteClient._put_event(queue, {"type": "telemetry", "distance_cm": 80})

    items = drain(queue)

    assert items == [{"type": "telemetry", "distance_cm": 80}]


@pytest.mark.asyncio
async def test_priority_event_is_sent_before_camera_frame():
    client = RobotRemoteClient(object())
    client._buffer = OutboundBuffer()
    client._buffer.put({"type": "camera", "stream": True, "image_bytes": b"frame"})
    client._buffer.put({"type": "command_result", "status": "completed"})

    queue, event = await client._next_outgoing_event()
    queue.task_done()

    assert event["type"] == "command_result"


@pytest.mark.asyncio
async def test_blocked_websocket_send_forces_reconnect():
    class SlowWebSocket:
        async def send(self, _payload):
            await asyncio.sleep(1)

    client = RobotRemoteClient(object())
    client.send_timeout = 0.01
    client._buffer = OutboundBuffer()
    client._buffer.put({"type": "status", "event": "ready"})

    with pytest.raises(ConnectionError, match="송신"):
        await client._send_loop(SlowWebSocket())


@pytest.mark.asyncio
async def test_valid_hello_ack_connects_before_normal_loops_start():
    controller = RecordingController()
    settings = RemoteSettings(
        server_url="wss://robot.example/ws/robot",
        robot_token="test-token",
        enabled=True,
    )
    client = RobotRemoteClient(controller, settings)
    websocket = HandshakeWebSocket(
        HelloAckMessage(server_time=123.5, protocol_version=PROTOCOL_VERSION).to_dict()
    )

    async def receive_loop(_websocket):
        controller.events.append(("loop", "receive"))

    async def send_loop(_websocket):
        controller.events.append(("loop", "send"))

    async def telemetry_loop():
        controller.events.append(("loop", "telemetry"))

    client._receive_loop = receive_loop
    client._send_loop = send_loop
    client._telemetry_loop = telemetry_loop

    await client._run_connected_session(websocket)

    hello = json.loads(websocket.sent[0])
    assert hello["type"] == "hello"
    assert hello["protocol_version"] == PROTOCOL_VERSION
    assert controller.events[0] == ("connected", True)
    assert {event for event in controller.events[1:]} == {
        ("loop", "receive"),
        ("loop", "send"),
        ("loop", "telemetry"),
    }


@pytest.mark.asyncio
async def test_incompatible_hello_ack_reconnects_without_marking_connected():
    controller = RecordingController()
    settings = RemoteSettings(
        server_url="wss://robot.example/ws/robot",
        robot_token="test-token",
        enabled=True,
    )
    client = RobotRemoteClient(controller, settings)
    websocket = HandshakeWebSocket(
        {
            "type": "hello_ack",
            "server_time": 123.5,
            "protocol_version": PROTOCOL_VERSION + 99,
        }
    )
    loops_started = []

    async def forbidden_loop(*_args):
        loops_started.append(True)

    client._receive_loop = forbidden_loop
    client._send_loop = forbidden_loop
    client._telemetry_loop = forbidden_loop

    with pytest.raises(ConnectionError, match="hello_ack 검증 실패"):
        await client._run_connected_session(websocket)

    assert controller.events == []
    assert loops_started == []
