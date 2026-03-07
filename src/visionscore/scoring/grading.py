from __future__ import annotations

from visionscore.models import Grade

_THRESHOLDS: list[tuple[float, Grade]] = [
    (95.0, Grade.S),
    (85.0, Grade.A),
    (70.0, Grade.B),
    (55.0, Grade.C),
    (40.0, Grade.D),
]

_GRADE_COLORS: dict[Grade, str] = {
    Grade.S: "magenta",
    Grade.A: "green",
    Grade.B: "blue",
    Grade.C: "yellow",
    Grade.D: "red",
    Grade.F: "bold red",
}


def assign_grade(score: float) -> Grade:
    """Map a 0-100 score to a letter grade."""
    for threshold, grade in _THRESHOLDS:
        if score >= threshold:
            return grade
    return Grade.F


def grade_color(grade: Grade) -> str:
    """Return a Rich color string for the given grade."""
    return _GRADE_COLORS.get(grade, "white")
