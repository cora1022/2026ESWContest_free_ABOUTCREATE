import time

from robot_core.controller import RobotController


class FakeHardware:
    def __init__(self, distance=100.0):
        self.distance = distance
        self.motion = "STOPPED"
        self.speech_listener = None

    def get_distance_cm(self):
        return self.distance

    def start_continuous_motion(self, direction):
        self.motion = direction

    def stop_motors(self):
        self.motion = "STOPPED"

    def capture_image(self):
        raise AssertionError("not used")

    def capture_jpeg(self, quality=None):
        return b"\xff\xd8\xff\xd9"

    def set_speech_listener(self, listener):
        self.speech_listener = listener


class FakeActions:
    def __init__(self):
        self.cancelled = False
        self.commands = []

    def cancel_current(self):
        self.cancelled = True

    def reset_cancel(self):
        self.cancelled = False

    def handle_command(self, text):
        self.commands.append(text)


def command(action, duration_ms=300):
    return {"id": f"test-{action}", "action": action, "duration_ms": duration_ms}


def test_remote_drive_expires_and_stops():
    hardware = FakeHardware()
    controller = RobotController(hardware, FakeActions())
    controller.start()
    try:
        result = controller.handle_remote_message(command("FORWARD", 250))
        assert result["status"] == "accepted"
        assert hardware.motion == "FORWARD"
        time.sleep(0.4)
        assert hardware.motion == "STOPPED"
    finally:
        controller.shutdown()


def test_obstacle_blocks_forward():
    hardware = FakeHardware(distance=12.0)
    controller = RobotController(hardware, FakeActions())
    result = controller.handle_remote_message(command("FORWARD"))
    assert result["status"] == "rejected"
    assert result["reason"] == "obstacle_detected"
    assert hardware.motion == "STOPPED"


def test_remote_disconnect_stops_active_motion_immediately():
    hardware = FakeHardware()
    controller = RobotController(hardware, FakeActions())
    controller.set_remote_connected(True)
    controller.handle_remote_message(command("RIGHT", 1000))
    assert hardware.motion == "RIGHT"

    controller.set_remote_connected(False)

    assert hardware.motion == "STOPPED"
    assert controller.telemetry_snapshot(sample_distance=False)["remote_control_active"] is False


def test_local_text_still_works_without_server():
    actions = FakeActions()
    controller = RobotController(FakeHardware(), actions)
    assert controller.execute_local_text("앞으로 가") is True
    assert actions.commands == ["앞으로 가"]


def test_remote_video_stream_emits_frames_and_stops():
    hardware = FakeHardware()
    controller = RobotController(hardware, FakeActions())
    events = []
    controller.set_event_listener(events.append)
    controller.start()
    try:
        result = controller.handle_remote_message(command("VIDEO_START", 8000))
        assert result["status"] == "accepted"
        time.sleep(0.1)
        assert any(event.get("type") == "camera" and event.get("stream") is True for event in events)
        assert any(event.get("image_bytes") == b"\xff\xd8\xff\xd9" for event in events if event.get("type") == "camera")
        assert controller.telemetry_snapshot(sample_distance=False)["video_active"] is True

        result = controller.handle_remote_message(command("VIDEO_STOP"))
        assert result["status"] == "completed"
        assert controller.telemetry_snapshot(sample_distance=False)["video_active"] is False
    finally:
        controller.shutdown()


def test_robot_speech_is_published_for_frontend_caption():
    hardware = FakeHardware()
    controller = RobotController(hardware, FakeActions())
    events = []
    controller.set_event_listener(events.append)

    hardware.speech_listener("테스트 안내입니다.", b"ID3-test", "audio/mpeg")

    assert events[-1]["type"] == "speech"
    assert events[-1]["text"] == "테스트 안내입니다."
    assert events[-1]["audio_content_type"] == "audio/mpeg"
    assert events[-1]["audio_b64"]
