from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from robot_app.actions.planner import CommandPlanner, clean_reply_text
from robot_app.config import RobotSettings
from robot_app.domain.ports import HardwarePort
from robot_app.intelligence.gemini import GeminiGateway


_DEFAULT_SETTINGS = RobotSettings.from_env()
GEMINI_MODEL = _DEFAULT_SETTINGS.ai.model
GEMINI_TIMEOUT_MS = _DEFAULT_SETTINGS.ai.timeout_ms
MOVE_SEC = _DEFAULT_SETTINGS.motion.move_sec
BACKWARD_SEC = _DEFAULT_SETTINGS.motion.backward_sec
TURN_SEC = _DEFAULT_SETTINGS.motion.turn_sec
TURN_AROUND_SEC = _DEFAULT_SETTINGS.motion.turn_around_sec
OBJECT_SEARCH_TURN_SEC = _DEFAULT_SETTINGS.motion.object_search_turn_sec
OBJECT_ALIGN_TURN_SEC = _DEFAULT_SETTINGS.motion.object_align_turn_sec
TARGET_STOP_DISTANCE_CM = _DEFAULT_SETTINGS.motion.target_stop_distance_cm
ULTRASONIC_STOP_CM = _DEFAULT_SETTINGS.ultrasonic.stop_distance_cm
MUSIC_DIR = _DEFAULT_SETTINGS.music_dir


class RobotActions:
    """Public action facade coordinating planning, AI and hardware operations."""

    def __init__(
        self,
        hardware: HardwarePort,
        settings: RobotSettings | None = None,
        *,
        gateway: GeminiGateway | None = None,
        planner: CommandPlanner | None = None,
    ) -> None:
        self.hw = hardware
        self.settings = settings or RobotSettings.from_env()
        self._cancel = threading.Event()
        self.gateway = gateway or GeminiGateway(self.settings.ai)
        self.planner = planner or CommandPlanner(self.gateway)
        self.client = self.gateway.client

    def cancel_current(self) -> None:
        self._cancel.set()

    def reset_cancel(self) -> None:
        self._cancel.clear()

    def _require_gemini(self) -> None:
        self.gateway.require_client()

    def _gemini_text(self, prompt: str) -> str:
        return self.gateway.text(prompt)

    def _gemini_vision(self, prompt: str, image_path: str | Path) -> str:
        return self.gateway.vision(prompt, image_path)

    def _extract_json(self, text: str) -> dict:
        return self.gateway.extract_json(text)

    def decide_command(self, command: str) -> dict[str, Any]:
        return self.planner.decide(command)

    def _normalize_decision(self, data: dict[str, Any], command: str) -> dict[str, Any]:
        return self.planner.normalize_decision(data, command)

    def _safe_repeat(self, value: object) -> int:
        return self.planner.safe_repeat(value)

    def _extract_repeat(self, text: str, default: int = 1) -> int:
        return self.planner.extract_repeat(text, default)

    def _split_sequence(self, command: str) -> list[str]:
        return self.planner.split_sequence(command)

    def _fallback_decide(self, command: str) -> dict[str, Any]:
        return self.planner.fallback_decide(command)

    def _fallback_conditional(self, command: str) -> dict[str, Any] | None:
        return self.planner.fallback_conditional(command)

    def _fallback_step(self, text: str) -> dict[str, Any] | None:
        return self.planner.fallback_step(text)

    def _make_sequence_reply(self, steps: list[dict[str, Any]]) -> str:
        return self.planner.make_sequence_reply(steps)

    def handle_command(self, command: str) -> None:
        self.reset_cancel()
        decision = self.decide_command(command)
        reply = clean_reply_text(decision.get("reply", "알겠습니다.")) or "알겠습니다."
        steps = decision.get("steps", [])
        if reply:
            self.hw.speak(reply)
        self.execute_steps(steps, original_command=command)

    def execute_steps(self, steps: list[dict[str, Any]], original_command: str = "") -> None:
        for index, step in enumerate(steps, start=1):
            if self._cancel.is_set():
                self.hw.stop_motors()
                print("현재 행동이 정지 요청으로 취소됐습니다.")
                return
            action = step.get("action", "UNKNOWN")
            repeat = self._safe_repeat(step.get("repeat", 1))
            print(f"🧩 단계 {index}/{len(steps)}: {action} x{repeat}")
            if action == "CONDITIONAL_ACTION":
                self.execute_conditional(step)
                continue
            if action == "PLAY_MUSIC":
                self.handle_music_mode(original_command)
                continue
            if action in ["VISION_QUESTION", "GENERAL_QUESTION", "DISTANCE_QUESTION", "GO_TO_OBJECT"]:
                self._execute_step(step, original_command)
                continue
            for repeat_index in range(repeat):
                if self._cancel.is_set():
                    self.hw.stop_motors()
                    return
                if repeat > 1:
                    print(f"   ↳ 반복 {repeat_index + 1}/{repeat}")
                self._execute_step(step, original_command)
                time.sleep(0.15)

    def _execute_step(self, step: dict[str, Any], original_command: str = "") -> None:
        action = step.get("action", "UNKNOWN")
        object_name = step.get("object_name", "")
        motion = self.settings.motion
        if action == "MOVE_FORWARD":
            self.hw.move_forward(motion.move_sec)
        elif action == "MOVE_UNTIL_OBSTACLE":
            distance = self.hw.move_forward_until_obstacle(
                stop_cm=self.settings.ultrasonic.stop_distance_cm
            )
            if distance is not None:
                self.hw.speak(f"앞에 약 {int(distance)}센티미터 남기고 멈췄어요.")
        elif action == "MOVE_BACKWARD":
            self.hw.move_backward(motion.backward_sec)
        elif action == "TURN_LEFT":
            self.hw.turn_left(motion.turn_sec)
        elif action == "TURN_RIGHT":
            self.hw.turn_right(motion.turn_sec)
        elif action == "TURN_AROUND":
            self.hw.turn_around(motion.turn_around_sec)
        elif action == "STOP":
            self.hw.stop_motors()
        elif action == "DISTANCE_QUESTION":
            distance = self.hw.get_distance_cm()
            self.hw.speak(f"앞쪽은 약 {int(distance)}센티미터 정도 떨어져 있어요.")
        elif action == "GO_TO_OBJECT":
            self.go_to_object(object_name or "물체")
        elif action == "VISION_QUESTION":
            self.answer_vision_question(original_command, object_name=object_name)
        elif action == "GENERAL_QUESTION":
            self.answer_general_question(original_command)
        else:
            self.hw.speak("그 동작은 아직 실행할 수 없어요.")

    def execute_conditional(self, step: dict[str, Any]) -> None:
        condition_type = step.get("condition_type", "vision")
        matched = False
        if condition_type == "distance":
            distance = self.hw.get_distance_cm()
            operator = step.get("distance_operator", "<")
            target = float(step.get("distance_cm") or self.settings.ultrasonic.stop_distance_cm)
            matched = distance < target if operator in ["<", "less_than"] else distance > target
        else:
            image_path = None
            try:
                image_path = self.hw.capture_image()
                question = step.get("condition_question") or "사진에서 사용자의 조건이 참인가?"
                prompt = f"""
로봇의 현재 전방 시야만 보고 조건이 참인지 판단해라.
앞 단계의 이동이나 회전이 있었다면 이미 끝난 상태다. 미래 예측이나 이전 위치 추측은 하지 마라.
조건: {question}
반드시 JSON 하나만 반환해라.
{{"matched": true/false, "reason": "짧은 한국어 이유"}}
reason에는 사진, 이미지, 화면, 카메라라는 단어를 쓰지 마라.
"""
                result = self._extract_json(self._gemini_vision(prompt, image_path))
                matched = bool(result.get("matched", False))
                reason = clean_reply_text(result.get("reason", ""))
                print(f"🔎 조건 판단: matched={matched}, reason={reason}")
            except Exception as exc:
                print(f"❌ 조건 판단 실패: {exc}")
                matched = False
            finally:
                self._safe_remove(image_path)

        if matched:
            self.hw.speak("조건이 맞아요. 실행할게요.")
            then_step = {
                "action": step.get("then_action", "UNKNOWN"),
                "object_name": step.get("then_object_name", ""),
                "repeat": step.get("repeat", 1),
            }
            self.execute_steps([then_step])
        else:
            self.hw.speak(
                clean_reply_text(step.get("else_reply"))
                or "조건이 맞지 않아서 실행하지 않을게요."
            )

    def answer_vision_question(self, question: str, object_name: str = "") -> None:
        image_path = None
        try:
            image_path = self.hw.capture_image()
            if object_name:
                prompt = f"""
너는 로봇의 현재 전방 시야를 직접 보고 있다.
앞 단계의 이동과 회전은 이미 끝났으므로, 오직 지금 보이는 현재 장면만 기준으로 판단해라.
미래 예측, 이전 위치 추측, '돌면 보일 것이다/없을 것이다' 같은 가정은 절대 하지 마라.

확인 대상: {object_name}

반드시 JSON 하나만 반환해라.
{{
  "visible": true 또는 false,
  "confidence": 0.0부터 1.0,
  "answer": "로봇이 사용자에게 말할 짧은 한국어 대사"
}}

answer 작성 규칙:
- '사진', '이미지', '화면', '카메라'라는 단어를 쓰지 마라.
- 로봇이 직접 보고 말하듯이 답해라.
- 보이면: '제 앞에 {object_name}가 보여요.' 또는 자연스러운 비슷한 문장으로 답해라.
- 안 보이면: '제 앞에는 {object_name}가 안 보여요.'라고 답해라.
- 보인다고 판단했으면 뒤에 반대로 부정하는 문장을 붙이지 마라.
"""
                result = self._extract_json(self._gemini_vision(prompt, image_path))
                visible = bool(result.get("visible", False))
                answer = clean_reply_text(result.get("answer", ""))
                if not answer:
                    answer = (
                        f"제 앞에 {object_name}가 보여요."
                        if visible
                        else f"제 앞에는 {object_name}가 안 보여요."
                    )
                self.hw.speak(answer)
                return

            prompt = f"""
너는 로봇의 현재 전방 시야를 직접 보고 있다.
앞 단계의 이동과 회전은 이미 끝났으므로, 오직 지금 보이는 현재 장면만 기준으로 답해라.
사용자의 전체 명령문에 포함된 이동 지시는 이미 수행된 것으로 보고, 마지막 확인 질문에만 답해라.
미래 예측이나 이전 위치 추측은 하지 마라.

사용자 질문: {question}

반드시 JSON 하나만 반환해라.
{{"answer": "로봇이 사용자에게 말할 짧은 한국어 대사"}}

answer 작성 규칙:
- '사진', '이미지', '화면', '카메라'라는 단어를 쓰지 마라.
- 별표, 따옴표, 마크다운, 괄호 속 행동 설명 없이 TTS용 대사만 넣어라.
- 로봇이 직접 보고 말하듯이 '제 앞에...', '제가 보기에는...' 같은 말투로 답해라.
"""
            result = self._extract_json(self._gemini_vision(prompt, image_path))
            self.hw.speak(
                clean_reply_text(result.get("answer", ""))
                or "제가 보기에는 확실하지 않아요."
            )
        except Exception as exc:
            print(f"❌ 시각 질문 처리 실패: {exc}")
            self.hw.speak("확인하는 중 문제가 생겼어요.")
        finally:
            self._safe_remove(image_path)

    def answer_general_question(self, question: str) -> None:
        try:
            reply = self._gemini_text(
                f"별표, 따옴표, 마크다운 없이 TTS용 한국어 대사만 짧게 답해줘. 질문: {question}"
            )
            self.hw.speak(clean_reply_text(reply))
        except Exception as exc:
            print(f"❌ 일반 질문 처리 실패: {exc}")
            self.hw.speak("질문에 답하는 중 문제가 생겼어요.")

    def go_to_object(self, object_name: str, max_steps: int = 7) -> None:
        motion = self.settings.motion
        self.hw.speak(f"{object_name}를 찾아서 가볼게요.")
        for step_index in range(1, max_steps + 1):
            if self._cancel.is_set():
                self.hw.stop_motors()
                return
            distance = self.hw.get_distance_cm()
            if distance <= motion.target_stop_distance_cm:
                self.hw.stop_motors()
                self.hw.speak(f"{object_name} 앞에 도착한 것 같아요.")
                return
            image_path = None
            try:
                image_path = self.hw.capture_image()
                navigation = self._analyze_object_navigation(object_name, image_path)
                print(f"🧭 이동 판단 {step_index}/{max_steps}:", navigation)
                if not navigation.get("visible", False):
                    self.hw.turn_left(motion.object_search_turn_sec)
                    continue
                position = navigation.get("position", "unknown")
                if position == "left":
                    self.hw.turn_left(motion.object_align_turn_sec)
                elif position == "right":
                    self.hw.turn_right(motion.object_align_turn_sec)
                else:
                    self.hw.move_forward(motion.move_sec)
            except Exception as exc:
                print(f"❌ 물체 접근 실패: {exc}")
                self.hw.stop_motors()
                self.hw.speak("이동 중 문제가 생겨서 멈출게요.")
                return
            finally:
                self._safe_remove(image_path)
        self.hw.stop_motors()
        self.hw.speak("안전을 위해 여기서 멈출게요.")

    def _analyze_object_navigation(self, object_name: str, image_path: str | Path) -> dict:
        prompt = f"""
로봇의 현재 전방 시야다. 목표 물체는 '{object_name}'이다.
JSON 하나만 반환해라.
{{"visible": true/false, "position": "left/center/right/unknown", "reason": "짧은 이유"}}
"""
        return self._extract_json(self._gemini_vision(prompt, image_path))

    def handle_music_mode(self, command: str = "") -> None:
        compact = command.replace(" ", "")
        if "프리렌" in compact:
            playlist = [
                ("좋아요. 프리렌 음악을 들려드릴게요.", "프리렌 하이라이트.mp3"),
                ("이번에는 모차르트의 아이네입니다.", "모차르트 하이라이트.mp3"),
            ]
        else:
            playlist = [
                ("알겠습니다. 모차르트의 아이네입니다.", "모차르트 하이라이트.mp3"),
                ("좋아요. 이번에는 프리렌 음악을 들려드릴게요.", "프리렌 하이라이트.mp3"),
            ]
        index = 0
        while index < len(playlist):
            intro, filename = playlist[index]
            self.hw.speak(intro)
            self.hw.play_audio_file(self.settings.music_dir / filename)
            self.hw.speak("더 재생할까요?")
            self.hw.command_led_on()
            try:
                answer = self.hw.listen_korean(
                    max_seconds=4.0,
                    silence_after=0.8,
                    wait_timeout=6.0,
                )
            finally:
                self.hw.command_led_off()
            compact_answer = answer.replace(" ", "")
            if not answer:
                self.hw.speak("대답이 없어서 음악 모드를 종료할게요.")
                return
            if any(word in compact_answer for word in ["그만", "멈춰", "정지", "아니", "아니요", "끝"]):
                self.hw.speak("네, 알겠습니다.")
                return
            if any(word in compact_answer for word in ["다른거", "다른것", "다음", "더", "응", "그래", "좋아"]):
                index += 1
                continue
            self.hw.speak("네, 알겠습니다.")
            return
        self.hw.speak("준비된 음악은 여기까지예요.")

    @staticmethod
    def _safe_remove(path: str | Path | None) -> None:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass


__all__ = [
    "BACKWARD_SEC",
    "GEMINI_MODEL",
    "GEMINI_TIMEOUT_MS",
    "MOVE_SEC",
    "MUSIC_DIR",
    "OBJECT_ALIGN_TURN_SEC",
    "OBJECT_SEARCH_TURN_SEC",
    "RobotActions",
    "TARGET_STOP_DISTANCE_CM",
    "TURN_AROUND_SEC",
    "TURN_SEC",
    "ULTRASONIC_STOP_CM",
    "clean_reply_text",
]
