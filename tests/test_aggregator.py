from __future__ import annotations

import pytest

from visionscore.config import AnalysisWeights
from visionscore.models import (
    AIFeedback,
    AestheticScore,
    AnalysisReport,
    CompositionScore,
    ImageMeta,
    TechnicalScore,
)
from visionscore.scoring.aggregator import ScoreAggregator


def _meta() -> ImageMeta:
    return ImageMeta(path="test.jpg", width=200, height=200, format="JPEG")


def _tech(overall: float = 70.0) -> TechnicalScore:
    return TechnicalScore(
        sharpness=70, exposure=70, noise=70, dynamic_range=70, overall=overall
    )


def _aesthetic(overall: float = 80.0) -> AestheticScore:
    return AestheticScore(nima_score=80, std_dev=1.0, confidence=0.8, overall=overall)


def _composition(overall: float = 60.0) -> CompositionScore:
    return CompositionScore(
        rule_of_thirds=60, subject_position=60, horizon=60, balance=60, overall=overall
    )


def _ai(score: float = 75.0) -> AIFeedback:
    return AIFeedback(description="test", genre="landscape", score=score)


class TestScoreAggregator:
    def test_all_present(self) -> None:
        report = AnalysisReport(
            image_meta=_meta(),
            technical=_tech(70),
            aesthetic=_aesthetic(80),
            composition=_composition(60),
            ai_feedback=_ai(75),
        )
        agg = ScoreAggregator()
        # 0.25*70 + 0.30*80 + 0.25*60 + 0.20*75 = 17.5 + 24 + 15 + 15 = 71.5
        assert agg.aggregate(report) == 71.5

    def test_aesthetic_missing(self) -> None:
        report = AnalysisReport(
            image_meta=_meta(),
            technical=_tech(70),
            aesthetic=None,
            composition=_composition(60),
            ai_feedback=_ai(75),
        )
        agg = ScoreAggregator()
        # active weights: 0.25 + 0.25 + 0.20 = 0.70
        # (0.25/0.70)*70 + (0.25/0.70)*60 + (0.20/0.70)*75
        expected = (0.25 / 0.70) * 70 + (0.25 / 0.70) * 60 + (0.20 / 0.70) * 75
        assert agg.aggregate(report) == round(expected, 1)

    def test_two_missing(self) -> None:
        report = AnalysisReport(
            image_meta=_meta(),
            technical=_tech(80),
            aesthetic=None,
            composition=_composition(60),
            ai_feedback=None,
        )
        agg = ScoreAggregator()
        # active weights: 0.25 + 0.25 = 0.50
        # (0.25/0.50)*80 + (0.25/0.50)*60 = 40 + 30 = 70
        assert agg.aggregate(report) == 70.0

    def test_all_missing(self) -> None:
        report = AnalysisReport(image_meta=_meta())
        agg = ScoreAggregator()
        assert agg.aggregate(report) == 0.0

    def test_only_technical(self) -> None:
        report = AnalysisReport(image_meta=_meta(), technical=_tech(85))
        agg = ScoreAggregator()
        assert agg.aggregate(report) == 85.0

    def test_custom_weights(self) -> None:
        weights = AnalysisWeights(
            technical=0.50, aesthetic=0.50, composition=0.0, ai_feedback=0.0
        )
        report = AnalysisReport(
            image_meta=_meta(), technical=_tech(80), aesthetic=_aesthetic(60)
        )
        agg = ScoreAggregator(weights=weights)
        assert agg.aggregate(report) == 70.0

    def test_all_scores_zero(self) -> None:
        report = AnalysisReport(
            image_meta=_meta(),
            technical=_tech(0),
            aesthetic=_aesthetic(0),
            composition=_composition(0),
            ai_feedback=_ai(0),
        )
        agg = ScoreAggregator()
        assert agg.aggregate(report) == 0.0

    def test_all_scores_hundred(self) -> None:
        report = AnalysisReport(
            image_meta=_meta(),
            technical=_tech(100),
            aesthetic=_aesthetic(100),
            composition=_composition(100),
            ai_feedback=_ai(100),
        )
        agg = ScoreAggregator()
        assert agg.aggregate(report) == 100.0
