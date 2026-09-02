import base64
import time
from contextlib import contextmanager

import pytest
from robot_protocol.transport import pack_binary_event
from robot_protocol.version import PROTOCOL_VERSION
from starlette.websockets import WebSocketDisconnect

@contextmanager
def connected_robot(client):
    with client.websocket_connect("/ws/robot") as robot:
        robot.send_json(
            {
                "type": "hello",
                "robot_id": "robot-01",
                "token": "robot-token-for-tests-123456789",
            }
        )
        hello_ack = robot.receive_json()
        assert hello_ack["type"] == "hello_ack"
        assert hello_ack["protocol_version"] == PROTOCOL_VERSION
        yield robot


def test_robot_receives_phone_command_and_reports_telemetry(client, login):
    login(client)
    with connected_robot(client) as robot:
        response = client.post(
            "/api/command",
            json={"action": "FORWARD", "duration_ms": 650},
        )
        assert response.status_code == 200
        forwarded = robot.receive_json()
        assert forwarded["type"] == "command"
        assert forwarded["action"] == "FORWARD"

        robot.send_json(
            {
                "type": "telemetry",
                "robot_id": "robot-01",
                "mode": "REMOTE",
                "motion": "FORWARD",
                "distance_cm": 88.5,
                "location": {"latitude": 37.5, "longitude": 127.0},
            }
        )
        status = client.get("/api/status").json()["state"]
        assert status["online"] is True
        assert status["distance_cm"] == 88.5

        response = client.post(
            "/api/command",
            json={"action": "VIDEO_START", "duration_ms": 8000},
        )
        assert response.status_code == 200
        forwarded = robot.receive_json()
        assert forwarded["action"] == "VIDEO_START"
        assert forwarded["duration_ms"] == 8000

        robot.send_json(
            {
                "type": "speech",
                "robot_id": "robot-01",
                "text": "로봇 음성 테스트입니다.",
                "audio_b64": base64.b64encode(b"ID3-test").decode("ascii"),
                "audio_content_type": "audio/mpeg",
                "timestamp": time.time(),
            }
        )
        time.sleep(0.05)
        events = client.get("/api/status").json()["events"]
        assert any(
            event.get("type") == "speech" and event.get("text") == "로봇 음성 테스트입니다."
            for event in events
        )
        assert all("audio_b64" not in event for event in events)


def test_binary_camera_frame_is_forwarded_directly_to_dashboard(client, login):
    image = b"\xff\xd8binary-jpeg\xff\xd9"
    login(client)
    with connected_robot(client) as robot:
        with client.websocket_connect("/ws/dashboard") as dashboard:
            assert dashboard.receive_json()["type"] == "state"
            robot.send_bytes(
                pack_binary_event(
                    {"type": "camera", "content_type": "image/jpeg", "stream": True},
                    image,
                )
            )
            for _ in range(3):
                message = dashboard.receive()
                if message.get("bytes") is not None:
                    assert message["bytes"] == image
                    break
            else:
                raise AssertionError("dashboard did not receive the binary camera frame")

        response = client.get("/api/camera/latest")
        assert response.status_code == 200
        assert response.content == image


def test_invalid_robot_token_never_marks_robot_online(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/robot") as robot:
            robot.send_json({"type": "hello", "robot_id": "robot-01", "token": "wrong-token"})
            robot.receive_json()

    assert client.get("/health").json()["robot_online"] is False


def test_unsupported_robot_protocol_version_is_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/robot") as robot:
            robot.send_json(
                {
                    "type": "hello",
                    "robot_id": "robot-01",
                    "token": "robot-token-for-tests-123456789",
                    "protocol_version": PROTOCOL_VERSION + 100,
                }
            )
            robot.receive_json()

    assert client.get("/health").json()["robot_online"] is False


def test_revoked_session_closes_dashboard_websocket(client, login):
    login(client)
    with client.websocket_connect("/ws/dashboard") as dashboard:
        assert dashboard.receive_json()["type"] == "state"

        response = client.delete("/api/session")

        assert response.status_code == 200
        with pytest.raises(WebSocketDisconnect):
            dashboard.receive_json()


def test_expired_session_closes_dashboard_websocket(client, login):
    login(client)
    session_token = client.cookies.get("robot_session")
    with client.websocket_connect("/ws/dashboard") as dashboard:
        assert dashboard.receive_json()["type"] == "state"
        client.app.state.services.sessions.sessions[session_token] = 0

        with pytest.raises(WebSocketDisconnect):
            dashboard.receive_json()
