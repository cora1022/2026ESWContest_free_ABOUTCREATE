"""Raspberry Pi와 L298N만 사용하는 간단한 전진/후진 주행 테스트."""

import time

import RPi.GPIO as GPIO


# BCM GPIO 번호와 L298N 입력 핀 연결
IN1 = 5
IN2 = 6
IN3 = 16
IN4 = 26

DRIVE_SECONDS = 1.0
STOP_SECONDS = 1.0


def set_motor_pins(in1, in2, in3, in4):
    """IN1~IN4에 순서대로 HIGH(1) 또는 LOW(0)를 출력한다."""
    GPIO.output(IN1, GPIO.HIGH if in1 else GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH if in2 else GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH if in3 else GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH if in4 else GPIO.LOW)


def forward():
    """양쪽 모터를 전진 방향으로 구동한다."""
    print("전진")
    set_motor_pins(0, 1, 1, 0)


def backward():
    """양쪽 모터를 후진 방향으로 구동한다."""
    print("후진")
    set_motor_pins(1, 0, 0, 1)


def stop():
    """L298N 입력을 모두 LOW로 설정해 모터를 정지한다."""
    print("정지")
    set_motor_pins(0, 0, 0, 0)


def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for pin in (IN1, IN2, IN3, IN4):
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)


def main():
    gpio_ready = False

    try:
        setup_gpio()
        gpio_ready = True

        forward()
        time.sleep(DRIVE_SECONDS)

        stop()
        time.sleep(STOP_SECONDS)

        backward()
        time.sleep(DRIVE_SECONDS)

        stop()
        print("주행 테스트 완료")
    except KeyboardInterrupt:
        print("\n사용자가 테스트를 중단했습니다.")
    finally:
        if gpio_ready:
            stop()
            GPIO.cleanup((IN1, IN2, IN3, IN4))
            print("GPIO 정리 완료")


if __name__ == "__main__":
    main()
