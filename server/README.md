# VPS 제어 서버

FastAPI 기반 제어 서버입니다. 브라우저 세션을 인증하고 Raspberry Pi와 WebSocket으로 연결해 명령, 상태, 카메라 프레임과 음성 이벤트를 중계합니다.

## 구조

```text
server/
├─ server/
│  ├─ app.py              # 앱 팩토리와 미들웨어 조립
│  ├─ config.py           # 환경변수 설정과 검증
│  ├─ schemas.py          # API 요청과 명령 생성
│  ├─ dependencies.py     # FastAPI 의존성
│  ├─ routers/            # HTTP와 WebSocket 진입점
│  ├─ services/           # 세션, 이벤트, 실시간 로봇 상태
│  └─ static/             # 웹 프론트와 기능별 JavaScript 모듈
├─ tests/
├─ tools/
└─ deploy/
```

서버 상태는 프로세스 메모리에서 관리하므로 Uvicorn은 반드시 단일 worker로 실행합니다. 여러 인스턴스로 확장하려면 세션과 실시간 상태를 Redis 같은 외부 저장소로 옮겨야 합니다.

## 로컬 실행

저장소 루트에서 다음 순서로 설치합니다.

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env.example`을 참고해 환경변수를 설정한 뒤 실행합니다.

```bash
uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 1
```

## 테스트

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## VPS 배포

모노레포를 `/opt/robot-pj`에 배치하고 `deploy/robot-server.service`를 설치합니다. 운영 환경변수는 `/etc/robot-server.env`, 이벤트 로그는 `/var/lib/robot-server/events.jsonl`에 둡니다.

실제 로봇 토큰과 대시보드 키는 소스 폴더나 Git에 저장하지 않습니다.
