# main_brain.py
import os
from google import genai
from google.genai import types
from actions import move_forward, spin_around, stop_moving, speak

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise RuntimeError('GOOGLE_API_KEY environment variable is required.')
client = genai.Client(api_key=api_key)

available_tools = [move_forward, spin_around, stop_moving, speak]

def decide_and_act(user_command: str, distance: float):
    """
    가상의 사용자 명령과 초음파 센서 거리를 입력받아 제미나이에게 전달합니다.
    """
    prompt = f"""
    사용자 명령: "{user_command}"
    현재 전방 장애물까지의 거리: {distance}cm
    
    당신은 이 로봇의 두뇌입니다. 전방 20cm 이내에 장애물이 있다면 
    앞으로 가지 말고 멈추거나 경고를 말해야 합니다.
    가장 적절한 행동을 선택하여 함수를 호출하세요.
    """
    
    print("🤔 제미나이 생각 중...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=available_tools,
            temperature=0.2, 
        )
    )
    
    if response.function_calls:
        for function_call in response.function_calls:
            function_name = function_call.name
            args = {k: v for k, v in function_call.args.items()} if function_call.args else {}
            
            # 1. 먼저 동작을 수행하기 전에 사용자에게 무엇을 할지 말하게 할 수도 있습니다.
            # speak(f"{function_name} 동작을 시작합니다.") 
            
            # 2. 실제 함수 실행
            globals()[function_name](**args)
    else:
        # 제미나이가 일반적인 텍스트 답변을 한 경우
        # 이 내용을 컴퓨터 스피커로 읽어줍니다.
        speak(response.text)
