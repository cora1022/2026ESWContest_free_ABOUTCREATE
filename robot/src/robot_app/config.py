from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


Env = Mapping[str, str]


def _text(env: Env, name: str, default: str) -> str:
    return str(env.get(name, default)).strip()


def _integer(env: Env, name: str, default: int) -> int:
    return int(_text(env, name, str(default)))


def _number(env: Env, name: str, default: float) -> float:
    return float(_text(env, name, str(default)))


def _flag(env: Env, name: str, default: bool) -> bool:
    return _text(env, name, "1" if default else "0") == "1"


@dataclass(frozen=True)
class GpioSettings:
    motor_in1: int = 5
    motor_in2: int = 6
    motor_in3: int = 16
    motor_in4: int = 26
    ultrasonic_trig: int = 23
    ultrasonic_echo: int = 24
    command_led: int = 25

    @classmethod
    def from_env(cls, env: Env) -> "GpioSettings":
        return cls(
            motor_in1=_integer(env, "L298N_IN1", 5),
            motor_in2=_integer(env, "L298N_IN2", 6),
            motor_in3=_integer(env, "L298N_IN3", 16),
            motor_in4=_integer(env, "L298N_IN4", 26),
            ultrasonic_trig=_integer(env, "ULTRASONIC_TRIG", 23),
            ultrasonic_echo=_integer(env, "ULTRASONIC_ECHO", 24),
            command_led=_integer(env, "COMMAND_LED_PIN", 25),
        )


@dataclass(frozen=True)
class UltrasonicSettings:
    enabled: bool = True
    safe_distance_cm: float = 25.0
    stop_distance_cm: float = 18.0
    timeout_is_clear: bool = False
    max_distance_cm: float = 400.0
    sensor_fail_distance_cm: float = 0.0

    @classmethod
    def from_env(cls, env: Env) -> "UltrasonicSettings":
        return cls(
            enabled=_flag(env, "ULTRASONIC_ENABLED", True),
            safe_distance_cm=_number(env, "SAFE_DISTANCE_CM", 25.0),
            stop_distance_cm=_number(env, "ULTRASONIC_STOP_CM", 18.0),
            timeout_is_clear=_flag(env, "ULTRASONIC_TIMEOUT_IS_CLEAR", False),
            max_distance_cm=_number(env, "ULTRASONIC_MAX_CM", 400.0),
        )


@dataclass(frozen=True)
class CameraSettings:
    index: int = 0
    width: int = 848
    height: int = 480
    jpeg_quality: int = 75
    input_format: str = "MJPG"
    input_fps: int = 30
    autofocus: bool = True
    warmup_frames: int = 12
    flush_frames: int = 1

    @classmethod
    def from_env(cls, env: Env) -> "CameraSettings":
        return cls(
            index=_integer(env, "CAMERA_INDEX", 0),
            width=_integer(env, "CAMERA_WIDTH", 848),
            height=_integer(env, "CAMERA_HEIGHT", 480),
            jpeg_quality=_integer(env, "CAMERA_JPEG_QUALITY", 75),
            input_format=_text(env, "CAMERA_INPUT_FORMAT", "MJPG").upper()[:4],
            input_fps=max(1, _integer(env, "CAMERA_INPUT_FPS", 30)),
            autofocus=_flag(env, "CAMERA_AUTOFOCUS", True),
            warmup_frames=max(0, _integer(env, "CAMERA_WARMUP_FRAMES", 12)),
            flush_frames=max(0, _integer(env, "CAMERA_CAPTURE_FLUSH_FRAMES", 1)),
        )


@dataclass(frozen=True)
class AudioSettings:
    input_device: str = "plughw:CARD=CAMERA,DEV=0"
    output_device: str = "plughw:CARD=UACDemoV10,DEV=0"
    sample_rate: int = 48_000
    channels: int = 1
    width_bytes: int = 2
    chunk_ms: int = 80
    min_energy: int = 430
    noise_multiplier: float = 2.0
    debug: bool = False
    error_backoff_sec: float = 3.0
    error_log_interval_sec: float = 15.0
    use_tts: bool = True
    tts_volume: float = 0.9
    tts_timeout_sec: str = ""
    tts_cache_dir: Path = Path("/tmp/robot_tts_cache")

    @classmethod
    def from_env(cls, env: Env) -> "AudioSettings":
        return cls(
            input_device=_text(env, "AUDIO_DEVICE", "plughw:CARD=CAMERA,DEV=0"),
            output_device=_text(env, "AUDIO_OUTPUT_DEVICE", "plughw:CARD=UACDemoV10,DEV=0"),
            sample_rate=_integer(env, "AUDIO_SAMPLE_RATE", 48_000),
            chunk_ms=_integer(env, "AUDIO_CHUNK_MS", 80),
            min_energy=_integer(env, "AUDIO_MIN_ENERGY", 430),
            noise_multiplier=_number(env, "AUDIO_NOISE_MULTIPLIER", 2.0),
            debug=_flag(env, "AUDIO_DEBUG", False),
            error_backoff_sec=max(2.0, _number(env, "AUDIO_ERROR_BACKOFF_SEC", 3.0)),
            error_log_interval_sec=max(5.0, _number(env, "AUDIO_ERROR_LOG_INTERVAL_SEC", 15.0)),
            use_tts=_flag(env, "USE_TTS", True),
            tts_volume=_number(env, "TTS_VOLUME", 0.9),
            tts_timeout_sec=_text(env, "TTS_TIMEOUT_SEC", ""),
            tts_cache_dir=Path(_text(env, "TTS_CACHE_DIR", "/tmp/robot_tts_cache")),
        )


@dataclass(frozen=True)
class AiSettings:
    model: str = "gemini-2.5-flash"
    timeout_ms: int = 15_000

    @classmethod
    def from_env(cls, env: Env) -> "AiSettings":
        return cls(
            model=_text(env, "GEMINI_MODEL", "gemini-2.5-flash"),
            timeout_ms=max(3_000, _integer(env, "GEMINI_TIMEOUT_MS", 15_000)),
        )


@dataclass(frozen=True)
class MotionSettings:
    move_sec: float = 0.45
    backward_sec: float = 0.6
    turn_sec: float = 1.2
    turn_around_sec: float = 2.0
    object_search_turn_sec: float = 1.0
    object_align_turn_sec: float = 0.8
    target_stop_distance_cm: float = 30.0

    @classmethod
    def from_env(cls, env: Env) -> "MotionSettings":
        return cls(
            move_sec=_number(env, "MOVE_SEC", 0.45),
            backward_sec=_number(env, "BACKWARD_SEC", 0.6),
            turn_sec=_number(env, "TURN_SEC", 1.2),
            turn_around_sec=_number(env, "TURN_AROUND_SEC", 2.0),
            object_search_turn_sec=_number(env, "OBJECT_SEARCH_TURN_SEC", 1.0),
            object_align_turn_sec=_number(env, "OBJECT_ALIGN_TURN_SEC", 0.8),
            target_stop_distance_cm=_number(env, "TARGET_STOP_DISTANCE_CM", 30.0),
        )


@dataclass(frozen=True)
class RemoteSettings:
    server_url: str = ""
    robot_id: str = "robot-01"
    robot_token: str = ""
    enabled: bool = True
    allow_insecure_server: bool = False
    telemetry_interval_sec: float = 1.0
    send_timeout_sec: float = 5.0
    handshake_timeout_sec: float = 10.0
    drive_lease_ms: int = 650
    video_fps: float = 4.0
    video_lease_ms: int = 8_000
    video_jpeg_quality: int = 70

    @classmethod
    def from_env(cls, env: Env) -> "RemoteSettings":
        server_url = _text(env, "ROBOT_SERVER_URL", "")
        return cls(
            server_url=server_url,
            robot_id=_text(env, "ROBOT_ID", "robot-01"),
            robot_token=_text(env, "ROBOT_TOKEN", ""),
            enabled=_flag(env, "REMOTE_ENABLED", True) and bool(server_url),
            allow_insecure_server=_flag(env, "ALLOW_INSECURE_SERVER", False),
            telemetry_interval_sec=max(0.5, _number(env, "TELEMETRY_INTERVAL_SEC", 1.0)),
            send_timeout_sec=max(1.0, _number(env, "REMOTE_SEND_TIMEOUT_SEC", 5.0)),
            handshake_timeout_sec=max(
                1.0,
                _number(env, "REMOTE_HANDSHAKE_TIMEOUT_SEC", 10.0),
            ),
            drive_lease_ms=_integer(env, "REMOTE_DRIVE_LEASE_MS", 650),
            video_fps=max(1.0, min(_number(env, "REMOTE_VIDEO_FPS", 4.0), 8.0)),
            video_lease_ms=max(3_000, min(_integer(env, "REMOTE_VIDEO_LEASE_MS", 8_000), 10_000)),
            video_jpeg_quality=max(30, min(_integer(env, "REMOTE_VIDEO_JPEG_QUALITY", 70), 90)),
        )


@dataclass(frozen=True)
class GnssSettings:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 2947

    @classmethod
    def from_env(cls, env: Env) -> "GnssSettings":
        return cls(
            enabled=_flag(env, "GNSS_ENABLED", False),
            host=_text(env, "GPSD_HOST", "127.0.0.1"),
            port=_integer(env, "GPSD_PORT", 2947),
        )


@dataclass(frozen=True)
class RobotSettings:
    gpio: GpioSettings = field(default_factory=GpioSettings)
    ultrasonic: UltrasonicSettings = field(default_factory=UltrasonicSettings)
    camera: CameraSettings = field(default_factory=CameraSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    ai: AiSettings = field(default_factory=AiSettings)
    motion: MotionSettings = field(default_factory=MotionSettings)
    remote: RemoteSettings = field(default_factory=RemoteSettings)
    gnss: GnssSettings = field(default_factory=GnssSettings)
    music_dir: Path = Path("music")

    @classmethod
    def from_env(cls, env: Env | None = None) -> "RobotSettings":
        source = os.environ if env is None else env
        return cls(
            gpio=GpioSettings.from_env(source),
            ultrasonic=UltrasonicSettings.from_env(source),
            camera=CameraSettings.from_env(source),
            audio=AudioSettings.from_env(source),
            ai=AiSettings.from_env(source),
            motion=MotionSettings.from_env(source),
            remote=RemoteSettings.from_env(source),
            gnss=GnssSettings.from_env(source),
            music_dir=Path(_text(source, "MUSIC_DIR", "music")),
        )
