import { resetCameraView } from "./camera.js";
import { $, actionLabels, state } from "./state.js";
import { safety } from "./ui.js";
import { clearVideoLease, setVideoState, startDefaultVideo } from "./video.js";

export function renderState(robot) {
  const online = Boolean(robot.online);
  const badge = $("#connectionBadge");
  badge.classList.toggle("online", online);
  badge.classList.toggle("offline", !online);
  badge.querySelector("strong").textContent = online ? "온라인" : "오프라인";

  const mode = String(robot.mode || "").toUpperCase();
  $("#modeValue").textContent = mode === "REMOTE" ? "원격 모드" : mode === "LOCAL" ? "로컬 모드" : "오프라인";
  $("#distanceValue").textContent = robot.distance_cm == null ? "-- cm" : `${Number(robot.distance_cm).toFixed(0)} cm`;
  setVideoState(Boolean(robot.video_active || state.videoLeaseTimer));

  if (!online) {
    state.videoAutoStartAttempted = false;
    clearVideoLease();
    setVideoState(false);
    resetCameraView("로봇 연결 끊김");
    safety("로봇이 VPS에 연결되어 있지 않습니다.", "danger");
  } else if (robot.obstacle) {
    safety("전방 장애물이 감지되어 전진이 차단됐습니다.", "warning");
  } else if (robot.remote_control_active) {
    safety("원격 제어가 활성화됐습니다.");
  } else {
    safety("로봇이 명령을 받을 준비가 됐습니다.");
  }

  if (online) queueMicrotask(startDefaultVideo);
}

export function eventLabel(event) {
  if (event.type === "speech") return `로봇: ${String(event.text || "").slice(0, 80)}`;
  const raw = event.action || event.event || event.type || "event";
  const reasonAction = String(event.reason || "").replace(/^simulated_/i, "").toUpperCase();
  const label = actionLabels[raw] || actionLabels[String(raw).toUpperCase()] || actionLabels[event.reason] || actionLabels[reasonAction];
  if (event.type === "command_result" && ["rejected", "failed"].includes(event.status)) return `명령 실패: ${event.reason || event.status}`;
  if (label && event.type === "command_result") return `${label} 완료`;
  return label || event.reason || raw;
}

export function addEvent(event) {
  if (event.type === "command_result" && ["rejected", "failed"].includes(event.status)) {
    if (String(event.reason || "").toLowerCase().includes("video")) {
      clearVideoLease();
      setVideoState(false);
    }
    safety(`로봇 명령 실패: ${event.reason || event.status}`, "danger");
  }
  if (event.reason === "video_stopped" || event.event === "video_stopped" || event.event === "video_failed") {
    clearVideoLease();
    setVideoState(false);
  }
  state.events.unshift(event);
  state.events = state.events.slice(0, 30);
  renderEvents();
}

export function renderEvents() {
  const list = $("#eventList");
  list.replaceChildren();
  if (!state.events.length) {
    const item = document.createElement("li");
    const text = document.createElement("strong");
    text.textContent = "아직 기록이 없습니다";
    item.append(text);
    list.append(item);
    return;
  }

  state.events.slice(0, 8).forEach((event) => {
    const item = document.createElement("li");
    const timestamp = event.timestamp || event.server_time || Date.now() / 1000;
    const timeElement = document.createElement("time");
    timeElement.textContent = new Date(timestamp * 1000).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    const text = document.createElement("strong");
    text.textContent = eventLabel(event);
    item.append(timeElement, text);
    list.append(item);
  });
}
