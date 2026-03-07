from __future__ import annotations

import pytest

from visionscore.models import Grade
from visionscore.scoring.grading import assign_grade, grade_color


class TestAssignGrade:
    def test_zero_is_f(self) -> None:
        assert assign_grade(0) == Grade.F

    def test_39_is_f(self) -> None:
        assert assign_grade(39.9) == Grade.F

    def test_40_is_d(self) -> None:
        assert assign_grade(40) == Grade.D

    def test_54_is_d(self) -> None:
        assert assign_grade(54.9) == Grade.D

    def test_55_is_c(self) -> None:
        assert assign_grade(55) == Grade.C

    def test_69_is_c(self) -> None:
        assert assign_grade(69.9) == Grade.C

    def test_70_is_b(self) -> None:
        assert assign_grade(70) == Grade.B

    def test_84_is_b(self) -> None:
        assert assign_grade(84.9) == Grade.B

    def test_85_is_a(self) -> None:
        assert assign_grade(85) == Grade.A

    def test_94_is_a(self) -> None:
        assert assign_grade(94.9) == Grade.A

    def test_95_is_s(self) -> None:
        assert assign_grade(95) == Grade.S

    def test_100_is_s(self) -> None:
        assert assign_grade(100) == Grade.S


class TestGradeColor:
    def test_all_grades_have_color(self) -> None:
        for grade in Grade:
            color = grade_color(grade)
            assert isinstance(color, str)
            assert len(color) > 0

    def test_s_is_magenta(self) -> None:
        assert grade_color(Grade.S) == "magenta"

    def test_a_is_green(self) -> None:
        assert grade_color(Grade.A) == "green"

    def test_f_is_bold_red(self) -> None:
        assert grade_color(Grade.F) == "bold red"
