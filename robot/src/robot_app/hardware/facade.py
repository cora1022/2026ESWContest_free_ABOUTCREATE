from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from robot_app.config import RobotSettings
from robot_app.hardware.audio import SpeechAudio
from robot_app.hardware.camera import UsbCamera
from robot_app.hardware.gpio_runtime import GpioRuntime
from robot_app.hardware.led import CommandLed
from robot_app.hardware.motor import MotorDriver
from robot_app.hardware.ultrasonic import UltrasonicSensor


class RobotHardware:
    """Compatibility facade over independently testable Raspberry Pi devices."""

    def __init__(
        self,
        settings: RobotSettings | None = None,
        *,
        gpio_runtime: GpioRuntime | None = None,
        initialize: bool = True,
    ) -> None:
        self.settings = settings or RobotSettings.from_env()
        self.gpio = gpio_runtime or GpioRuntime(self.settings.gpio)
        if initialize:
            self.gpio.setup()
        self.motor = MotorDriver(self.gpio, self.settings.gpio)
        self.led = CommandLed(self.gpio, self.settings.gpio)
        self.ultrasonic = UltrasonicSensor(self.gpio, self.settings.gpio, self.settings.ultrasonic)
        self.camera_device = UsbCamera(self.settings.camera, initialize=initialize)
        self.audio = SpeechAudio(self.settings.audio, initialize=initialize)

    @property
    def gpio_ready(self) -> bool:
        return self.gpio.ready

    @property
    def camera(self):
        return self.camera_device.capture

    @property
    def audio_input_ok(self) -> bool | None:
        return self.audio.input_ok

    @property
    def audio_output_ok(self) -> bool | None:
        return self.audio.output_ok

    def set_speech_listener(self, listener: Callable | None) -> None:
        self.audio.set_speech_listener(listener)

    def setup_gpio(self) -> None:
        self.gpio.setup()

    def _set_led(self, value: bool) -> None:
        self.led._set(value)

    def command_led_on(self) -> None:
        self.led.on()

    def command_led_off(self) -> None:
        self.led.off()

    def start_led_blink(self, interval: float = 0.25) -> None:
        self.led.start_blink(interval)

    def stop_led_blink(self, force_message: bool = True) -> None:
        self.led.stop_blink(force_message)

    def _write_motors(self, in1: int, in2: int, in3: int, in4: int) -> None:
        self.motor.write(in1, in2, in3, in4)

    def stop_motors(self) -> None:
        self.motor.stop()

    def start_continuous_motion(self, direction: str) -> None:
        self.motor.start_continuous(direction)

    def _run_timed_motion(self, states: tuple[int, int, int, int], seconds: float) -> bool:
        return self.motor.run_timed_states(states, seconds)

    def move_forward(self, seconds: float = 0.45) -> bool:
        distance = self.get_distance_cm()
        if distance <= self.settings.ultrasonic.safe_distance_cm:
            self.stop_motors()
            print(f"🚧 전방 {distance:.1f}cm 장애물 감지. 전진 취소.")
            return False
        print(f"⬆️ 전진 {seconds:.2f}초")
        return self.motor.run_timed("FORWARD", seconds)

    def move_backward(self, seconds: float = 0.6) -> bool:
        return self.motor.move_backward(seconds)

    def turn_left(self, seconds: float = 4.0) -> bool:
        return self.motor.turn_left(seconds)

    def turn_right(self, seconds: float = 4.0) -> bool:
        return self.motor.turn_right(seconds)

    def turn_around(self, seconds: float = 8.0) -> bool:
        return self.motor.turn_around(seconds)

    def move_forward_until_obstacle(
        self,
        stop_cm: float | None = None,
        max_seconds: float = 12.0,
    ) -> float | None:
        stop_cm = float(stop_cm or self.settings.ultrasonic.stop_distance_cm)
        print(f"⬆️ 초음파 전용 전진 시작: 정지거리={stop_cm:.1f}cm")
        started_at = time.monotonic()
        last_distance = None
        self.motor._cancel.clear()
        while time.monotonic() - started_at < max_seconds:
            if self.motor._cancel.is_set():
                self.stop_motors()
                return last_distance
            distance = self.get_distance_cm()
            last_distance = distance
            if distance <= stop_cm:
                self.stop_motors()
                return last_distance
            self.motor.write(0, 1, 1, 0)
            time.sleep(0.22)
            self.stop_motors()
            time.sleep(0.06)
        self.stop_motors()
        return last_distance

    def get_distance_cm(self) -> float:
        return self.ultrasonic.measure_cm()

    def _read_distance_cm(self) -> float:
        return self.ultrasonic._read_distance_cm()

    def _get_distance_once(self) -> tuple[float | None, str]:
        return self.ultrasonic.get_once()

    def setup_camera(self) -> None:
        self.camera_device.setup()

    def capture_jpeg(self, quality: int | None = None) -> bytes:
        return self.camera_device.capture_jpeg(quality)

    def capture_image(self, path: str | None = None) -> str:
        return self.camera_device.capture_image(path)

    def setup_audio(self) -> None:
        self.audio.setup()

    def _alsa_device_available(self, command: str, device: str, direction: str) -> bool:
        return self.audio._alsa_device_available(command, device, direction)

    def _audio_error(self, direction: str, detail: object) -> None:
        self.audio._audio_error(direction, detail)

    def _wait_for_audio_retry(self) -> bool:
        return self.audio._wait_for_audio_retry()

    def _record_until_silence_wav(self, path: str, **kwargs) -> str | None:
        return self.audio.record_until_silence_wav(path, **kwargs)

    def listen_korean(self, **kwargs) -> str:
        return self.audio.listen_korean(**kwargs)

    def _player_cmd(self, file_path: str | Path) -> list[str] | None:
        return self.audio.player_command(file_path)

    def play_audio_file(self, file_path: str | Path, timeout: float | None = None) -> bool:
        return self.audio.play_audio_file(file_path, timeout)

    def speak(self, text: object) -> None:
        self.audio.speak(text)

    def _notify_speech(
        self,
        text: str,
        audio_bytes: bytes | None = None,
        audio_content_type: str = "audio/mpeg",
    ) -> None:
        self.audio._notify_speech(text, audio_bytes, audio_content_type)

    def health_snapshot(self) -> dict[str, object]:
        return {
            "gpio_ready": self.gpio_ready,
            "camera_ok": self.camera is not None,
            "audio_input_ok": self.audio_input_ok,
            "audio_output_ok": self.audio_output_ok,
            "ultrasonic_enabled": self.settings.ultrasonic.enabled,
        }

    def cleanup(self) -> None:
        self.stop_led_blink(force_message=False)
        self.command_led_off()
        self.stop_motors()
        self.camera_device.close()
        self.gpio.cleanup()
