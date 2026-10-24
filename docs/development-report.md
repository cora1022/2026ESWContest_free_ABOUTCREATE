# 개발완료보고서 반영 내용

원문은 `2026ESWContest_자유공모_ABOUTCREATE_개발완료보고서.pdf`입니다. 제24회 임베디드SW경진대회 자유공모부문, 작품명은 「생각하고 동작하는 라즈베리파이 로봇」, 팀명은 About Create로 표기돼 있습니다.

README의 제작 배경, 원격 제어 화면, 케이스 개선과 팀 역할은 이 보고서를 근거로 보완했습니다. 원본 PDF의 전체 페이지 번호를 기준으로 아래에 출처를 정리했습니다.

## 내용 출처

| 페이지 | README에 반영한 내용 |
|---|---|
| 1 | 대회, 부문, 작품명과 팀명 |
| 3~4 | IoT 수업에서 시작한 개발 배경, OpenClaw의 도구 선택 방식에서 얻은 아이디어, 통합 시연 영상 |
| 6 | 세션 연결과 웹 원격 제어 화면, PC와 모바일 접속 |
| 8~10 | Raspberry Pi 5와 장치 구성, TT 모터 배치, 스티로폼에서 포맥스로 바꾼 차체 |
| 11~14, 17 | 음성과 원격 명령 처리, Gemini 행동 계획, 명령 검증과 Raspberry Pi 내부 안전정지 |
| 15 | 자석으로 탈부착하는 지붕, 벨크로로 분리하는 배터리와 Raspberry Pi |
| 21 | 5월, 6월과 8월 개발 일정, 황영연과 김민준의 역할 |

## 이미지 출처

이미지는 PDF 내부에 포함된 원본 JPEG를 추출했습니다. 사진 속 장치나 화면 내용을 다시 생성하지 않았습니다. README 갤러리에서는 같은 줄의 사진 높이를 맞추기 위해 일부 사진을 같은 비율로 잘랐습니다. `-aligned.jpg`는 표시용 사본이며, 추출한 원본도 함께 보관합니다.

| 이미지 | 페이지 | 내용 |
|---|---:|---|
| `images/report-robot-complete.jpg` | 4 | 카메라와 센서를 통합한 실물 로봇 |
| `images/report-dashboard-login.jpg` | 6 | 연결 상태와 제어 키를 확인하는 세션 화면 |
| `images/report-dashboard-control.jpg` | 6 | 카메라 영상과 방향 제어 대시보드 |
| `images/report-motor-layout.jpg` | 8 | 차체 하부 TT 모터 배치 |
| `images/report-case-fabrication.jpg` | 10 | 포맥스 케이스 제작 |
| `images/report-magnetic-roof.jpg` | 15 | 자석 지붕 |
| `images/report-removable-battery.jpg` | 15 | 분리 가능한 배터리 |
| `images/report-removable-pi.jpg` | 15 | 분리 가능한 Raspberry Pi |

기존 제작 사진 4장과 `robot-demo.gif`는 과거 커밋 `25dc0ae`에서 복원한 자료입니다.

## 현재 코드와의 관계

보고서의 `main_brain.py`, `actions.py`, `controller.py` 같은 표기는 제작 당시의 실행 흐름을 설명합니다. 현재 소스는 `robot/src/robot_app`과 `server/server` 아래의 계층별 모듈로 나뉘어 있으므로 README의 설치와 실행은 현재 패키지 구조를 따릅니다.

보고서는 웹 원격 제어를 개발 결과로 설명하고 접속 화면과 영상 수신 장면을 제시합니다. 반면 기존 하드웨어 인수 기록에는 HC-SR04 반복 측정, 교정된 네 방향 모터 동작과 브라우저 원격 주행이 추가 검증 항목으로 남아 있습니다. README에서는 보고서의 결과와 저장소의 인수 시험 기록을 구분해 기술했습니다.

위치 기능은 보고서에서도 GNSS 모듈 장착 후 적용할 대상으로 설명합니다. 현재 대시보드에 위치 화면이 있는 것으로 소개하지 않았습니다. 자율순찰, 가전 제어와 AI 구독 모델 역시 완료된 기능으로 보지 않았습니다.

[README로 돌아가기](../README.md)

유튜브 링크 카드 `images/youtube-demo-preview.png`는 [시연 영상](https://youtu.be/NtMfFOqJAB8)의 공식 썸네일과 YouTube oEmbed에서 확인한 제목, 채널명을 사용했습니다. 재생 버튼과 제목 영역을 덧붙인 표시용 카드이며, 클릭하면 원본 영상으로 이동합니다.
