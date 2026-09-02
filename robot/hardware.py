"""Backward-compatible imports for the packaged hardware implementation."""

from robot_app.config import RobotSettings
from robot_app.hardware.audio import clean_tts_text
from robot_app.hardware.facade import RobotHardware
from robot_app.hardware.gpio_runtime import GPIO, GPIO_AVAILABLE


_SETTINGS = RobotSettings.from_env()
IN1 = _SETTINGS.gpio.motor_in1
IN2 = _SETTINGS.gpio.motor_in2
IN3 = _SETTINGS.gpio.motor_in3
IN4 = _SETTINGS.gpio.motor_in4
ULTRASONIC_TRIG = _SETTINGS.gpio.ultrasonic_trig
ULTRASONIC_ECHO = _SETTINGS.gpio.ultrasonic_echo
COMMAND_LED_PIN = _SETTINGS.gpio.command_led
AUDIO_DEVICE = _SETTINGS.audio.input_device
AUDIO_OUTPUT_DEVICE = _SETTINGS.audio.output_device
AUDIO_SAMPLE_RATE = _SETTINGS.audio.sample_rate
AUDIO_CHANNELS = _SETTINGS.audio.channels
AUDIO_WIDTH_BYTES = _SETTINGS.audio.width_bytes
AUDIO_CHUNK_MS = _SETTINGS.audio.chunk_ms
AUDIO_MIN_ENERGY = _SETTINGS.audio.min_energy
AUDIO_NOISE_MULTIPLIER = _SETTINGS.audio.noise_multiplier
AUDIO_DEBUG = _SETTINGS.audio.debug
AUDIO_ERROR_BACKOFF_SEC = _SETTINGS.audio.error_backoff_sec
AUDIO_ERROR_LOG_INTERVAL_SEC = _SETTINGS.audio.error_log_interval_sec
USE_TTS = _SETTINGS.audio.use_tts
TTS_VOLUME = _SETTINGS.audio.tts_volume
TTS_TIMEOUT_SEC = _SETTINGS.audio.tts_timeout_sec
TTS_CACHE_DIR = _SETTINGS.audio.tts_cache_dir
CAMERA_INDEX = _SETTINGS.camera.index
CAMERA_WIDTH = _SETTINGS.camera.width
CAMERA_HEIGHT = _SETTINGS.camera.height
CAMERA_JPEG_QUALITY = _SETTINGS.camera.jpeg_quality
CAMERA_INPUT_FORMAT = _SETTINGS.camera.input_format
CAMERA_INPUT_FPS = _SETTINGS.camera.input_fps
CAMERA_AUTOFOCUS = _SETTINGS.camera.autofocus
CAMERA_WARMUP_FRAMES = _SETTINGS.camera.warmup_frames
CAMERA_CAPTURE_FLUSH_FRAMES = _SETTINGS.camera.flush_frames
ULTRASONIC_ENABLED = _SETTINGS.ultrasonic.enabled
SAFE_DISTANCE_CM = _SETTINGS.ultrasonic.safe_distance_cm
ULTRASONIC_STOP_CM = _SETTINGS.ultrasonic.stop_distance_cm
ULTRASONIC_TIMEOUT_IS_CLEAR = _SETTINGS.ultrasonic.timeout_is_clear
SENSOR_FAIL_DISTANCE_CM = _SETTINGS.ultrasonic.sensor_fail_distance_cm


__all__ = ["RobotHardware", "clean_tts_text"]
