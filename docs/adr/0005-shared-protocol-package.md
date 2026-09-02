# ADR 0005. 통신 계약을 독립 공통 패키지로 관리한다

- 상태: 승인
- 날짜: 2026-09-02

## 배경

초기 분리 구조에는 동일한 `transport.py`가 `robot`과 `server`에 각각 존재했습니다. 한쪽만 수정하면 테스트가 각 폴더에서는 통과해도 실제 연결에서 binary frame이 호환되지 않을 수 있습니다.

## 결정

명령, 메시지, protocol version과 `RBT1` framing을 `packages/robot-protocol`의 installable Python package로 관리합니다.

- runtime은 Python 표준 라이브러리만 사용합니다.
- 두 애플리케이션은 `robot_protocol`을 import합니다.
- 전체 모노레포를 각 장비에 checkout하고 필요한 애플리케이션 가상환경에 package를 설치합니다.
- 공통 계약 테스트는 package 폴더에 한 번만 둡니다.

## 결과

통신 규격의 단일 원본과 명시적인 version을 갖게 됩니다. 대신 `robot` 또는 `server` 폴더만 따로 복사해 배포할 수 없고, protocol 변경 시 VPS와 Pi의 순차 배포 호환성을 고려해야 합니다. 현재 규모에서는 별도 package registry보다 같은 모노레포의 local package 설치가 단순합니다.
