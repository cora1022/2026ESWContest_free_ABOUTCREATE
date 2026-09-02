from __future__ import annotations

import threading

from robot_app.config import GpioSettings
from robot_app.hardware.gpio_runtime import GpioRuntime


DIRECTION_STATES: dict[str, tuple[int, int, int, int]] = {
    "FORWARD": (0, 1, 1, 0),
    "BACKWARD": (1, 0, 0, 1),
    "LEFT": (0, 1, 0, 1),
    "RIGHT": (1, 0, 1, 0),
}


class MotorDriver:
    def __init__(self, runtime: GpioRuntime, settings: GpioSettings) -> None:
        self.runtime = runtime
        self.settings = settings
        self._cancel = threading.Event()
        self._write_lock = threading.Lock()

    def write(self, in1: int, in2: int, in3: int, in4: int) -> None:
        with self._write_lock:
            if not self.runtime.ready:
                print(f"[TEST MOTOR] IN1={in1}, IN2={in2}, IN3={in3}, IN4={in4}")
                return
            pins = (
                self.settings.motor_in1,
                self.settings.motor_in2,
                self.settings.motor_in3,
                self.settings.motor_in4,
            )
            for pin, value in zip(pins, (in1, in2, in3, in4)):
                self.runtime.output(pin, bool(value))

    def stop(self) -> None:
        self._cancel.set()
        self.write(0, 0, 0, 0)
        print("🛑 모터 정지")

    def start_continuous(self, direction: str) -> None:
        direction = str(direction or "").upper()
        if direction not in DIRECTION_STATES:
            self.stop()
            raise ValueError(f"알 수 없는 이동 방향: {direction}")
        self._cancel.clear()
        self.write(*DIRECTION_STATES[direction])

    def run_timed(self, direction: str, seconds: float) -> bool:
        return self.run_timed_states(DIRECTION_STATES[direction], seconds)

    def run_timed_states(self, states: tuple[int, int, int, int], seconds: float) -> bool:
        seconds = max(0.0, min(float(seconds), 12.0))
        self._cancel.clear()
        self.write(*states)
        cancelled = self._cancel.wait(seconds)
        self.stop()
        return not cancelled

    def move_backward(self, seconds: float = 0.6) -> bool:
        print(f"⬇️ 후진 {seconds:.2f}초")
        return self.run_timed("BACKWARD", seconds)

    def turn_left(self, seconds: float = 4.0) -> bool:
        print(f"↩️ 좌회전 {seconds:.2f}초")
        return self.run_timed("LEFT", seconds)

    def turn_right(self, seconds: float = 4.0) -> bool:
        print(f"↪️ 우회전 {seconds:.2f}초")
        return self.run_timed("RIGHT", seconds)

    def turn_around(self, seconds: float = 8.0) -> bool:
        print(f"🔄 뒤로 돌기 {seconds:.2f}초")
        return self.turn_right(seconds)
