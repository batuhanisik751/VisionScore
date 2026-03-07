from __future__ import annotations

import json
from unittest.mock import patch

import numpy as np
import pytest

from visionscore.analyzers.ai_feedback import AIFeedbackAnalyzer, _SYSTEM_PROMPT
from visionscore.models import AIFeedback
from visionscore.pipeline.loader import LoadedImage, load_image

VALID_JSON_RESPONSE = json.dumps(
    {
        "genre": "landscape",
        "description": "A mountain lake at sunset",
        "strengths": [
            "Excellent golden hour light",
            "Strong leading lines",
            "Clean horizon",
        ],
        "improvements": [
            "Foreground could be stronger",
            "Consider wider angle",
            "Sky slightly overexposed",
        ],
        "mood": "serene",
        "score": 78,
        "reasoning": "A well-composed landscape with beautiful light.",
    }
)


@pytest.fixture
def analyzer() -> AIFeedbackAnalyzer:
    return AIFeedbackAnalyzer(host="http://localhost:11434", model="llava")


# ---- Image Encoding ----


class TestImageEncoding:
    def test_encode_produces_jpeg_bytes(self, analyzer: AIFeedbackAnalyzer) -> None:
        image = LoadedImage(
            original=np.zeros((100, 100, 3), dtype=np.uint8),
            resized=np.zeros((100, 100, 3), dtype=np.uint8),
            path="test.jpg",
            format="JPEG",
            width=100,
            height=100,
        )
        result = analyzer._encode_image(image)
        assert result[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_encode_different_shapes(self, analyzer: AIFeedbackAnalyzer) -> None:
        for shape in [(50, 80, 3), (200, 300, 3), (10, 10, 3)]:
            image = LoadedImage(
                original=np.zeros(shape, dtype=np.uint8),
                resized=np.zeros(shape, dtype=np.uint8),
                path="test.jpg",
                format="JPEG",
                width=shape[1],
                height=shape[0],
            )
            result = analyzer._encode_image(image)
            assert isinstance(result, bytes)
            assert len(result) > 0


# ---- Prompt Construction ----


class TestPromptConstruction:
    def test_messages_structure(self, analyzer: AIFeedbackAnalyzer) -> None:
        image_bytes = b"\xff\xd8\xff\xe0fake_jpeg"
        messages = analyzer._build_messages(image_bytes)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "images" in messages[1]
        assert messages[1]["images"] == [image_bytes]

    def test_system_prompt_contains_required_fields(self) -> None:
        for field in [
            "genre",
            "description",
            "strengths",
            "improvements",
            "mood",
            "score",
            "reasoning",
        ]:
            assert field in _SYSTEM_PROMPT


# ---- JSON Parsing ----


class TestJsonParsing:
    def test_parse_valid_json(self, analyzer: AIFeedbackAnalyzer) -> None:
        result = analyzer._parse_response(VALID_JSON_RESPONSE)
        assert result.genre == "landscape"
        assert result.score == 78.0
        assert len(result.strengths) == 3
        assert len(result.improvements) == 3

    def test_parse_json_in_code_fence(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = f"```json\n{VALID_JSON_RESPONSE}\n```"
        result = analyzer._parse_response(raw)
        assert result.genre == "landscape"

    def test_parse_json_with_surrounding_text(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = f"Here is my analysis:\n{VALID_JSON_RESPONSE}\nI hope this helps!"
        result = analyzer._parse_response(raw)
        assert result.genre == "landscape"

    def test_parse_malformed_returns_default(self, analyzer: AIFeedbackAnalyzer) -> None:
        result = analyzer._parse_response("This is not JSON at all.")
        assert result.description == "AI feedback unavailable"
        assert result.score == 50.0

    def test_parse_empty_string_returns_default(self, analyzer: AIFeedbackAnalyzer) -> None:
        result = analyzer._parse_response("")
        assert result.description == "AI feedback unavailable"
        assert result.score == 50.0

    def test_parse_missing_fields_uses_defaults(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = json.dumps({"score": 65})
        result = analyzer._parse_response(raw)
        assert result.score == 65.0
        assert result.genre == ""
        assert result.strengths == []

    def test_parse_score_clamped_high(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = json.dumps({"score": 150})
        result = analyzer._parse_response(raw)
        assert result.score == 100.0

    def test_parse_score_clamped_low(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = json.dumps({"score": -10})
        result = analyzer._parse_response(raw)
        assert result.score == 0.0

    def test_parse_score_as_string(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = json.dumps({"score": "75"})
        result = analyzer._parse_response(raw)
        assert result.score == 75.0

    def test_parse_strengths_as_string(self, analyzer: AIFeedbackAnalyzer) -> None:
        raw = json.dumps({"strengths": "Good lighting"})
        result = analyzer._parse_response(raw)
        assert result.strengths == ["Good lighting"]


# ---- Extract JSON (static method) ----


class TestExtractJson:
    def test_direct_json(self) -> None:
        raw = '{"key": "value"}'
        assert AIFeedbackAnalyzer._extract_json(raw) == {"key": "value"}

    def test_fenced_json(self) -> None:
        raw = '```json\n{"key": "value"}\n```'
        assert AIFeedbackAnalyzer._extract_json(raw) == {"key": "value"}

    def test_brace_matching(self) -> None:
        raw = 'Some text before {"key": "value"} and after'
        assert AIFeedbackAnalyzer._extract_json(raw) == {"key": "value"}

    def test_no_json_returns_none(self) -> None:
        assert AIFeedbackAnalyzer._extract_json("just plain text") is None

    def test_nested_braces(self) -> None:
        raw = '{"outer": {"inner": 1}}'
        result = AIFeedbackAnalyzer._extract_json(raw)
        assert result == {"outer": {"inner": 1}}


# ---- Retry Logic ----


class TestRetryLogic:
    def test_succeeds_on_first_attempt(
        self, analyzer: AIFeedbackAnalyzer, normal_image_path
    ) -> None:
        image = load_image(normal_image_path)
        with patch.object(
            analyzer._client,
            "chat",
            return_value=_make_chat_response(VALID_JSON_RESPONSE),
        ) as mock_chat:
            result = analyzer.analyze(image)
            assert mock_chat.call_count == 1
        assert isinstance(result, AIFeedback)

    def test_retries_once_then_succeeds(
        self, analyzer: AIFeedbackAnalyzer, normal_image_path
    ) -> None:
        image = load_image(normal_image_path)
        with patch.object(
            analyzer._client,
            "chat",
            side_effect=[
                ConnectionError("refused"),
                _make_chat_response(VALID_JSON_RESPONSE),
            ],
        ) as mock_chat:
            result = analyzer.analyze(image)
            assert mock_chat.call_count == 2
        assert result.genre == "landscape"

    def test_raises_after_two_failures(
        self, analyzer: AIFeedbackAnalyzer, normal_image_path
    ) -> None:
        image = load_image(normal_image_path)
        with patch.object(
            analyzer._client,
            "chat",
            side_effect=ConnectionError("refused"),
        ):
            with pytest.raises(ConnectionError, match="Ollama not available"):
                analyzer.analyze(image)

    def test_retries_on_response_error(
        self, analyzer: AIFeedbackAnalyzer, normal_image_path
    ) -> None:
        image = load_image(normal_image_path)
        import ollama

        with patch.object(
            analyzer._client,
            "chat",
            side_effect=[
                ollama.ResponseError("model not found"),
                _make_chat_response(VALID_JSON_RESPONSE),
            ],
        ) as mock_chat:
            result = analyzer.analyze(image)
            assert mock_chat.call_count == 2
        assert isinstance(result, AIFeedback)


# ---- Integration ----


class TestAnalyzeIntegration:
    def test_returns_ai_feedback_model(
        self, analyzer: AIFeedbackAnalyzer, normal_image_path
    ) -> None:
        image = load_image(normal_image_path)
        with patch.object(
            analyzer._client,
            "chat",
            return_value=_make_chat_response(VALID_JSON_RESPONSE),
        ):
            result = analyzer.analyze(image)
        assert isinstance(result, AIFeedback)

    def test_all_fields_populated(self, analyzer: AIFeedbackAnalyzer, normal_image_path) -> None:
        image = load_image(normal_image_path)
        with patch.object(
            analyzer._client,
            "chat",
            return_value=_make_chat_response(VALID_JSON_RESPONSE),
        ):
            result = analyzer.analyze(image)
        assert result.genre == "landscape"
        assert result.description == "A mountain lake at sunset"
        assert result.mood == "serene"
        assert len(result.strengths) == 3
        assert len(result.improvements) == 3
        assert result.reasoning != ""

    def test_score_in_valid_range(self, analyzer: AIFeedbackAnalyzer, normal_image_path) -> None:
        image = load_image(normal_image_path)
        with patch.object(
            analyzer._client,
            "chat",
            return_value=_make_chat_response(VALID_JSON_RESPONSE),
        ):
            result = analyzer.analyze(image)
        assert 0 <= result.score <= 100


# ---- Helpers ----


def _make_chat_response(content: str):
    """Build a minimal mock object mimicking ollama ChatResponse."""
    from unittest.mock import MagicMock

    response = MagicMock()
    response.message.content = content
    return response
