# actions.py
import os
from gtts import gTTS
import pygame
import time

def speak(text: str):
    """텍스트를 MP3로 변환하여 저장하고 스피커로 재생합니다."""
    print(f"🔊 로봇 응답: '{text}'")
    
    filename = "speech.mp3"
    
    try:
        # 1. gTTS를 사용하여 음원 생성 (한국어)
        tts = gTTS(text=text, lang='ko')
        tts.save(filename)

        # 2. pygame을 사용하여 오디오 재생
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # 3. 재생이 끝날 때까지 대기
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # 4. 재생 종료 후 파일 해제 (다음에 다시 쓰기 위함)
        pygame.mixer.music.unload()
        
    except Exception as e:
        print(f"❌ 오디오 재생 중 오류 발생: {e}")

# 나머지 동작 함수들
def move_forward(duration: int):
    print(f"▶️ [동작] {duration}초 동안 앞으로 이동합니다.")

def spin_around():
    print("▶️ [동작] 제자리에서 빙글빙글 돕니다!")

def stop_moving():
    print("▶️ [동작] 즉시 멈춥니다.")