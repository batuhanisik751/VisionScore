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

    def aggregate(
        self,
        report: AnalysisReport,
        plugin_weights: dict[str, tuple[float, str]] | None = None,
    ) -> float:
        active: list[tuple[float, float]] = []
        weight_map = self._weights.model_dump()

        for key, (attr, field) in _SCORE_FIELDS.items():
            component = getattr(report, attr, None)
            if component is None:
                continue
            score = getattr(component, field)
            active.append((weight_map[key], score))

        # Plugin contributions
        if plugin_weights:
            for plugin_name, (weight, score_field) in plugin_weights.items():
                if weight <= 0.0:
                    continue
                plugin_data = report.plugin_results.get(plugin_name)
                if not isinstance(plugin_data, dict):
                    continue
                score = plugin_data.get(score_field, 0.0)
                if isinstance(score, (int, float)):
                    active.append((weight, float(score)))

        if not active:
            return 0.0

        total_weight = sum(w for w, _ in active)
        overall = sum((w / total_weight) * s for w, s in active)
        return round(max(0.0, min(100.0, overall)), 1)
