export const state = {
  authenticated: false,
  socket: null,
  socketReconnectTimer: null,
  driveTimer: null,
  activeButton: null,
  videoActive: false,
  videoStarting: false,
  videoUserDisabled: false,
  videoAutoStartAttempted: false,
  videoLeaseTimer: null,
  cameraLoading: false,
  cameraRefreshPending: false,
  cameraFrameVersion: 0,
  events: [],
  recognition: null,
  captionTimer: null,
  speechEnabled: localStorage.getItem("robotSpeechMuted") !== "1",
};

export const $ = (selector) => document.querySelector(selector);

export const elements = {
  loginOverlay: $("#loginOverlay"),
  loginError: $("#loginError"),
  safetyMessage: $("#safetyMessage"),
  voiceButton: $("#voiceButton"),
  videoButton: $("#videoButton"),
  captionSoundButton: $("#captionSoundButton"),
  serverConnection: $("#serverConnection"),
  robotConnection: $("#robotConnection"),
};

export const actionLabels = {
  FORWARD: "전진",
  BACKWARD: "후진",
  LEFT: "좌회전",
  RIGHT: "우회전",
  STOP: "주행 종료",
  CAPTURE_IMAGE: "사진 촬영",
  TEXT_COMMAND: "음성 명령",
  VIDEO_START: "영상 시작",
  VIDEO_STOP: "영상 종료",
  robot_connected: "로봇 연결됨",
  robot_disconnected: "로봇 연결 끊김",
  camera_updated: "사진 갱신",
  speech: "로봇 음성",
  video_started: "영상 시작됨",
  video_lease_refreshed: "영상 연결 유지",
  video_stopped: "영상 종료됨",
  video_failed: "영상 오류",
  video_lease_expired: "영상 연결 종료",
};
