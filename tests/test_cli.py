from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from visionscore.cli import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_info_command(normal_image_path: Path):
    result = runner.invoke(app, ["info", str(normal_image_path)])
    assert result.exit_code == 0
    assert "200" in result.output
