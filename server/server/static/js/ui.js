import { elements } from "./state.js";

export function setConnectionCheck(element, stateName, label) {
  element.classList.remove("checking", "online", "offline");
  element.classList.add(stateName);
  element.querySelector("strong").textContent = label;
}

export function safety(message, level = "") {
  elements.safetyMessage.textContent = message;
  elements.safetyMessage.dataset.level = level;
}
