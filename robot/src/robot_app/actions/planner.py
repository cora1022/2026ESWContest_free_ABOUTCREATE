from __future__ import annotations

import re
from typing import Any

from robot_app.intelligence.gemini import GeminiGateway


NUMBER_WORDS = {
    "한": 1,
    "하나": 1,
    "한번": 1,
    "일": 1,
    "두": 2,
    "둘": 2,
    "이": 2,
    "세": 3,
    "셋": 3,
    "삼": 3,
    "네": 4,
    "넷": 4,
    "사": 4,
    "다섯": 5,
    "오": 5,
    "여섯": 6,
    "육": 6,
    "일곱": 7,
    "칠": 7,
    "여덟": 8,
    "팔": 8,
    "아홉": 9,
    "구": 9,
    "열": 10,
    "십": 10,
}


def clean_reply_text(text: object) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"^\s*[-•]\s*", "", value, flags=re.MULTILINE)
    for char in ['*', '"', "'", "“", "”", "‘", "’", "「", "」", "『", "』"]:
        value = value.replace(char, "")
    value = re.sub(
        r"\([^)]*(?:재생|mp3|wav|파일|카메라|촬영|분석|동작|행동)[^)]*\)",
        "",
        value,
        flags=re.IGNORECASE,
    )
    replacements = {
        "사진에서": "제 앞에",
        "사진에는": "제 앞에는",
        "사진 속에는": "제 앞에는",
        "사진 속에": "제 앞에",
        "사진을 보면": "제가 보기에는",
        "이미지에서": "제 앞에",
        "이미지에는": "제 앞에는",
        "화면에서": "제 앞에",
        "화면에는": "제 앞에는",
        "카메라 화면에서": "제 앞에",
        "카메라 화면에는": "제 앞에는",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = value.replace("보이기는 합니다만", "보여요.")
    return re.sub(r"\s+", " ", value).strip()


class CommandPlanner:
    def __init__(self, gateway: GeminiGateway) -> None:
        self.gateway = gateway

    def decide(self, command: str) -> dict[str, Any]:
        prompt = f"""
너는 라즈베리파이 RC카 로봇의 한국어 명령 분류기다.
반드시 JSON 하나만 반환해라.
reply, else_reply, reason에는 스피커로 그대로 말해도 되는 짧은 한국어 대사만 넣어라.
별표, 따옴표, 마크다운, 괄호 속 행동 설명, 파일명, JSON 밖 설명은 절대 넣지 마라.

중요: 사용자가 여러 동작을 말하면 steps 배열에 순서대로 넣어라.
예:
- "앞으로 두 칸 가고 뒤로 한번 돌아" => MOVE_FORWARD repeat 2, TURN_AROUND repeat 1
- "앞으로 네 번 가 봐" => MOVE_FORWARD repeat 4
- "왼쪽으로 두 번 돌고 앞으로 한 번 가" => TURN_LEFT repeat 2, MOVE_FORWARD repeat 1

가능한 step action:
- MOVE_FORWARD: 짧게 앞으로 이동
- MOVE_UNTIL_OBSTACLE: 카메라 없이 초음파만 보고 장애물 직전까지 전진
- MOVE_BACKWARD: 짧게 뒤로 이동
- TURN_LEFT: 왼쪽으로 회전
- TURN_RIGHT: 오른쪽으로 회전
- TURN_AROUND: 180도 회전. "뒤로 돌아"는 이것이다.
- STOP: 정지
- GO_TO_OBJECT: 특정 물체 앞까지 이동
- DISTANCE_QUESTION: 앞 거리 질문
- VISION_QUESTION: 카메라로 현재 로봇의 앞을 보고 답해야 하는 질문. 특정 물체가 보이는지 묻는 경우 object_name에 물체명을 넣어라.
- GENERAL_QUESTION: 일반 질문
- CONDITIONAL_ACTION: "~이면 ~해" 조건부 명령
- PLAY_MUSIC: 음악 재생
- UNKNOWN

반환 형식:
{{
  "reply": "TTS로 바로 말할 짧은 한국어 대사",
  "steps": [
    {{"action":"MOVE_FORWARD", "repeat":2, "object_name":"", "condition_question":"", "then_action":""}}
  ]
}}

조건부 명령 예:
"내가 진라면을 들고 있으면 앞으로 와 봐" =>
{{"reply":"조건을 확인하고 실행할게요.", "steps":[{{"action":"CONDITIONAL_ACTION", "condition_type":"vision", "condition_question":"사진에서 사용자가 진라면을 들고 있나?", "then_action":"MOVE_FORWARD", "repeat":1, "else_reply":"조건이 맞지 않아요."}}]}}

명령: {command}
"""
        try:
            data = self.gateway.extract_json(self.gateway.text(prompt))
            decision = self.normalize_decision(data, command)
            print("🧠 Gemini 판단:", decision)
            return decision
        except Exception as exc:
            print(f"⚠️ Gemini 명령 분류 실패, 규칙 기반으로 대체합니다: {exc}")
            return self.fallback_decide(command)

    def normalize_decision(self, data: dict[str, Any], command: str) -> dict[str, Any]:
        if "steps" not in data:
            action = data.get("action", "UNKNOWN")
            step = dict(data)
            step["action"] = action
            step["repeat"] = self.extract_repeat(command, default=int(step.get("repeat") or 1))
            data = {"reply": data.get("reply", "알겠습니다."), "steps": [step]}
        data["reply"] = clean_reply_text(data.get("reply", "알겠습니다.")) or "알겠습니다."
        clean_steps = []
        for step in data.get("steps", []):
            if not isinstance(step, dict):
                continue
            step.setdefault("action", "UNKNOWN")
            step.setdefault("object_name", "")
            for key in ["else_reply", "reason", "reply"]:
                if key in step:
                    step[key] = clean_reply_text(step.get(key))
            step["repeat"] = self.safe_repeat(step.get("repeat", 1))
            clean_steps.append(step)
        if not clean_steps:
            return self.fallback_decide(command)
        if len(clean_steps) == 1 and clean_steps[0].get("repeat", 1) == 1:
            action = clean_steps[0].get("action")
            if action in ["MOVE_FORWARD", "MOVE_BACKWARD", "TURN_LEFT", "TURN_RIGHT", "TURN_AROUND"]:
                clean_steps[0]["repeat"] = self.extract_repeat(command, default=1)
        data["steps"] = clean_steps
        return data

    @staticmethod
    def safe_repeat(value: object) -> int:
        try:
            repeat = int(value)
        except Exception:
            repeat = 1
        return max(1, min(repeat, 10))

    def extract_repeat(self, text: str, default: int = 1) -> int:
        compact = text.replace(" ", "")
        match = re.search(r"(\d+)(번|칸|회)", compact)
        if match:
            return self.safe_repeat(match.group(1))
        for word, count in sorted(NUMBER_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(fr"{word}(번|칸|회)", compact):
                return count
        return default

    @staticmethod
    def split_sequence(command: str) -> list[str]:
        text = command.replace(",", " ")
        return [part.strip() for part in re.split(r"하고|그리고|그다음|다음에|다음", text) if part.strip()]

    def fallback_decide(self, command: str) -> dict[str, Any]:
        conditional = self.fallback_conditional(command)
        if conditional:
            return conditional
        compact = command.replace(" ", "")
        if any(word in compact for word in ["음악", "노래", "클래식", "모차르트", "프리렌"]):
            return {
                "reply": "음악을 틀어드릴게요.",
                "steps": [{"action": "PLAY_MUSIC", "repeat": 1, "object_name": ""}],
            }
        steps = [step for part in self.split_sequence(command) if (step := self.fallback_step(part))]
        if not steps:
            step = self.fallback_step(command)
            if step:
                steps.append(step)
        if not steps:
            return {
                "reply": "명령을 정확히 이해하지 못했어요.",
                "steps": [{"action": "UNKNOWN", "repeat": 1, "object_name": ""}],
            }
        return {"reply": self.make_sequence_reply(steps), "steps": steps}

    def fallback_conditional(self, command: str) -> dict[str, Any] | None:
        compact = command.replace(" ", "")
        markers = ["있으면", "보이면", "들고있으면", "라면", "이면", "면은"]
        marker = next((item for item in markers if item in compact), None)
        if not marker:
            return None
        index = compact.find(marker)
        condition_raw = compact[: index + len(marker)]
        then_raw = compact[index + len(marker) :]
        then_step = self.fallback_step(then_raw) or {"action": "UNKNOWN", "repeat": 1, "object_name": ""}
        step = {
            "action": "CONDITIONAL_ACTION",
            "condition_type": "vision",
            "condition_question": f"사진에서 다음 조건이 참인가? 조건: {condition_raw}",
            "then_action": then_step.get("action", "UNKNOWN"),
            "then_object_name": then_step.get("object_name", ""),
            "repeat": then_step.get("repeat", 1),
            "else_reply": "조건이 맞지 않아요.",
        }
        return {"reply": "조건을 확인하고 실행할게요.", "steps": [step]}

    def fallback_step(self, text: str) -> dict[str, Any] | None:
        compact = text.replace(" ", "")
        repeat = self.extract_repeat(text, default=1)
        if any(word in compact for word in ["멈춰", "정지", "스톱", "그만"]):
            return {"action": "STOP", "repeat": 1, "object_name": ""}
        if any(word in compact for word in ["거리", "얼마나가까", "몇센티"]):
            return {"action": "DISTANCE_QUESTION", "repeat": 1, "object_name": ""}
        vision_words = [
            "보여",
            "보이니",
            "보이는",
            "뭐가있",
            "무엇이있",
            "보고",
            "카메라",
            "설명해",
            "말해봐",
            "말해줘",
            "몇개",
            "몇개야",
            "쓰고",
            "입고",
            "정답",
            "문제",
            "종이",
        ]
        if any(word in compact for word in vision_words):
            return {"action": "VISION_QUESTION", "repeat": 1, "object_name": ""}
        if any(word in compact for word in ["부딪히기직전", "닿기전", "장애물앞", "앞으로계속", "계속가"]):
            return {"action": "MOVE_UNTIL_OBSTACLE", "repeat": 1, "object_name": ""}
        object_words = ["진라면", "음료수", "박스", "상자", "컵", "사람", "의자", "책", "종이", "손가락"]
        for object_name in object_words:
            if object_name in text and any(word in compact for word in ["앞까지", "가줘", "가봐", "다가"]):
                return {"action": "GO_TO_OBJECT", "repeat": 1, "object_name": object_name}
        if "왼" in compact:
            return {"action": "TURN_LEFT", "repeat": repeat, "object_name": ""}
        if "오른" in compact:
            return {"action": "TURN_RIGHT", "repeat": repeat, "object_name": ""}
        if "뒤로돌" in compact or ("뒤로" in compact and "돌" in compact) or "180" in compact:
            return {"action": "TURN_AROUND", "repeat": repeat, "object_name": ""}
        if "뒤" in compact or "후진" in compact:
            return {"action": "MOVE_BACKWARD", "repeat": repeat, "object_name": ""}
        if "앞" in compact or "전진" in compact or "와" in compact:
            return {"action": "MOVE_FORWARD", "repeat": repeat, "object_name": ""}
        return None

    @staticmethod
    def make_sequence_reply(steps: list[dict[str, Any]]) -> str:
        if len(steps) == 1:
            step = steps[0]
            action = step.get("action")
            repeat = step.get("repeat", 1)
            if action == "MOVE_FORWARD":
                return f"앞으로 {repeat}번 이동할게요." if repeat > 1 else "앞으로 갈게요."
            if action == "MOVE_BACKWARD":
                return f"뒤로 {repeat}번 이동할게요." if repeat > 1 else "뒤로 갈게요."
            if action == "TURN_AROUND":
                return f"뒤로 {repeat}번 돌게요." if repeat > 1 else "뒤로 돌게요."
            return "알겠습니다."
        return f"알겠습니다. {len(steps)}개의 동작을 순서대로 실행할게요."
