from robot_app.config import GpioSettings, RobotSettings, UltrasonicSettings
from robot_app.hardware.facade import RobotHardware
from robot_app.hardware.motor import DIRECTION_STATES, MotorDriver
from robot_app.hardware.ultrasonic import UltrasonicSensor


class FakeRuntime:
    def __init__(self, ready: bool) -> None:
        self.ready = ready
        self.outputs = []

    def output(self, pin, value):
        self.outputs.append((pin, value))

    def input(self, _pin):
        return 0

    def setup(self):
        pass

    def cleanup(self):
        self.ready = False


def test_disabled_ultrasonic_blocks_real_gpio_forward():
    settings = UltrasonicSettings(enabled=False)
    sensor = UltrasonicSensor(FakeRuntime(True), GpioSettings(), settings)

    assert sensor.measure_cm() == settings.sensor_fail_distance_cm


def test_disabled_ultrasonic_keeps_virtual_development_distance():
    sensor = UltrasonicSensor(
        FakeRuntime(False),
        GpioSettings(),
        UltrasonicSettings(enabled=False),
    )

    assert sensor.measure_cm() == 100.0


def test_forward_motor_mapping_matches_physical_wiring():
    runtime = FakeRuntime(True)
    settings = GpioSettings()
    motor = MotorDriver(runtime, settings)

    motor.start_continuous("FORWARD")

    expected = list(
        zip(
            (
                settings.motor_in1,
                settings.motor_in2,
                settings.motor_in3,
                settings.motor_in4,
            ),
            (False, True, True, False),
        )
    )
    assert DIRECTION_STATES["FORWARD"] == (0, 1, 1, 0)
    assert runtime.outputs == expected


def test_hardware_facade_blocks_forward_when_sensor_reports_obstacle():
    runtime = FakeRuntime(True)
    hardware = RobotHardware(RobotSettings(), gpio_runtime=runtime, initialize=False)
    hardware.ultrasonic.measure_cm = lambda: 10.0
    started = []
    hardware.motor.run_timed = lambda *_args: started.append(True) or True

    assert hardware.move_forward(0.1) is False
    assert started == []
    assert runtime.outputs[-4:] == [
        (5, False),
        (6, False),
        (16, False),
        (26, False),
    ]
