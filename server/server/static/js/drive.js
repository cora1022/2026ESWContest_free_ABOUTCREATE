import { sendCommand } from "./commands.js";
import { state } from "./state.js";

export function startDrive(action, button) {
  stopDrive(false);
  state.activeButton = button;
  button.classList.add("active");
  sendCommand(action).catch(() => stopDrive(false));
  state.driveTimer = setInterval(() => sendCommand(action).catch(() => stopDrive(false)), 260);
}

export function stopDrive(sendStop = true) {
  const wasDriving = Boolean(state.driveTimer || state.activeButton);
  if (state.driveTimer) clearInterval(state.driveTimer);
  state.driveTimer = null;
  if (state.activeButton) state.activeButton.classList.remove("active");
  state.activeButton = null;
  if (sendStop && state.authenticated && wasDriving) sendCommand("STOP").catch(() => {});
}

export function initializeDriveControls() {
  document.querySelectorAll(".drive-button").forEach((button) => {
    const begin = (event) => {
      event.preventDefault();
      if (!state.authenticated) return;
      startDrive(button.dataset.action, button);
    };
    button.addEventListener("pointerdown", begin);
    button.addEventListener("pointerup", () => stopDrive());
    button.addEventListener("pointercancel", () => stopDrive());
    button.addEventListener("pointerleave", () => stopDrive());
    button.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && !event.repeat) begin(event);
    });
    button.addEventListener("keyup", (event) => {
      if (event.key === "Enter" || event.key === " ") stopDrive();
    });
  });
}
