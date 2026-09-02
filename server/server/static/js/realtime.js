import { api } from "./api.js";
import { displayCameraBlob, loadCamera, resetCameraView } from "./camera.js";
import { addEvent, renderEvents, renderState } from "./dashboard.js";
import { presentRobotSpeech } from "./speech.js";
import { $, elements, state } from "./state.js";
import { setConnectionCheck, safety } from "./ui.js";
import { clearVideoLease, setVideoState } from "./video.js";

export async function refreshConnectionPreview() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch("/health", { cache: "no-store", signal: controller.signal });
    if (!response.ok) throw new Error("health check failed");
    const payload = await response.json();
    setConnectionCheck(elements.serverConnection, "online", "연결됨");
    setConnectionCheck(
      elements.robotConnection,
      payload.robot_online ? "online" : "offline",
      payload.robot_online ? "온라인" : "연결 대기",
    );
  } catch (_) {
    setConnectionCheck(elements.serverConnection, "offline", "연결되지 않음");
    setConnectionCheck(elements.robotConnection, "offline", "확인할 수 없음");
  } finally {
    clearTimeout(timeout);
  }
}

export function disconnectDashboardSocket() {
  if (state.socketReconnectTimer) clearTimeout(state.socketReconnectTimer);
  state.socketReconnectTimer = null;
  if (state.socket) {
    state.socket.onclose = null;
    state.socket.close();
  }
  state.socket = null;
}

export function connectDashboardSocket() {
  disconnectDashboardSocket();
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${scheme}://${location.host}/ws/dashboard`);
  state.socket = socket;
  socket.binaryType = "arraybuffer";
  socket.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      state.cameraFrameVersion += 1;
      displayCameraBlob(new Blob([event.data], { type: "image/jpeg" }));
      return;
    }
    const message = JSON.parse(event.data);
    if (message.type === "state") renderState(message.state);
    if (message.type === "event") {
      addEvent(message.event);
      if (message.event.type === "speech") presentRobotSpeech(message.event.text);
    }
    if (message.type === "camera_updated") loadCamera();
    if (message.type === "speech") {
      const speechEvent = { ...message };
      delete speechEvent.audio_b64;
      addEvent(speechEvent);
      presentRobotSpeech(message.text, message.audio_b64, message.audio_content_type);
    }
  };
  socket.onclose = () => {
    if (state.socket !== socket) return;
    state.socket = null;
    showDashboardConnectionLost();
    if (state.authenticated) state.socketReconnectTimer = setTimeout(connectDashboardSocket, 2000);
  };
}

export function showDashboardConnectionLost() {
  clearVideoLease();
  setVideoState(false);
  resetCameraView("서버 연결 재시도 중");
  const badge = $("#connectionBadge");
  badge.classList.remove("online");
  badge.classList.add("offline");
  badge.querySelector("strong").textContent = "연결 끊김";
  $("#modeValue").textContent = "오프라인";
  safety("대시보드 연결이 끊겨 다시 연결하고 있습니다.", "danger");
}

export function waitForDashboardSocket() {
  const socket = state.socket;
  if (!socket || socket.readyState === WebSocket.OPEN) return Promise.resolve();
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timeout);
      resolve();
    };
    const timeout = setTimeout(finish, 2000);
    socket.addEventListener("open", finish, { once: true });
    socket.addEventListener("close", finish, { once: true });
  });
}

export async function refreshStatus() {
  const response = await api("/api/status");
  const payload = await response.json();
  renderState(payload.state);
  state.events = payload.events || [];
  renderEvents();
  if (payload.camera_time) loadCamera();
}
