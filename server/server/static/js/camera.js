import { api } from "./api.js";
import { $, state } from "./state.js";

export async function loadCamera() {
  if (state.cameraLoading) {
    state.cameraRefreshPending = true;
    return;
  }
  state.cameraLoading = true;
  const requestVersion = state.cameraFrameVersion;
  try {
    const response = await api(`/api/camera/latest?t=${Date.now()}`);
    const blob = await response.blob();
    if (requestVersion === state.cameraFrameVersion) displayCameraBlob(blob);
  } catch (_) {
  } finally {
    state.cameraLoading = false;
    if (state.cameraRefreshPending) {
      state.cameraRefreshPending = false;
      loadCamera();
    }
  }
}

export function displayCameraBlob(blob) {
  const image = $("#cameraImage");
  if (image.dataset.url) URL.revokeObjectURL(image.dataset.url);
  const url = URL.createObjectURL(blob);
  image.dataset.url = url;
  image.src = url;
  image.hidden = false;
  $("#cameraStandby").hidden = true;
  $("#cameraTime").textContent = `마지막 갱신 ${new Date().toLocaleTimeString()}`;
}

export function resetCameraView(message) {
  const image = $("#cameraImage");
  if (image.dataset.url) URL.revokeObjectURL(image.dataset.url);
  delete image.dataset.url;
  image.removeAttribute("src");
  image.hidden = true;
  $("#cameraStandby span").textContent = message;
  $("#cameraStandby").hidden = false;
}

export function initializeCameraControls() {
  $("#captureButton").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const label = button.querySelector("span");
    button.disabled = true;
    label.textContent = "촬영 요청 중";
    try {
      await api("/api/camera", { method: "POST" });
      $("#cameraTime").textContent = "로봇에 촬영을 요청했습니다.";
    } catch (error) {
      $("#cameraTime").textContent = error.message;
    } finally {
      button.disabled = false;
      label.textContent = "사진 촬영";
    }
  });
}
