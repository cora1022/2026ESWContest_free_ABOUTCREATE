from robot_app.config import RobotSettings


def test_settings_parse_named_audio_devices_and_remote_limits():
    settings = RobotSettings.from_env(
        {
            "AUDIO_DEVICE": "plughw:CARD=CAMERA,DEV=0",
            "AUDIO_OUTPUT_DEVICE": "plughw:CARD=UACDemoV10,DEV=0",
            "ROBOT_SERVER_URL": "wss://robot.example/ws/robot",
            "REMOTE_VIDEO_FPS": "99",
            "REMOTE_VIDEO_JPEG_QUALITY": "100",
            "REMOTE_SEND_TIMEOUT_SEC": "0.1",
            "REMOTE_HANDSHAKE_TIMEOUT_SEC": "0.1",
        }
    )

    assert settings.audio.input_device == "plughw:CARD=CAMERA,DEV=0"
    assert settings.audio.output_device == "plughw:CARD=UACDemoV10,DEV=0"
    assert settings.remote.enabled is True
    assert settings.remote.video_fps == 8.0
    assert settings.remote.video_jpeg_quality == 90
    assert settings.remote.send_timeout_sec == 1.0
    assert settings.remote.handshake_timeout_sec == 1.0


def test_settings_keep_disabled_ultrasonic_fail_closed():
    settings = RobotSettings.from_env({"ULTRASONIC_ENABLED": "0"})

    assert settings.ultrasonic.enabled is False
    assert settings.ultrasonic.sensor_fail_distance_cm == 0.0
