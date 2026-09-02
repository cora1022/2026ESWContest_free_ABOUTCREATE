# Raspberry Pi 설치 안내

현재 모노레포 배포 경로와 설치 명령은 [Raspberry Pi 배포 문서](deployment/raspberry-pi.md)에서 관리합니다.

이전 평면 구조의 `requirements-robot.txt`, `.env.robot.example`, `deploy/raspberry-pi/robot.service.example` 경로는 더 이상 사용하지 않습니다. 현재 기준은 다음과 같습니다.

```text
/home/dslab/Desktop/robot-pj/
├─ packages/robot-protocol/
└─ robot/
   ├─ .venv/
   └─ .env
```

모터가 움직이는 시험은 자동 설치에 포함하지 않으며 [하드웨어 안전 조건](hardware.md)을 확인한 뒤 별도로 진행합니다.
