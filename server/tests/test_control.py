from datetime import datetime, timezone

from server.schemas import CommandRequest, build_command


def test_command_rejected_when_robot_is_offline(client, login):
    login(client)
    response = client.post("/api/command", json={"action": "FORWARD"})
    assert response.status_code == 503


def test_invalid_command_is_rejected_before_forwarding(client, login):
    login(client)
    response = client.post("/api/command", json={"action": "FLY"})
    assert response.status_code == 422
    assert response.json()["detail"] == "허용되지 않은 명령입니다."


def test_motion_command_has_shorter_ttl_than_media_command():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    motion = build_command(CommandRequest(action="forward"), now=now)
    media = build_command(CommandRequest(action="VIDEO_START"), now=now)

    motion_ttl = datetime.fromisoformat(motion["expires_at"]) - now
    media_ttl = datetime.fromisoformat(media["expires_at"]) - now

    assert motion["action"] == "FORWARD"
    assert motion_ttl.total_seconds() == 2
    assert media_ttl.total_seconds() == 15
