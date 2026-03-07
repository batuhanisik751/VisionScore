from __future__ import annotations

from visionscore.config import AnalysisWeights
from visionscore.models import AnalysisReport


_SCORE_FIELDS: dict[str, tuple[str, str]] = {
    "technical": ("technical", "overall"),
    "aesthetic": ("aesthetic", "overall"),
    "composition": ("composition", "overall"),
    "ai_feedback": ("ai_feedback", "score"),
}


class ScoreAggregator:
    """Compute a weighted overall score from available analyzer results."""

    def __init__(self, weights: AnalysisWeights | None = None) -> None:
        self._weights = weights or AnalysisWeights()

    def aggregate(self, report: AnalysisReport) -> float:
        active: list[tuple[float, float]] = []
        weight_map = self._weights.model_dump()

        for key, (attr, field) in _SCORE_FIELDS.items():
            component = getattr(report, attr, None)
            if component is None:
                continue
            score = getattr(component, field)
            active.append((weight_map[key], score))

        if not active:
            return 0.0

        total_weight = sum(w for w, _ in active)
        overall = sum((w / total_weight) * s for w, s in active)
        return round(max(0.0, min(100.0, overall)), 1)
