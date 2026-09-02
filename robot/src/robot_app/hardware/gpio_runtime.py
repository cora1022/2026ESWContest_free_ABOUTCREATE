from __future__ import annotations

from robot_app.config import GpioSettings

try:
    import RPi.GPIO as GPIO

    GPIO_AVAILABLE = True
except Exception:
    GPIO = None
    GPIO_AVAILABLE = False


class GpioRuntime:
    """Own GPIO setup and cleanup so individual devices cannot clean up each other."""

    def __init__(self, settings: GpioSettings, gpio_module=None) -> None:
        self.settings = settings
        self.gpio = GPIO if gpio_module is None else gpio_module
        self.ready = False

    def setup(self) -> None:
        if self.ready:
            return
        if self.gpio is None:
            print("⚠️ RPi.GPIO를 불러오지 못했습니다. 테스트 모드로 동작합니다.")
            return

        gpio = self.gpio
        gpio.setmode(gpio.BCM)
        gpio.setwarnings(False)
        output_pins = [
            self.settings.motor_in1,
            self.settings.motor_in2,
            self.settings.motor_in3,
            self.settings.motor_in4,
            self.settings.ultrasonic_trig,
            self.settings.command_led,
        ]
        for pin in output_pins:
            gpio.setup(pin, gpio.OUT)
            gpio.output(pin, gpio.LOW)
        gpio.setup(self.settings.ultrasonic_echo, gpio.IN)
        self.ready = True
        print("✅ 실제 GPIO 하드웨어 모드 활성화")
        print(f"💡 LED: GPIO{self.settings.command_led}")

    def output(self, pin: int, value: bool) -> None:
        if self.ready:
            self.gpio.output(pin, self.gpio.HIGH if value else self.gpio.LOW)

    def input(self, pin: int) -> int:
        if not self.ready:
            return 0
        return int(self.gpio.input(pin))

    def cleanup(self) -> None:
        if not self.ready:
            return
        self.gpio.cleanup()
        self.ready = False
        print("✅ GPIO cleanup 완료")
