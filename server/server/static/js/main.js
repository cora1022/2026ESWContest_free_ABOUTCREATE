import { setUnauthorizedHandler } from "./api.js";
import { initializeCameraControls } from "./camera.js";
import { initializeDriveControls, stopDrive } from "./drive.js";
import {
  connectDashboardSocket,
  disconnectDashboardSocket,
  refreshConnectionPreview,
  refreshStatus,
  waitForDashboardSocket,
} from "./realtime.js";
import { initializeSpeechControls } from "./speech.js";
import { $, elements, state } from "./state.js";
import { safety } from "./ui.js";
import { clearVideoLease, initializeVideoControls, setVideoState, stopVideo } from "./video.js";

function logout() {
  clearVideoLease();
  setVideoState(false);
  $("#frontendSpeech").pause();
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  state.authenticated = false;
  state.videoUserDisabled = false;
  state.videoAutoStartAttempted = false;
  elements.loginOverlay.classList.remove("hidden");
  disconnectDashboardSocket();
}

async function initialize() {
  try {
    connectDashboardSocket();
    await waitForDashboardSocket();
    await refreshStatus();
  } catch (error) {
    safety(error.message, "danger");
  }
}

async function restoreSession() {
  const legacySession = sessionStorage.getItem("robotSession") || "";
  const headers = legacySession ? { Authorization: `Bearer ${legacySession}` } : {};
  try {
    const response = await fetch("/api/session", { headers, credentials: "same-origin" });
    if (!response.ok) return;
    state.authenticated = true;
    state.videoUserDisabled = false;
    state.videoAutoStartAttempted = false;
    sessionStorage.removeItem("robotSession");
    elements.loginOverlay.classList.add("hidden");
    await initialize();
  } catch (_) {
  }
}

function initializeLogin() {
  $("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    elements.loginError.textContent = "";
    const submitButton = event.currentTarget.querySelector('button[type="submit"]');
    const submitLabel = submitButton.querySelector("span");
    submitButton.disabled = true;
    submitLabel.textContent = "인증하고 연결하는 중";
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Session-Mode": "cookie" },
        body: JSON.stringify({ key: $("#accessKey").value }),
        credentials: "same-origin",
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "로그인 실패");
      state.authenticated = true;
      state.videoUserDisabled = false;
      state.videoAutoStartAttempted = false;
      $("#accessKey").value = "";
      elements.loginOverlay.classList.add("hidden");
      await initialize();
    } catch (error) {
      elements.loginError.textContent = error.message;
    } finally {
      submitButton.disabled = false;
      submitLabel.textContent = "제어 세션 시작";
    }
  });
}

async function bootstrap() {
  setUnauthorizedHandler(logout);
  initializeLogin();
  initializeDriveControls();
  initializeCameraControls();
  initializeVideoControls();
  initializeSpeechControls();

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopDrive();
      stopVideo();
    }
  });
  window.addEventListener("pagehide", () => {
    stopDrive();
    stopVideo();
  });

  await refreshConnectionPreview();
  setInterval(refreshConnectionPreview, 4000);
  await restoreSession();
}

bootstrap();
