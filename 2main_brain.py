#pip install google-generativeai
"""Legacy function-calling experiment retained for reference.

The current physical robot entrypoint is main_brain.py. This historical file
depends on an older ``robot`` object and is not part of the restored runtime.
"""

import os
import google.generativeai as genai
import actions 
from actions import robot

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 1. API key is read from the environment. Do not commit real keys.
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    raise RuntimeError('GOOGLE_API_KEY environment variable is required.')
genai.configure(api_key=API_KEY)
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

# 2. 제미나이가 사용할 수 있는 물리적 행동(함수) 목록
# (주의: 말하기 기능은 기본 응답 텍스트로 처리하므로 도구 목록에서 뺐습니다)
tool_list = [
    actions.move_forward, 
    actions.move_backward, 
    actions.spin_around, 
    actions.stop_moving
]

# 3. 모델 초기화 및 시스템 지침 설정
model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    tools=tool_list,
    system_instruction=(
        "당신은 라즈베리파이 5 기반의 자율주행 로봇입니다. "
        "사용자의 명령을 들으면 무조건 자연스럽고 친근한 한국어 문장으로 먼저 대답할 내용을 작성하세요. "
        "그리고 사용자의 명령에 따라 물리적 행동이 필요하다면 적절한 함수를 함께 호출하세요. "
        "전방 15cm 이내에 장애물이 있다면 절대 앞으로 전진하는 함수를 호출하지 말고 이유를 설명하세요."
    )
)

def run_robot():
    print("\n[시스템] 로봇 두뇌 가동 시작! 음성 명령을 기다립니다...")
    robot.speak("안녕하세요! 명령을 내려주세요.")
    
    # 문맥 유지를 위해 채팅 세션 시작
    chat = model.start_chat(enable_automatic_function_calling=False)
    
    while True:
        # A. 이벤트 발생 대기 (사용자의 음성 명령이 들어올 때까지 대기)
        user_command = robot.listen_command()
        
        # 유효하지 않은 음성 무시
        if "이해하지 못" in user_command or "연결할 수 없" in user_command or not user_command:
            continue
            
        if "종료" in user_command:
            robot.speak("시스템을 종료합니다. 안녕히 계세요!")
            break

        # B. 음성 명령이 들어오면 그제야 현재 상태(센서값)를 확인
        distance = robot.get_distance_cm()
        print(f"[상황 인지] 명령: '{user_command}' / 전방 거리: {distance:.1f} cm")
        
        # C. 제미나이에게 판단 요청
        prompt = f"""
        사용자 명령: "{user_command}"
        현재 전방 거리: {distance:.1f}cm
        """
        
        try:
            print("[AI 생각 중...]")
            response = chat.send_message(prompt)
            
            # D. 결과 처리 (말하기 + 행동하기)
            # 제미나이의 응답(response)은 텍스트(대답)와 함수 호출(행동) 파트로 나뉠 수 있습니다.
            for part in response.parts:
                
                # 1. 텍스트 응답이 있다면 무조건 스피커로 말하기
                if part.text:
                    print(f"🤖 AI 대답: {part.text.strip()}")
                    robot.speak(part.text.strip())
                
                # 2. 함수 호출 결정이 있다면 모터 움직이기
                if part.function_call:
                    func_name = part.function_call.name
                    func_args = dict(part.function_call.args)
                    
                    print(f"⚙️ [물리적 행동 실행] {func_name}({func_args})")
                    
                    # actions.py에 있는 해당 이름의 함수를 찾아 실행
                    func_to_call = getattr(actions, func_name)
                    func_to_call(**func_args)
                    
        except Exception as e:
            print(f"[오류 발생] {e}")
            robot.speak("어이쿠, 생각하는 중에 오류가 발생했어요.")

if __name__ == "__main__":
    try:
        run_robot()
    except KeyboardInterrupt:
        print("\n강제 종료됨.")
    finally:
        robot.wheels.stop()
        if hasattr(robot, 'camera'):
            robot.camera.release()
