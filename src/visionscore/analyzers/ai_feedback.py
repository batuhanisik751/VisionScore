from __future__ import annotations

import json
import re

import cv2
import ollama
from ollama import ChatResponse

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.models import AIFeedback, ImageMeta
from visionscore.pipeline.loader import LoadedImage

_SYSTEM_PROMPT = """\
You are an expert photography critic and instructor with decades of experience \
evaluating photographs across all genres. Analyze the provided image and respond \
with ONLY a JSON object (no markdown, no explanation outside the JSON).

The JSON must have exactly these keys:
{
  "genre": "one of: landscape, portrait, street, macro, wildlife, architecture, abstract, food, event, other",
  "description": "A 1-2 sentence description of the image content and subject matter",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "improvements": ["improvement 1", "improvement 2", "improvement 3"],
  "mood": "The emotional mood or atmosphere (e.g., serene, dramatic, joyful, melancholic)",
  "score": 72,
  "reasoning": "A 2-3 sentence explanation of the overall score"
}

Rules:
- "score" must be an integer from 0 to 100
- "strengths" and "improvements" must each have exactly 3 items
- Each item should be a concise phrase (under 15 words)
- Be constructive and specific in improvements, not vague
- Score guidelines: 0-20 poor, 21-40 below average, 41-60 average, 61-80 good, 81-100 excellent\
"""

_USER_PROMPT = (
    "Analyze this photograph as an expert photography critic. Respond with only the JSON object."
)


class AIFeedbackAnalyzer(BaseAnalyzer):
    """Vision LLM analyzer using Ollama + LLaVA for natural language photo critique."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llava") -> None:
        self._host = host
        self._model = model
        self._client = ollama.Client(host=host)

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> AIFeedback:
        image_bytes = self._encode_image(image)
        messages = self._build_messages(image_bytes)

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                raw = self._call_ollama(messages)
                return self._parse_response(raw)
            except (ConnectionError, ollama.ResponseError, ollama.RequestError) as e:
                last_error = e
                if attempt == 0:
                    continue
                break

        raise ConnectionError(
            f"Ollama not available at {self._host} (model: {self._model}). "
            "Ensure Ollama is running: ollama serve"
        ) from last_error

    def _encode_image(self, image: LoadedImage) -> bytes:
        success, buffer = cv2.imencode(".jpg", image.resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode image for AI feedback")
        return buffer.tobytes()

    def _build_messages(self, image_bytes: bytes) -> list[dict]:
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_PROMPT, "images": [image_bytes]},
        ]

    def _call_ollama(self, messages: list[dict]) -> str:
        response: ChatResponse = self._client.chat(
            model=self._model,
            messages=messages,
            format="json",
        )
        return response.message.content or ""

    def _parse_response(self, raw: str) -> AIFeedback:
        data = self._extract_json(raw)
        if data is None:
            return AIFeedback(description="AI feedback unavailable", score=50.0)

        score = data.get("score", 50)
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 50.0
        score = max(0.0, min(100.0, score))

        strengths = data.get("strengths", [])
        if isinstance(strengths, str):
            strengths = [strengths]
        strengths = [str(s) for s in strengths[:5]]

        improvements = data.get("improvements", [])
        if isinstance(improvements, str):
            improvements = [improvements]
        improvements = [str(s) for s in improvements[:5]]

        return AIFeedback(
            description=str(data.get("description", "")),
            genre=str(data.get("genre", "")),
            strengths=strengths,
            improvements=improvements,
            mood=str(data.get("mood", "")),
            score=round(score, 1),
            reasoning=str(data.get("reasoning", "")),
        )

    @staticmethod
    def _extract_json(raw: str) -> dict | None:
        # Attempt 1: direct parse
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Attempt 2: strip markdown code fences
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        # Attempt 3: brace-matching to find first {...} block
        start = raw.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(raw[start : i + 1])
                            if isinstance(data, dict):
                                return data
                        except json.JSONDecodeError:
                            pass
                        break

        return None
