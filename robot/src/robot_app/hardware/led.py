from __future__ import annotations

import threading

from robot_app.config import GpioSettings
from robot_app.hardware.gpio_runtime import GpioRuntime


class CommandLed:
    def __init__(self, runtime: GpioRuntime, settings: GpioSettings) -> None:
        self.runtime = runtime
        self.pin = settings.command_led
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def _set(self, value: bool) -> None:
        self.runtime.output(self.pin, value)

    def on(self) -> None:
        self.stop_blink(force_message=False)
        self._set(True)
        print("💡 LED ON")

    def off(self) -> None:
        self.stop_blink(force_message=False)
        self._set(False)
        print("💡 LED OFF")

    def start_blink(self, interval: float = 0.25) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def blink_loop() -> None:
            state = False
            while not self._stop.is_set():
                state = not state
                self._set(state)
                self._stop.wait(interval)
            self._set(False)

        self._thread = threading.Thread(target=blink_loop, name="command-led", daemon=True)
        self._thread.start()
        print("💡 LED BLINK START")

    def stop_blink(self, force_message: bool = True) -> None:
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join(timeout=1.0)
            self._thread = None
            if force_message:
                print("💡 LED BLINK STOP")
        self._set(False)
