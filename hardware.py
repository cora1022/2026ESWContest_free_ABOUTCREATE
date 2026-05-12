# actions.py
def move_forward(duration: int):
    print(f"▶️ [가상 모터] {duration}초 동안 앞으로 이동합니다.")

def spin_around():
    print("▶️ [가상 모터] 제자리에서 빙글빙글 돕니다!")

def stop_moving():
    print("▶️ [가상 모터] 모든 움직임을 즉시 멈춥니다 삐익-.")

def speak(text: str):
    print(f"▶️ [가상 스피커] 🔊 '{text}'")