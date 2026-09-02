from __future__ import annotations

import json
import os
import re
from pathlib import Path

import PIL.Image
from google import genai
from google.genai import types

from robot_app.config import AiSettings


class GeminiGateway:
    """Small adapter that keeps the Gemini SDK outside application services."""

    def __init__(self, settings: AiSettings, api_key: str | None = None) -> None:
        self.settings = settings
        resolved_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not resolved_key:
            print("⚠️ Gemini API 키가 없습니다. .env 또는 환경변수를 설정하세요.")
            self.client = None
        else:
            self.client = genai.Client(
                api_key=resolved_key,
                http_options=types.HttpOptions(timeout=settings.timeout_ms),
            )
            print("✅ Gemini 클라이언트 준비 완료")

    def require_client(self) -> None:
        if self.client is None:
            raise RuntimeError("Gemini API 키가 없습니다.")

    def text(self, prompt: str) -> str:
        self.require_client()
        response = self.client.models.generate_content(model=self.settings.model, contents=prompt)
        return (response.text or "").strip()

    def vision(self, prompt: str, image_path: str | Path) -> str:
        self.require_client()
        image = PIL.Image.open(image_path)
        try:
            response = self.client.models.generate_content(
                model=self.settings.model,
                contents=[prompt, image],
            )
            return (response.text or "").strip()
        finally:
            image.close()

    @staticmethod
    def extract_json(text: str) -> dict:
        value = text.strip()
        value = re.sub(r"^```json", "", value, flags=re.IGNORECASE).strip()
        value = re.sub(r"^```", "", value).strip()
        value = re.sub(r"```$", "", value).strip()
        match = re.search(r"\{.*\}", value, flags=re.DOTALL)
        if match:
            value = match.group(0)
        return json.loads(value)
