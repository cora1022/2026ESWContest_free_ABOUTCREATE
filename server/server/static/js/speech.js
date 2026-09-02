import { sendCommand } from "./commands.js";
import { $, elements, state } from "./state.js";
import { safety } from "./ui.js";

export function updateSpeechButton() {
  elements.captionSoundButton.setAttribute("aria-pressed", String(state.speechEnabled));
  elements.captionSoundButton.setAttribute("aria-label", state.speechEnabled ? "프론트 음성 끄기" : "프론트 음성 켜기");
  elements.captionSoundButton.querySelector("i").className = state.speechEnabled ? "ph ph-speaker-high" : "ph ph-speaker-slash";
}

function speakWithBrowserVoice(caption) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(caption);
  utterance.lang = "ko-KR";
  utterance.rate = 1;
  const koreanVoice = window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase().startsWith("ko"));
  if (koreanVoice) utterance.voice = koreanVoice;
  window.speechSynthesis.speak(utterance);
}

function playSpeechAudio(audioB64, audioContentType, fallbackCaption) {
  if (!audioB64) {
    speakWithBrowserVoice(fallbackCaption);
    return;
  }

  try {
    const binary = window.atob(audioB64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    const audio = $("#frontendSpeech");
    audio.pause();
    if (audio.dataset.url) URL.revokeObjectURL(audio.dataset.url);
    const url = URL.createObjectURL(new Blob([bytes], { type: audioContentType || "audio/mpeg" }));
    audio.dataset.url = url;
    audio.src = url;
    audio.currentTime = 0;
    audio.play().catch(() => speakWithBrowserVoice(fallbackCaption));
  } catch (_) {
    speakWithBrowserVoice(fallbackCaption);
  }
}

export function presentRobotSpeech(text, audioB64 = "", audioContentType = "audio/mpeg") {
  const caption = String(text || "").trim();
  if (!caption) return;

  $("#captionText").textContent = caption;
  $("#robotCaption").hidden = false;
  if (state.captionTimer) clearTimeout(state.captionTimer);
  state.captionTimer = setTimeout(() => {
    $("#robotCaption").hidden = true;
  }, Math.max(6000, Math.min(16000, caption.length * 180)));

  if (!state.speechEnabled) return;
  playSpeechAudio(audioB64, audioContentType, caption);
}

async function sendVoiceText(text) {
  const command = text.trim();
  if (!command) return;
  elements.voiceButton.classList.remove("listening");
  elements.voiceButton.setAttribute("aria-pressed", "false");
  elements.voiceButton.querySelector("span").textContent = "명령 전송 중";
  try {
    await sendCommand("TEXT_COMMAND", { text: command, duration_ms: 650 });
    safety(`음성 명령 전송: ${command}`);
  } finally {
    elements.voiceButton.querySelector("span").textContent = "음성 명령";
  }
}

export function initializeSpeechControls() {
  elements.captionSoundButton.addEventListener("click", () => {
    state.speechEnabled = !state.speechEnabled;
    localStorage.setItem("robotSpeechMuted", state.speechEnabled ? "0" : "1");
    if (!state.speechEnabled) {
      const audio = $("#frontendSpeech");
      audio.pause();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    }
    updateSpeechButton();
  });

  $("#frontendSpeech").addEventListener("ended", (event) => {
    const audio = event.currentTarget;
    if (audio.dataset.url) {
      URL.revokeObjectURL(audio.dataset.url);
      delete audio.dataset.url;
      audio.removeAttribute("src");
    }
  });

  elements.voiceButton.addEventListener("click", () => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      const text = window.prompt("로봇에 전달할 명령을 입력하세요.");
      if (text) sendVoiceText(text).catch(() => {});
      return;
    }

    if (state.recognition) {
      state.recognition.stop();
      return;
    }

    const recognition = new Recognition();
    state.recognition = recognition;
    recognition.lang = "ko-KR";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      elements.voiceButton.classList.add("listening");
      elements.voiceButton.setAttribute("aria-pressed", "true");
      elements.voiceButton.querySelector("span").textContent = "듣는 중";
    };
    recognition.onresult = (event) => sendVoiceText(event.results[0][0].transcript).catch(() => {});
    recognition.onerror = () => safety("음성을 인식하지 못했습니다. 다시 시도해 주세요.", "warning");
    recognition.onend = () => {
      state.recognition = null;
      elements.voiceButton.classList.remove("listening");
      elements.voiceButton.setAttribute("aria-pressed", "false");
      if (elements.voiceButton.querySelector("span").textContent === "듣는 중") {
        elements.voiceButton.querySelector("span").textContent = "음성 명령";
      }
    };
    recognition.start();
  });

  updateSpeechButton();
}
