import { api } from "./api.js";
import { safety } from "./ui.js";

export async function sendCommand(action, extra = {}) {
  try {
    const response = await api("/api/command", {
      method: "POST",
      body: JSON.stringify({ action, duration_ms: 650, ...extra }),
      keepalive: action === "STOP" || action === "VIDEO_STOP",
    });
    return await response.json();
  } catch (error) {
    safety(error.message, "danger");
    throw error;
  }
}
