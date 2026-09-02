from __future__ import annotations

import threading
import time

from robot_app.config import GpioSettings, UltrasonicSettings
from robot_app.hardware.gpio_runtime import GpioRuntime


class UltrasonicSensor:
    def __init__(
        self,
        runtime: GpioRuntime,
        gpio_settings: GpioSettings,
        settings: UltrasonicSettings,
    ) -> None:
        self.runtime = runtime
        self.trig_pin = gpio_settings.ultrasonic_trig
        self.echo_pin = gpio_settings.ultrasonic_echo
        self.settings = settings
        self._lock = threading.Lock()

    def measure_cm(self) -> float:
        with self._lock:
            return self._read_distance_cm()

    def _read_distance_cm(self) -> float:
        if not self.settings.enabled:
            if self.runtime.ready:
                print("⚠️ 초음파 센서가 비활성화되어 안전상 0cm 처리.")
                return self.settings.sensor_fail_distance_cm
            print("📏 [GPIO 없는 개발 모드] 테스트용 거리: 100cm")
            return 100.0
        if not self.runtime.ready:
            print("📏 [가상 센서] 전방 거리: 100cm")
            return 100.0

        readings: list[float] = []
        timeout_count = 0
        stuck_high_count = 0
        for _ in range(3):
            distance, status = self.get_once()
            if status == "ok" and distance is not None:
                readings.append(distance)
            elif status == "timeout":
                timeout_count += 1
            elif status == "stuck_high":
                stuck_high_count += 1
            time.sleep(0.04)

        if readings:
            readings.sort()
            distance_cm = readings[len(readings) // 2]
            print(f"📏 전방 거리: {distance_cm:.1f}cm")
            return float(distance_cm)
        if stuck_high_count > 0:
            print("⚠️ 초음파 ECHO가 처음부터 HIGH입니다. 안전상 0cm 처리.")
            return self.settings.sensor_fail_distance_cm
        if timeout_count > 0:
            if self.settings.timeout_is_clear:
                print(f"📏 초음파 반사 없음. 설정에 따라 {self.settings.max_distance_cm:.0f}cm 처리.")
                return self.settings.max_distance_cm
            print("⚠️ 초음파 반사 없음. 원격 주행 안전상 0cm 처리.")
            return self.settings.sensor_fail_distance_cm
        print("⚠️ 초음파 측정 실패. 안전상 0cm 처리.")
        return self.settings.sensor_fail_distance_cm

    def get_once(self) -> tuple[float | None, str]:
        try:
            if self.runtime.input(self.echo_pin) == 1:
                time.sleep(0.002)
                if self.runtime.input(self.echo_pin) == 1:
                    return None, "stuck_high"

            self.runtime.output(self.trig_pin, False)
            time.sleep(0.0002)
            self.runtime.output(self.trig_pin, True)
            time.sleep(0.00001)
            self.runtime.output(self.trig_pin, False)

            timeout = time.monotonic() + 0.03
            while self.runtime.input(self.echo_pin) == 0:
                if time.monotonic() > timeout:
                    return None, "timeout"
            start = time.monotonic()

            timeout = start + 0.03
            while self.runtime.input(self.echo_pin) == 1:
                if time.monotonic() > timeout:
                    return None, "timeout"
            end = time.monotonic()

            distance_cm = (end - start) * 34300 / 2
            if distance_cm < 2 or distance_cm > 400:
                return None, "timeout"
            return float(distance_cm), "ok"
        except Exception as exc:
            print(f"⚠️ 거리 측정 실패: {exc}")
            return None, "fail"
