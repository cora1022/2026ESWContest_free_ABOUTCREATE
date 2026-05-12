#python test_case.py
from main_brain import decide_and_act

def run_tests():
    # 3가지의 가상 상황(시나리오)을 준비합니다.
    scenarios = [
        {
            "description": "정상적인 전진 명령",
            "command": "앞으로 3초만 가볼래?",
            "distance": 100.0  # 장애물 없음
        },
        {
            "description": "장애물 감지 상황 (20cm 이하)",
            "command": "앞으로 쭉 가봐!",
            "distance": 15.0   # 코앞에 벽이 있음!
        },
        {
            "description": "감정 표현 명령",
            "command": "오늘 기분 어때? 신나게 돌아봐",
            "distance": 50.0
        }
    ]

    print("🚀 로봇 AI 두뇌 테스트를 시작합니다...\n")

    for i, scenario in enumerate(scenarios):
        print("=" * 50)
        print(f"테스트 {i+1} : {scenario['description']}")
        print(f"🎤 입력된 음성: '{scenario['command']}'")
        print(f"📏 센서 거리: {scenario['distance']}cm")
        print("-" * 50)
        
        # main_brain의 핵심 함수에 가상 데이터를 넣어서 실행
        decide_and_act(scenario['command'], scenario['distance'])
        print("\n")

if __name__ == "__main__":
    run_tests()