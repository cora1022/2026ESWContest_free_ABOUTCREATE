import { sendCommand } from "./commands.js";
import { $, elements, state } from "./state.js";
import { safety } from "./ui.js";

export function setVideoState(active) {
  state.videoActive = Boolean(active);
  elements.videoButton.classList.toggle("active", state.videoActive);
  elements.videoButton.setAttribute("aria-pressed", String(state.videoActive));
  elements.videoButton.querySelector("i").className = state.videoActive ? "ph ph-video-camera-slash" : "ph ph-video-camera";
  elements.videoButton.querySelector("span").textContent = state.videoActive ? "영상 종료" : "영상 시작";
  $("#videoStatus").hidden = !state.videoActive;
  if (state.videoActive && $("#cameraImage").hidden) {
    $("#cameraStandby span").textContent = "영상 수신 중";
  }
}

export function clearVideoLease() {
  if (state.videoLeaseTimer) clearInterval(state.videoLeaseTimer);
  state.videoLeaseTimer = null;
}

export async function startVideo() {
  if (state.videoStarting || state.videoActive) return;
  state.videoStarting = true;
  elements.videoButton.disabled = true;
  try {
    await sendCommand("VIDEO_START", { duration_ms: 8000 });
    setVideoState(true);
    clearVideoLease();
    state.videoLeaseTimer = setInterval(() => {
      sendCommand("VIDEO_START", { duration_ms: 8000 }).catch(() => {
        clearVideoLease();
        setVideoState(false);
      });
    }, 5000);
    safety("컬러 영상 모드가 시작됐습니다.");
  } catch (_) {
    clearVideoLease();
    setVideoState(false);
  } finally {
    state.videoStarting = false;
    elements.videoButton.disabled = false;
  }
}

export function startDefaultVideo() {
  if (!state.authenticated || state.videoUserDisabled || state.videoAutoStartAttempted || state.videoActive || state.videoStarting || state.videoLeaseTimer) return;
  state.videoAutoStartAttempted = true;
  startVideo();
}

export function stopVideo(sendStop = true) {
  const wasActive = state.videoActive || Boolean(state.videoLeaseTimer);
  clearVideoLease();
  setVideoState(false);
  if (sendStop && state.authenticated && wasActive) {
    sendCommand("VIDEO_STOP").catch(() => {});
  }
}

export function initializeVideoControls() {
  elements.videoButton.addEventListener("click", () => {
    if (state.videoActive) {
      state.videoUserDisabled = true;
      stopVideo();
    } else {
      state.videoUserDisabled = false;
      state.videoAutoStartAttempted = true;
      startVideo();
    }
  });
}
