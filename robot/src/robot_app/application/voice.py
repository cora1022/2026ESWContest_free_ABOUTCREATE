from __future__ import annotations

import time


WAKE_WORDS = ["명령시작", "명령 시작", "명령을시작", "명령을 시작"]
EXIT_WORDS = ["종료", "꺼져", "끝내", "프로그램 종료", "그만"]


def normalize(text: object) -> str:
    return str(text or "").replace(" ", "").strip()


def is_wake_word(text: object) -> bool:
    normalized = normalize(text)
    return any(normalize(word) in normalized for word in WAKE_WORDS)


def is_exit_command(text: object) -> bool:
    normalized = normalize(text)
    return any(normalize(word) in normalized for word in EXIT_WORDS)


def listen_command_with_retry(hardware, retry_count: int = 2) -> str:
    for attempt in range(1, retry_count + 1):
        hardware.command_led_on()
        try:
            command = hardware.listen_korean(
                max_seconds=8.0,
                silence_after=1.2,
                wait_timeout=8.0,
                hard_limit_seconds=30.0,
                keep_recording_while_voice=True,
            )
        finally:
            hardware.command_led_off()
        if command:
            return command
        if attempt < retry_count:
            hardware.speak("잘 못 들었어요. 다시 말씀해주세요.")
            time.sleep(0.25)
    return ""


def run_voice_loop(hardware, controller) -> None:
    hardware.command_led_off()
    hardware.speak("로봇이 켜졌습니다. 명령 시작이라고 말하면 준비할게요.")
    print("로컬 음성 모드와 VPS 원격 모드가 함께 시작됐습니다.")
    while True:
        print("\n대기 중... '명령 시작'을 기다립니다.")
        hardware.command_led_off()
        wake_text = hardware.listen_korean(
            max_seconds=3.0,
            silence_after=0.6,
            wait_timeout=8.0,
            hard_limit_seconds=4.0,
            keep_recording_while_voice=False,
        )
        if not wake_text:
            time.sleep(0.5)
            continue
        if is_exit_command(wake_text):
            hardware.speak("프로그램을 종료할게요.")
            return
        if not is_wake_word(wake_text):
            continue

        hardware.speak("네, 말씀해주세요.")
        time.sleep(0.25)
        command = listen_command_with_retry(hardware, retry_count=2)
        if not command:
            print("명령이 들리지 않아 대기 모드로 돌아갑니다.")
            continue
        if is_exit_command(command):
            hardware.speak("프로그램을 종료할게요.")
            return

        print(f"최종 로컬 명령: {command}")
        hardware.start_led_blink()
        try:
            if not controller.execute_local_text(command):
                hardware.speak("지금은 휴대폰 원격 제어 중이라 명령을 실행하지 않을게요.")
        finally:
            hardware.stop_led_blink()
            hardware.command_led_off()
