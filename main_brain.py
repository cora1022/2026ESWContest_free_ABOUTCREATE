import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from hardware import RobotHardware
from actions import RobotActions

WAKE_WORDS = ["명령시작", "명령 시작", "명령을시작", "명령을 시작"]
EXIT_WORDS = ["종료", "꺼져", "끝내", "프로그램 종료", "그만"]


def normalize(text):
    return text.replace(" ", "").strip()


def is_wake_word(text):
    t = normalize(text)
    return any(normalize(word) in t for word in WAKE_WORDS)


def is_exit_command(text):
    t = normalize(text)
    return any(normalize(word) in t for word in EXIT_WORDS)


def listen_command_with_retry(hw, retry_count=2):
    for attempt in range(1, retry_count + 1):
        hw.command_led_on()
        try:
            command = hw.listen_korean(
                max_seconds=8.0,
                silence_after=1.2,
                wait_timeout=8.0,
                hard_limit_seconds=30.0,
                keep_recording_while_voice=True,
            )
        finally:
            hw.command_led_off()

        if command:
            return command

        if attempt < retry_count:
            hw.speak("잘 못 들었어요. 다시 말씀해주세요.")
            time.sleep(0.25)

    return ""


def main():
    hw = RobotHardware()
    actions = RobotActions(hw)

    try:
        # 명령 시작 대기 중에는 LED OFF
        hw.command_led_off()
        hw.speak("로봇이 켜졌습니다. 명령 시작이라고 말하면 준비할게요.")
        print("✅ 대기 모드 시작")
        print("👉 '명령 시작' 대기 중에는 LED OFF")
        print("👉 실제 명령 듣는 중에는 LED ON")
        print("👉 명령 처리 중에는 LED BLINK")

        while True:
            print("\n👂 대기 중... '명령 시작'을 기다립니다. LED는 꺼져 있습니다.")
            hw.command_led_off()
            wake_text = hw.listen_korean(
                max_seconds=3.0,
                silence_after=0.6,
                wait_timeout=8.0,
                hard_limit_seconds=4.0,
                keep_recording_while_voice=False,
            )

            if not wake_text:
                continue
            if is_exit_command(wake_text):
                hw.speak("프로그램을 종료할게요.")
                break
            if not is_wake_word(wake_text):
                continue

            hw.speak("네, 말씀해주세요.")
            time.sleep(0.25)
            command = listen_command_with_retry(hw, retry_count=2)

            if not command:
                print("🤫 명령이 들리지 않아 대기 모드로 돌아갑니다.")
                hw.command_led_off()
                continue

            print(f"🚀 최종 명령: {command}")

            if is_exit_command(command):
                hw.speak("프로그램을 종료할게요.")
                break

            hw.start_led_blink()
            try:
                actions.handle_command(command)
            finally:
                hw.stop_led_blink()
                hw.command_led_off()

    except KeyboardInterrupt:
        print("\n🧹 사용자가 종료했습니다.")
        hw.speak("종료합니다.")
    finally:
        hw.cleanup()


if __name__ == "__main__":
    main()
