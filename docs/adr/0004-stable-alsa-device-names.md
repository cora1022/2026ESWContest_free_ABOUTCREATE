# ADR 0004. USB 오디오는 ALSA 카드 이름으로 선택한다

- 상태: 승인
- 날짜: 2026-09-02

## 배경

USB 허브의 연결 순서가 바뀌면 ALSA 카드 번호도 달라집니다. 실제 장비에서 웹캠 마이크와 USB 출력 장치가 재연결된 뒤 숫자 기반 `plughw:4,0`과 `plughw:3,0`이 다른 장치를 가리킬 수 있었습니다.

## 결정

장치 번호 대신 ALSA가 제공하는 카드 이름을 환경 설정에 사용합니다.

```dotenv
AUDIO_DEVICE=plughw:CARD=CAMERA,DEV=0
AUDIO_OUTPUT_DEVICE=plughw:CARD=UACDemoV10,DEV=0
```

시작 시 입력과 출력 장치를 확인하고, 장치 오류가 반복될 때는 backoff와 log rate limit을 적용합니다.

## 결과

동일 USB 장치가 다시 연결될 때 카드 번호 변화의 영향을 줄입니다. 같은 이름의 장치가 여러 개 있거나 장치 firmware가 이름을 바꾸는 경우에는 udev 규칙 같은 추가 식별 방식이 필요합니다.
