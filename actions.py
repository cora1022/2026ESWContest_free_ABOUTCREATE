import os
import re
import json
import time
from pathlib import Path

import PIL.Image
from google import genai

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

MOVE_SEC = float(os.getenv("MOVE_SEC", "0.45"))
BACKWARD_SEC = float(os.getenv("BACKWARD_SEC", "0.6"))
TURN_SEC = float(os.getenv("TURN_SEC", "1.2"))
TURN_AROUND_SEC = float(os.getenv("TURN_AROUND_SEC", "2.0"))
OBJECT_SEARCH_TURN_SEC = float(os.getenv("OBJECT_SEARCH_TURN_SEC", "1.0"))
OBJECT_ALIGN_TURN_SEC = float(os.getenv("OBJECT_ALIGN_TURN_SEC", "0.8"))
TARGET_STOP_DISTANCE_CM = float(os.getenv("TARGET_STOP_DISTANCE_CM", "30"))
ULTRASONIC_STOP_CM = float(os.getenv("ULTRASONIC_STOP_CM", "18"))
MUSIC_DIR = Path(os.getenv("MUSIC_DIR", "music"))

NUMBER_WORDS = {
    "한": 1, "하나": 1, "한번": 1, "일": 1,
    "두": 2, "둘": 2, "이": 2,
    "세": 3, "셋": 3, "삼": 3,
    "네": 4, "넷": 4, "사": 4,
    "다섯": 5, "오": 5,
    "여섯": 6, "육": 6,
    "일곱": 7, "칠": 7,
    "여덟": 8, "팔": 8,
    "아홉": 9, "구": 9,
    "열": 10, "십": 10,
}


def clean_reply_text(text):
    text = str(text or "").strip()
    if not text:
        return ""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
    for ch in ['*', '"', "'", "“", "”", "‘", "’", "「", "」", "『", "』"]:
        text = text.replace(ch, "")
    text = re.sub(r"\([^)]*(?:재생|mp3|wav|파일|카메라|촬영|분석|동작|행동)[^)]*\)", "", text, flags=re.IGNORECASE)
    # 로봇이 외부 사진을 설명하는 말투가 아니라, 직접 보고 말하는 말투로 정리
    pov_replacements = {
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
    for src, dst in pov_replacements.items():
        text = text.replace(src, dst)
    text = text.replace("보이기는 합니다만", "보여요.")
    text = re.sub(r"\s+", " ", text).strip()
    return text


class RobotActions:
    def __init__(self, hardware):
        self.hw = hardware
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("⚠️ Gemini API 키가 없습니다. .env 또는 환경변수를 설정하세요.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            print("✅ Gemini 클라이언트 준비 완료")

    # -----------------------------
    # Gemini helpers
    # -----------------------------
    def _require_gemini(self):
        if self.client is None:
            raise RuntimeError("Gemini API 키가 없습니다.")

    def _gemini_text(self, prompt):
        self._require_gemini()
        response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return (response.text or "").strip()

    def _gemini_vision(self, prompt, image_path):
        self._require_gemini()
        image = PIL.Image.open(image_path)
        try:
            response = self.client.models.generate_content(model=GEMINI_MODEL, contents=[prompt, image])
            return (response.text or "").strip()
        finally:
            image.close()

    def _extract_json(self, text):
        text = text.strip()
        text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^```", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            text = match.group(0)
        return json.loads(text)

    # -----------------------------
    # Decision
    # -----------------------------
    def decide_command(self, command):
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
            raw = self._gemini_text(prompt)
            data = self._extract_json(raw)
            decision = self._normalize_decision(data, command)
            print("🧠 Gemini 판단:", decision)
            return decision
        except Exception as e:
            print(f"⚠️ Gemini 명령 분류 실패, 규칙 기반으로 대체합니다: {e}")
            return self._fallback_decide(command)

    def _normalize_decision(self, data, command):
        # 예전 단일 action 형식도 새 steps 형식으로 변환
        if "steps" not in data:
            action = data.get("action", "UNKNOWN")
            step = dict(data)
            step["action"] = action
            step["repeat"] = self._extract_repeat(command, default=int(step.get("repeat") or 1))
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
            step["repeat"] = self._safe_repeat(step.get("repeat", 1))
            clean_steps.append(step)

        if not clean_steps:
            return self._fallback_decide(command)

        # Gemini가 "네 번"을 reply에는 반영했지만 repeat을 빼먹는 경우 보정
        if len(clean_steps) == 1 and clean_steps[0].get("repeat", 1) == 1:
            action = clean_steps[0].get("action")
            if action in ["MOVE_FORWARD", "MOVE_BACKWARD", "TURN_LEFT", "TURN_RIGHT", "TURN_AROUND"]:
                clean_steps[0]["repeat"] = self._extract_repeat(command, default=1)

        data["steps"] = clean_steps
        return data

    def _safe_repeat(self, value):
        try:
            n = int(value)
        except Exception:
            n = 1
        return max(1, min(n, 10))

    def _extract_repeat(self, text, default=1):
        c = text.replace(" ", "")
        m = re.search(r"(\d+)(번|칸|회)", c)
        if m:
            return self._safe_repeat(m.group(1))
        for word, num in sorted(NUMBER_WORDS.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(fr"{word}(번|칸|회)", c):
                return num
        return default

    def _split_sequence(self, command):
        # "하고", "그리고", "다음", "그다음" 기준으로 분리
        text = command.replace(",", " ")
        parts = re.split(r"하고|그리고|그다음|다음에|다음", text)
        return [p.strip() for p in parts if p.strip()]

    def _fallback_decide(self, command):
        # 조건부 먼저 처리
        cond = self._fallback_conditional(command)
        if cond:
            return cond

        # 음악
        c_all = command.replace(" ", "")
        if any(w in c_all for w in ["음악", "노래", "클래식", "모차르트", "프리렌"]):
            return {"reply": "음악을 틀어드릴게요.", "steps": [{"action": "PLAY_MUSIC", "repeat": 1, "object_name": ""}]}

        steps = []
        for part in self._split_sequence(command):
            step = self._fallback_step(part)
            if step:
                steps.append(step)

        if not steps:
            step = self._fallback_step(command)
            if step:
                steps.append(step)

        if not steps:
            return {"reply": "명령을 정확히 이해하지 못했어요.", "steps": [{"action": "UNKNOWN", "repeat": 1, "object_name": ""}]}

        return {"reply": self._make_sequence_reply(steps), "steps": steps}

    def _fallback_conditional(self, command):
        compact = command.replace(" ", "")
        markers = ["있으면", "보이면", "들고있으면", "라면", "이면", "면은"]
        marker = next((m for m in markers if m in compact), None)
        if not marker:
            return None

        # 원문에서 대략 분리. 정확하지 않아도 Gemini vision 조건 판단으로 보완.
        idx = compact.find(marker)
        condition_raw = compact[:idx + len(marker)]
        then_raw = compact[idx + len(marker):]
        then_step = self._fallback_step(then_raw) or {"action": "UNKNOWN", "repeat": 1, "object_name": ""}

        condition_question = f"사진에서 다음 조건이 참인가? 조건: {condition_raw}"
        step = {
            "action": "CONDITIONAL_ACTION",
            "condition_type": "vision",
            "condition_question": condition_question,
            "then_action": then_step.get("action", "UNKNOWN"),
            "then_object_name": then_step.get("object_name", ""),
            "repeat": then_step.get("repeat", 1),
            "else_reply": "조건이 맞지 않아요.",
        }
        return {"reply": "조건을 확인하고 실행할게요.", "steps": [step]}

    def _fallback_step(self, text):
        c = text.replace(" ", "")
        repeat = self._extract_repeat(text, default=1)

        if any(w in c for w in ["멈춰", "정지", "스톱", "그만"]):
            return {"action": "STOP", "repeat": 1, "object_name": ""}
        if any(w in c for w in ["거리", "얼마나가까", "몇센티"]):
            return {"action": "DISTANCE_QUESTION", "repeat": 1, "object_name": ""}
        if any(w in c for w in ["부딪히기직전", "닿기전", "장애물앞", "앞으로계속", "계속가"]):
            return {"action": "MOVE_UNTIL_OBSTACLE", "repeat": 1, "object_name": ""}

        object_words = ["진라면", "음료수", "박스", "상자", "컵", "사람", "의자", "책", "종이", "손가락"]
        for obj in object_words:
            if obj in text and any(w in c for w in ["앞까지", "가줘", "가봐", "다가"]):
                return {"action": "GO_TO_OBJECT", "repeat": 1, "object_name": obj}

        if "왼" in c:
            return {"action": "TURN_LEFT", "repeat": repeat, "object_name": ""}
        if "오른" in c:
            return {"action": "TURN_RIGHT", "repeat": repeat, "object_name": ""}
        if "뒤로돌" in c or ("뒤로" in c and "돌" in c) or "180" in c:
            return {"action": "TURN_AROUND", "repeat": repeat, "object_name": ""}
        if "뒤" in c or "후진" in c:
            return {"action": "MOVE_BACKWARD", "repeat": repeat, "object_name": ""}
        if "앞" in c or "전진" in c or "와" in c:
            return {"action": "MOVE_FORWARD", "repeat": repeat, "object_name": ""}

        if any(w in c for w in ["보여", "보고", "쓰고", "입고", "정답", "문제", "종이", "있어", "몇개", "몇개야"]):
            return {"action": "VISION_QUESTION", "repeat": 1, "object_name": ""}
        return None

    def _make_sequence_reply(self, steps):
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

    # -----------------------------
    # Public handler
    # -----------------------------
    def handle_command(self, command):
        decision = self.decide_command(command)
        reply = clean_reply_text(decision.get("reply", "알겠습니다.")) or "알겠습니다."
        steps = decision.get("steps", [])
        if reply:
            self.hw.speak(reply)
        self.execute_steps(steps, original_command=command)

    def execute_steps(self, steps, original_command=""):
        for idx, step in enumerate(steps, start=1):
            action = step.get("action", "UNKNOWN")
            repeat = self._safe_repeat(step.get("repeat", 1))
            print(f"🧩 단계 {idx}/{len(steps)}: {action} x{repeat}")

            if action == "CONDITIONAL_ACTION":
                self.execute_conditional(step)
                continue
            if action == "PLAY_MUSIC":
                self.handle_music_mode(original_command)
                continue
            if action in ["VISION_QUESTION", "GENERAL_QUESTION", "DISTANCE_QUESTION", "GO_TO_OBJECT"]:
                self._execute_step(step, original_command)
                continue

            for r in range(repeat):
                if repeat > 1:
                    print(f"   ↳ 반복 {r + 1}/{repeat}")
                self._execute_step(step, original_command)
                time.sleep(0.15)

    def _execute_step(self, step, original_command=""):
        action = step.get("action", "UNKNOWN")
        object_name = step.get("object_name", "")

        if action == "MOVE_FORWARD":
            self.hw.move_forward(MOVE_SEC)
        elif action == "MOVE_UNTIL_OBSTACLE":
            distance = self.hw.move_forward_until_obstacle(stop_cm=ULTRASONIC_STOP_CM)
            if distance is not None:
                self.hw.speak(f"앞에 약 {int(distance)}센티미터 남기고 멈췄어요.")
        elif action == "MOVE_BACKWARD":
            self.hw.move_backward(BACKWARD_SEC)
        elif action == "TURN_LEFT":
            self.hw.turn_left(TURN_SEC)
        elif action == "TURN_RIGHT":
            self.hw.turn_right(TURN_SEC)
        elif action == "TURN_AROUND":
            self.hw.turn_around(TURN_AROUND_SEC)
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

    # -----------------------------
    # Conditional action
    # -----------------------------
    def execute_conditional(self, step):
        condition_type = step.get("condition_type", "vision")
        matched = False
        reason = ""

        if condition_type == "distance":
            distance = self.hw.get_distance_cm()
            op = step.get("distance_operator", "<")
            target = float(step.get("distance_cm") or ULTRASONIC_STOP_CM)
            matched = distance < target if op in ["<", "less_than"] else distance > target
            reason = f"거리 {distance:.1f}cm 기준"
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
            except Exception as e:
                print(f"❌ 조건 판단 실패: {e}")
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
            self.hw.speak(clean_reply_text(step.get("else_reply")) or "조건이 맞지 않아서 실행하지 않을게요.")

    # -----------------------------
    # Vision / object navigation
    # -----------------------------
    def answer_vision_question(self, question, object_name=""):
        image_path = None
        try:
            image_path = self.hw.capture_image()

            # 특정 물체 존재 여부 확인은 전체 명령문을 다시 넘기지 않는다.
            # 이미 이동/회전이 끝난 현재 시야만 기준으로 판단하게 한다.
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
                    answer = f"제 앞에 {object_name}가 보여요." if visible else f"제 앞에는 {object_name}가 안 보여요."
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
            self.hw.speak(clean_reply_text(result.get("answer", "")) or "제가 보기에는 확실하지 않아요.")
        except Exception as e:
            print(f"❌ 시각 질문 처리 실패: {e}")
            self.hw.speak("확인하는 중 문제가 생겼어요.")
        finally:
            self._safe_remove(image_path)

    def answer_general_question(self, question):
        try:
            self.hw.speak(clean_reply_text(self._gemini_text(f"별표, 따옴표, 마크다운 없이 TTS용 한국어 대사만 짧게 답해줘. 질문: {question}")))
        except Exception as e:
            print(f"❌ 일반 질문 처리 실패: {e}")
            self.hw.speak("질문에 답하는 중 문제가 생겼어요.")

    def go_to_object(self, object_name, max_steps=7):
        self.hw.speak(f"{object_name}를 찾아서 가볼게요.")
        for step_idx in range(1, max_steps + 1):
            distance = self.hw.get_distance_cm()
            if distance <= TARGET_STOP_DISTANCE_CM:
                self.hw.stop_motors()
                self.hw.speak(f"{object_name} 앞에 도착한 것 같아요.")
                return

            image_path = None
            try:
                image_path = self.hw.capture_image()
                nav = self._analyze_object_navigation(object_name, image_path)
                print(f"🧭 이동 판단 {step_idx}/{max_steps}:", nav)

                if not nav.get("visible", False):
                    self.hw.turn_left(OBJECT_SEARCH_TURN_SEC)
                    continue

                position = nav.get("position", "unknown")
                if position == "left":
                    self.hw.turn_left(OBJECT_ALIGN_TURN_SEC)
                elif position == "right":
                    self.hw.turn_right(OBJECT_ALIGN_TURN_SEC)
                else:
                    self.hw.move_forward(MOVE_SEC)
            except Exception as e:
                print(f"❌ 물체 접근 실패: {e}")
                self.hw.stop_motors()
                self.hw.speak("이동 중 문제가 생겨서 멈출게요.")
                return
            finally:
                self._safe_remove(image_path)

        self.hw.stop_motors()
        self.hw.speak("안전을 위해 여기서 멈출게요.")

    def _analyze_object_navigation(self, object_name, image_path):
        prompt = f"""
로봇의 현재 전방 시야다. 목표 물체는 '{object_name}'이다.
JSON 하나만 반환해라.
{{"visible": true/false, "position": "left/center/right/unknown", "reason": "짧은 이유"}}
"""
        return self._extract_json(self._gemini_vision(prompt, image_path))

    # -----------------------------
    # Music mode
    # -----------------------------
    def handle_music_mode(self, command=""):
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

        idx = 0
        while idx < len(playlist):
            intro, filename = playlist[idx]
            self.hw.speak(intro)
            path = MUSIC_DIR / filename
            self.hw.play_audio_file(path)
            self.hw.speak("더 재생할까요?")

            self.hw.command_led_on()
            try:
                answer = self.hw.listen_korean(max_seconds=4.0, silence_after=0.8, wait_timeout=6.0)
            finally:
                self.hw.command_led_off()

            a = answer.replace(" ", "")
            if not answer:
                self.hw.speak("대답이 없어서 음악 모드를 종료할게요.")
                return
            if any(w in a for w in ["그만", "멈춰", "정지", "아니", "아니요", "끝"]):
                self.hw.speak("네, 알겠습니다.")
                return
            if any(w in a for w in ["다른거", "다른것", "다음", "더", "응", "그래", "좋아"]):
                idx += 1
                continue
            self.hw.speak("네, 알겠습니다.")
            return

        self.hw.speak("준비된 음악은 여기까지예요.")

    def _safe_remove(self, path):
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
