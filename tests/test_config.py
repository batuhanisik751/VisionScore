from __future__ import annotations

from pathlib import Path

from visionscore.config import Settings


class TestExpandPath:
    def test_model_dir_tilde_expanded(self) -> None:
        s = Settings(model_dir="~/my_models")
        assert "~" not in str(s.model_dir)
        assert s.model_dir == Path.home() / "my_models"

    def test_plugin_dir_tilde_expanded(self) -> None:
        s = Settings(plugin_dir="~/my_plugins")
        assert "~" not in str(s.plugin_dir)
        assert s.plugin_dir == Path.home() / "my_plugins"

    def test_model_dir_path_object_expanded(self) -> None:
        s = Settings(model_dir=Path("~/models"))
        assert "~" not in str(s.model_dir)
        assert s.model_dir == Path.home() / "models"

    def test_plugin_dir_path_object_expanded(self) -> None:
        s = Settings(plugin_dir=Path("~/plugins"))
        assert "~" not in str(s.plugin_dir)
        assert s.plugin_dir == Path.home() / "plugins"

    def test_model_dir_absolute_unchanged(self) -> None:
        s = Settings(model_dir="/tmp/models")
        assert s.model_dir == Path("/tmp/models")


class TestExpandOptionalPath:
    def test_custom_model_path_none_stays_none(self) -> None:
        s = Settings(custom_model_path=None)
        assert s.custom_model_path is None

    def test_custom_model_path_empty_string_becomes_none(self) -> None:
        s = Settings(custom_model_path="")
        assert s.custom_model_path is None

    def test_custom_model_path_whitespace_becomes_none(self) -> None:
        s = Settings(custom_model_path="   ")
        assert s.custom_model_path is None

    def test_custom_model_path_tilde_expanded(self) -> None:
        s = Settings(custom_model_path="~/my_model.pt")
        assert "~" not in str(s.custom_model_path)
        assert s.custom_model_path == Path.home() / "my_model.pt"

    def test_custom_model_path_path_object_expanded(self) -> None:
        s = Settings(custom_model_path=Path("~/model.pt"))
        assert "~" not in str(s.custom_model_path)
        assert s.custom_model_path == Path.home() / "model.pt"

    def test_custom_model_path_absolute_unchanged(self) -> None:
        s = Settings(custom_model_path="/tmp/model.pt")
        assert s.custom_model_path == Path("/tmp/model.pt")
